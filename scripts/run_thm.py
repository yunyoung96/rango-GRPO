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
from model_deployment.pgts_searcher import PGTSSearchConf
from model_deployment.progress_searcher import ProgressSearchConf
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
    # ★ GOLD_PREFIX: gold 증명의 앞부분을 **정답으로 채운 채** 나머지를 풀게 한다.
    #   표류(drift)를 제거하고 "남은 부분을 조합할 수 있는가"만 분리해서 재기 위함.
    #   미설정이면 기존과 동일(None).
    _gp = os.environ.get("GOLD_PREFIX") or None
    straight_line_conf = StraightLineSearcherConf(
        timeout=timeout,
        print_proofs=True,
        initial_proof=_gp,
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

        case "rmaxts" | "rango-grpo-rmaxts":
            # RMaxTS 탐색(full). DUCB + RMax reward + truncate-resume + state merging.
            # rango-grpo-rmaxts = GRPO 학습 정책 + RMaxTS(DeepSeek-Prover-V1.5 정식 full 구성).
            return RMaxTSSearchConf(timeout=timeout, n_rollout_steps=8, print_proofs=True)
        case "rmaxts-noreward":  # ablation: RMax intrinsic reward 제거
            return RMaxTSSearchConf(timeout=timeout, print_proofs=True, use_reward=False)
        case "rmaxts-nomerge":   # ablation: state-merging 제거(pure tree)
            return RMaxTSSearchConf(timeout=timeout, print_proofs=True, use_merge=False)
        case "rmaxts-nomcts":    # ablation: DUCB 제거(uniform 랜덤 선택)
            return RMaxTSSearchConf(timeout=timeout, print_proofs=True, use_ducb=False)

        case "bfs-prover" | "bfs-dpo":  # BFS-Prover length-normalized best-first, α=0.5(논문)
            return BFSProverSearchConf(timeout=timeout, alpha=0.5, expand_width=2, print_proofs=True)
        case "bfs-prover-trace":  # BFS-Prover + 트리 덤프(expert-iter/DPO 학습 데이터 수집)
            return BFSProverSearchConf(
                timeout=timeout, alpha=0.5, expand_width=2, print_proofs=True,
                trace_out="data/bfs_trees/trees.jsonl",
            )
        case "bfs-a0":           # ablation: length-norm 제거(α=0, 순수 누적 log-prob)
            return BFSProverSearchConf(timeout=timeout, alpha=0.0, expand_width=2, print_proofs=True)
        case "bfs-a1" | "rango-grpo-bfs":  # ablation: full length-norm(α=1.0, per-tactic 평균)
            # rango-grpo-bfs = GRPO 학습 정책 + 최고 탐색(BFS α=1.0) 결합.
            return BFSProverSearchConf(timeout=timeout, alpha=1.0, expand_width=2, print_proofs=True)

        # ── Planner–Executor (PLANNER_EXECUTOR_DESIGN.md): 강한 로컬 planner가 분해 제안,
        #    우리 1.3B(executor)+coq-lsp가 실행. dense 채점(MC 금지). GPU1 단독(CVD=1→cuda:0).
        case "rango-planner":            # Qwen2.5-Coder-7B planner (bf16, ~15GB — 32B는 tf5.1 4bit로더 버그로 OOM)
            # PLANNER_URL 설정 시 persistent planner_server 사용(정리 재로드 방지, w2 가능).
            return BFSProverSearchConf(
                timeout=timeout, alpha=0.5, expand_width=4, print_proofs=True,
                use_planner=True, planner_model="Qwen/Qwen2.5-Coder-7B-Instruct",
                planner_4bit=False, planner_device="cuda:0", plan_bonus=500.0,
                planner_url=os.environ.get("PLANNER_URL"), plan_budget=8,  # 32B 속도위해 정리당 호출 20→8
            )
        case "rango-planner-6b":         # 6.7B planner (로컬, 배관 스모크)
            return BFSProverSearchConf(
                timeout=timeout, alpha=0.5, expand_width=4, print_proofs=True,
                use_planner=True, planner_model="deepseek-ai/deepseek-coder-6.7b-instruct",
                planner_4bit=True, planner_device="cuda:0", plan_bonus=500.0,
            )
        case "rango-vfsearch":           # value-free MC(대조/ablation, 17% 붕괴 확인용)
            return BFSProverSearchConf(
                timeout=timeout, alpha=0.5, expand_width=4, print_proofs=True,
                use_vfsearch=True, mc_K=4, mc_D=6,
            )

        case "grpo-rollout" | "grpo-rollout-cur":
            # GRPO rollout 수집(binary reward). cur=커리큘럼(run_all --idx-file로 정리 선택).
            return GRPORolloutSearchConf(
                timeout=timeout, group_size=8, max_steps=20,
                out="data/grpo_rollouts/rollouts.jsonl",
            )
        case "grpo-rollout-pf":
            # ★ planner-first 실험(dead group 축소): 32B가 opening 분해, 이후 rango.
            #   PLANNER_FIRST_URL env 설정 시 opening 주입(grpo_rollout.rollout_attempt). out/retry는 env로.
            import os as _os
            return GRPORolloutSearchConf(
                timeout=timeout, group_size=8, max_steps=20,
                max_retries=int(_os.environ.get("ROLLOUT_RETRY", "1")),
                out=_os.environ.get("ROLLOUT_OUT", "data/grpo_rollouts/planner_first.jsonl"),
            )
        # ⚠️ 아래 alias 들의 out 경로는 **서로 달라야 한다**. 예전에 전부 rollouts.jsonl 을 공유해
        #   E3 수집이 round-1 원본을 덮어썼다(md5 동일 확인). GRPO_ROLLOUT_ANALYSIS.md §0 참조.
        case "grpo-rollout-dense":
            # (E2) dense reward: 미완 시도에 QED value 부분보상 → 성긴 신호 완화.
            return GRPORolloutSearchConf(
                timeout=timeout, group_size=8, max_steps=20,
                out="data/grpo_rollouts/E2-dense.jsonl",
                qed_ckpt="models/qed_value/qed.pt", shaping_coef=0.3,
            )
        case "grpo-rollout-g16":
            # (E4) scale: G=16 샘플 → 신호 절대량↑.
            return GRPORolloutSearchConf(
                timeout=timeout, group_size=16, max_steps=20,
                out="data/grpo_rollouts/E4-g16.jsonl",
            )
        case "grpo-rollout-r2":
            # (E1) expert-iteration: round-1 GRPO adapter 정책으로 재-rollout.
            return GRPORolloutSearchConf(
                timeout=timeout, group_size=8, max_steps=20,
                out="data/grpo_rollouts/E1-r2.jsonl",
            )
        case "pgts":
            # PGTS(2604.24354) FULL: bfs-a1(우리 최강 탐색) + tactic-pattern 재랭킹 + 기호적 가지치기.
            # 베이스가 bfs-a1(α=1.0, 16/40)이라 bfs-a1 대비 순수 delta가 이 기법의 기여분.
            return PGTSSearchConf(
                timeout=timeout, alpha=1.0, beta=0.5, expand_width=2,
                pattern_db="data/tactic_patterns/patterns.json",
                use_failure_dict=True, use_no_progress_filter=True, print_proofs=True,
            )
        case "pgts-sym":
            # ablation: 패턴 재랭킹 제거(β=0) → 기호적 가지치기(failure dict + no-progress)만의 기여.
            return PGTSSearchConf(
                timeout=timeout, alpha=1.0, beta=0.0, expand_width=2, pattern_db=None,
                use_failure_dict=True, use_no_progress_filter=True, print_proofs=True,
            )
        case "pgts-pat":
            # ablation: 기호적 가지치기 제거 → tactic-pattern 재랭킹만의 기여.
            return PGTSSearchConf(
                timeout=timeout, alpha=1.0, beta=0.5, expand_width=2,
                pattern_db="data/tactic_patterns/patterns.json",
                use_failure_dict=False, use_no_progress_filter=False, print_proofs=True,
            )

        case "rango-progress" | "rango-progress-a05" | "rango-progress-a10" | "rango-progress-a0":
            # LeanProgress(2502.17925): progress critic(남은 스텝 수) 를 logprob 과 블렌드.
            #   α sweep — 논문은 0.2 최적, α=1.0(순수 value) 는 18.5% 로 붕괴한다고 보고.
            #   우리 rango-qed(-1) 가 value 로 랭킹해서 죽은 것과 같은 함정 → α 를 직접 쓸어 확인한다.
            #   α=0 은 bfs-a1 과 순위가 동일해야 한다(정규화 sanity check).
            a = {"rango-progress": 0.2, "rango-progress-a05": 0.5,
                 "rango-progress-a10": 1.0, "rango-progress-a0": 0.0}[model_alias]
            return ProgressSearchConf(
                timeout=timeout, alpha=a, expand_width=2, print_proofs=True,
                critic_dir="models/progress_critic",
            )

        case "grpo-rollout-e1fix":
            # E1(expert-iter) 재검증: round-1 = rango-grpo-fix(정정본) 정책으로 재롤아웃 → 재학습.
            return GRPORolloutSearchConf(
                timeout=timeout, group_size=8, max_steps=20,
                out="data/grpo_rollouts/e1fix.jsonl",
            )

        case "grpo-rollout-scale":
            # ★ CompCert 내부 학습셋 확대(40→200). 재샘플링 없음(k=0) — rango-grpo 와 유일한 차이가
            #   '학습셋 크기'뿐이 되게. --idx-file data/compcert_scale_idx.txt (cc[200:400]).
            return GRPORolloutSearchConf(
                timeout=timeout, group_size=8, max_steps=20,
                out="data/grpo_rollouts/scale.jsonl",
            )
        case "grpo-rollout-bigscale":
            # ★ 대규모 scale: CompCert 뒤 1000개로 GRPO 학습 → 앞 5091개 평가(disjoint).
            #   --idx-file data/compcert_bigscale_train_idx.txt (뒤 1000). 재샘플 k=0.
            return GRPORolloutSearchConf(
                timeout=timeout, group_size=8, max_steps=20,
                out="data/grpo_rollouts/bigscale.jsonl",
            )

        case "grpo-rollout-bigscale2":
            # ★ bigscale2: compcert 1000~1299(300개)로 GRPO 학습용 롤아웃. 원본 rango 정책, workers=2.
            #   --idx-file data/compcert_bs2_train_idx.txt. 평가는 앞 1000(disjoint).
            return GRPORolloutSearchConf(
                timeout=timeout, group_size=8, max_steps=20,
                out="data/grpo_rollouts/bigscale2.jsonl",
            )

        case "grpo-rollout-goldsft":
            # ★ gold-SFT 데이터: gold 참조증명만 replay 기록(on-policy 없음).
            #   --sft 로 이걸 학습 = rango-style SFT(외부 gold teacher forcing).
            #   GOLD_FILE/ROLLOUT_OUT env 로 커리큘럼·출력 지정(기본=bs2). t1000 등 새 split용.
            import os as _os
            return GRPORolloutSearchConf(
                timeout=timeout, group_size=1, max_steps=30, gold_only=True,
                gold_file=_os.environ.get("GOLD_FILE", "data/curriculum/gold_bs2.json"),
                out=_os.environ.get("ROLLOUT_OUT", "data/grpo_rollouts/goldsft_bs2.jsonl"),
            )

        case "grpo-rollout-bs2sft":
            # ★ SFT→GRPO on-policy(confound 수정): SFT 모델 정책으로 300개 재롤아웃 → GRPO 학습에 사용.
            #   (기존 bigscale2.jsonl 은 원본 rango 롤아웃이라 SFT 모델엔 off-policy)
            return GRPORolloutSearchConf(
                timeout=timeout, group_size=8, max_steps=20,
                out="data/grpo_rollouts/bigscale2_sft.jsonl",
            )

        case "grpo-rollout-cross":
            # ★ cross-repo 롤아웃(§10 P6): non-CompCert repo 로 학습 데이터 수집.
            #   run_all --idx-file data/crossrepo/train_idx.txt 로 대상 정리 지정.
            #   재샘플링 k=4(dead group 완화) + 경로 분리. 평가는 CompCert → sibling 누출 0.
            return GRPORolloutSearchConf(
                timeout=timeout, group_size=8, max_steps=20, max_retries=4,
                out="data/grpo_rollouts/cross.jsonl",
            )

        case "grpo-rollout-retry":
            # ★ 재샘플링 롤아웃 (GRPO_ROLLOUT_ANALYSIS.md §7 P1 처방).
            #   INVALID 는 state 를 안 바꾸므로 같은 state 에서 다시 뽑는다. 기존 롤아웃은 첫 실수에
            #   즉사했고(실패의 100%), 그게 dead group 73% 의 원인이었다.
            #   실측 p=0.815 → k=4 면 p_eff≈0.99, L=14 완주율 5.7% → 91.5%(보수 가정).
            #   비용: 스텝의 81%가 첫 샘플에 통과 → 기대 샘플수 1/p≈1.23 (≈25% 증가, 5배 아님).
            return GRPORolloutSearchConf(
                timeout=timeout, group_size=8, max_steps=20, max_retries=4,
                out="data/grpo_rollouts/retry.jsonl",
            )

        case "grpo-rollout-backward":
            # ★ Backward curriculum (sparse reward 의 구조적 해법).
            #   인간 gold 증명의 중간 상태(남은 tactic 4개)에서도 롤아웃을 돌린다.
            #   정리마다 **그룹 2개**를 만든다: s_0(처음)에서 8개, s_k(중간)에서 8개.
            #   ⚠️ 한 그룹에 섞으면 안 된다 — 그룹 평균이 V(s) baseline 이라 같은 s 에서 나와야 한다.
            #   기대: 혼합그룹(신호O) 비율 27% → 90%+ (p=0.816, remaining=4 → 98.9%).
            #   재샘플링(k=4)도 함께 켠다 — 두 처방이 곱해진다.
            return GRPORolloutSearchConf(
                timeout=timeout, group_size=8, max_steps=20, max_retries=4,
                curriculum_file="data/curriculum/backward.json",
                out="data/grpo_rollouts/backward.jsonl",
            )

        case "grpo-rollout-subgoal":
            # ★ Subgoal-first 재귀 커리큘럼 (B: deep→shallow 부트스트랩).
            #   gold 증명 트리의 decompose 노드(goal 수 증가 지점)에서 seed → 모델이 fresh subgoal 롤아웃.
            #   backward 와 같은 seeding 이지만 seed 지점이 **canonical decompose 노드**(얕고 재현가능)라
            #   배포 때 모델이 실제 도달하는 state → transfer 가능(backward 의 깊은 idiosyncratic 상태와 대비).
            #   스테이지별 curriculum/out 은 env 로 주입(run_subgoal_bigscale.sh 가 깊음→얕음 순 호출).
            return GRPORolloutSearchConf(
                timeout=timeout,
                group_size=int(os.environ.get("SUBGOAL_GS", "6")),        # 속도: 8→6
                max_steps=int(os.environ.get("SUBGOAL_MAXSTEPS", "16")),  # 속도: 20→16
                max_retries=int(os.environ.get("SUBGOAL_RETRIES", "2")),  # 속도: 4→2 (INVALID 재샘플 배수↓)
                curriculum_file=os.environ.get("SUBGOAL_CURRICULUM", "data/curriculum/subgoal.json"),
                curriculum_frac=float(os.environ.get("SUBGOAL_FRAC", "0.5")),
                out=os.environ.get("SUBGOAL_OUT", "data/grpo_rollouts/subgoal.jsonl"),
                skip_s0=(os.environ.get("SUBGOAL_SKIP_S0", "1") == "1"),   # subgoal: s0 그룹 생략(dead=낭비)
                subgoal_reward=(os.environ.get("SUBGOAL_REWARD", "0") == "1"),  # leaf-first: focused subgoal 닫힘=reward
            )

        case "grpo-rollout-adaptprefix":
            # ★ Adaptive trace prefix: revcurr 후보 중 정답률~0.5 인 prefix 를 정리별로 골라 그 그룹 수집(+s0).
            #   pass-rate 조준 커리큘럼. on-fix. curriculum=revcurr.json(모든 후보 prefix).
            return GRPORolloutSearchConf(
                timeout=timeout, group_size=8, max_steps=20, max_retries=4, probe_k=3,
                adapt_prefix=True, curriculum_file="data/curriculum/revcurr.json",
                out="data/grpo_rollouts/adaptprefix.jsonl",
            )
        case "grpo-rollout-fixdyn":
            # ★ Dynamic sampling(DAPO): dead s0 그룹을 mixed 될 때까지 재샘플(최대 4). on-policy pass-rate 제어.
            #   (8→4 로 낮춤: 5% 정리는 8회 재샘플해도 대개 헛수고 → 속도 우선.)
            return GRPORolloutSearchConf(
                timeout=timeout, group_size=8, max_steps=20, dyn_resample=4,
                out="data/grpo_rollouts/fixdyn.jsonl",
            )
        case "grpo-rollout-passk":
            # ★ pass@K 진단: fix 정책으로 정리당 K(=8)개 완증명 시도(온도샘플) → 저장.
            #   하나라도 COMPLETE 면 solved@K. jsonl 에 8시도 다 남으므로 pass@1~8 사후계산.
            #   "천장이 능력이냐 디코딩이냐" 판별용. curriculum/gold/dyn 전부 off(순수 롤아웃).
            return GRPORolloutSearchConf(
                timeout=timeout, group_size=8, max_steps=30,
                out="data/grpo_rollouts/passk.jsonl",
            )
        case "grpo-rollout-dapo":
            # ★ DAPO(2503.14476) rollout: dynamic sampling(dead s0 그룹 재샘플, dyn_resample=4).
            #   나머지 3기법(clip-higher/token-level/overlong)은 grpo_train --dapo 에서. on-fix.
            return GRPORolloutSearchConf(
                timeout=timeout, group_size=8, max_steps=20, dyn_resample=4,
                out="data/grpo_rollouts/dapo.jsonl",
            )
        case "grpo-rollout-bread":
            # ★ BREAD: on-policy 궤적 + INVALID 지점 gold 다리. gold_file 필요. on-fix.
            return GRPORolloutSearchConf(
                timeout=timeout, group_size=8, max_steps=20, max_retries=2, bread=True,
                gold_file="data/curriculum/gold.json",
                out="data/grpo_rollouts/bread.jsonl",
            )

        case "grpo-rollout-vine":
            # ★ VinePPO(2410.01679): backbone G개 + 각 on-policy state 에서 MC value(k개 분기) 추정.
            #   step별 advantage=V(s')−V(s). gold state 안 씀 → 전이문제 회피. Tree 분기로 탐색 효율.
            #   비쌈(state당 k_mc 롤아웃) → group_size 작게(4), k_mc=3, max_steps 12.
            return GRPORolloutSearchConf(
                timeout=timeout, group_size=4, max_steps=12, vine_k=3,
                out="data/grpo_rollouts/vine.jsonl",
            )

        case "grpo-rollout-revcurr":
            # ★ Reverse curriculum(전체 역행): gold 의 모든 중간상태(remaining 2~8)에서 각각 롤아웃.
            #   정리당 s_0 + 여러 curriculum 그룹(평균 ~5). 각 시작상태가 자기 baseline.
            #   fix 정책으로 수집(on-fix). all-success/all-fail 그룹은 학습때 스킵(중간밴드만 신호).
            return GRPORolloutSearchConf(
                timeout=timeout, group_size=8, max_steps=20, max_retries=4,
                curriculum_file="data/curriculum/revcurr.json",
                out=os.environ.get("ROLLOUT_OUT", "data/grpo_rollouts/revcurr.jsonl"),
                # ★ SUBGOAL_SKIP_S0=1: s0(정리 처음) 그룹 생략 → curriculum(gold subgoal 시작) 그룹만.
                #   진단(gold subgoal 닫기율)용: 커버 안 된 정리는 빠르게 건너뜀.
                skip_s0=(os.environ.get("SUBGOAL_SKIP_S0", "0") == "1"),
            )

        case "grpo-rollout-luffy":
            # ★ LUFFY (2504.14945): off-policy gold 주입으로 dead group 부활.
            #   정리마다 s_0 그룹(8개 π_old 샘플)에 **인간 gold 증명 궤적 1개**(재생·검증)를 섞는다.
            #   dead group(전부 실패)이라도 gold(r=1) 덕에 그룹 mean≠0 → advantage 신호 생성.
            #   학습 때 gold 토큰은 clip 없이 shaping f(π_θ) 으로(--luffy), on-policy 는 표준 GRPO.
            #   재샘플링(k=4)도 함께: precision 실패를 줄이면서 gold 로 정답 방향을 준다.
            return GRPORolloutSearchConf(
                timeout=timeout, group_size=8, max_steps=20, max_retries=4,
                gold_file="data/curriculum/gold.json",
                out="data/grpo_rollouts/luffy.jsonl",
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
        case "rango" | "rango-best-beam" | "rango-best-rand" | "rango-mem" | "rango-mem-wide" | "rango-portfolio" | "rango-portfolio-08" | "rango-portfolio-06" | "rango-vlog" | "rango-vguided" | "rango-hybrid" | "rango-hybrid-v" | "rango-qed" | "rango-qed-hybrid" | "rango-qed-sum" | "rango-qed-min" | "rmaxts" | "rmaxts-noreward" | "rmaxts-nomerge" | "rmaxts-nomcts" | "bfs-prover" | "bfs-a0" | "bfs-a1" | "bfs-prover-trace" | "grpo-rollout" | "grpo-rollout-cur" | "grpo-rollout-dense" | "grpo-rollout-g16" | "grpo-rollout-retry" | "grpo-rollout-cross" | "grpo-rollout-scale" | "grpo-rollout-bigscale" | "grpo-rollout-backward" | "quarry" | "quarry-heur" | "quarry-trace" | "pgts" | "pgts-sym" | "pgts-pat" | "rango-progress" | "rango-progress-a05" | "rango-progress-a10" | "rango-progress-a0":
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

        case "grpo-rollout-luffy" | "grpo-rollout-revcurr" | "grpo-rollout-vine" \
                | "grpo-rollout-adaptprefix" | "grpo-rollout-fixdyn" | "grpo-rollout-bread" \
                | "grpo-rollout-passk":
            # ★ on-fix 롤아웃: 롤아웃도 **fix 정책**으로 수집(expert-iteration).
            #   fix(base 정정 GRPO, @40 +4)가 현재 최고 정책 → 그 위에서 롤아웃/재학습.
            #   luffy=gold 주입, revcurr=전체 역행. 둘 다 fix 정책으로 수집.
            formatter = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf,
                proof_retriever_conf=bm25_proof_conf,
                num_premises=50,
                num_proofs=20,
            )
            return [DecoderTacticGenConf(Path("models/rango-grpo-fix/adapter"), [formatter])]

        case "rango-grpo" | "rango-grpo-self" | "grpo-rollout-pf" | "rango-planner" | "rango-planner-6b" | "rango-vfsearch":
            # GRPO-self: **same-project** RL — CompCert(train idx 200:240)로 학습하고 CompCert(eval 0:40)
            #   를 푼다. 탐색 rollout 기반(정답 proof 미열람)이라 SFT 누출은 아니나, 같은 프로젝트라
            #   sibling 전이 confound가 남는다(→ 향후 rango-grpo-cross 로 대비). `rango-grpo`는 구 alias(동일).
            # GRPO(DeepSeek-Prover-V1.5)로 RL fine-tune한 rango adapter + 동일 retrieval 프롬프트.
            # rango-planner* / rango-vfsearch = **executor로 이 π₀(37.5%)를 그대로** 쓰고 searcher만 다름.
            # ★ EXEC_ADAPTER env 로 executor 어댑터 교체 가능(예: leaf-subgoal 모델). 미설정 시 π₀.
            formatter = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf,
                proof_retriever_conf=bm25_proof_conf,
                num_premises=50,
                num_proofs=20,
            )
            _exec = os.environ.get("EXEC_ADAPTER", "models/rango-grpo/adapter")
            return [DecoderTacticGenConf(Path(_exec), [formatter])]

        case "rango-grpo-fix":
            # base 정정 재학습: 기존 rango-grpo 는 **base** 위에서 학습되고 **instruct** 위에 배포됐다
            #   (adapter_config 의 base_model_name_or_path = instruct, 추론 서버가 이를 따름).
            #   → 데이터생성/최적화/배포 정책이 셋 다 달랐다. instruct 로 통일해 재학습한 것.
            #   rango-grpo 와의 차이는 **베이스 모델뿐** — 알고리즘·데이터·하이퍼 동일.
            formatter = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf,
                proof_retriever_conf=bm25_proof_conf,
                num_premises=50,
                num_proofs=20,
            )
            return [DecoderTacticGenConf(Path("models/rango-grpo-fix/adapter"), [formatter])]

        case "rango-grpo-backward" | "rango-grpo-backward-prm":
            # backward curriculum 롤아웃으로 학습한 GRPO.
            formatter = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf,
                proof_retriever_conf=bm25_proof_conf,
                num_premises=50,
                num_proofs=20,
            )
            sub = "backward" if model_alias == "rango-grpo-backward" else "backward-prm"
            return [DecoderTacticGenConf(Path(f"models/rango-grpo-{sub}/adapter"), [formatter])]

        case "rango-grpo-luffy" | "rango-grpo-luffy-kl" | "rango-grpo-luffy-ch":
            # LUFFY (2504.14945): gold 주입 롤아웃(--luffy)으로 학습한 GRPO.
            #   -kl = Conservative(gold 항에 KL 복원, 회귀 방지). 롤아웃은 luffy.jsonl 공유.
            #   -ch = clip-higher(on-policy 항 상한 확대, exploration 보존). 롤아웃 공유.
            formatter = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf,
                proof_retriever_conf=bm25_proof_conf,
                num_premises=50,
                num_proofs=20,
            )
            sub = model_alias.replace("rango-grpo-", "")  # luffy / luffy-kl / luffy-ch
            return [DecoderTacticGenConf(Path(f"models/rango-grpo-{sub}/adapter"), [formatter])]

        case "rango-grpo-revcurr":
            # Reverse curriculum(전체 역행): gold 모든 중간상태 롤아웃으로 학습한 GRPO(on-fix).
            formatter = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf,
                proof_retriever_conf=bm25_proof_conf,
                num_premises=50,
                num_proofs=20,
            )
            return [DecoderTacticGenConf(Path("models/rango-grpo-revcurr/adapter"), [formatter])]

        case "rango-grpo-vine":
            # VinePPO(2410.01679): on-policy MC advantage 로 학습한 GRPO(on-fix).
            formatter = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf,
                proof_retriever_conf=bm25_proof_conf,
                num_premises=50,
                num_proofs=20,
            )
            return [DecoderTacticGenConf(Path("models/rango-grpo-vine/adapter"), [formatter])]

        case ("rango-grpo-adaptprefix" | "rango-grpo-fixdyn" | "rango-grpo-bread"
              | "rango-grpo-dapo" | "rango-grpo-revcurr-anneal"
              | "rango-grpo-rft-gold" | "rango-grpo-rft-self" | "rango-grpo-dapg"
              | "rango-grpo-bs2-sft" | "rango-grpo-bs2-sftgrpo"
              | "rango-grpo-bs2-ppo" | "rango-grpo-bs2-sftppo"
              | "rango-grpo-awac" | "rango-grpo-goldshape" | "rango-grpo-vdpo"
              | "rango-grpo-ppo-linear" | "rango-grpo-ppo-mlp" | "rango-grpo-ppo-mlp2" | "rango-grpo-ppo-tanh" | "rango-grpo-ppo-sigmoid"
              | "rango-grpo-subgoal" | "rango-grpo-subgoal-s1" | "rango-grpo-subgoal-s2"
              | "rango-grpo-subgoal-bs2" | "rango-grpo-subgoal-bs2-s1" | "rango-grpo-subgoal-bs2-s2" | "rango-grpo-subgoal-bs2-s0"
              | "rango-grpo-cascade-s1" | "rango-grpo-cascade-s2" | "rango-grpo-cascade-s3" | "rango-grpo-cascade-s0"
              | "rango-grpo-cascade-harvest" | "rango-grpo-cascade-s0r2"
              | "rango-grpo-ei-r1" | "rango-grpo-ei-r2" | "rango-grpo-ei-r3" | "rango-grpo-ei-r4"
              | "rango-grpo-dapo-small" | "rango-grpo-vapo"):
            # adaptprefix=pass-rate 조준, fixdyn=dynamic sampling, bread=gold 다리,
            # dapo=4기법 종합, revcurr-anneal=anneal-to-s0. 전부 on-fix.
            formatter = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf,
                proof_retriever_conf=bm25_proof_conf,
                num_premises=50,
                num_proofs=20,
            )
            sub = model_alias.replace("rango-grpo-", "")
            return [DecoderTacticGenConf(Path(f"models/rango-grpo-{sub}/adapter"), [formatter])]

        case s if s.startswith("rango-grpo-ei-r") or s.startswith("rango-grpo-eisafe-r") or s.startswith("rango-grpo-div"):
            # EI R5+ / 안전-EI(eisafe) 임의 라운드 자동 처리 (본문 동일)
            formatter = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf,
                proof_retriever_conf=bm25_proof_conf, num_premises=50, num_proofs=20,
            )
            sub = model_alias.replace("rango-grpo-", "")
            return [DecoderTacticGenConf(Path(f"models/rango-grpo-{sub}/adapter"), [formatter])]

        case "grpo-rollout-e1fix":
            # E1 재롤아웃 정책 = 정정된 round-1 (rango-grpo-fix)
            formatter = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf,
                proof_retriever_conf=bm25_proof_conf, num_premises=50, num_proofs=20,
            )
            return [DecoderTacticGenConf(Path("models/rango-grpo-fix/adapter"), [formatter])]

        case "rango-grpo-e2fix" | "rango-grpo-e3fix" | "rango-grpo-e4fix" | "rango-grpo-e1fix":
            # ★ sparse-mitigation 기법 재검증 (베이스 정정 후). 옛 effstudy(E1~E4)는 base 불일치
            #   버그가 있던 상태로 평가돼 전부 실패 판정. fix 가 -1→+2 로 뒤집힌 걸 보고 재검증.
            #   e2=dense reward, e3=curriculum, e4=G16 scale, e1=expert-iter(round2).
            formatter = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf,
                proof_retriever_conf=bm25_proof_conf, num_premises=50, num_proofs=20,
            )
            sub = model_alias.replace("rango-grpo-", "")  # e2fix / e3fix / ...
            return [DecoderTacticGenConf(Path(f"models/rango-grpo-{sub}/adapter"), [formatter])]

        case "rango-grpo-bigscale":
            # 대규모 scale(뒤1000 학습): 원본 rango 초기화, 앞 5091 평가.
            formatter = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf,
                proof_retriever_conf=bm25_proof_conf, num_premises=50, num_proofs=20)
            return [DecoderTacticGenConf(Path("models/rango-grpo-bigscale/adapter"), [formatter])]

        case "grpo-rollout-bigscale2" | "grpo-rollout-goldsft":
            # bigscale2/goldsft 롤아웃 정책 = 원본 rango(checkpoint-54500), straight-line.
            #   (goldsft 는 생성 안 하지만 example 빌드용 formatter/retrieval 필요 → 동일 client)
            formatter = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf,
                proof_retriever_conf=bm25_proof_conf, num_premises=50, num_proofs=20)
            return [DecoderTacticGenConf(Path("models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500"), [formatter])]

        case "grpo-rollout-bs2sft":
            # SFT→GRPO on-policy 재롤아웃 정책 = SFT 모델(bs2-sft adapter).
            formatter = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf,
                proof_retriever_conf=bm25_proof_conf, num_premises=50, num_proofs=20)
            return [DecoderTacticGenConf(Path("models/rango-grpo-bs2-sft/adapter"), [formatter])]

        case "grpo-rollout-subgoal":
            # ★ Subgoal-first 롤아웃 정책 = init 정책과 동일(on-policy). env SUBGOAL_POLICY 로 주입:
            #   게이트=models/rango-grpo-fix/adapter(fix), bigscale=checkpoint-54500(원본 rango).
            formatter = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf,
                proof_retriever_conf=bm25_proof_conf, num_premises=50, num_proofs=20)
            pol = os.environ.get("SUBGOAL_POLICY", "models/rango-grpo-fix/adapter")
            return [DecoderTacticGenConf(Path(pol), [formatter])]

        case "rango-grpo-bigscale2":
            # bigscale2 평가: compcert 300개(1000~1299)로 GRPO 학습한 adapter. 앞 1000 평가.
            formatter = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf,
                proof_retriever_conf=bm25_proof_conf, num_premises=50, num_proofs=20)
            return [DecoderTacticGenConf(Path("models/rango-grpo-bigscale2/adapter"), [formatter])]

        case "rango-grpo-scale" | "rango-grpo-scale-prm":
            # CompCert 200개로 학습한 GRPO. rango-grpo(40개) 대비 유일한 변인 = 학습셋 크기.
            #   신호그룹이 12개→대폭 늘 것으로 기대(dead group 문제 완화).
            formatter = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf,
                proof_retriever_conf=bm25_proof_conf, num_premises=50, num_proofs=20,
            )
            sub = "scale" if model_alias == "rango-grpo-scale" else "scale-prm"
            return [DecoderTacticGenConf(Path(f"models/rango-grpo-{sub}/adapter"), [formatter])]

        case "rango-grpo-cross" | "rango-grpo-cross-prm":
            # cross-repo 학습 GRPO 평가. -prm 은 process reward 추가.
            #   rango-grpo(same-project) 대비 유일한 변인 = **학습 데이터 출처**(다른 repo, 더 많음).
            formatter = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf,
                proof_retriever_conf=bm25_proof_conf,
                num_premises=50, num_proofs=20,
            )
            sub = "cross" if model_alias == "rango-grpo-cross" else "cross-prm"
            return [DecoderTacticGenConf(Path(f"models/rango-grpo-{sub}/adapter"), [formatter])]

        case "rango-grpo-retry" | "rango-grpo-retry-prm":
            # 재샘플링 롤아웃으로 학습한 GRPO.
            #   -retry     : outcome reward 만 (재샘플링의 순수 효과)
            #   -retry-prm : + process reward  (재샘플링 × PRM 결합 = 풀스택)
            formatter = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf,
                proof_retriever_conf=bm25_proof_conf,
                num_premises=50,
                num_proofs=20,
            )
            sub = "retry" if model_alias == "rango-grpo-retry" else "retry-prm"
            return [DecoderTacticGenConf(Path(f"models/rango-grpo-{sub}/adapter"), [formatter])]

        case "rango-grpo-prm":
            # PRM-GRPO(Process-Verified RL, 2606.20068): outcome reward + **coq-lsp 검증 기반
            #   per-tactic process reward**(φ: +1 증명완결 / -0.05 유효하나 실패 / -0.10 에러)를
            #   각 tactic의 **첫 토큰**에 건다. GRPO의 실병목(40그룹 중 28개가 dead=신호 0)을 직접 겨냥.
            #   정책/프롬프트는 rango-grpo와 동일 — 유일한 변인은 **학습 신호**다.
            formatter = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf,
                proof_retriever_conf=bm25_proof_conf,
                num_premises=50,
                num_proofs=20,
            )
            return [DecoderTacticGenConf(Path("models/rango-grpo-prm/adapter"), [formatter])]

        case "bfs-dpo":
            # BFS-Prover full: DPO(+expert-iter)로 학습한 adapter + BFS-Prover 탐색.
            formatter = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf,
                proof_retriever_conf=bm25_proof_conf,
                num_premises=50,
                num_proofs=20,
            )
            return [DecoderTacticGenConf(Path("models/bfs-dpo/adapter"), [formatter])]

        case "grpo-rollout-r2" | "rango-grpo-e1" | "rango-grpo-e2" | "rango-grpo-e3" | "rango-grpo-e4":
            # effectiveness study: 각 GRPO 변형 adapter로 rollout(r2)/평가(e1-e4). 동일 retrieval 프롬프트.
            adapter = {
                "grpo-rollout-r2": "models/rango-grpo/adapter",   # E1 rollout은 round-1 정책
                "rango-grpo-e1": "models/rango-grpo-e1/adapter",
                "rango-grpo-e2": "models/rango-grpo-e2/adapter",
                "rango-grpo-e3": "models/rango-grpo-e3/adapter",
                "rango-grpo-e4": "models/rango-grpo-e4/adapter",
            }[model_alias]
            formatter = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf,
                proof_retriever_conf=bm25_proof_conf,
                num_premises=50,
                num_proofs=20,
            )
            return [DecoderTacticGenConf(Path(adapter), [formatter])]

        case "rango-grpo-rmaxts" | "rango-grpo-bfs":
            # 학습×탐색 교차 ablation: GRPO 학습 adapter + RMaxTS/BFS 탐색.
            formatter = GeneralFormatterConf(
                premise_client_conf=tfidf_premise_conf,
                proof_retriever_conf=bm25_proof_conf,
                num_premises=50,
                num_proofs=20,
            )
            return [DecoderTacticGenConf(Path("models/rango-grpo/adapter"), [formatter])]

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


class _NoOrigResult:
    """results/*.json(참고용 비교 결과)이 없을 때 쓰는 빈 결과 — 출력 전용이라 평가엔 영향 없음."""
    proof = None
    time = None


def get_orig_result(model_alias: str, split: Split, idx: int):
    """참고용 이전 결과. **화면 출력에만 쓴다.**

    ★ results/*.json 은 논문 배포 결과라 서버에 없을 수 있다. 없다고 평가가 죽으면 안 되므로
      빈 결과로 대체한다(성공/실패 판정과 무관 — 판정은 실제 Coq 실행 결과로만 한다)."""
    thm = get_theorem(split, idx, COQSTOQ_LOC)
    for alias in (model_alias, "rango"):
        try:
            return get_result(alias, thm)
        except (ValueError, FileNotFoundError, OSError):
            continue
    return _NoOrigResult()


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
