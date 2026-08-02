# rango-augmented 실험 세팅 (재현 runbook)

다른 서버에서 git pull 후 재현하기 위한 완전한 세팅. 두 실험: **(1) 재랭킹 A/B**(추론만, 준비완료) + **(2) rango-augmented 재학습**([TYPES] collator 구현 필요).

## 0. 사전 조건 (다른 서버)
- 이 repo (main 브랜치 pull)
- **gitignore된 것 재생성 필요**(data/ 무시됨): 아래 §1.
- 원본 데이터: `raw-data/coqstoq-test/`(data_points, sentences.db, repos), `CoqStoq/`, 기존 rango 모델 `models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500`.
- opam/coq 환경(코드 동일), GPU(RTX6000 Ada 48GB×2 기준).

## 1. gitignore된 인덱스·split 재생성 (CPU, 다른 서버서 1회)
```bash
# (a) decidability 인덱스 (compound decider)
python3 scripts/build_decider_index.py          # → data/ddr_index.json (505 decider)
# (b) inductive 생성자 인덱스 (정제본)
python3 scripts/build_ind_constructors.py        # → data/ind_constructors_clean.json (626 타입)
# (c) tst1000tr5091 split (test 앞1000 / train 5091)
python3 scripts/build_tst_split.py CoqStoq       # → data/compcert_tst1000tr5091_{test,train}_idx.txt
# (d) gold 커리큘럼 (train gold 궤적)
python3 scripts/build_gold_trajectories.py --project compcert --start 1000 --num 5091 \
    --out data/curriculum/gold_tst1000tr5091.json   # → 4298 정리
```

## 2. 핵심 코드 변경 (이번 세션, git에 포함)
- **`src/tactic_gen/tactic_data.py`**: `rerank_premises`(블렌드 α=5: BM25순위 prior + 타입지향점수), env **`RERANK_PREMISES=1`** 시 ProofPremiseCollator가 premise 재정렬. `_rr_*` 헬퍼(결론 head/연산/notation 매칭).
- **`scripts/run_thm.py`**: `grpo-rollout-goldsft`에 `GOLD_FILE`/`ROLLOUT_OUT` env override(새 split gold 데이터 생성용).
- 검증/빌드 스크립트: `build_decider_index.py`, `build_ind_constructors.py`, `build_tst_split.py`, `rerank_premises_typed.py`, `test_ddr_coverage.py`, `test_augmented_dryrun.py`, `render_augmented_examples.py`, `validate_augmented.py`, `au_rank_probe.py`.

## 3. 실험 (1) 재랭킹 A/B — 준비완료 (추론만, 학습 불필요)
같은 executor·rand200·@300s, `RERANK_PREMISES` 0(off) vs 1(on). 재랭킹이 test 성공률로 전이되나.
```bash
EXEC=models/rango-grpo-subgoal-bs2/adapter        # 또는 다른 executor
RAND=data/compcert_bs2_rand200_idx.txt
# baseline
HF_HUB_OFFLINE=1 EXEC_ADAPTER=$EXEC RERANK_PREMISES=0 \
  python3 scripts/run_all.py --alias rango-grpo --idx-file $RAND --timeout 300 --gpus 0,1 --workers 2 \
  --out all_results/rerank_base
# treatment
HF_HUB_OFFLINE=1 EXEC_ADAPTER=$EXEC RERANK_PREMISES=1 \
  python3 scripts/run_all.py --alias rango-grpo --idx-file $RAND --timeout 300 --gpus 0,1 --workers 2 \
  --out all_results/rerank_on
```
(이 저장소엔 `all_log/rerank_ab_queue.sh`로 자동화 — tst1000tr5091 학습 후 실행. 다른 서버선 위 커맨드 직접.)

**검증됨(7 데이터셋)**: 재랭킹(블렌드) top-1 +11~18pp, top-5 regression 0, 순열보존·결정성·크래시0·누수0. 상세 [[REVIEW]].

## 4. 실험 (2) rango-augmented 재학습 — [TYPES] collator 구현 후
목표: 증강 프롬프트로 1.3B 재학습 → (a) gold lemma top-1↑ (b) CompCert 성공률↑. 통제군=비증강 same-split.

### 4a. 파이프라인 개요 (bigscale2 방법 + split만 tst1000tr5091)
```
rango baseline(checkpoint-54500) → gold-SFT(gold replay, train 5091) → SFT 롤아웃 → GRPO
```
`all_log/tst1000tr5091_train.sh`가 **비증강 baseline**(rango-tst1000tr5091-sft/-sftgrpo) 생성. hyperparam: SFT `--sft --kl_beta 0 --lr 1e-6 --epochs 2 --micro_bsz 2 --max_len 3072`, GRPO `--kl_beta 0.04 --lr 1e-6 --epochs 2`. 롤아웃 G=8 max_steps20 retries1 @300s.

### 4b. 증강판 (구현 필요 = 남은 작업)
1. **[TYPES] collator 섹션 추가** (`ProofPremiseCollator.collate_input`): `RERANK_PREMISES`처럼 env `INJECT_TYPES=1` 가드로 `[TYPES]\n<selective 생성자>\n[DECIDERS]\n<decider>` 를 [STATE] 앞에 삽입, **독립 토큰예산**(≤200, premise 안 뺏게). selective 규칙 = `scripts/test_augmented_dryrun.py`/`render_augmented_examples.py`의 `selective_types`(inductive 변수·≤8생성자·결론우선·top6/200토큰) 그대로.
2. **증강 데이터**: gold/롤아웃 각 step에 위 섹션 추가(학습·추론 **동일 규칙** 필수 — 안 그러면 OOD).
3. **continue-SFT**: init=base rango, 증강데이터, 위 hyperparam. `RERANK_PREMISES=1 INJECT_TYPES=1`로 학습·평가 모두.
4. **평가**: (a) gold top-1(teacher-forcing, vs base +2pp 하한) (b) rand200 vs `rango-tst1000tr5091-sft`(비증강).

### 4c. 사전검토 (실행 전 필수) — [[REVIEW]] 체크리스트
- 학습·추론 포맷 동일(RERANK_PREMISES·INJECT_TYPES 양쪽), [TYPES] 독립예산, [TYPES]/decider 조회에 premise_filter exclusion(누수), 1차는 재랭킹+[TYPES]만([DECIDERS]/[SIGNATURES] 2차), 소규모 dry-eval(20정리) 후 전체.
- CPU 무거운 검증은 학습 coq-lsp와 경합(gold replay 느려짐) → 겹치지 않게.

## 5. 결론 (해볼 가치)
재랭킹(블렌드)은 7 데이터셋서 strict 검증된 **선택 개선**(닫기 90% 오lemma 겨냥). end 성능 전이는 실험(3),(4)가 판정. 도달성 천장은 별개. 상세 [[PLAN]] [[REVIEW]] [[../SELECTION_REPRESENTATION_INDEX]].

## 6. GPU 정책
gpu 2개 사용, 외부 유저 gpu0 접근 감지 시 gpu1로(`all_log/gpu0_alert_watch.sh` alert-only, 수동판단). test는 workers=2, train은 워커 많이.
