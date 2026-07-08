# 진행 상태 (자율 진행 중 — 매 틱 갱신)

> 갱신: 2026-07-08 06:00 UTC. 사용자 부재 중 자동 진행. 돌아오면 이 문서부터 보세요.

## 지금 실행 중
- **bigger 재실행**: `rango-portfolio` 진행중. sauto 완료(19/60, **unique idx27,43,76**). unique-solve 강점 측정용 60정리 @600.

## 자동 큐 (순차, 선행 완료 시 자동 시작)
1. **bigger 재실행** (진행중): sauto → portfolio → mem → search → vguided × 60정리. 매 기법 후 `unique_solves.md` 갱신.
2. **A/B both**: rango 동일스텝 A(normal) vs B(gold lemma) → retrieval vs capacity 깨끗한 delta.
3. **lean raw-6.7b oracle**: 15파일, 사용자 요청 capacity 수치(가벼운 재실행).
4. **QED**: value 학습 → `rango-qed` + `rango-qed-hybrid`(QED+retrieval 혼용) 평가.
5. **6.7B 파인튜닝**: on-the-fly LmDataset(rango 레시피) QLoRA 20k step → **fine-tuned 6.7b oracle**(진짜 capacity 판정).


## ★핵심 긍정 결과 (2026-07-08)
- **portfolio가 큰 세트(60정리)에서 net +2** (27 vs baseline 25), unique 3[idx27,43,55], 회귀 1. 조사 전체 첫 견고한 net-양. 강점은 자동화형 정리 포함 큰 세트에서만 드러남. **baseline 대체 아닌 union이어야 순증.**

## 핵심 결론 (지금까지, 정직하게)
- **inference-time 방법 전부 baseline(11/20) 미달**: search/retrieval-hint/sauto/portfolio/probe/hybrid/RL. (FINAL_REPORT.md)
- **unique-solve 강점**: 탐색계열이 idx27(portfolio는 +55)을 baseline 대신 품. retrieval-hint계열은 강점 0.
- **RL(QEDCartographer 영감 value-guided)**: value 잘 학습(gap 0.85)돼도 약한 classical 탐색 못 살림 → 9/20 net−2.
- **QEDCartographer 논문 충실 재구현 완료**(coq2vec + value iteration + product backup): eval 대기중(큐 4).
- **raw 6.7B**: 포맷 드리프트로 자유탐색 실패(0/20). oracle(teacher-forcing)에선 더 coherent.
- **oracle 예비**: rango(1.3B fine-tuned) A=8%/B(gold lemma)=10% top-1 → **gold lemma 소폭 개선 = retrieval이 주 병목 아닐 수 있음**(단 compound-tactic 하한, 깨끗한 A/B both로 확정 예정).

## 보고서 위치
- `FINAL_REPORT.md` 종합 · `unique_solves.md` 강점 · `JOURNAL.md` 시간순 · `MR1_RL_PLAN.md`/`MR_HYBRID_PLAN.md` 설계 · `oracle_*.md` teacher-forcing 상세

## 내가 계속 하는 것
매 틱: 진행 확인 + 로그 분석 + 보고서 갱신 + **문제 감지·자동 수정**(지금까지 잡은 것: negative-데이터 유실, QED 디바이스 버그, hybrid 단일체인 약점, 4h+ 6.7b oracle 블로킹 → 정리).
