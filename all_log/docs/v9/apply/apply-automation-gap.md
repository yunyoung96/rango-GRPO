# v9 프롬프트는 `apply` 에 필요한 정보를 갖고 있나

> 한 줄 요약: **아니다.** `apply` 가 하는 다섯 가지 중 프롬프트가 받쳐 주는 것은
> **③ 결론 단일화**와 **⑤ subgoal 개수** 둘뿐이다. ① 이름 해석 · ② 타입 확보 ·
> ④ evar 해소에 필요한 정보는 `sentences.db` 단계에서 이미 **버려져 있어서**
> 프롬프트를 아무리 키워도 들어오지 않는다.

이 문서는 실제 스텝 하나를 골라 **Coq 쪽 사정 → 프롬프트가 만들어지는 경로 →
완성된 프롬프트 전문 → 무엇이 없어서 무슨 일이 나는가** 를 끝까지 따라간다.

- 재현 스크립트: `scripts/dump_one_prompt.py`
- 이 문서가 쓴 프롬프트 원본: `all_log/docs/v9/apply/example-prompt.txt`

> 짝이 되는 문서: [`apply-rewrite-forms.md`](apply-rewrite-forms.md) 는 **증상**을 잰다 —
> 위치 인자형 `apply (L a _ c)` 42.9% · `apply L a b` 44.1% 가 맨 `apply` 17.1% 보다
> 나쁘고, 이유를 "arity 와 순서를 모르기 때문"으로 짚는다. 이 문서는 **왜 모를 수밖에
> 없는지**를 짚는다 — 진짜 arity 가 프롬프트에 없다(§4-②, 선언의 11.3%).

---

## 0. `apply` 는 무엇을 하는 기계인가

`apply c` 는 한 덩어리가 아니라 다섯 단계다. 각 단계가 **서로 다른 정보**를 먹는다.

```
① 이름 해석    c 라는 글자를 지금 이 시점의 환경에서 상수로 바꾼다
               (Import 상태 · 모듈 경로 · 펑터가 만들어 낸 이름)
② 타입 확보    그 상수의 타입을 커널에서 읽는다
               (섹션 변수 방출 · Set Implicit Arguments · Arguments 지시가 반영된 것)
③ 결론 단일화  타입을 ∀x…, H₁→…→C 로 쪼개고 x 를 evar 로 둔 뒤
               C 를 goal 과 맞춘다 — **conversion(δ 펼침)까지 허용**하면서
④ evar 해소    남은 구멍을 typeclass instance · canonical structure · coercion 으로 메운다
⑤ subgoal      못 푼 전제 H_i 를 순서대로 남긴다
```

"apply 가 알아서 해 준다"는 말은 ③④를 가리킨다. 그런데 **③④가 돌기 전에 ①②가
성립해야 한다.** 우리 프롬프트가 빠뜨린 곳이 정확히 거기다.

---

## 1. 예제 — CompCert `Unusedglobproof.v`, gold 는 `apply list_forall2_app.`

```
데이터포인트  /tmp/coq-dataset/data_points/AbsInt-CompCert-backend-Unusedglobproof.v
proof 52 · step 5
gold tactic   apply list_forall2_app.
```

이 파일은 `splits/official-split.json` 의 `test_files` 에 있다 — 학습에 안 들어간다.
즉 **평가에서 실제로 만나는** 스텝이다.

### 1-1. 그 시점의 goal (정규화 전, 데이터포인트 원문)

```coq
p, tp: program
used: IS.t
USED_VALID: valid_used_set p used
TRANSF: match_prog_1 used p tp
ge, tge: Genv.t fundef unit
pm: PTree.t (globdef fundef unit)
m, tm: mem
IM: Genv.init_mem p = Some m
TIM: Genv.init_mem tp = Some tm
i1: init_data
il: list init_data
IHil: (forall id : ident, ref_init il id -> kept id) ->
      list_forall2 (memval_inject init_meminj) (Genv.bytes_of_init_data_list ge il)
                                               (Genv.bytes_of_init_data_list tge il)
H: forall id : ident, ref_init (i1 :: il) id -> kept id

list_forall2 (memval_inject init_meminj)
  (Genv.bytes_of_init_data ge i1 ++ Genv.bytes_of_init_data_list ge il)
  (Genv.bytes_of_init_data tge i1 ++ Genv.bytes_of_init_data_list tge il)
```

goal 의 `list_forall2` 는 **인자가 셋**이다 — `(memval_inject init_meminj)`, 그리고
`++` 로 붙은 리스트 둘.

### 1-2. `list_forall2_app` 의 소스 원문 (`lib/Coqlib.v:1148`)

```coq
Section FORALL2.

Variable A: Type.
Variable B: Type.
Variable P: A -> B -> Prop.          ← ★ 이 셋이 문제의 전부다

Inductive list_forall2: list A -> list B -> Prop :=
  | list_forall2_nil:  list_forall2 nil nil
  | list_forall2_cons: forall a1 al b1 bl,
      P a1 b1 -> list_forall2 al bl -> list_forall2 (a1 :: al) (b1 :: bl).

Lemma list_forall2_app:
  forall a2 b2 a1 b1,
  list_forall2 a1 b1 -> list_forall2 a2 b2 ->
  list_forall2 (a1 ++ a2) (b1 ++ b2).      ← 인자가 **둘**이다
Proof. induction 1; intros; simpl. auto. constructor; auto. Qed.

...
End FORALL2.
```

섹션 안에서는 `A B P` 가 문맥에 떠 있으므로 `list_forall2 a1 b1` 이라고 쓴다.
`End FORALL2.` 를 만나는 순간 Coq 은 **쓰인 섹션 변수를 앞으로 방출한다.**
그래서 밖에서 본 진짜 타입은 이렇게 된다.

```coq
list_forall2_app
  : forall (A B : Type) (P : A -> B -> Prop)
           (a2 : list A) (b2 : list B) (a1 : list A) (b1 : list B),
    list_forall2 P a1 b1 -> list_forall2 P a2 b2 ->
    list_forall2 P (a1 ++ a2) (b1 ++ b2)
```

**이건 추측이 아니다.** 두 가지가 직접 확인해 준다.

1. 바로 다음 줄(`End FORALL2.` 아래)의 `list_forall2_imply` 는 같은 파일에서
   `list_forall2 P1 l1 l2` 라고 **P 를 명시해서** 쓴다.
2. §1-1 의 실제 goal 이 `list_forall2 (memval_inject init_meminj) … …` 로
   **세 인자**를 보여 준다.

### 1-3. 그런데 `sentences.db` 에 저장된 것은 소스 원문 그대로다

```
text          Lemma list_forall2_app: forall a2 b2 a1 b1, list_forall2 a1 b1 ->
              list_forall2 a2 b2 -> list_forall2 (a1 ++ a2) (b1 ++ b2).
module        []
sentence_type TermType.LEMMA
file_path     /coq-dataset/repos/AbsInt-CompCert/lib/Coqlib.v
line          1162
```

`A`, `B`, `P` 라는 글자가 어디에도 없다. `Variable A: Type.` 이라는 줄은
**DB 에 아예 없다**(§4 참조).

---

## 2. 프롬프트가 만들어지는 경로

`scripts/dump_one_prompt.py` 가 추론과 같은 경로로 부르는 순서다.

| # | 하는 일 | 코드 |
|---|---|---|
| 1 | goal 의 식별자로 질의를 만든다 | `premise_client.get_premise_scores` |
| 2 | 후보 풀을 **필터**한다 (`proj-thm`) | `premise_filter.PremiseFilter` |
| 3 | tfidf 로 stage1 5,000개를 고른다 | `tier_rank.STAGE1` |
| 4 | 구조 재랭킹 `afh70` 으로 다시 세운다 | `tier_rank.structural_scores` |
| 5 | 상위 100개를 `[PREMISES]` 후보로 넘긴다 | `num_premises: 100` |
| 6 | 타입지향 재랭킹을 한 번 더 건다 | `tactic_data.rerank_premises` |
| 7 | 896토큰까지 담고 **역순**으로 출력한다 | `allocate_and_fmt(..., reverse=True)` |
| 8 | bm25 로 유사 증명 12개 → 256토큰 | `num_proofs: 12` / `proof_tokens` |
| 9 | `[TYPES]`/`[DEFINITIONS]`/notation 을 뒤에 붙인다 | `tactic_data.augment_v2_section` |
| 10 | 이름을 전부 익명화한다 | `_maybe_normalize_input` |

핵심은 **2번**이다. `known_filter: proj-thm` 은 풀을 이렇게 자른다.

```
프로젝트 파일    THEOREM · LEMMA · FACT · REMARK · COROLLARY · PROPOSITION · PROPERTY   ← 남는다
                DEFINITION · INDUCTIVE · RECORD · CLASS · INSTANCE · FIXPOINT ·
                NOTATION · OTHER                                                       ← 전부 뺀다
stdlib 파일      **전 종류 제외** — 한 줄도 안 들어온다
```

`premise_format_alias: basic` 이고 `BasicPremiseFormat.format` 은
`return sentence.text` 한 줄이다(`premise_selection/premise_formatter.py:47`).
즉 **`Sentence.module` 필드가 있는데도 프롬프트에는 안 쓴다.**

7번의 `reverse=True` 때문에 `[PREMISES]` 는 **맨 아랫줄이 1위**다.
10번의 `_L#` 번호는 검색(afh70) 순위 순으로 붙으므로 `_L0` 이 1위다.

---

## 3. 완성된 프롬프트 (전문 · 2,003토큰 / 상한 3,072)

전문은 `all_log/docs/v9/apply/example-prompt.txt`. 여기서는 문제가 되는 부분만 인용한다.

### 3-1. `[PREMISES]` 의 마지막 네 줄 (= 순위 4위 → 1위)

```
Lemma _L1: forall f vl, list_forall2 (memval_inject f) (List.repeat _T1 (length vl)) vl.
Inductive list_forall2: list A -> list B -> Prop := | list_forall2_nil: list_forall2 nil nil | list_forall2_cons: forall a1 al b1 bl, P a1 b1 -> list_forall2 al bl -> list_forall2 (a1 :: al) (b1 :: bl).
Theorem _L9: forall f v1 v2 chunk, Val.inject f v1 v2 -> list_forall2 (memval_inject f) (encode_val chunk v1) (encode_val chunk v2).
Lemma _L0: forall a2 b2 a1 b1, list_forall2 a1 b1 -> list_forall2 a2 b2 -> list_forall2 (a1 ++ a2) (b1 ++ b2).
```

**검색은 정답을 1위로 맞혔다.** `_L0 = list_forall2_app` 이다.
그런데 같은 화면 안에서 `list_forall2` 가 **두 가지 arity 로 동시에** 등장한다.

```
_L1 · _L9        list_forall2 (memval_inject f) … …      ← 인자 3개 (섹션 밖 정리라 P 가 보인다)
_L0 · Inductive  list_forall2 … …                        ← 인자 2개 (섹션 안 원문)
```

무엇이 맞는지 가려 줄 정보는 프롬프트 어디에도 없다. `Variable P: A -> B -> Prop.`
한 줄만 있으면 되는데 그 줄은 `sentences.db` 에 없다.

> 곁가지 — `Inductive list_forall2` 는 `proj-thm` 이 INDUCTIVE 를 빼는데도 실려 있다.
> `PREMISE_ADMIT_USED=1` 이 "제외 종류지만 프로젝트에서 tactic 인자로 실제로 쓰인 것"을
> 되살리기 때문이다(`data/used_names.json`: `list_forall2` = 10회 · 7파일, 기준은
> `ADMIT_MIN_FILES=2`). 이 장치는 **의도대로 돌고 있다** — 그래서 문제가 검색이 아니라
> **실린 문장의 내용**이라는 것이 더 분명해진다.

### 3-2. `[STATE]` (익명화 후)

```
i1: init_data
il: list init_data
IHil: (forall id : _f10, _f11 il id -> _f12 id) ->
list_forall2 (memval_inject _f3) (Genv._f5 ge il)
  (Genv._f5 tge il)
H: forall id : _f10, _f11 (i1 :: il) id -> _f12 id

list_forall2 (memval_inject _f3)
  (Genv._f4 ge i1 ++ Genv._f5 ge il)
  (Genv._f4 tge i1 ++ Genv._f5 tge il)
```

### 3-3. 정답

```
gold      apply list_forall2_app.
프롬프트   apply _L0.
```

---

## 4. 그래서 무엇이 없나 — 단계별

### ① 이름 해석 — **없다**

프롬프트는 `Lemma gss : …` 처럼 **모듈 경로를 뗀 이름**만 보여 준다.
`Sentence.module` 은 채워져 있는데 `BasicPremiseFormat` 이 안 쓴다.

측정 (coqstoq-test 60파일, `apply`/`eapply` 인자 3,293건):

```
apply            2,534   77.0%
eapply             759   23.0%
한정이름 M.f        400   12.1%   ← 프롬프트만 보고는 M 을 복원할 방법이 없다
```

여기에 **펑터가 만든 이름**이 더 얹힌다. CompCert 가 tactic 인자로 쓰는 한정 이름의
**27.0%**(9,523회 중 2,575회, 337종)는 소스 어디에도 선언이 없다 —
`Module Pregmap := EMap(PregEq).` 한 줄이 만들어 내기 때문이다.
자세한 것은 `all_log/docs/premise/functor-names.md`.

### ② 타입 확보 — **없다**

premise 는 **소스 선언문 그대로**다. elaborate 를 거친 타입이 아니다.
그래서 다음 셋이 프롬프트에 원리적으로 안 들어온다.

- **섹션 변수 방출** — 이 문서의 예제가 그것이다
- **`Set Implicit Arguments`** — implicit 이 `{A}` 로 적혀 있을 때만 보인다
- **`Arguments` 지시** — 나중 줄에서 implicit/스코프를 바꾼 것

`sentences.db` 582,037행 전수 조회:

```
Set Implicit Arguments            0 행
Arguments …                       1 행
Variable / Hypothesis / Context   0 행
Existing Instance                 0 행
Section                           2 행
Hint …                          355 행
Coercion                        284 행
Canonical                     1,193 행
Module N := F(A)                324 행   ← TermType.OTHER 라 풀에서 제외
```

실제 소스에는 이만큼 있다 (`/tmp/coq-dataset/repos`, `.v` 101,460개):

```
Set Implicit Arguments      15,615 파일  (15.4%)
Arguments 지시              10,386 파일  (10.2%)
Section                     32,829 파일  (32.4%)
Variable/Hypothesis/Context 30,026 파일  (29.6%)
```

**15,615개 파일이 선언한 것을 DB 는 0행 갖고 있다.**

얼마나 자주 물리나 — 표본 2,500파일 · 선언 57,062개
(판정: 선언이 Section 안에 있고 그 섹션 변수 이름이 statement 본문에 실제로
등장하면 방출된다. 안 쓰인 변수는 방출되지 않으므로 세지 않았다 — **하한**이다):

```
Section 안 선언                18,150   31.8%
★ 방출로 타입이 달라지는 선언     6,434   11.3%
```

즉 **프롬프트에 실리는 premise 문장 9개 중 1개는 실제 타입과 다르다.**

### ③ 결론 단일화 — **있다**

goal 전문(`[STATE]`, 여러 goal 은 `[GOAL]` 로 구분)과 premise 결론이 모두 있다.
`apply` 가 하는 일 중 프롬프트가 온전히 받쳐 주는 유일한 단계다.

### ③′ conversion (δ 펼침) — **부분만 있다**

`apply` 는 문법이 아니라 **변환까지 봐서** 맞춘다. 그러려면 정의가 필요하다.
그런데 DEFINITION 154,558행 · FIXPOINT 26,140행은 검색 풀 밖이고,
통로는 `[DEFINITIONS]` 주입 하나뿐이다. 그 주입에는 캡이 둘 있다.

- 블록 전체 `DEFS_TOKENS=300`
- **항목당 `cap=60`** (`augment._shorten`) — 넘으면 `:=` 앞 시그니처만 남긴다

이 프롬프트에 실제로 그 일이 일어났다.

```
프롬프트   Definition _f4 (i: init_data): list memval          ← 본문이 없다
인덱스     Definition bytes_of_init_data (i: init_data): list memval :=
             match i with | Init_int8 n => inj_bytes (encode_int 1%nat …) | … end
```

인덱스(`data/func_defs_v3.json`)에는 본문이 **다 있는데** 프롬프트에서 잘렸다.
시그니처만으로도 타입 정보는 되지만, δ 펼침에 필요한 것은 **본문**이다.
(이 예제에서는 펼침이 필요 없어 결과에 영향은 없다.)

### ③″ notation / scope — **부분만 있다**

`NOTATION_PROJ=1` 이 goal 에 실제로 나타난 기호로 프로젝트 notation 을 앵커링해
넣는다(발화율 23.1%). stdlib notation 과 scope(`%Z` 등)는 없다.

### ④ evar 해소 — **없다**

typeclass instance · canonical structure · coercion 은 `apply` 가 마지막에 구멍을
메우는 수단인데 프롬프트에 한 줄도 없다.
INSTANCE 는 DB 에 **19,714행이나 있는데** `proj-thm` 이 통째로 뺀다.
Coercion·Canonical 은 DB 자체에 사실상 없다(위 표).

### ⑤ subgoal 개수 — **있다**

전제 개수와 순서는 문장에서 읽힌다. 변수가 결론에 안 나타나면 `eapply` 가 필요하다는
판단도 문장만으로 가능하다. 실제로 gold 의 23.0% 가 `eapply` 이고 이건 배울 수 있다.

### 그 밖 — stdlib 은 통째로 없다

`proj-thm` 의 `coq_excludes` 가 stdlib 전 종류를 뺀다.
`app_assoc`, `in_or_app` 같은 것으로 하는 `apply` 는 **전적으로 사전학습 기억**이다.

---

## 5. 우리 판정기도 같은 이유로 틀린다

`src/tactic_gen/applicable.py` 는 premise 를 `∀x…, H→…→C` 로 파싱해 바인더를
메타변수로 두고 C 를 goal 결론과 단방향 단일화한다 — 위 **③⑤의 축소판**이다.
같은 쌍을 두 형태로 먹여 보면 이렇게 갈린다.

```python
goal   = "… list_forall2 (memval_inject init_meminj) (… ++ …) (… ++ …)"

# (a) 프롬프트에 실리는 것 = 소스 원문
"Lemma list_forall2_app: forall a2 b2 a1 b1, list_forall2 a1 b1 -> …"
    → {'apply': False, 'rw': False, 'rw_rev': False, 'parsed': True}

# (b) 실제 타입 = 섹션 변수 방출 후
"Lemma list_forall2_app: forall (A B : Type) (P : A -> B -> Prop) a2 b2 a1 b1,
   list_forall2 P a1 b1 -> list_forall2 P a2 b2 -> list_forall2 P (a1 ++ a2) (b1 ++ b2)."
    → {'apply': True,  'rw': False, 'rw_rev': False, 'parsed': True}
```

gold 는 `apply list_forall2_app.` 이고 Coq 에서 **된다**. 즉 (a) 는 오답이다.

파서가 나쁜 게 아니다. **먹인 문장이 실제 타입이 아니다.** 모델이 읽는 것도 (a) 다.

> 참고 — 이 판정은 프로덕션 랭킹에는 안 쓰인다.
> `rerank_premises` 의 `APPLICABLE_RERANK` 기본값은 `0` 이고(`tactic_data.py:103`),
> 프로덕션 랭커 `afh70`(`tier_rank.structural_scores`)은 RRF(tfidf)+RRF(C′)+
> α-동치 커널로만 세운다. 판정기는 만들어 두고 **랭킹에도 프롬프트에도 안 넣은
> 상태**다.

---

## 6. 두 번째 예제 — 이름 자체가 풀에 없는 경우

`backend/Asmgenproof0.v` 의 한 정리에서 gold 10스텝 중 9개를 채워 주고 마지막
`rewrite Pregmap.gso; auto.` 하나만 맡겼다.

```
모델이 시도한 것   94회 · 서로 다른 58종
Pregmap            뱉었다 (문맥은 읽었다)
gso                한 번도 안 나왔다
대신               apply H1.(7회) · red.(5회) · exact preg_val.(4회)
```

`Pregmap.gso` 는 CompCert 에서 40회 쓰이는데 선언은 0회다.
`Module Pregmap := EMap(PregEq).` 가 만들어 내고, DB 에는 `module=["EMap"]` 인
추상 명제만 있다. `try_candidates` 를 늘려도, 형태 변형 DPO 를 해도 안 고쳐진다 —
**후보 분포에 그 이름이 없다.** (`all_log/docs/premise/functor-names.md`)

---

## 7. 이 프롬프트에서 눈에 띈 다른 것들

전문을 읽다 보면 apply 와 직접 관련은 없지만 자리를 먹는 것들이 보인다.

```
Theorem shift_symbol_address: …        ← 같은 줄이 두 번 실렸다 (다른 파일의 동일 정리)
Notation mem := Mem.mem.
Definition mem := mem'.                ← 같은 이름 두 줄이 서로 다른 것을 가리킨다
Record _T0 : Set := { _f0 : A; key : nat }.     ← A 가 어디에도 안 묶여 있다 (같은 섹션 문제)
Inductive _f2 {A: Type} {s: state}: Type := R … ← 이 goal 과 무관
```

`Record _T0` 은 §4-② 와 **같은 병**이다 — `[TYPES]` 로 주입한 정의도 소스 원문이라
섹션 변수가 빠져 있다. 주입 경로를 고쳐도 원천이 같으면 같은 구멍이 남는다.

---

## 8. 규모 요약

| 무엇 | 수치 | 출처 |
|---|---|---|
| gold lemma 가 프롬프트에 있는 비율 | 77% | `normalize_names.premise_names` 주석 |
| `apply`/`eapply` 인자 중 한정 이름 | 12.1% | coqstoq-test 60파일 3,293건 |
| CompCert 한정 이름 중 선언 없음(펑터) | 27.0% | `premise/functor-names.md` |
| 섹션 변수 방출로 타입이 달라지는 선언 | 11.3% (하한) | repos 표본 2,500파일 57,062선언 |
| `Set Implicit Arguments` 를 쓰는 파일 | 15.4% | repos 전수 101,460 |
| `Arguments` 지시를 쓰는 파일 | 10.2% | repos 전수 101,460 |
| 그 명령들이 `sentences.db` 에 있는 행 | 0 / 1 / 0 | 582,037행 전수 |
| 풀에서 제외되는 INSTANCE | 19,714행 | `proj-thm` |
| 풀에서 제외되는 stdlib | 전 종류 | `proj-thm` `coq_excludes` |

---

## 9. 고칠 수 있는 것 — 비용순

### (1) 모듈 경로를 붙인다 — 가장 싸다

`Sentence.module` 이 이미 채워져 있다. `BasicPremiseFormat.format` 이
`sentence.text` 대신 한정 이름을 앞에 붙이면 된다. Coq 실행이 필요 없다.
`[PREMISES]` 안에 동명이 실리는 예제가 41.1% 라는 기존 실측이 있으므로
익명화의 "동명이면 매핑에서 뺀다" 규칙도 함께 완화할 수 있다.

### (2) 펑터 인스턴스를 전개한다 — 싸다

`Module N := F(A).` 은 이미 `TermType.OTHER` 로 DB 에 있다. 그 줄을 파싱해
F 의 멤버를 `N.*` 이름으로 복제하면 된다. CompCert 기준 43개 모듈뿐이고
Coq 실행이 필요 없다. (`PREMISE_ADMIT_USED` 로는 못 살린다 — 그건 선언이 있는데
종류로 빠진 경우를 구제하는 장치다.)

### (3) 섹션 변수를 방출한 문장을 저장한다 — 중간

인덱스를 만들 때 `Section`/`End`/`Variable` 을 추적해, 실제로 쓰인 변수를 앞에
`forall` 로 붙인 문장을 함께 저장한다. Coq 실행 없이 텍스트 처리로 되고,
§5 의 판정기 오답도 같이 고쳐진다. **먼저 해 볼 값어치가 가장 큰 항목이다** —
11.3% 를 한 번에 되돌린다.

### (4) elaborate 된 타입을 받아 온다 — 비싸다

인덱스 빌드 때 Coq 을 띄워 `About`/`Print` 로 진짜 타입을 받는다.
`Set Implicit Arguments` · `Arguments` · 섹션 · 펑터가 **한 번에** 해결되지만
150개 프로젝트를 다시 컴파일해야 한다.

### (5) ④를 위한 주입 — 미지수

INSTANCE 를 풀에 넣거나 `[DEFINITIONS]` 처럼 goal 앵커링으로 instance/coercion 을
주입한다. 효과 근거가 아직 없다.

### 하지 말 것 — 예산 늘리기

`TYPES_TOKENS`/`DEFS_TOKENS` 를 300→400/600 으로 올린 실험(2026-08-22)은
환각률 17.6% → 17.6% 로 **전혀 안 움직였고** premise 만 14.4 → 13.5 로 줄었다.
문제는 **양이 아니라 종류**다. 이 문서가 든 예제도 프롬프트가 2,003/3,072 토큰이라
자리가 1,000토큰 넘게 남아 있었다.

---

## 10. 재현

```bash
# 프롬프트 전문
PYTHONPATH=src python3 scripts/dump_one_prompt.py \
    /tmp/coq-dataset/data_points/AbsInt-CompCert-backend-Unusedglobproof.v 52 5

# 소스 원문
sed -n '1148,1200p' /tmp/coq-dataset/repos/AbsInt-CompCert/lib/Coqlib.v

# DB 에 저장된 모습 · 그 명령들이 DB 에 없다는 것 (sqlite3 CLI 는 이 환경에 없다)
python3 -c "
import sqlite3
c = sqlite3.connect('raw-data/coq-dataset/sentences.db')
for r in c.execute(\"select text, module, sentence_type from sentence where text like 'Lemma list_forall2_app%'\"):
    print(r)
for pat in ('Set Implicit%', 'Arguments %', 'Variable%', 'Section %'):
    n = c.execute('select count(*) from sentence where text like ?', (pat,)).fetchone()[0]
    print(pat, n)
"

# 판정기가 두 형태에서 갈리는 것
PYTHONPATH=src python3 -c "
from tactic_gen.applicable import applicability
g='list_forall2 (memval_inject init_meminj) (a ++ b) (c ++ d)'
print(applicability(g, 'Lemma f: forall a2 b2 a1 b1, list_forall2 a1 b1 -> list_forall2 a2 b2 -> list_forall2 (a1 ++ a2) (b1 ++ b2).'))
print(applicability(g, 'Lemma f: forall (A B : Type) (P : A -> B -> Prop) a2 b2 a1 b1, list_forall2 P a1 b1 -> list_forall2 P a2 b2 -> list_forall2 P (a1 ++ a2) (b1 ++ b2).'))
"
```
