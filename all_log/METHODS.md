# 기법(alias) 총정리 — 각 방법이 뭔지·결과·출처

> 실행: `python3 scripts/run_thm.py run <alias> test <idx>` 또는 `run_all.py --alias <alias>`.
> 출처: **rango**=원본 코드, **mine**=내가 추가, **paper**=논문 충실 재구현.
> 결과는 first-20 @600 기준(baseline=11/20). "unique"=baseline이 못 푸는데 이 기법이 푼 정리.

## 0. 기준선
| alias | 뭐하는가 | 결과 | 출처 |
|-------|---------|------|------|
| `rango` | **baseline**. straight-line: 증명 통째 greedy 생성→실패시 재샘플링(diverse restart) | 11/20 | rango |
| `no-retrieval` | retrieval 없이 생성(검색 기여 측정용) | 5/14 | mine |

## 1. 탐색/백트래킹 계열 (classical best-first)
| alias | 뭐하는가 | 결과 | 출처 |
|-------|---------|------|------|
| `rango-best-beam` | classical best-first(누적 log-prob 우선), **memo 없음**, branch4 | 8/20 | rango |
| `rango-best-rand` | best-beam인데 beam 대신 랜덤 샘플 후보 | ~8/20 | mine |
| `rango-mem` | classical + **use_memo**(transposition table + 실패tactic memo + cycle guard), branch8 | 8/20, 19/60 (unique 27,43) | mine(M2) |
| `rango-mem-wide` | mem + branch16 | 10/20 | mine |

## 2. 검색-힌트(retrieval hint) 계열 — *전부 baseline 열등, unique 0*
| alias | 뭐하는가 | 결과 | 출처 |
|-------|---------|------|------|
| `rango-align` | retrieval된 형제 증명의 정렬된 다음 tactic을 프롬프트 힌트로 | 9/20 | mine |
| `rango-apply` | top premise를 apply/exploit 강제 후보로 추가 | 8/20 | mine |
| `rango-alignapply` | align + apply 결합 | 9/20 | mine |
| `rango-apply-sl` | apply 강제를 straight-line에 | 9/20 | mine |

## 3. 다양성(diversity) 계열
| alias | 뭐하는가 | 결과 | 출처 |
|-------|---------|------|------|
| `rango-ensemble` | straight-line이 retrieval-fine-tuned ↔ no-retrieval 모델 번갈아 | 10/20 | mine |
| `rango-divsample` | 같은 모델 retrieval on/off 프롬프트 번갈아(ensemble 약점 보완) | 10/20 | mine |

## 4. 자동화(hammer/CoqHammer) 계열
| alias | 뭐하는가 | 결과 | 출처 |
|-------|---------|------|------|
| `rango-sauto` | retrieval-guided hammer. top premise를 `sauto use:`로 먹여 자동증명 | 9/20, 19/60 (**unique 27,43,76** 자동화형) | mine |
| `rango-psauto` | portfolio(강한 straight-line) + sauto fallback client | 10/20 | mine |
| `rango-search` | Coq `Search`로 stdlib lemma 찾아 sauto use (built-in premise) | 7/20 | mine |

## 5. Portfolio(조합) 계열 — ★유일한 net-양
| alias | 뭐하는가 | 결과 | 출처 |
|-------|---------|------|------|
| **`rango-portfolio`** | **straight-line(앞 70%) → 실패시 classical+memo(뒤 30%)**. 두 방식 union | **12/20, 27/60 (net +2, unique 27,43,55)** | mine |
| `rango-hprobe` | 값싼 sauto probe(≤90s) + full straight-line (무손실 fallback 시도) | 8/20 (net−3) | mine |

## 6. RL / value 계열 (탐색 순서를 학습으로 유도) — *전부 net-음*
| alias | 뭐하는가 | 결과 | 출처 |
|-------|---------|------|------|
| `rango-vlog` | classical+memo로 탐색 트리 (state,label) 덤프 (value 학습 데이터 생성) | (eval 아님) | mine |
| `rango-vguided` | 학습된 supervised value(MLP)로 classical frontier 블렌드 (MR1, QEDCartographer-영감) | 9/20 | mine |
| `rango-qed` | **QEDCartographer 충실**: coq2vec LSTM value + γ^dist value-iteration + product-over-subgoals backup | 8/20 (=mem, value 기여 0) | mine(paper-영감 충실) |
| `rango-qed-hybrid` | qed value + retrieval 확신 게이팅(확신↑→greedy boost) | (평가중) | mine |

## 7. Hybrid(확신 게이팅) 계열
| alias | 뭐하는가 | 결과 | 출처 |
|-------|---------|------|------|
| `rango-hybrid` | retrieval 확신(top log-prob)↑→greedy width, ↓→classical 탐색 (adaptive-width) | 2/20 (단일체인 약점) | mine |
| `rango-hybrid-v` | hybrid + value 블렌드 | 2/20 | mine |

## 8. 논문 알고리즘 충실 재구현 (rango 탐색과 안 섞음, 정책 모델만 Coq 1.3B)
| alias | 뭐하는가 | 결과 | 출처 |
|-------|---------|------|------|
| `rmaxts` | **DeepSeek-Prover-V1.5** (2408.08152). DUCB MCTS(γ=.99) + RMax intrinsic reward(novelty) + truncate-and-resume + state merging | (큐 대기) | paper 충실 |
| `bfs-prover` | **BFS-Prover** (2502.03438). length-normalized best-first: `score=Σlogp/L^α`, α=0.5, width2 | (큐 대기) | paper 충실 |

## 9. 기타
| alias | 뭐하는가 | 결과 | 출처 |
|-------|---------|------|------|
| `rango-inter-file` | cross-file retrieval 변형(파일 경계 넘어 형제 증명 검색) | 실험적 | mine |

---
## 한눈 요약
- **baseline(11) 넘은 건 portfolio(12@20, +2@60)뿐** — 그것도 큰 세트에서만. 나머지 전부 ≤ baseline.
- **unique 강점**(baseline 구조적으로 못 풂): idx 27,43,55,76 — sauto/classical 자동화·백트랙 계열이 품.
- **RL/value(vguided/qed): 학습은 되나 탐색 못 살림 → net−.**
- **논문 재구현(rmaxts/bfs-prover): 실행 대기 중** — 우리 세팅(Coq 1.3B)에서 어떻게 되는지 실측 예정.
