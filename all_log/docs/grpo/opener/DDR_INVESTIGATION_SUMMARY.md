# DDR 조사 종합 정리 (2026-08-02)

compound `destruct (…)` 생성 재료 추출을 위한 **Decidability-Directed Retrieval** 조사 전말.
질문 흐름: "compound 커버리지 어떻게 올리나 → decider 구현·측정 → 개선 → 표현 한계".

## 0. TL;DR
- 기존 `_targeted_cands`는 gold compound의 **59% 커버**(이전 "20%"는 as절 측정버그, 정정).
- DDR(부분식추출 + decider인덱스) = **69%**(+10pp). 개선재료 추가로 **80%**(+20pp)까지.
- 가장 큰 레버: **순서/삼분 decider**(+9pp). "새 retrieval"(타입인덱스 Mode2)은 **notation이 연산을 가려** 텍스트만으론 약함(15%).
- 천장(~80%)의 남은 20% = **가설(H) 기반 spec lemma + 깊은 라이브러리 lemma** → 텍스트 표현의 원리적 한계 → [[../REPRESENTATION_FOR_TRANSFER]].

## 1. 측정 방법 (CPU-only, 재현 가능)
- 데이터: `data/grpo_rollouts/goldsft_bs2.jsonl`(gold 증명, proof_state+tactic). compound destruct = `destruct (E)`이고 E head가 단순변수 아님, state 있는 것 = **n=59**.
- 도구: `scripts/build_decider_index.py`(코퍼스 53387 sentence → decider 505: type_eq90/pred_dec175/op_spec202 → `data/ddr_index.json`), `scripts/test_ddr_coverage.py`.
- 커버 = "gold destruct가 후보 리스트에 드나"(후보생성 상한; 모델선택·유효성 별개).
- ⚠️ **as절 주의**: gold `destruct(E) as [[..]]`의 as절은 destruct 대상과 무관 → 떼고 비교(안 그러면 20%로 오측정. 이게 초기 오류였음).

## 2. 커버리지 개선 실측 (누적)
| 구성 | 커버 | 기준선 대비 |
|---|---|---|
| 기준선 `_targeted_cands`(①~⑤) | 59% | — |
| DDR 기본(Mode1 부분식 + Mode2 인덱스) | **69%** | +10pp |
| + notation 맵(`?=`→compare 등) | 71% | +12pp |
| + **순서/삼분 decider**(Rle_or_lt, Zle_or_lt…) | **78%** | **+19pp** ★최대 |
| + 가설(H) 인자 | 71% | +12pp |
| **전부 결합** | **80%** | **+20pp** |

**→ 답: DDR은 +10을 넘어 +20pp(80%)까지 개선 가능.**

## 3. 각 레버 설명
### Mode1 — 부분식 전수추출 (68%, 최대 단일기여)
goal의 `f args` 부분식 전부 → `destruct (f args)`. 기존 ②(match/if scrutinee만)의 일반화. destruct 대상의 68%가 **goal에 이미 있음**(`transf_function f`, `proj_bytes cl`, `Ptrofs.eq_dec ofs ofs0`). **즉시 구현가치**(코드 몇 줄).

### 순서/삼분 decider 인덱스 (+9pp, 최대 개선)
`Rle_or_lt`, `Zle_or_lt`, `Rlt_le_dec` 등은 반환형이 `{x≤y}+{y<x}`(삼분)라 이름이 `_dec`/`_spec`이 **아니어서** 자동인덱스가 놓침. goal에 순서관계(`<`,`<=`,`Rle`…)가 있으면 이들을 후보로. **CompCert에 순서 case-split이 흔해 큰 이득**.

### notation 맵 (+2pp)
`(v0 ?= v1)%positive`↔`compare`, `x <? y`↔`ltb`. goal의 notation 심볼 → 연산 head → spec 인덱스. 작지만 Mode2의 근본약점(아래)을 부분보완.

### 가설(H) 인자 (+2pp)
`destruct (Zle_lt_or_eq _ _ H')`처럼 인자가 **가설 이름**. 가설명을 인자후보에 포함.

## 4. Mode2(타입인덱스=새 retrieval)가 약한 이유 — 핵심 발견
실제 인덱스로 Mode2 단독 = **15%**(이전 이름패턴 근사 34%는 과대치).
- **notation이 연산 이름을 가림**: gold `Pos.compare_spec`인데 goal엔 `?=`. `Z.ltb_spec`←`<?`. → 텍스트에 head가 안 보여 조회 실패.
- **→ decider retrieval을 제대로 하려면 goal의 desugar(notation 확장)/타입정보/AST 필요.** 텍스트만으론 원리적 한계.

## 5. 천장(~80%)의 남은 20% — 무엇이 안 되나
남은 12개(n=59 중): `type_instr_complete te e v`, `in_dests _ _ H`, `parmove_initial_reg_or_temp _ _ _ A`, `Rnd_DN_UP_pt_split F x d u …`, `relative_error_N_FLX'_ex …`, `Mem.valid_access_load …`, `classic (exists s, …)`, `env0!id`, `tree'_not_empty m`...
- 성격: **가설을 인자로 받는 도메인 spec lemma** + **깊은 라이브러리 lemma**(goal 어휘와 무관). 이름·구조가 goal에 안 드러남 → 순수 텍스트론 못 잡음.
- 이건 **일반 lemma-selection = capacity 벽**(oracle +2pp)과 같은 부류. enumeration으론 한계, 모델이 배워야.

## 6. 결론 & 다음
- **compound 후보생성은 개선 여지 큼**(59→80%, 저비용 CPU). 특히 Mode1 부분식추출 + 순서decider는 즉시 구현가치.
- 단 **후보생성≠end성능**: opening/compound는 병목이 아니었음(닫기·도달이 벽, 여러 실측). 후보를 잘 줘도(opener-tac 92% 인자일치) test 성능은 parity였음.
- **진짜 레버는 표현**: Mode2 약점(notation)·전이 실패(타입정보 부재)가 가리키는 방향 → [[../REPRESENTATION_FOR_TRANSFER]](타입 컨텍스트 주입 후 전이율 측정).
- ⚠️ n=59 표본·후보생성 상한 측정. 개선재료(순서decider·notation·hyp)는 per-example 튜닝 아닌 **원리적 규칙**이라 일반화 기대되나 더 큰 표본 검증 필요.

관련: [[DDR_COMPOUND_RETRIEVAL]] · [[COMPOUND_CANDIDATES]] · [[../REPRESENTATION_FOR_TRANSFER]] · [[CLOSING_FAILURE_ANALYSIS]] · [[RANKING_GOLD_VS_APPLIED]]
