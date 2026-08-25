# `concrete` 란 무엇인가 — 전개된 펑터 이름의 **추상 타입을 구체화**하는 것

> 한 줄: 펑터 안의 명제는 `elt`·`X.t` 같은 **추상 타입**으로 쓰여 있어서 goal 과
> 어휘가 안 겹친다. 인스턴스가 정한 실제 타입으로 바꿔 주면 랭킹이 올라온다.
> **실측: `Pregmap.gso` 가 735위 → 53위** (프롬프트는 상위 100개).

---

## 1. 배경 — 왜 이름만 되살려서는 부족한가

`functor-names.md` 가 밝힌 문제: `Module Pregmap := EMap(PregEq).` 이 만들어 내는
`Pregmap.gso` 는 **선언이 소스 어디에도 없어** 검색 풀에 못 든다.

그래서 풀에 있는 `EMap` 의 선언을 `Pregmap` 이름으로 복제해 넣었다. 이름 문제는
풀렸는데 — **랭킹이 안 올라왔다.**

```
FUNCTOR_EXPAND=1 (이름만 복제)
  풀     3,022개 → 6,225개  (Pregmap.gso 들어감 ✓)
  순위   Pregmap.gso = 735위    (프롬프트는 상위 100개 → 여전히 안 실림)
```

---

## 2. 왜 안 올라오나 — 어휘가 안 겹친다

복제한 명제는 펑터 **안의 원문 그대로**다.

```coq
Lemma Pregmap.gso: forall (A: Type) (i j: elt) (x: A) (m: t A),
                     i <> j -> (set j x m) i = m i.
                               ↑ elt · t A · set — 전부 **추상 이름**
```

그런데 goal 은 레지스터에 관한 것이고, 상위권 premise 는 이렇게 생겼다.

```coq
  1  Lemma preg_of_data:   forall r, data_preg (preg_of r) = true.
  2  Lemma preg_of_not_PC: forall r, preg_of r <> PC.
  4  Lemma preg_val:       forall ms sp rs r, agree ms sp rs -> Val.lessdef (ms r) rs#(preg_of r).
```

`preg` 라는 어휘가 goal 과 겹친다. `elt` 는 안 겹친다.
우리 랭커(afh70)는 명제의 α-정규형 **구조 유사도**를 보는데, 추상형과 구체형은
구조가 닮았어도 **이름이 전부 달라** 점수가 안 붙는다.

---

## 3. `concrete` 가 하는 일

Coq 이 펑터를 적용할 때 실제로 하는 치환을 **텍스트로 흉내 낸다.**

```coq
(* lib/Maps.v — 펑터 안 *)
Module EMap(X: EQUALITY_TYPE) <: MAP.
  Definition elt := X.t.          ← ① elt = X.t
  ...
End EMap.

(* x86/Asm.v — 인자 모듈 *)
Module PregEq.
  Definition t := preg.           ← ② X.t = preg
End PregEq.

(* x86/Asm.v:310 *)
Module Pregmap := EMap(PregEq).   ← ③ X := PregEq
```

세 단계를 이으면

$$\texttt{elt} \overset{①}{=} \texttt{X.t} \overset{③}{=} \texttt{PregEq.t} \overset{②}{=} \texttt{preg}$$

그래서 `concrete` 는 이렇게 만든다.

```coq
abstract: Lemma Pregmap.gso: forall (A: Type) (i j: elt)  (x: A) (m: t A), i <> j -> (set j x m) i = m i.
concrete: Lemma Pregmap.gso: forall (A: Type) (i j: preg) (x: A) (m: t A), i <> j -> (set j x m) i = m i.
                                                     ↑ 여기가 바뀐다
```

구현은 두 조각이다.

| 파일 | 역할 |
|---|---|
| `scripts/build_functor_argdefs.py` | `{프로젝트: {인스턴스 N: {"t": τ}}}` 맵을 만든다 (소스에서 `Definition t := τ` 를 긁는다) |
| `src/premise_selection/functor_expand.py` | 복제할 때 `elt`·`X.t` 를 τ 로 치환 (`FUNCTOR_EXPAND_CONCRETE=1`) |

compcert 에서 구체화 가능한 인스턴스:

```
Pregmap → preg   Regmap → mreg   ZMap → Z   NMap → N
ZTree   → Z      Sort   → positive   Solver → numbering
```

---

## 4. 효과 — 실측

같은 스텝(`backend/Asmgenproof0.v`, gold 가 `rewrite Pregmap.gso; auto.` 인 자리):

| | 풀 크기 | `Pregmap.gso` 순위 | 프롬프트에 실림 |
|---|---|---|---|
| 전개 **끔** | 3,022 | **없음** (선언 자체가 없다) | ✗ |
| 전개만 (abstract) | 6,225 | **735위** | ✗ |
| 전개 + **concrete** | 6,225 | **53위** | **✓** |

`Pregmap.*` 전체 순위 분포도 달라진다.

```
abstract:  [14, 735, 3019, 3882, 5353, 5446, 5495]
concrete:  [13,  30,   46,   53,   62,   66,   99]   ← 전부 top-100 안
```

---

## 5. ★ 한계 — 이건 **근사**다, 진짜 Coq 상세화가 아니다

정규식 치환이라 못 하는 것이 있다.

**(1) 파생 타입을 못 편다.** 위 예에서 `(m: t A)` 가 그대로 남았다.
실제로는 `Definition t (A: Type) := X.t -> A.` 이므로 `Pregmap.t A = preg -> A` 여야 한다.

**(2) 인자 이름을 `X` 로 가정한다.** 펑터가 `Module F(M: SIG)` 로 쓰면 `M.t` 를 못 잡는다.

**(3) 다인자 펑터 미지원.** `F(A)(B)`.

**(4) `Definition t := τ` 가 단순할 때만 잡는다.** τ 가 40자 넘거나 식별자 하나가
아니면 건너뛴다(오치환 방지).

**(5) 과치환 위험.** 다른 뜻의 `elt` 가 있으면 잘못 바꾼다.

### 그래서 어떻게 쓰나

**랭킹용으로만 쓰는 것이 안전하다.** 살짝 틀린 명제를 모델에게 보여주면 오도할 수 있다.
지금은 프롬프트에도 그대로 들어가는데, 두 가지 이유로 감수할 만하다.

* 모델이 실제로 필요로 하는 것은 **이름**이다 — 명제는 "이게 맞나" 판단용이다
* 치환된 부분(`elt → preg`)은 **더 정확해진 쪽**이다. 틀린 방향이 아니라 덜 일반적인 방향이다

다만 `t A` 처럼 **안 편 부분이 남아** 명제가 반쯤 구체화된 상태라는 점은 알고 있어야 한다.
정확히 하려면 Coq 을 돌려 `Print Pregmap.gso` 를 받아오면 되는데, 그건
43개 인스턴스 × 수천 멤버라 비용이 크다. **먼저 A/B 로 이득을 확인하고 결정한다.**

---

## 6. 설정

| 이름 | 기본값 | 뜻 |
|---|---|---|
| `FUNCTOR_EXPAND` | **`0`** | 전개 자체. **아직 정식 채택 아님** |
| `FUNCTOR_EXPAND_CONCRETE` | `1` | 전개할 때 추상 타입을 치환 (전개가 켜져야 의미 있음) |
| `FUNCTOR_EXPAND_MAX` | `4000` | 한 예제에 더할 수 있는 최대 개수(풀 폭발 방지) |

셋 다 **캐시 도장**에 들어간다 — 풀이 바뀌면 캐시된 `LmExample` 이 달라지므로
안 넣으면 옛 캐시를 조용히 쓴다.

```bash
# 켜고 돌리기
FUNCTOR_EXPAND=1 FUNCTOR_EXPAND_CONCRETE=1 python3 scripts/run_all.py --alias rango-v9 …

# 맵 다시 만들기
python3 scripts/build_functor_instances.py CoqStoq/test-repos data/functor_instances_test.json
python3 scripts/build_functor_argdefs.py   CoqStoq/test-repos data/functor_argdefs_test.json
```
