# mixed rollout이 실패하는 이유 — tactic 단위 실증 분석 (2026-08-06)

> ⚙️ **분석 당시 학습률: lr=3e-4→3e-5 (cosine).** 이 문서의 모든 수치(probe 29→30, apply INVALID율, mixed/dead, R1/E/X 분해)는 실험 **`tst1000tr5091_bc_lr3e-4_kl0.015_B100_G8`**(batch b000~b039)의 롤아웃에서 나온 것. 결과 요약=[[../grpo/BC_LR3E-4_RESULT]]. (이후 lr=1e-3 실험은 별도 태그 `..._lr1e-3_...`.)

**질문**: GRPO 학습에 쓰이는 mixed 그룹(성공·실패 섞인 정리)에서 **실패는 왜 나나?** 어느 tactic이 문제인가?

**데이터**: tst1000tr5091 batch-chunk GRPO **(lr=3e-4)** 의 mixed rollout 33 batch — **859 그룹 / 6872 attempt / 58,159 tactic**.
(각 그룹 = 같은 정리 G=8 시도. mixed = 성공·실패 섞임 = GRPO 학습에 실제 쓰인 그룹.)

## 2단계 분할 (rollout 성공여부 × tactic 유효성)

```
┌────────── 성공 rollout(attempt) ─────────┬────────── 실패 rollout(attempt) ─────────┐
│ tactic 22,506                            │ tactic 35,653                            │
│  VALID 21,000 / INVALID 1,506            │  VALID 27,100 / INVALID 8,553            │
│  INVALID율 6.7%                          │  INVALID율 24.0%   ← 3.6배               │
└──────────────────────────────────────────┴──────────────────────────────────────────┘
```
- **성공 rollout도 6.7%는 INVALID를 침** — 단 `max_retries` 재샘플로 극복하고 Qed까지 감.
- **실패 rollout은 INVALID율 24%** — 못 넘고 죽음. 성공/실패의 3.6배 격차가 여기.

## tactic별 4분면 (**실패한 증명속 거부 개수** 내림차순, 빈도 50+ 만)

**📖 열 읽는 법 — 두 축이 겹쳐 있음(이게 헷갈림의 원인):**
```
                        Coq 통과(VALID)   Coq 거부(INVALID)
  증명 성공한 시도에서:        X                Y        ← "성공한 증명속: 통과/거부"
  증명 실패한 시도에서:        Z                W        ← "실패한 증명속: 통과/거부"
```
- **세로축 = 증명 시도(attempt) 전체가 결국 성공(Qed)/실패(죽음)** — 정리 하나를 tactic 여럿으로 잇는 한 번의 시도.
- **가로축(슬래시 앞/뒤) = 그 tactic 한 방을 Coq이 통과(VALID)/거부(INVALID)** — tactic 단위.
- **예) apply "성공한 증명속 1381/315"**: 결국 성공한 시도들 안에서 apply가 1381번 통과·315번 거부(재샘플로 극복). **"실패한 증명속 921/2047"**: 실패한 시도들 안에선 921 통과·2047 거부(거부 압도→죽음).

`통과中/거부中 INV%`(오른쪽 3열, *이탤릭*)=각 그룹 내 거부율. `전체`=성공+실패 합산. (md엔 글자색이 없어 열 분리+이탤릭으로 수/%를 구분.)

| tactic | 인자(실측) | 성공증명속 통과/거부 | 실패증명속 통과/**거부**↓ | 성공中 거부% | 실패中 거부% | 전체 거부% | **총 tactic** |
|---|:--|--:|--:|--:|--:|--:|--:|
| **apply** | **lemma/가설**(±in,with) | 1381/315 | 921/**2047** | *18.6%* | *69.0%* | *50.6%* | **4664** |
| **rewrite** | **lemma/가설**(±<-,in) | 1164/246 | 889/**1552** | *17.4%* | *63.6%* | *46.7%* | **3851** |
| eapply | lemma/**가설**(IH) | 464/56 | 404/**518** | *10.8%* | *56.2%* | *39.8%* | **1442** |
| now | **tactic**² | 523/71 | 49/**337** | *12.0%* | *87.3%* | *41.6%* | **980** |
| constructor | 無(±with)¹ | 447/27 | 375/**261** | *5.7%* | *41.0%* | *25.9%* | **1110** |
| lia | 無 | 329/12 | 43/**134** | *3.5%* | *75.7%* | *28.2%* | **518** |
| assert | 명제(±by) | 47/21 | 68/**117** | *30.9%* | *63.2%* | *54.5%* | **253** |
| generalize | 가설/식(±dependent) | 91/16 | 150/**114** | *15.0%* | *43.2%* | *35.0%* | **371** |
| congruence | 無 | 119/10 | 59/**76** | *7.8%* | *56.3%* | *32.6%* | **264** |
| exists | 항(witness) | 193/25 | 107/**75** | *11.5%* | *41.2%* | *25.0%* | **400** |
| reflexivity | 無 | 114/8 | 36/**73** | *6.6%* | *67.0%* | *35.1%* | **231** |
| elim | 가설/식 | 55/8 | 104/**43** | *12.7%* | *29.3%* | *24.3%* | **210** |
| replace | 식 **with** 식 | 14/8 | 22/**42** | *36.4%* | *65.6%* | *58.1%* | **86** |
| erewrite | lemma/**가설** | 21/5 | 24/**42** | *19.2%* | *63.6%* | *51.1%* | **92** |
| specialize | 가설+인자 | 21/4 | 19/**36** | *16.0%* | *65.5%* | *50.0%* | **80** |
| ring | 無¹ | 19/4 | 1/**27** | *17.4%* | *96.4%* | *60.8%* | **51** |
| — 무인자·안정(실패열 미집계) — | | | | | | | |
| intros/Proof/auto/eauto/simpl | 無 | (대량) | — | *<8%* | — | *~0.1–3%* | (수천) |

*(총 tactic = 성공V+성공I+실패V+실패I. 위 16개 인자tactic 합계 14,603개. apply 4664·rewrite 3851이 압도적 = 실패의 주무대.)*

¹ **ring·constructor은 인자 없음** — INVALID은 '무엇을 넣을지'가 아니라 goal이 조건(ring식/구조체)에 안 맞는 **적용가능성(applicability) 실패**. 선택 실패와 성격 다름. (ring n=51로 표본 작음.)
² **now는 `now <tactic>`** — 뒤 tactic 실행 후 `easy`로 닫음. 인자가 '자동'이 아니라 **tactic**(실측 100%가 apply/destruct/rewrite… 등 하위 tactic).

> **📊 인자 종류 실측 (36 gz 전량, `rewrite`가 항상 lemma가 아님)**: `rewrite`는 첫인자가 **대문자(lemma류) 57% vs 소문자(가설/local) 43%**, 게다가 `<-`(역방향) 14%·`in H`(위치지정) 11%·`;`연쇄 26%. `apply`는 **가설이 오히려 더 많음**(lemma 42% vs 가설 58%, `with` 13%·`in H` 7%). `eapply`는 가설/귀납가설(IH) 79%. → 선택 대상은 'global lemma'만이 아니라 **lemma+local 가설 둘 다**이고, 방향(`<-`)·위치(`in`)·부가인자(`with`)까지 고른다. 앞표의 `인자` 열은 이를 반영해 정정함.

> **읽는 법 — 왜 성공中/실패中 분리가 중요한가**: apply는 **성공 rollout 안에서는 INVALID가 *18.6%***(재샘플로 극복)뿐인데 **실패 rollout 안에서는 *69.0%***가 INVALID다. 전체 50.6%는 이 둘의 합산이지 "어디서나 절반이 틀림"이 아니다. **성공/실패를 가르는 건 apply INVALID율의 격차**(18.6%↔69.0%, 3.7배)이고, ring·now는 더 극단(17.4%↔96.4% / 12.0%↔87.3%).

## 세 가지 발견

### ① "인자를 써넣는 tactic"일수록 INVALID율이 높다 (선택 실패)
- 상위 독식: ring(61%)·replace(58%)·assert(55%)·apply(51%)·rewrite(47%) — **모두 lemma/식/명제를 직접 지정**.
- 하위: intros·Proof·auto·simpl·eauto — **인자 없음 → 거의 안 틀림**(<5%).
- 즉 실패는 **"어느 tactic을 칠지"가 아니라 "무엇(lemma/식)을 써넣을지"에서 난다.**

### ② INVALID(문법적 죽음)의 절반은 apply/rewrite — 성공/실패 공통
- 전체 INVALID(SI 1506 + FI 8553 = 10,059) 중 **apply(2362) + rewrite(1798) = 41%.**
- 성공 rollout이 틀릴 때도, 실패가 죽을 때도 **항상 apply/rewrite**. 틀리는 지점은 보편적으로 "lemma 선택".

### ③ 한 batch 안에서 실패·VALID엔 auto/eauto가 성공보다 많다 (단, "시간에 따라 증가"는 아님)
- **한 batch 스냅샷**: 실패·VALID에서 auto·eauto·simpl 합 ~25% vs 성공·VALID ~11%.
  → 그 batch의 실패 rollout이 맞는 lemma 못 찾아 auto/eauto로 때우는 경향(VALID지만 진전 없음)은 관찰됨.
- ⚠️ **정정(시계열 검증, 33 batch)**: "GRPO 학습이 진행될수록 auto가 는다"는 **근거 없음 — 반증됨.**
  auto+eauto 비율은 초반10 batch 10.2% → 후반10 batch 6.8%로 **오히려 감소**(2~17% 노이즈 진동, 추세 없음).
  → "GRPO가 auto 도피를 강화한다"는 앞선 서술은 과잉해석이라 철회.

## 결론 — 병목 = premise/lemma 선택
- 모델은 tactic 종류(apply/rewrite/destruct)는 정확히 고른다. **못 하는 건 그 인자(어느 lemma/식/변수)**.
- `apply plus_two/three/four` 처럼 **그럴듯한 이름을 랜덤 시도**하는 패턴이 대표적 (INVALID 예시).
- 이전 결론([[../../../memory: coverage-not-wall-selection-reachability]] 취지)과 완전 일치: **벽 = coverage/생성이 아니라 selection.**

## GRPO 실패와의 연결 (왜 probe 정체했나) — ★시계열 근거로 검증
가설: "GRPO가 강화하는 건 일반화 가능한 선택 능력이 아니라 train 정리 lemma 암기라 held-out 전이 안 됨."
이걸 뒷받침하는 **직접 근거(rollout 33 batch 시계열, harvest gz)**:

| | 초반 10 batch | 후반 10 batch |
|---|---|---|
| **apply INVALID율** | 62.1% | **64.7% (안 줄음)** |
| 전체 INVALID율 | 23.1% | 24.0% (불변) |
| auto+eauto% | 10.2% | 6.8% |

- **33 batch를 학습하고 정책이 kl 0.07까지 움직였는데도(앞서 확인), apply의 INVALID율이 62→65%로 전혀 안 줄었다.**
  = GRPO 학습이 **"타입 맞는 lemma 선택"을 못 가르쳤다는 직접 증거.** rollout 품질(선택 정확도)이 안 변함.
- rollout INVALID율이 불변 → held-out probe도 불변(29→30)이 당연. **정체의 인과가 여기서 드러남.**
- 주의: "특정 lemma 암기" 자체(train 정리 성공률↑)는 이 실험에서 train probe를 안 재서 직접 확인 못 함
  (probe는 held-out만). 확정된 건 "**held-out lemma 선택 정확도가 33 batch 내내 불변**"이라는 것.

## 함의 (다음 방향)
- **reward 튜닝(dense 등)만으론 부족** — 선택 능력은 1.3B 용량 + retrieval 품질 문제.
- **직접 처방 = premise 선택을 입력에서 좁혀주기**: 타입 지향 재랭킹 + [TYPES]/[DEFINITIONS] 주입
  ([[../grpo/rango_augmented/AUGMENTED_FINAL]]). apply/rewrite 후보 lemma를 미리 걸러 selection 병목 직공.
- 또는 lemma 선택에 강한 retrieval(hard-negative 대조 등).

---

## INVALID의 원인 — hallucination인가, 틀린 인자인가? (2026-08-06)

**질문**: `apply L`이 INVALID일 때, **없는 이름을 지어낸(hallucination)** 건가, **실존하는데 타입/문맥이 안 맞는(틀린 인자)** 건가?

### ⚠️ 현재 저장 데이터로는 확정 불가 → 저장을 켰다
- 확정하려면 coq-lsp 에러 메시지("was not found" vs "Unable to unify")가 필요한데, **기존 gz엔 `coq_error`가 없음**(RECORD_ERROR 꺼져 있었음, 실측).
- **조치(2026-08-06)**: `grpo_rollout.py`의 `RECORD_ERROR` 기본값을 **`1`(켬)**으로 변경(INVALID step만, 600자). 이제 **앞으로 모든 롤아웃이 "왜 틀렸는지"를 저장**. 끄려면 `RECORD_ERROR=0`.
- **분류기**: `scripts/classify_rollout_errors.py` — `coq_error` → `HALLUC_ref_not_found`(없는 참조) / `TYPE_mismatch`(타입·인자) / `APPLICABILITY`(tactic 부적용) / `SYNTAX` / `OTHER`. **앞으로 롤아웃마다 이걸로 원인 분포를 보고**.

### 프록시 추정 (에러 없이, 이름 실존 여부로 — 잠정)
23,552개 INVALID apply계열 step을, 넣은 이름이 실존하는지로 대략 분류(에러메시지 없이 가능한 최선):

| 분류 | 개수 | 비율 | 의미 |
|---|--:|--:|---|
| ① LOCAL_HYP (로컬 가설) | 2,601 | *11.0%* | 실존 — 가설을 잘못 씀(타입/사용 오류) |
| ② IN_RETRIEVED (검색된 후보) | 7,051 | *29.9%* | 실존·available — 타입 안 맞음 |
| ③ REAL_ELSEWHERE (딴 데서 성공한 참조) | 3,550 | *15.1%* | 실존(다른 goal서 성공한 lemma) |
| ④ HALLUC_CAND (어디서도 성공 안 함) | 10,343 | *43.9%* | hallucination **후보**(상한) |

- **실존 참조가 최소 56.1%(①+②+③)** → 이만큼은 **hallucination이 아니라 "틀린 인자/문맥"(선택 실패)** 확정.
- ⚠️ **④조차 대부분 실존**: ④ 상위 토큰이 `Zle_trans`·`PMap.gss`·`Rmult_le_compat_l`·`proof_irrelevance`·`range_perm_trans` 등 **전부 실제 CompCert/Coq stdlib lemma**. 단지 우리가 retrieval로 안 띄웠거나 우리 롤아웃서 성공한 적 없을 뿐. → **진짜(존재하지 않는 이름) hallucination은 44%보다 훨씬 작다.**
- **잠정 결론**: **INVALID의 압도적 다수는 실존 lemma/가설을 잘못된 타입·문맥에 넣은 "틀린 인자"**이지 없는 이름을 지어낸 게 아니다. → 처방은 *hallucination 억제*보다 **타입 정합 선택**(retriever/type-check)이 맞다([[TYPE_LEARNING_RESEARCH]] 방향 A/B와 정합).
- ※ 위 %는 상·하한(프록시). **정확한 hallucination vs 타입불일치 비율은 이제 저장되는 `coq_error`를 `classify_rollout_errors.py`로 돌려 확정**한다.

---

## apply·rewrite 실패 정밀 분석 — "없는 lemma인가, 검색된 걸 못 쓰나?" (2026-08-06)

**질문**: apply/rewrite가 틀릴 때 (a) 없는 lemma를 지어낸 건가, (b) 적절한 게 retrieval(50개 후보)에 있는데 못 쓰는 건가?

**방법**: 각 INVALID의 사용 lemma를 **그 step의 검색후보 50개 head 이름** · 로컬 가설 · 전체 코퍼스 사전(206k, 4개 sentence DB)과 대조. (apply=apply+eapply, rewrite=rewrite+erewrite)

**📂 데이터 출처(전수, 샘플 아님)**: 이 실험(`tst1000tr5091`)의 롤아웃 파일(`.jsonl.gz`) **36개 = batch b000~b035 전부**를 스캔. 규모: **group 3,288**(정리별 G=8 시도 묶음) / **attempt 26,304**(개별 증명 시도) / **step 220,234**(tactic 1회 실행). 그중 **INVALID step 52,288(23.7%)**, 이 중 **apply계열 14,433 + rewrite계열 10,486 = 24,919개를 전량 분류**. *(용어: gz파일=batch=정리100개, step=tactic 한 줄. 앞의 성공/실패 4분면 표는 **mixed 그룹만**의 부분집합이라 숫자가 작고, 이 분석은 **전 그룹**이라 큼.)*

| 분류 | apply INVALID 14,433 | rewrite INVALID 10,486 | 뜻(처방) |
|---|--:|--:|---|
| **R1 검색후보에 있었음(타입 안 맞음)** | *33.4%* | *29.0%* | 🎯 retrieval이 띄운 상위 후보를 골라놓고 **타입 못 맞춤** = 순수 선택실패. retrieval 탓 아님 |
| **H 로컬 가설 오용** | *8.3%* | *14.7%* | 가설을 틀린 타입/문맥에 |
| **E 실존이나 미검색(off-book)** | *22.1%* | *25.7%* | 실존 lemma를 **검색 리스트 무시하고** 파라메트릭 기억서 꺼냄 |
| **X 사전에도 없는 이름** | *36.2%* | *30.6%* | ⚠️ **대부분 실존 stdlib**(아래) → 진짜 hallucination은 이보다 훨씬 작음 |

### 📌 각 분류 실제 예시 (실 롤아웃에서 추출)
| 분류 | 실제 tactic | goal(요약) | 검색 top5 head | 판정 이유 |
|---|---|---|---|---|
| **R1** | `apply generic_format_FLT in Hb.` | `Hb: generic_format beta (FLX_exp prec) x` | generic_format_FLX_1, FLT_format_generic, **generic_format_FLT**(3위), … | 검색 **3위**에 있던 걸 골랐으나 Hb는 **FLX**계열인데 lemma는 **FLT**용 → 타입 불일치 거부 |
| **H** | `apply H4.` | `… H0:… H1:In n3 …` (H4는 로컬 가설) | reachable_trans, in_app, … | `H4`는 검색후보 아님·**로컬 가설**. 결론 타입 안 맞아 거부 |
| **E** | `apply Ziter_base.` | `Z.iter 0 f x = x` | Zdiv_interval_2, eqmod_small_eq, … (무관) | `Ziter_base`는 goal에 딱 맞는 **실존 lemma지만 검색 top엔 없음** → 기억서 꺼냄(retrieval recall miss) |
| **X** | `apply Zle_0_eq in H.` | `H: Z.pos p <= 0` | Ple_refl, Ple_succ, … | `Zle_0_eq`가 **사전에 없음** → 없는 이름이거나 미수록 stdlib. (`Z.le_0_eq`의 오기 가능성) |

> 💡 R1 예시가 핵심: **generic_format_FLT는 이미 검색 3위로 눈앞에 있었다.** 모델이 그걸 골랐지만 goal이 FLX인데 FLT lemma라 튕김 = **retrieval이 아니라 타입 선택의 실패.**

### 🔬 X는 왜 틀렸나 — "이름 자체가 (그대로는) 존재하지 않음" (+이전 과장 정정)
X(사전에 없는 이름) 8,451개를 **정규화(대소문자·구두점 무시)**로 더 쪼개면:

| 세부 | 비율 | 뜻 | 예 |
|---|--:|---|---|
| 오타/철자 변형 | *4.4%* | 실존 이름을 **철자만 틀림** | `Rmult_ASSOC`→`Rmult_assoc`, `Rnd_Up_pt_unique`→`Rnd_UP_pt_unique`, `R_lt_minus`→`Rlt_minus` |
| novel | *95.6%* | 정규화해도 매칭 없음 | `Z.iter_base/small/forall`, `generic_format_generic_format_inversion` |

- **핵심 메커니즘 = 조합형 이름 창작(compositional hallucination)**: novel의 상당수는 **실존 접두어+그럴듯한 접미어를 조합**해 지어낸 이름. `generic_format_generic_format_inversion`(접두어 중복), `Z.iter_base/small/forall`(실존 `Z.iter`에 창작 접미어), `apply plus_two/three/four`. → **진짜 hallucination(존재하지 않는 이름).**
- 단 novel 일부(`Rnd_U_pt_unique`류)는 **Flocq 실존인데 우리 DB에 없어** 섞임 → 정규화로도 실존/창작 완전히 못 가름.
- ⚠️ **이전 과장 정정**: 앞서 "X는 대부분 실존 stdlib"이라 한 건 **과했다.** 실제론 **4% 오타(실존)+96% novel(실존 stdlib과 조합형 창작이 섞임)**이고 **조합형 창작이 뚜렷이 존재**. 즉 R1/E(실존을 타입 못 맞춤)와 달리 **X는 "이름 자체가 없어서" 튕기는 경우가 상당**하다.
- **두 실패 모드**: ① **타입 불일치**(이름 실존, 타입/인자 안 맞음 = R1·H·E + X의 실존분) → `coq_error` "unable to unify". ② **이름 없음**(오타분+창작분) → "was not found". **정확한 비율은 저장되는 `coq_error`로만 확정**([[record-rollout-errors]]).

### 🔑 R1의 결정적 근거 — "검색은 됐는데 타입 못 맞춘다"
- R1(검색후보에 있던 걸 골라 실패)의 **사용 lemma 검색순위: 중앙 4~5위, top5내 55~58%, top10내 76~77%**(후보 50개 중).
- 즉 모델은 **retrieval을 무시하는 게 아니라 상위 후보를 고른다. 그런데 그 상위가 타입이 안 맞는다.** → 문제는 "검색이 안 됨"이 아니라 **"타입 정합으로 못 고름".**

### 답 (사용자 질문 직답)
- **"없는 lemma를 지어냈나?"** → **소수.** X 36%조차 대부분 실존 stdlib. 순수 hallucination은 그 일부.
- **"retrieval엔 있는데 못 쓰나?"** → **그렇다, 강하게.**
  - **1/3(R1)**: 검색 **상위후보(중앙 4위)를 골라놓고 타입 못 맞춤**.
  - **또 절반가량(E+X 대부분)**: 실존 lemma를 **검색 리스트 무시하고** 기억서 꺼냄(=검색 활용·recall 문제).
- **공통 처방**: retrieval **유무**가 아니라 **타입 정합 선택/활용** 능력 결여 → [[TYPE_LEARNING_RESEARCH]] 방향 A(타입 hard-neg contrastive: 상위후보를 타입으로 재정렬) + B(type-check process reward)가 정확히 이 지점을 겨냥.
- ※ 프록시(이름 대조). 확정치는 `coq_error` 분류([[record-rollout-errors]])로 갱신.

### 🗂️ "사전(dictionary)"이 뭔가
- **4개 sentence DB(sqlite)의 모든 문장에서 lemma/정의 이름을 추출한 집합 = 206,127개**(모듈 short명 포함).
  - `raw-data/coq-dataset/sentences.db`(학습 코퍼스) + `coqstoq-{test,val,cutoff}-sentences.db`.
  - 추출: 각 문장이 `Lemma|Theorem|Definition|Fixpoint|Corollary|Remark|Fact|Instance|Record|Inductive|Let NAME …` 이면 그 `NAME`(+`A.b`의 `b`)을 담음.
- **용도**: 사용 lemma가 "우리 데이터셋에 실존하는 이름인가" 판정(E vs X 가르기).
- ⚠️ **한계**: DB가 **CompCert/프로젝트 파일 위주**라 Coq **표준 라이브러리**(ZArith `Zle_trans` 등)가 대부분 빠짐 → 실존 stdlib이 X로 오분류. 그래서 X는 hallucination **상한**일 뿐 실제론 훨씬 작음.

### 🧮 정확히 어떻게 계산했나 (알고리즘)
1. **대상**: 보존 롤아웃 gz **36개(=이 실험 batch b000~b035 전부)**를 스트리밍, `result=="INVALID"` 이고 tactic head∈{apply,eapply,rewrite,erewrite}인 step만. (apply=apply+eapply 14,433 / rewrite=rewrite+erewrite 10,486)
2. **사용 lemma 추출**: tactic head 뒤에서 `<-`/`->` 제거 후 **첫 식별자**(모듈수식 `PMap.gss` 유지, `in/with/by/at/as` 키워드는 건너뜀). 예 `apply Zle_0_eq in H` → `Zle_0_eq`.
3. **검색후보 head 집합**: 그 step의 `example.premises`(후보 50개 텍스트) 각각에서 `Lemma NAME:` 의 `NAME` 추출 → 50개 head 집합.
4. **로컬 가설 집합**: `example.proof_state`의 `⊢`(goal) **위쪽** 줄 `name : type`에서 `name`.
5. **분류(우선순위대로, 먼저 걸리는 것)**:
   - 사용 lemma가 **검색후보 head에 있으면 → R1** (그 인덱스+1을 순위로 기록; `premises[0]`=최상위 랭킹).
   - 아니고 **로컬 가설이면 → H**.
   - 아니고 **사전(206k)에 있으면 → E**.
   - 다 아니면 → **X**.
   - 모듈 short명(`PMap.gss`→`gss`)도 양쪽에서 대조해 매칭 누락 방지.
6. **R1 순위 통계**: R1로 분류된 것들의 기록 순위로 중앙값·top5내·top10내 비율 계산 → (apply 중앙 5위/top5 55%, rewrite 중앙 4위/top5 58%).
- 재현: 위 로직은 일회성 분석 스크립트(스크래치)로 실행. 확정판은 `coq_error` 기반 `scripts/classify_rollout_errors.py`.

관련: [[TYPE_LEARNING_RESEARCH]] · [[record-rollout-errors]] · [[apply-invalid-mostly-real-ref]] · [[../grpo/TOKEN_VS_TACTIC_CREDIT]] · [[../grpo/rango_augmented/AUGMENTED_FINAL]]
