from __future__ import annotations
import rango_defaults as _D   # ★ 프로덕션 기본값 단일 출처

import os
from typing import Iterable, Any, Optional
import sys, os
import argparse
import re
import functools
from pathlib import Path
import random
import math
import requests
from dataclasses import dataclass
from enum import Enum

from data_management.dataset_file import (
    Goal,
    DatasetFile,
    DPCache,
    get_ids_from_sentence,
    get_ids_from_goal,
)
from data_management.sentence_db import SentenceDB
from data_management.dataset_file import FocusedStep, Proof, Sentence
from premise_selection.premise_formatter import (
    ContextFormat,
    PremiseFormat,
    CONTEXT_ALIASES,
    PREMISE_ALIASES,
)
from premise_selection.premise_filter import PremiseFilter, PremiseFilterConf
from premise_selection.retrieved_premise_db import RetrievedPremiseDB
from proof_retrieval.bm25 import bm25
from proof_retrieval.tfidf import tf_idf, compute_idfs
from coqpyt.coq.structs import TermType

from util.util import FlexibleUrl


@dataclass
class SelectModelConf:
    ALIAS = "select"
    checkpoint_loc: Path
    vector_db_loc: Optional[Path]
    cached_premise_loc: Optional[Path]

    @classmethod
    def from_yaml(cls, yaml_data: Any) -> SelectModelConf:
        if "cached_premise_loc" in yaml_data:
            cached_premise_loc = Path(yaml_data["cached_premise_loc"])
        else:
            cached_premise_loc = None
        return cls(
            Path(yaml_data["checkpoint_loc"]),
            Path(yaml_data["vector_db_loc"]),
            cached_premise_loc,
        )


@dataclass
class LookupClientConf:
    ALIAS = "lookup"
    context_format_alias: str
    premise_format_alias: str
    premise_filter_conf: PremiseFilterConf

    @classmethod
    def from_yaml(cls, yaml_data: Any) -> LookupClientConf:
        return cls(
            yaml_data["context_format_alias"],
            yaml_data["premise_format_alias"],
            PremiseFilterConf.from_yaml(yaml_data["premise_filter"]),
        )


@dataclass
class SparseConf:
    ALIAS = "sparse"
    kind: SparseKind
    context_format_alias: str
    premise_format_alias: str
    premise_filter_conf: PremiseFilterConf
    sentence_db_loc: Path
    cached_premise_loc: Optional[Path]

    @classmethod
    def from_yaml(cls, yaml_data: Any) -> SparseConf:
        if "cached_premise_loc" in yaml_data:
            cached_premise_loc = Path(yaml_data["cached_premise_loc"])
        else:
            cached_premise_loc = None
        return cls(
            SparseKind.from_str(yaml_data["kind"]),
            yaml_data["context_format_alias"],
            yaml_data["premise_format_alias"],
            PremiseFilterConf.from_yaml(yaml_data["premise_filter"]),
            Path(yaml_data["sentence_db_loc"]),
            cached_premise_loc,
        )


@dataclass
class SelectModelClientConf:
    ALIAS = "select-client"
    urls: list[FlexibleUrl]
    context_format_alias: str
    premise_format_alias: str
    premise_filter_conf: PremiseFilterConf
    sentence_db_loc: Path
    cached_premise_loc: Optional[Path]

    def merge(self, other: SelectModelClientConf) -> SelectModelClientConf:
        new_urls = self.urls + other.urls
        assert self.context_format_alias == other.context_format_alias
        assert self.premise_format_alias == other.premise_format_alias
        assert self.premise_filter_conf == other.premise_filter_conf
        assert self.sentence_db_loc == other.sentence_db_loc
        return SelectModelClientConf(
            new_urls,
            self.context_format_alias,
            self.premise_format_alias,
            self.premise_filter_conf,
            self.sentence_db_loc,
            self.cached_premise_loc,
        )

    def update_ips(self, port_map: dict[int, tuple[str, int]]):
        for url in self.urls:
            new_ip, new_port = port_map[url.id]
            url.ip = new_ip
            url.port = new_port

    @classmethod
    def from_yaml(cls, yaml_data: Any) -> SelectModelClientConf:
        if "cached_premise_loc" in yaml_data:
            cached_premise_loc = Path(yaml_data["cached_premise_loc"])
        else:
            cached_premise_loc = None
        return cls(
            [FlexibleUrl.from_yaml(u) for u in yaml_data["urls"]],
            yaml_data["context_format_alias"],
            yaml_data["premise_format_alias"],
            PremiseFilterConf.from_yaml(yaml_data["premise_filter"]),
            Path(yaml_data["sentence_db_loc"]),
            cached_premise_loc,
        )


# @dataclass
# class TFIdfProofClientConf:
#     ALIAS = "tfidf-proof"
#     context_format_alias: str
#     premise_format_alias: str
#     premise_filter_conf: PremiseFilterConf
#     text_proof_retriever_conf: TfIdfProofRetrieverConf
#     nucleus_size: int

#     @classmethod
#     def from_yaml(cls, yaml_data: Any) -> TFIdfProofClientConf:
#         return cls(
#             yaml_data["context_format_alias"],
#             yaml_data["premise_format_alias"],
#             PremiseFilterConf.from_yaml(yaml_data["premise_filter"]),
#             TfIdfProofRetrieverConf.from_yaml(yaml_data["text_proof_retriever"]),
#             yaml_data["nucleus_size"],
#         )


SelectClientConf = (
    SelectModelClientConf | SelectModelConf | SparseConf | LookupClientConf
)


def select_conf_from_yaml(yaml_data: Any) -> SelectClientConf:
    attempted_alias = yaml_data["alias"]
    match attempted_alias:
        case SelectModelConf.ALIAS:
            return SelectModelConf.from_yaml(yaml_data)
        case SelectModelClientConf.ALIAS:
            return SelectModelClientConf.from_yaml(yaml_data)
        case SparseConf.ALIAS:
            return SparseConf.from_yaml(yaml_data)
        case LookupClientConf.ALIAS:
            return LookupClientConf.from_yaml(yaml_data)
        case _:
            raise ValueError("Unknown Configuration")


class SelectPremiseClient:
    def __init__(
        self,
        urls: list[str],
        context_format: type[ContextFormat],
        premise_format: type[PremiseFormat],
        premise_filter: PremiseFilter,
        sentence_db: SentenceDB,
        cached_premises: Optional[RetrievedPremiseDB],
    ):
        self.context_format = context_format
        self.premise_format = premise_format
        self.premise_filter = premise_filter
        self.sentence_db = sentence_db
        self.cached_premises = cached_premises
        self.session = requests.Session()
        self.urls = urls

    def clear_transformation_matrix(self):
        for url in self.urls:
            request_data = {
                "method": "clear_transform_mat",
                "params": [],
                "jsonrpc": "2.0",
                "id": 0,
            }
            self.session.post(url, json=request_data)

    def set_transformation_matrix(
        self, premises: list[Sentence], steps: list[FocusedStep], proofs: list[Proof]
    ):
        assert len(premises) == len(steps)
        assert len(steps) == len(proofs)
        cstrs = [self.context_format.format(s, p) for s, p in zip(steps, proofs)]
        premises_json = [s.to_json(self.sentence_db, False) for s in premises]
        for url in self.urls:
            request_data = {
                "method": "set_transform_mat",
                "params": [premises_json, cstrs],
                "jsonrpc": "2.0",
                "id": 0,
            }
            self.session.post(url, json=request_data).json()

    def get_premise_scores_from_strings(
        self, context_str: str, premises: list[Sentence]
    ) -> list[float]:
        idxs: list[int] = []
        orig_idxs: list[int] = []
        orig_idxs_other: list[int] = []
        other_premises: list[Sentence] = []
        for i, p in enumerate(premises):
            if p.db_idx is not None:
                idxs.append(p.db_idx)
                orig_idxs.append(i)
            else:
                other_premises.append(p)
                orig_idxs_other.append(i)

        other_premises_json = [
            s.to_json(self.sentence_db, False) for s in other_premises
        ]
        request_data = {
            "method": "get_scores",
            "params": [context_str, idxs, other_premises_json],
            "jsonrpc": "2.0",
            "id": 0,
        }
        request_url = random.choice(self.urls)
        response = self.session.post(request_url, json=request_data).json()
        result = response["result"]

        orig_idxs = orig_idxs + orig_idxs_other
        new_order = sorted(range(len(orig_idxs)), key=lambda idx: orig_idxs[idx])
        scores: list[float] = []
        for new_idx in new_order:
            scores.append(result[new_idx])
        return scores

    def get_ranked_premises(
        self,
        step_idx: int,
        proof: Proof,
        dp_obj: DatasetFile,
        premises: list[Sentence],
        training: bool,
    ) -> list[Sentence]:
        if training:
            cached_scores = get_cached_premises(
                self.cached_premises, step_idx, proof, dp_obj, self.sentence_db
            )
            if cached_scores:
                return cached_scores
        step = proof.steps[step_idx]
        formatted_context = self.context_format.format(step, proof)
        premise_scores = self.get_premise_scores_from_strings(
            formatted_context, premises
        )
        num_premises = len(premise_scores)
        arg_sorted_premise_scores = sorted(
            range(num_premises), key=lambda idx: -1 * premise_scores[idx]
        )
        ranked_premises: list[Sentence] = []
        for idx in arg_sorted_premise_scores:
            ranked_premises.append(premises[idx])
        return ranked_premises

    def close(self):
        self.sentence_db.close()

    @classmethod
    def from_conf(cls, conf: SelectModelClientConf) -> SelectPremiseClient:
        return cls(
            [u.get_url() for u in conf.urls],
            CONTEXT_ALIASES[conf.context_format_alias],
            PREMISE_ALIASES[conf.premise_format_alias],
            PremiseFilter.from_conf(conf.premise_filter_conf),
            SentenceDB.load(conf.sentence_db_loc),
            (
                RetrievedPremiseDB.load(conf.cached_premise_loc)
                if conf.cached_premise_loc is not None
                else None
            ),
        )


class SparseKind(Enum):
    TFIDF = 0
    BM25 = 1

    @classmethod
    def from_str(cls, s: str) -> SparseKind:
        match s:
            case "tfidf":
                return cls.TFIDF
            case "bm25":
                return cls.BM25
            case _:
                raise ValueError(f"Unknown SparseKind {s}")


def get_cached_premises(
    cached_premises: Optional[RetrievedPremiseDB],
    step_idx: int,
    proof: Proof,
    dset_file: DatasetFile,
    sentence_db: SentenceDB,
) -> Optional[list[Sentence]]:
    if cached_premises is None:
        return None
    return cached_premises.get_premises(
        step_idx, proof.proof_idx, dset_file, sentence_db
    )


# ★★ **랭커는 파이썬 상수가 단일 출처다.** shell `export` 로 두면 위험하다 —
#   `source` 를 잊으면 조용히 다른 랭커(tfidf)로 돌아가는데, 결과만 보고는
#   설정이 빠진 건지 랭커가 나쁜 건지 구분할 수 없다.
#   env 는 **절제 실험용 덮어쓰기**로만 쓴다(`RETRIEVAL_MODE=tfidf` 등).
#
#   근거 (CompCert TEST 1,200스텝 · 이름 개명 조건 · exp_abcd)
#       A·프롬프트 ALL   tfidf 30.2%  →  afh70 42.0%   (+11.8pp)
#       합성 ALL·P       tfidf 90.1%  →  afh70 97.2%   (+7.1pp, McNemar p=0.0001)
#   비용 (CompCert 40파일 147스텝 · 캐시 워밍 후 · bench_ranker_scale.py)
#       검색 14.5ms(tfidf) → 25.0ms(afh70) · 노드 300ms 대비 4.6% → 7.7%
DEFAULT_RETRIEVAL_MODE = _D.PROD_DEFAULTS["RETRIEVAL_MODE"]   # 단일 출처


def retrieval_mode() -> str:
    """실제로 쓰이는 랭커 이름. env 가 있으면 그것, 없으면 파이썬 기본값."""
    return _D.get("RETRIEVAL_MODE") or DEFAULT_RETRIEVAL_MODE


@dataclass
class SparseClient:
    kind: SparseKind
    context_format: type[ContextFormat]
    premise_format: type[PremiseFormat]
    premise_filter: PremiseFilter
    sentence_db: SentenceDB
    cached_premises: Optional[RetrievedPremiseDB]

    def get_premise_scores(
        self, context: Goal, premises: list[Sentence]
    ) -> list[float]:
        # premise_strs = [self.premise_format.format(p) for p in premises]
        premise_docs = [get_ids_from_sentence(p) for p in premises]
        query_hyp_ids, query_goal_ids = get_ids_from_goal(context)
        query_ids = query_hyp_ids + query_goal_ids
        # query_ids = query_goal_ids
        # query = tokenize(context_str)
        match self.kind:
            case SparseKind.TFIDF:
                base = tf_idf(query_ids, premise_docs)
            case SparseKind.BM25:
                base = bm25(query_ids, premise_docs)
            case _:
                base = tf_idf(query_ids, premise_docs)

        # ★ 구조 재랭킹 (all_log/docs/premise/final.md)
        #   RRF(tfidf, 결론구조 C', 질의 포함률) + 3.0×[결론 트리 완전일치]
        #   실측 목표지표 ALL@50: TEST 86.4→95.6 · VAL 86.5→94.9 · TRAIN 87.8→97.2%
        #   되돌리려면 RETRIEVAL_MODE=tfidf (기본은 eqx)
        _mode = retrieval_mode()
        if _mode == "tfidf" or not premises:
            return base
        try:
            from tactic_gen.tier_rank import structural_scores, STAGE1
            texts = [getattr(p, "text", "") or "" for p in premises]
            # ★ eqx (기본) — RRF(tfidf) + RRF(C') + W·1[전체 명제가 α-동치]
            #   `structural` 의 cov·def 를 뺀다. 실측(TEST n=3000, 이름 개명 조건):
            #       목표 ALL·P  structural 85.7 → eqx 92.8   A 30.7 → 36.4
            #   cov 는 A 를 −5.7pp 해치고 C 에 기여가 없다(2차 절제 실험).
            #   def 는 정규식 휴리스틱이라 논문에서 정당화가 안 된다.
            # ★ `eqx` = 지시자(τ=1) · `afh<NN>` = 커널(τ=NN/100). 같은 경로를 쓴다.
            #   afh100 은 eqx 와 **완전히 같다**(족의 끝점 — 자기검사로 못박음).
            _kw = {}
            if _mode == "eqx" or _mode.startswith("afh"):
                _kw = dict(use_eq=False, use_cov=False, use_def=False, use_eqx=True)
                if _mode.startswith("afh"):
                    try:
                        from tactic_gen import tier_rank as _tr
                        _tr.EQX_TAU = int(_mode[3:]) / 100.0
                    except Exception:
                        pass
            return structural_scores(
                getattr(context, "goal", "") or "", getattr(context, "hyps", []) or [],
                texts, base, query_ids=query_ids, docs=premise_docs,
                stage1=_D.num("RETRIEVAL_STAGE1"), **_kw)
        except Exception:
            # ★ 재랭킹이 어떤 이유로 실패해도 **검색 자체가 죽으면 안 된다** — tfidf 로 돌아간다
            return base

    def get_ranked_premises(
        self,
        step_idx: int,
        proof: Proof,
        dp_obj: DatasetFile,
        premises: list[Sentence],
        training: bool,
    ) -> list[Sentence]:
        if training:
            cached_scores = get_cached_premises(
                self.cached_premises, step_idx, proof, dp_obj, self.sentence_db
            )
            if cached_scores:
                return cached_scores
        step = proof.steps[step_idx]
        if len(step.goals) == 0:
            empty_premises: list[Sentence] = []
            return empty_premises
        focused_goal = step.goals[0]
        # formatted_context = self.context_format.format(step, proof)
        premise_scores = self.get_premise_scores(focused_goal, premises)
        num_premises = len(premise_scores)
        arg_sorted_premise_scores = sorted(
            range(num_premises), key=lambda idx: -1 * premise_scores[idx]
        )
        ranked_premises: list[Sentence] = []
        for idx in arg_sorted_premise_scores:
            ranked_premises.append(premises[idx])
        return ranked_premises

    @classmethod
    def from_conf(cls, conf: SparseConf) -> SparseClient:
        if conf.cached_premise_loc is not None:
            cached_premises = RetrievedPremiseDB.load(conf.cached_premise_loc)
        else:
            cached_premises = None
        return cls(
            conf.kind,
            CONTEXT_ALIASES[conf.context_format_alias],
            PREMISE_ALIASES[conf.premise_format_alias],
            PremiseFilter.from_conf(conf.premise_filter_conf),
            SentenceDB.load(conf.sentence_db_loc),
            cached_premises,
        )


@dataclass
class LookupClient:
    context_format: type[ContextFormat]
    premise_format: type[PremiseFormat]
    premise_filter: PremiseFilter
    HYP_PENALTY = 0.7
    COQ_PENALTY = 0.5

    name_forms = [
        re.compile(r"Definition\s+(\S+?)[\[\]\{\}\(\):=,\s]"),
        re.compile(r"Fixpoint\s+(\S+?)[\[\]\{\}\(\):=,\s]"),
        re.compile(r"CoFixpoint\s+(\S+?)[\[\]\{\}\(\):=,\s]"),
        re.compile(r"Inductive\s+(\S+?)[\[\]\{\}\(\):=,\s]"),
        re.compile(r"CoInductive\s+(\S+?)[\[\]\{\}\(\):=,\s]"),
        re.compile(r"Variant\s+(\S+?)[\[\]\{\}\(\):=,\s]"),
        re.compile(r"Class\s+(\S+?)[\[\]\{\}\(\):=,\s]"),
        re.compile(r"Module Type\s+(\S+?)[\[\]\{\}\(\):=,\s]"),
        re.compile(r"Module\s+(\S+?)[\[\]\{\}\(\):=,\s]"),
        re.compile(r"Instance\s+(\S+?)[\[\]\{\}\(\):=,\s]"),
    ]

    def get_name_from_premise(self, premise: Sentence) -> Optional[str]:
        for name_form in self.name_forms:
            search_match = name_form.search(premise.text)
            if search_match is not None:
                (name,) = search_match.groups()
                return name
        return None

    def get_ranked_premises(
        self,
        step_idx: int,
        proof: Proof,
        dp_obj: DatasetFile,
        premises: list[Sentence],
        training: bool,
    ) -> list[Sentence]:
        step = proof.steps[step_idx]
        if len(step.goals) == 0:
            empty_premises: list[Sentence] = []
            return empty_premises
        focused_goal = step.goals[0]
        premise_names = [self.get_name_from_premise(p) for p in premises]
        # print(premise_names)
        premise_scores: list[float] = []
        hyp_id_list, goal_id_list = get_ids_from_goal(focused_goal)
        hyp_ids = set(hyp_id_list)
        goal_ids = set(goal_id_list)
        for sentence, name in zip(premises, premise_names):
            if name is None:
                premise_scores.append(0)
            elif name in goal_ids:
                from_coq = os.path.join("lib", "coq", "theories") in sentence.file_path
                premise_score = self.COQ_PENALTY if from_coq else 1
                premise_scores.append(premise_score)
            elif name in hyp_ids:
                from_coq = os.path.join("lib", "coq", "theories") in sentence.file_path
                premise_score = (
                    self.COQ_PENALTY * self.HYP_PENALTY
                    if from_coq
                    else self.HYP_PENALTY
                )
                premise_scores.append(premise_score)
            else:
                premise_scores.append(0)

        num_premises = len(premise_scores)
        arg_sorted_premise_scores = sorted(
            range(num_premises), key=lambda idx: -1 * premise_scores[idx]
        )
        ranked_premises: list[Sentence] = []
        for idx in arg_sorted_premise_scores:
            if premise_scores[idx] == 0:
                break
            ranked_premises.append(premises[idx])
        return ranked_premises

    @classmethod
    def from_conf(cls, conf: LookupClientConf) -> LookupClient:
        return cls(
            CONTEXT_ALIASES[conf.context_format_alias],
            PREMISE_ALIASES[conf.premise_format_alias],
            PremiseFilter.from_conf(conf.premise_filter_conf),
        )


SelectClient = SelectPremiseClient | SparseClient | LookupClient


dp_cache = DPCache()


def select_client_from_conf(conf: SelectClientConf) -> SelectClient:
    match conf:
        case SelectModelConf():
            raise ValueError("Select Conf Cannot be directly converted into a client.")
        case SelectModelClientConf():
            return SelectPremiseClient.from_conf(conf)
        case SparseConf():
            return SparseClient.from_conf(conf)
        case LookupClientConf():
            return LookupClient.from_conf(conf)
