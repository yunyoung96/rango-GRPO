from __future__ import annotations
from typing import Any, Optional
from pathlib import Path
from dataclasses import dataclass
import os
import functools
import re

_ID_FORM = re.compile(r"[^\[\]\{\}\(\):=,\s]+")

_LEMMA_NAME = re.compile(
    r"^\s*(?:Lemma|Theorem|Remark|Corollary|Definition|Fixpoint|Instance|Fact|Property|Proposition|Global\s+Instance)\s+([A-Za-z_][\w']*)"
)


def _lemma_name(text: str) -> Optional[str]:
    """premise 텍스트('Lemma load_rule: ...')에서 lemma 이름 추출."""
    m = _LEMMA_NAME.match(text.strip())
    return m.group(1) if m else None


import subprocess as _sp
import tempfile as _tf

_SEARCH_REQUIRES = "From Coq Require Import Bool Arith ZArith List Lia.\n"
_SEARCH_RESULT = re.compile(r"^([A-Za-z_][\w'.]*):")
_search_cache: dict[str, list[str]] = {}


def coq_search(idents: list[str], max_results: int = 6) -> list[str]:
    """Coq `Search`로 stdlib built-in lemma를 찾는다(BM25가 못 찾는 것).
    goal 식별자들을 Search에 넣어 매칭 lemma 이름을 반환. subprocess coqc."""
    idents = [i for i in idents if re.fullmatch(r"[A-Za-z_][\w'.]*", i) and len(i) > 1]
    if not idents:
        return []
    key = " ".join(sorted(set(idents))[:4])
    if key in _search_cache:
        return _search_cache[key]
    query = "Search " + " ".join(sorted(set(idents))[:4]) + "."
    src = _SEARCH_REQUIRES + query + "\n"
    found: list[str] = []
    try:
        with _tf.NamedTemporaryFile("w", suffix=".v", delete=False) as f:
            f.write(src)
            path = f.name
        out = _sp.run(["coqc", path], capture_output=True, text=True, timeout=40).stdout
        for line in out.splitlines():
            m = _SEARCH_RESULT.match(line.strip())
            if m and m.group(1) not in found:
                found.append(m.group(1))
            if len(found) >= max_results:
                break
    except Exception:
        found = []
    finally:
        try:
            os.remove(path)
        except Exception:
            pass
    _search_cache[key] = found
    return found


from data_management.line_dict import LineDict
from data_management.splits import FileInfo
from data_management.dataset_file import (
    DatasetFile,
    Proof,
    Sentence,
    Goal,
)
from premise_selection.rerank_client import (
    PremiseClient,
    PremiseConf,
    premise_conf_from_yaml,
    premise_client_from_conf,
    premise_conf_update_ips,
    close_premise_client,
)

from proof_retrieval.proof_retriever import (
    ProofRetriever,
    ProofRetrieverConf,
    proof_conf_update_ips,
    proof_retriever_conf_from_yaml,
    proof_retriever_from_conf,
    close_proof_retriever,
)

from util.util import get_basic_logger


GOAL_SEP = "\n[GOAL]\n"


def get_repos_path(file_path: str) -> Path:
    repos_path = Path("")
    hit_repos = False
    for p in Path(file_path).parts:
        if p == "repos":
            hit_repos = True
        if hit_repos:
            repos_path = repos_path / p
    return repos_path


class LmExample:
    def __init__(
        self,
        proof_script: str,
        proof_state: str,
        next_steps: list[str],
        proofs: Optional[list[str]] = None,
        premises: Optional[list[str]] = None,
        file_name: Optional[str] = None,
        proof_idx: Optional[int] = None,
        step_idx: Optional[int] = None,
    ) -> None:
        self.proof_script = proof_script
        self.proof_state = proof_state
        self.next_steps = next_steps
        self.proofs = proofs
        self.premises = premises
        self.file_name = file_name
        self.proof_idx = proof_idx
        self.step_idx = step_idx

    def __hash__(self) -> int:
        next_step_str = "<NEXT_SEP>".join(self.next_steps)
        proof_str = "<PROOF_SEP>".join(self.proofs) if self.proofs is not None else ""
        prem_str = "<PREM_SEP>".join(self.premises) if self.premises is not None else ""
        return hash(
            (
                self.proof_script,
                self.proof_state,
                next_step_str,
                proof_str,
                prem_str,
                self.file_name,
                self.proof_idx,
                self.step_idx,
            )
        )

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, LmExample):
            return False
        return (
            self.proof_script == other.proof_script
            and self.proof_state == other.proof_state
            and self.next_steps == other.next_steps
            and self.proofs == other.proofs
            and self.premises == other.premises
            and self.file_name == other.file_name
            and self.proof_idx == other.proof_idx
            and self.step_idx == other.step_idx
        )

    def to_json(self) -> Any:
        return {
            "proof_script": self.proof_script,
            "proof_state": self.proof_state,
            "next_steps": self.next_steps,
            "proofs": self.proofs,
            "premises": self.premises,
            "file_name": self.file_name,
            "proof_idx": self.proof_idx,
            "step_idx": self.step_idx,
        }

    @classmethod
    def from_json(cls, json_data: Any) -> LmExample:
        # Backward compatability
        if "target" in json_data:
            next_steps = [json_data["target"]]
        else:
            next_steps = json_data["next_steps"]
        proofs = json_data["proofs"] if "proofs" in json_data else None
        premises = json_data["premises"] if "premises" in json_data else None
        file_name = json_data["file_name"] if "file_name" in json_data else None
        proof_idx = json_data["proof_idx"] if "proof_idx" in json_data else None
        step_idx = json_data["step_idx"] if "step_idx" in json_data else None
        return cls(
            json_data["proof_script"],
            json_data["proof_state"],
            next_steps,
            proofs,
            premises,
            file_name,
            proof_idx,
            step_idx,
        )


def fmt_goals(goals: list[Goal]) -> str:
    goal_strings = [goal.to_string() for goal in goals]
    return GOAL_SEP.join(goal_strings)


@dataclass
class GeneralFormatterConf:
    ALIAS = "general"
    premise_client_conf: Optional[PremiseConf]
    proof_retriever_conf: Optional[ProofRetrieverConf]
    num_premises: Optional[int]
    num_proofs: Optional[int]
    align_hint: bool = False  # M3(C1): retrieval된 sibling의 aligned 다음 tactic을 프롬프트에 주입
    apply_hint: bool = False  # M4': top premise가 강하면 apply/eapply/exploit <premise>를 강제 후보로
    sauto_hint: bool = False  # rango-sauto: sauto/hauto/`sauto use:<premise>`를 강제 후보로 (retrieval-guided hammer)
    search_hint: bool = False  # rango-search: Coq Search로 stdlib lemma 찾아 premise에 추가

    def __hash__(self) -> int:
        return hash(str(self))

    @classmethod
    def from_yaml(cls, yaml_data: Any) -> GeneralFormatterConf:
        if "premise" in yaml_data:
            premise_conf = premise_conf_from_yaml(yaml_data["premise"])
            assert "num_premises" in yaml_data
            num_premises = yaml_data["num_premises"]
        else:
            premise_conf = None
            num_premises = None

        if "proof_ret" in yaml_data:
            proof_ret_conf = proof_retriever_conf_from_yaml(yaml_data["proof_ret"])
            assert "num_proofs" in yaml_data
            num_proofs = yaml_data["num_proofs"]
        else:
            proof_ret_conf = None
            num_proofs = None

        return cls(
            premise_conf,
            proof_ret_conf,
            num_premises,
            num_proofs,
            yaml_data.get("align_hint", False),
            yaml_data.get("apply_hint", False),
            yaml_data.get("sauto_hint", False),
            yaml_data.get("search_hint", False),
        )


class GeneralFormatter:
    def __init__(
        self,
        premise_client: Optional[PremiseClient],
        proof_retriever: Optional[ProofRetriever],
        num_premises: Optional[int],
        num_proofs: Optional[int],
        align_hint: bool = False,
        apply_hint: bool = False,
        sauto_hint: bool = False,
        search_hint: bool = False,
    ):
        self.premise_client = premise_client
        self.proof_retriever = proof_retriever
        self.num_premises = num_premises
        self.num_proofs = num_proofs
        self.align_hint = align_hint
        self.apply_hint = apply_hint
        self.sauto_hint = sauto_hint
        self.search_hint = search_hint
        # M4': example_from_step이 채우는 강제 apply 대상 premise 이름들 (get_recs가 소비)
        self.forced_premises: list[str] = []

    def example_from_step(
        self,
        step_idx: int,
        proof_idx: int,
        dp_obj: DatasetFile,
        training: bool = False,
        **kwargs: Any,
    ) -> LmExample:
        # ★ retrieval debug 프린트 게이트(기본 OFF) — 학습 시 예제마다 수백줄 출력해 치명적 저속.
        _rdbg = os.environ.get("RANGO_RETRIEVAL_DEBUG") == "1"
        def _dp(*_a, **_k):
            if _rdbg:
                print(*_a, **_k)
        proof = dp_obj.proofs[proof_idx]
        step = proof.steps[step_idx]
        file_repos_path = get_repos_path(dp_obj.file_context.file)

        # ── 현재 상태 출력 ──────────────────────────────────────────────
        script_so_far = proof.proof_prefix_to_string(step).strip()
        _dp(f"\n  ── 현재 증명 script (step_idx={step_idx}) ──")
        for line in script_so_far.splitlines():
            _dp(f"    {line}")
        _dp(f"  ── 현재 Goal state ──")
        for gi, g in enumerate(step.goals):
            _dp(f"    [Goal {gi}]")
            for h in g.hyps:
                _dp(f"      hyp: {h}")
            _dp(f"      ⊢   {g.goal}")

        def print_query_state(indent: str, goals: list[Goal]) -> None:
            """아래 top5가 '지금까지 어떤 tactic까지 실행됐고, 현재 어떤 goal
            상태인지'(= 검색 쿼리로 쓰인 상태)에서 뽑힌 것임을 top5 바로 앞에
            다시 보여준다."""
            _dp(f"{indent}── 이 top5를 뽑은 기준 상태 ──")
            _dp(f"{indent}· 지금까지 실행한 tactic (step_idx={step_idx}):")
            if script_so_far:
                for line in script_so_far.splitlines():
                    _dp(f"{indent}    {line}")
            else:
                _dp(f"{indent}    (아직 실행한 tactic 없음 — 증명 시작 지점)")
            _dp(f"{indent}· 위 tactic들을 실행한 뒤의 현재 goal (총 {len(goals)}개, 이걸 쿼리로 검색):")
            if not goals:
                _dp(f"{indent}    (남은 goal 없음)")
            for gi, g in enumerate(goals):
                _dp(f"{indent}    [Goal {gi}]")
                for h in g.hyps:
                    _dp(f"{indent}      hyp: {h}")
                _dp(f"{indent}      ⊢   {g.goal}")

        def print_retrieved(rank: int, text: str, query_set: set[str]) -> None:
            """검색된 증명/전제 전체를 (줄바꿈 유지하여) 출력한다.
            기존엔 한 줄로 flatten 후 160자에서 잘라 theorem 뒤 proof 본문이
            통째로 사라졌었다 → 전체를 그대로 보여준다."""
            text = text.strip()
            item_ids = set(_ID_FORM.findall(text))
            matched = sorted(query_set & item_ids)
            _dp(f"      Top{rank}:")
            for line in text.splitlines():
                _dp(f"          {line}")
            id_preview = sorted(item_ids)[:15]
            _dp(f"              item_ids(전체): {id_preview}{'...' if len(item_ids) > 15 else ''}")
            _dp(f"              매칭 IDs      : {matched}")

        if self.proof_retriever is not None:
            assert self.num_proofs is not None
            # 쿼리 ID 계산 (BM25/TFIDF에 실제 사용되는 값)
            proof_query_hyp_ids: list[str] = []
            proof_query_goal_ids: list[str] = []
            for g in step.goals:
                hyp_ids, goal_ids = g.get_ids()
                proof_query_hyp_ids.extend(hyp_ids)
                proof_query_goal_ids.extend(goal_ids)
            proof_query_set = set(proof_query_hyp_ids + proof_query_goal_ids)
            retriever_type = type(self.proof_retriever).__name__
            kind = getattr(self.proof_retriever, "kind", "?")
            _dp(f"\n  [Proof Retrieval ({retriever_type}, {kind})]")
            print_query_state("    ", step.goals)
            _dp(f"    쿼리 hyp_ids : {proof_query_hyp_ids}")
            _dp(f"    쿼리 goal_ids: {proof_query_goal_ids}")
            all_similar_proofs = self.proof_retriever.get_similar_proofs(
                step_idx,
                proof,
                dp_obj,
                training,
            )
            _dp(f"    전체 후보: {len(all_similar_proofs)}개  →  top5:")
            for j, p in enumerate(all_similar_proofs[:5]):
                print_retrieved(j + 1, p.proof_text_to_string(), proof_query_set)
            simliar_proofs = all_similar_proofs[: self.num_proofs]
            similar_proof_strs = [p.proof_text_to_string() for p in simliar_proofs]

            # M3(C1): 매칭된 sibling 중간상태의 '다음 tactic'을 복원해 프롬프트에 힌트로 주입
            if self.align_hint and hasattr(self.proof_retriever, "get_similar_proof_steps"):
                try:
                    steps = self.proof_retriever.get_similar_proof_steps(
                        step_idx, proof, dp_obj, training
                    )
                    if steps:
                        ref_proof, step_id = steps[0]
                        aligned = ref_proof.steps[step_id.step_idx].step.text.strip()
                        # 자명한 tactic(Proof./불릿/빈값)은 힌트로 무의미 → 건너뜀
                        trivial = (not aligned) or aligned == "Proof." or all(
                            c in "*-+{} " for c in aligned
                        )
                        if not trivial:
                            # 주석(* *) 대신 실제 tactic을 그대로 최상단에 주입 —
                            # 모델이 따라 해도 유효 Coq이라 안전. 유사증명 스니펫처럼 취급됨.
                            similar_proof_strs = [aligned] + similar_proof_strs
                            _dp(f"  [Align hint] {aligned}")
                except Exception as _e:
                    _dp(f"  [Align hint] skipped ({_e})")
        else:
            similar_proof_strs = None

        self.forced_premises = []  # M4': 매 스텝 초기화
        if self.premise_client is not None:
            assert self.num_premises is not None
            filtered_result = (
                self.premise_client.premise_filter.get_pos_and_avail_premises(
                    step, proof, dp_obj
                )
            )
            # 쿼리 ID 계산 (focused_goal = goals[0])
            premise_type = type(self.premise_client).__name__
            kind = getattr(self.premise_client, "kind", "?")
            _dp(f"\n  [Premise Retrieval ({premise_type}, {kind})]")
            # premise 검색은 focused_goal(goals[0]) 하나만 쿼리로 사용
            print_query_state("    ", step.goals[:1])
            prem_query_set: set[str] = set()
            if step.goals:
                focused_goal = step.goals[0]
                prem_hyp_ids, prem_goal_ids = focused_goal.get_ids()
                prem_query_set = set(prem_hyp_ids + prem_goal_ids)
                _dp(f"    쿼리 focused_goal ⊢ {focused_goal.goal}")
                _dp(f"    쿼리 hyp_ids : {prem_hyp_ids}")
                _dp(f"    쿼리 goal_ids: {prem_goal_ids}")
            all_relevant_premises = self.premise_client.get_ranked_premises(
                step_idx, proof, dp_obj, filtered_result.avail_premises, training
            )
            _dp(f"    전체 후보: {len(all_relevant_premises)}개  →  top5:")
            for j, p in enumerate(all_relevant_premises[:5]):
                print_retrieved(j + 1, p.text, prem_query_set)
            relevant_premises = all_relevant_premises[: self.num_premises]
            relevant_premise_strs = [p.text for p in relevant_premises]

            # M4': top premise가 강하면 그 lemma 이름을 추출해 강제 apply 대상으로 stash
            # sauto는 비싸므로 초기 goal(step_idx<=1)에만 주입(sparse) — 모든 노드면 시간 폭식→회귀.
            if self.apply_hint or (self.sauto_hint and step_idx <= 1):
                for p in all_relevant_premises[:2]:  # top-2 premise
                    name = _lemma_name(p.text)
                    if name and name not in self.forced_premises:
                        self.forced_premises.append(name)
                if self.forced_premises:
                    _dp(f"  [Apply hint] 강제 apply 대상: {self.forced_premises}")
        else:
            relevant_premise_strs = None

        # rango-search: 초기 goal의 식별자로 Coq Search → stdlib built-in lemma를
        # 찾아 forced_premises에 추가(get_recs가 sauto use:로 먹임). BM25가 못 찾는 것.
        if self.search_hint and step_idx <= 1 and step.goals:
            goal_ids: list[str] = []
            for g in step.goals[:1]:
                _, gid = g.get_ids()
                goal_ids.extend(gid)
            found = coq_search(goal_ids)
            for name in found:
                if name not in self.forced_premises:
                    self.forced_premises.append(name)
            if found:
                _dp(f"  [Search hint] stdlib lemma: {found}")

        script = proof.proof_prefix_to_string(step)
        goals = fmt_goals(step.goals)
        next_steps = [s.step.text for s in proof.steps[step_idx:]]
        return LmExample(
            script,
            goals,
            next_steps,
            similar_proof_strs,
            relevant_premise_strs,
            str(file_repos_path),
            proof_idx,
            step_idx,
        )

    def close(self):
        if self.proof_retriever is not None:
            close_proof_retriever(self.proof_retriever)

    @classmethod
    def from_conf(cls, conf: GeneralFormatterConf) -> GeneralFormatter:
        if conf.premise_client_conf is not None:
            premise_client = premise_client_from_conf(conf.premise_client_conf)
            assert conf.num_premises is not None
        else:
            premise_client = None

        if conf.proof_retriever_conf is not None:
            assert conf.num_proofs is not None
            proof_retriever = proof_retriever_from_conf(conf.proof_retriever_conf)
        else:
            proof_retriever = None

        return cls(
            premise_client,
            proof_retriever,
            conf.num_premises,
            conf.num_proofs,
            getattr(conf, "align_hint", False),
            getattr(conf, "apply_hint", False),
            getattr(conf, "sauto_hint", False),
            getattr(conf, "search_hint", False),
        )


FormatterConf = GeneralFormatterConf


def formatter_from_conf(c: FormatterConf) -> LmFormatter:
    match c:
        case GeneralFormatterConf():
            return GeneralFormatter.from_conf(c)


def formatter_update_ips(f: FormatterConf, port_map: dict[int, tuple[str, int]]):
    match f:
        case GeneralFormatterConf():
            if f.premise_client_conf is not None:
                premise_conf_update_ips(f.premise_client_conf, port_map)
            if f.proof_retriever_conf is not None:
                proof_conf_update_ips(f.proof_retriever_conf, port_map)


def formatter_conf_from_yaml(yaml_data: Any) -> FormatterConf:
    attempted_alias = yaml_data["alias"]
    match attempted_alias:
        case GeneralFormatterConf.ALIAS:
            return GeneralFormatterConf.from_yaml(yaml_data)
        case _:
            raise ValueError("Formatter conf not found: " + attempted_alias)


LmFormatter = GeneralFormatter


def close_lm_formatter(lm_formatter: LmFormatter):
    match lm_formatter:
        case GeneralFormatter():
            if lm_formatter.proof_retriever is not None:
                close_proof_retriever(lm_formatter.proof_retriever)
            if lm_formatter.premise_client is not None:
                close_premise_client(lm_formatter.premise_client)
