# 포섭 격자 — 필터와 랭커는 쌍대다

## 0. 먼저 용어

### `concl(L)` — lemma 의 결론

lemma 는 대개 `forall …, 전제 -> … -> 결론` 꼴이다. **Π-바인더와 전제를 벗기고 남는 것**이
결론이다. 벗길 때 바인더는 **evar(미지수)** 로 바꾼다 — `eapply` 가 하는 일 그대로다.

```
L = PTree.gso
  : forall (A : Type) (i j : positive) (x : A) (m : PTree.tree A),
      i <> j -> PTree.get i (PTree.set j x m) = PTree.get i m
     └──────────── 바인더 5개 ────────────┘  └전제┘  └──────── 결론 ────────┘

concl(L) = PTree.get ?i (PTree.set ?j ?x ?m) = PTree.get ?i ?m
```

- `?i`·`?j`·`?x`·`?m` 은 evar 다. **아직 뭐가 될지 모르는 자리**다.
- 같은 이름은 같은 evar 다 — `?i` 가 두 번 나오면 둘은 같은 값이어야 한다.
- 몇 개를 벗길지는 하나가 아니다. `x -> y -> z` 는 `z` 로도, `y -> z` 로도,
  통째로도 결론이 될 수 있다. 그래서 **모든 화살표 접미사**를 본다 (`max_arrows` 까지).

코드: `descend` (바인더 벗기기) · `unifies_upto` (모든 접미사 시도)

### 항의 순서

`t₁ ≼ t₂` = "`t₁` 이 더 일반적" = `∃σ. σt₁ = t₂`.
`σ` 는 치환(변수 → 항)이다.

```
?x ≼ f ?y ≼ f (g a)          왼쪽이 더 일반적
```

```
       ⊤ = ?x   (가장 일반적 — 무엇이든 된다)
            │
       ┌────┴────┐
    f ?y        g ?z
       │            \
   ┌───┴───┐         …
 f (g a)  f b
       │
       ⊥  (단일화 불가 — 아래로 못 감)

   위 = 일반적,  아래 = 구체적
   두 항의 join(⊔) = 위로 올라가 만나는 첫 점  … 이 아니라 아래로 내려가 만나는 점 = mgu
   두 항의 meet(⊓) = 위로 올라가 만나는 첫 점                            = lgg
```

이 순서로 항들은 **격자**를 이룬다 — 어떤 두 항에도 최소상계(join)와 최대하계(meet)가 있다.

---

## 1. mgu — 가장 일반적인 단일자
```
        lgg (meet, ⊓) = 둘의 공통 뼈대            ↑ 더 일반적
                 ?  =  PTree.get ?a ?b               │
                 ↑          ↑                        │
        ┌────────┘          └────────┐               │
   concl(L)                        goal              │
   get ?i (set ?j ?x ?m) = get ?i ?m   get i (set j x m) = get i m
        └────────┐          ┌────────┘               │
                 ↓          ↓                        │
        mgu (join, ⊔) = 둘을 같게 만든 것              ↓ 더 구체적
                 get i (set j x m) = get i m

   join 이 존재하나?  → 예/아니오        →  필터
   meet 이 얼마나 큰가? → 정도            →  랭커
```


두 항 `s`, `t` 를 **같게 만드는** 치환 중 가장 일반적인 것.

```
s = PTree.get ?i (PTree.set ?j ?x ?m) = PTree.get ?i ?m      ← concl(gso)
t = PTree.get i  (PTree.set j  x  m)  = PTree.get i  m       ← goal

mgu = { ?i↦i, ?j↦j, ?x↦x, ?m↦m }
```

- 존재하면 **join `s ⊔ t` 가 존재**한다. 그게 `σs = σt` 다.
- 존재하지 않는 예:
  ```
  s = ?n + 0 = ?n      (nat)
  t = a + 0 = a        (Z)      → 타입이 달라 실패
  ```

### 왜 이게 **필터**인가

`apply L` 이 성공한다 ⟺ **`concl(L)` 을 goal 과 같게 만드는 치환이 있다.**
그게 정확히 mgu 의 존재다. 즉 필터는

```
질문:  concl(L) ⊔ goal  이 존재하는가
```

를 묻는 이항 술어이고, **근사가 아니라 tactic 성공 조건 그 자체**다.
그래서 정밀도가 apply **96.9%** · apply…in **99.8%** 로 나온다.

코드: `unify_ap` = `Unification.w_unify ~flags:(elim_flags ())`

---

## 2. lgg — 가장 구체적인 공통 일반화

Plotkin(1970)·Reynolds(1970). 두 항의 **불일치 자리를 변수로 바꿔** 얻는다.

```
lgg( f a (g b),  f a (h c) )  =  f a ?x
      └같음┘ └다름┘              └─────┘ 같은 부분만 남고 다른 자리는 변수
```

- **가장 구체적**이라는 뜻: `f a ?x` 보다 더 구체적이면서 둘 다를 일반화하는 항은 없다.
- 이게 meet `⊓` 다. 항상 존재한다(최악이라도 `?x`).

### 왜 이게 **랭커**인가

필터를 통과한 후보는 **전부 적용 가능**하다. 그중 무엇이 이 goal 에 **맞춤한가**를
가려야 한다. 그 척도가 **공유 구조의 양**이다.

- `lgg` 가 크다 = goal 과 구조를 많이 공유한다 = 이 goal 을 겨냥한 lemma 다.
- `lgg` 가 1 이다 = 머리조차 안 맞고 evar 로만 통과했다 = 아무 goal 에나 적용되는 것이다.

즉 **필터는 join 의 존재를, 랭커는 meet 의 크기를 묻는다.** 두 개의 무관한
휴리스틱이 아니라 **한 격자의 두 연산**이다.

---

## 3. `lgg_size` — 항을 만들지 않고 크기만 센다

```ocaml
let rec lgg_size sigma a b =
  let (ha, aa) = decompose_app sigma a in     (* a = ha aa₁ … aaₙ *)
  let (hb, ab) = decompose_app sigma b in
  if 인자수 같음 && ha = hb then
    1 + Σᵢ lgg_size sigma aaᵢ abᵢ             (* 머리 1칸 + 자식들 *)
  else
    1                                          (* 변수 하나 — 크기 1 *)
```

### 무슨 말인가

lgg 를 **실제로 만들려면** 새 변수를 만들고 치환을 관리해야 한다. 그런데 우리는
**크기만** 필요하다. 크기는 재귀로 바로 세진다:

- **머리가 같고 인자 수도 같으면** → 그 자리는 lgg 에 살아남는다. 노드 1개(머리) +
  각 인자의 lgg 크기를 더한다.
- **하나라도 다르면** → 그 자리 전체가 변수 하나로 뭉개진다. 크기 1.

```
a = f a (g b)          b = f a (h c)
    ↓ 머리 f 같음, 인자 2개 같음  → 1 + lgg(a,a) + lgg(g b, h c)
    ↓ lgg(a, a)     = 1                       (머리 a 같음, 인자 0개)
    ↓ lgg(g b, h c) = 1                       (머리 g ≠ h → 변수)
  = 1 + 1 + 1 = 3      →  lgg 는 `f a ?x`, 노드 3개 ✓
```

**비용**: 두 항을 나란히 한 번 훑는다 — `O(min(|a|,|b|))`. 치환도, 새 항도 없다.

---

## 4. 점수

```
score(g, L) = |lgg(g, concl L)| / |g|     ∈ (0, 1]
```

- 분모 `|g|` = goal 의 노드 수. 정규화해서 goal 크기가 다른 지점끼리 비교 가능하게 한다.
- 1에 가까울수록 goal 을 통째로 닮았다는 뜻이다.

### 실측 예시 — 무엇을 보여주는가

goal (노드 20개):
```
PTree.get i (PTree.set j x m) = PTree.get i m
```

| 후보 | 진술문 (요약) | lgg | score |
|---|---|---|---|
| **`PTree.gso`** (정답) | `… i <> j -> (set j x m)!i = m!i` | **15** | **0.75** |
| `N.measure_left_induction` | `… (forall x, … -> A x) -> forall x, … -> A x` | 1 | 0.05 |
| `Ring_polynom.PEeval` | `… -> R` (결론이 유연) | 1 | 0.05 |

**둘 다 필터는 통과했다.** `measure_left_induction` 의 결론은 `A x` 이고 `A` 가 evar 라
어떤 goal 과도 단일화된다 — 적용은 되지만 **정보가 없다.**

`gso` 는 결론이 goal 과 **머리부터 인자까지** 겹친다. 20칸 중 15칸을 공유한다.
변수 자리 5칸(`?i ?j ?x ?m` 과 타입)만 다르다.

즉 lgg 는 **"적용 가능한가"(필터가 이미 답함) 위에서 "얼마나 이 goal 을 겨냥했는가"**
를 재는 것이다.

### 한계

- lgg 는 **한 신호일 뿐**이다. 단독으로는 @10 **36.5%** (무작위 20.2%, 나이브베이즈 76.6%).
- 크기가 큰 goal 에서 유리하게 나오는 편향이 있어 `|g|` 로 나눈다.
- `lcp`(Baire 거리)와 강하게 상관된다 → 나이브 베이즈가 그 중복을 흡수한다.

---

## 코드

| | |
|---|---|
| `lgg_size` | `ocaml/applic/applic_main.ml` |
| `descend` · `unifies_upto` | 결론 뽑기 |
| `unify_ap` | mgu 존재 판정 |
| 점수 사용 | `scripts/applic_rank.py` — `s_lgg` · `feats` 의 `("lgg", …)` |

관련 — [baire.md](baire.md) (같은 것을 문자열 수준에서) · [information.md](information.md) (신호 결합)
