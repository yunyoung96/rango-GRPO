"""Planner–Executor (PLANNER_EXECUTOR_DESIGN.md): 강한 로컬 LLM을 'planner'로 써서
현재 Coq goal의 **고수준 분해**(어느 변수 induction / 어느 hyp destruct / 어느 lemma apply)를
제안한다. executor(우리 1.3B + coq-lsp)가 이 후보들을 실제로 적용·검증한다.

핵심 설계:
  · planner는 **Coq 전용 prover가 아니어도 됨** — 범용 코드/추론 모델(Qwen2.5-Coder-32B 등)에
    few-shot 프롬프트로 '분해 전략'만 시킨다. 정확한 구문/인자는 coq-lsp 검증이 걸러낸다.
  · 출력 = 곧바로 searcher에 강제 후보로 넣을 **tactic 문자열 리스트**('\ninduction n.' 등).
  · **학습 안 함**(추론만) → covariate-shift/capacity 벽 회피(분해를 executor에서 뺌).
  · goal 문자열 캐시로 같은 state 재질의 방지.

bitsandbytes 4bit 로드(우리 기존 transformers 스택; vLLM/awq 불요).
"""
from __future__ import annotations
import json
import re
from dataclasses import dataclass, field
from typing import Any, Optional


# ── few-shot: CompCert류 Coq 분해 전략(고수준). 정확 구문은 executor/coq-lsp가 책임. ──
_SYSTEM = (
    "You are a Coq proof strategist. Given the current proof GOAL (hypotheses above the "
    "line, conclusion below), propose a SHORT ordered list of high-level structural moves "
    "that decompose the goal. Prefer: induction on a recursive variable (nat/list/...), "
    "destruct on a hypothesis (conjunction/disjunction/inductive), inversion on an equality/"
    "constructor hypothesis, or apply/rewrite with a relevant lemma. "
    "Reply ONLY with a JSON array of Coq tactics, most-promising first, e.g. "
    '["induction n.", "destruct l.", "apply Nat.add_comm."]. No prose.'
)

# 학습된 opener 프롬프트 (train_opener_sft.py의 SYSTEM과 동일해야 함)
_OPENER_SYSTEM = (
    "You are a Coq proof strategist. Given the current GOAL, output ONLY a JSON array "
    "of the opening Coq tactics that decompose it (induction/destruct/inversion on the "
    "right target), most-promising first. No prose."
)
# 선택형 opener 프롬프트 (train_opener_sel.py의 SYSTEM과 동일해야 함)
_OPENER_SEL_SYSTEM = (
    "You are a Coq proof strategist. Given the GOAL and enumerated CANDIDATE decompositions, "
    "output ONLY a JSON array with the best opening Coq tactic(s). Pick a candidate if one fits, "
    "otherwise write your own. No prose."
)
# tactic-단위 opener 프롬프트 (train_opener_tac.py의 SYSTEM과 동일해야 함)
_OPENER_TAC_SYSTEM = (
    "You are a Coq proof strategist. Given the GOAL, enumerated CANDIDATE decompositions, "
    "and retrieved RELEVANT LEMMAS/PROOFS, output the SINGLE next opening tactic that decomposes "
    "the goal (induction/destruct/inversion on the right target, with the right argument — use a "
    "candidate or a retrieved lemma when it fits). If the goal is already sufficiently decomposed "
    'and needs no further structural step, output exactly "No More Decomposition". No prose.'
)
_NMD = "No More Decomposition"


def _build_tac_input(goal_str, premises, proofs, n_prem=30, n_proof=4):
    """train_opener_tac.py build_input 과 동일 포맷(입력 조립)."""
    from tactic_gen.grpo_rollout import _targeted_cands
    cands = [c.strip() for c in _targeted_cands([goal_str])]
    lines = [f"GOAL:\n{(goal_str or '').strip()}", ""]
    ct = "\n".join(f"- {c}" for c in cands) if cands else "(none)"
    lines.append(f"CANDIDATE DECOMPOSITIONS:\n{ct}"); lines.append("")
    prem = [p.split('\n')[0][:140] for p in (premises or [])[:n_prem]]
    lines.append("RELEVANT LEMMAS:\n" + ("\n".join(f"- {p}" for p in prem) if prem else "(none)"))
    lines.append("")
    prf = []
    for p in (proofs or [])[:n_proof]:
        head = p.split('\n'); nm = head[0][:100]; body = " ".join(x.strip() for x in head[1:4])[:120]
        prf.append(f"- {nm} | {body}")
    lines.append("RELEVANT PROOFS:\n" + ("\n".join(prf) if prf else "(none)"))
    return "\n".join(lines)

_FEWSHOT = [
    (
        "n : nat\nl : list nat\n============================\nlength (rev l) = length l",
        '["induction l.", "simpl.", "rewrite app_length.", "rewrite IHl."]',
    ),
    (
        "H : A /\\ B\n============================\nB /\\ A",
        '["destruct H.", "split.", "assumption."]',
    ),
    (
        "n m : nat\nH : S n = S m\n============================\nn = m",
        '["inversion H.", "reflexivity."]',
    ),
]


@dataclass
class PlannerConf:
    # Qwen2.5-Coder-7B(bf16 ~15GB)이 기본 — 32B는 transformers 5.1의 bnb 4bit 로더 버그(양자화 전
    # full bf16을 GPU에 올려 48GB OOM)로 로드 불가. 7B bf16은 bnb 경로를 안 타 안전 + 6.7B보다 강함.
    model_name: str = "Qwen/Qwen2.5-Coder-7B-Instruct"
    load_4bit: bool = False
    init_adapter: Optional[str] = None   # LoRA 어댑터(예: 학습된 opener) 경로. 있으면 base 위에 얹음.
    opener_mode: bool = False   # 학습된 opener면 True — 학습 프롬프트(few-shot 없이) 사용
    select_mode: bool = False   # 선택형 opener: 입력에 _targeted_cands 열거후보 포함(학습과 동일)
    tac_mode: bool = False      # tactic-단위 opener(신규): 입력=goal+후보+lemma/proof retrieval, 출력=다음 tactic 1개 or "No More Decomposition"
    device: str = "cuda:0"     # CVD 리매핑 하에서 GPU1이 cuda:0
    max_new_tokens: int = 160
    temperature: float = 0.3
    n_moves: int = 6           # 채택할 최대 후보 수
    # ★ persistent 서버 모드: 설정 시 in-process 로드 대신 planner_server(HTTP)에 질의.
    #   run_all이 정리별 subprocess라 in-process면 정리마다 재로드 → 서버로 한 번만 로드/공유(+w2 가능).
    server_url: Optional[str] = None
    ALIAS = "planner"

    @classmethod
    def from_yaml(cls, y: Any) -> "PlannerConf":
        return cls(
            y.get("model_name", "Qwen/Qwen2.5-Coder-7B-Instruct"),
            y.get("load_4bit", False),
            y.get("device", "cuda:0"),
            y.get("max_new_tokens", 160),
            y.get("temperature", 0.3),
            y.get("n_moves", 6),
            y.get("server_url", None),
        )


class PlannerClient:
    """로컬 LLM planner. plan(goal_str) -> list[Coq tactic str] (searcher 강제 후보용)."""

    def __init__(self, conf: PlannerConf):
        self.conf = conf
        self._model = None
        self._tok = None
        self._cache: dict[str, list[str]] = {}

    # 지연 로드: import 시 무거운 모델 안 올림.
    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        # local_files_only: 캐시된 모델만 사용(미인증 HF fetch hang 방지 — 스모크서 'Fetching 2 files 0%' 멈춤).
        self._tok = AutoTokenizer.from_pretrained(self.conf.model_name, local_files_only=True)
        if "awq" in self.conf.model_name.lower():
            # ★ AWQ(사전 4bit): transformers 5.1의 quantizer_awq는 gptqmodel(=transformers 5.14 업그레이드 유발,
            #   파이프라인 위험)을 요구 → 대신 autoawq 자체 로더 사용(transformers 안 건드림). ~19GB 안착(32B OK).
            from awq import AutoAWQForCausalLM
            self._model = AutoAWQForCausalLM.from_quantized(
                self.conf.model_name, fuse_layers=False,
                device_map={"": self.conf.device}, local_files_only=True,
            )
            return
        kwargs: dict[str, Any] = {"local_files_only": True, "low_cpu_mem_usage": True}
        if self.conf.load_4bit:
            # ★ 4bit 경로: top-level dtype 금지(주면 4bit 무력화). compute dtype은 BnB가 담당.
            #   device_map="auto"로 샤드 스트리밍 양자화(={"":dev}는 bf16 샤드를 한꺼번에 올려 47GB OOM).
            #   CUDA_VISIBLE_DEVICES로 GPU 고정하므로 auto가 그 GPU만 씀.
            kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_use_double_quant=True,
            )
            kwargs["device_map"] = "auto"
        else:
            kwargs["dtype"] = torch.bfloat16
            kwargs["device_map"] = {"": self.conf.device}
        self._model = AutoModelForCausalLM.from_pretrained(self.conf.model_name, **kwargs)
        if self.conf.init_adapter:   # 학습된 opener LoRA 얹기
            from peft import PeftModel
            self._model = PeftModel.from_pretrained(self._model, self.conf.init_adapter)
        self._model.eval()

    def _build_messages(self, goal_str: str, premises=None, proofs=None) -> list[dict]:
        if self.conf.tac_mode:
            # tactic-단위 opener: goal+후보+lemma/proof retrieval (train_opener_tac.py와 동일).
            return [{"role": "system", "content": _OPENER_TAC_SYSTEM},
                    {"role": "user", "content": _build_tac_input(goal_str, premises, proofs)}]
        if self.conf.select_mode:
            # 선택형 opener: 열거후보를 입력에 포함(train_opener_sel.py와 동일).
            from tactic_gen.grpo_rollout import _targeted_cands
            cands = [c.strip() for c in _targeted_cands([goal_str])]
            ct = "\n".join(f"- {c}" for c in cands) if cands else "(none)"
            return [{"role": "system", "content": _OPENER_SEL_SYSTEM},
                    {"role": "user", "content": f"GOAL:\n{goal_str}\n\nCANDIDATES:\n{ct}"}]
        if self.conf.opener_mode:
            # 학습된 opener: 학습 때와 동일 프롬프트(few-shot 없이).
            return [{"role": "system", "content": _OPENER_SYSTEM},
                    {"role": "user", "content": f"GOAL:\n{goal_str}"}]
        msgs = [{"role": "system", "content": _SYSTEM}]
        for g, a in _FEWSHOT:
            msgs.append({"role": "user", "content": f"GOAL:\n{g}"})
            msgs.append({"role": "assistant", "content": a})
        msgs.append({"role": "user", "content": f"GOAL:\n{goal_str}"})
        return msgs

    @staticmethod
    def _parse_moves(text: str) -> list[str]:
        """모델 출력에서 tactic 리스트 파싱: JSON 배열 우선, 실패 시 줄 단위 fallback."""
        m = re.search(r"\[.*?\]", text, re.DOTALL)
        if m:
            try:
                arr = json.loads(m.group(0))
                out = [str(t).strip() for t in arr if str(t).strip()]
                if out:
                    return out
            except Exception:
                pass
        # fallback: 각 줄에서 '.'로 끝나는 tactic처럼 보이는 것 (번호/불릿 접두 제거)
        out = []
        for ln in text.splitlines():
            ln = ln.strip().strip('",')
            ln = re.sub(r"^(\d+[.)]|[-*•])\s*", "", ln).strip()  # "1. ", "- ", "* " 등 제거
            if ln.endswith(".") and 2 < len(ln) < 80 and not ln.startswith(("#", "//")):
                out.append(ln)
        return out

    def plan(self, goal_str: str, premises=None, proofs=None) -> list[str]:
        """현재 goal에 대한 고수준 분해 tactic 후보. searcher가 그대로 'script + tactic'으로 적용.
        각 tactic 앞에 '\\n'을 붙여 우리 검색 프레임 규약(_targeted_cands와 동일)에 맞춘다.
        tac_mode면 premises/proofs(retrieval)도 입력에 포함하고, 출력이 NMD면 ["__NMD__"] 반환.
        server_url 설정 시 planner_server(HTTP)에 질의, 아니면 in-process 생성."""
        if not goal_str:
            return []
        if goal_str in self._cache:
            return self._cache[goal_str]
        if self.conf.server_url:
            moves = self._plan_http(goal_str, premises, proofs)
        else:
            moves = self._plan_local(goal_str, premises, proofs)
        # tac_mode: NMD 감지 → 정지 신호 sentinel (개행 붙이지 않음)
        if self.conf.tac_mode and any(_NMD.lower() in m.lower() for m in moves):
            self._cache[goal_str] = ["__NMD__"]
            return ["__NMD__"]
        moves = moves[: self.conf.n_moves]
        # 검색 프레임 규약: 각 tactic은 개행으로 시작(우리 _targeted_cands / recs와 동일 포맷)
        tactics = [("\n" + t if not t.startswith("\n") else t) for t in moves]
        self._cache[goal_str] = tactics
        return tactics

    def _plan_local(self, goal_str: str, premises=None, proofs=None) -> list[str]:
        self._ensure_loaded()
        import torch
        prompt = self._tok.apply_chat_template(
            self._build_messages(goal_str, premises, proofs), tokenize=False, add_generation_prompt=True
        )
        inputs = self._tok(prompt, return_tensors="pt").to(self.conf.device)
        with torch.no_grad():
            out = self._model.generate(
                **inputs, max_new_tokens=self.conf.max_new_tokens,
                do_sample=self.conf.temperature > 0, temperature=max(self.conf.temperature, 1e-3),
                pad_token_id=self._tok.eos_token_id,
            )
        text = self._tok.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        return self._parse_moves(text)

    def _plan_http(self, goal_str: str, premises=None, proofs=None) -> list[str]:
        """persistent planner_server에 POST. 실패 시 빈 리스트(탐색은 정책 후보로 계속).
        tac_mode면 premises/proofs(retrieval)도 함께 보낸다."""
        import urllib.request
        try:
            body = {"goal": goal_str}
            if premises is not None:
                body["premises"] = premises
            if proofs is not None:
                body["proofs"] = proofs
            data = json.dumps(body).encode()
            req = urllib.request.Request(
                self.conf.server_url.rstrip("/") + "/plan", data=data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=60) as r:
                return list(json.loads(r.read().decode()).get("plan", []))
        except Exception:
            return []

    @classmethod
    def from_conf(cls, conf: PlannerConf) -> "PlannerClient":
        return cls(conf)
