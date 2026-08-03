# rango-augmented 최종 설계 (2026-08-03)

**프롬프트에 넣을 것의 확정 스펙.** 이 파일이 augmented의 최종 정답. 근거는 모두 CPU 실측(train300 + compcert5091 + 모델롤아웃, n≥2500~5000).
바탕: [[PLAN]] · [[REVIEW]] · [[STRUCTURAL_INFO_MAP]] · [[COMPOSITION_IS_THE_WALL]] · [[DECIDER_DEEP_DIVE]].

---

## 0. 핵심 프레임 (왜)
한 프로젝트서 학습→다른 프로젝트 전이하려면 **lexical(이름) 아닌 structural(구조)** 정보 필요.
현재 프롬프트는 goal의 함수/타입을 **이름만** 줌 (함수 정의 프롬프트에 **0%**) = **불완전한 상태**. Coq 커널은 완전한 정의 환경에서 goal을 보는데 프롬프트는 정의를 잘라냄.
→ **구조를 재귀적으로 복원**해 "완전한 상태"에 가깝게 + 재랭킹으로 선택을 도움.

---

## 1. 넣는 것 (확정)
| # | 항목 | 상태 | 넣나 |
|---|---|---|---|
| 1 | **재랭킹** (premise 순서 재배치, 블렌드 α5) | ✅배선됨 `RERANK_PREMISES=1` | **넣음** |
| 2 | **[TYPES]** (타입 생성자, **재귀**) | 재구현 필요 | **넣음** |
| 3 | **[DEFINITIONS]** (함수 정의, **재귀**) | 미구현 | **넣음** |
| 4 | [DECIDERS] | | **뺌** (goal스캔 `_targeted_cands`가 이미 함, [[DECIDER_DEEP_DIVE]]) |
| 5 | [SIGNATURES] | | **뺌** (premise에 70% 중복) |

---

## 2. ★ [TYPES] 최종 스펙 (재귀 + 랭킹 + stdlib leaf + 캡)

### 규칙
1. **시작점**: goal의 **가설 + 결론** 타입 (가설 필수 — 결론만 하면 커버 33%로 폭락, gold는 가설 변수를 destruct).
2. **재귀**: 타입 정의 안에 나오는 타입도 따라감(**depth 1**로 충분 — depth2와 커버 동일 100%). `val := Vint int | Vptr block ptrofs` → block, ptrofs도.
3. **stdlib leaf**: `nat`/`Z`/`positive`/`list`/`bool`/`int`... 에서 **재귀 멈춤 + 주입 안 함**(모델이 이미 앎). gold destruct의 20%가 stdlib지만 정의 불필요.
4. **랭킹** (예산 캡이 뒤를 자르므로 중요한 것 우선): `가설변수 타입 +10 > 결론등장 +5 > depth 낮음 > 생성자 적음`.
5. **예산 캡**: 랭킹 높은 순으로 채우다 **≤300토큰**서 중단. 각 정의 축약(≤50토큰, 큰 재귀타입은 앞부분+`...`).

### 실측 (n=5002, 4데이터셋)
| | 값 |
|---|---|
| 토큰 | 중앙 226, p95 296, **최대 300**(캡, 안 터짐) |
| 타입 수 | 중앙 5, 최대 14 |
| **gold destruct/induction 커버** | **39/39 = 100%** |
| 캡 초과 | **0** |

### 왜 재귀·랭킹이 필수였나 (당신 지적 = 데이터 검증)
| 지적 | 검증 |
|---|---|
| "1단계만은 소용없다(재귀 필수)" | ✅ depth0은 최대 1687(터짐), gold 안의 참조타입 놓침 |
| "stdlib 제외해도 되지?" | ✅ gold의 20%가 stdlib(list/nat)=모델이 앎, 빼도 커버 유지. 재귀 leaf로 폭발도 막음 |
| "결론 등장만 넣으면?" | ❌ 결론만=커버 33%. gold는 **가설 변수** 타입 destruct → 가설 포함 필수 |
| "예산 캡이 뒤 자름→랭킹?" | ✅ 잘림 43% 발생, BFS는 gold 앞3위 33%뿐 → 랭킹(가설변수+10)으로 커버 100% |

---

## 3. ★ [DEFINITIONS] 최종 스펙 (함수 정의, 재귀)

### 규칙
1. **시작점**: goal **결론에 등장하는 정의된 함수**(f(...) or 대문자). 전부(unfold만 아님 — 모든 tactic이 함수 다룸).
2. **재귀**: 함수 정의 안에 나오는 함수도(**depth 1**). stdlib 함수는 leaf+제외.
3. **예산 캡**: ≤300토큰. 큰 재귀함수(sem_shift 377·최대3303)는 **시그니처만**(≤60토큰, `:=` 앞).

### 실측 (n=5002)
| | 값 |
|---|---|
| 토큰 | 중앙 **0**(대부분 결론에 도메인함수 없음), p95 204, 최대 **299**(안 터짐) |
| 함수 수 | 중앙 0, 최대 11 |
| 캡 초과 | **0** |

### 근거
goal 함수 정의가 프롬프트에 **0%** = 불완전한 상태([[STRUCTURAL_INFO_MAP]]). 함수 정의는 unfold(8%)뿐 아니라 **모든 tactic 판단의 구조 근거**. 재료 72% 코퍼스에 있음. 필요할 때만(p95 204) 주입, 대부분 0토큰.

---

## 4. 프롬프트 구조 (배선)
```
[TYPES]        val := Vundef | Vint int | Vptr block ptrofs   (재귀·랭킹·도메인만)
               block := ...                                    (val이 참조, depth1)
[DEFINITIONS]  make_predecessors m := fold_right ...           (결론 함수, 재귀)
[PREMISES] <재랭킹된 순서>                                     (순서만 재배치)
[PROOFS] ... [STATE] ... [SCRIPT] ... [TACTIC]
```
- [TYPES]/[DEFINITIONS] **독립 예산**(각 ≤300), premise_tokens 안 뺏음. [STATE] 앞 삽입.
- **합쳐도 ~450토큰** (중앙 226+0), 헤드룸(~900) 안. 최대여도 300+300+base < 4096.
- 배선 = 재랭킹 패턴: env 가드 `INJECT_TYPES`/`INJECT_DEFS`, collate_input에 삽입. 학습·추론 **동일 env**.

---

## 5. 인덱스 (오프라인 빌드, proof-독립)
| 인덱스 | 내용 | 빌드 |
|---|---|---|
| `data/type_defs.json` | 타입명 → (정의, stdlib여부) | Inductive+Definition, 코퍼스+CompCert소스 스캔 (~10161) |
| `data/func_defs.json` | 함수명 → (정의, stdlib여부) | Definition+Fixpoint (~10059) |
- stdlib 판정: 이름 화이트리스트 + file_path(`/lib/coq`,`/theories`).
- **다른 서버 재생성**: 스크립트로 (build_type_index.py 신규).

---

## 6. 구현 순서 (저쪽 서버)
1. `augment.py` 재작성: `selective_types`(재귀+랭킹+stdlib leaf+캡), `definitions`(재귀+캡) 추가.
2. 인덱스 빌드 스크립트: `build_type_index.py`, `build_func_index.py`(=build_ind_constructors 확장).
3. collator 배선: `INJECT_TYPES`/`INJECT_DEFS` env, [STATE] 앞 삽입, 독립예산.
4. CPU 렌더 검증: 노이즈(로컬변수/stdlib 새는지)·크기·gold커버 재현.
5. 학습: base rango 위 continue-SFT, `RERANK_PREMISES=1 INJECT_TYPES=1 INJECT_DEFS=1`. 통제군=비증강 same-split(tst1000tr5091-sft).

## 7. 평가
- (a) gold apply/destruct top-1 (b) rand200 성공률 (c) **★전이율**: train에 없던 타입/함수가 test에 나올 때 적용되나.

## 8. 정직한 한계
- 정보 주입은 **재료 완전성(수평)** → oracle "gold 줘도 +2pp"가 상한 프레임. 순 성능 **+1~2pp 예측**, 전이율에서 더 큼.
- **진짜 레버 = 조합 학습(수직)**: [[../composition/SFT_VS_GRPO]] (rationale SFT / dense reward GRPO). augmented는 재료 정리, 조립은 별도 트랙.
- gold 커버 표본(39)이 크진 않음 — "재귀 필요/안터짐/결론만33%"는 견고, 절대 커버는 ±.

관련: [[STRUCTURAL_INFO_MAP]] · [[COMPOSITION_IS_THE_WALL]] · [[../composition/README]] · [[DECIDER_DEEP_DIVE]] · [[EXPERIMENT_SETUP]]
