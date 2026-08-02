# compound가 닫기(closing)를 못 고치는 이유 — 데이터 근거

작성 2026-08-01. 질문: "opener가 잘 열어도 rango가 못 닫는데, **인자를 틀려서** 못 닫는 거면 compound(인자 후보)를 rango에 주면 잘 닫지 않을까?"

## 논리 자체는 맞다
- 닫기 실패가 **"lemma는 맞는데 인자를 틀려서"**라면 → compound류(인자 후보 제공)가 가치 있음.
- 검증 방법: 닫기 INVALID를 (a) 같은 lemma인데 인자 틀림 (b) 아예 다른 lemma (c) apply 아님 으로 분류.

## 실제 데이터 (opener-tac 롤아웃, 닫기 INVALID 1396개)
| 유형 | 비율 | compound 도움? |
|---|---|---|
| apply/rewrite 아님 (destruct/intros 등 — 여는쪽) | **68%** (945) | 여는 쪽 이슈 |
| **같은 lemma인데 실패 (인자/형태만 틀림)** | **2%** (25) | ✅ compound 도움 |
| **아예 다른 lemma 선택 (선택 자체 틀림)** | **31%** (426) | ❌ 무관 |

→ **"인자만 틀린" 경우 = 2%뿐.** 닫기 실패의 대부분은:
- 68% = 닫는 대신 또 분해하거나 intros 등 (여는쪽/구조 오류)
- 31% = **gold에 없는 엉뚱한 lemma를 고름** (lemma 선택 자체가 틀림)

## 결론: compound가 고칠 수 있는 건 2%
- 님 논리는 옳지만, **"인자 틀림"이 닫기 실패의 2%뿐**이라 compound로 닫기 성능을 못 올림.
- 닫기 실패의 정체 = **인자 오류가 아니라 "무슨 lemma를 언제 쓸지 모름"**(선택+조합).

---

## 그럼 왜 rango는 premise 50개(recall 88.5%)를 받고도 못 쓰나?
정답 lemma가 입력에 있는데도 못 쓰는 이유 = **recall이 아니라 use의 문제** (capacity):

### ① 보는 것 ≠ 고르는 것 (selection)
premise 50개 중 **정답을 1위로 지목**해야 함. 정답이 50개 안에 있어도(recall 88.5%), 이름 비슷한 것(`Ropp_involutive` vs gold `Ropp_0`)을 고름. 50중 1 랭킹이 어려움.

### ② 어떻게 엮는지 (composition)
lemma를 봐도 **순서·인자·어느 subgoal**에 적용할지가 전략. 예 gold `rewrite pred_0, succ_opp, pred_ulp_0` — 여러 lemma를 정확한 순서로. 리스트만 봐선 이 조합을 못 짬.

### ③ 1.3B 표현력 한계 (capacity)
①선택+②조합은 "이 goal에 이 lemma가 왜 맞는지" 의미적 정렬 필요. 1.3B는 retrieval을 참고는 해도 goal-lemma 의미 매칭이 약해 **얕은 패턴(이름 유사)**으로 고름. 더 큰 모델일수록 이 정렬이 나아짐 → "capacity".

**비유**: 공식집(premise 50)을 펴놓고 봐도 **어느 공식을 언제 쓸지 모르면** 문제를 못 푼다. 공식이 눈앞에 있음(recall) ≠ 적재적소에 씀(use). 후자가 1.3B의 벽.

## 종합
- 닫기 실패 = 인자 오류(2%)가 아니라 **lemma 선택·조합을 모름**(90%+) → **compound 무효**.
- premise를 봐도 못 쓰는 건 recall이 아니라 **선택+조합 capacity** 문제.
- → compound retrieval을 rango에 추가해도 닫기(=성능)는 거의 안 오름. (열기 25% + 또-분해 일부만 소폭)

관련: [[CLOSING_FAILURE_ANALYSIS]] · [[COMPOUND_COMPARISON]] · [[OPENER_TAC]]
