from __future__ import annotations

import re
import os
import pickle
import random
import functools
from typing import Any, Optional
from pathlib import Path
import json
from dataclasses import dataclass

# from datasets import Dataset
from torch.utils.data import Dataset

from transformers import AutoTokenizer, PreTrainedTokenizer, BatchEncoding
from tactic_gen.data_collator_compat import DataCollatorForCompletionOnlyLM
from tactic_gen.augment import (selective_types, definitions, project_of,
                                types_v2, definitions_v2)   # rango-augmented: [TYPES]/[DEFINITIONS] canonical 규칙(train/infer 공유)
import jsonlines
from data_management.dataset_file import DatasetFile
from data_management.sentence_db import SentenceDB
from data_management.jsonl_utils import ExampleDB
from data_management.line_dict import LineDict
from data_management.splits import Split
from data_management.dataset_file import DPCache, StepID


# ── 타입-지향 premise 재랭킹 (RERANK_PREMISES=1). apply 대상 lemma를 결론매칭으로 앞으로. ──
#   근거: docs/grpo/TYPED_RERANK_AND_COMPOSITION.md (BM25 top-1 22%→재랭킹 36%). AU applyshape의 경량판.
_RR_LN = re.compile(r'(?:Lemma|Theorem|Definition|Corollary|Remark|Fact|Fixpoint)\s+[A-Za-z_][\w\'\.]*\s*:?\s*(.*)', re.S)

def _rr_goal_concl(goal: str) -> str:
    parts = (goal or "").split('\n\n', 1)
    return parts[1] if len(parts) > 1 else (goal or "")

def _rr_prem_concl(ptext: str) -> str:
    m = _RR_LN.match((ptext or "").strip())
    body = m.group(1) if m else (ptext or "")
    depth = 0; last = -1; i = 0
    while i < len(body) - 1:
        ch = body[i]
        if ch == '(': depth += 1
        elif ch == ')': depth -= 1
        elif depth == 0 and body[i:i+2] == '->': last = i
        i += 1
    return body[last+2:] if last >= 0 else body

def _rr_chead(txt: str):
    m = re.match(r"\(?\s*([A-Za-z_][\w'\.]*)", (txt or "").strip())
    return m.group(1).split('.')[-1] if m else None

_RR_KW = {'forall','exists','fun','match','with','end','let','in','if','then','else',
          'Type','Prop','Set','return','as','fix','cofix'}

# notation → 숨은 연산 이름 (goal은 '^'로 보이지만 lemma는 'Zpower'로 씀 → 매칭 복구).
#   surgical(흔한 것만) — Set Printing All처럼 goal 전개 안 함(프롬프트 안 터짐). 등식/순서 심볼 제외(너무 흔함).
_RR_NOTA = {'^': ['Zpower', 'pow', 'Rpower'], '?=': ['compare'], '<?': ['ltb'],
            '<=?': ['leb'], '=?': ['eqb']}

def _rr_ops(txt: str) -> set:
    """연산/술어 head 집합 = 대문자시작 or qualified(.) or 소문자라도 길이>1 식별자 중 키워드 제외.
    (등식 'a=b'에서 첫토큰만 보는 chead의 약점 보완 — 연산 이름 전부를 신호로.) + notation 확장."""
    out = set()
    for t in re.findall(r"[A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*", txt or ""):
        s = t.split('.')[-1]
        if s in _RR_KW or len(s) < 2:
            continue
        if t[0].isupper() or '.' in t or len(s) >= 3:
            out.add(s)
    for sym, names in _RR_NOTA.items():          # notation 심볼 있으면 숨은 연산이름 추가
        if sym in (txt or ""):
            out.update(names)
    return out

def _rr_score(goal_c: str, prem: str) -> float:
    pc = _rr_prem_concl(prem)
    s = 0.0
    gh, ph = _rr_chead(goal_c), _rr_chead(pc)
    if gh and ph and gh == ph: s += 3.0                          # 결론 최상위 head 일치
    go, po = _rr_ops(goal_c), _rr_ops(pc)
    s += len(go & po) * 1.0                                       # 연산/술어 head 중첩(등식·rewrite 강신호)
    s += len(set(re.findall(r"[A-Za-z_][\w']*", goal_c)) & set(re.findall(r"[A-Za-z_][\w']*", pc))) * 0.1
    if ('=' in goal_c) == ('=' in pc): s += 0.3                   # 등식/비등식 형태 일치
    return s

_RR_ALPHA = 5.0   # 블렌드 가중: BM25순위 prior + α×타입지향점수. (검증: α=5가 gold·rollout 모두 top-1/5 최선)

def rerank_premises(example) -> Optional[list]:
    """example.premises를 **블렌드**(BM25 원순위 prior + α×타입지향점수)로 재정렬.
    순수 rerank는 쉬운케이스(gold가 이미 BM25상위)를 흔들어 top-5 저하 → BM25 prior로 방지하면서
    묻힌 gold를 끌어올림. 검증(7 데이터셋): top-1 +11~18pp, top-5 regression 없음. premises 없으면 None.
    ※ 안정정렬 아님 주의 — 명시적 tie-break(원순위 i)로 결정성 보장."""
    prem = getattr(example, "premises", None)
    if not prem:
        return prem
    gc = _rr_goal_concl(getattr(example, "proof_state", "") or "")
    n = len(prem)
    # 점수 = (원순위 prior: 앞=높음) + α×타입매칭. 동점은 원순위 i로 결정적 tie-break.
    scored = [((n - i) + _RR_ALPHA * _rr_score(gc, prem[i]), -i, i) for i in range(n)]
    scored.sort(key=lambda x: (-x[0], -x[1]))
    return [prem[i] for _, _, i in scored]


# ── [TYPES] 구조컨텍스트 주입 (INJECT_TYPES=1). rango-augmented 1차 구성의 두번째 레버. ──
#   근거: docs/grpo/rango_augmented/{PLAN,REVIEW}.md — selective 규칙(가설+결론 inductive 타입,
#   ≤8생성자, top-6, ≤200토큰)은 canonical `tactic_gen.augment.selective_types` 하나만 쓴다
#   (학습·추론·검증스크립트 공유 = R1 포맷불일치 방지).
#   ★ 독립 토큰예산: premise/state/proof 예산을 건드리지 않고 [TYPES] 자체 캡(TYPES_TOKENS, 기본 200)만
#     적용 → premise 를 밀어내지 않음(REVIEW R2). dry-run 실측 중앙 +50토큰(4096 budget 초과 +0.4pp).
_IT_INDEX: Optional[dict] = None


def _it_index() -> dict:
    """inductive 생성자 인덱스(정제본) 지연로드. 없으면 {} → [TYPES] 자동 비활성(프롬프트=base)."""
    global _IT_INDEX
    if _IT_INDEX is None:
        path = os.environ.get("IND_INDEX_PATH", "data/ind_constructors_clean.json")
        try:
            with open(path) as f:
                _IT_INDEX = json.load(f)
            _logger.info(f"[TYPES] inductive 인덱스 {len(_IT_INDEX)}타입 로드: {path}")
        except OSError:
            _logger.warning(f"[TYPES] 인덱스 없음({path}) — INJECT_TYPES 무시(base 프롬프트)")
            _IT_INDEX = {}
    return _IT_INDEX


_FD_INDEX: Optional[dict] = None


def _fd_index() -> dict:
    """함수 정의 인덱스 지연로드(scripts/build_func_defs.py 산출). 없으면 {} → [DEFINITIONS] 비활성."""
    global _FD_INDEX
    if _FD_INDEX is None:
        path = os.environ.get("FUNC_DEFS_PATH", "data/func_defs.json")
        try:
            with open(path) as f:
                _FD_INDEX = json.load(f)
            _logger.info(f"[DEFINITIONS] 함수정의 인덱스 {len(_FD_INDEX)}개 로드: {path}")
        except OSError:
            _logger.warning(f"[DEFINITIONS] 인덱스 없음({path}) — INJECT_DEFS 무시")
            _FD_INDEX = {}
    return _FD_INDEX


TYPES_SEP = "\n[TYPES]\n"
DEFS_SEP = "\n[DEFINITIONS]\n"

# augment_v2_section 이 방금 주입한 {이름: 정의문}. 인용 타깃(cite_target)이 참조한다.
#   ※ 같은 예제에 대해 collate_input → collate 가 연달아 불리므로 모듈 전역으로 충분하다
#     (dataloader 워커는 프로세스가 분리되어 서로 간섭하지 않음).
_LAST_INJECTED: dict = {}


def defs_section(tokenizer: PreTrainedTokenizer, example: LmExample,
                 exclude: Optional[set] = None) -> str:
    """INJECT_DEFS=1 이면 '\\n[DEFINITIONS]\\n<함수 정의문>...' 섹션, 아니면 "".

    goal 결론의 함수 정의를 복원해 상태를 완전하게 만든다(PHASE2_DECIDER_GUIDE §D).
    ★ 너무 긴 정의는 시그니처만, 시그니처도 길면 아예 넣지 않는다(DEFS_MAX_BODY/DEFS_MAX_SIG).
    [TYPES] 와 **별도의 독립 예산**(DEFS_TOKENS, 기본 200) — premise 를 밀어내지 않는다."""
    if os.environ.get("INJECT_DEFS", "0") != "1":
        return ""
    # ★ ablation(ABLATE_DEFS=1): 섹션 **헤더는 유지**하고 내용만 비운다.
    #   그냥 INJECT_DEFS=0 으로 끄면 프롬프트 포맷 자체가 달라져(=학습과 불일치, OOD) 성능이 떨어져도
    #   "정보가 필요했다"의 증거가 못 된다. 포맷을 고정해야 **정보의 기여**만 분리된다.
    if os.environ.get("ABLATE_DEFS", "0") == "1":
        return DEFS_SEP + "(none)"
    idx = _fd_index()
    if not idx:
        return ""

    def _ntok(s: str) -> int:
        return len(tokenizer(s or "", add_special_tokens=False)["input_ids"])

    lines = definitions(
        getattr(example, "proof_state", "") or "", idx,
        project=getattr(example, "file_name", None),   # ★ 파일 경로 전체 — 같은 파일→디렉토리→프로젝트 순 선택
        max_defs=int(os.environ.get("DEFS_MAX", "5")),
        budget_tok=int(os.environ.get("DEFS_TOKENS", "200")),
        max_body=int(os.environ.get("DEFS_MAX_BODY", "80")),
        max_sig=int(os.environ.get("DEFS_MAX_SIG", "40")),
        ntok=_ntok,
        exclude=exclude,                                   # [TYPES] 에 이미 나온 이름은 제외
    )
    if not lines:
        return ""
    return DEFS_SEP + "\n".join(line for _, line in lines)


def augment_v2_section(tokenizer: PreTrainedTokenizer, example: LmExample,
                       base_str: str) -> str:
    """AUGMENT_V2=1 일 때 프롬프트 **맨 뒤**(응답 템플릿 직전)에 붙일 [TYPES]/[DEFINITIONS] 블록.

    v1 과 다른 점:
      · 위치: [STATE] 앞 → **맨 뒤**. 생성 지점에 가까워 recency 이득, 잘라낼 때 경계도 명확.
      · 내용: [TYPES] 가 생성자 이름만이 아니라 **정의문**(인자 타입 포함) + 재귀 depth1.
      · ★ 길이 보장: 남은 자리를 계산해 **이 블록만 잘라낸다**. 프롬프트 한도를 넘겨서
        토크나이저가 앞쪽(premise)을 잘라내는 일이 없도록, 여기서 먼저 예산을 맞춘다.
    """
    if os.environ.get("AUGMENT_V2", "0") != "1":
        return ""
    # ★ ablation: 섹션 **헤더는 유지**하고 내용만 비운다(포맷 고정 → 정보의 기여만 분리).
    #   그냥 INJECT_*=0 으로 끄면 프롬프트 형식 자체가 학습과 달라져(OOD) 성능이 떨어져도
    #   "정보가 필요했다"의 증거가 못 된다.
    ab_t = os.environ.get("ABLATE_TYPES", "0") == "1"
    ab_d = os.environ.get("ABLATE_DEFS", "0") == "1"
    if ab_t and ab_d:
        return (TYPES_SEP + "(none)") + (DEFS_SEP + "(none)")
    idx = _fd_index()
    if not idx:
        return ""

    def _ntok(s: str) -> int:
        return len(tokenizer(s or "", add_special_tokens=False)["input_ids"])

    hard = int(os.environ.get("HARD_SEQ_LEN", "4096"))
    out_tokens = int(os.environ.get("AUG_OUT_TOKENS", "128"))   # 정답(tactic) 자리
    margin = 16
    room = hard - _ntok(base_str) - out_tokens - margin
    if room <= 32:
        return ""                       # 자리가 없으면 아예 안 넣는다(프롬프트 보호)
    t_budget = min(int(os.environ.get("TYPES_TOKENS", "300")), room)
    goal = getattr(example, "proof_state", "") or ""
    proj = getattr(example, "file_name", None)   # ★ 파일 경로 전체(pick_def 가 거리순으로 좁힘)
    parts = []
    used = 0
    injected = {}          # ★ 실제로 프롬프트에 들어간 {이름: 정의문} — 인용 타깃 생성에 쓴다
    if os.environ.get("INJECT_TYPES", "0") == "1":
        if ab_t:
            parts.append(TYPES_SEP + "(none)")
        else:
            tl = types_v2(goal, idx, project=proj, budget_tok=t_budget, ntok=_ntok)
            if tl:
                blk = TYPES_SEP + "\n".join(l for _, l in tl)
                parts.append(blk)
                used += _ntok(blk)
                injected.update(dict(tl))
    if os.environ.get("INJECT_DEFS", "0") == "1":
        if ab_d:
            parts.append(DEFS_SEP + "(none)")
        else:
            d_budget = min(int(os.environ.get("DEFS_TOKENS", "300")), max(0, room - used))
            if d_budget > 16:
                dl = definitions_v2(goal, idx, project=proj, budget_tok=d_budget, ntok=_ntok)
                if dl:
                    parts.append(DEFS_SEP + "\n".join(l for _, l in dl))
                    injected.update(dict(dl))
    _LAST_INJECTED.clear()
    _LAST_INJECTED.update(injected)      # collate 가 바로 뒤에서 읽는다(같은 스레드·같은 예제)
    return "".join(parts)


def types_section(tokenizer: PreTrainedTokenizer, example: LmExample) -> str:
    """INJECT_TYPES=1 이면 '\\n[TYPES]\\n<T := c1 | c2>...' 섹션, 아니면 "" (=base 프롬프트 그대로).
    ※ 결정적(점수 동점은 타입명순) — 학습·추론이 같은 goal 에 같은 섹션을 만든다."""
    if os.environ.get("INJECT_TYPES", "0") != "1":
        return ""
    # ★ ablation(ABLATE_TYPES=1): 헤더 유지, 내용만 비움(defs_section 과 같은 이유 — 포맷 고정).
    if os.environ.get("ABLATE_TYPES", "0") == "1":
        return TYPES_SEP + "(none)"
    idx = _it_index()
    if not idx:
        return ""
    budget = int(os.environ.get("TYPES_TOKENS", "200"))

    def _ntok(s: str) -> int:
        return len(tokenizer(s or "", add_special_tokens=False)["input_ids"])

    lines = selective_types(
        getattr(example, "proof_state", "") or "", idx, budget_tok=budget, ntok=_ntok
    )
    if not lines:
        return ""
    return TYPES_SEP + "\n".join(line for _, line in lines)


from model_deployment.conf_utils import (
    formatter_conf_to_client_conf,
    start_servers,
    wait_for_servers,
)

from tactic_gen.lm_example import (
    LmExample,
    LmFormatter,
    FormatterConf,
    formatter_conf_from_yaml,
    formatter_from_conf,
)
from util.train_utils import allocate_tokens
from util.util import get_basic_logger
from util.shuffled_idx import ShuffledIndex
from util.constants import DATA_POINTS_NAME

_logger = get_basic_logger(__name__)

# 동적 패딩(패딩 낭비 제거). 기본 꺼짐 — 기존 동작 보존.
_DYN_PAD = os.environ.get("DYNAMIC_PADDING", "0") == "1"

# FROM HERE: https://huggingface.co/docs/trl/sft_trainer#train-on-completions-only
RESPONSE_TEMPLATE = "[TACTIC]"
NEWLINE_RESPONSE_TEMPLATE = f"\n{RESPONSE_TEMPLATE}\n"

__test_lm_json = {
    "proof_script": "Theorem rev_app : forall x l, rev l ++ [x] = rev (x::l).\nProof.\n  intros.",
    "proof_state": "x: X\nl: list X\n\nrev l ++ [x] = rev (x :: l)",
    "next_steps": ["\n  simpl.", " reflexivity.", "\nQed."],
    "proofs": [
        "Theorem rev_app_distr : forall l l' : list X, rev (l ++ l') = rev l' ++ rev l.\nProof.\n  intros.\n  induction l. destruct l'.\n    simpl. reflexivity.\n    simpl. rewrite app_nil_r. reflexivity.\n    simpl. rewrite IHl. rewrite app_assoc. reflexivity.\nQed.",
        "Theorem app_nil_r : forall l : list X, l ++ [] = l.\nProof.\n  intros.\n  induction l.\n    simpl. reflexivity.\n    simpl. rewrite IHl. reflexivity.\nQed.",
        "Theorem app_assoc : forall l m n : list X, l ++ m ++ n = (l ++ m) ++ n.\nProof.\n  intros.\n  induction l. destruct m. destruct n.\n    simpl. reflexivity.\n    simpl. reflexivity.\n    simpl. reflexivity.\n    simpl. rewrite IHl. reflexivity.\nQed.",
        "Theorem app_length : forall l l' : list X, length l + length l' = length (l ++ l').\nProof.\n  intros.\n  induction l. destruct l'.\n    simpl. reflexivity.\n    simpl. reflexivity.\n    simpl. rewrite IHl. reflexivity.\nQed.",
    ],
    "premises": [
        "Theorem rev_app_distr : forall l l' : list X, rev (l ++ l') = rev l' ++ rev l.",
        "Theorem app_nil_r : forall l : list X, l ++ [] = l.",
        "Theorem app_assoc : forall l m n : list X, l ++ m ++ n = (l ++ m) ++ n.",
        "Theorem app_length : forall l l' : list X, length l + length l' = length (l ++ l').",
    ],
}

TEST_LM_EXAMPLE = LmExample.from_json(__test_lm_json)


def whole_number_allocate(
    tokenizer: PreTrainedTokenizer,
    ss: list[str],
    allowance: int,
) -> list[str]:
    cur_allowance = allowance
    allowed_passages: list[str] = []
    for s in ss:
        s_toks = tokenizer.tokenize(s)
        cur_allowance -= len(s_toks)
        if cur_allowance < 0:
            break
        allowed_passages.append(s)
    return allowed_passages


def allocate_and_fmt(
    tokenizer: PreTrainedTokenizer,
    ss: Optional[list[str]],
    allowance: int,
    reverse: bool = True,
) -> str:
    if ss is None:
        return ""
    allowed_passages = whole_number_allocate(tokenizer, ss, allowance)
    if reverse:
        return "\n".join(allowed_passages[::-1])
    else:
        return "\n".join(allowed_passages)


@dataclass
class BasicCollatorConf:
    script_tokens: int
    state_tokens: int
    out_tokens: int
    whole_proof: bool
    ALIAS = "basic"

    @classmethod
    def from_yaml(cls, yaml_data: Any) -> BasicCollatorConf:
        return cls(
            yaml_data["script_tokens"],
            yaml_data["state_tokens"],
            yaml_data["out_tokens"],
            yaml_data.get("whole_proof", False),
        )


@dataclass
class BasicCollator:
    script_tokens: int
    state_tokens: int
    out_tokens: int
    whole_proof: bool

    STATE_SEP = "\n[STATE]\n"
    SCRIPT_SEP = "\n[SCRIPT]\n"

    def collate_input(self, tokenizer: PreTrainedTokenizer, example: LmExample) -> str:
        state_str, _ = allocate_tokens(
            tokenizer, example.proof_state, self.state_tokens
        )
        script_str, _ = allocate_tokens(
            tokenizer, example.proof_script, self.script_tokens
        )
        combined_str = (
            self.STATE_SEP
            + state_str
            + self.SCRIPT_SEP
            + script_str
            + NEWLINE_RESPONSE_TEMPLATE
        )
        return combined_str

    def collate(self, tokenizer: PreTrainedTokenizer, example: LmExample) -> str:
        input_str = self.collate_input(tokenizer, example)
        if self.whole_proof:
            target = "".join(example.next_steps)
        else:
            target = example.next_steps[0]
        out_str, _ = allocate_tokens(
            tokenizer, target, self.out_tokens, truncate_front=False
        )
        combined_str = input_str + out_str
        return combined_str

    @classmethod
    def from_conf(cls, conf: BasicCollatorConf) -> BasicCollator:
        return cls(
            conf.script_tokens,
            conf.state_tokens,
            conf.out_tokens,
            conf.whole_proof,
        )


@dataclass
class PremiseCollatorConf:
    script_tokens: int
    state_tokens: int
    premise_tokens: int
    out_tokens: int
    whole_proof: bool
    ALIAS = "premise"

    @classmethod
    def from_yaml(cls, yaml_data: Any) -> PremiseCollatorConf:
        return cls(
            yaml_data["script_tokens"],
            yaml_data["state_tokens"],
            yaml_data["premise_tokens"],
            yaml_data["out_tokens"],
            yaml_data.get("whole_proof", False),
        )


@dataclass
class PremiseCollator:
    script_tokens: int
    state_tokens: int
    premise_tokens: int
    out_tokens: int
    whole_proof: bool

    STATE_SEP = "\n[STATE]\n"
    SCRIPT_SEP = "\n[SCRIPT]\n"
    PREMISE_SEP = "\n[PREMISES]\n"

    def collate_input(self, tokenizer: PreTrainedTokenizer, example: LmExample) -> str:
        premise_str = allocate_and_fmt(tokenizer, example.premises, self.premise_tokens)
        state_str, _ = allocate_tokens(
            tokenizer, example.proof_state, self.state_tokens
        )
        script_str, _ = allocate_tokens(
            tokenizer, example.proof_script, self.script_tokens
        )
        combined_str = (
            self.PREMISE_SEP
            + premise_str
            + self.STATE_SEP
            + state_str
            + self.SCRIPT_SEP
            + script_str
            + NEWLINE_RESPONSE_TEMPLATE
        )
        return combined_str

    def collate(self, tokenizer: PreTrainedTokenizer, example: LmExample) -> str:
        input_str = self.collate_input(tokenizer, example)
        if self.whole_proof:
            target = "".join(example.next_steps)
        else:
            target = example.next_steps[0]
        out_str, _ = allocate_tokens(
            tokenizer, target, self.out_tokens, truncate_front=False
        )
        combined_str = input_str + out_str
        return combined_str

    @classmethod
    def from_conf(cls, conf: PremiseCollatorConf) -> PremiseCollator:
        return cls(
            conf.script_tokens,
            conf.state_tokens,
            conf.premise_tokens,
            conf.out_tokens,
            conf.whole_proof,
        )


@dataclass
class ProofCollatorConf:
    script_tokens: int
    state_tokens: int
    proof_tokens: int
    out_tokens: int
    whole_proof: bool
    ALIAS = "proof"

    @classmethod
    def from_yaml(cls, yaml_data: Any) -> ProofCollatorConf:
        return cls(
            yaml_data["script_tokens"],
            yaml_data["state_tokens"],
            yaml_data["proof_tokens"],
            yaml_data["out_tokens"],
            yaml_data.get("whole_proof", False),
        )


@dataclass
class ProofCollator:
    script_tokens: int
    state_tokens: int
    proof_tokens: int
    out_tokens: int
    whole_proof: bool

    STATE_SEP = "\n[STATE]\n"
    SCRIPT_SEP = "\n[SCRIPT]\n"
    PROOF_SEP = "\n[PROOFS]\n"

    def collate_input(self, tokenizer: PreTrainedTokenizer, example: LmExample) -> str:
        proof_str = allocate_and_fmt(tokenizer, example.proofs, self.proof_tokens)
        state_str, _ = allocate_tokens(
            tokenizer, example.proof_state, self.state_tokens
        )
        script_str, _ = allocate_tokens(
            tokenizer, example.proof_script, self.script_tokens
        )
        combined_str = (
            self.PROOF_SEP
            + proof_str
            + self.STATE_SEP
            + state_str
            + self.SCRIPT_SEP
            + script_str
            + NEWLINE_RESPONSE_TEMPLATE
        )
        return combined_str

    def collate(self, tokenizer: PreTrainedTokenizer, example: LmExample) -> str:
        input_str = self.collate_input(tokenizer, example)
        if self.whole_proof:
            target = "".join(example.next_steps)
        else:
            target = example.next_steps[0]
        out_str, _ = allocate_tokens(
            tokenizer, target, self.out_tokens, truncate_front=False
        )
        combined_str = input_str + out_str
        return combined_str

    @classmethod
    def from_conf(cls, conf: ProofCollatorConf) -> ProofCollator:
        return cls(
            conf.script_tokens,
            conf.state_tokens,
            conf.proof_tokens,
            conf.out_tokens,
            conf.whole_proof,
        )


@dataclass
class ProofPremiseCollatorConf:
    script_tokens: int
    state_tokens: int
    proof_tokens: int
    premise_tokens: int
    out_tokens: int
    whole_proof: bool
    ALIAS = "proof-premise"

    @classmethod
    def from_yaml(cls, yaml_data: Any) -> ProofPremiseCollatorConf:
        return cls(
            yaml_data["script_tokens"],
            yaml_data["state_tokens"],
            yaml_data["proof_tokens"],
            yaml_data["premise_tokens"],
            yaml_data["out_tokens"],
            yaml_data.get("whole_proof", False),
        )


@dataclass
class ProofPremiseCollator:
    script_tokens: int
    state_tokens: int
    proof_tokens: int
    premise_tokens: int
    out_tokens: int
    whole_proof: bool

    STATE_SEP = "\n[STATE]\n"
    SCRIPT_SEP = "\n[SCRIPT]\n"
    PROOF_SEP = "\n[PROOFS]\n"
    PREMISE_SEP = "\n[PREMISES]\n"

    def collate_input(self, tokenizer: PreTrainedTokenizer, example: LmExample) -> str:
        proof_str = allocate_and_fmt(tokenizer, example.proofs, self.proof_tokens)
        _prem = example.premises
        if os.environ.get("RERANK_PREMISES", "0") == "1":
            _prem = rerank_premises(example)   # ★ 타입-지향 재랭킹(결론매칭)로 앞쪽 우선
        premise_str = allocate_and_fmt(tokenizer, _prem, self.premise_tokens)
        state_str, _ = allocate_tokens(
            tokenizer, example.proof_state, self.state_tokens
        )
        script_str, _ = allocate_tokens(
            tokenizer, example.proof_script, self.script_tokens
        )
        # ★ 구조컨텍스트: [TYPES](생성자) + [DEFINITIONS](정의). 각각 독립예산 — premise 안 뺏음.
        #   v1(기본): [STATE] 앞에 삽입.  v2(AUGMENT_V2=1): 맨 뒤(응답 템플릿 직전) + 길이 보장.
        if os.environ.get("AUGMENT_V2", "0") == "1":
            base_str = (
                self.PREMISE_SEP + premise_str
                + self.PROOF_SEP + proof_str
                + self.STATE_SEP + state_str
                + self.SCRIPT_SEP + script_str
            )
            return base_str + augment_v2_section(tokenizer, example, base_str) + NEWLINE_RESPONSE_TEMPLATE
        types_str = types_section(tokenizer, example)   # INJECT_TYPES=0 이면 ""
        _tnames = {ln.split(" :=")[0].strip()            # [TYPES] 가 이미 보여준 타입명
                   for ln in types_str.split("\n") if " :=" in ln}
        defs_str = defs_section(tokenizer, example, exclude=_tnames)   # INJECT_DEFS=0 이면 ""
        combined_str = (
            self.PREMISE_SEP
            + premise_str
            + self.PROOF_SEP
            + proof_str
            + types_str
            + defs_str
            + self.STATE_SEP
            + state_str
            + self.SCRIPT_SEP
            + script_str
            + NEWLINE_RESPONSE_TEMPLATE
        )
        return combined_str

    def collate(self, tokenizer: PreTrainedTokenizer, example: LmExample) -> str:
        input_str = self.collate_input(tokenizer, example)   # ← _LAST_INJECTED 가 여기서 채워진다
        if self.whole_proof:
            target = "".join(example.next_steps)
        else:
            target = example.next_steps[0]
        # ★ CITE_TARGET=1: 타깃 앞에 '[USES] <쓴 정의>' 인용을 붙인다.
        #   ablation 결론(clean vs wrong 차이 ±0, McNemar p=1.000)이 "모델이 섹션을 안 읽는다"였다.
        #   원인은 loss 가 tactic 토큰에서만 계산되는데 gold 가 destruct/induction 인 비율이 10.5%뿐이라
        #   나머지 89.5% 는 섹션 없이 예측되기 때문 → **무시하는 것이 최적해**.
        #   인용을 타깃에 넣으면 섹션을 읽지 않을 때 loss 가 오르므로 gradient 압력이 생긴다.
        if os.environ.get("CITE_TARGET", "0") == "1":
            from tactic_gen.cite_target import make_cite
            cite = make_cite(target, getattr(example, "proof_state", "") or "",
                             dict(_LAST_INJECTED))
            target = cite + "\n" + target
        out_str, _ = allocate_tokens(
            tokenizer, target, self.out_tokens, truncate_front=False
        )
        combined_str = input_str + out_str
        return combined_str

    @classmethod
    def from_conf(cls, conf: ProofPremiseCollatorConf) -> ProofPremiseCollator:
        return cls(
            conf.script_tokens,
            conf.state_tokens,
            conf.proof_tokens,
            conf.premise_tokens,
            conf.out_tokens,
            conf.whole_proof,
        )


@dataclass
class NoScriptCollatorConf:
    state_tokens: int
    proof_tokens: int
    premise_tokens: int
    out_tokens: int
    whole_proof: bool
    ALIAS = "no-script"

    @classmethod
    def from_yaml(cls, yaml_data: Any) -> NoScriptCollatorConf:
        return cls(
            yaml_data["state_tokens"],
            yaml_data["proof_tokens"],
            yaml_data["premise_tokens"],
            yaml_data["out_tokens"],
            yaml_data.get("whole_proof", False),
        )


@dataclass
class NoScriptCollator:
    state_tokens: int
    proof_tokens: int
    premise_tokens: int
    out_tokens: int
    whole_proof: bool

    STATE_SEP = "\n[STATE]\n"
    PROOF_SEP = "\n[PROOFS]\n"
    PREMISE_SEP = "\n[PREMISES]\n"

    def collate_input(self, tokenizer: PreTrainedTokenizer, example: LmExample) -> str:
        proof_str = allocate_and_fmt(tokenizer, example.proofs, self.proof_tokens)
        _prem = example.premises
        if os.environ.get("RERANK_PREMISES", "0") == "1":
            _prem = rerank_premises(example)   # ★ 타입-지향 재랭킹(결론매칭)로 앞쪽 우선
        premise_str = allocate_and_fmt(tokenizer, _prem, self.premise_tokens)
        state_str, _ = allocate_tokens(
            tokenizer, example.proof_state, self.state_tokens
        )
        combined_str = (
            self.PREMISE_SEP
            + premise_str
            + self.PROOF_SEP
            + proof_str
            + self.STATE_SEP
            + state_str
            + NEWLINE_RESPONSE_TEMPLATE
        )
        return combined_str

    def collate(self, tokenizer: PreTrainedTokenizer, example: LmExample) -> str:
        input_str = self.collate_input(tokenizer, example)
        if self.whole_proof:
            target = "".join(example.next_steps)
        else:
            target = example.next_steps[0]
        out_str, _ = allocate_tokens(
            tokenizer, target, self.out_tokens, truncate_front=False
        )
        combined_str = input_str + out_str
        return combined_str

    @classmethod
    def from_conf(cls, conf: NoScriptCollatorConf) -> NoScriptCollator:
        return cls(
            conf.state_tokens,
            conf.proof_tokens,
            conf.premise_tokens,
            conf.out_tokens,
            conf.whole_proof,
        )


@functools.lru_cache(maxsize=10000)
def get_file_lines(file: Path) -> list[str]:
    with file.open("r") as f:
        return f.read().split("\n")


@dataclass
class NPrevLineCollatorConf:
    script_tokens: int
    state_tokens: int
    prefix_tokens: int
    out_tokens: int
    data_loc: Path
    line_dict_loc: Path
    whole_proof: bool
    ALIAS = "n-prev-line"

    @classmethod
    def from_yaml(cls, yaml_data: Any) -> NPrevLineCollatorConf:
        return cls(
            yaml_data["script_tokens"],
            yaml_data["state_tokens"],
            yaml_data["prefix_tokens"],
            yaml_data["out_tokens"],
            Path(yaml_data["data_loc"]),
            Path(yaml_data["line_dict_loc"]),
            yaml_data.get("whole_proof", False),
        )


@dataclass
class NPrevLineCollator:
    script_tokens: int
    state_tokens: int
    prefix_tokens: int
    out_tokens: int
    data_loc: Path
    line_dict: LineDict
    whole_proof: bool

    STATE_SEP = "\n[STATE]\n"
    SCRIPT_SEP = "\n[SCRIPT]\n"
    PREFIX_SEP = "\n[PREFIX]\n"

    def get_prefix_lines(self, file_repos_path: Path, proof_idx: int) -> list[str]:
        file_loc = self.data_loc / file_repos_path
        file_lines = get_file_lines(file_loc)

        if self.line_dict.has_file(str(file_repos_path)):
            prefix_lines = file_lines[
                : self.line_dict.get(str(file_repos_path), proof_idx)
            ]
        else:
            prefix_lines = []
        return prefix_lines

    def collate_input(self, tokenizer: PreTrainedTokenizer, example: LmExample) -> str:
        assert example.file_name is not None
        assert example.proof_idx is not None
        prefix_lines = self.get_prefix_lines(
            Path(example.file_name), example.proof_idx
        )[
            ::-1
        ]  # Take last lines
        prefix_str = allocate_and_fmt(tokenizer, prefix_lines, self.prefix_tokens)
        state_str, _ = allocate_tokens(
            tokenizer, example.proof_state, self.state_tokens
        )
        script_str, _ = allocate_tokens(
            tokenizer, example.proof_script, self.script_tokens
        )
        combined_str = (
            self.PREFIX_SEP
            + prefix_str
            + self.STATE_SEP
            + state_str
            + self.SCRIPT_SEP
            + script_str
            + NEWLINE_RESPONSE_TEMPLATE
        )
        return combined_str

    def collate(self, tokenizer: PreTrainedTokenizer, example: LmExample) -> str:
        input_str = self.collate_input(tokenizer, example)
        if self.whole_proof:
            target = "".join(example.next_steps)
        else:
            target = example.next_steps[0]
        out_str, _ = allocate_tokens(
            tokenizer, target, self.out_tokens, truncate_front=False
        )
        combined_str = input_str + out_str
        return combined_str

    @classmethod
    def from_conf(cls, conf: NPrevLineCollatorConf) -> NPrevLineCollator:
        line_dict = LineDict.load(conf.line_dict_loc)
        return cls(
            conf.script_tokens,
            conf.state_tokens,
            conf.prefix_tokens,
            conf.out_tokens,
            conf.data_loc,
            line_dict,
            conf.whole_proof,
        )


ExampleCollator = (
    BasicCollator
    | PremiseCollator
    | ProofCollator
    | ProofPremiseCollator
    | NPrevLineCollator
    | NoScriptCollator
)

ExampleCollatorConf = (
    BasicCollatorConf
    | PremiseCollatorConf
    | ProofCollatorConf
    | ProofPremiseCollatorConf
    | NPrevLineCollatorConf
    | NoScriptCollatorConf
)


def example_collator_conf_from_yaml(yaml_data: Any) -> ExampleCollatorConf:
    attempted_alias = yaml_data["alias"]
    match attempted_alias:
        case BasicCollatorConf.ALIAS:
            return BasicCollatorConf.from_yaml(yaml_data)
        case PremiseCollatorConf.ALIAS:
            return PremiseCollatorConf.from_yaml(yaml_data)
        case ProofCollatorConf.ALIAS:
            return ProofCollatorConf.from_yaml(yaml_data)
        case ProofPremiseCollatorConf.ALIAS:
            return ProofPremiseCollatorConf.from_yaml(yaml_data)
        case NPrevLineCollatorConf.ALIAS:
            return NPrevLineCollatorConf.from_yaml(yaml_data)
        case NoScriptCollatorConf.ALIAS:
            return NoScriptCollatorConf.from_yaml(yaml_data)
        case _:
            raise ValueError(f"Could not find example collator: {attempted_alias}")


def example_collator_from_conf(conf: ExampleCollatorConf) -> ExampleCollator:
    match conf:
        case BasicCollatorConf():
            return BasicCollator.from_conf(conf)
        case PremiseCollatorConf():
            return PremiseCollator.from_conf(conf)
        case ProofCollatorConf():
            return ProofCollator.from_conf(conf)
        case ProofPremiseCollatorConf():
            return ProofPremiseCollator.from_conf(conf)
        case NPrevLineCollatorConf():
            return NPrevLineCollator.from_conf(conf)
        case NoScriptCollatorConf():
            return NoScriptCollator.from_conf(conf)


class LmProcessedDataset(Dataset):
    def __init__(
        self,
        data_path: Path,
        tokenizer: PreTrainedTokenizer,
        example_collator: ExampleCollator,
        hard_seq_len: int,
        max_n_examples: Optional[int] = None,
    ) -> None:
        super(LmProcessedDataset, self).__init__()
        self.edb = ExampleDB.load(data_path)
        __shuffled_list = list(range(self.edb.size()))
        random.seed(0)
        random.shuffle(__shuffled_list)
        self.edb_map = dict(zip(range(self.edb.size()), __shuffled_list))
        self.raw_examples: list[LmExample] = []
        self.collator = DataCollatorForCompletionOnlyLM(
            response_template=NEWLINE_RESPONSE_TEMPLATE,
            tokenizer=tokenizer,
            mlm=False,
        )
        self.hard_seq_len = hard_seq_len
        self.tokenizer = tokenizer
        self.example_collator = example_collator
        self.max_n_examples = max_n_examples

    def __len__(self) -> int:
        if self.max_n_examples is not None:
            return self.max_n_examples
        return self.edb.size()

    def __getitem__(self, idx: int) -> Any:
        target_idx = self.edb_map[idx]
        target_lm_example = LmExample.from_json(
            json.loads(self.edb.retrieve(target_idx + 1))
        )
        clean_example = self.example_collator.collate(self.tokenizer, target_lm_example)
        return self.tokenizer(
            clean_example,
            max_length=self.hard_seq_len,
            truncation=True,
            # ★ DYNAMIC_PADDING=1 이면 여기서 패딩하지 않고 collator 가 배치 최장길이로 맞춘다.
            #   프롬프트 중앙이 ~1700 토큰인데 전부 4096 으로 채우면 연산의 절반 이상이 패딩이다
            #   (loss 는 pad 를 -100 으로 마스크하므로 **수학적으로 동일**, 속도만 개선).
            padding=(False if _DYN_PAD else "max_length"),
        )


@dataclass
class TacticDataConf:
    data_loc: Path
    sentence_db_loc: Path
    shuffled_index_loc: Path
    formatter_conf: FormatterConf
    model_name: str
    collator_conf: ExampleCollatorConf
    cache_loc: Path
    hard_seq_len: int
    max_n_examples: Optional[int]

    @classmethod
    def from_yaml(cls, yaml_data: Any) -> TacticDataConf:
        return cls(
            Path(yaml_data["data_loc"]),
            Path(yaml_data["sentence_db_loc"]),
            Path(yaml_data["shuffled_index_loc"]),
            formatter_conf_from_yaml(yaml_data["formatter_conf"]),
            yaml_data["model_name"],
            example_collator_conf_from_yaml(yaml_data["collator_conf"]),
            Path(yaml_data["cache_loc"]),
            yaml_data["hard_seq_len"],
            yaml_data.get("max_n_examples", None),
        )


def get_tokenizer(model_name: str, add_eos=True) -> PreTrainedTokenizer:
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    tokenizer.padding_side = "right"
    tokenizer.truncation_side = "left"
    if add_eos:
        tokenizer.add_eos_token = True
    else:
        tokenizer.add_eos_token = False
    assert tokenizer.pad_token_id != tokenizer.eos_token_id
    if model_name.startswith("codellama") or model_name.startswith(
        "openai-community/gpt"
    ):
        tokenizer.add_special_tokens({"pad_token": "[PAD]"})
        # print("ADDING PAD TOKEN")
        # tokenizer.add_eos_token = True
        # pad_token = "<PRE>"
        # encoded_ids = tokenizer.encode(pad_token)
        # assert len(encoded_ids) == 3
        # assert encoded_ids[0] == tokenizer.bos_token_id
        # assert encoded_ids[2] == tokenizer.eos_token_id

        # tokenizer.pad_token = pad_token
        # tokenizer.pad_token_id = encoded_ids[1]
    return tokenizer


class ExamplePage:
    def __init__(self, dp_name: str, page: dict[int, dict[int, LmExample]]):
        self.dp_name = dp_name
        self.page = page


class ExampleCache:
    def __init__(self, cache_loc: Path):
        self.cache_loc = cache_loc
        os.makedirs(self.cache_loc, exist_ok=True)
        self.num_cached = 0

    def get(
        self,
        step_id: StepID,
        formatter: LmFormatter,
        data_loc: Path,
        sentence_db: SentenceDB,
    ) -> Optional[LmExample]:
        file_loc = self.cache_loc / step_id.file
        if file_loc.exists():
            with file_loc.open("rb") as f:
                page: ExamplePage = pickle.load(f)
                if (
                    step_id.proof_idx in page.page
                    and step_id.step_idx in page.page[step_id.proof_idx]
                ):
                    return page.page[step_id.proof_idx][step_id.step_idx]
                else:
                    return None
        else:
            dp_loc = data_loc / DATA_POINTS_NAME / step_id.file
            dp = DatasetFile.load(dp_loc, sentence_db)
            # ★ 거대 파일 방어: 캐시 미스면 원래 **파일 전체**(모든 proof × step)를 빌드하는데,
            #   예제당 검색이 수 초인 파일(gaia 계열 등)에선 페이지 하나에 수 시간이 걸린다.
            #   그 사이 dataloader 워커가 멈추고 → HF DataLoader 는 워커 순서를 기다리므로 학습 전체가 정지.
            #   그런 파일은 **요청된 예제만** 만들어 돌려준다(캐시엔 안 남김 — 다음에 또 만들지만 수 초).
            _pairs = sum(len(p.steps) for p in dp.proofs)
            if _pairs > int(os.environ.get("CACHE_MAX_PAGE", "600")):
                if step_id.proof_idx < len(dp.proofs) and step_id.step_idx < len(
                    dp.proofs[step_id.proof_idx].steps
                ):
                    return formatter.example_from_step(
                        step_id.step_idx, step_id.proof_idx, dp, training=True
                    )
                return None
            num_examples = 0
            new_page_dict: dict[int, dict[int, LmExample]] = {}
            for proof_idx, proof in enumerate(dp.proofs):
                new_page_dict[proof_idx] = {}
                for step_idx, step in enumerate(proof.steps):
                    example = formatter.example_from_step(
                        step_idx, proof_idx, dp, training=True
                    )
                    new_page_dict[proof_idx][step_idx] = example
                    num_examples += 1
            new_page = ExamplePage(step_id.file, new_page_dict)
            self.num_cached += num_examples
            # ★ 원자적 쓰기(tmp → rename): 저장 도중 죽어도 반쪽 페이지가 캐시에 남지 않는다.
            #   (반쪽이 남으면 다음 실행이 그걸 읽다 UnpicklingError 로 죽는다. DDP 다중워커도 안전.)
            #   ※ tmp 이름은 **짧게** — data_point 파일명이 255자인 것이 195개 있어 접미사를 붙이면
            #     ENAMETOOLONG 으로 죽는다(같은 디렉토리라 rename 은 그대로 원자적).
            tmp_loc = file_loc.parent / f".tmp-{os.getpid()}-{abs(hash(step_id.file)) % 10**8}"
            with tmp_loc.open("wb") as f:
                pickle.dump(new_page, f)
            os.replace(tmp_loc, file_loc)
            if (
                step_id.proof_idx in new_page_dict
                and step_id.step_idx in new_page_dict[step_id.proof_idx]
            ):
                return new_page_dict[step_id.proof_idx][step_id.step_idx]
            else:
                return None


class LmDataset(Dataset):
    def __init__(
        self,
        data_loc: Path,
        sentence_db: SentenceDB,
        shuffled_idx: ShuffledIndex,
        split: Split,
        formatter: LmFormatter,
        tokenizer: PreTrainedTokenizer,
        example_collator: ExampleCollator,
        cache_loc: Path,
        hard_seq_len: int,
        max_n_examples: Optional[int],
    ) -> None:
        super(LmDataset, self).__init__()
        self.data_loc = data_loc
        self.sentence_db = sentence_db
        self.shuffled_idx = shuffled_idx
        self.split = split
        self.formatter = formatter
        self.tokenizer = tokenizer
        self.example_collator = example_collator
        self.hard_seq_len = hard_seq_len
        self.max_n_examples = max_n_examples
        self.collator = DataCollatorForCompletionOnlyLM(
            response_template=NEWLINE_RESPONSE_TEMPLATE,
            tokenizer=tokenizer,
            mlm=False,
        )
        self.example_cache = ExampleCache(cache_loc)

    def __len__(self) -> int:
        if self.max_n_examples is not None:
            return self.max_n_examples
        return self.shuffled_idx.split_length(self.split)

    def raw_example(self, index: int) -> LmExample:
        """index 번째 원본 LmExample(프롬프트 렌더 전). 사전점검·디버깅이 학습과 같은 예제를 보게 한다."""
        step_id = self.shuffled_idx.get_idx(self.split, index)
        get_cached = self.example_cache.get(
            step_id, self.formatter, self.data_loc, self.sentence_db
        )
        if get_cached is not None:
            return get_cached
        dp = DatasetFile.load(
            self.data_loc / DATA_POINTS_NAME / step_id.file, self.sentence_db
        )
        return self.formatter.example_from_step(
            step_id.step_idx, step_id.proof_idx, dp, training=True
        )

    def __getitem__(self, index: int) -> Any:
        example = self.raw_example(index)
        clean_example = self.example_collator.collate(self.tokenizer, example)
        return self.tokenizer(
            clean_example,
            max_length=self.hard_seq_len,
            truncation=True,
            # ★ DYNAMIC_PADDING=1 이면 여기서 패딩하지 않고 collator 가 배치 최장길이로 맞춘다.
            #   프롬프트 중앙이 ~1700 토큰인데 전부 4096 으로 채우면 연산의 절반 이상이 패딩이다
            #   (loss 는 pad 를 -100 으로 마스크하므로 **수학적으로 동일**, 속도만 개선).
            padding=(False if _DYN_PAD else "max_length"),
        )

    @classmethod
    def from_conf(
        cls, conf: TacticDataConf, split: Split, max_num_examples: Optional[int] = None
    ) -> LmDataset:
        formatter_client_conf, next_num, commands = formatter_conf_to_client_conf(
            conf.formatter_conf, 0
        )
        if 0 < len(commands):
            start_servers(commands)
            wait_for_servers(next_num)
        formatter = formatter_from_conf(formatter_client_conf)
        shuffled_idx = ShuffledIndex.load(conf.shuffled_index_loc)
        sentence_db = SentenceDB.load(conf.sentence_db_loc)
        return cls(
            conf.data_loc,
            sentence_db,
            shuffled_idx,
            split,
            formatter,
            get_tokenizer(conf.model_name),
            example_collator_from_conf(conf.collator_conf),
            conf.cache_loc,
            conf.hard_seq_len,
            max_num_examples,
        )
