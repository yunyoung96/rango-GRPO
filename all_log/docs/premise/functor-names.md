# 왜 `Pregmap.gso` 는 검색으로 못 찾나 — Coq 모듈 시스템과 우리 검색 풀

> 한 줄 요약: **CompCert 가 tactic 인자로 쓰는 이름의 27% 는 소스 어디에도 선언되어
> 있지 않다.** 모듈 시스템이 만들어 내는 이름이기 때문이다. 우리 검색 풀은
> "선언문"으로 만들어지므로, 그 이름들은 **원리적으로 풀에 없다.**

---

## 1. Coq 모듈 시스템 — 문법 4단계

### 1-1. `Module` — 그냥 이름공간

```coq
Module PregEq.
  Definition t  := preg.        (* 프로세서 레지스터 타입 *)
  Definition eq := preg_eq.     (* 그 동등성 판정 함수 *)
End PregEq.
```

`x86/Asm.v:305`. 안의 것들은 밖에서 `PregEq.t`, `PregEq.eq` 로 부른다.
**이건 소스에 그대로 쓰여 있다.** `grep "Definition t"` 하면 나온다.

### 1-2. `Module Type` — 인터페이스(시그니처)

```coq
Module Type EQUALITY_TYPE.
  Parameter t: Type.
  Parameter eq: forall (x y: t), {x = y} + {x <> y}.
End EQUALITY_TYPE.
```

`lib/Maps.v:1421`. `Parameter` 는 **선언만 하고 정의하지 않는다** — "이런 게 있어야
한다"는 요구사항이다. 정리에 해당하는 요구사항은 `Axiom` 으로 쓴다:

```coq
Module Type MAP.
  Parameter elt: Type.
  Parameter t: Type -> Type.
  Parameter get: forall (A: Type), elt -> t A -> A.
  Parameter set: forall (A: Type), elt -> A -> t A -> t A.
  Axiom gso:
    forall (A: Type) (i j: elt) (x: A) (m: t A),
    i <> j -> get i (set j x m) = get i m.
  ...
End MAP.
```

`lib/Maps.v:151`. **여기서 `gso` 는 "요구사항"이지 증명된 정리가 아니다.**

### 1-3. `Module F (X : T)` — 펑터, 즉 **모듈을 받아 모듈을 만드는 함수**

```coq
Module EMap(X: EQUALITY_TYPE) <: MAP.

  Definition elt := X.t.                         (* 키 타입은 X 가 정한다 *)
  Definition t (A: Type) := X.t -> A.            (* 맵 = 키→값 함수 *)
  Definition get (A: Type) (x: X.t) (m: t A) := m x.
  Definition set (A: Type) (x: X.t) (v: A) (m: t A) :=
    fun (y: X.t) => if X.eq y x then v else m y.

  Lemma gso:
    forall (A: Type) (i j: elt) (x: A) (m: t A),
    i <> j -> (set j x m) i = m i.
  Proof.
    intros. unfold set. case (X.eq i j); intro.
    congruence. reflexivity.
  Qed.

End EMap.
```

`lib/Maps.v:1426`. 읽는 법:

* `EMap(X: EQUALITY_TYPE)` — "`EQUALITY_TYPE` 을 만족하는 모듈 `X` 를 하나 주면"
* `<: MAP` — "내가 돌려주는 것은 `MAP` 시그니처를 만족한다"
  (`<:` 는 **투명** 부여 — 안의 정의가 밖에서도 보인다. `:` 로 쓰면 **봉인**되어
  `set` 의 본문이 안 보이고 시그니처만 남는다. CompCert 는 `<:` 를 써서 `unfold` 가 된다)

★ **`EMap` 자체는 모듈이 아니다.** 함수다. `EMap.gso` 를 직접 쓸 수는 없다.

### 1-4. `Module N := F(A)` — 펑터 적용(인스턴스화)

```coq
Module Pregmap := EMap(PregEq).
```

`x86/Asm.v:310`. **이 한 줄**이 실행되는 순간 Coq 환경에

```
Pregmap.elt   Pregmap.t     Pregmap.get   Pregmap.set
Pregmap.gi    Pregmap.gss   Pregmap.gso   …
```

가 **전부 생겨난다.** `X` 자리에 `PregEq` 가 대입된 형태로.

```coq
(* EMap 안의 원본 *)
Lemma gso: forall (A: Type) (i j: elt) (x: A) (m: t A),
  i <> j -> (set j x m) i = m i.

(* Pregmap.gso 로 구체화된 것 — elt := PregEq.t := preg *)
Pregmap.gso : forall (A: Type) (i j: preg) (x: A) (m: preg -> A),
  i <> j -> (Pregmap.set j x m) i = m i.
```

---

## 2. 핵심 — **그 이름은 소스 어디에도 쓰여 있지 않다**

```bash
$ grep -rn "Lemma Pregmap.gso" .          # 아무것도 안 나온다
$ grep -rn "Pregmap\.gso" . | head -3     # 나오는 건 전부 **사용처**
backend/Asmgenproof0.v:92:  ... apply Pregmap.gso. red; intro; subst. auto.
backend/Asmgenproof0.v:106: rewrite Pregmap.gso. auto. apply not_eq_sym. ...
backend/Asmgenproof0.v:115: rewrite IHrl by auto. rewrite Pregmap.gso; auto.
```

CompCert 전체에서 `Pregmap.gso` 는 **40회 사용**되는데 **선언은 0회**다.

비유하자면 쿠키 틀이다. `EMap` 이 틀, `PregEq` 가 반죽, `Pregmap` 이 찍어낸 쿠키.
쿠키에는 틀의 무늬가 다 있지만 **그 무늬를 손으로 새긴 적은 없다.**

(OCaml 이면 `module StringMap = Map.Make(String)` 뒤의 `StringMap.find`,
Java/C++ 면 `List<String>` 의 메서드와 같다. 컴파일러가 만들어 낸다.)

---

## 3. 우리 검색 풀은 **선언문**으로 만들어진다

`sentences.db` 는 소스를 훑어 **문장(sentence)** 단위로 저장한다.
582,037행이고 스키마는 `(id, text, file_path, module, sentence_type, line)` 이다.

즉 `Lemma gso: …` 라는 **줄**을 보고 한 행을 만든다. 그런데 그 줄은
**`EMap` 안**에 있으므로 저장되는 모습은:

```
module        = ["EMap"]
sentence_type = TermType.LEMMA
text          = "Lemma gso: forall (A: Type) (i j: elt) (x: A) (m: t A),
                 i <> j -> (set j x m) i = m i."
file_path     = /coq-dataset/repos/AbsInt-CompCert/lib/Maps.v
```

**`Pregmap` 이라는 글자는 어디에도 없다.**

그리고 `Module Pregmap := EMap(PregEq).` 이라는 줄은 저장되긴 하는데

```
sentence_type = TermType.OTHER      ← premise 후보가 아니다
```

로 들어간다. 즉 "이 둘이 같다"는 연결고리가 **풀 밖에** 있다.

### 실제 DB 조회 결과

```
'Pregmap.gso' 를 이름으로 갖는 문장          : 0
module 컬럼에 'Pregmap' 이 들어간 행         : 없음
'gso' 가 저장된 module                      : ["EMap"] ["PTree"] ["PMap"] ["IMap"] ["ITree"]
                                              ↑ 전부 **틀 이름**
'Module Pregmap := EMap(PregEq).'          : TermType.OTHER 로 딱 한 줄
```

---

## 4. 그래서 실제로 무슨 일이 일어났나

`backend/Asmgenproof0.v` 의 한 정리. gold 증명이 10스텝인데 **9스텝을 정답으로
채워 주고** 마지막 하나만 모델에게 맡겼다.

```coq
 0  intros.
 1  apply agree_set_mreg with (rs'#(preg_of r) <- (rs#(preg_of r))); auto.
 2  apply agree_undef_regs with rs; auto.
 3  intros.
 4  unfold Pregmap.set.                      (* set 의 정의를 편다 → if … then … else … *)
 5  destruct (PregEq.eq r' (preg_of r)).     (* if 의 조건을 두 가지로 가른다 *)
 6  congruence.                              (* 같은 가지 *)
 7  auto.
 8  intros.                                  ← 여기까지 줬다
 9  rewrite Pregmap.gso; auto.               ★ 남은 하나
```

5번에서 **같다/다르다**로 갈랐고 9번은 "다르다" 가지다. 문맥에
`n : r' <> preg_of r` 가 이미 있으니 `gso` 의 전제(`i <> j`)가 바로 충족된다.
**문맥이 `gso` 를 쓰라고 가리키고 있는 상황이다.**

결과: 모델은 **94회 · 서로 다른 58종**을 시도하고 실패했다.

* `Pregmap` 이라는 모듈 이름은 **나왔다** (문맥은 읽었다)
* `gso` 는 **한 번도 안 나왔다**
* 대신 `apply H1.`(7회) · `red.`(5회) · `exact preg_val.`(4회) 를 맴돌았다

`try_candidates` 를 8로 올려도, 형태 변형 DPO 를 해도 이건 안 고쳐진다.
**후보 분포에 그 이름이 없기 때문이다.**

---

## 5. 규모 — 예외적 사례가 아니다

CompCert 에서 `Module X := F(Y).` 꼴의 펑터 인스턴스가 **43개** 있다
(`Int`, `Pregmap`, `Regmap`, `Byte`, `EqSet`, `IS`, `Labelset`, `AE`, `DS`, …).

`apply` / `rewrite` / `exact` / `specialize` / `destruct` 등의 **인자**로 쓰인
한정 lemma 참조를 세면:

```
전체 9,523회  중  펑터 모듈 소속 2,575회 = 27.0%   (서로 다른 이름 337종)

  301  Int.ltu             179  Int.eq
  118  Int.unsigned_repr    86  Int.ltu_inv
   75  Int.eq_dec           68  Int.add_commut
   47  Int.eqm_refl         42  Int.eqm_unsigned_repr_l
   38  Pregmap.gso          35  Pregmap.gss
```

`Int` 은 `lib/Integers.v` 의 `Module Int := Make(Wordsize_32).` 이다.
**tactic 이 부르는 lemma 이름 넷 중 하나가 검색 불가능하다.**

---

## 6. `EMap.gso` 가 풀에 있는데도 소용이 없는 이유

앞서 "결론은 안 바뀐다"고 쓴 부분을 풀어 쓴다. 세 겹이다.

**(1) 이름이 다르다.** 검색이 `EMap.gso` 를 1위로 올려 프롬프트에 실어도,
모델이 프롬프트에서 보는 글자는 `EMap.gso` 다. Coq 에서 `apply EMap.gso` 는
**오류다** — `EMap` 은 모듈이 아니라 펑터라서 그 안의 이름을 직접 못 부른다.
증명이 쓸 수 있는 유일한 이름은 `Pregmap.gso` 인데, 그걸 알려면
`Pregmap = EMap(PregEq)` 를 알아야 한다.

**(2) 그 연결고리가 premise 로 안 실린다.** `Module Pregmap := EMap(PregEq).` 은
`TermType.OTHER` 라 premise 후보에서 빠진다. 프롬프트에 그 줄이 들어갈 경로가 없다.

**(3) 랭킹도 안 올라간다.** `EMap.gso` 의 명제는 추상 타입으로 쓰여 있다:

```coq
forall (A: Type) (i j: elt) (x: A) (m: t A), i <> j -> (set j x m) i = m i
```

`elt`·`t A` 는 **아무 타입이나** 될 수 있는 이름이다. 반면 goal 은 레지스터
(`preg`)와 `Pregmap.set` 에 관한 것이다. 어휘가 `set` 과 `<>` 정도만 겹친다.
우리 랭커(afh70)는 명제의 α-정규형 구조 유사도를 보는데, 추상형과 구체형은
구조가 닮았어도 **이름이 전부 다르다.** 상위 100 안에 들 이유가 없다.

---

## 7. stdlib 이야기는 왜 **별개**인가

여기서 헷갈리기 쉬운 점 하나. `gso` 라는 **맨 이름**은 Coq stdlib 에도 있다:

```
/root/.opam/coqstoq/lib/coq/theories/FSets/FMapPositive.v:201  Theorem gss:
                                                        :210  Theorem gso:
```

이건 `PositiveMap.gso` — **다른 맵 타입에 대한 다른 정리**다. 이름만 같다.

우리 코드에는 stdlib 를 다루는 장치가 **둘** 있고, **판정 기준이 다르다.**

| 장치 | 판정 기준 | 무엇을 바꾸나 |
|---|---|---|
| `is_stdlib_name` | **맨 이름** (`name.split(".")[-1]`) | **익명화**만 — stdlib 이름은 `_L#` 로 안 바꾼다 |
| `PremiseFilter` | **파일 경로**에 `lib/coq/theories` 가 있는가 | **검색 풀** 구성 |

```python
# normalize_names.py:138
def is_stdlib_name(name: str) -> bool:
    n = (name or "").split(".")[-1]      # Pregmap.gso → "gso"
    return n in _stdlib_names()          # → True (충돌!)

# premise_filter.py:174
from_coq = os.path.join("lib", "coq", "theories") in premise.file_path
if from_coq and (premise.sentence_type in self.coq_excludes):   # LEMMA 포함
    return False                                                 # 풀에서 제외
```

`EMap.gso` 의 경로는 `/coq-dataset/repos/AbsInt-CompCert/lib/Maps.v` 다.
`lib/coq/theories` 가 없으므로 `from_coq = False` → 프로젝트 코드로 분류 →
`non_coq_excludes` 에 LEMMA 가 없으므로 **풀에 정상적으로 들어간다.**

즉 **stdlib 필터는 이 문제와 무관하다.** 맨 이름 충돌은 익명화에만 영향을 주고,
그건 "stdlib 이름은 안 바꾼다"는 안전한 쪽 동작이라 지금 해롭지 않다.
(CompCert Lemma/Theorem 5,879개 중 162개 = 2.8% 가 이 충돌 상태다.)

**정리: stdlib 분류 문제가 아니라 펑터 이름 문제다.**

---

## 8. 고치는 법 — 재료는 DB 에 이미 다 있다

`Module Pregmap := EMap(PregEq).` 이 `TermType.OTHER` 로 **이미 저장돼 있다.**
그러니 일회성 인덱스 작업으로 풀 수 있다.

```
① OTHER 문장에서 `Module <N> := <F>(<A>).` 를 파싱   → (Pregmap, EMap, PregEq)
② module = ["EMap"] 인 LEMMA/THEOREM 문장을 모두 긁는다
③ 이름을 `Pregmap.gso` 로 바꿔 풀에 추가한다
```

명제 본문은 두 선택지가 있다.

* **싼 것** — 추상 명제를 그대로 두고 이름만 바꾼다.
  `Pregmap.gso : forall (A: Type) (i j: elt) …`
  → 랭킹은 여전히 약하지만 **이름이 프롬프트에 실린다.** 지금은 그것조차 없다.
* **정확한 것** — `A` 의 정의를 따라 치환한다 (`elt := PregEq.t := preg`).
  `Pregmap.gso : forall (A: Type) (i j: preg) (x: A) (m: preg -> A) …`
  → 어휘가 goal 과 겹쳐 **랭킹도 올라간다.** 치환은 `PregEq` 의 `Definition t := preg`
  를 따라가면 되므로 Coq 실행 없이 텍스트로 가능하다.

43개 모듈뿐이므로 비용이 작다. Coq 을 돌릴 필요도, 새 파싱기를 만들 필요도 없다.

### 참고 — 기존 장치와의 관계

`PREMISE_ADMIT_USED=1` 은 "제외 종류라도 tactic 인자로 실제 쓰인 이름은 풀에 되살린다"
는 장치다. 이름이 **선언으로 존재하는데 종류 때문에 빠진 경우**를 구제한다.
`Pregmap.gso` 는 **선언 자체가 없으므로** 이 장치로도 못 살린다. 다른 문제다.

---

## 부록 — 재현

```bash
# 선언이 없다
grep -rn "Lemma Pregmap.gso" CoqStoq/test-repos/compcert          # 0건
grep -rc "Pregmap\.gso"      CoqStoq/test-repos/compcert -r       # 사용 40건

# DB 에도 없다
python3 -c "
import sqlite3; c=sqlite3.connect('/tmp/coq-dataset/sentences.db')
print(c.execute(\"select count(*) from sentence where module like '%Pregmap%'\").fetchone())"

# 규모
python3 - <<'PY'
import re, glob, collections
CC='CoqStoq/test-repos/compcert'
funct={m.group(1) for f in glob.glob(CC+'/**/*.v', recursive=True)
       for m in re.finditer(r"(?m)^\s*Module\s+([A-Za-z_][\w']*)\s*(?:<:[^:=]*)?:=\s*[A-Za-z_][\w'.]*\s*\(",
                            open(f, errors='ignore').read())}
REF=re.compile(r"\b(?:e?apply|e?rewrite|exact|specialize|refine|destruct|induction)\s+(?:<-\s*)?\(?\s*([A-Z][\w']*)\.([a-z_][\w']*)")
t=f_=0
for p in glob.glob(CC+'/**/*.v', recursive=True):
    for m in REF.finditer(open(p, errors='ignore').read()):
        t+=1; f_ += m.group(1) in funct
print(f'{f_}/{t} = {f_/t*100:.1f}%')
PY
```

---

## 9. 같은 뿌리의 세 얼굴 — "맨 이름을 키로 쓴다"

이 문서는 **부재**(필요한 한정이름의 선언이 없다)를 다뤘다. 그런데 같은 뿌리에서
**정반대 증상**도 나온다. 정리해 둔다.

> **뿌리**: 우리 파이프라인은 곳곳에서 **맨 이름**(`name.split(".")[-1]`)을 키로 쓰는데,
> Coq 의 이름은 **한정 경로**(`Pregmap.gso`)다. 그 대응이 1:1 이 아니다.

| | 증상 | 대응 관계 | 규모 | 어디서 |
|---|---|---|---|---|
| **부재** | 필요한 한정이름의 **선언이 없다** | 한정이름 → 선언 = **0:1** | tactic 인자 참조의 **27.0%** | 검색 풀 (§2–§5) |
| **모호** | 맨 이름 하나에 **선언이 여럿** | 맨이름 → 선언 = **1:N** | 맨 이름의 **7.6%** | 이름으로 선언을 되찾을 때 |
| **오분류** | 맨 이름이 stdlib 과 겹쳐 stdlib 취급 | 맨이름 → 출처 = **1:N** | CompCert Lemma 의 **2.8%** | `is_stdlib_name` (§7) |

### 9-1. 모호의 실측

compcert 선언의 **맨 이름 9,280종** 중 **708종(7.6%)** 이 선언을 2개 이상 갖는다.

```
t          46개 · 모듈 [AVal, EMap, IMap, ISet, …]
eq         33개 · 모듈 [AVal, IndexedEqKind, IndexedMreg, IndexedSlot, …]
eq_sym     20개 · 모듈 [AVal, LBoolean, LEq, LFSet, …]
eq_refl    19개 · 모듈 [AVal, LBoolean, LEq, LFSet, …]
eq_trans   19개 · 모듈 [AVal, LBoolean, LEq, LFSet, …]
```

**심한 것들이 전부 펑터가 찍어낸 인터페이스 멤버다.** `Module Type` 이 `t`·`eq`·`eq_sym`
을 요구하니 인스턴스마다 하나씩 생긴다. 즉 §1 의 펑터 구조가 부재와 모호를 **동시에** 만든다.

### 9-2. 실제로 물린 사례

`scripts/oracle_lemma_eval.py` 를 처음 쓸 때, gold lemma 의 선언문을 찾으려고

```sql
SELECT text FROM sentence WHERE text LIKE 'Lemma gso:%' LIMIT 1
```

를 썼다. `gso` 는 PTree·PMap·IMap·EMap·ITree 에 **전부** 있으므로 첫 매치가
엉뚱한 명제일 수 있다. 그걸 프롬프트에 꽂으면 **오라클 실험 자체가 무효**가 된다.

→ 세 단계로 좁히고 **품질을 기록**하도록 고쳤다.

```
① 한정자(Pregmap)가 module 컬럼에 있는가   → "정확"
② 같은 프로젝트(compcert) 파일 안인가       → "프로젝트"
③ 아무거나                                 → "모호"  (신뢰도 낮음. 보고에서 분리)
```

★ **펑터 인스턴스는 ①이 원리적으로 안 잡힌다** — `Pregmap` 은 `module` 컬럼에 없다.
그래서 `Pregmap.gso` 를 찾으면 항상 ②나 ③으로 떨어진다. 부재가 모호를 낳는다.

### 9-3. 그래서 §8 의 수정이 **둘 다** 해결한다

`Module N := F(A).` 를 전개해 `N.member` 를 풀에 넣으면

* **부재**가 사라진다 — 증명이 부르는 그 이름이 생긴다
* **모호**도 사라진다 — `Pregmap.t` · `IMap.t` · `ISet.t` 로 **완전 한정**되어 유일해진다

즉 전개는 이름을 늘리는 게 아니라 **이름공간을 Coq 이 실제로 보는 것과 맞추는** 일이다.

남는 것은 **오분류**뿐인데, 그건 익명화에만 영향을 주고 안전한 쪽으로 실수하므로
(§7) 급하지 않다. 정리하려면 `is_stdlib_name` 도 한정이름을 보게 바꾸면 된다.
