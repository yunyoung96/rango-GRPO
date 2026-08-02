# closing 실패 원인 분석 (opener-tac 롤아웃)

작성 2026-08-01. opener가 잘 열어준(w compound, 인자 92%) 뒤 rango가 **닫기(closing)에서 왜 실패**하나. dead 그룹의 closing(step≥2) INVALID **1362~1396개** 분석.

## 1. 실패 tactic 종류 분포
| 유형 | 비율 |
|---|---|
| **잘못된 lemma apply/rewrite** | **39%** (541) |
| 기타(intros/기타 tactic) | 35% (482) |
| 닫는 대신 또 분해(destruct/induction) | 22% (313) |
| automation(auto/lia) 실패 | 4% (60) |
| apply 인자만 틀림(순수) | 0% |

→ 닫기 실패의 주범 = **lemma apply/rewrite (39%)** + 또-분해(22%).

## 2. ★ "인자를 못 맞춘 건가?" → **아니다. tactic·lemma를 아예 다르게 고른다.**

### (a) tactic 종류 대조 (gold와)
| | 비율 |
|---|---|
| **종류가 gold에 없음 (아예 다른 접근)** | **68%** (921) |
| 종류는 gold에 있음 (종류 맞고 인자/시점 틀림) | 32% (441) |

→ **68%는 gold가 안 쓰는 tactic 종류를 시도** = "인자 오류"가 아니라 **접근 자체가 다름**.

### (b) apply/rewrite의 lemma 대조 (gold에 그 lemma가 있나)
| | 개수 |
|---|---|
| **gold에 없는 lemma (아예 다른 lemma 시도)** | **412** |
| gold에 있는 lemma (lemma 맞는데 적용 실패) | 43 |

→ **90%(412/455)가 gold에 없는 lemma를 고름** = **lemma 선택 자체가 틀림** (인자·적용법 문제 아님).

## 3. 결론 — 닫기 벽의 정체
opener는 **여는 것(인자까지 92%)**을 해결했지만, 닫기는 다른 문제:
- **인자를 못 맞추는 게 아니라, 이 정리에 필요한 lemma·전략(접근)을 모른다.**
- 68% 다른 tactic 종류, 90% gold에 없는 lemma → **도메인 증명 지식 부족**.
- retrieval로 lemma를 봐도(recall 88.5%) greedy에서 **어느 걸 어떻게 쓸지 못 고름**.

예 (`succ_pred`): gold는 `rewrite <- Hx.` / `unfold pred.`인데 모델은 `rewrite <- succ_opp.` / `unfold succ; apply Rlt_antisym.` → **분해(destruct)는 gold와 정확히 일치(opener 덕)지만, 그 뒤 닫기 경로를 완전히 다르게 감.**

→ **열기(선택+인자)는 opener/retrieval로 풀리지만, 닫기(lemma 선택+증명 경로)는 1.3B capacity 벽.** compound retrieval을 rango에 넣어도 이 68%/90%는 안 고쳐짐(닫기용 lemma 선택 문제라서).

관련: [[COMPOUND_COMPARISON]] · [[OPENER_TAC]] · `7B_w_compound/FAILED.md`
