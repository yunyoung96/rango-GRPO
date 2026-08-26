# `apply` · `rewrite` 가 취할 수 있는 모든 형태 — 문법과 CompCert 실측

> 왜 이 문서가 필요한가: 우리 실패의 상당수가 **"lemma 이름은 맞는데 형태가 틀린"**
> 것이다. 그런데 "형태"가 정확히 무엇들인지 정리된 적이 없었다. 여기서 문법을 다 세우고,
> **CompCert 가 실제로 쓰는 분포**와 **모델이 실제로 쓰는 분포**를 나란히 둔다.

---

## 0. "종류별 분해"가 무슨 말인가

`scripts/next_step_report.py` 는 gold 의 다음 한 수를 물어본 결과를 두 갈래로 찍는다.

```
                 스텝    top1    top8  │  이름스텝   이름맞힘    완벽  조립실패  도달실패
   apply/eapply   412   18.2%   31.1%  │     412     55.3%   31.1%    24.2%    44.7%
   rewrite        380   12.4%   22.6%  │     380     48.9%   22.6%    26.3%    51.1%
   rewrite <-     143    9.1%   16.8%  │     143     41.3%   16.8%    24.5%    58.7%
   apply … with    47    6.4%   12.8%  │      47     51.1%   12.8%    38.3%    48.9%
```
*(숫자는 형식 예시다. 실제 값은 실행 결과로 채운다.)*

읽는 법:

* **이름맞힘** — 후보 8개 중 하나라도 gold 가 부르는 lemma **이름**을 언급했는가
* **완벽** — 이름도 맞고 tactic 전체가 gold 와 같은가
* **조립실패** — 이름은 맞혔는데 전체가 다르다 → **형태를 못 맞춘 것**
* **도달실패** — 이름조차 안 나왔다 → **떠올리지 못한 것**

그래서 예컨대 `apply` 행의 도달실패가 낮고 조립실패가 높은데 `rewrite` 행은 반대라면,
"`apply` 는 뭘 쓸지는 아는데 어떻게 쓸지를 모르고, `rewrite` 는 아예 못 떠올린다"가 된다.
**대책이 완전히 다르다** — 앞은 DPO 형태 쌍, 뒤는 검색이다.

---

## 1. `apply` 계열 — 문법 전부

### 1-1. 기본형

```coq
apply L.                    (* L 의 결론이 goal 과 단일화. 남은 전제가 새 goal 이 된다 *)
```
단일화는 **고차 패턴 단일화**로 자동으로 일어난다. 모든 인자를 Coq 이 알아서 정한다.
정하지 못하면 실패한다: `Unable to find an instance for the variable x`.

### 1-2. `eapply` — 못 정한 것을 **미룬다**

```coq
eapply L.                   (* 못 정한 변수는 evar(?x)로 남기고 진행 *)
```
남은 `?x` 는 뒤의 tactic 이 채운다. **실패를 뒤로 미루는** 형태라 실패율이 가장 낮다.

### 1-3. 인자를 직접 주는 두 방법

```coq
apply L with (x := e).            (* ★ 이름으로. arity 를 몰라도 된다 *)
apply L with (x := e) (y := e').  (* 여러 개 *)
apply (L a _ c).                  (* 항 부분적용. 위치로. _ 는 Coq 이 채운다 *)
apply L a b.                      (* 위치 나열 — CompCert 에는 사실상 없다 *)
```

**핵심 차이**: `with (x := e)` 는 **바꾸고 싶은 것만** 이름으로 지정한다. lemma 의
인자가 몇 개인지, 어느 게 암묵인지 몰라도 된다.
`apply (L a _ c)` 는 **자리를 알아야** 한다 — arity 와 순서를 틀리면 바로 죽는다.

`with` 뒤에 이름 하나만 오는 형태도 있다(**괄호도 `:=` 도 없다**):

```coq
apply Rle_trans with x.                    (* 첫 미결정 변수를 x 로 *)
apply agree_change_sp with (parent_sp s).  (* 항으로 — parent_sp 는 정의(함수) *)
```

이때 뒤에 오는 것은 대개 **데이터**(변수·정의·생성자)지 증명이 아니다.
증명이 오는 경우는 §1-7 에서 따로 본다.

### 1-4. 방향 — 가설에 적용

```coq
apply L in H.               (* 전방향: H 를 L 로 변형 *)
apply L in H as [x Hx].     (* 변형하면서 분해 *)
apply L in H1, H2.          (* 여러 가설에 *)
eapply L in H.
```
`apply L`(후방향, goal 을 바꾼다)과 **방향이 반대**다. L 의 결론이 `H` 와 맞아야 한다.

### 1-5. iff 전용 방향 지정

```coq
apply -> L.                 (* L : A <-> B 일 때 A → B 방향 *)
apply <- L.                 (* B → A 방향 *)
```

### 1-6. 기타

```coq
simple apply L.             (* delta 전개 없이 — 더 엄격, 더 빠름 *)
apply L1, L2.               (* L1 적용 후 첫 subgoal 에 L2 *)
apply L; auto.              (* 적용 후 남은 subgoal 을 auto 로 *)
exact (L a b).              (* goal 을 정확히 닫는 항을 직접 준다. 새 goal 없음 *)
refine (L _ _ e _).         (* 구멍 뚫린 항. 구멍이 새 goal 이 된다 *)
```

**스펙트럼**(자동↔수동):
```
apply  <  eapply  <  apply … with  <  apply (L a _ c)  <  refine  <  exact
 ↑ 전부 자동                              ↑ 자리를 알아야                 ↑ 전부 수동
```

### 1-7. ★ 한 tactic 이 lemma 를 **여러 개** 부르는 형태

`apply L1 with L2` 같은 것이 실제로 있다. 세 갈래인데 **뜻이 전부 다르다.**

```coq
(* ㉮ 가설 자리를 다른 증명으로 채운다 — 이것이 "apply L1 with L2" 다 *)
apply Rlt_le_trans with (2 := proj1 Hx').   (* L1 의 2번째 전제를 proj1 Hx' 로 *)
apply Rle_not_lt with (1 := H).             (* 1번째 전제를 가설 H 로 *)
now apply H2 with (3 := Rle_refl x).        (* 3번째 전제를 stdlib lemma 로 *)

(* ㉯ 차례로 적용한다 — 쉼표 *)
apply eventually_and_invariant; eauto using subject_reduction, wt_prog.
now apply F2R_neq_0, Zgt_not_eq.            (* L1 적용 후 첫 subgoal 에 L2 *)

(* ㉰ 항 안에 lemma 가 들어간다 — 괄호 적용 *)
apply (combine_comparison_cmp_sound valu c v v0 res res'); auto.
```

**㉮ 의 `(N := proof)` 가 핵심이다.** `N` 은 lemma 의 **N 번째 전제**를 가리키고,
거기에 넣는 것은 **증명**이다 — 가설(`H1`)일 수도, 다른 lemma(`Rle_refl x`)일 수도,
합성(`proj1 Hx'`)일 수도 있다. 이름으로 지정하는 `(x := e)` 와 달리 **숫자**를 쓴다
(전제에는 이름이 없으므로).

> 모델이 이 형태를 내려면 **lemma 를 두 개 동시에 떠올려야** 한다.
> 하나는 뼈대(`Rlt_le_trans`), 하나는 그 구멍을 메울 증명(`proj1 Hx'`).
> 검색이 둘 다 실어 줘야 한다는 뜻이다 — v10 이 gold 를 **전부** 끼워 넣는 이유.

---

## 2. `rewrite` 계열 — 문법 전부

`rewrite` 는 **등식(또는 iff)** 을 받아 goal 안의 부분항을 치환한다.
`L : a = b` 이면 goal 의 `a` 를 `b` 로 바꾼다.

### 2-1. 기본형과 방향

```coq
rewrite L.                  (* a → b *)
rewrite <- L.               (* b → a. 반대 방향 *)
rewrite -> L.               (* a → b. 기본값이라 거의 안 쓴다 *)
```

### 2-2. 어느 인스턴스인지 지정

```coq
rewrite (L a b).            (* ★ L 을 부분적용해 **어느 인스턴스**인지 못박는다 *)
rewrite L with (x := e).    (* 같은 일을 이름으로 *)
```
`rewrite L` 이 `Found no subterm matching` 으로 죽는 흔한 이유는 **어느 인스턴스인지
Coq 이 못 고르는 것**이다. 인자를 박으면 그게 해결된다.

### 2-3. 몇 번째 등장인지 지정

```coq
rewrite L at 1.             (* 첫 번째 등장만 *)
rewrite L at 2 4.           (* 2·4 번째 *)
rewrite <- (L x) at 1.      (* 조합 *)
```

### 2-4. 반복 지정

```coq
rewrite !L.                 (* 1회 이상 최대한 반복. 0회면 실패 *)
rewrite ?L.                 (* 0회 이상. 0회여도 성공 *)
rewrite 2!L.                (* 정확히 2회 *)
```

### 2-5. 위치

```coq
rewrite L in H.             (* 가설 H 안에서 *)
rewrite L in H1, H2.
rewrite L in *.             (* goal 과 모든 가설에서 *)
rewrite L in * |-.          (* 가설에서만 *)
```

### 2-6. 부수 goal 처리

```coq
rewrite L by auto.          (* L 의 전제(부수 goal)를 auto 로 즉시 닫는다 *)
rewrite L by lia.
```
조건부 등식(`H : P -> a = b`)을 쓸 때 필요하다. `by` 가 없으면 `P` 가 새 goal 로 남는다.

### 2-7. 연쇄와 변종

```coq
rewrite L1, L2, <- L3.      (* 차례로. 하나라도 실패하면 전체 실패 *)
erewrite L.                 (* 못 정한 변수를 evar 로 — eapply 의 rewrite 판 *)
setoid_rewrite L.           (* 동치관계(setoid) 아래에서 *)
rewrite_strat (topdown L).  (* 재작성 전략 지정 *)
```

**`rewrite` 도 lemma 를 여러 개 쓴다** — 오히려 `apply` 보다 흔하다.

```coq
(* ㉮ 쉼표 나열 — rewrite 의 다중 lemma 는 대부분 이것이다 *)
rewrite Zzero_ext_spec, zlt_false, Z.shiftr_spec.
rewrite andb_true_r, orb_false_r; auto.

(* ㉯ 부수 전제를 다른 증명으로 채운다 — apply 의 (N := proof) 와 같다 *)
rewrite F2R_change_exp with (1 := H).
rewrite cexp_inbetween_float with (1 := Px) (2 := Bx).
rewrite round_AW_UP with (1 := Rabs_pos _).      (* stdlib lemma 를 넣는다 *)
rewrite Rnd_N_pt_unique with (3 := Hm) (4 := Rxf) (5 := Rxg).   (* 세 개 *)

(* ㉰ 항 적용 *)
try rewrite (ireg_of_eq _ _ EQ); try rewrite (freg_of_eq _ _ EQ).
```

㉮ 는 **순차**다(`L1` 로 고치고, 그 결과에 `L2`). ㉯ 는 **동시**다
(`L1` 하나를 쓰는데 그 전제를 메우는 데 다른 증명이 필요).
하나라도 실패하면 **전체가 실패**한다 — 부분 성공이 없다.

### 2-8. 전부 합친 최대형

```coq
rewrite <- (L a b) at 2 in H by lia.
        │   │      │    │      └ 부수 goal 을 lia 로
        │   │      │    └ 가설 H 안에서
        │   │      └ 두 번째 등장만
        │   └ 인스턴스를 a b 로 못박고
        └ 반대 방향으로
```

---

## 3. CompCert 는 실제로 무엇을 쓰나

`apply`/`eapply`/`rewrite`/`erewrite` 호출 **45,572회** (주석 제거 후, 특징 중복 집계).

| 특징 | 횟수 | 비중 | 예 |
|---|---|---|---|
| 맨 형태 (`apply L.`) | 28,206 | **61.9%** | `apply integer_representable_n` |
| `eapply` | 6,478 | 14.2% | `eapply ZofB_range_widen` |
| `<-` | 2,626 | 5.8% | `rewrite <- two_power_nat_equiv` |
| `with (x := e)` | 2,457 | **5.4%** | `apply integer_representable_2p with (p := 31)` |
| `by tac` | 2,093 | 4.6% | `rewrite BofZ_plus by auto` |
| `(항 부분적용)` | 1,592 | **3.5%** | `rewrite (Bcompare_swap _ _ x y)` |
| `in H` | 1,473 | 3.2% | `rewrite ZofB_correct in C` |
| `,` (여러 개) | 1,349 | 3.0% | `rewrite SU, <- E` |
| `!` (반복) | 645 | 1.4% | `rewrite ! Int.add_assoc` |
| `erewrite` | 358 | 0.8% | |
| `at N` | 145 | 0.3% | `rewrite <- (repr_unsigned x) at 1` |
| `?` (0회 이상) | 49 | 0.1% | |
| `->` | 21 | 0.0% | |

★ **`apply L a b` (괄호 없는 위치 나열)는 10회 = 0.0%** 다. 그나마도 파싱 artifact.
CompCert 는 인자를 줄 때 **항상** `with (x := e)` 아니면 `(L a b)` 를 쓴다.

---

## 3.5. ★ lemma 를 몇 개나 쓰나 — 실측

CompCert `.v` 297개 · `apply`/`eapply`/`rewrite`/`erewrite` 호출 **21,223회**.
tactic 한 줄 안에서 **선언이 실재하는 이름**을 몇 개 부르는지 셌다
(sentence DB 의 선언 이름 37,569개와 대조 · 가설/지역이름은 안 셈).

| tactic | 호출 | lemma 0개 | **1개** | **2개** | **3개 이상** |
|---|---|---|---|---|---|
| `apply` | 9,426 | 25.1% | 65.2% | **6.4%** | **3.3%** |
| `eapply` | 3,104 | 33.3% | 64.0% | 2.5% | 0.2% |
| `rewrite` | 8,535 | 38.5% | 50.9% | **7.5%** | **3.1%** |
| `erewrite` | 158 | 44.9% | 52.5% | 1.9% | 0.6% |

**`apply` 9.7% · `rewrite` 10.6% 가 lemma 를 둘 이상 쓴다.** 드물지 않다.
(0개는 `apply H`(가설)·`rewrite IHn`(귀납가설) 같은 지역 이름만 쓰는 경우다.)

### 여러 개일 때 어떤 형태인가

| 형태 | 건수 | 예 |
|---|---|---|
| `rewrite` 쉼표 나열 | 409 | `rewrite andb_true_r, orb_false_r; auto.` |
| `apply … with <항>` | 299 | `apply agree_change_sp with (parent_sp s).` |
| `rewrite (L a b)` 항 적용 | 258 | `rewrite (ireg_of_eq _ _ EQ)` |
| `apply (L a b)` 항 적용 | 216 | `apply (combine_comparison_cmp_sound valu c v …)` |
| `apply` 쉼표 나열 | 102 | `now apply F2R_neq_0, Zgt_not_eq.` |

### ★ `with (N := 증명)` — 두 lemma 를 동시에 떠올려야 하는 형태

`with` 뒤에 오는 것의 정체를 갈라 보면:

| | 건수 |
|---|---|
| `apply … with (N := 가설/지역)` | **253** |
| **`apply … with (N := 증명 lemma)`** | **91** |
| `apply … with (N := 정의)` | 27 |
| `rewrite … with (N := 가설/지역)` | **138** |
| **`rewrite … with (N := 증명 lemma)`** | 2 |
| `rewrite … with (N := 정의)` | 5 |

**`apply L1 with (N := L2)` 로 진짜 증명 lemma 를 넣는 것이 91건.** 대표 예:

```coq
apply Rlt_le_trans with (2 := proj1 Hx').
apply Rlt_trans   with (1 := proj2 Hx').
now apply H2      with (3 := Rle_refl x).
eapply Rle_trans  with (2 := F2R_ge _ K).
```

`proj1`/`proj2` 가 33건씩으로 가장 많다 — 연언 가설에서 한쪽을 꺼내 전제에 꽂는 관용구다.

> **이 형태가 v10 에 직접 걸린다.** 모델이 뼈대(`Rlt_le_trans`)와 구멍을 메울
> 증명(`proj1 Hx'`)을 **동시에** 떠올려야 하므로, 검색이 **둘 다** 실어 줘야 한다.
> gold 를 하나만 끼워 넣으면 나머지 하나는 여전히 프롬프트에 없다 —
> v10 이 `MAX_INJECT = 0`(무제한)으로 **전부** 끼워 넣는 이유다
> ([v10/README.md §5.6](../../v10/README.md)).

---

## 4. 모델은 무엇을 쓰나 — 그리고 어디서 죽나

rand200 부분 실행(26정리 · 생성 15,453개)에서 형태별 사용량과 INVALID 율:

| 형태 | 모델 사용 | 실패율 | CompCert 비중 |
|---|---|---|---|
| `eapply L` | 659 | **7.1%** | 14.2% |
| `apply L with (x := e)` | **26** | **11.5%** | 5.4% |
| `apply L` | 475 | 17.1% | 61.9% |
| **`rewrite (L a b)`** | **16** | **25.0%** | 3.5% |
| `apply (L a _ c)` | 14 | 42.9% | 3.5% |
| **`apply L a b`** | **93** | **44.1%** | **0.0%** ★ |
| `rewrite L` | 563 | 44.4% | 61.9% |
| `rewrite <- L` | 209 | 51.2% | 5.8% |
| `apply L in H` | 60 | 63.3% | 3.2% |
| `rewrite L at n` | **0** | — | 0.3% |

### 읽어야 할 것 넷

**① 모델이 없는 형태를 지어낸다.** `apply L a b` 를 93회 썼는데 CompCert 에는 **0회**다.
그리고 44.1% 가 실패한다. 학습 데이터에 없는 문법을 만들어 내고 있다.

**② 가장 잘 되는 형태를 가장 덜 쓴다.**
`apply … with` 는 실패율 11.5% 로 맨 `apply`(17.1%)보다 낫고 CompCert 도 5.4% 쓰는데,
모델은 26회밖에 안 쓴다(맨 `apply` 475회 대비 **1/18**).

**③ `rewrite` 가 최악인데 해법이 안 쓰인다.**
`rewrite L` 실패율 44.4%. 그런데 인스턴스를 박은 `rewrite (L a b)` 는 25.0% 로 절반이고,
모델은 16회만 쓴다(563회 대비 **1/35**). 위치 지정 `at n` 은 **한 번도 안 쓴다.**

**④ 위치로 채우는 건 오히려 독이다.**
`apply (L a _ c)` 42.9% · `apply L a b` 44.1% — 둘 다 맨 `apply`(17.1%)보다 나쁘다.
**arity 와 순서를 모르기 때문**이다. 이것이 `refine` 이 답이 아닌 이유이기도 하다 —
`refine (L _ _ e _)` 은 정확히 "자리를 다 알아야 하는" 극단이다.

---

## 5. 그래서 무엇을 가르쳐야 하나

**중간 형태의 정의**: *arity 를 몰라도 되는 부분 지정*.

| 축 | 좋은 중간 | 나쁜 중간 |
|---|---|---|
| 인자 | `with (x := e)` — 이름으로 하나만 | `(L a _ c)` · `L a b` — 자리를 다 알아야 |
| 인스턴스 | `rewrite (L a b)` — 어느 것인지 | |
| 등장 위치 | `rewrite L at n` | |
| 미루기 | `eapply` · `erewrite` | |
| 부수 goal | `by auto` · `by lia` | |

DPO 형태 쌍(`dpo-design.md` Tier A)의 변형 집합을 이걸로 잡아야 한다:

```
apply L   →  eapply L
          →  apply L with (x := <goal 에서 읽은 항>)
          →  apply L in H
rewrite L →  rewrite <- L
          →  rewrite (L <인자>)
          →  rewrite L at 1  /  at 2
          →  erewrite L
          →  rewrite L by auto
```

**위치 인자형(`apply (L a b)` · `apply L a b`)은 변형 집합에서 뺀다.** 실측이
"맨 형태보다 나쁘다"고 말하고 있고, CompCert 도 안 쓴다.

---

## 부록 — 재현

```bash
python3 scripts/count_multi_lemma.py   # §3.5 lemma 개수 분포
python3 scripts/count_with_args.py     # §3.5 with 인자의 정체
```


```bash
python3 - <<'PY'
import re, glob, collections
CC="CoqStoq/test-repos/compcert"
CALL=re.compile(r"(?<![\w'])(e?apply|e?rewrite)\b([^.;|]*)", re.S)
c=collections.Counter(); tot=0
for f in glob.glob(CC+"/**/*.v", recursive=True):
    s=re.sub(r"\(\*.*?\*\)"," ",open(f,errors="ignore").read(),flags=re.S)
    for m in CALL.finditer(s):
        a=" "+m.group(2).strip()+" "; tot+=1
        if " with " in a: c["with"]+=1
        if re.match(r"\s*<-", a): c["<-"]+=1
        if re.match(r"\s*\(", a): c["(항)"]+=1
        if re.search(r"\bat\s+\d", a): c["at N"]+=1
        if re.search(r"\bby\b", a): c["by"]+=1
print(tot, dict(c))
PY
```
