from __future__ import annotations

import re
import os
import pickle
import random
import copy
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
                                types_v2, definitions_v2, pick_def)   # rango-augmented: [TYPES]/[DEFINITIONS] canonical 규칙(train/infer 공유)
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

# ── 적용가능성 가산 (APPLICABLE_RERANK=1). "닮았나"가 아니라 "**되나**"를 본다. ──
#   타입점수는 head·연산자 중첩을 세므로 `apply mul_comm` 이 안 되는데도 높은 점수를 준다.
#   `tactic_gen.applicable` 은 premise 를 `forall x…, H→…→C` 로 파싱해 C 를 goal 결론과
#   일차 단일화한다(rewrite 는 등식 한 변이 goal 부분항과 맞는지).
#
#   ★ **필터가 아니라 가산**이다. 판정 재현율이 90% 라 10% 는 gold 를 잘못 떨어뜨린다.
#     걸러내면 그만큼 정답이 사라지므로, 점수만 올려 순위로 반영한다.
#   가중치 β: CompCert gold 129건 스윕에서 20~30 이 평평한 최적 (docs 참고).
#     β=30 → top1 34.9→46.5% · top5 63.6→70.5% · top10 76.7→81.4% · top20 92.2→96.9%
#     프롬프트에 실제로 실리는 premise 가 중앙 21개이므로 **top20 이 실질 지표**다.
_RR_BETA = float(os.environ.get("APPLICABLE_BETA", "30"))
_RR_APPLICABLE = os.environ.get("APPLICABLE_RERANK", "0") == "1"


def rerank_premises(example) -> Optional[list]:
    """example.premises를 **블렌드**(BM25 원순위 prior + α×타입지향점수 [+ β×적용가능성])로 재정렬.
    순수 rerank는 쉬운케이스(gold가 이미 BM25상위)를 흔들어 top-5 저하 → BM25 prior로 방지하면서
    묻힌 gold를 끌어올림. 검증(7 데이터셋): top-1 +11~18pp, top-5 regression 없음. premises 없으면 None.
    ※ 안정정렬 아님 주의 — 명시적 tie-break(원순위 i)로 결정성 보장."""
    prem = getattr(example, "premises", None)
    if not prem:
        return prem
    state = getattr(example, "proof_state", "") or ""
    gc = _rr_goal_concl(state)
    n = len(prem)
    if _RR_APPLICABLE:
        from tactic_gen.applicable import usable_flags
        # goal 파싱 1회 + premise 분해 캐시. premise 마다 부르면 goal 을 n 번 재파싱한다.
        ok = usable_flags(state, list(prem))
    else:
        ok = None
    # 점수 = (원순위 prior: 앞=높음) + α×타입매칭 [+ β×적용가능성]. 동점은 원순위 i로 tie-break.
    scored = [((n - i) + _RR_ALPHA * _rr_score(gc, prem[i])
               + (_RR_BETA if (ok and ok[i]) else 0.0), -i, i) for i in range(n)]
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
# ★ 에러 조건부 학습(ERROR_COND=1): 직전 시도와 Coq 이 준 에러를 프롬프트에 넣는다.
#   기존 SFT 는 순수 `state -> gold tactic` 이라, 실패 정리당 INVALID 가 중앙 52회 나는데도
#   **에러에서 아무것도 배우지 않는다**. 에러에는 정답이 들어 있다
#   (`Expects a disjunctive pattern with 10 branches`, `... was not found`).
ATTEMPT_SEP = "\n[ATTEMPT]\n"
ERROR_SEP = "\n[ERROR]\n"
# ★ TYPE_FACTS=1: 모델이 '|' 를 세게 하지 말고 **미리 계산한 사실**을 준다.
#   실패의 핵심이 분기 수 오류(238건)인데, 그건 정의문을 파싱해 세야 나온다.
#   `T0: 6 ctors, arities [0,1,1,1,1,2]` 로 주면 정답 패턴이 거의 복사가 된다.
#   (아이디어 목록 4 '파생 사실 명시화')
FACTS_SEP = "\n[TYPE-FACTS]\n"

# augment_v2_section 이 방금 주입한 {이름: 정의문}. 인용 타깃(cite_target)이 참조한다.
#   ※ 같은 예제에 대해 collate_input → collate 가 연달아 불리므로 모듈 전역으로 충분하다
#     (dataloader 워커는 프로세스가 분리되어 서로 간섭하지 않음).
_LAST_INJECTED: dict = {}

# ★ 추론 정규화용 — 마지막으로 적용한 매핑을 보관한다(역매핑에 필요).
_LAST_INFER_MAPPING: dict = {}


def last_inference_mapping() -> dict:
    """직전 `collate_input` 이 적용한 정규화 매핑. 추론 후 역매핑에 쓴다."""
    return dict(_LAST_INFER_MAPPING)


def _maybe_normalize_input(text: str, example) -> str:
    """추론 프롬프트 정규화. `NORMALIZE_INFERENCE=1` 일 때만 동작한다.

    ★ 학습(`collate`)은 프롬프트와 **정답에 같은 매핑**을 적용한다. 추론에는 정답이
      없으므로 프롬프트만 바꾸고, **매핑을 남겨** 생성 결과를 되돌린다.
      되돌리지 않으면 모델이 만든 `apply L0.` 를 Coq 이 거부한다.
    """
    global _LAST_INFER_MAPPING
    _LAST_INFER_MAPPING = {}
    if os.environ.get("NORMALIZE_INFERENCE", "0") != "1":
        return text
    from tactic_gen.normalize_names import build_mapping, apply_mapping
    key = (f"{getattr(example, 'file_name', '')}:"
           f"{getattr(example, 'proof_idx', '')}:{getattr(example, 'step_idx', '')}")
    try:
        m = build_mapping(dict(_LAST_INJECTED), key, avoid_text=text,
                          premises=list(getattr(example, "premises", None) or []),
                          proof_script=getattr(example, "proof_script", "") or "")
    except Exception:
        return text
    if not m:
        return text
    _LAST_INFER_MAPPING = m
    return apply_mapping(text, m)

# distractor 샘플링용 키 목록(1회만 생성 — 예제마다 만들면 8만 원소 리스트가 매번 생긴다)
_DISTRACTOR_KEYS = None


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
    # ★ 함수 진입 즉시 초기화 — 조기 반환 경로(AUGMENT_V2 off / 인덱스 없음 / 자리 부족)가
    #   여럿이라 끝에서만 지우면 **이전 예제의 주입 이름이 남는다**.
    #   실제로 그 탓에 goal 은 정규화됐는데 정의는 없는 예제가 400개 중 20건 나왔다.
    _LAST_INJECTED.clear()
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
    # ★ TYPE_FACTS: 주입된 타입의 생성자 수·인자수를 계산해 한 줄로 명시
    if os.environ.get("TYPE_FACTS", "0") == "1" and injected:
        from model_deployment.type_constrained import ctor_arities
        facts = []
        for nm, dfn in injected.items():
            ar = ctor_arities(dfn)
            if ar:
                facts.append(f"{nm}: {len(ar)} ctors, arities {ar}")
        if facts:
            parts.append(FACTS_SEP + "\n".join(facts[:6]))
    if os.environ.get("INJECT_DEFS", "0") == "1":
        if ab_d:
            parts.append(DEFS_SEP + "(none)")
        else:
            d_budget = min(int(os.environ.get("DEFS_TOKENS", "300")), max(0, room - used))
            if d_budget > 16:
                dl = definitions_v2(goal, idx, project=proj, budget_tok=d_budget, ntok=_ntok)
                # ★ RAFT distractor: goal 과 무관한 정의를 K개 섞는다.
                #   distractor 가 없으면 '인용'은 **거기 있는 하나를 베끼기**라 판별 압력이 없다.
                #   섞으면 goal 과 맞는 것을 **골라야** 하므로 실제로 읽고 매칭해야 한다.
                #   (아이디어 목록 10 RAFT. goal 에 없는 이름이라 make_cite 는 이를 인용하지 않는다)
                k = int(os.environ.get("DISTRACTORS", "0"))
                if k > 0 and dl:
                    import hashlib as _h
                    # ★ 키 리스트를 예제마다 새로 만들면 안 된다 — 인덱스가 8만 개라
                    #   예제당 80,716원소 리스트 생성이 되어 학습이 2배 느려졌다(6.02 → s/it).
                    global _DISTRACTOR_KEYS
                    if _DISTRACTOR_KEYS is None:
                        _DISTRACTOR_KEYS = list(idx.keys())
                    keys = _DISTRACTOR_KEYS
                    seed = int(_h.md5((goal or "")[:200].encode()).hexdigest()[:8], 16)
                    have = {n for n, _ in dl} | set(injected)
                    extra = []
                    for j in range(k * 12):
                        nm = keys[(seed + j * 7919) % len(keys)]
                        if nm in have or nm in (goal or ""):
                            continue
                        d = pick_def(idx.get(nm), proj)
                        if not d or _ntok(d) > 60:
                            continue
                        extra.append((nm, d)); have.add(nm)
                        if len(extra) >= k:
                            break
                    dl = dl + extra
                if dl:
                    parts.append(DEFS_SEP + "\n".join(l for _, l in dl))
                    injected.update(dict(dl))
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

# ★ Qwen 토크나이저 대응 (실측):
#   Qwen 은 ']' 와 뒤따르는 개행을 **한 토큰**으로 병합한다(']\n\n' = 2533).
#   그래서 템플릿 "\n[TACTIC]\n" 의 토큰열이 문맥에 **한 번도 나타나지 않고**,
#   DataCollatorForCompletionOnlyLM 은 못 찾으면 **경고 없이 전체를 마스킹**한다
#   → 라벨이 0개인 채로 몇 시간을 학습하게 된다(실제로 검증에서 잡음).
#
#   실측으로 확인한 유일한 정합 조합(Qwen·deepseek 모두 12/12, 라벨==타깃):
#     · 템플릿 = "[TACTIC]\n"  (앞 개행 없음)
#     · 타깃    = 선행 개행 제거
#   프롬프트 본문은 그대로 "...\n[TACTIC]\n" 로 끝난다 — 개행 하나가 프롬프트 쪽으로 옮겨질 뿐.
#   생성 시에는 model_wrapper 가 TACTIC_LEADING_NL=1 로 개행을 다시 붙인다
#   (탐색기가 cur_proof_script + tactic 으로 이어붙이므로 개행이 없으면 Coq 구문이 깨진다).
STRIP_TARGET_NL = os.environ.get("STRIP_TARGET_NL", "0") == "1"
MASK_TEMPLATE = f"{RESPONSE_TEMPLATE}\n" if STRIP_TARGET_NL else NEWLINE_RESPONSE_TEMPLATE

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
    # ★ 담기 방식 (`PREMISE_PACK`) — 자세한 근거는 docs/premise/packing.md
    #
    #   premise 길이 편차가 극심하다(최소 16 · 중앙 147 · 최대 928 토큰).
    #   긴 것 하나(175토큰)가 뒤의 짧은 것(20토큰) 여러 개를 밀어낸다.
    #
    #     greedy   순위대로 담다가 넘치면 **중단**(원본). 긴 것 하나에 뒤가 다 막힌다
    #     skip     넘치는 것만 **건너뛴다**. 세 스플릿 모두 양수(gold +0.6~3.9pp), 비용 0
    #     knapsack 가치/무게 비로 담는다. 개수는 19→30 이지만 **긴 gold 를 버린다**
    #              (TRAIN -5.6pp / TEST +7.7pp / VAL +15.1pp — 스플릿 의존)
    #     hybrid ★ 상위 K 개는 **순위대로 무조건** 담고(긴 gold 를 지킨다),
    #              남은 예산을 knapsack 으로 채운다(짧은 것을 더 건진다)
    #
    #   hybrid 의 근거(TRAIN gold 261건 진단):
    #     · knapsack 이 버리는 gold = 순위 중앙 **3위**인데 길이 중앙 **64토큰** (36건 손해)
    #     · knapsack 이 건지는 gold = 순위 중앙 **34위**인데 길이 중앙 22토큰 (21건 이득)
    #     → 상위 K 를 지키면 손해를 막고 이득은 남는다.
    mode = os.environ.get("PREMISE_PACK", "hybrid")
    # ★ K=4 확정 (세 스플릿 실측, greedy 대비 gold 포함률)
    #     K=4   TRAIN -0.9p · TEST +9.0p · VAL +15.4p   평균 +7.8p  ← 채택
    #     K=8   TRAIN +4.4p · TEST +5.4p · VAL +11.0p   평균 +6.9p
    #     K=16  TRAIN +3.5p · TEST +2.4p · VAL  +6.2p   평균 +4.0p
    #   TRAIN 은 학습 데이터라 gold 가 이미 상위(순위 중앙 4위)이고, 실제 추론 대상은
    #   처음 보는 프로젝트다 — held-out(TEST 8위 · VAL 10위)에 맞춘다.
    topk = int(os.environ.get("PREMISE_PACK_TOPK", "4"))
    lens = [len(tokenizer.tokenize(x)) for x in ss]

    def _greedy(idxs, left, skip):
        out = []
        for i in idxs:
            n = lens[i]
            if n > left:
                if skip:
                    continue
                break
            left -= n
            out.append(i)
        return out, left

    def _knap(idxs, left):
        """가치/무게 비 내림차순. 가치는 원래 순위(앞일수록 높다)."""
        N = len(ss)
        order = sorted(idxs, key=lambda i: -((N - i) / max(lens[i], 1)))
        out = []
        for i in order:
            if lens[i] <= left:
                left -= lens[i]
                out.append(i)
        return out, left

    all_idx = list(range(len(ss)))
    if mode == "greedy":
        picked, _ = _greedy(all_idx, allowance, skip=False)
    elif mode == "skip":
        picked, _ = _greedy(all_idx, allowance, skip=True)
    elif mode == "knapsack":
        picked, _ = _knap(all_idx, allowance)
    else:                                    # hybrid (기본)
        head, left = _greedy(all_idx[:topk], allowance, skip=True)
        tail, _ = _knap(all_idx[topk:], left)
        picked = head + tail
    # ★ 원래 순위 순서를 유지해 돌려준다 — 호출부가 reverse 로 뒤집어 상위를 goal 쪽에 둔다
    picked.sort()
    return [ss[i] for i in picked]


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
            # ★ 에러 조건부: 직전 실패 시도와 Coq 에러(있을 때만). 포맷은 항상 고정하지 않는다 —
            #   추론 첫 시도에는 에러가 없으므로, 섹션 자체가 없는 형태도 학습해야 한다.
            att = getattr(example, "attempted_tactic", None)
            err = getattr(example, "coq_error", None)
            if os.environ.get("ERROR_COND", "0") == "1" and att and err:
                e_str, _ = allocate_tokens(tokenizer, str(err),
                                           int(os.environ.get("ERROR_TOKENS", "96")))
                a_str, _ = allocate_tokens(tokenizer, str(att),
                                           int(os.environ.get("ATTEMPT_TOKENS", "64")))
                base_str = base_str + ATTEMPT_SEP + a_str + ERROR_SEP + e_str
            return _maybe_normalize_input(
                base_str + augment_v2_section(tokenizer, example, base_str)
                + NEWLINE_RESPONSE_TEMPLATE, example)
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
        if self.whole_proof:
            target = "".join(example.next_steps)
        else:
            target = example.next_steps[0]

        # ★ ERROR_COND 데이터 주입: 학습 코퍼스에는 에러 필드가 없다(순수 state->tactic).
        #   그대로면 [ATTEMPT]/[ERROR] 는 60,000 step 동안 한 번도 안 채워진다 = 죽은 기능.
        #   실제 Coq 문구 그대로 합성해 붙인다(분기수 오류 / 이름 없음 — 실패의 48%).
        if os.environ.get("ERROR_COND", "0") == "1":
            from tactic_gen.synth_error import make as _synth
            _k = (f"{getattr(example, 'file_name', '')}:"
                  f"{getattr(example, 'proof_idx', '')}:{getattr(example, 'step_idx', '')}")
            _att, _err = _synth(target, getattr(example, "proof_state", "") or "", {}, _k)
            if _att:
                example = copy.copy(example)
                example.attempted_tactic, example.coq_error = _att, _err

        # ① 프롬프트는 **원래 이름**으로 구성한다.
        #    ★ 정규화된 goal 로 정의를 조회하면 인덱스에 없어 [TYPES]/[DEFINITIONS] 가 통째로
        #      사라진다(실측). 반드시 원본으로 섹션을 만든 뒤 마지막에 치환해야 한다.
        input_str = self.collate_input(tokenizer, example)   # ← _LAST_INJECTED 가 채워짐

        # ①-b ★ cut 치환 (how-to-learn.txt §3)
        #   gold tactic 이 쓰는 lemma L 이 검색 결과에 없으면, 모델은 프롬프트에서
        #   읽을 수 없는 이름을 지어내야 한다 — 배울 수 없는 예제다(실측 15.2%).
        #   그럴 때 L 과 같은 명제 L' 을 **cut**(= `assert (P) as H`)으로 세우고
        #   그것을 쓰는 형태로 정답을 바꾼다. 명제는 goal 에서 읽히므로 학습이 가능해진다.
        #
        #   ★ cut 은 여기서 만들지 않는다 — 정확한 명제를 얻으려면 Coq 이 필요한데
        #     학습 머신에는 Coq 이 없다. `scripts/build_cuts.py` 로 미리 만들어 둔
        #     jsonl 을 **조회만** 한다(CUTS_PATH).
        #   ★ 조회 실패 = 그 스텝은 cut 이 없거나 cut 을 만들어도 재검색이 안 되는 경우.
        #     그때는 원래 gold tactic 을 그대로 쓴다(환각을 감수한다 — how-to-learn §3).
        #   ★ 정규화(③)보다 **먼저** 해야 한다. 정규화 후에 바꾸면 cut 명제 안의 이름이
        #     프롬프트의 매핑과 어긋난다.
        #   ★★ 결정은 **여기서** 내린다 — 미리 만들어 둔 것은 "무엇을 assert 할 수
        #     있는가" 라는 재료(계획)뿐이다.
        #     옛 방식은 cut 생성 시점에 검색을 돌려 "어느 gold 가 없는가" 까지 확정하고
        #     조립본을 저장했다. 그러면 **검색 정책이 cut 파일에 박힌다** — 랭커를 바꾸면
        #     (structural → eqx) 전제가 틀린 산출물이 되고, 5시간짜리 재생성이 필요했다.
        #     지금은 완성된 프롬프트를 보고 **실제로 안 보이는 것만** assert 한다.
        #
        #       (1) gold 가 전부 보인다        → gold tactic 그대로
        #       (2) 일부가 안 보인다           → 그것들만 assert 해서 조립
        #       (3) 계획이 없다(hopeless)      → `resolved_example` 이 이미 걸러냈다
        if os.environ.get("CUTS_PATH", ""):
            from tactic_gen import cut_lookup
            _ck = (f"{getattr(example, 'file_name', '')}:"
                   f"{getattr(example, 'proof_idx', '')}:"
                   f"{getattr(example, 'step_idx', '')}")
            _plan = cut_lookup.plan_for(_ck)
            if _plan:
                _miss = [(nm, ty) for nm, ty in (_plan.get("lem") or [])
                         if not re.search(r"(?<![\w'])" + re.escape(nm) + r"(?![\w'])",
                                          input_str)]
                if _miss:
                    try:
                        from tactic_gen.assert_split import transform as _tf
                        _new = _tf(_plan.get("tac", target),
                                   [(nm, f"Lemma {nm} : {ty}.") for nm, ty in _miss],
                                   proof_script=getattr(example, "proof_script", "") or "",
                                   state=getattr(example, "proof_state", "") or "")
                    except Exception:
                        _new = None
                    # 조립이 실패하면 **저장해 둔 전체 조립본**으로 물러선다.
                    #   그것도 없으면 gold 그대로 — 환각을 감수한다(how-to-learn §3).
                    if _new and isinstance(_new, str):
                        target = _new
                    elif _plan.get("cut"):
                        target = _plan["cut"]
            else:
                # 옛 형식(`step` 의 조립본) 호환 — 계획 파일로 완전히 넘어가면 지운다
                _cut = cut_lookup.cut_for(_ck)
                if _cut:
                    target = _cut

        # ② 인용 타깃: 프롬프트에 실제로 주입된 정의만 인용(없는 걸 인용시키면 환각 조장)
        if os.environ.get("CITE_TARGET", "0") == "1":
            from tactic_gen.cite_target import make_cite
            target = make_cite(target, getattr(example, "proof_state", "") or "",
                               dict(_LAST_INJECTED)) + "\n" + target

        # ③ α-이름 정규화: **완성된 프롬프트 전체와 정답에 같은 매핑**을 적용한다.
        #    이러면 goal 의 `val` 과 [TYPES] 의 `Inductive val := ...` 이 함께 `T0` 가 되어
        #    조회 가능성은 유지되면서 **이름 암기만 무력화**된다.
        #    (ablation: clean vs wrong 차이 ±0 → 모델이 안 읽는 이유는 '읽을 필요가 없어서'다)
        if os.environ.get("NORMALIZE_NAMES", "0") == "1":
            from tactic_gen.normalize_names import build_mapping, apply_mapping, should_normalize
            key = (f"{getattr(example, 'file_name', '')}:"
                   f"{getattr(example, 'proof_idx', '')}:{getattr(example, 'step_idx', '')}")
            # ★ 가망 없는 스텝(how-to-learn §3 의 (3))은 **정규화를 끈다.**
            #   정답이 프롬프트에 없는 이름을 쓰는데 정규화까지 하면 `L92` 같은
            #   무의미 토큰을 외우게 된다. 진짜 이름이 그나마 낫다.
            _skip_norm = False
            if os.environ.get("CUTS_PATH", ""):
                from tactic_gen import cut_lookup
                _skip_norm = cut_lookup.is_hopeless(key)
            if _skip_norm:
                pass
            elif should_normalize(key):
                # v7: premises 를 넘겨 [PREMISES] lemma 이름도 정규화 대상에 포함
                #     (NORMALIZE_PREMISES=1 일 때만 실제로 대상이 된다)
                mapping = build_mapping(dict(_LAST_INJECTED), key,
                                        avoid_text=input_str + target,
                                        premises=list(getattr(example, "premises", None) or []),
                                        proof_script=getattr(example, "proof_script", "") or "")
                # ★★ 프롬프트에 **실제로 없는 이름**은 매핑에서 뺀다.
                #   build_mapping 은 `example.premises` 전부를 대상으로 하는데,
                #   프롬프트는 premise_tokens(896) 에서 잘린다. 잘려나간 premise 의
                #   이름이 정답에 있으면, 매핑 후 정답에만 `L92` 가 남아
                #   **프롬프트 어디에도 없는 이름**이 된다 — 정확히 우리가 없애려던 환각이다.
                #   (실측: 300 예제 중 2건. details.md §7 에 미해결로 적혀 있던 것)
                #   매핑을 안 하면 원래 이름이 남고, 그건 최소한 의미 힌트라도 있다.
                if mapping:
                    mapping = {k: v for k, v in mapping.items()
                               if re.search(r"(?<![\w'])" + re.escape(k) + r"(?![\w'])",
                                            input_str)}
                if mapping:
                    input_str = apply_mapping(input_str, mapping)
                    target = apply_mapping(target, mapping)
                # ★ 동명 충돌(증명 중인 정리 이름이 [PREMISES] 에도 있는 경우, 실측 1.3%):
                #   매핑에 넣으면 둘 다 같은 이름이 되어 "증명 대상"과 "주어진 사실"을
                #   구분할 수 없다. 선언부 한 곳만 G# 로 바꿔 분리한다.
                import tactic_gen.normalize_names as _nn
                if _nn.LAST_THM_DECL:
                    used = set(re.findall(r"\bG(\d+)\b", input_str))
                    k = 0
                    while str(k) in used:
                        k += 1
                    # apply_mapping 이 이미 원래 이름을 L# 로 바꿔놨으므로,
                    # **바뀐 이름**을 기준으로 선언부만 다시 G# 로 바꾼다.
                    cur = mapping.get(_nn.LAST_THM_DECL, _nn.LAST_THM_DECL)
                    input_str = _nn.substitute_theorem_decl(input_str, cur, f"G{k}")

        if STRIP_TARGET_NL:
            target = target.lstrip("\n")     # 개행은 프롬프트 쪽 "[TACTIC]\n" 이 이미 갖고 있다
        out_str, _ = allocate_tokens(
            tokenizer, target, self.out_tokens, truncate_front=False
        )
        return input_str + out_str

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
            response_template=MASK_TEMPLATE,
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


# ★ 캐시에 **구워지는** 설정들.  `formatter.example_from_step` 이 만드는 LmExample 에
#   이 값들이 그대로 들어간다(검색 결과·주입 정의·유사 증명). 값이 바뀌면 옛 캐시는
#   **다른 실험의 데이터**다. 그런데 캐시 키는 step_id 뿐이라 그냥 쓰면 조용히 섞인다.
#   → 지문(stamp)을 남기고 다르면 **큰 소리로 멈춘다**(자동 삭제는 하지 않는다 —
#     몇 시간치 워밍을 말없이 버리는 쪽이 더 위험하다. 사람이 판단하게 한다).
#
#   ※ collate 단계에서 적용되는 것(PREMISE_PACK, NORMALIZE_*, CUTS_PATH 등)은
#     캐시에 안 구워지므로 여기 넣지 않는다.
_CACHE_STAMP_KEYS = (
    "RETRIEVAL_MODE", "RETRIEVAL_STAGE1", "RERANK_PREMISES",
    "INJECT_TYPES", "INJECT_DEFS", "TYPES_TOKENS", "DEFS_TOKENS",
    "FUNC_DEFS_PATH", "AUGMENT_V2", "CACHE_MAX_PAGE",
)


def _cache_stamp(formatter) -> str:
    import hashlib
    parts = [f"{k}={os.environ.get(k, '')}" for k in _CACHE_STAMP_KEYS]
    parts.append(f"formatter={type(formatter).__name__}")
    for attr in ("num_premises", "num_proofs"):
        parts.append(f"{attr}={getattr(formatter, attr, None)}")
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:16] + "  " + " ".join(parts)


class ExampleCache:
    def __init__(self, cache_loc: Path):
        self.cache_loc = cache_loc
        os.makedirs(self.cache_loc, exist_ok=True)
        self.num_cached = 0
        self.__stamp_checked = False

    def _check_stamp(self, formatter) -> None:
        """캐시가 **지금 설정으로 만들어진 것**인지 확인한다."""
        if self.__stamp_checked:
            return
        self.__stamp_checked = True
        want = _cache_stamp(formatter)
        loc = self.cache_loc / "CACHE_STAMP.txt"
        if loc.exists():
            have = loc.read_text().strip()
            if have.split()[0] != want.split()[0]:
                raise RuntimeError(
                    "\n★ 예제 캐시가 **다른 설정**으로 만들어졌다 — 그대로 쓰면 조용히 다른 실험이 된다.\n"
                    f"   캐시: {self.cache_loc}\n"
                    f"   저장된 설정: {have}\n"
                    f"   지금  설정: {want}\n"
                    "   설정을 되돌리거나, 의도한 변경이면 캐시를 지우고 다시 시작하라:\n"
                    f"     rm -rf {self.cache_loc}\n")
        else:
            try:
                loc.write_text(want + "\n")
            except Exception:
                pass

    def get(
        self,
        step_id: StepID,
        formatter: LmFormatter,
        data_loc: Path,
        sentence_db: SentenceDB,
    ) -> Optional[LmExample]:
        self._check_stamp(formatter)
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


# 진단 모드에서 건너뛴 '판정 없음' 스텝 수 — 스크립트가 읽어 보고한다.
_UNCOVERED_SKIPS = [0]


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
            response_template=MASK_TEMPLATE,
            tokenizer=tokenizer,
            mlm=False,
        )
        self.example_cache = ExampleCache(cache_loc)
        self.__check_cut_coverage()

    # ── ★ cut 파일 커버리지 자기검사 ────────────────────────────────────────
    #  cut 파일은 인덱스 [START, START+N) 만 훑는 **범위 제한 산출물**이다.
    #  그런데 조회 쪽은 범위 밖 스텝에 조용히 None/False 를 준다:
    #      cut_for(sid)     → None    (cut 치환 안 됨)
    #      is_hopeless(sid) → False   (CUT_DROP_HOPELESS 도 함께 죽음)
    #  오류도 경고도 없다. 실제로 파일럿 규모(60,000) 산출물이 본번(640,000 소비)에
    #  들어간 채 학습이 4시간 넘게 돌았고, step 1,875 이후 cut 이 전혀 작동하지 않았다.
    #
    #  ★ 외부 검증 스크립트로는 부족하다 — 안 돌리면 그만이다.
    #    **데이터셋 자신이** 자기 전제조건을 확인한다. 어느 경로로 학습을 시작하든 걸린다.
    def __check_cut_coverage(self) -> None:
        if not os.environ.get("CUTS_PATH", ""):
            return
        try:
            from tactic_gen import cut_lookup
            start, end = cut_lookup.scanned_range()
        except Exception:
            return
        need = self.shuffled_idx.split_length(self.split)
        if self.max_n_examples is not None:
            need = min(need, self.max_n_examples)
        if end >= need and start <= 0:
            _logger.info(f"[cut] 커버리지 OK — 스캔 [{start:,}, {end:,}) ⊇ 사용 {need:,}")
            return
        msg = (f"\n★ cut 파일 커버리지 부족 — 조용히 기능이 죽는다.\n"
               f"   파일        {os.environ['CUTS_PATH']}\n"
               f"   스캔 범위    [{start:,}, {end:,})\n"
               f"   필요 범위    [0, {need:,})   ({self.split})\n"
               f"   범위 밖 스텝은 cut 치환도 CUT_DROP_HOPELESS 도 작동하지 않는다.\n"
               f"   메우려면:  python3 scripts/build_cuts.py {max(need-end,0)+20000} "
               f"{self.split.name.lower()} <out> {end}\n"
               f"   (의도한 부분 실행이면 CUTS_ALLOW_PARTIAL=1)\n")
        if os.environ.get("CUTS_ALLOW_PARTIAL", "0") == "1":
            _logger.warning(msg)
            print(msg, flush=True)
            return
        raise RuntimeError(msg)

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

    _cut_range = None          # (start, end) — 첫 호출에 채운다

    def _hopeless(self, example) -> bool:
        """이 스텝이 '가망 없음'(how-to-learn §3 의 ③)인가.

        gold lemma 가 후보 풀에도 없고 cut 도 못 세운 스텝이다. 정답이 **프롬프트에
        없는 이름**을 쓰므로, 이걸로 학습하면 모델에게 *볼 수 없는 이름을 지어내라*고
        가르치는 셈이다. `CUT_DROP_HOPELESS=1` 이면 학습에서 제외한다.
        """
        if not os.environ.get("CUTS_PATH", ""):
            return False
        from tactic_gen import cut_lookup
        return cut_lookup.is_hopeless(
            f"{getattr(example, 'file_name', '')}:"
            f"{getattr(example, 'proof_idx', '')}:{getattr(example, 'step_idx', '')}")

    def _uncovered(self, index: int) -> bool:
        """이 인덱스가 cut **판정을 못 받은** 구간인가.

        ★ 왜 이게 필요한가 (설계의 핵심):
          cut 파일에 그 스텝이 없다는 것은 두 가지 중 하나다.
            ⓐ 훑어봤고 cut 이 필요 없었다        → 그냥 쓰면 된다
            ⓑ 아예 안 훑었다(생성 범위 밖)        → **알 수 없다**
          그런데 `cut_for()` 도 `is_hopeless()` 도 둘을 구분 못 하고 똑같이
          "해당 없음" 을 돌려준다. 그러면 ⓑ 가 ⓐ 로 둔갑해서, gold 가 프롬프트에
          없는 스텝이 cut 없이 그대로 학습에 들어간다 = **환각을 가르친다.**
          이것이 커버리지 사고의 진짜 원인이었다. 범위 검사는 그 증상을 잡아낸
          **탐지기**였을 뿐이다.

          그래서 여기서 ⓑ 를 **인덱스 단위로** 가른다. 그리고 ⓑ 는 **건너뛰지 않고
          죽인다.** cut 은 전 구간을 만들도록 되어 있으므로, 없다는 것은 정상 상태가
          아니라 **생성이 덜 끝났다는 버그**다. 조용히 건너뛰면 "90%만 학습하고 성공
          보고" 가 되는데, 그게 우리가 계속 당한 실패 모드다.

          (hopeless 는 다르다 — 그건 원리적으로 고칠 수 없는 스텝이라 **의도적으로**
           건너뛰는 것이고 비율도 측정돼 있다(6.7%). 둘을 같이 취급하면 안 된다.)

          `CUTS_ALLOW_PARTIAL=1` 일 때만 건너뛴다 — 생성 중에 돌리는 진단 스크립트용이다.
        """
        if self._cut_range is None:
            if not os.environ.get("CUTS_PATH", ""):
                self._cut_range = (0, 1 << 62)          # cut 미사용 — 전부 커버로 본다
            else:
                from tactic_gen import cut_lookup
                self._cut_range = cut_lookup.scanned_range()
        a, b = self._cut_range
        return not (a <= index < b)

    def resolved_example(self, index: int):
        """학습이 **실제로 쓰는** 예제. 가망 없거나 판정을 못 받은 스텝은 다음으로 치환한다.

        ★ 가망 없는 스텝으로 학습하면 *볼 수 없는 이름을 지어내라*고 가르치는 셈이다.
          길이(`__len__`)를 바꾸면 스케줄러·재개가 어긋나므로 **인덱스를 치환**한다.
          실측 제외율 6.7% 라 같은 예제를 두 번 보는 일은 드물다.

        사전점검 스크립트도 이걸 써야 학습과 같은 예제를 본다.
        """
        example = self.raw_example(index)
        if os.environ.get("CUT_DROP_HOPELESS", "0") != "1":
            return example
        n = len(self)
        _partial = os.environ.get("CUTS_ALLOW_PARTIAL", "0") == "1"
        for _ in range(64):
            if self._uncovered(index):
                # ★ 건너뛰지 않는다 — 생성이 덜 끝났다는 뜻이므로 **죽인다**.
                if not _partial:
                    a, b = self._cut_range
                    raise RuntimeError(
                        f"cut 판정이 없는 인덱스 {index:,} 로 학습하려 한다.\n"
                        f"   cut 파일이 훑은 연속 범위 [{a:,}, {b:,}) · "
                        f"필요 [0, {n:,})\n"
                        f"   cut 은 전 구간을 만들도록 되어 있다 — 없다는 것은 "
                        f"**생성이 덜 끝났다**는 뜻이다.\n"
                        f"   메우려면: bash scripts/gen_cuts_all.sh "
                        f"{self.split.name.lower()} && "
                        f"bash scripts/merge_cuts.sh {self.split.name.lower()}\n"
                        f"   (생성 중 진단이면 CUTS_ALLOW_PARTIAL=1)")
                _UNCOVERED_SKIPS[0] += 1
            elif not self._hopeless(example):
                return example
            index = (index + 1) % n
            try:
                example = self.raw_example(index)
            except Exception:
                return example
        return example

    def __getitem__(self, index: int) -> Any:
        example = self.resolved_example(index)
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
