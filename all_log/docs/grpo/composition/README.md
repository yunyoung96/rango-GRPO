# composition — 조립 학습 (색인)

조립(apply THIS lemma to THESE hyps)을 decoder에 학습시키기. **핵심 발견: 재료(가설+premise)는 있는데 조립을 못 함(oracle +2pp) = 정보 아닌 조립 능력.**

## 문서
| 파일 | 내용 |
|---|---|
| [DESIGN.md](DESIGN.md) | **바닥부터 설계** — 문제→왜 안되나(희소보상+credit뭉갬)→3방법(A dense reward/B rationale/C 하드네거) 각 구현. 논문없이 이해되게 |
| [SFT_VS_GRPO.md](SFT_VS_GRPO.md) | **★ SFT 방향 vs GRPO 방향** — SFT(rationale/재료정렬/분해) + GRPO(dense reward/credit분리/하드네거) + 통합 SFT→GRPO 파이프라인 |
| [RESEARCH.md](RESEARCH.md) | 논문조사 — 메타발견(조립특화 decoder objective 논문 없음=novel), 결정논문(CREME/CuDIP/process-verified RL) |

## 한 줄 요약
- **SFT 방향**: gold 조립을 "왜"까지 배움(SFT-1 rationale=1순위, 값쌈). 조립 가르치기.
- **GRPO 방향**: 자기 조립이 productive했나 강화(GRPO-1 dense reward=1순위, coq-lsp 공짜라벨). 조립 다듬기.
- **통합**: SFT(가르치기) → GRPO(다듬기).
- **novelty**: 조립특화 decoder objective는 미개척(논문 없음).
- **회의**: test 전이는 별개(과거 DPO unique-0), 벽이 도달성일 수도(§10). 단 조립특화는 안 해봄.

## 다음 (CPU 사전검증 → GPU 학습)
1. CPU: GRPO-1(productive-VALID 구별되나)·SFT-1(근거 합성되나)·하드네거(뽑히나) 실현가능성
2. GPU: tst1000tr5091(비증강 baseline) 완료 후 SFT-1 or GRPO-1 프로토타입

관련: [[../rango_augmented/COMPOSITION_IS_THE_WALL]] · [[../SUBGOAL_PAPER_ASSESSMENT]] §10 도달성
