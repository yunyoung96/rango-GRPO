import argparse
import json
import os
import shutil

from pathlib import Path
from dataclasses import dataclass
from coqstoq import Split, EvalTheorem, get_theorem, get_theorem_list
from coqstoq.check import Result, EvalResults

from tactic_gen.lm_example import GeneralFormatterConf

from proof_retrieval.proof_retriever import SparseProofRetrieverConf
from proof_retrieval.proof_retriever import DeepProofRetrieverConf

from premise_selection.premise_client import SparseConf, SparseKind
from premise_selection.premise_filter import PROJ_THM_FILTER_CONF
from premise_selection.rerank_client import PremiseConf

from model_deployment.tactic_gen_client import TacticGenConf, DecoderTacticGenConf
from model_deployment.searcher import (
    SearcherConf,
    StraightLineSearcherConf,
    ClassicalSearchConf,
)
from model_deployment.portfolio_searcher import PortfolioSearchConf
from model_deployment.rmaxts_searcher import RMaxTSSearchConf
from model_deployment.bfs_prover_searcher import BFSProverSearchConf
from model_deployment.quarry_searcher import QuarrySearchConf
from tactic_gen.grpo_rollout import GRPORolloutSearchConf
from model_deployment.run_proof import TestProofConf

from model_deployment.classical_searcher import ClassicalSuccess, ClassicalFailure
from model_deployment.prove import run_proof, RunProofConf, LocationInfo, RangoResult
from model_deployment.straight_line_searcher import (
    StraightLineSuccess,
    StraightLineFailure,
)
from model_deployment.whole_proof_searcher import (
    WholeProofSuccess,
    WholeProofFailure,
)
from model_deployment.tactic_gen_client import (
    TacticGenConf,
    tactic_conf_update_ips,
    tactic_gen_conf_from_yaml,
    tactic_gen_client_from_conf,
)
from model_deployment.conf_utils import (
    wait_for_servers,
    start_servers,
    tactic_gen_to_client_conf,
    StartModelCommand,
)

from util.util import get_basic_logger, clear_port_map, set_rango_logger

COQSTOQ_LOC = Path("CoqStoq")


def str2split(s: str) -> Split:
    match s:
        case "test":
            return Split.TEST
        case "val":
            return Split.VAL
        case "cutoff":
            return Split.CUTOFF
        case _:
            raise ValueError(
                f"Unknown split {s}. Available splits are 'test', 'val', 'cutoff'."
            )


def get_eval_thm(split: Split, idx: int) -> EvalTheorem:
    assert COQSTOQ_LOC.exists()
    return get_theorem(split, idx, COQSTOQ_LOC)


def get_data_loc(split: Split) -> Path:
    match split:
        case Split.TEST:
            p = Path("raw-data/coqstoq-test")
            assert p.exists()
            return p
        case Split.VAL:
            p = Path("raw-data/coqstoq-val")
            assert p.exists()
            return p
        case Split.CUTOFF:
            p = Path("raw-data/coqstoq-cutoff")
            assert p.exists()
            return p


def get_sentence_db_loc(split: Split) -> Path:
    match split:
        case Split.TEST:
            p = Path("raw-data/coqstoq-test/coqstoq-test-sentences.db")
            assert p.exists()
            return p
        case Split.VAL:
            p = Path("raw-data/coqstoq-val/coqstoq-val-sentences.db")
            assert p.exists()
            return p
        case Split.CUTOFF:
            p = Path("raw-data/coqstoq-cutoff/coqstoq-cutoff-sentences.db")
            assert p.exists()
            return p


def get_searcher_conf(model_alias: str) -> SearcherConf:
    timeout = 600
    straight_line_conf = StraightLineSearcherConf(
        timeout=timeout,
        print_proofs=True,
        initial_proof=None,
        token_mask=None,
    )

    match model_alias:
        case "rango-best-beam":
            return ClassicalSearchConf(
                max_branch=4,
                max_search_steps=1000000,
                depth_limit=30,
                timeout=600,
                beam_decode=True,
                initial_proof=None,
            )

        case "rango-best-rand":
            return ClassicalSearchConf(
                max_branch=4,
                max_search_steps=1000000,
                depth_limit=30,
                timeout=600,
                beam_decode=False,
                initial_proof=None,
            )

        case "rango-apply" | "rango-alignapply" | "rango-sauto" | "rango-search":
            # M4'/조합/sauto: classical+memo (강제 후보를 시도하려면 다중 후보 탐색 필요)
            return ClassicalSearchConf(
                max_branch=8,
                max_search_steps=1000000,
                depth_limit=30,
                timeout=600,
                beam_decode=True,
                initial_proof=None,
                use_memo=True,
            )

        case "rango-mem-wide":
            # M2 변형: classical+memo, 분기 16으로 확대
            return ClassicalSearchConf(
                max_branch=16,
                max_search_steps=1000000,
                depth_limit=30,
                timeout=600,
                beam_decode=True,
                initial_proof=None,
                use_memo=True,
            )

        case "rango-mem":
            # M2: best-first + transposition table/failed-tactic memo/cycle guard.
            # M1(branch=4)이 baseline보다 좁아 하락 → memo가 dedup으로 감당하므로 branch 확대(8).
            return ClassicalSearchConf(
                max_branch=8,
                max_search_steps=1000000,
                depth_limit=30,
                timeout=600,
                beam_decode=True,
                initial_proof=None,
                use_memo=True,
            )

        case "rango-vlog":
            # MR1(RL): classical+memo로 탐색 트리 생성 + (state,label) 덤프(value model 학습 데이터).
            return ClassicalSearchConf(
                max_branch=8,
                max_search_steps=1000000,
                depth_limit=30,
                timeout=timeout,
                beam_decode=True,
                initial_proof=None,
                use_memo=True,
                log_tree=True,
                log_dir="data/vguided_trees",
            )

        case "rango-vguided":
            # MR1(RL): 학습된 value head로 frontier 블렌드된 best-first.
            return ClassicalSearchConf(
                max_branch=8,
                max_search_steps=1000000,
                depth_limit=30,
                timeout=timeout,
                beam_decode=True,
                initial_proof=None,
                use_memo=True,
                value_ckpt="models/value_head/value.pt",
                value_weight=1.0,
            )

        case "rango-apply-sl":
            # straight-line(강한 base) + 각 step 다중후보 시도(forced apply premise 포함)
            return StraightLineSearcherConf(
                timeout=timeout,
                print_proofs=True,
                initial_proof=None,
                token_mask=None,
                try_candidates=6,
            )

        case "rango-psauto":
            return PortfolioSearchConf(
                straight_conf=StraightLineSearcherConf(
                    timeout=timeout, print_proofs=True, initial_proof=None, token_mask=None,
                ),
                classical_conf=ClassicalSearchConf(
                    max_branch=8, max_search_steps=1000000, depth_limit=30,
                    timeout=timeout, beam_decode=True, initial_proof=None, use_memo=True,
                ),
                timeout=timeout, straight_frac=0.8,
            )

        case "rmaxts":
            # RMaxTS 탐색(full). DUCB + RMax reward + truncate-resume + state merging.
            return RMaxTSSearchConf(timeout=timeout, n_rollout_steps=8, print_proofs=True)
        case "rmaxts-noreward":  # ablation: RMax intrinsic reward 제거
            return RMaxTSSearchConf(timeout=timeout, print_proofs=True, use_reward=False)
        case "rmaxts-nomerge":   # ablation: state-merging 제거(pure tree)
            return RMaxTSSearchConf(timeout=timeout, print_proofs=True, use_merge=False)
        case "rmaxts-nomcts":    # ablation: DUCB 제거(uniform 랜덤 선택)
            return RMaxTSSearchConf(timeout=timeout, print_proofs=True, use_ducb=False)

        case "bfs-prover":       # BFS-Prover length-normalized best-first, α=0.5(논문)
            return BFSProverSearchConf(timeout=timeout, alpha=0.5, expand_width=2, print_proofs=True)
        case "bfs-prover-trace":  # BFS-Prover + 트리 덤프(expert-iter/DPO 학습 데이터 수집)
            return BFSProverSearchConf(
                timeout=timeout, alpha=0.5, expand_width=2, print_proofs=True,
                trace_out="data/bfs_trees/trees.jsonl",
            )
        case "bfs-a0":           # ablation: length-norm 제거(α=0, 순수 누적 log-prob)
            return BFSProverSearchConf(timeout=timeout, alpha=0.0, expand_width=2, print_proofs=True)
        case "bfs-a1":           # ablation: full length-norm(α=1.0, per-tactic 평균)
            return BFSProverSearchConf(timeout=timeout, alpha=1.0, expand_width=2, print_proofs=True)

        case "grpo-rollout":
            # GRPO rollout 수집: 정리당 G개 증명 시도 생성·검증 → 그룹 jsonl(학습 데이터).
            return GRPORolloutSearchConf(
                timeout=timeout, group_size=8, max_steps=20,
                out="data/grpo_rollouts/rollouts.jsonl",
            )
        case "quarry":
            # Quarry(Planning to Hammer, 2606.17981) FULL: LLM 분해 + CoqHammer 재귀 + 난이도 랭킹.
            return QuarrySearchConf(
                timeout=timeout, k=8, branch=1, max_depth=5,
                max_llm_calls=60, print_proofs=True,
                difficulty_ckpt="models/quarry_difficulty/difficulty.json",
            )
        case "quarry-heur":
            # Quarry, 난이도 모델 = heuristic θ(학습 전). ablation 아님, 학습X 버전.
            return QuarrySearchConf(
                timeout=timeout, k=8, branch=1, max_depth=5,
                max_llm_calls=60, print_proofs=True, difficulty_ckpt=None,
            )
        case "quarry-trace":
            # trace 수집용(Algorithm 2 학습 데이터). difficulty=heuristic, trace 저장.
            return QuarrySearchConf(
                timeout=timeout, k=8, branch=2, max_depth=5,
                max_llm_calls=80, print_proofs=True, difficulty_ckpt=None,
                trace_out="data/quarry_traces/traces.jsonl",
            )

        case "rango-qed":
            # QEDCartographer 충실 재구현: coq2vec value + product-over-subgoals backup으로
            # best-first 우선순위 유도(value-first). value_weight>0로 블렌드 활성.
            return ClassicalSearchConf(
                max_branch=8, max_search_steps=1000000, depth_limit=30,
                timeout=timeout, beam_decode=True, initial_proof=None,
                use_memo=True, value_weight=1.0,
                qed_ckpt="models/qed_value/qed.pt",
            )

        case "rango-qed-sum" | "rango-qed-min":
            # QED ablation: AND backup을 product 대신 sum/min으로 (effectiveness study).
            return ClassicalSearchConf(
                max_branch=8, max_search_steps=1000000, depth_limit=30,
                timeout=timeout, beam_decode=True, initial_proof=None,
                use_memo=True, value_weight=1.0,
                qed_ckpt="models/qed_value/qed.pt",
                qed_backup="sum" if model_alias == "rango-qed-sum" else "min",
            )

        case "rango-qed-hybrid":
            # 사용자 요청: QEDCartographer 탐색 + retrieval 확신 높으면 rango greedy 혼용.
            #   qed value(product backup)로 순서화 + 확신 스텝은 boost로 depth-first commit.
            return ClassicalSearchConf(
                max_branch=8, max_search_steps=1000000, depth_limit=30,
                timeout=timeout, beam_decode=True, initial_proof=None,
                use_memo=True, value_weight=1.0,
                qed_ckpt="models/qed_value/qed.pt",
                hybrid_conf=True, conf_threshold=-0.05,
            )

        case "rango-hybrid":
            # MR-Hybrid: retrieval-신뢰도(모델 top log-prob) 게이팅 adaptive-width best-first.
            # 확신↑ → greedy(rango 기법), 확신↓ → width8 탐색. use_memo로 중복 방지.
            return ClassicalSearchConf(
                max_branch=8, max_search_steps=1000000, depth_limit=30,
                timeout=timeout, beam_decode=True, initial_proof=None,
                use_memo=True, hybrid_conf=True, conf_threshold=-0.05,
            )

        case "rango-hybrid-v":
            # MR-Hybrid + MR1 value: 불확신 구간을 학습된 value로 정렬.
            return ClassicalSearchConf(
                max_branch=8, max_search_steps=1000000, depth_limit=30,
                timeout=timeout, beam_decode=True, initial_proof=None,
                use_memo=True, hybrid_conf=True, conf_threshold=-0.05,
                value_ckpt="models/value_head/value.pt", value_weight=1.0,
            )

        case "rango-hprobe":
            return PortfolioSearchConf(
                straight_conf=StraightLineSearcherConf(
                    timeout=timeout, print_proofs=True, initial_proof=None, token_mask=None,
                ),
                classical_conf=ClassicalSearchConf(
                    max_branch=8, max_search_steps=1000000, depth_limit=30,
                    timeout=timeout, beam_decode=True, initial_proof=None, use_memo=True,
                ),
                timeout=timeout, straight_frac=0.8,
                phase2_mode="straight", probe_cap=90,
            )

        case "rango-portfolio" | "rango-portfolio-08" | "rango-portfolio-06":
            # straight-line → 실패시 classical-mem. union 노림. straight_frac 변형.
            frac = {"rango-portfolio": 0.7, "rango-portfolio-08": 0.8,
                    "rango-portfolio-06": 0.6}[model_alias]
            return PortfolioSearchConf(
                straight_conf=StraightLineSearcherConf(
                    timeout=timeout, print_proofs=True,
                    initial_proof=None, token_mask=None,
                ),
                classical_conf=ClassicalSearchConf(
                    max_branch=8, max_search_steps=1000000, depth_limit=30,
                    timeout=timeout, beam_decode=True, initial_proof=None,
                    use_memo=True,
                ),
                timeout=timeout,
                straight_frac=frac,
            )

        case _:
            return straight_line_conf


def get_prefix_conf(model_alias: str, split: Split) -> TacticGenConf:
    assert model_alias == "prefix" or model_alias == "hybrid"
    model_loc = Path("models/deepseek-prefix-final")
    checkpoint = model_loc / "checkpoint-61000"
    checkpoint_loc = Path(checkpoint)

    match split:
        case Split.TEST:
            shutil.copy(
                model_loc / "test_conf.yaml",
                model_loc / "training_conf.yaml",
            )
        case Split.CUTOFF:
            shutil.copy(
                model_loc / "cutoff_conf.yaml",
                model_loc / "training_conf.yaml",
            )
        case Split.VAL:
            raise ValueError("Not supported in artifact. Doesn't appear in the paper.")

    formatter = GeneralFormatterConf(
        premise_client_conf=None,
        proof_retriever_conf=None,
        num_premises=None,
        num_proofs=None,
    )
    return DecoderTacticGenConf(Path(checkpoint), [formatter])


def get_tactic_confs(model_alias: str, split: Split) -> list[TacticGenConf]:
    data_loc = get_data_loc(split)
    sentence_db_loc = get_sentence_db_loc(split)

    tfidf_premise_conf = SparseConf(
        kind=SparseKind.TFIDF,
        context_format_alias="basic",
        premise_format_alias="basic",
        premise_filter_conf=PROJ_THM_FILTER_CONF,
        sentence_db_loc=sentence_db_loc,
        cached_premise_loc=None,
    )

    bm25_proof_conf = SparseProofRetrieverConf(
        kind="bm25",
        max_examples=20,
        data_loc=data_loc,
        sentence_db_loc=sentence_db_loc,
        cached_proof_loc=None,
        first_step_only=False,
    )

    match model_alias:
        case "rango" | "rango-best-beam" | "rango-best-rand" | "rango-mem" | "rango-mem-wide" | "rango-portfolio" | "rango-portfolio-08" | "rango-portfolio-06" | "rango-vlog" | "rango-vguided" | "rango-hybrid" | "rango-hybrid-v" | "rango-qed" | "rango-qed-hybrid" | "rango-qed-sum" | "rango-qed-min" | "rmaxts" | "rmaxts-noreward" | "rmaxts-nomerge" | "rmaxts-nomcts" | "bfs-prover" | "bfs-a0" | "bfs-a1" | "bfs-prover-trace" | "grpo-rollout" | "quarry" | "quarry-heur" | "quarry-trace":
            checkpoint = (
                "models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500"
            )
            formatter = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf,
                proof_retriever_conf=bm25_proof_conf,
                num_premises=50,
                num_proofs=20,
            )
            return [DecoderTacticGenConf(Path(checkpoint), [formatter])]

        case "rango-6.7b":
            # 헤비 레버 1: raw DeepSeek-Coder-6.7B-instruct(LoRA 미적용) + 동일 Rango 프롬프트.
            # 모델 용량이 진짜 레버인지 검증(구조형 하드코어 겨냥).
            formatter = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf,
                proof_retriever_conf=bm25_proof_conf,
                num_premises=50,
                num_proofs=20,
            )
            return [DecoderTacticGenConf(Path("models/rango-6.7b/base"), [formatter])]

        case "rango-6.7b-ft":
            # 헤비 레버 2: Rango 데이터로 QLoRA 파인튜닝한 6.7B (device2에서 학습).
            # 순수 capacity 판정용(포맷 학습됨 + 큰 용량). ckpt=models/rango-6.7b-ft/final(심링크).
            formatter = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf,
                proof_retriever_conf=bm25_proof_conf,
                num_premises=50,
                num_proofs=20,
            )
            return [DecoderTacticGenConf(Path("models/rango-6.7b-ft/final"), [formatter])]

        case "rango-divsample":
            # (A1 개선) 같은 강한 rango 모델에서 retrieval on/off 토글(ensemble의
            # 약한 2nd모델 문제 회피). straight-line이 두 client(동일 checkpoint,
            # retrieval-on formatter / retrieval-off formatter)를 재시도마다 번갈아.
            ck = "models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500"
            on_fmt = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf,
                proof_retriever_conf=bm25_proof_conf,
                num_premises=50,
                num_proofs=20,
            )
            off_fmt = GeneralFormatterConf(
                premise_client_conf=None,
                proof_retriever_conf=None,
                num_premises=None,
                num_proofs=None,
            )
            return [
                DecoderTacticGenConf(Path(ck), [on_fmt]),
                DecoderTacticGenConf(Path(ck), [off_fmt]),
            ]

        case "rango-ensemble":
            # (3) retrieval 과의존 보완: straight-line이 retrieval-finetune과
            # no-retrieval-finetune(basic-ablation)을 재시도마다 번갈아 사용.
            rango_fmt = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf,
                proof_retriever_conf=bm25_proof_conf,
                num_premises=50,
                num_proofs=20,
            )
            noretr_fmt = GeneralFormatterConf(
                premise_client_conf=None,
                proof_retriever_conf=None,
                num_premises=None,
                num_proofs=None,
            )
            return [
                DecoderTacticGenConf(
                    Path("models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500"),
                    [rango_fmt],
                ),
                DecoderTacticGenConf(
                    Path("models/deepseek-basic-ablation/checkpoint-37500"),
                    [noretr_fmt],
                ),
            ]

        case "rango-sauto":
            # retrieval-guided hammer: top premise를 sauto use:로 먹임 (coq-hammer-tactics)
            checkpoint = (
                "models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500"
            )
            formatter = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf,
                proof_retriever_conf=bm25_proof_conf,
                num_premises=50,
                num_proofs=20,
                sauto_hint=True,
            )
            return [DecoderTacticGenConf(Path(checkpoint), [formatter])]

        case "rango-psauto":
            # portfolio: phase1 plain straight-line(강함) + phase2 sauto fallback client
            ck = "models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500"
            plain_fmt = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf, proof_retriever_conf=bm25_proof_conf,
                num_premises=50, num_proofs=20,
            )
            sauto_fmt = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf, proof_retriever_conf=bm25_proof_conf,
                num_premises=50, num_proofs=20, sauto_hint=True,
            )
            return [DecoderTacticGenConf(Path(ck), [plain_fmt]),
                    DecoderTacticGenConf(Path(ck), [sauto_fmt])]

        case "rango-hprobe":
            # 값싼 sauto probe(앞 90s) + full straight-line(plain, 나머지 전부).
            # 예산 분할 없이 straight-line에 거의 전부 → 회귀0 + sauto 보너스만.
            ck = "models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500"
            plain_fmt = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf, proof_retriever_conf=bm25_proof_conf,
                num_premises=50, num_proofs=20,
            )
            sauto_fmt = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf, proof_retriever_conf=bm25_proof_conf,
                num_premises=50, num_proofs=20, sauto_hint=True,
            )
            return [DecoderTacticGenConf(Path(ck), [plain_fmt]),
                    DecoderTacticGenConf(Path(ck), [sauto_fmt])]

        case "rango-search":
            # built-in premise: Coq Search로 stdlib lemma 찾아 sauto use: (사용자 아이디어)
            checkpoint = (
                "models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500"
            )
            formatter = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf,
                proof_retriever_conf=bm25_proof_conf,
                num_premises=50,
                num_proofs=20,
                sauto_hint=True,
                search_hint=True,
            )
            return [DecoderTacticGenConf(Path(checkpoint), [formatter])]

        case "rango-alignapply":
            # 조합: align 힌트 + apply 강제 (classical+memo)
            checkpoint = (
                "models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500"
            )
            formatter = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf,
                proof_retriever_conf=bm25_proof_conf,
                num_premises=50,
                num_proofs=20,
                align_hint=True,
                apply_hint=True,
            )
            return [DecoderTacticGenConf(Path(checkpoint), [formatter])]

        case "rango-align":
            # M3(C1): straight-line + retrieval sibling의 aligned 다음 tactic을 프롬프트 힌트로
            checkpoint = (
                "models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500"
            )
            formatter = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf,
                proof_retriever_conf=bm25_proof_conf,
                num_premises=50,
                num_proofs=20,
                align_hint=True,
            )
            return [DecoderTacticGenConf(Path(checkpoint), [formatter])]

        case "rango-apply" | "rango-apply-sl":
            # M4'/변형: 좋은 premise면 apply/eapply/exploit 강제 후보 (classical 또는 straight-line multi-cand)
            checkpoint = (
                "models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500"
            )
            formatter = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf,
                proof_retriever_conf=bm25_proof_conf,
                num_premises=50,
                num_proofs=20,
                apply_hint=True,
            )
            return [DecoderTacticGenConf(Path(checkpoint), [formatter])]

        case "rango-inter-file":
            checkpoint = (
                "models/deepseek-bm25-proof-tfidf-proj-thm-prem-random/checkpoint-54000"
            )
            formatter = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf,
                proof_retriever_conf=bm25_proof_conf,
                num_premises=50,
                num_proofs=20,
            )
            return [DecoderTacticGenConf(Path(checkpoint), [formatter])]

        case "no-lemma":
            checkpoint = "models/deepseek-bm25-proof-final/checkpoint-56500"
            formatter = GeneralFormatterConf(
                premise_client_conf=None,
                proof_retriever_conf=bm25_proof_conf,
                num_premises=None,
                num_proofs=20,
            )
            return [DecoderTacticGenConf(Path(checkpoint), [formatter])]

        case "no-lemma-inter-file":
            checkpoint = "models/deepseek-bm25-proof-random/checkpoint-54000"
            formatter = GeneralFormatterConf(
                premise_client_conf=None,
                proof_retriever_conf=bm25_proof_conf,
                num_premises=None,
                num_proofs=20,
            )
            return [DecoderTacticGenConf(Path(checkpoint), [formatter])]

        case "no-proof":
            checkpoint = "models/deepseek-tfidf-proj-thm-prem-final/checkpoint-51500"
            formatter = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf,
                proof_retriever_conf=None,
                num_premises=50,
                num_proofs=None,
            )
            return [DecoderTacticGenConf(Path(checkpoint), [formatter])]

        case "no-proof-inter-file":
            checkpoint = "models/deepseek-tfidf-proj-thm-prem-random/checkpoint-54000"
            formatter = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf,
                proof_retriever_conf=None,
                num_premises=50,
                num_proofs=None,
            )
            return [DecoderTacticGenConf(Path(checkpoint), [formatter])]

        case "no-retrieval":
            checkpoint = "models/deepseek-basic-ablation/checkpoint-37500"
            formatter = GeneralFormatterConf(
                premise_client_conf=None,
                proof_retriever_conf=None,
                num_premises=None,
                num_proofs=None,
            )
            return [DecoderTacticGenConf(Path(checkpoint), [formatter])]

        case "no-retrieval-inter-file":
            checkpoint = "models/deepseek-basic-ablation-random/checkpoint-53500"
            formatter = GeneralFormatterConf(
                premise_client_conf=None,
                proof_retriever_conf=None,
                num_premises=None,
                num_proofs=None,
            )
            return [DecoderTacticGenConf(Path(checkpoint), [formatter])]

        case "first-step":
            checkpoint = "models/deepseek-bm25-first-step-proof-tfidf-proj-thm-prem-final/checkpoint-56000"
            first_step_proof_conf = SparseProofRetrieverConf(
                kind="bm25",
                max_examples=20,
                data_loc=data_loc,
                sentence_db_loc=sentence_db_loc,
                cached_proof_loc=None,
                first_step_only=True,
            )
            formatter = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf,
                proof_retriever_conf=first_step_proof_conf,
                num_premises=50,
                num_proofs=20,
            )
            return [DecoderTacticGenConf(Path(checkpoint), [formatter])]

        case "tfidf-proof":
            checkpoint = "models/deepseek-proof-prem-final/checkpoint-45500"
            tfidf_proof_conf = SparseProofRetrieverConf(
                kind="tfidf",
                max_examples=20,
                data_loc=data_loc,
                sentence_db_loc=sentence_db_loc,
                cached_proof_loc=None,
                first_step_only=False,
            )
            formatter = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf,
                proof_retriever_conf=tfidf_proof_conf,
                num_premises=50,
                num_proofs=20,
            )
            return [DecoderTacticGenConf(Path(checkpoint), [formatter])]

        case "codebert-proof":
            checkpoint = "models/deepseek-codebert-proof-tfidf-proj-thm-prem-final/checkpoint-57500"
            codebert_proof_conf = DeepProofRetrieverConf(
                model_name="microsoft/codebert-base",
                vector_db_loc=Path("data/test-codebert-proof-state-vector-db"),
                max_seq_len=512,
                max_num_proofs=20,
                data_loc=data_loc,
                sentence_db_loc=sentence_db_loc,
                first_step_only=False,
            )
            formatter = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf,
                proof_retriever_conf=codebert_proof_conf,
                num_premises=50,
                num_proofs=20,
            )
            return [DecoderTacticGenConf(Path(checkpoint), [formatter])]

        case "prefix":
            return [get_prefix_conf(model_alias, split)]

        case "hybrid":
            prefix_conf = get_prefix_conf(model_alias, split)
            rango_checkpoint = (
                "models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500"
            )
            rango_formatter = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf,
                proof_retriever_conf=bm25_proof_conf,
                num_premises=50,
                num_proofs=20,
            )
            rango_conf = DecoderTacticGenConf(Path(rango_checkpoint), [rango_formatter])
            return [rango_conf, prefix_conf]

        case _:
            raise ValueError(f"Unknown model alias {model_alias}.")


def get_test_proof(model_alias: str, split: Split, idx: int) -> TestProofConf:
    eval_thm = get_eval_thm(split, idx)
    data_loc = get_data_loc(split)
    sentence_db_loc = get_sentence_db_loc(split)
    searcher_conf = get_searcher_conf(model_alias)
    tactic_confs = get_tactic_confs(model_alias, split)
    return TestProofConf(
        eval_thm,
        COQSTOQ_LOC,
        data_loc,
        sentence_db_loc,
        searcher_conf,
        tactic_confs,
        True,
        False,
    )


def get_results_loc(model_alias: str) -> list[Path]:
    results_locs = {
        "rango": [
            Path("results/rango.json"),
            Path("results/rango-cutoff.json"),
        ],
        "rango-inter-file": [
            Path("results/rango-abl-intersect-random.json"),
        ],
        "rango-best-beam": [
            Path("results/rango-abl-best-first-beam.json"),
        ],
        "rango-best-rand": [
            Path("results/rango-abl-best-first-temp.json"),
        ],
        "no-lemma": [
            Path("results/rango-abl-no-lemmas.json"),
            Path("results/rango-abl-intersect-no-lemma-final.json"),
        ],
        "no-lemma-inter-file": [
            Path("results/rango-abl-intersect-no-lemma-random.json"),
        ],
        "no-proof": [
            Path("results/rango-abl-no-proofs.json"),
            Path("results/rango-abl-intersect-no-proofs-final.json"),
        ],
        "no-proof-inter-file": [
            Path("results/rango-abl-intersect-no-proofs-random.json"),
        ],
        "no-retrieval": [
            Path("results/rango-abl-no-retrieval.json"),
            Path("results/rango-abl-intersect-no-retrieval-final.json"),
        ],
        "no-retrieval-inter-file": [
            Path("results/rango-abl-intersect-no-retrieval-random.json"),
        ],
        "first-step": [Path("results/rango-abl-first-step.json")],
        "tfidf-proof": [Path("results/rango-abl-tfidf.json")],
        "codebert-proof": [Path("results/rango-abl-codebert.json")],
        "prefix": [
            Path("results/rango-abl-prefix.json"),
            Path("results/rango-abl-prefix-cutoff.json"),
        ],
        "hybrid": [
            Path("results/rango-abl-prefix-hybrid.json"),
            Path("results/rango-abl-prefix-hybrid-cutoff.json"),
        ],
    }
    if model_alias not in results_locs:
        raise ValueError(f"No results found for {model_alias}.")
    return results_locs[model_alias]


def get_result(model_alias: str, thm: EvalTheorem) -> Result:
    results_locs = get_results_loc(model_alias)
    for results_loc in results_locs:
        with open(results_loc) as f:
            eval_data = json.load(f)
            results = EvalResults.from_json(eval_data)
            assert len(results.results)
        for r in results.results:
            if r.thm == thm:
                return r
    raise ValueError(f"Do not have a results for {model_alias}")


def get_orig_result(model_alias: str, split: Split, idx: int) -> Result:
    thm = get_theorem(split, idx, COQSTOQ_LOC)
    try:
        return get_result(model_alias, thm)
    except ValueError:
        # 새로 만든 alias(rango-mem 등)는 결과 json이 없으므로 rango 기준으로 대체
        return get_result("rango", thm)


def print_info():
    print("Table 2:")
    print("  rango")
    print()
    print("Table 3:")
    print("  rango")
    print()
    print("Table 4:")
    print("  rango")
    print("  no-lemma")
    print("  no-proof")
    print("  no-retrieval")
    print()
    print("Table 5:")
    print("  rango")
    print("  rango-inter-file")
    print("  no-lemma")
    print("  no-lemma-inter-file")
    print("  no-proof")
    print("  no-proof-inter-file")
    print("  no-retrieval")
    print("  no-retrieval-inter-file")
    print()
    print("Table 6:")
    print("  rango")
    print("  tfidf-proof")
    print("  codebert-proof")
    print()
    print("Table 7:")
    print("  rango")
    print("  prefix")
    print("  hybrid")
    print()
    print("Table 8:")
    print("  rango")
    print("  rango-best-beam")
    print("  rango-best-rand")
    exit()


def print_result(theorem_list: list[EvalTheorem], result: Result):
    idx = theorem_list.index(result.thm)
    success_str = "Success" if result.proof is not None else "Failure"
    t = result.time
    assert t is not None
    print("{:6d}; {:7s}; {:5.1f}".format(idx, success_str, t))
    # print("{:3d}; {:7s}; {:04.1f}".format(idx, success_str, t))
    # print(f"{idx:3d}; {success_str:7s}; {t:4.1f}")


def print_avail_thms(alias: str, split: Split):
    results_locs = get_results_loc(alias)
    PRINT_NUM = 50
    num_printed = 0
    thms = get_theorem_list(split, COQSTOQ_LOC)
    for results_loc in results_locs:
        with results_loc.open("r") as fin:
            results_data = json.load(fin)
            results = EvalResults.from_json(results_data)
            for r in results.results:
                if r.thm.project.split != split.value:
                    continue
                print_result(thms, r)
                num_printed += 1
                if num_printed == PRINT_NUM:
                    return


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(dest="command")

    preview_parser = subparsers.add_parser("preview")
    preview_parser.add_argument("alias")
    preview_parser.add_argument("split")

    info_parser = subparsers.add_parser("info")

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("alias")
    run_parser.add_argument("split")
    run_parser.add_argument("idx", type=int)
    run_parser.add_argument(
        "--timeout", type=int, default=600,
        help="search 제한 시간(초). 미지정 시 기본값 600.",
    )

    eval_parser = subparsers.add_parser("eval")
    eval_parser.add_argument("alias")
    eval_parser.add_argument("split")
    eval_parser.add_argument(
        "--timeout", type=int, default=600,
        help="search 제한 시간(초). 미지정 시 기본값 600.",
    )

    args = parser.parse_args()
    if getattr(args, "alias", None) in ("rango-sauto", "rango-repair", "rango-search", "rango-psauto", "rango-hprobe"):
        os.environ["RANGO_HAMMER_PREAMBLE"] = "1"
    if args.command == "info":
        print_info()
        exit()

    elif args.command == "preview":
        coqstoq_split = str2split(args.split)
        print_avail_thms(args.alias, coqstoq_split)
        exit()

    assert args.command == "run" or args.command == "eval"
    coqstoq_split = str2split(args.split)

    if args.command == "run":
        conf = get_test_proof(args.alias, coqstoq_split, args.idx)
        print(conf.thm.project.dir_name, conf.thm.path)
        orig_result = get_orig_result(args.alias, coqstoq_split, args.idx)
        print("Original Proof:")
        print(orig_result.proof)
        print("Original Time:")
        print(orig_result.time)
        # rango.json(published Rango) 기준 성공 여부 — 실행 alias와 무관하게 항상 rango
        try:
            _rango_ref = get_result("rango", conf.thm)
            print(f"RANGO_JSON_SUCCESS: {_rango_ref.proof is not None}")
        except Exception as _e:
            print(f"RANGO_JSON_SUCCESS: unknown ({_e})")
    else:
        assert args.command == "eval"
        conf = get_test_proof(args.alias, coqstoq_split, 0)

    # search 제한 시간 덮어쓰기 (미지정 시 default 600)
    conf.search_conf.timeout = args.timeout
    print(f"[search timeout] {conf.search_conf.timeout}s")

    # Example: 37
    print("\n\n Loading model...")
    clean_tactic_confs: list[TacticGenConf] = []
    all_commands: list[StartModelCommand] = []
    next_num = 0
    for tactic_conf in conf.tactic_confs:
        clean_tactic_conf, n_commands, commands = tactic_gen_to_client_conf(
            tactic_conf, next_num
        )
        all_commands.extend(commands)
        clean_tactic_confs.append(clean_tactic_conf)
        next_num = n_commands

    procs = []
    if 0 < len(all_commands):
        clear_port_map()
        procs = start_servers(all_commands)
        port_map = wait_for_servers(next_num)
        for tactic_conf in clean_tactic_confs:
            tactic_conf_update_ips(tactic_conf, port_map)

    conf.tactic_confs = clean_tactic_confs

    if args.command == "run":
        orig_result = get_orig_result(args.alias, coqstoq_split, args.idx)
        try:
            result = run_proof(conf.to_run_conf())
            match result:
                case ClassicalSuccess():
                    print(
                        f"\n\n ORIGINAL RESULT: {'SUCCESS' if orig_result.proof is not None else 'FAILURE'}"
                    )
                    print(f"ORIGINAL TIME: {orig_result.time}")
                    print(f"ORIGINAL PROOF: {orig_result.proof}")
                    print("CURRENT RESULT: SUCCESS")
                    print(f"CURRENT TIME: {result.time}")
                    print(f"CURRENT PROOF:")
                    print(result.successful_candidate.proof_str)

                case ClassicalFailure():
                    print("failed")
                case StraightLineSuccess():
                    print(
                        f"\n\nORIGINAL RESULT: {'SUCCESS' if orig_result.proof is not None else 'FAILURE'}"
                    )
                    print(f"ORIGINAL TIME: {orig_result.time}")
                    print(f"ORIGINAL PROOF: {orig_result.proof}")
                    print("CURRENT RESULT: SUCCESS")
                    print(f"CURRENT TIME: {result.time}")
                    print(f"CURRENT PROOF:")
                    print(result.successful_proof.proof_text_to_string())

                case StraightLineFailure():
                    print("failed")
                case WholeProofSuccess():
                    print(result.successful_proof.proof_text_to_string())
                case WholeProofFailure():
                    print("failed")
        finally:
            for p in procs:
                p.kill()

    else:
        assert args.command == "eval"
        theorem_list = get_theorem_list(coqstoq_split, COQSTOQ_LOC)
        results: list[Result] = []
        try:
            for thm in theorem_list[37:]:
                thm_conf = TestProofConf(
                    thm,
                    conf.coqstoq_loc,
                    conf.data_loc,
                    conf.sentence_db_loc,
                    conf.search_conf,
                    conf.tactic_confs,
                    conf.print_proofs,
                    conf.print_trees,
                )
                search_result = run_proof(thm_conf.to_run_conf())
                result = RangoResult.from_search_result(thm, search_result)
                results.append(result)
        finally:
            for p in procs:
                p.kill()
