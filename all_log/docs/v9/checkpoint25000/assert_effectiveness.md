# `assert`(cut) 기계는 작동하는가 — 설계 의도 대비 실측

> 넣은 이유: **검색이 gold lemma 를 못 찾을 때**, 모델이 그 명제를 직접 세우고
> (`assert`) 바로 닫게(`{ exact L. }`) 하려는 것.
> 이 문서는 그게 실제로 일어나는지, 어디서 끊기는지를 잰다.
>
> 자료: rand200 대조군 200정리 완주 (ckpt-25000 · 3072 · w2 단독 · 성공률 30.0%)

---

## 0. 결론 세 줄

1. **기계는 설계대로 작동한다.** `assert → exact → 사용` 3단 체인이 실제로 완성된다.
2. **끊기는 곳은 `exact` 다.** close 시도 1,767건 중 **33.1% 실패**, 그 **99.8%가 "이름 없음"**.
   명제는 맞게 세우는데 **닫을 lemma 이름을 지어낸다.**
3. 그래서 "`assert` 뒤에 `{` 를 강제"하는 보상은 **표적이 아니다** —
   모델은 이미 70.6% 가 close 를 시도한다. 문제는 close 의 **내용**이다.

---

## 1. 설계 — cut 기계가 만드는 것

`src/tactic_gen/assert_split.py:206`

```python
out = [f"assert ({stmt}) as {h}. {{ exact {nm}. }}" for stmt, h, nm in lines]
```

그런데 이 전체가 학습 정답이 되는 게 아니다. `tactic_data.py`

```python
subs = _split_substeps(cut)          # [(assert, "assert"), (close, "close"), (final, "final")]
pick = hash(key) % len(subs)         # ★ 그중 **하나만** 정답
```

`_split_substeps` 의 주석:

```
assert  `assert (P) as H.`   — 이 다음 goal 이 P 가 된다
close   `exact L.`           — goal 이 P. **여기가 검색이 필요한 스텝**이다
final   마무리               — 원래 tactic 을 H_asrt 로 바꾼 것
```

즉 **스텝 단위 모델이므로 세 조각을 세 스텝에 나눠 학습**한다. 추론에서도
`assert` 한 스텝, `exact` 한 스텝, `final` 한 스텝으로 나온다.

---

## 2. 실제로 체인이 완성되는가 — **된다**

로그에서 뽑은 실제 3단 체인:

```
[idx 1073 · 깊이 3]
   3. assert (forall x y z, x<=y -> y<=z -> x<=z) as H_asrt0.   → VALID
   4. exact le_trans.                                            → VALID
   5. apply (H_asrt0 (Zdigits x) (Zdigits (x + 1))).             → VALID

[idx 1111 · 깊이 2]
   2. assert (forall r1 r2 r3, r1 <= r2 -> r2 < r3 -> r1 < r3) as H_asrt0.  → VALID
   3. exact le_lt_trans.                                                     → VALID
   4. apply H_asrt0 with 0%R.                                                → VALID

[idx 115 · 깊이 4]
   4. assert (forall x y, (x < y)%R -> x <> y) as H_asrt0.       → VALID
   5. exact Rlt_not_eq.                                          → VALID
   6. destruct (H_asrt0 (round beta fexp Zrnd_odd x) 0) as [].   → VALID

[idx 1009 · 깊이 3]
   3. assert (forall bc ge rs sp m ae rm am, ematch bc rs ae -> …) as H_asrt0.  → VALID
   4. exact abuiltin_arg_sound.                                                 → VALID
   5. generalize (H_asrt0 bc ge m sp m rm am).                                  → VALID
```

**설계한 그대로다.** 명제를 세우고, 검색으로 찾은 lemma 로 닫고, 그 가설을 쓴다.

---

## 3. 숫자로 — 어디서 얼마나 새는가

### 3-1. 1단계 `assert` — 명제 세우기

```
모델이 만든 assert 4,874개
   VALID   3,727 = 76.5%      ← Coq 이 명제로 받아들인다
   INVALID 1,147 = 23.5%      (없는 이름·표기·scope)
   H_asrt 이름 사용 71.5%      ← 학습의 cut 패턴을 그대로 따라함
```

### 3-2. 2단계 `close` — 닫기

VALID 인 assert 뒤에 **같은 시도의 다음 스텝**이 있는 2,505건에서:

| 다음 스텝 | 건수 | 비중 |
|---|---|---|
| **`exact …` 로 시작** | 1,525 | **60.9%** |
| `{` 로 시작 | 242 | 9.7% |
| 또 `assert` | 161 | 6.4% |
| `apply …` | 85 | 3.4% |
| 그 밖 | 490 | 19.6% |

**70.6% 가 close 를 시도한다.** (1,213건은 assert 직후 시도 자체가 끝났다.)

그 close 의 결과:

```
assert(VALID) → close 로 이어진 1,767건
   VALID    1,183 = 66.9%
   INVALID    584 = 33.1%
       └ 이름 없음  583 = 99.8%   ★
       └ 구문         1 =  0.2%
```

### 3-3. 3단계 `final` — 세운 가설 쓰기

```
close 성공 뒤 final 스텝:  VALID 562 · INVALID 117
```

**562번은 3단이 전부 통과한다.**

---

## 4. ★ 끊기는 지점 — 명제는 맞는데 **이름을 지어낸다**

close 실패 583건의 99.8%가 "이름 없음"이고, 예시가 증상을 그대로 보여준다.

```coq
assert (forall x y z, x<=y -> y<z -> x<z) as H_asrt0.    (* VALID — 명제는 정확 *)
exact zle_lt_trans.        → The variable zle_lt_trans was not found

assert (forall x y, x<y <-> y>=x) as H_asrt0.             (* VALID *)
exact lt_ge_iff.           → The variable lt_ge_iff was not found

assert (forall x y z, (z<=x)%Z <-> (z<=y)%Z) as H_asrt0.  (* VALID *)
exact Zle_is_le.           → The variable Zle_is_le was not found
```

전부 **그럴듯한 이름**이다 — `zle_lt_trans`(진짜는 `Z.le_lt_trans`),
`lt_ge_iff`, `Zle_is_le`. 모델은 **무엇이 필요한지는 아는데 그것의 이름을 모른다.**

### 그리고 이건 원래 목적과 정확히 맞물린다

cut 기계를 넣은 이유가 "검색이 이름을 못 찾을 때"였다. 실측:

```
(gold lemma, 정리) 쌍 304개 중
   모델이 α-유사도 ≥0.55 인 명제를 세운 것  135 = 44.4%
   유사도 = 1.00 (α-동치, 즉 같은 명제)     다수
```

```coq
gold lemma : bpow_ge_0
  명제     : Theorem bpow_ge_0 : forall e : Z, (0 <= bpow e)%R.
  모델     : assert (forall e : Z, (0 <= bpow e)%R).          ← 글자까지 동일

gold lemma : Zceil_imp
  명제     : Theorem Zceil_imp : forall n x, (IZR (n-1) < x <= IZR n)%R -> Zceil x = n.
  모델     : assert (forall n x, (IZR (n-1) < x <= IZR n)%R -> Zceil x = n) as H_asrt0.

gold lemma : unsigned_zero
  명제     : Theorem unsigned_zero: unsigned zero = 0.
  모델     : assert (unsigned zero = 0).
```

**명제 재구성은 이미 되고 있다.** 실패는 그 다음, 이름을 대는 자리다.

---

## 5. 전체 proof 비교 — gold vs 생성

### 5-1. 거의 맞은 경우 (idx 528 · `lib/Maps.v` · 실패)

```coq
── gold (2스텝) ──
assert (REC: forall k v l m, list_norepet (map fst l) -> In (k, v) …)
{ induction l as [ | [k1 v1] l]; simpl; intros.
  contradiction.
  inv H. destruct H0. …

── 모델이 만든 가장 긴 증명 (15줄) ──
Proof.
assert (REC: forall l k v,                        ← 이름도 REC, 구조도 같음
  list_norepet (map fst l) ->                        (인자 순서만 k v l → l k v)
  In (k, v) l ->
  T.get k (of_list l) = Some v).
{
induction l as [ | [k1 v1] l]; simpl; intros.       ← gold 와 **글자까지 동일**
- destruct H0.
- destruct H0.
  + inversion H0; subst.
    inversion H; subst.
    apply of_list_unique.
```

gold 는 `contradiction. inv H.` 로 가는데 모델은 `destruct H0` 로 갈라 다른 가지로 들어갔다.
**백트래킹이 없어** 되돌아오지 못한다.

### 5-2. VALID 루프에 빠진 경우 (idx 1111 · `flocq/Prop/Relative.v` · 실패)

```coq
── gold (4스텝) ──
assert (Pu_ro := u_ro_pos).
apply (Rmult_le_reg_r (1 + u_ro)); [lra|].
unfold Rdiv; rewrite Rmult_assoc, Rinv_l; [|lra].
assert (0 <= u_ro * u_ro)%R; [apply Rmult_le_pos|]; lra.

── 모델 (15줄) ──
Proof.
assert (H := u_rod1pu_ro_pos).     ← gold 의 u_ro_pos 와 비슷한 것을 골랐다
unfold u_ro in H.
unfold Rdiv in H.                  ↓
unfold Rdiv in H.                  ↓  같은 것을 12번 반복
unfold Rdiv in H.                  ↓  (전부 VALID · 상태는 안 바뀜)
…
assert (forall r, r <> 0 -> / r <> 0) as H_asrt0.
```

`try_candidates=1` 이라 같은 노드에서 다른 후보를 못 보고, 상태가 같으니 같은 것을 또 뽑는다.

### 5-3. cut 을 계단처럼 쌓은 경우 (idx 584 · `flocq/Core/Generic_fmt.v` · 실패)

```coq
── gold (5스텝) ──
intros x ex Hx He.
apply Zceil_imp.
simpl.
assert (H := mantissa_small_pos x ex Hx He).   ← 있는 lemma 를 한 줄로 끌어온다
split ; try apply Rlt_le ; apply H.

── 모델 (13줄) ──
Proof.
intros x ex Hx He.                    ← 여기까지 gold 와 동일
cut ((x * bpow (- fexp ex)) < 1)%R.   ↓ 목표를 자기가 만든 부등식으로 바꾸고
intros H.
cut ((x * bpow (- fexp ex)) >= 0)%R.  ↓ 또 만들고
intros H0.
cut ((x * bpow (- fexp ex)) <= 1)%R.  ↓ 또 만든다
intros H1.
```

세울 때마다 증명할 subgoal 이 하나씩 는다.

---

## 6. gold 는 `assert` 뒤에 무엇을 하나 — 코퍼스 실측

| 다음에 오는 것 | CompCert (2,227개) | TRAIN 표본 (1,123개) |
|---|---|---|
| 같은 문장에서 `by tac` | **26.7%** | 5.0% |
| 같은 문장에서 `; tac` | 2.5% | 1.9% |
| 같은 문장에서 `{ … }` | 0.6% | 0.5% |
| **바로 다음이 `{`** | **33.3%** | 20.3% |
| 바로 다음이 불릿 | 0.0% | 0.6% |
| **그냥 다음 tactic (구분자 없음)** | **36.9%** | **71.7%** |

**즉시 닫는 비율**(같은 문장 + 바로 `{`)은 CompCert **63.1%**, TRAIN **27.7%** 다.
나머지는 중괄호 없이 이어지는 tactic 들이 그 assert 를 증명한다.

```coq
(* ② 바로 다음이 { *)
assert (A: 0 <= p' < 2 ^ Z.of_nat n).
{ rewrite <- two_power_nat_equiv; apply … }

(* ① 같은 문장 by *)
assert (Int.max_unsigned = two_p 31 + two_p 31 - 1) by reflexivity.

(* ④ 구분자 없음 — 다음 tactic 들이 곧 증명 *)
assert (repr a = a).
rewrite (repr_some a a'); auto.
```

---

## 7. "`assert` 뒤에 무조건 `{` 를 하게 RL" 은 답인가 — **표적이 아니다**

세 가지 이유.

**(1) 모델은 이미 close 를 시도한다.** VALID assert 뒤 **70.6%** 가
`exact`(60.9%) 또는 `{`(9.7%) 로 이어진다. "안 닫는다"가 문제가 아니다.

**(2) `{` 자체가 gold 의 지배적 형태가 아니다.** CompCert 기준 `{` 는 33.3% 이고
`by tac` 이 26.7%, 구분자 없음이 36.9% 다. `{` 를 강제하면 **gold 분포에서 멀어진다.**

**(3) 진짜 실패는 close 의 *내용* 이다.** close INVALID 584건의 **99.8%가 "이름 없음"**.
`{` 를 붙였어도 그 안의 `exact zle_lt_trans.` 는 똑같이 실패한다.

### 형태를 보상하면 안 되는 이유

Coq 은 이미 **결과로** 채점해 준다(VALID/INVALID/COMPLETE). 형태에 보상을 주면
"형태는 맞는데 안 통하는" 것을 강화한다. 지금 실패의 대부분이 정확히 그 종류다.

### 대신 보상할 것

`assert → close → final` **3단이 전부 VALID 로 통과했는가** 를 보상하면 된다.
그건 형태가 아니라 **결과**이고, 지금 562번 일어난다. GRPO 의 Coq 보상이
이미 그것을 준다 — 다만 **정리 단위 보상(0/1)이라 신호가 희소**하다.

→ **cut 체인 완성을 중간 보상**으로 주는 것이 자연스럽다.
저장소의 `shape_gold`(potential-based shaping, 최적 정책 불변 보장)가 바로 그 틀이다.

---

## 8. 그래서 무엇을 해야 하나

| 표적 | 크기 | 수단 |
|---|---|---|
| **close 의 이름 환각** | close 실패의 **99.8%** | ★ **세운 명제를 질의로 재검색** (아래) |
| assert 자체의 환각 | assert 의 23.5% | 검색 풀 (펑터 전개 등) |
| VALID 루프 | idx 1111 형 | 상태 불변 tactic 거부 · `try_candidates>1` |
| 갈래 이탈 | idx 528 형 | 백트래킹 |

### ★ 가장 유망한 것 — 명제로 되찾기

지금 흐름:

```
assert (forall x y z, x<=y -> y<z -> x<z) as H_asrt0.   ← 명제는 정확하다
exact zle_lt_trans.                                     ← 이름을 지어낸다 (실패)
```

고칠 흐름:

```
assert (P) 를 세운 직후, **P 를 질의로** premise 풀을 검색한다
   → α-동치(유사도 1.0)인 premise 가 있으면 그 이름으로 exact 를 채운다
```

우리에게 **그 판정기가 이미 있다** — `eqx`/`afh70` 이 정확히 "전체 명제의 α-동치"를 본다
(`au_f_alpha`). 이 문서의 §4 분석에 쓴 것이 그것이다.

그리고 이 방식은 `functor-names.md` 가 지적한 근본 문제를 정면으로 돌파한다:
**지금 검색은 goal 로만 질의하는데, 외부 참조 lemma 는 goal 어휘에 안 나타난다.**
`assert` 가 세운 명제로 질의하면 **필요한 명제 자체로** 찾게 된다.

---

## 부록 — 재현

```bash
# 체인 실측
python3 - <<'PY'
import re, glob
D="all_results/v9_ckpt25000_rand200_t600_w2/logs"
# 후보 tactic 과 결과를 깊이(내부iterate#) 와 함께 읽어 assert→close→final 을 잇는다
PY

# gold 코퍼스에서 assert 뒤에 오는 것
#   (CompCert 2,227개 · TRAIN 표본 1,123개)
```
