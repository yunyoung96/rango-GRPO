# 구조 정보 지도 — lexical→structural, cross-project 전이 (2026-08-02)

**동기(사용자 프레임)**: 한 프로젝트서 학습→다른 프로젝트 전이하려면 **lexical(이름) 아닌 structural(구조)** 정보를 배워야. 그래서 타입 정의([TYPES])를 넣음. **더 넣을 구조 정보가 있나?**

## 1. 현재 프롬프트 = 전부 lexical
| 섹션 | 주는 것 | 성격 |
|---|---|---|
| [STATE] | goal — 타입/함수 **이름만**(val, make_predecessors) | lexical |
| [SCRIPT] | tactic 이력 | — |
| [PREMISES] | lemma statement(이름+시그니처) | 반-structural(시그니처는 구조) |
| [PROOFS] | 유사 증명 | lexical |
→ 타입이 **어떤 구조인지**(생성자·재귀·필드), 함수가 **뭘 계산하는지**(정의)는 없음. 모델은 이름 표층연상만 학습 → 새 프로젝트서 이름 바뀌면 무너짐.

## 2. gold tactic이 의존하는 구조 정보 (전이 관점)
| tactic (gold 비율) | 필요 구조정보 | [TYPES] 커버 | 프롬프트에 |
|---|---|---|---|
| apply/rewrite (26%) | lemma 시그니처 | — | [PREMISES]에 있음 |
| **destruct/induction (12%)** | 타입 생성자·재귀 | ✅ | **[TYPES]로 주입** |
| intro (11%) | 구조무관 | — | — |
| **unfold/simpl (8%)** | **함수 정의(body)** | ❌ | ❌ **완전 없음** |
| 자동화 auto/lia (8%) | 구조무관 | — | — |
| **constructor (5%)** | **goal 타입 생성자** | 부분 | ❌ |
| **inversion (2%)** | **가설 Prop inductive 구조** | ❌ | ❌ |

## 3. ★ 더 넣을 구조 정보 후보 (우선순위)
| 구조정보 | 비율 | 넣을 가치 | 근거 |
|---|---|---|---|
| **[TYPES] 데이터 생성자** | 12% | ✅ 1차(구현중) | 검증됨, 노이즈0, 커버87~100% |
| **[DEFINITIONS] 함수 정의(unfold)** | 8% | ⭐ **다음 후보** | 완전 없는 구조정보. [TYPES]와 동일방식. 전이 명확("이 함수는 이렇게 계산") |
| **[TYPES] 확장: goal 타입 생성자** | 5% | selective_types에 goal 타입 추가(저비용) | constructor용 |
| 가설 Prop inductive(inversion용) | 2% | 낮음 | 비율 작음. Prop inductive 정의 |

### ① [DEFINITIONS] — 가장 유망한 다음 후보 (근거 격상)
- `unfold make_predecessors` → 그 함수가 뭘 계산하는지 알아야. 현재 goal엔 이름만.
- 방식: 코퍼스서 `Definition/Fixpoint` 인덱싱 → goal의 함수head → 정의 주입.
- `[TYPES]`의 자매. 전이: 다른 프로젝트도 함수 정의 봐야 판단.

**★★ 근거 재평가 (2026-08-02, CPU 실측) — "unfold 8%"가 아니라 "상태 완전성":**
- goal 결론의 함수/타입 참조 **8656개 중 정의가 프롬프트에 있는 건 0%.** **100%가 이름만 = 불완전한 상태 표현.**
- 예: `is_nan_FF (SF2FF x) = is_nan_SF x` — SF2FF/is_nan_FF가 뭔지 정의 없음. 모델은 이름 표층연상만.
- **Coq 커널은 완전한 정의 환경에서 goal을 봄. 프롬프트는 정의를 다 잘라내고 이름만 줌 = 불완전 스냅샷.**
- → 함수 정의는 **unfold 8%만이 아니라 모든 tactic(apply/rewrite/destruct) 판단의 구조적 근거.** [DEFINITIONS] 값이 "unfold 커버 8%"보다 큼(상태 표현 완전성). **전이 관점에선 [TYPES]보다 클 수도** — 함수 정의야말로 이름 아닌 계산구조.

**실측 (재료·크기):**
- 함수정의 인덱스: 코퍼스 **10059개**. unfold 대상 커버 **43%**(CompCert소스 스캔하면 더).
- 정의 토큰: 중앙 **43** 평균 87 p90 147 **최대 3303**(재귀함수). **17%가 100토큰↑.**
- ⚠️ **터짐 위험**: goal당 함수 여러 개 × 정의 43토큰 → 다 넣으면 터짐. **selective 필수**(관련 함수 몇 개·≤80토큰·큰 재귀함수는 시그니처만).
- 예시: `cmpf`(36tok), `Plt`(17), `ptr64`(9), `list_disjoint`(48), `sem_shift`(377 큰것).

### [DEFINITIONS] 선별 — proof-독립 (2026-08-02 정정)
- ❌ **"unfold 빈도" 기각**: proof를 봐야 아는 정보 → test(proof 모름) 복원 전제 위반 = 누수.
- ❌ **"apply lemma가 쓰는 함수" 좁힘 부적절**: 함수는 apply만이 아니라 unfold/simpl/fold/rewrite/destruct 모두 다룸.
- ✅ **선별 = goal 결론에 등장하는 정의된 함수 전부** (proof 독립, goal만 봄).
  - goal당 정의된 함수 **중앙 1~2개**뿐(예 `is_nan_FF(SF2FF x)=is_nan_SF x`→3개) → 전부 넣어도 안 터짐.
  - 재료: gold unfold 대상 함수의 **72%가 코퍼스에 정의 있음**(로컬변수 in/x 제외 후).
  - 규칙: goal 함수 ∩ 코퍼스정의 ∩ (로컬변수/키워드 아님), 정의 ≤80토큰(큰 재귀함수는 시그니처만).
- **개수 작아 복잡한 랭킹 불필요**(decider와 대조 — decider는 89개라 랭킹필수, 함수는 1~3개).

## 4. 정직한 경고 (조합 벽과의 관계)
- 이 구조정보도 **재료 제공(수평)** → oracle +2pp 논리 적용가능(함수정의 줘도 "언제 unfold"는 조합).
- **단 전이 관점은 다름**: 조합벽=capacity, 전이실패=구조 안 배워 이름 과적합. 구조정보는 **전이를 직접 겨냥** → 성능(+2pp)보다 **전이율(train→타프로젝트)**에서 값 클 수 있음.
- → 평가 시 **같은 프로젝트 성능**뿐 아니라 **train에 없던 타입/함수의 test 적용률(전이)**을 봐야 구조정보 값이 드러남.

## 5. 결론
- **넣을 구조정보 = [TYPES](데이터 생성자, 1차) + [DEFINITIONS](함수 정의, 다음후보).**
- goal 타입 생성자는 [TYPES] 확장으로 저비용 추가.
- 나머지(가설 Prop inductive)는 비율 작음.
- **핵심: "타입만"이 아니라 "타입 정의 + 함수 정의"가 구조정보의 두 축.** 둘 다 lexical→structural 전이 겨냥.
- 단 재료 제공은 상한(+2pp) 있고, 진짜 전이 검증은 [[COMPOSITION_IS_THE_WALL]] + 전이율 측정 필요.

관련: [[COMPOSITION_IS_THE_WALL]] · [[REPRESENTATION_FOR_TRANSFER]] · [[DECIDER_DEEP_DIVE]] · [[PLAN]]
