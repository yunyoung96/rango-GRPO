# Coq 안에서 적용 가능한 lemma 찾기 — `SearchPattern` / `SearchRewrite`

> 한 줄: **goal 하나에서 질의를 기계적으로 뽑아 Coq 자신의 색인에 물어본다.**
> 밖에서 색인을 새로 만드는 8판본이 전부 실패한 자리를, Coq 내장 색인이 넘는다.

관련 문서 — [applicability-filter.md](applicability-filter.md) (색인 8판본 실패기),
[classical-lemma-retrieval.md](classical-lemma-retrieval.md) (고전 선행 연구)

---

## 1. 무슨 문제인가

`apply L` / `rewrite L` 을 쓰려면 **그 자리에서 실제로 적용되는 `L`** 을 찾아야 한다.
현행 rango 는 tf-idf 로 **관련성**을 점수 매긴다. 그런데 우리가 원하는 건 관련성이
아니라 **적용가능성**이다 — 이건 이항 술어이고, 텍스트 유사도로 근사되지 않는다.

밖에서 색인(지문·판별트리·치환트리)을 만들어 보는 시도는 8판본 전부 실패했다.
이유는 [applicability-filter.md](applicability-filter.md) §4 에 있다 — 출력형 텍스트를
보는 한 **변환(delta/iota)·notation·암묵인자**를 넘을 수 없다.

Coq 은 그 색인을 이미 갖고 있다. `SearchPattern` / `SearchRewrite` 다.

---

## 2. 질의는 어떻게 뽑나

**손으로 쓰지 않는다.** goal 하나에서 6족(族)이 기계적으로 나온다.
구현은 `src/premise_selection/coq_query.py`.

| 족 | 생성 규칙 | 노리는 것 |
|---|---|---|
| **① 사다리** | goal → 지역이름을 `?x` 로 → 인자만 흐림 → 관계만 남김 | `apply` 의 결론 매칭 |
| **② 부분항** | goal 의 **모든 부분항**마다 사다리 1~2단 | `rewrite` 의 redex |
| **③ 기호결합** | 경직 상수를 조합, 많은 것부터 줄여가며 | 좁고 정확한 후보 |
| **④ 가설방향** | 각 가설을 `<가설타입> -> ?zfwd` 로 | `apply L in H` (전방추론) |
| **⑤ 가설안** | 가설의 기호로 질의 | `rewrite L in H` |
| **⑥ 넓게** | 기호 하나씩, 관계 무제약 | 재현율 바닥 받치기 |
| **⑦ notation** | `Search "**"` — 문자열로 직접 | 프로젝트 고유 notation |

### 핵심 규칙 — 지역 이름만 `?` 로 바꾼다

```
goal:  PTree.get i (PTree.set j x (snd m)) = ...
지역:  i, j, m, x, A, H            ← 가설·변수. `?i` `?j` `?m` 로
전역:  PTree.get, PTree.set, snd    ← 경직 상수. 그대로 둔다
```

같은 이름은 **같은 `?`** 를 쓴다 — 그래야 `f a b = f x y` 처럼 "변수가 서로 달라야
한다"는 조건이 유지된다. `?x` 는 이름 있는 패턴 변수라 Coq 이 일관성을 강제한다.

---

## 3. 실제 전사 — 세 지점

### 3.1 `apply` — 왜 **사다리**가 필요한가

`idx 282 · flocq/Core/Raux.v` · gold = `apply Rle_lt_trans with (r1 * r4)%R.`

```
가설   r1, r2, r3, r4: R
       Pr1: (0 <= r1)%R      Pr3: (0 <= r3)%R
       H12: (r1 < r2)%R      H34: (r3 < r4)%R
goal   (r1 * r3 < r2 * r4)%R
```

질의 8개가 나왔고, 사다리 세 단이 이렇게 갈린다:

```
[0] ①사다리   6개   SearchPattern ((?r1 * ?r3 < ?r2 * ?r4)%R).
      │ Rmult_lt_compat_l: forall r r1 r2, (0 < r)%R -> (r1 < r2)%R -> (r * r1 < r * r2)%R
      │ Rmult_lt_compat_r: forall r r1 r2, (0 < r)%R -> (r1 < r2)%R -> (r1 * r < r2 * r)%R
      │ Rlt_3PI2_2PI: (3 * (PI / 2) < 2 * PI)%R
      │ … (11줄 더)

[1] ①사다리  19개   SearchPattern (((?r1 ?a0 ?a1) < (?r2 ?b0 ?b1))%R).
      │ Rplus_lt_compat_l: forall r r1 r2, (r1 < r2)%R -> (r + r1 < r + r2)%R
      │ Rplus_lt_compat:   forall r1 r2 r3 r4, (r1 < r2)%R -> (r3 < r4)%R -> (r1 + r3 < r2 + r4)%R
      │ … (36줄 더)

[2] ①사다리  ★gold  SearchPattern ((?zl < ?zr)%R).
      │ H12: (r1 < r2)%R
      │ Rgt_lt: forall r1 r2 : R, (r1 > r2)%R -> (r2 < r1)%R
      │ … (351줄 더)          ← 여기에 Rle_lt_trans 가 있다
```

**L0 도 L1 도 gold 을 못 찾는다.** `Rle_lt_trans : r1 <= r2 -> r2 < r3 -> r1 < r3` 의
결론은 `?a < ?b` 로, **goal 보다 일반적**이다. `SearchPattern` 은 "패턴의 인스턴스"를
찾으므로, 구체적인 패턴으로는 일반적인 lemma 를 **원리적으로** 못 잡는다.

> 이게 사다리를 쓰는 이유다. 어느 추상도에서 맞을지 모르니 **구체→추상으로 단을
> 올리며** 훑고 합집합한다. 대신 L2 는 357개를 반환한다 — 정밀도를 재현율과 맞바꾼다.

전체 8질의 합집합 **518개**, 우주(~20,000) 대비 **39배 축소**.

### 3.2 `rewrite` — 기호결합이 먼저 맞는 경우

`idx 1088 · lib/Integers.v` · gold = `rewrite bits_shl by lia.`

```
가설   x, y, z: int   Y, Z, i: BinNums.Z
       H: 0 <= Y < zwordsize    H1: 0 <= i < zwordsize    l: Z < Y
goal   (if zlt i (Y - Z) then false
        else testbit (zero_ext (zwordsize - Y) x) (i - (Y - Z)))
       = testbit (shl x y) (i + Z)
```

```
[0] ③기호결합   1개   Search zlt testbit zero_ext.
      │ bits_zero_ext: forall n x i, 0 <= i ->
      │   testbit (zero_ext n x) i = (if zlt i n then testbit x i else false)

[1] ③기호결합  ★gold  Search zlt testbit.
      │ bits_zero_ext: …
      │ sign_bit_of_unsigned: …
      │ … (29줄 더)            ← 여기에 bits_shl

[2] ③기호결합  ★gold  Search zlt.
      │ Zmax_spec / Zmin_spec / zlt_false / …
```

기호를 **많은 것부터 줄여가며** 쏘는 게 요점이다. `zlt testbit zero_ext` 는 1개로
너무 좁고, `zlt testbit` 에서 gold 이 나온다. 합집합 **4,490개**.

### 3.3 `rewrite` — 부분항을 정확히 짚어야 하는 경우

`idx 472 · lib/Maps.v` (Module PMap) · gold = `rewrite PTree.gso; auto.`

```
가설   A: Type   i, j: positive   x: A   m: t A   H: i <> j
goal   match PTree.get i (PTree.set j x (snd m)) with Some x0 => x0 | None => fst m end
     = match PTree.get i (snd m)              with Some x0 => x0 | None => fst m end
```

```
[0] ③기호결합   0개   Search PTree.get PTree.set snd.
[1] ③기호결합  ★gold  Search PTree.get PTree.set.
      │ PTree.gss:     forall [A] i x m, PTree.get i (PTree.set i x m) = Some x
      │ PTree.gsident: forall {A} i m [v], PTree.get i m = Some v -> PTree.set i v m = m
      │ … (6줄 더)      ← 여기에 PTree.gso
```

이 goal 은 `SearchRewrite` 로도 직접 잡힌다:

```coq
SearchRewrite (PTree.get ?i (PTree.set ?j ?x ?m)).
```
```
PTree.gss:    forall [A] (i : positive) (x : A) (m : PTree.tree A), (PTree.set i x m) ! i = Some x
PTree.gso:    forall [A] [i j : positive] (x : A) (m : PTree.tree A),
                i <> j -> (PTree.set j x m) ! i = m ! i          ← gold
PTree.gsspec: forall [A] (i j : positive) (x : A) (m : PTree.t A),
                (PTree.set j x m) ! i = (if peq i j then Some x else m ! i)
```

**후보 3개.** 우주 20,000 → 3 이면 6,600배 축소다. 다만 이 질의를 만들려면
부분항을 정확히 뽑아야 하는데, 여기 **두 개의 함정**이 있었다(§5.2, §5.3).

---

## 4. 드라이버 — `coqc` 가 아니라 `coqtop`

가장 크게 회수한 것은 질의 생성이 아니라 **실행 방식**이다.

`coqc` 는 vernacular 오류가 나면 **그 파일 처리를 중단**한다. 질의를 수십 개
이어붙이는 우리 방식에서는 **하나만 깨져도 뒤가 전부 죽는다.**

실측(w7, CompCert 245 지점):

```
발행 질의 중앙 59  ·  실제 실행 중앙 32
질의를 잃은 지점 93/245 = 38.0%
잃은 질의 총 4,080개 (지점당 21.7)
```

범인은 세 부류였다:

| 오류 | 예 |
|---|---|
| 문법 오류 | `Search zlt mod.` — `mod` 는 예약어 |
| 미해결 이름 | `SearchRewrite (Some x0).` — `x0` 는 match 바인더 |
| notation | `Error: Abbreviation is not applied enough.` |

하나씩 막을 수도 있지만, **구조로 푸는 길**이 있다. `coqtop` 은 오류를 찍고 **다음
명령을 계속 실행한다.** 직접 확인:

```coq
(* 같은 파일을 coqc 와 coqtop 에 각각 먹인다 *)
SearchRewrite (PTree.get ?i (PTree.set ?j ?x ?m)).   (* 정상 *)
Search zlt mod.                                       (* 문법 오류 *)
SearchPattern (?zl => ?zr).                           (* 문법 오류 *)
Search nonexistent_thing_xyz.                         (* 미해결 이름 *)
SearchRewrite (PTree.get ?i (PTree.remove ?j ?m)).   (* 정상 *)
```

```
coqc   → 1번 질의 출력 후 2번에서 Error, 파일 종료. 3·4·5 실행 안 됨.
coqtop → 2·3·4 에서 각각 Error 를 찍고, 5번을 정상 실행.
           PTree.grs / PTree.gro / PTree.grspec
```

`scripts/coq_search_eval.py` 의 `DRIVER = "coqtop"` 한 줄이다.

---

## 5. 실측 — 판본별 gold 복원율

CompCert · rand200 · `apply`/`rewrite` 지점.

| 판본 | 바뀐 것 | 질의지점 | **gold 복원** |
|---|---|---|---|
| v3 | 최초 (`?x` 없음) | 256 | 51.6% |
| v5 | `?x` + 사다리 | 252 | 60.3% |
| v8 | 스코프 보존 (`%R` 를 안 벗김) | 242 | 74.0% |
| w4 | 전방추론(`-> ?zfwd`) + 가설안 | 252 | 86.5% |
| w5/w6 | elaborate 기호 + 넓게 | 248 | 87.9% |
| w7 | `match` 오인 수정 · 괄호없는 부분항 | 245 | 88.2% |
| **w8** | **드라이버 `coqtop`** | **347** | **96.5%** (apply 96.2% · rewrite 97.1%) |

w7→w8 에서 **질의지점이 245→347 로 늘어난 것**이 핵심이다. 이전 판본들의 재현율은
"살아남은 지점" 위에서만 잰 값이라 **낙관 편향**이 있었다. 같은 분모(347)로 다시 쓰면:

```
w6/w7   218/347 = 62.8%       ← 죽은 지점을 미검출로 세면
w8      335/347 = 96.5%
```

죽은 지점 99개는 "후보 0개"였으므로 실제 파이프라인에서도 미검출이다. 즉
**드라이버 교체 한 줄이 +33.7pp** 다. 질의 생성 개선 전부(v3→w7, +36.6pp)에
맞먹는다.

### 남은 12건 (3.5%)

| 이유 | 수 |
|---|---|
| L7 까지 가도 안 나옴 (질의 부족) | 대부분 |
| 지점 자체가 죽음 (L6·L7 에서 345·343) | 2~4 |

### 5.1 왜 `?x` 인가 — 전칭 변수 vs 경직 상수

`_` 는 익명 홀이라 여러 번 써도 서로 **다른** 것이 될 수 있다. `?x` 는 이름이 붙어
같은 이름이면 같은 것이어야 한다. `f ?a ?b = f ?a ?b` 와 `f _ _ = f _ _` 는 다르다.

### 5.2 함정 — `match` 를 적용으로 오인

`_args_of` 가 공백으로 쪼개서:

```
SearchPattern ((match ?a0 ?a1 ?a2 … ?a14) = (match ?b0 … ?b14)).
```

`match` 는 `with` 가 있어야 하므로 **파스 오류**다. `_NOTAPP` 로
`match|if|let|fun|forall|exists|fix|cofix` 를 걸러 고쳤다.

### 5.3 함정 — 괄호 없는 적용을 통째로 놓침

`rewrite_targets` 가 `(` … `)` 만 모았다. §3.3 의 진짜 redex 인

```
PTree.get i (PTree.set j x (snd m))
```

은 괄호가 안 쳐져 있어 **한 번도 질의가 되지 않았다.** gold 이 바로 그 좌변인데도.
`app_subterms()` 를 새로 넣어 깊이 0 의 최대 적용 런을 뽑는다:

```
app_subterms(goal) →
   PTree.get i (PTree.set j x (snd m))    ← 새로 잡히는 것
   PTree.set j x (snd m)
   PTree.get i (snd m)                    ← 새로 잡히는 것
   Some x0
```

### 5.4 함정 — 질의 하나가 뜻을 바꾼다

| 잘못 | 왜 |
|---|---|
| `(0 <= ?x)%R` → `Nat.le 0 ?x` | 스코프 `%R` 를 벗기면 **다른 명제**가 된다 (+7.2pp) |
| `Int.testbit` → `Int` + `testbit` | 정규화 이름을 점에서 쪼개면 안 된다 |
| `m |= P` 의 `|=` 를 `=` 로 분해 | 중위 연산자 경계 검사 필요 |
| `forall ?x, …` / `fun ?x =>` | goal **안쪽 바인더**는 절대 추상화하면 안 된다 |
| `eapply L in *` | apply 계열에 `in *` 는 **문법 오류** (`in H` 는 유효) |

### 5.5 함정 — 파일 위치

`Maps.v` 에는 `Theorem gso` 가 **셋**(PTree 376 · PMap 1266 · 1498) 있다. 정리 본문을
텍스트로 찾으면 첫 번째에 걸리고, 거기는 `Module PTree` **안**이라 `PTree.gso` 가
아직 존재하지 않는다. CoqStoq 의 `theorem_start_pos.line` 을 쓴다. 실측 199 중 1건.

---

## 6. 비용

| | 지점당 |
|---|---|
| 전체 질의(57개) | 2.0s |
| **경제판(8질의)** | **0.28s** · 복원 78.6% |
| tf-idf 랭킹 (후보 5,000) | 0.06s |

병목은 tf-idf 가 아니라 **Coq 질의**다. 노드 예산 300ms 안에 넣으려면 8질의판이다.

---

## 7. 결과 요약

```
gold 복원율   62.8%  →  96.5%      (같은 분모 347 지점)
   · apply    96.2%
   · rewrite  97.1%
후보 수       5,973개/지점          (우주 ~20,000 대비 3.3배 축소)
```

재현율은 사실상 풀렸다. **남은 문제는 축소율**이다 — 5,973개는 프롬프트에
싣기에 너무 많다. 그래서 다음 단계가 두 개다:

1. **커널 검증** — `assert_succeeds` 로 실제 적용 가능한 것만 (후보당 0.11ms).
   [applicability-filter.md](applicability-filter.md) §4.17.
2. **필터 후 랭킹** — 좁아진 모집단에 같은 tf-idf 를 다시 매긴다.
   실측 @10 42.4%→60.9%, @100 56.1%→82.0%.

---

## 8. 재현

```bash
# 전사 하나 뜨기 (goal → 질의 → 실제 Coq 출력)
python3 scripts/search_demo.py 472 5
python3 scripts/search_demo.py 282 2
python3 scripts/search_demo.py 1088 18

# 전체 측정
CS_N=200 CS_JOBS=4 CS_LEVELS=3 CS_RWN=4 CS_WIDE=1 CS_WIDEN=8 CS_FWD=1 \
CS_OUT=all_log/coq_search_w8.jsonl python3 scripts/coq_search_eval.py

# 어느 질의가 파일을 죽였나
python3 scripts/killer_query.py
```
