# `rewrite L` 은 왜 실패하나 — 889건 해부

> `rewrite L` 은 rand200 에서 모델이 **1,785회** 생성하고 **814회 실패(45.6%)** 했다.
> 형태별 실패 중 **가장 큰 단일 항목**이고, `rewrite` 계열 전체로는
> **1,251건 = 전체 실패의 77%** 다. 왜 그런지 오류 문구로 해부한다.
>
> 자료: rand200 로그 124정리 (ckpt-12000/25000 합산)

---

## 1. 오류 종류 — 하나가 압도한다

`rewrite <이름>` 으로 시작하는 tactic 의 INVALID **889건**:

| 오류 | 건수 | 비중 |
|---|---|---|
| **대상 없음** (`Found no subterm matching …`) | **739** | **83.1%** |
| 이름 없음 (환각) | 78 | 8.8% |
| 기타 (대부분 `The LHS of X does not match …`) | 38 | 4.3% |
| 등식이 아님 (`Cannot find a relation to rewrite`) | 18 | 2.0% |
| 아무것도 안 바뀜 (`Nothing to rewrite`) | 15 | 1.7% |
| 구문 오류 | 1 | 0.1% |

`기타` 의 대부분도 결국 좌변 불일치(`The LHS of pop_spec_ok (pop _ _ _ _ = (_, _))
does not match any subterm of the goal`)이므로, **좌변이 goal 에 없다**가
**약 87%** 다.

**환각(이름 없음)은 8.8% 뿐이다.** `rewrite` 문제는 환각 문제가 아니다.

---

## 2. `rewrite` 가 하는 일 — 왜 "좌변"인가

```coq
L : a = b
```

`rewrite L` 은 goal 안에서 **`a` 와 맞는 부분항을 찾아** `b` 로 바꾼다.
`a` 를 **좌변(LHS)** 이라 하고, 이게 goal 어디에도 없으면 즉시 실패한다.

```coq
(* L : Int64.eq x y = Int64.eq y x   — 좌변은 Int64.eq ?x ?y *)
Goal   Int.eq p q = true
rewrite Int64.eq_sym.
   → Found no subterm matching "Int64.eq ?M ?M" in the current goal
     (goal 에는 Int.eq 만 있고 Int64.eq 는 없다)
```

`L` 의 좌변에 자유변수가 있으면 **패턴**이 된다(`?M` 이 그것). 패턴이 일반적일수록
맞을 자리가 많아지고, 구체적일수록 좁아진다.

---

## 3. 그 739건을 다시 가른다

### 3-1. 무엇으로 재작성하려 했나

| | 건수 | 비중 |
|---|---|---|
| **전역 lemma** | **706** | **94.9%** |
| 가설 (`H`·`EQ`·`STORE` 등) | 38 | 5.1% |

**거의 전부 라이브러리 lemma 다.** 문맥의 등식 가설을 잘못 쓰는 문제가 아니다.

### 3-2. 좌변 패턴이 얼마나 일반적이었나

| 좌변 패턴 | 건수 | 비중 |
|---|---|---|
| **메타변수 3개 이상 (매우 일반)** | **375** | **50.4%** |
| 메타변수 1~2개 | 237 | 31.9% |
| 메타변수 없음 (완전 구체) | 94 | 12.6% |
| (가설 쪽) | 38 | 5.1% |

**절반이 "매우 일반적인 패턴인데도 안 맞았다"** 는 것이 핵심이다.

```coq
rewrite split_join_bits.
   좌변 패턴: split_bits (join_bits ?M ?M ?M)
   → 세 인자가 전부 자유변수인데도 goal 에 그런 모양이 없다
```

인자가 전부 metavariable 이라 **`split_bits (join_bits …)` 라는 모양만 있으면
무엇이든 맞는다.** 그게 안 맞았다는 건 goal 에 그 연산 조합이 **아예 없다**는 뜻이다.

---

## 4. 그래서 원인은 무엇인가

`rewrite L` 실패의 가능한 원인은 다섯이다.

| 원인 | 고치는 형태 | 이번 자료가 말하는 것 |
|---|---|---|
| ① **방향이 반대** (goal 에 우변이 있음) | `rewrite <- L` | 가능. 다만 §3-2 의 "매우 일반" 절반은 방향을 바꿔도 모양 자체가 없다 |
| ② **인스턴스가 다름** | `rewrite (L a b)` | 메타변수 1~2개·구체 44.5% 구간의 후보 |
| ③ **위치가 다름** (가설 안) | `rewrite L in H` | 가능. 다만 `in *` 을 써도 `Nothing to rewrite` 가 15건뿐 |
| ④ **먼저 펴야 함** (`unfold` 뒤라야 모양이 드러남) | `unfold f; rewrite L` | 판별 불가(로그로는 못 봄) |
| ⑤ **애초에 틀린 lemma** | — | **§3-2 의 "매우 일반" 375건(50.4%) 이 여기 강하게 해당** |

★ **결론: `rewrite L` 실패의 절반은 형태 문제가 아니라 선택 문제다.**
좌변 패턴이 전부 metavariable 인데도 안 맞았다면, 방향·인스턴스·위치를 아무리
바꿔도 안 된다. **goal 과 상관없는 lemma 를 고른 것**이다.

이는 오라클 실험(`../checkpoint25000/experiment.md`)의 결론과 일치한다 —
**조건부 조립은 66~70% 로 준수하고 병목은 선택**이다.

---

## 5. 실제 사례

**(a) 모듈을 틀림** — `Int64` vs `Int`

```
rewrite Int64.eq_sym.
   → Found no subterm matching "Int64.eq ?M ?M"
```
goal 은 32비트 `Int` 인데 64비트 `Int64` 의 lemma 를 골랐다.
`functor-names.md` 의 펑터 문제와 이어진다 — `Int`·`Int64` 는 같은 펑터
`Make` 의 서로 다른 인스턴스라 **멤버 이름이 똑같다**(`eq_sym` 이 양쪽에 다 있다).

**(b) 연산 조합이 goal 에 없음**

```
rewrite split_join_bits.
   좌변: split_bits (join_bits ?M ?M ?M)
   → 자유변수 셋인데도 안 맞는다 = goal 에 그 조합이 없다
```

**(c) 가설을 등식으로 오인**

```
rewrite H0.       → Cannot find a relation to rewrite.
rewrite rolm_sound. → Cannot find a relation to rewrite.
```
`H0` 가 등식이 아닌데 `rewrite` 를 걸었다. 18건(2.0%).

**(d) 이미 그 모양이 없음**

```
rewrite H in *.   → Nothing to rewrite.
```
`in *` 로 전체를 훑어도 바뀔 게 없다. 15건(1.7%).

**(e) 문법을 틀림**

```
rewrite pop_preserves_invariant by eauto.
   → Syntax error: [ltac_use_default] expected after [tactic]
```
`by tac` 형태는 학습에 0.1% 밖에 없어서(CompCert 는 1.4%) 문법 자체를 틀린다.
이 형태만 따로 보면 실패율이 **84.4%(27/32)** 로 최악이다.

---

## 6. 무엇을 해야 하나

| 표적 | 크기 | 수단 |
|---|---|---|
| **선택 실패** (매우 일반 패턴인데 불일치) | ~50% of 739 | 검색·재랭킹. 특히 **펑터 인스턴스 구분**(`Int` vs `Int64` vs `Byte`) |
| 인스턴스/방향 | ~45% of 739 | DPO 형태 쌍 — `rewrite (L a b)` · `rewrite <- L` · `at n` |
| 환각 | 78건 (8.8%) | 검색 풀 |
| `by tac` 문법 | 27건 (84.4%) | 학습 분포 — TRAIN 0.1% vs CompCert 1.4% |

**우선순위**: `rewrite` 계열이 전체 실패의 **77%** 를 차지하므로 여기가 가장 큰 표적이다.
그중 절반이 선택 문제이므로, **펑터 인스턴스를 구분해 주는 검색 개선**
(`functor-names.md` §8)이 `rewrite` 에도 직접 듣는다 —
`Int.eq_sym` 과 `Int64.eq_sym` 이 지금은 풀에서 **같은 `eq_sym`** 으로 보인다.

---

## 부록 — 재현

```bash
python3 - <<'PY'
import re, glob, collections
DIRS=["all_results/v9_ckpt25000_rand200_t600_w2/logs"]
RW=re.compile(r"^\s*rewrite\s+[A-Za-z_]")
c=collections.Counter()
for D in DIRS:
    for f in glob.glob(D+"/*"):
        L=open(f, errors="ignore").read().split("\n")
        for i,l in enumerate(L):
            if "후보 tactic:" not in l: continue
            if not RW.match(l.split("후보 tactic:",1)[1].strip().strip("'")): continue
            blk=L[i+1:i+5]
            if not any("TacticResult.INVALID" in x for x in blk): continue
            err=" ".join(blk)
            c["대상없음" if "Found no subterm" in err else
              "환각" if "not found in the current" in err else "기타"]+=1
print(c)
PY
```
