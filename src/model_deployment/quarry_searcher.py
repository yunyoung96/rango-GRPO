"""Quarry (Planning to Hammer, arXiv:2606.17981) — FULL 구현.

프레임워크 = Planning(LLM 분해) + Execution(CoqHammer) + 난이도 모델 랭킹.
Algorithm 1 (SolveGoal) 재귀:
  1) Phase1 fast-path: CoqHammer(sauto/hauto/…)로 goal 직접 시도.
  2) 실패 & budget>0: LLM이 goal을 k개 후보로 분해([LEMMA]/[TARGET] 블록).
  3) 각 후보 검증 + 난이도 모델로 랭킹, 상위 B개에 대해:
       각 서브레마 ℓ를 `assert (ℓ) as H.`로 서브골 생성 → 재귀 SolveGoal로 실제 증명,
       모든 서브레마 풀리면 target 증명 p(c) 적용 → goal 닫힘 확인.

★환경 대체(불가피):
  · admit 기반 type-check 불가(check_proof가 "admit." 문자열 차단) → assert 서브골을
    **재귀로 실제 증명**해 스플라이스(admit 없이 동등 검증).
  · 외부 ATP 없음 → CoqHammer = sauto/hauto/eauto/lia/congruence 조합(우리 환경 최대치).
  · 논문 모델(대형)은 rango 1.3B로 대체. 알고리즘은 논문 그대로, rango 탐색과 안 섞음.
  · OCaml/opam 버전 불변.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from coqpyt.coq.lsp.structs import Goal
from data_management.dataset_file import Proof
from model_deployment.proof_manager import ProofManager, TacticResult
from model_deployment.tactic_gen_client import TacticGenClient
from model_deployment.straight_line_searcher import (
    StraightLineSuccess,
    StraightLineFailure,
)
from model_deployment.quarry_features import featurize_statement
from model_deployment.quarry_difficulty import DifficultyModel

# CoqHammer fast-path 후보(순서=시도 우선순위). 외부 ATP 없어 sauto/hauto 중심.
HAMMER_TACTICS = ["sauto", "hauto", "eauto", "congruence", "lia", "easy", "auto"]


@dataclass
class QuarrySearchConf:
    timeout: int
    k: int = 8                      # 후보 분해 수
    branch: int = 1                 # B: 상위 몇 후보를 실제 추적
    max_depth: int = 5              # 재귀 최대 깊이
    hammer_timeout: int = 30        # goal당 hammer 제한(초) — 우리는 check_proof 자체 타임아웃 사용
    max_llm_calls: int = 60         # theorem당 LLM 분해 호출 상한
    difficulty_ckpt: Optional[str] = None  # 학습된 θ 경로(없으면 heuristic)
    print_proofs: bool = True
    initial_proof: Optional[str] = None
    trace_out: Optional[str] = None  # Algorithm 2용 trace 저장 경로(jsonl)
    ALIAS = "quarry"

    @classmethod
    def from_yaml(cls, yaml_data: Any) -> "QuarrySearchConf":
        return cls(
            yaml_data["timeout"],
            yaml_data.get("k", 8),
            yaml_data.get("branch", 1),
            yaml_data.get("max_depth", 5),
            yaml_data.get("hammer_timeout", 30),
            yaml_data.get("max_llm_calls", 60),
            yaml_data.get("difficulty_ckpt", None),
            yaml_data.get("print_proofs", True),
            yaml_data.get("initial_proof", None),
            yaml_data.get("trace_out", None),
        )


@dataclass
class Candidate:
    lemmas: list[str]                    # 서브레마 문장들 ℓ₁..ℓₘ
    target: str                          # p(c): 서브레마 가정하 goal 닫는 tactic script
    raw: str = ""


# ── 분해 출력 파서: [LEMMA]..[END] 블록들 + [TARGET]..[END] ──────────────
_LEMMA_RE = re.compile(r"\[LEMMA\](.*?)\[END\]", re.DOTALL)
_TARGET_RE = re.compile(r"\[TARGET\](.*?)\[END\]", re.DOTALL)


def parse_decomposition(text: str) -> Optional[Candidate]:
    lemmas = [m.group(1).strip() for m in _LEMMA_RE.finditer(text)]
    tgt = _TARGET_RE.search(text)
    if not lemmas or tgt is None:
        return None
    lemmas = [_clean_stmt(l) for l in lemmas if _clean_stmt(l)]
    target = tgt.group(1).strip()
    if not lemmas or not target:
        return None
    return Candidate(lemmas=lemmas, target=target, raw=text[:400])


def _clean_stmt(s: str) -> str:
    s = s.strip()
    # 앞의 "Lemma foo :" 같은 머리 제거, 뒤 마침표 정리
    s = re.sub(r"^\s*(Lemma|Theorem|forall_lemma)\b[^:]*:", "", s).strip()
    s = s.rstrip(".").strip()
    return s


# ── few-shot 분해 프롬프트(논문 artifact 비공개 → 직접 설계) ──────────────
FEWSHOT = """You are decomposing a Coq proof goal into helper sublemmas.
Output helper lemmas as [LEMMA]<statement>[END] blocks, then one [TARGET]<tactics>[END]
block giving a short tactic script that closes the goal assuming the helper lemmas
(named H1, H2, ... in order).

Example.
Goal:
  forall n : nat, n + 0 = n
Decomposition:
[LEMMA]forall m : nat, m + 0 = m[END]
[TARGET]intro n. apply H1.[END]

Now decompose this goal.
Goal:
{goal}
Decomposition:
"""


class QuarrySearcher:
    def __init__(
        self,
        tactic_clients: list[TacticGenClient],
        proof_manager: ProofManager,
        conf: QuarrySearchConf,
    ):
        self.clients = tactic_clients
        self.pm = proof_manager
        self.conf = conf
        self.timeout = conf.timeout
        self.difficulty = DifficultyModel.load(
            Path(conf.difficulty_ckpt) if conf.difficulty_ckpt else None
        )
        self.total_model_time = 0.0
        self.n_llm_calls = 0
        self.hyp_counter = 0
        self.traces: list[dict] = []

        init_dset = proof_manager.get_initial_context()
        if init_dset is None:
            raise ValueError("Could not get initial datasetfile")
        self.theorem = init_dset.proofs[-1].theorem
        init = proof_manager.check_proof(conf.initial_proof or "", self.theorem)
        assert init.tactic_result == TacticResult.VALID and init.current_goals is not None
        self.init_check = init

    @classmethod
    def from_conf(cls, conf: QuarrySearchConf, tactic_clients, proof_manager):
        return cls(tactic_clients, proof_manager, conf)

    def _client(self):
        return self.clients[self.n_llm_calls % len(self.clients)]

    def _fresh_hyp(self) -> str:
        self.hyp_counter += 1
        return f"HQ{self.hyp_counter}"

    def _goals_text(self, goals: list[Goal]) -> str:
        parts = []
        for g in goals[:1]:  # 프롬프트엔 focus goal 위주
            for h in g.hyps:
                names = ", ".join(h.names)
                parts.append(f"  {names} : {h.ty}")
            parts.append(f"  ⊢ {g.ty}")
        return "\n".join(parts)

    # ── goal 종료 판정: script 적용 후 focus goal이 닫혔는가 ──
    def _closes(self, script: str, n_before: int) -> tuple[bool, Optional[Any]]:
        res = self.pm.check_proof(script, self.theorem)
        if res.tactic_result == TacticResult.COMPLETE:
            return True, res
        if res.tactic_result == TacticResult.VALID and res.current_goals is not None:
            if len(res.current_goals) < n_before:  # focus goal 하나 닫힘
                return True, res
        return False, res

    # ── Phase1: CoqHammer fast-path ──
    def _try_hammer(self, prefix: str, n_before: int, start: float) -> Optional[str]:
        for tac in HAMMER_TACTICS:
            if time.time() - start >= self.timeout:
                return None
            script = f"{prefix} {tac}."
            ok, _ = self._closes(script, n_before)
            if self.conf.print_proofs:
                print(f"  [Quarry] hammer {tac} → {'OK' if ok else 'x'}")
            if ok:
                return f"{tac}."
        return None

    # ── Phase2: LLM 분해 생성 ──
    def _decompose(self, goals: list[Goal]) -> list[Candidate]:
        if self.n_llm_calls >= self.conf.max_llm_calls:
            return []
        prompt = FEWSHOT.format(goal=self._goals_text(goals))
        t0 = time.time()
        outs = self._client().generate_raw(
            prompt, n=self.conf.k, max_new_tokens=256, temperature=1.0
        )
        self.total_model_time += time.time() - t0
        self.n_llm_calls += 1
        cands: list[Candidate] = []
        seen = set()
        for o in outs:
            c = parse_decomposition(o)
            if c is None:
                continue
            key = (tuple(c.lemmas), c.target)
            if key in seen:
                continue
            seen.add(key)
            cands.append(c)
        return cands

    # ── 난이도 랭킹: 후보의 최대 서브레마 난이도 오름차순(쉬운 것 먼저) ──
    def _rank(self, cands: list[Candidate]) -> list[Candidate]:
        def cand_diff(c: Candidate) -> float:
            return max(self.difficulty.difficulty(featurize_statement(l)) for l in c.lemmas)
        return sorted(cands, key=cand_diff)

    # ── Algorithm 1: SolveGoal(prefix, goals, depth) → 닫는 script or None ──
    def _solve(self, prefix: str, goals: list[Goal], depth: int, start: float) -> Optional[str]:
        n_before = len(goals)
        if time.time() - start >= self.timeout:
            return None
        # Phase1 fast-path
        ham = self._try_hammer(prefix, n_before, start)
        if ham is not None:
            self._record(goals, depth, "hammer", True)
            return ham
        if depth >= self.conf.max_depth:
            self._record(goals, depth, "depth-cut", False)
            return None
        # Phase2 분해
        cands = self._decompose(goals)
        if not cands:
            self._record(goals, depth, "no-cands", False)
            return None
        ranked = self._rank(cands)
        # Phase3: 상위 B개 추적
        for c in ranked[: self.conf.branch]:
            if time.time() - start >= self.timeout:
                return None
            assembled = ""
            names: list[str] = []
            ok = True
            for lemma in c.lemmas:
                hyp = self._fresh_hyp()
                names.append(hyp)
                step = f"{assembled} assert ({lemma}) as {hyp}."
                probe = f"{prefix}{step}"
                res = self.pm.check_proof(probe, self.theorem)
                if res.tactic_result != TacticResult.VALID or res.current_goals is None:
                    ok = False
                    break  # 서브레마 문장이 ill-formed
                # assert가 만든 서브골 = res.current_goals[0]. 재귀로 실제 증명.
                sub = self._solve(probe, res.current_goals, depth + 1, start)
                if sub is None:
                    ok = False
                    break
                assembled = f"{step} {sub}"
            if not ok:
                self._record(goals, depth, "sublemma-fail", False)
                continue
            # 모든 서브레마 풀림 → target 증명 p(c) 적용
            tgt = _rename_hyps(c.target, names)
            full = f"{prefix}{assembled} {tgt}"
            closed, _ = self._closes(full, n_before)
            if self.conf.print_proofs:
                print(f"  [Quarry] depth={depth} target apply → {'CLOSE' if closed else 'x'}")
            if closed:
                self._record(goals, depth, "decompose", True)
                return f"{assembled} {tgt}"
        self._record(goals, depth, "exhausted", False)
        return None

    def _record(self, goals: list[Goal], depth: int, kind: str, success: bool):
        if self.conf.trace_out and goals:
            g = goals[0]
            self.traces.append({
                "depth": depth, "kind": kind, "success": success,
                "goal": g.ty, "num_hyps": len(g.hyps),
                "stmt": g.ty,
            })

    def search(self, **kwargs) -> StraightLineSuccess | StraightLineFailure:
        start = time.time()
        goals = self.init_check.current_goals
        assert goals is not None
        script = self._solve(self.conf.initial_proof or "", goals, 0, start)
        elapsed = time.time() - start
        if self.conf.trace_out and self.traces:
            self._flush_traces()
        if script is not None:
            final = f"{self.conf.initial_proof or ''}{script}"
            res = self.pm.check_proof(final, self.theorem)
            if res.tactic_result == TacticResult.COMPLETE and res.new_proof is not None:
                if self.conf.print_proofs:
                    print(f"[Quarry] 성공 (LLM {self.n_llm_calls}회, {elapsed:.1f}s)")
                return StraightLineSuccess(elapsed, self.total_model_time, res.new_proof, [])
        return StraightLineFailure(elapsed, self.total_model_time, [])

    def _flush_traces(self):
        import json
        p = Path(self.conf.trace_out)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a") as f:
            for t in self.traces:
                f.write(json.dumps(t, ensure_ascii=False) + "\n")


def _rename_hyps(target: str, names: list[str]) -> str:
    """target 스크립트의 H1,H2.. 참조를 실제 생성된 hyp 이름으로 치환."""
    out = target
    for i, nm in enumerate(names, 1):
        out = re.sub(rf"\bH{i}\b", nm, out)
    return out
