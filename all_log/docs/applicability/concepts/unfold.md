# `unfold` 은 검색이 아니다 — 방향이 반대다

> `apply`/`rewrite` 는 **바깥 우주에서 goal 에 맞는 것을 찾는다.**
> `unfold` 은 **goal 안에 이미 있는 것을 세어 거른다.** 매칭이 없다.

---

## 0. `unfold` 이 뭔가 — Coq 전술 자체

**"이름을 정의 본문으로 바꿔치기한다."** 그게 전부다. δ-환원이라고 부른다.

```coq
Definition Ple (p q : nat) : Prop := p <= q.
```

```
   ① unfold 전                     ② unfold Ple 후
   ─────────────────────        ─────────────────────
   a, b : nat                    a, b : nat
   H : Ple a b                   H : Ple a b            ← 가설은 그대로
   ══════════════                ══════════════
   Ple a (b + 0)                 a <= b + 0             ← goal 만 바뀌었다
   └┬┘                            └──┬──┘
   이름                          정의 본문으로 치환 (+ β-환원)
```

```
   ③ unfold Ple in H 까지 하면
   ─────────────────────
   H : a <= b                    ← 가설도 펼쳐진다
   ══════════════
   a <= b + 0
```

### ★ 뜻은 하나도 안 바뀐다

```coq
Definition twice (n : nat) := n + n.

Goal forall n, twice n = n + n.
  intro n.
  (* goal :  twice n = n + n *)
  unfold twice.
  (* goal :  n + n = n + n   ← 이제 눈에 보인다 *)
  reflexivity.
Qed.
```

`twice n = n + n` 과 `n + n = n + n` 은 Coq 에게 **정의적으로 같다.**
`unfold` 은 증명을 진전시키는 게 아니라 **모양을 바꾼다.**

```
   ┌────────────────────────────────────────────────────┐
   │  unfold 은 의미를 바꾸지 않는다.                     │
   │  다음 전술의 **구문 매칭**이 되게 만드는 것이 목적이다. │
   └────────────────────────────────────────────────────┘
```

이게 핵심이다. `rewrite` 는 keyed 매칭이라 머리가 구문적으로 맞아야 하고,
판별트리도 구문적이다 → [limits.md](limits.md).
`unfold` 은 사람이 **손으로 δ 를 적용해서 그 구문 장벽을 넘는 것**이다.

### 변형

| | |
|---|---|
| `unfold f` | goal 에서 `f` 를 전부 편다 |
| `unfold f in H` | 가설 `H` 에서 편다 |
| `unfold f in *` | 전부 |
| `unfold f at 1` | **1번째 출현만** |
| `unfold f, g` | 둘을 편다 |
| `fold f` | **역방향** — 본문을 이름으로 접는다 |

```
   goal :  twice (twice n) = twice n + twice n
   unfold twice at 1.
   goal :  twice n + twice n = twice n + twice n     ← 바깥 것만 펴졌다
```

### 무엇을 펼 수 있나 — Coq 이 직접 답한 것

```coq
Lemma L : forall n, n + 0 = n. Proof. … Qed.
Fail unfold L.      (*  L is opaque.  *)

Axiom A : nat -> Prop.
Fail unfold A.      (*  A is opaque.  *)

Parameter P : nat.
Fail unfold P.      (*  P is opaque.  *)

Fail unfold S.      (*  Cannot turn constructor S into an evaluable reference. *)

unfold Nat.add.     (*  OK — Fixpoint 는 펼쳐진다 *)
```

```
   펼 수 있다        Definition · Fixpoint · Let      (const_body = Def _)
   못 편다          Qed 로 닫은 Lemma (OpaqueDef)
                    Axiom · Parameter · Variable (Undef)
                    귀납형 생성자 (S · cons · conj)   ← 애초에 정의가 없다
```

**`Qed` vs `Defined` 가 갈림길이다.** 같은 lemma 도 `Defined` 로 닫으면
`Def _` 가 되어 펼 수 있다. 그래서 우리 술어 `const_body = Def _` 는
"펼 수 있나" 를 **정확히** 판정한다 — 근사가 아니다.

### 왜 증명에 자주 나오나

CompCert 같은 코드는 개념에 이름을 붙여 둔다.

```coq
Definition Ple (p q : positive) := (p <= q)%positive.
Definition zle : forall x y : Z, {x <= y} + {x > y} := …
```

읽기는 좋지만 **전술이 구문으로 매칭하려면 이름이 방해가 된다.**
그래서 증명 중간중간 `unfold` 로 벗겨 가며 나아간다.
실측에서 rand200 스텝의 **10.2%** 가 `unfold` 이다.

---

## 1. 방향이 반대다

```
   apply / rewrite  ── 바깥에서 안으로 ──────────────────────────
                        12,652개 lemma 우주
                              │  "이 중 goal 에 맞는 게 뭐냐"
                              ▼  ← 단일화(매칭)가 필요하다
                            goal

   unfold           ── 안에서 밖으로 ────────────────────────────
                            goal
                              │  "여기 있는 상수 중 펼칠 수 있는 게 뭐냐"
                              ▼  ← 국소 술어 하나면 된다
                           3~7개
```

**우주를 안 본다.** 그래서 후보가 지점당 3~7개고, 회수율이 100% 다.

---

## 2. 코드 전부

```ocaml
let unfoldable env c =
  match (Environ.lookup_constant c env).Declarations.const_body with
  | Declarations.Def _ -> true          (* 투명한 Definition *)
  | _ -> false                          (* Axiom · Parameter · Qed 로 닫힌 것 *)

let unfold_cands env sigma terms =
  let rec go t =
    (match EConstr.kind sigma (fst (EConstr.decompose_app sigma t)) with
     | Constr.Const (c, _) -> if unfoldable env c then 수집한다
     | _ -> ());
    EConstr.iter sigma go t          (* 모든 부분항으로 재귀 *)
  in List.iter go terms
```

이게 전부다. **단일화도, 판별트리도, 랭킹 신호도 안 쓴다.**

```
   goal 과 가설의 모든 부분항을 훑는다
        │
        ├─ 머리가 Const c 인가?              ─── 아니면 버림
        │
        └─ const_body 가 Def _ 인가?         ─── 아니면 버림
                  │
                  └── 수집
```

### `const_body` 세 가지

| 생성자 | 무엇 | 펼 수 있나 |
|---|---|---|
| `Def _` | `Definition f := …` (투명) | **O** |
| `OpaqueDef _` | `Lemma … Qed.` 로 닫힌 증명항 | X |
| `Undef _` | `Axiom` · `Parameter` · `Variable` | X |

**`Qed` 로 닫으면 `OpaqueDef` 가 되어 δ-환원이 막힌다.** 그래서 lemma 는
후보가 되지 않는다 — 자동으로 `Definition` 만 남는다.

---

## 3. 왜 "매칭 관계가 깔끔하지 않다" 는 느낌이 드나

맞다. **`unfold` 에는 맞출 두 항이 없다.**

```
   apply L      concl(L)  ≟  goal            두 항을 맞춘다
   rewrite L    L 의 한 변 ≟  goal 의 부분항   두 항을 맞춘다
   unfold f     ─────────────────────────    맞출 게 없다
                f 가 goal 에 나타나는가?  (예/아니오)
                f 를 펼칠 수 있는가?      (예/아니오)
```

`apply`/`rewrite` 는 **관계**(단일화 가능한가)를 판정한다.
`unfold` 은 **속성**(나타나는가 · 투명한가)을 판정한다.

```
   관계 판정  →  두 집합의 곱  →  비싸다  →  트리로 좁힌다
   속성 판정  →  한 집합의 부분집합  →  싸다  →  그냥 센다
```

이게 채널을 나눈 이유 그 자체다. **한 술어로 다 못 한다.**

---

## 4. 그래서 100% 는 무슨 뜻인가 — 정직하게

```
   unfold  풀에 100.0%   @10 100.0%   순위중앙 1
```

**@10 100% 는 랭커가 좋아서가 아니다.** 후보가 애초에 열 개 안팎이다.

```
   지점당 unfold 후보:  중앙 7 · p25 3 · p75 11 · p90 16 · max 31
                              └──── 대부분 @10 안에 다 들어간다 ────┘
```

정확히 말하면:

```
   회수율 100%     ← 이게 진짜 성과다. 술어가 완전하다
   @10 100%        ← 회수율 100% + 후보가 작다 의 따름 결과
```

**랭킹 문제가 아니라 열거 문제**라서 푼 것이다.

---

## 4.5 ★★ 정정 — 이건 애초에 검색 문제가 아니다

앞 절들이 이 채널을 "회수율 100%" 로 자랑하는데, **지표가 질문을 잘못 던지고 있다.**

```ocaml
let terms = concl :: List.map snd hyps in     (* goal + 가설 *)
unfold_cands env sigma terms
```

**후보는 정의상 `terms` 의 부분집합이다.** 즉 goal·가설에 이미 나타나는 이름뿐이다.
그런데 모델은 프롬프트에서 **증명 상태를 이미 보고 있다.**

```
   apply / rewrite    답이 12,416개 우주 어딘가       → 검색이 필요하다
   unfold             답이 goal 안에 이미 보인다       → 검색할 게 없다
```

### 그래서 "풀에 1.5% → 100%" 는 과장이다

이 지표는 **"gold 이 검색된 풀에 있나"** 를 묻는다. 답이 goal 에 보이면
그 질문 자체가 빗나간다 — premise 목록이 비어도 모델은 goal 을 읽고
`unfold Ple` 을 쓸 수 있다.

```
   우리가 잰 것       tf-idf 랭킹 안에서 gold 의 순위      → 0.0% @10
   재야 했던 것       모델이 실제로 unfold 을 맞히는 비율    → 안 쟀다
```

**둘은 다른 수치다.** 이 문서와 결과 보고서가 앞의 것을 뒤의 것처럼 읽히게 썼다.

### 남는 실제 값은 둘뿐이다

| | |
|---|---|
| ① **펼 수 있는지 판정** | goal 만 봐서는 `Ple` 이 투명 Definition 인지 Qed 로 닫힌 Lemma 인지 모른다. `lookup_constant` 가 필요하다 |
| ② `destruct` 의 정답 자리 | 단독 기여 75 중 25가 destruct 다 → [destruct.md](destruct.md) §3.5 |

①의 압축률(goal 의 전체 상수 대비 몇 개가 남나)은 **안 쟀다.** 후보 중앙 7개만
알고 분모를 모른다. 2~4배 수준이면 약한 필터다.

### 게다가 우리가 싣는 statement 는 쓸모없다

```ocaml
let stmt nm = … Retyping.get_type_of env sg tm …     (* 타입을 낸다 *)
```

```
   UNFOLD Ple occ=2 z=6 :: nat -> nat -> Prop
                           └── 타입. 정작 필요한 본문(p <= q)이 아니다
```

프롬프트에는 `Lemma Ple : nat -> nat -> Prop.` 로 실린다.
**`unfold` 을 도우려면 정의 본문을 줘야 하는데 이름만 반복하고 있다.**

### r11 의 결정

```
   남긴 채널   ap · in · rw · rwh      ← 진짜 검색이 필요한 것
   뺀 채널     uf · ds · dc
```

`uf` 는 **버린 게 아니라 검색 범위에서 뺀 것**이다. 되살릴 값은 남아 있다:

- 랭킹 밖에서 **전량 프롬프트에 싣기** (3~7개라 예산을 거의 안 먹는다). `FREE_CH` 자리.
- 싣는다면 **타입이 아니라 정의 본문**으로. 지금 형태는 정보가 0이다.

플러그인은 `ApplicWideChannels 1` 로 되살린다. 코드는 그대로 있다.

---

## 5. 현행 tf-idf 가 0% 인 이유 — 랭킹이 아니다

> ⚠ 아래 수치는 **tf-idf 랭킹 안의 순위**다. 모델의 실제 성공률이 아니다. §4.5 참조.

```
                        현행 tf-idf     우리
   unfold gold 풀에        1.5%        100.0%
   unfold gold @10         0.0%         31.8%
```

**랭킹이 나빠서가 아니라 풀에 애초에 안 들어간다** (1.5%).

```
   tf-idf 의 전제:  "정답은 바깥 lemma 목록 어딘가에 있고,
                     goal 과 어휘가 겹치는 것을 찾으면 된다"

   unfold 의 현실:  정답이 **goal 안에** 있다.
                    goal 에 `Ple` 이 보인다는 사실 자체가 답이다.
```

어휘 겹침으로는 "이 상수를 펼쳐라" 를 표현할 수 없다. `Ple` 은
goal 과 100% 겹치지만, 그건 tf-idf 에게 **정보가 아니라 잡음**이다
(모든 goal 은 자기 자신과 겹친다).

> 이건 랭커를 갈아서 고칠 수 있는 문제가 아니다. **모집단을 만드는 방식**이 다르다.
> 다만 §4.5 대로, 모델이 goal 을 보고 있으므로 **이 차이가 성능 차이로 그대로
> 이어지지는 않는다.** 우리가 잰 것은 랭킹이지 성공률이 아니다.

---

## 6. 우리가 안 하는 것 — 한계

이름만 준다. 나머지는 모델의 몫이다.

| gold 형태 | 우리가 주는 것 | 빠진 것 |
|---|---|---|
| `unfold Ple` | `Ple` | — (완전) |
| `unfold Ple in H` | `Ple` | **어느 가설에서** |
| `unfold Ple at 2` | `Ple` | **몇 번째 출현** |
| `fold Ple` | `Ple` | **방향** (접는 것) |
| `unfold Ple, Plt` | `Ple`·`Plt` 따로 | **묶음** |

그리고 **어느 것을 펼칠지**는 여전히 선택이다 — 후보가 7개면 7개 중 하나다.
회수율 100% 가 성공률 100% 를 뜻하지 않는다.

### 신호는 두 개만 낸다

```
   UNFOLD Ple occ=2 z=6 g=20
                ▲     ▲
          goal 에      그 상수가 이끄는
          몇 번 나오나   부분항 크기
```

나이브베이즈에서 `('occ',2) +6.30` · `('ch','uf') +6.18` 로 둘 다 강한 가점이다.
**"자주 나오는 상수일수록 펼칠 대상"** 이라는 것을 데이터가 확인해 준다.

---

## 6.5 ★ `uf` 채널은 destruct 의 정답도 찾는다 — 실측

`unfold` 채널의 진짜 값은 `unfold` 이 아니다.

| 채널 | gold 포함 | **단독 기여** | 후보 중앙 | 효율 |
|---|---|---|---|---|
| ap | 115 | 46 | 334 | 0.14 |
| in | 70 | 9 | 618 | 0.015 |
| rw | 88 | 47 | 418 | 0.11 |
| **uf** | 109 | **75** | **7** | **10.7** |
| ds | 0 | 0 | 3 | 0 |
| dc | 36 | 0 | 171 | 0 |

`uf` 의 단독 기여 75개 내역:

```
   unfold     43
   destruct   25    ← ★ destruct (peq a b) 의 peq 가 goal 에 이미 있다
   case        5
   induction   2
```

**후보 7개로 75지점을 혼자 살린다.** 다른 어떤 채널보다 두 자릿수 효율이 좋다.
"unfold 만 위한 채널" 이 아니라 **"goal 에 있는 상수" 채널**이고,
그게 `destruct`·`case` 의 정답 자리이기도 하다. → [destruct.md](destruct.md) §3.5

---

## 7. `destruct` 와 비교

| | `unfold` | `destruct` |
|---|---|---|
| 정답이 어디 있나 | **goal 안** | 바깥 (판정 함수) |
| 판정 | 속성 (투명한가) | 관계 (인자가 맞나) |
| 후보 수 | 3~7 | 91 |
| 인자를 고르나 | 아니오 | **예** ← 어렵다 |
| 회수율 | 100.0% | 78.0% |

둘 다 "apply/rewrite 같은 깔끔한 매칭이 아니다" 지만 **반대 방향으로** 그렇다.
`unfold` 은 너무 쉬워서, `destruct` 는 너무 어려워서.
→ [destruct.md](destruct.md)

---

## 관련

[channels.md](channels.md) · [destruct.md](destruct.md) ·
[../terminology/delta-reduction.md](../terminology/delta-reduction.md) ·
[../terminology/tf-idf.md](../terminology/tf-idf.md)
