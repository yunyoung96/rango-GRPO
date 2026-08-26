# `assert` 는 쓸모없는 명제를 만드는가, gold lemma 를 베끼는가 — 전체 proof 로 본다

> 대상: `checkpoint-25000` CompCert rand200 전탐색 로그 (`all_results/v9_ckpt25000_rand200_t600_w2/logs`)
> 표본: `assert` 를 생성한 정리 **121개** · assert 후보 **5,209건** · 채택된 assert **2,709건**
> 스크립트: `scripts/assert_reality.py` (생성 없음 · CPU 전용) · 원자료 `all_log/assert_reality.json`

---

## 0. 답

**베낀다.** 다만 "베껴서 쓰는" 데까지는 못 간다.

| | |
|---|---|
| assert 명제 ↔ gold lemma signature 토큰 겹침 **중앙값** | **43%** |
| 겹침 **≥80%** (사실상 재진술) | **566 / 3,580 = 15.8%** |
| 겹침 **≥50%** | **1,661 / 3,580 = 46.4%** |
| 겹침 **0%** (완전히 무관) | 153 / 3,580 = 4.3% |
| assert 자체가 Coq 을 통과 | **1,638 / 3,580 = 45.8%** |

**"자명한 명제만 만든다"는 틀렸다.** 절반 가까이가 gold lemma 의 재진술이고,
15.8% 는 signature 를 거의 그대로 옮겨 적는다.

그런데 —

| assert 바로 뒤에 무엇이 오나 (채택된 2,709건) | |
|---|---|
| **`Proof.`** (무의미 반복) | **1,469 = 54.2%** |
| **`exact` / `apply <이름>`** (의도한 동작) | **496 = 18.3%** |
| 또 다른 `assert` | 240 = 8.9% |
| `intros` | 157 = 5.8% |
| 나머지 | 347 = 12.8% |

**의도한 `{ exact L }` 로 이어지는 것은 18.3% 뿐이고, 54.2% 는 `Proof.` 무한반복으로 샌다.**

---

## 1. 사례 A — 이름을 알면서도 assert 를 거쳐 간다 (성공, 그러나 218스텝)

**`idx 1365` · CompCert `lib/Integers.v` · 성공 (349초)**

### gold proof 전체 — 3줄

```coq
Theorem and_shl: forall x y n, and (shl x n) (shl y n) = shl (and x y) n.
Proof.
  intros. apply bitwise_binop_shl with andb. exact bits_and. auto.
Qed.
```

### gold 가 쓰는 lemma 의 signature

```coq
Lemma bitwise_binop_shl :
  forall f f' x y n,
    (forall x y i, 0 <= i < zwordsize -> testbit (f x y) i = f' (testbit x i) (testbit y i)) ->
    f' false false = false ->
    f (shl x n) (shl y n) = shl (f x y) n.

Lemma bits_and :
  forall x y i, 0 <= i < zwordsize -> testbit (and x y) i = testbit x i && testbit y i.
```

### 모델이 만든 proof 전체 — 218스텝

```coq
   1| Proof.
   2| intros.
   3| Proof.
   4| intros.
   5| Proof.
   6| intros.
   7| Proof.
   8| intros.
   9| Proof.
  10| intros.
       … (Proof./intros. 무한반복 — 이 짝이 총 80회) …
  19| assert (H: forall i, 0 <= i < zwordsize ->
                testbit (shl x n) i = testbit (and x y) i).
  20| {
  21| intros.
  22| Proof.
  23| intros.
       … 다시 Proof./intros. 반복이 190스텝까지 …
 213| assert (forall f f' x y n,
              (forall x y i, 0 <= i < zwordsize ->
                 testbit (f x y) i = f' (testbit x i) (testbit y i)) ->
              f' false false = false ->
              f (shl x n) (shl y n) = shl (f x y) n) as H_asrt0.
 214| exact bitwise_binop_shl.
 215| apply H_asrt0 with (f:=and) (f':=fun x y => x && y).
 216| intros.
 217| rewrite bits_and; auto.
 218| trivial.
```

### 읽는 법

**스텝 213 의 assert 는 `bitwise_binop_shl` 의 signature 와 토큰 100% 일치한다.**
그리고 **스텝 214 에서 `exact bitwise_binop_shl.` 로 닫는다** — **모델은 이름을 알고 있었다.**

즉 이 경우 assert 는 아무것도 벌어 주지 않았다. `apply bitwise_binop_shl with andb` 라고
바로 쓸 수 있었는데, **명제를 한 번 베껴 쓴 다음 그 이름으로 닫는 우회로**를 갔다.

그리고 그 우회로에 닿기까지 **`Proof.`/`intros.` 를 80쌍(160스텝) 낭비했다.**
성공은 했지만 349초가 걸렸다. gold 는 3줄이다.

> 중복 상위: `Proof.` 80회 · `intros.` 80회 · `unfold shl.` 7회 · `rewrite and_commut.` 3회

---

## 2. 사례 B — 베꼈지만 못 쓴다 (실패)

**`idx 702` · Flocq `Core/Float_prop.v` · 실패 (600초 timeout)**

### gold proof 전체 — 4줄

```coq
Theorem ge_0_F2R : forall m e : Z, (0 <= F2R (Float beta m e))%R -> (0 <= m)%Z.
Proof.
intros m e H.
apply le_F2R with e.
now rewrite F2R_0.
Qed.
```

### gold lemma signature

```coq
Theorem le_F2R : forall e m1 m2 : Z, (F2R (Float beta m1 e) <= F2R (Float beta m2 e))%R -> (m1 <= m2)%Z.
Theorem F2R_0 : forall e : Z, F2R (Float beta 0 e) = 0%R.
```

### 모델이 만든 proof — 1,176스텝

```coq
   1| Proof.
   2| intros m e H.
   3| unfold F2R in H.
   4| simpl in H.
       …
     | assert (forall (m:Z)(e:radix), F2R (Float beta m e) = (IZR m * bpow e)%R) as H_asrt0.
       ← F2R 의 정의를 그대로 베낀 것. Coq 통과(VALID). 그런데 닫지 못한다
       …
```

중복 상위:

```
  340× auto with arith.
  197× Proof.
  185× intros m e H.
  106× unfold F2R in H.
   79× simpl in H.
```

**1,176스텝 중 907스텝(77%)이 위 다섯 개의 반복이다.** `le_F2R` 은 한 번도 안 나온다.

---

## 3. 사례 C — 베낀 명제가 정확한데도 실패 (실패)

**`idx 1111` · Flocq — 실패, 538스텝, assert 후보 254개**

### gold proof 전체 — 6줄

```coq
Lemma u_rod1pu_ro_le_u_ro : (u_ro / (1 + u_ro) <= u_ro)%R.
Proof.
assert (Pu_ro := u_ro_pos).
apply (Rmult_le_reg_r (1 + u_ro)); [lra|].
unfold Rdiv; rewrite Rmult_assoc, Rinv_l; [|lra].
assert (0 <= u_ro * u_ro)%R; [apply Rmult_le_pos|]; lra.
Qed.
```

### gold lemma signature

```coq
Lemma Rmult_le_reg_r : forall r r1 r2, 0 < r -> r1 * r <= r2 * r -> r1 <= r2.
Lemma Rmult_assoc   : forall r1 r2 r3:R, r1 * r2 * r3 = r1 * (r2 * r3).
Lemma Rmult_le_pos  : forall r1 r2, 0 <= r1 -> 0 <= r2 -> 0 <= r1 * r2.
Definition Rdiv (r1 r2:R) : R := r1 * / r2.
```

### 모델이 만든 것

```coq
assert (forall r r1 r2, 0 < r -> r * r1 <= r * r2 -> r1 <= r2) as H_asrt0.
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^  Rmult_le_reg_r 과 100% 일치
```

**명제는 정확하다.** (인자 순서만 `r1*r` → `r*r1` 로 다르다.)
그런데 이 assert 를 닫지 못하고, 대신 이런 것들을 반복한다:

```
  275× Proof.
   31× exact le_trans.
   23× assert (forall r1 r2 r3, r1 <= r2 -> r2 < r3 -> r1 < r3) as H_asrt0.
   19× unfold u_ro.
   18× assert (forall r1 r2 r3, r1 <= r2 -> r2 <= r3 -> r1 <= r3) as H_asrt0.
```

**같은 assert 를 41번(23+18) 다시 세운다.** 세우고, 못 닫고, 다시 세운다.

---

## 4. 정리 — `assert` 가 한 일

| | |
|---|---|
| ✅ 명제는 안다 | 겹침 중앙 43% · ≥80% 가 15.8% · Coq 통과 45.8% |
| ❌ 그걸로 진도를 못 뺀다 | `{ exact L }` 로 이어지는 것 **18.3%** · `Proof.` 로 새는 것 **54.2%** |
| ❌ 필요 없을 때도 쓴다 | 사례 A — 이름을 알면서(`exact bitwise_binop_shl`) 우회 |
| ❌ 같은 걸 반복한다 | 사례 C — 동일 assert 41회 |

**`assert` 는 "이름을 모를 때의 대안"이 아니라 "이름을 부르는 대신 하는 딴짓"이 됐다.**

이것이 v10 에서 `CUT_SUBSTEP` 을 끄고 **gold lemma 를 프롬프트에 직접 끼워 넣는**
쪽으로 바꾼 이유다 → [../../v10/README.md](../../v10/README.md)

---

## 5. 재현

```bash
python3 scripts/assert_reality.py all_results/v9_ckpt25000_rand200_t600_w2/logs
# → all_log/assert_reality.json
```
