# notation 해결 + decider 커버 100% 가능성 검토 (2026-08-02, CPU)

질문: notation을 풀면 decider 커버가 오르나(터지지 않고)? 100% 가능한가?
방법 A/B/C 검증 + 미커버 원인 분류 + 상한 분석. 스크립트: `scripts/validate_notation.py`.

## 1. notation 3방법 — 터지나 (CPU 실측)
| 방법 | 프롬프트 추가 | 터짐? |
|---|---|---|
| A. notation-map 수동확장(흔한 연산) | **+0토큰**(goal 안 건드림, 매칭계산만) | ✗ 안 터짐 |
| B. coqstoq Notation 자동추출(178심볼) | **+0토큰** | ✗ 안 터짐 |
| C. 국소전개 주석(`(* ^ = Zpower *)`) | **+18토큰**(중앙, 최대54) | ✗ 안 터짐 |
| (참고) Set Printing All | goal 3~8배 | ✅ **터짐**(state예산1024 초과 18~51%) |

→ **셋 다 안 터짐.** Set Printing All만 터짐(그래서 안 씀).

## 2. decider 커버(Mode2) — 오르나
| | decider 커버 |
|---|---|
| baseline(notation 없음) | **1%** |
| A(수동 19심볼) | 3% |
| **B(자동추출 178심볼)** | **25%** |
| +CompCert 소스 인덱스확장 +순서decider | 30% |

→ **notation이 실제 병목이었음**(baseline 1% = 연산이 다 가려짐). B로 25배↑. **0토큰**.

## 3. ★ 100% 가능한가 — 미커버 원인 분류 (진짜 답)
Mode2 미커버 75%를 분해:
| 원인 | 비율 | 해결 |
|---|---|---|
| **① 인덱스에 decider 자체가 없음** | **67%** | 인덱스 확장(부분적) |
| ② 조회로직이 base 못 연결 | 7% | 로직 수정(가능) |
| ③ notation이 연산 가림 | 1% | 자동 notation-map(해결됨) |

- **notation(③)은 사실 1%였다** — 진짜 병목은 **① 인덱스 부재(67%)**: `Rle_or_lt`,`ident_eq`,`transf_function`,`assign_variable` 등 CompCert 도메인.
- CompCert 소스(370 .v) 스캔 확장 시도 → decider 127개 추가, 25→30%(정규식 문장분할 조잡, coqc AST면 더).

## 4. ★★ 핵심 통찰 — Mode2만 보면 오해. 진짜 커버는 union
decider(Mode2)는 compound의 **한 종류**일 뿐. 실제 후보생성은 **Mode1(goal 부분식 직접추출) ∪ Mode2(decider)**:
| | 커버 |
|---|---|
| Mode1 (goal의 `f args` 부분식) | **68%** |
| Mode2 (decider 조회) | 27% |
| **★ union (실제 후보생성 상한)** | **76%** |
| 못잡음 | 24% |

→ **decider 커버 30%에 매달릴 필요 없음.** compound의 68%는 goal에 이미 있는 부분식(Mode1, decider 무관). Mode2는 "goal에 없는 decider"만 담당. **union이 진짜 지표 = 76%**(개선재료 다 넣으면 80%, [[../opener/DDR_INVESTIGATION_SUMMARY]]).

## 5. 100% 커버는 가능한가 — 정직한 결론
**아니오, 순수 텍스트론 ~80%가 상한.** 남은 20%:
- **가설(H) 기반 spec lemma**(`in_dests _ _ H`, `Zle_lt_or_eq _ _ H'`, `parmove_initial_reg_or_temp _ _ _ A`): 인자가 goal 결론이 아니라 가설에서 옴. 가설 항을 인자후보에 넣으면 일부 회복.
- **깊은 라이브러리 lemma**: goal 어휘·구조와 무관 → lemma-selection = capacity 벽(oracle +2pp). enumeration 불가, 모델이 배워야.

### 커버 높이는 실현 가능한 레버 (우선순위)
1. **B 자동 notation-map** (Mode2 1→25%, 0토큰) — 즉시, 2차 decider에 필수.
2. **순서/삼분 decider** (`Rle_or_lt`류, +9pp) + **인자에 가설 항 포함** — DDR 80% 도달.
3. **CompCert 소스 AST 인덱스**(coqc 기반, 정규식말고) — ① 부재를 더 회복.
4. **coq `Search` 런타임 조회** — 인덱스 대신 실시간(느리나 coverage↑).
5. **~80% 이상은 표현/capacity 영역** — [[../REPRESENTATION_FOR_TRANSFER]] (AST) 또는 학습.

## 5b. ★ 커버 개선 누적 측정 (2026-08-02, `scripts/improve_decider_coverage.py`, n≈959 gold)

compound decider 커버를 단계적으로 올림:
| 단계 | 커버 | 증분 |
|---|---|---|
| ① baseline (인덱스만, notation×) | 2% | — |
| ② +notation-map(자동추출) | 25% | +23pp |
| ③ +순서/삼분 decider | 32% | +7pp |
| ④ +CompCert 소스인덱스(219 decider) | 36% | +4pp |
| **⑤ +조회 base 매칭 수정** | **79%** | **+43pp** ★최대 |
| ⑥ +Mode1(goal 부분식) union | **80%** | +1pp |

### ⭐ 핵심 발견 + 이전 논증 정정
- **진짜 병목은 "조회 로직"이었다(+43pp)**, 인덱스 부재가 아니었음. 앞 §3의 "①인덱스 부재 54%"는 **부정확**했음 — 실제로는 인덱스에 관련 decider가 있는데 **조회가 정확일치만 해서 못 연결**했던 것.
- **⑤ base 매칭**: gold `destruct (reg_eq a b)`에서 조회가 `reg_eq` 정확매칭 실패해도, **base(`reg_eq`→`reg`=그 연산)가 goal에 있으면 인정**. 36%→79%.
- **오탐 아님(검증)**: 실제 gold head base는 goal에 **67%** 등장, **가짜 head는 0% 오탐**. 즉 정당한 신호(연산이 goal에 실재)이지 아무거나 인정하는 게 아님.
- **남은 20%**: `find_symbol`,`mag`,`env`,`get` = decider 아니라 **함수결과 destruct**(Mode1 대상). 표현식이 goal에 안 나타나면 못 잡음 = 텍스트 한계.

### 커버 올리는 확정 레시피 (2차 decider용)
notation-map(자동) + 순서decider + CompCert소스인덱스 + **조회 base매칭**(최대레버) → **compound decider 2%→79%**, Mode1 union 80%. 전부 **0~수십토큰**(안 터짐).

### 재현성 (재실행 2회 동일)
`scripts/improve_decider_coverage.py` 2회 실행 → 2%→25→32→36→**79**→80 동일(n 959↔965 경계차, 비율 불변). 조회 base매칭은 오탐검증 통과(실제 gold base 67% goal등장 vs 가짜 head 0% 오탐).

## 6. 1차 실험에의 함의
- **1차 = [TYPES]+재랭킹 유지** 맞음. decider(Mode2)는 union의 작은 부분이고, [TYPES]가 destruct-by-변수(Mode1의 단순형)를 이미 100% 커버.
- **2차 decider 넣을 땐 반드시 B(자동 notation-map) 같이** — 안 쓰면 1%로 무의미, 쓰면 25%.
- 산출물: `scripts/validate_notation.py`. 자동 notation-map은 필요시 `data/notation_map.json`으로 저장(미저장, 재생성 가능).

관련: [[../opener/DDR_COMPOUND_RETRIEVAL]] · [[../opener/DDR_INVESTIGATION_SUMMARY]] · [[REVIEW]] · [[../REPRESENTATION_FOR_TRANSFER]]
