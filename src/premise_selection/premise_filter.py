from __future__ import annotations
import rango_defaults as _D   # ★ 프로덕션 기본값 단일 출처
from typing import Any, Optional
import ipdb

from dataclasses import dataclass

import sys, os
import re
import json

from data_management.dataset_file import DatasetFile, Proof, FocusedStep, Sentence
from coqpyt.coq.structs import TermType

from enum import Enum
from util.constants import RANGO_LOGGER
import logging

_logger = logging.getLogger(RANGO_LOGGER)


class KnownFilter(Enum):
    ALL = 0
    PROJ = 1
    THM = 2
    PROJ_THM = 3

    @classmethod
    def from_str(cls, filter_str: str) -> KnownFilter:
        if filter_str == "all":
            return cls.ALL
        if filter_str == "proj":
            return cls.PROJ
        if filter_str == "thm":
            return cls.THM
        if filter_str == "proj-thm":
            return cls.PROJ_THM
        raise ValueError(f"Unknown filter string {filter_str}")


@dataclass(frozen=True)
class PremiseFilterConf:
    coq_excludes: list[str]
    non_coq_excludes: list[str]
    general_excludes: list[str]

    def __hash__(self) -> int:
        return hash(
            (
                tuple(self.coq_excludes),
                tuple(self.non_coq_excludes),
                tuple(self.general_excludes),
            )
        )

    @classmethod
    def from_yaml(cls, yaml_data: Any) -> PremiseFilterConf:
        known_filter = None
        if "known_filter" in yaml_data:
            known_filter = KnownFilter.from_str(yaml_data["known_filter"])
            match known_filter:
                case KnownFilter.ALL:
                    return NO_FILTER_CONF
                case KnownFilter.PROJ:
                    return PROJ_FILTER_CONF
                case KnownFilter.THM:
                    return THM_FILTER_CONF
                case KnownFilter.PROJ_THM:
                    return PROJ_THM_FILTER_CONF
        return cls(
            yaml_data["coq_excludes"],
            yaml_data["non_coq_excludes"],
            yaml_data["general_excludes"],
        )


@dataclass
class FilteredResult:
    pos_premises: list[Sentence]
    avail_premises: list[Sentence]


@dataclass
class OOFCache:
    dset_file: DatasetFile
    filtered_list: list[Sentence]
    filtered_set: set[Sentence]


# ★★ **풀 구성이 환각의 최대 원인이다** (실측: 결손 이름의 62%가 여기서 나온다).
#
#   `PROJ_THM_FILTER_CONF` 는 프로젝트 파일에서 DEFINITION·INDUCTIVE·RECORD·FIXPOINT
#   를 검색 풀에서 통째로 뺀다. 그런데 HoTT 는 **정리를 `Definition` 으로 선언한다** —
#   실측: HoTT 선언 18,557개 중 풀에 드는 것은 3,157개(17.0%)뿐이다.
#   그래서 정답이 `srapply isequiv_adjointify` 를 써도 그 이름은 검색으로 못 온다.
#
#   "이름만 Definition 인 정리" 를 가르는 구문 규칙은 둘 다 깨졌다:
#     · `:=` 없음(스크립트로 증명)  → cancelL·inv_pp 는 `:=` 가 있다(증명항으로 쓴 정리)
#     · 타입이 명제 모양            → isequiv_adjointify 의 타입은 그냥 `IsEquiv f`
#   믿을 수 있는 건 **사용 사실**뿐이다 — 누가 tactic 인자로 쓴 적이 있는가.
#
#   ★ 누출 방지: split 이 **프로젝트 단위**라 TRAIN 전용 집계는 VAL/TEST 에서 텅 빈다.
#     대신 **서로 다른 파일 2개 이상**을 요구한다 — 평가 대상 파일 자신의 기여만으로는
#     절대 승격되지 않는다.
#
#   실측 풀 증가(파일>=2)  전체 +15.9% · HoTT +66.7% · CompCert +21.4% · gaia +3.3%
_USED_NAMES = None
_USED_HEAD = re.compile(
    r"^\s*(?:#\[[^\]]*\]\s*)?(?:Global\s+|Local\s+|Polymorphic\s+|Monomorphic\s+|"
    r"Program\s+|Private\s+|Cumulative\s+|NonCumulative\s+)*"
    r"(?:Lemma|Theorem|Corollary|Remark|Fact|Proposition|Property|Definition|Example|"
    r"Fixpoint|CoFixpoint|Inductive|CoInductive|Variant|Record|Structure|Class|"
    r"Instance|Axiom|Parameter|Let)\s+([A-Za-z_][\w']*)")
# ★ **따옴표 없는 축약형 Notation** — `Notation ZeroR := ([0]:R).`
#   실측: CoRN 의 ZeroR 은 34개 파일에서 82회, OneR 은 16개 파일에서 38회 쓰인다.
#   결손 이름 13건 중 2건이 이 형태였고, premise 원문이 곧 모델이 필요한 답이다.
#   기호 notation(`Notation "A ⊢I phi" := ...`)은 여기 안 걸린다 — 그건 검색이 아니라
#   goal 앵커링(notation_index)이 맡는다.
_USED_ABBR = re.compile(
    r"^\s*(?:Local\s+|Global\s+)?Notation\s+([A-Za-z_][\w']*)\s*:=")
_USED_PROJ = re.compile(r"(?:^|/)repos/([^/]+)/")


def _used_names() -> dict:
    global _USED_NAMES
    if _USED_NAMES is None:
        try:
            with open(os.environ.get("USED_NAMES_PATH", "data/used_names.json")) as f:
                _USED_NAMES = json.load(f)
        except Exception:
            _USED_NAMES = {}
    return _USED_NAMES


def admit_by_usage(premise) -> bool:
    """제외 종류이지만 **프로젝트에서 실제로 tactic 인자로 쓰인** premise 인가."""
    if (not _D.flag("PREMISE_ADMIT_USED")):
        return False
    idx = _used_names()
    if not idx:
        return False
    m = _USED_PROJ.search(premise.file_path or "")
    if not m:
        return False
    e = idx.get(m.group(1))
    if not e:
        return False
    h = _USED_HEAD.match(premise.text or "") or _USED_ABBR.match(premise.text or "")
    if not h:
        return False
    v = e.get(h.group(1))
    if not v:
        return False
    n, nf = (v if isinstance(v, list) else [v, 99])
    return (nf >= _D.num("ADMIT_MIN_FILES")
            and n >= int(os.environ.get("ADMIT_MIN_USES", "1")))


class PremiseFilter:
    def __init__(
        self,
        coq_excludes: list[TermType] = [],
        non_coq_excludes: list[TermType] = [],
        general_excludes: list[TermType] = [],
    ) -> None:
        self.coq_excludes = coq_excludes
        self.non_coq_excludes = non_coq_excludes
        self.general_excludes = general_excludes
        self.__oof_cache: Optional[OOFCache] = None

    def filter_premise(self, premise: Sentence) -> bool:
        if premise.sentence_type in self.general_excludes:
            return False
        from_coq = os.path.join("lib", "coq", "theories") in premise.file_path
        if from_coq and (premise.sentence_type in self.coq_excludes):
            return False
        if (not from_coq) and (premise.sentence_type in self.non_coq_excludes):
            # ★ 제외 종류라도 **실제로 쓰인 이름**이면 되살린다(PREMISE_ADMIT_USED=1).
            return admit_by_usage(premise)
        return True

    def get_in_file_filtered_premises(
        self, step: FocusedStep, proof: Proof, dset_obj: DatasetFile
    ) -> list[Sentence]:
        in_file_before_proof = dset_obj.get_in_file_premises_before(proof)
        return [p for p in in_file_before_proof if self.filter_premise(p)]

    def __check_dset_cache(self, dset_obj: DatasetFile) -> OOFCache:
        match self.__oof_cache:
            case OOFCache(dset_file=cache_dset_file) if cache_dset_file is dset_obj:
                return self.__oof_cache
            case _:
                filtered_list = [
                    p
                    for p in dset_obj.out_of_file_avail_premises
                    if self.filter_premise(p)
                ]
                self.__oof_cache = OOFCache(dset_obj, filtered_list, set(filtered_list))
                return self.__oof_cache

    def get_oof_filtered_premises(self, dset_obj: DatasetFile) -> list[Sentence]:
        cache_result = self.__check_dset_cache(dset_obj)
        return cache_result.filtered_list

    def get_pos_filtered_premises(
        self,
        step: FocusedStep,
        proof: Proof,
        dset_obj: DatasetFile,
        oof_premises: set[Sentence],
        in_file_premises: set[Sentence],
    ) -> list[Sentence]:
        all_positive_candidates = step.step.context
        filtered_positive_candidates: list[Sentence] = []
        for pos_premise in all_positive_candidates:
            passes_filter = self.filter_premise(pos_premise)
            same_file = pos_premise.file_path == proof.theorem.term.file_path
            prev_line_in_file = same_file and (
                pos_premise.line < proof.theorem.term.line
            )
            premise_available = (not same_file) or prev_line_in_file
            premise_in_context = (pos_premise in in_file_premises) or (
                pos_premise in oof_premises
            )
            if passes_filter and premise_available and premise_in_context:
                filtered_positive_candidates.append(pos_premise)
            if passes_filter and not premise_available:
                _logger.warning(
                    f"Same file positive premise not available at {pos_premise.file_path}:{pos_premise.line}",
                )
            if passes_filter and not premise_in_context:
                _logger.warning(
                    f"Positive premise not in context at {pos_premise.file_path}:{pos_premise.line}",
                )

        return filtered_positive_candidates

    def get_pos_and_avail_premises(
        self, step: FocusedStep, proof: Proof, dset_obj: DatasetFile
    ) -> FilteredResult:
        """TODO: Change proof.line to step.line"""
        in_file_premises = self.get_in_file_filtered_premises(step, proof, dset_obj)
        cache_result = self.__check_dset_cache(dset_obj)
        filtered_avail_candidates = cache_result.filtered_list + in_file_premises
        filtered_pos_candidates = self.get_pos_filtered_premises(
            step, proof, dset_obj, cache_result.filtered_set, set(in_file_premises)
        )
        return FilteredResult(filtered_pos_candidates, filtered_avail_candidates)

    @classmethod
    def from_conf(cls, conf: PremiseFilterConf) -> PremiseFilter:
        coq_excludes: list[TermType] = []
        for exclude in conf.coq_excludes:
            coq_excludes.append(TermType[exclude])

        non_coq_excludes: list[TermType] = []
        for exclude in conf.non_coq_excludes:
            non_coq_excludes.append(TermType[exclude])

        general_excludes: list[TermType] = []
        for exclude in conf.general_excludes:
            general_excludes.append(TermType[exclude])

        return cls(coq_excludes, non_coq_excludes, general_excludes)


PROJ_THM_FILTER_CONF = PremiseFilterConf(
    coq_excludes=[
        "THEOREM",
        "LEMMA",
        "DEFINITION",
        "NOTATION",
        "INDUCTIVE",
        "COINDUCTIVE",
        "RECORD",
        "CLASS",
        "INSTANCE",
        "FIXPOINT",
        "COFIXPOINT",
        "SCHEME",
        "VARIANT",
        "FACT",
        "REMARK",
        "COROLLARY",
        "PROPOSITION",
        "PROPERTY",
        "OBLIGATION",
        "TACTIC",
        "RELATION",
        "SETOID",
        "FUNCTION",
        "DERIVE",
        "OTHER",
    ],
    non_coq_excludes=[
        "DEFINITION",
        "NOTATION",
        "INDUCTIVE",
        "COINDUCTIVE",
        "RECORD",
        "CLASS",
        "INSTANCE",
        "FIXPOINT",
        "COFIXPOINT",
        "SCHEME",
        "VARIANT",
        "OBLIGATION",
        "TACTIC",
        "RELATION",
        "SETOID",
        "FUNCTION",
        "DERIVE",
        "OTHER",
    ],
    general_excludes=[],
)

PROJ_FILTER_CONF = PremiseFilterConf(
    coq_excludes=[
        "THEOREM",
        "LEMMA",
        "DEFINITION",
        "NOTATION",
        "INDUCTIVE",
        "COINDUCTIVE",
        "RECORD",
        "CLASS",
        "INSTANCE",
        "FIXPOINT",
        "COFIXPOINT",
        "SCHEME",
        "VARIANT",
        "FACT",
        "REMARK",
        "COROLLARY",
        "PROPOSITION",
        "PROPERTY",
        "OBLIGATION",
        "TACTIC",
        "RELATION",
        "SETOID",
        "FUNCTION",
        "DERIVE",
        "OTHER",
    ],
    non_coq_excludes=[],
    general_excludes=[],
)

THM_FILTER_CONF = PremiseFilterConf(
    coq_excludes=[
        "DEFINITION",
        "NOTATION",
        "INDUCTIVE",
        "COINDUCTIVE",
        "RECORD",
        "CLASS",
        "INSTANCE",
        "FIXPOINT",
        "COFIXPOINT",
        "SCHEME",
        "VARIANT",
        "OBLIGATION",
        "TACTIC",
        "RELATION",
        "SETOID",
        "FUNCTION",
        "DERIVE",
        "OTHER",
    ],
    non_coq_excludes=[
        "DEFINITION",
        "NOTATION",
        "INDUCTIVE",
        "COINDUCTIVE",
        "RECORD",
        "CLASS",
        "INSTANCE",
        "FIXPOINT",
        "COFIXPOINT",
        "SCHEME",
        "VARIANT",
        "OBLIGATION",
        "TACTIC",
        "RELATION",
        "SETOID",
        "FUNCTION",
        "DERIVE",
        "OTHER",
    ],
    general_excludes=[],
)

NO_FILTER_CONF = PremiseFilterConf(
    coq_excludes=[],
    non_coq_excludes=[],
    general_excludes=[],
)
