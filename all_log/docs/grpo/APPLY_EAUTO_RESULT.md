# APPLY_EAUTO 결과 (2026-07-30, 게이트 미달)

apply류 INVALID(58~68%) 시 eapply/eauto using/rewrite 방향·위치·side-cond 변형을 실행해
dead group을 줄이는지 A/B(같은 100정리, SFT 정책 G8, OFF vs ON).

## 결과 (near-final 91/85)
| 지표 | OFF(baseline) | ON(apply→eauto 확장) |
|---|---|---|
| 신호그룹(정리 ≥1성공) | 21% | 18% |
| dead group | 78% | 81% |
| 시도단위 성공(per-rollout) | 9.6% | 10.3% |

## 결론: dead group 개선 없음 (게이트 미달)
- 시도 단위는 아주 소폭↑(9.6→10.3%, apply 스텝 몇 개 회복). 정리 단위(dead group)는 **개선 없음**.
- 원인: apply-INVALID의 **80%가 이미 off-path**(앞 단계 잘못된 분해로 롤아웃이 이미 망가짐) → apply만 고쳐도 정리 못 살림.
- [[DECOMPOSITION_TYPOLOGY]]와 정합: 병목은 apply-인자가 아니라 **compound-destruct(52%) 선택**. eauto는 이걸 안 건드림.
- → GRPO/DPO/증류 확장 안 감(상한 낮음). apply-arg 자동화는 marginal.
