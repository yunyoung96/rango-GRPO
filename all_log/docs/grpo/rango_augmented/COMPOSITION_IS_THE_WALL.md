# 조합(composition)이 벽이다 — rango-augmented 심층분석의 최종 결론 (2026-08-02)

**정보 주입([TYPES]/decider/[SIGNATURES])이 아니라 "조합 사고력"이 진짜 벽.**
이번 세션 전체가 이 결론으로 수렴. 정보는 대부분 이미 프롬프트에 있고, 못 하는 건 그걸 조합(선택+적용+경로)하는 능력.

## 1. 수렴하는 증거 (여러 독립 측정)
| 측정 | 값 | 함의 |
|---|---|---|
| **oracle**: gold lemma 직접 주입 → top-1 | 8→**10%** (+2pp) | 정답 알려줘도 못 씀 = 정보 아닌 조합 |
| **B2 재료 위치**: 인자=가설79%, lemma=premise54% | 재료 있음 | 재료 있는데 조합 못 함 |
| **apply 실패 분해**: 인자오류 | **0%** | 형식 아닌 "무엇을 어떻게" |
| apply 실패: 잘못된 lemma 선택 | **90%** | 선택(조합의 일부)이 벽 |
| **INVALID 재샘플 복구** | **94%** | 국소 유효성 아닌 전역 구성 |
| gold tactic이 rango top5에 | **35%** | 65% 선택실패 + 35% 뽑아도 off-path |

→ 전부 **"정보는 있는데 조합(선택·적용·경로)을 못 한다"**를 가리킴.

### 대표 예시 — 재료 다 있는데 조합 못 함 (B2)
```
destruct (type_instr_complete te e v)
    · type_instr_complete = premise retrieval에 있음 ✓
    · te, e, v = 가설에 있음 ✓
    · 못 하는 것 = "이 premise lemma를 이 가설들에 apply" 조합

destruct (in_dests _ _ H)
    · in_dests = premise에 ✓,  H = 가설에 ✓
    · 못 하는 것 = 둘을 연결(apply)

destruct (Rnd_DN_UP_pt_split F x d u Hxd Hxu g Hg)
    · lemma = premise ✓,  Hxd/Hxu/Hg = 가설 ✓
    · 못 하는 것 = 7개 인자를 올바른 lemma에 배치하는 조합
```
→ **재료(premise lemma + 가설)가 프롬프트에 다 있음.** [PREMISES]에도 있고 [STATE] 가설에도 있음. 그래도 못 하는 = 조합 능력.

## 2. 왜 정보 주입이 한계인가
- [TYPES]: goal당 3개, 커버 87~100%, 노이즈0 — **깨끗하나 destruct-by-변수만**.
- decider: B1(12%)만 진짜 생성 대상, B2(26%)는 재료가 이미 있음(가설+premise).
- [SIGNATURES]: 70%가 이미 premise에 있음(중복).
- **핵심**: 정보(재료)는 대부분 프롬프트에 이미 있음. oracle이 증명 — 정답을 손에 쥐여줘도 +2pp.
- → **정보를 더 주는 수평 확장은 +2pp 천장.** 조합을 가르치는 수직 확장이 필요.

## 3. 조합 사고력을 키우는 방법 (수직)
### (1) 재랭킹 + 학습 — 이미 하는 것의 진짜 값
재랭킹은 "정답을 위로"가 아니라 **"이 goal엔 이 lemma"라는 매칭을 학습시키는 신호**. oracle +2pp가 하한인 건 모델이 "주어진 후보를 쓰도록" 학습 안 됨. 재랭킹된 걸 쓰도록 학습 → 조합력↑.

### (2) ★ 성공 궤적 expert-iteration — 가장 유망
"이 goal → 이 lemma를 이 가설에 apply → 성공" **전체 궤적을 학습**. gold 흉내(behavior cloning) 아니라 **모델이 검색으로 찾은 성공 경로**를 학습 → 조합을 end-to-end 내재화. §10에서 SFT→GRPO가 안 밀리는 이유(도달+선택+조합 함께 배움).

### (3) 하드-네거티브 (조합 구별력)
"타입 맞지만 틀린 lemma"를 오답으로 → 맞는 조합과 구별. contrastive/DPO. selection 예리화.

### (4) Process reward (조합 단계별)
전체 성공 전에도 "올바른 lemma 선택 시 부분보상" → 조합 중간단계 강화. 희소보상(dead 62%) 완화.

### (5) 구조 표현 (조합 가능한 형태)
[TYPES]가 "이름 연상" 대신 "구조 규칙" 배우게 → 전이가능 조합. 단 표현(AST/타입)이 도와야. [[REPRESENTATION_FOR_TRANSFER]].

## 4. rango-augmented 방향 재정립
```
1차 (정보 정리): 재랭킹 + [TYPES]        ← 조합 재료를 잘 배치 (수평)
2차 (조합 학습): expert-iteration          ← 재료로 조합하는 능력 (수직) ★진짜 레버
                + process-reward / 하드네거티브
```
- **"정보 얼마나 주나"(수평)보다 "조합 어떻게 가르치나"(수직)가 핵심.**
- [TYPES]/decider 심층분석 = 1차(재료 정리)의 상한을 정량화한 것. 조합력이 2차의 본질.
- 단 도달성 천장(§10) 여전 — 조합 개선도 완전체 성공엔 도달(navigation)이 함께여야.

## 5. 한 줄 결론
**compound/apply 실패는 정보 부족이 아니라 조합 사고력 부족.** 재료(가설·premise·타입)는 대부분 프롬프트에 있고(oracle +2pp가 증명), 그걸 선택·적용·연결하는 능력이 벽. → **정보 주입([TYPES]/decider)은 재료 정리(1차, 상한 명확)이고, 진짜 레버는 조합을 학습시키는 것(expert-iteration 등, 2차).**

관련: [[DECIDER_DEEP_DIVE]] · [[REVIEW]] · [[REPRESENTATION_FOR_TRANSFER]] · [[../SUBGOAL_PAPER_ASSESSMENT]] §10 · [[../opener/CLOSING_FAILURE_ANALYSIS]] · [[../multiturn-dropped-validity-not-wall(memory)]]
