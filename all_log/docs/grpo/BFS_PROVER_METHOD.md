# BFS-Prover (arXiv:2502.03438) — 논문 충실 재구현 + 우리 실험

작성 2026-07-28. dead-group 돌파를 위한 정공법: **못 푸는 정리를 강한 탐색으로 뚫어 → 그 성공풀이를 정답 삼아 self-training(expert iteration)**. subgoal/invertible이 도달성 병목([[SUBGOAL_PAPER_ASSESSMENT]] §10)에 막힌 뒤 시도하는 대안.

관련 코드: `src/model_deployment/bfs_prover_searcher.py`(탐색), `src/tactic_gen/bfs_dpo_data.py`(데이터추출), `src/tactic_gen/dpo.py`·`dpo_train.py`(DPO), `all_log/run_bfsprover.sh`(오케스트레이터). 정책=rango baseline(DeepSeek-Coder-1.3B+LoRA, checkpoint-54500), Lean→Coq 이식.

---

## 0. 한 줄 요약
> **베이스라인이 못 푸는 hard 정리를 length-normalized best-first 탐색으로 억지로 뚫어 → 성공경로=SFT 정답, 컴파일에러 tactic=DPO 오답 → 자기를 학습 → 점점 더 많이 푸는 정책으로 진화 → 안 본 정리(rand200)로 검증.**

핵심: GRPO에서 8번 다 실패하면 신호 0(dead group)이던 문제를, **BFS로 한 번이라도 뚫으면 학습 신호가 생긴다**.

---

## 1. beam vs BFS — 정확히 무슨 차이

둘 다 "정책 LLM이 tactic 후보를 내고 Coq으로 검사"하지만 **탐색 전략**이 다르다.

| | **beam (필터용)** | **BFS best-first (수집용)** |
|---|---|---|
| 후보 선택 | 결정론적 — 가장 확신하는 tactic만 (greedy/beam) | temperature 샘플링 — 다양하게 |
| 트리 | 얕고 좁게, 확신 경로만 | 우선순위 큐로 **깊게** 확장 |
| 노드 우선순위 | (탐색 안 함) | `score(s_L) = (Σ_{t} log p(a_t|s_t)) / L^α`, α=0.5 |
| 목적 | **"이미 쉽게 푸는가?"** 판정 | **"힘껏 뒤지면 뚫리는가?"** 발굴 |
| 비용 | 쌈 (timeout 120s) | 비쌈 (timeout 300s, 깊은 탐색) |

**length normalization(`/L^α`)이 논문의 핵심 트릭**: 누적 log-prob(Σ log p)은 경로가 길수록 무조건 작아져(음수 누적) → 짧은 증명에 편향. `L^α`로 나눠 **깊은 경로도 공정하게 경쟁**시켜 긴 증명 발굴. α↑ 또는 expansion width↓ → 더 깊이 탐색.

**왜 beam으로 먼저 거르나 (self-filtering)**: 이미 beam으로 쉽게 푸는 정리를 학습에 넣으면 낭비 + 쉬운 패턴만 강화. beam-solved를 **빼고** hard에만 BFS를 투입해 **"어려운 것"에 데이터·연산을 집중** → 라운드마다 코퍼스가 더 어렵고 다양해짐(논문 2.3 step1).

---

## 2. 왜 SFT와 DPO를 **둘 다** 하나

같은 성공 트리에서 **두 종류의 신호**를 뽑아 상보적으로 쓴다.

| | **SFT (expert iteration)** | **DPO (compiler feedback)** |
|---|---|---|
| 데이터 | 성공경로의 (state, tactic) — **정답만** | 같은 state의 (성공tactic ≻ **컴파일에러**tactic) 선호쌍 |
| 학습 | MLE: "이 상태 → 이 tactic 확률↑" | `L = -log σ(β·[(logπ_w-logπ_ref_w)-(logπ_l-logπ_ref_l)])` |
| 가르치는 것 | **무엇을 해야 하는가** (positive) | **무엇을 하지 말아야 하는가** (negative) |
| 한계 보완 | 오답 정보 없음 | 정답 방향 제시 없음 |

- **SFT만으론 부족**: 정답만 보여주면 "에러 낼 tactic"의 확률을 직접 누르지 못함. 탐색 중 계속 같은 에러를 냄.
- **DPO가 채움**: BFS 도중 **실제로 컴파일 에러 난 tactic**(on-policy negative)을 성공tactic보다 낮게 → 정책 분포를 **날카롭게(sharpen)** → 탐색 효율↑, 에러 가지 덜 침.
- 순서: baseline 위에 **누적 성공코퍼스로 SFT** → 그 위에 **라운드 에러쌍으로 DPO** → 다음 라운드 탐색정책. (논문: SFT는 base+누적 전체, DPO는 on-policy 대안. 우리는 둘 다 적용.)

### DPO negative = **컴파일 에러(INVALID)만** (논문 준수)
우리 초기 구현은 valid-but-off-path tactic도 negative로 넣었으나, 논문은 **"Lean compiler error"만** negative. `bfs_dpo_data.extract_dpo_pairs`를 INVALID만으로 수정(2026-07-28).

---

## 3. Expert Iteration 루프 (라운드별)

```
π_0 = rango SFT baseline
라운드 r:
  1) Beam Filtering:   train300 → 결정론적 beam → beam-solved 제외 → hard 남김
  2) Data Collection:  hard → BFS(temp 샘플, 깊게) → 성공 정리의 트리 덤프
  3) 추출:             성공경로 → SFT(누적 append), 컴파일에러 tactic → DPO 선호쌍
  4) SFT:              baseline 위 **누적 성공코퍼스 전체** MLE
  5) DPO:              그 위 라운드 에러쌍 선호학습 → π_r (다음 탐색정책)
최종:  rand200(train 미사용) BFS 평가 — baseline+BFS vs π_final+BFS
```

**flywheel**: R2 beam은 R1에서 배운 덕에 더 많이 풀림 → hard 축소 → 남은 hard를 또 BFS로 뚫음 → 데이터 누적 → 더 강한 정책. 라운드마다 "풀 수 있는 범위"가 넓어짐.

**현재 NROUNDS=2** (R1+R2). resume 가드 있음 → 나중에 `NROUNDS=3`으로 재실행하면 R1·R2 skip, R3만 신규 실행.

---

## 4. 우리 실험 진행 (train 300, rand200, GPU1)

기준: **2026-07-28 19:50 KST**. 정책 π_0 = rango baseline(checkpoint-54500). GPU1, 16워커+스레드캡(OMP=2, thrash 방지).

| 단계 | 결과 |
|---|---|
| **R1 Beam 필터** | 300/300 완료 · **beam-solved 28** → **hard 272정리** |
| **R1 BFS 수집** | 272 hard 중 **BFS-solved 69** (진행 완료 근접) ← **핵심 신호: beam 못 푼 걸 BFS가 69개 뚫음** |
| R1 SFT+DPO | 대기 (수집 완료 후) |
| R2 (전체 반복) | 대기 |
| 최종 rand200 평가 | 대기 (baseline+BFS vs EI+BFS) |

- **의미**: baseline이 결정론적으론 못 풀던 hard 272개 중 69개(≈25%)를 강한 탐색으로 닫음 → 그 성공풀이가 self-training 데이터. dead-group을 **실제로 뚫는 중**.
- **성능 병목(측정)**: 정리당 elapsed ~307s인데 search timeout 120s → **~190s는 정리마다 모델서버+retrieval 인덱스 재빌드**(GPU util 0%, CPU/GPU 용량은 남음). 워커 증설로 해결 안 됨(20워커→load 403 thrash). **진짜 해법 = retrieval 캐싱**(`cached_proof_loc`/`cached_premise_loc` 프리빌드, ~2× 가속) — 다음 적용 후보.

### ETA (실측 3.7정리/분)
R1 잔여 + R2 + 최종 eval(rand200×2, timeout600 = 최대구간 ~4.5h) → **B 전체 ~11h → 07-29 새벽 ~04:30 완료**. (환경 GPU 재교체 없을 때 기준.)

---

## 5. 대조 실험: invertible-BFS (A) — 부정적
같은 BFS 탐색기에 invertible 분해 후보(`_targeted_cands`: 타입-지향 결정절차 case-split — R→`destruct(Rle_or_lt 0 x)`, Z쌍→`zeq/zlt/zle`, positive→`peq`, goal match/if scrutinee destruct)를 주입(`BFS_INVERT=1`).
- **결과: plain-BFS 0/34, invert-BFS 0/34** (invauto 34정리, timeout 120s). 둘 다 전멸 → invauto셋이 너무 어려워 신호 없음, A/B 비교 무의미.
- 결론: invertible 주입은 이 셋에선 기여 없음. [[DECOMPOSITION_IDEAS]]의 도달성 병목과 일관. **BFS-Prover(B) 쪽이 유망**.

---

## 6. 논문 vs 우리 구현 차이 (정직 기록)
| 항목 | 논문 | 우리 |
|---|---|---|
| 대상 | Lean4 (MiniF2F) | Coq (CompCert) |
| 정책 | BFS-Prover 전용(대규모 EI+DPO) | rango baseline 1.3B+LoRA |
| score | Σlogp/L^α, α=0.5 | 동일 |
| expand width E | 튜닝 | 2 (논문 평가값) |
| DPO negative | 컴파일 에러 | 동일(INVALID만, 수정완료) |
| SFT 데이터 | 누적 (state,tactic) 전체 | 동일(grpo_train --sft 재사용) |
| 라운드 | 다수 | 2 (신호확인용, 확장가능) |
| retrieval | (Lean) | BM25 proof + TF-IDF premise (rango) |

**미세 차이**: temperature(코드 기본 1.0, 논문 1.1 언급), beam width. 결과에 큰 영향 없을 것으로 판단, 필요시 조정.

---

## 관련
- dead-group 3분류·도달성: [[SUBGOAL_PAPER_ASSESSMENT]] §10, [[IDEAS]] §4
- invertible 분해: [[DECOMPOSITION_IDEAS]]
- interleaved SFT-RL 문헌 맥락: [[INTERLEAVED_SFT_RL]]
- EI(full-theorem GRPO판): [[EI_PROGRESS]] (이건 GRPO 기반, 이 문서는 BFS+DPO 기반)
