# 절차 — 입력에서 출력까지

> r1~r11 을 관통하는 **개괄**이다. 판본마다 달라지는 것은 [../versions/](../versions/README.md).
>
> **r11 기준 정정 두 가지** (아래 본문은 6채널 시절 서술이 남아 있다):
> - 채널이 **넷**이다 — `ap · in · rw · rwh`. `uf`·`ds`·`dc` 는 뺐다
>   (`ds` 단독기여 0 · `dc` 단독기여 0 · `uf` 는 검색이 아님).
>   `ApplicWideChannels 1` 로 되살린다. → [../versions/r11.md](../versions/r11.md)
> - 정렬은 **채널 안에서** 한다. 한 줄로 합치면 `rw`(268개)가 `ap`(334)+`in`(618)에
>   묻혀 rewrite @10 이 75.4% → 38.6% 로 무너진다. → [../results/r11.md](../results/r11.md)
> 여기서는 "무엇이 들어가 무엇이 나오는가" 와 "그 사이에 무슨 일이 일어나는가" 를 적는다.

---

## 0. 한 장 요약

```
입력   증명 상태 하나 (goal + 가설)  +  살아있는 Coq 환경
  │
  ├─[A] 색인 구축      환경의 모든 상수·귀납형 → 판별트리 3개      (파일당 1회, ~0.8s)
  │
  ├─[B] 후보 생성      4채널(r11). 트리 조회 또는 선형 훑기        (상한)
  │
  ├─[C] 판정           커널 단일화                                (정확)
  │
  ├─[D] 신호           lgg · lcp · evar · redex 크기 …
  │
  ├─[E] 랭킹           나이브 베이즈 (비트)
  │
  └─[F] 배분           채널별 물채우기 → 프롬프트 슬롯
  │
출력   순서 있는 premise 목록 + 신호
```

핵심 원칙 두 개:

1. **상한 → 판정.** 빠른 구조(트리)가 과대근사하고, 정확한 것(커널)이 결정한다.
   순서를 바꾸면 건전성이 깨진다.
2. **채널은 tactic 규칙에서 유도한다.** 발명하지 않는다.

---

## 1. 입력

### 1.1 무엇이 필요한가

| | 예 |
|---|---|
| goal (결론) | `PTree.get i (PTree.set j x m) = PTree.get i m` |
| 가설 | `A : Type` · `i j : positive` · `x : A` · `m : t A` · `H : i <> j` |
| Coq 환경 | 그 파일이 `Require` 한 것이 전부 로드된 상태 |

**환경이 살아 있어야 한다.** 텍스트만으로는 안 된다 — 판정이 커널 단일화이기 때문이다.
그래서 저장소가 컴파일(`.vo`)돼 있어야 한다.

### 1.2 실제 진입점

```coq
Require Import Applic.
Lemma foo : … .
Proof.
  intros A i j x m H.
  applic_filter.          ← 여기서 절차가 돈다
```

---

## 2. [A] 색인 구축 — 파일당 한 번

```
for each c in Environ.fold_constants ∪ fold_inductives:
    ty ← Retyping.get_type_of (fresh_global c)      # 완전히 elaborate 된 타입
    if too_big ty: skip                             # 4000 노드 초과는 건너뛴다
    d ← 0
    loop:
        parts ← concl_parts(ty_d)                   # /\ · <-> 로 분해
        for p in parts:  dn_apply.add(pattern p, (c, d))
        if ty_d 가 관계면:  dn_rw.add(좌변/우변 패턴, (c, d*2+변))
        if ty_d 의 전제가 비의존:  dn_prem.add(pattern, (c, d))
        if ty_d 가 Prod:  ty_{d+1} ← subst(new_evar, body); d ← d+1
        else: break
```

<details><summary><b>기호 설명</b></summary>

| 기호 | 뜻 |
|---|---|
| `c` | 후보 하나. 상수(`Constant.t`)·귀납형·생성자 중 하나 |
| `ty` | `c` 의 **타입**. `PTree.gso` 라면 `forall (A)(i j)(x)(m), i<>j -> …` 전체 |
| **`ty_d`** | `ty` 에서 **바인더를 d개 벗긴 것**. `ty_0 = ty`, `ty_1` 은 `forall A` 를 벗긴 것 … |
| `d` | 벗긴 개수 = **깊이**. `max_arrows`(=20) 까지 |
| `parts` | `ty_d` 를 `/\`·`<->` 로 쪼갠 조각들. `A /\ B` 면 `[A/\B, A, B]` |
| `pattern p` | `p` 를 판별트리 키로 바꾼 것 (`DN.constr_pattern`) |
| `dn_apply` | 결론 색인. 키 = `(후보번호, 깊이)` |
| `dn_rw` | rewrite 색인. 키 = `(후보번호, 깊이*2 + 변)`. 변 0=좌변 1=우변 |
| `dn_prem` | 전제 색인. `apply L in H` 용 |
| **관계** | 결론이 `eq`·`iff` 이거나 `Rewrite.is_applied_rewrite_relation` 이 인정하는 것 |
| **비의존 전제** | `Prod(_, a, b)` 에서 `b` 가 그 바인더를 안 쓰는 것 = 진짜 화살표 `a -> b` |
| `new_evar` | 미지수. 바인더를 벗길 때 그 자리에 넣는다 — `eapply` 가 하는 일 |
| `subst` | `body` 안의 그 바인더 자리를 evar 로 치환 |

</details>

**코드**: [`applic_main.ml:215` `index_cand`](../../../../ocaml/applic/applic_main.ml) ·
[`:260` `build_index`](../../../../ocaml/applic/applic_main.ml)

**출력**: 판별트리 3개 + 후보 배열 + 선언 타입 배열

```
cand=12,652   pat=87,139   build=0.83s
```

`TransparentState` 는 `Some empty`(경직)다. `None`(전부 투명)이면 트리가 가름을
포기해 40배 느려진다 → [../concepts/limits.md](../concepts/limits.md)

## 3. [B]+[C] 채널별 후보 생성과 판정

> **`applic_filter` 한 번이 채널을 전부 돈다.**
> r11 기본은 **넷** — apply · apply…in · rewrite(goal) · rewrite(가설).
> `ApplicWideChannels 1` 을 켜면 unfold · destruct · decide 셋이 더 나온다.
> 구현: [`applic.mlg:8`](../../../../ocaml/applic/applic.mlg) → [`applic_main.ml:980` `filter_tac`](../../../../ocaml/applic/applic_main.ml)
> → 계산은 [`:718` `compute`](../../../../ocaml/applic/applic_main.ml) 가 다 한다.

### 3.1 apply

```
for i, c in 후보배열:
    if not suffix_compat(선언타입[i], goal): continue      # ① 값싼 선별
    ty ← 타입(c)                                            # ② 캐시된 elaborate 타입
    for d in 0 .. max_arrows:                               # ③ 화살표 접미사마다
        (sg, t) ← descend(ty, d)                            #    바인더를 evar 로
        for p in concl_parts(t):                            #    /\ · <-> 분해
            if unify_ap(p, goal): 통과 → 신호 기록; break    # ④ 커널 단일화
```

<details><summary><b>기호 설명</b></summary>

| 기호 | 뜻 |
|---|---|
| `후보배열` | `build_index` 가 만든 `idx.cands`. 상수·귀납형·생성자 12,652개 |
| `선언타입[i]` | `idx.rawty[i]`. **elaborate 전** 선언 타입. 값싼 선별용 |
| `suffix_depths` | 머리 **라벨**만 비교해 **맞는 깊이 목록**을 돌려준다. 12,652 → 5,821 |

> ★ r11 에서 `suffix_compat`(bool) → `suffix_depths`(깊이 목록)로 바꿨다.
> 예전엔 "어느 한 깊이라도 맞나" 만 보고 통과시킨 뒤 `depth_of` 가
> **깊이 0~20 을 전부 커널 단일화**했다. 맞는 깊이만 시도하게 하니
> 0.45 → 0.39초 (−14%), 채널 수치는 완전 동일.
| `goal` | 지금 증명 상태의 결론 (`Proofview.Goal.concl`) |
| `타입(c)` | `fresh_global` + `get_type_of`. 지점마다 캐시한다 (`cand_type_i`) |
| `(sg, t)` | `sg` = evar 가 추가된 **새 sigma**, `t` = d개 벗긴 결론. **sg 를 계속 들고 가야** 한다 |
| `unify_ap` | `w_unify ~flags:(elim_flags ())` — `apply`/`eapply` 와 같은 플래그 |
| `신호` | `lgg` · `lcp` · `e`(=d, 벗긴 개수) |

</details>

**코드**: [`:742` `try_apply`](../../../../ocaml/applic/applic_main.ml) ·
[`:388` `unifies_upto`](../../../../ocaml/applic/applic_main.ml) ·
[`:460` `suffix_compat`](../../../../ocaml/applic/applic_main.ml)

- **트리를 안 쓴다.** 경직 트리로 좁히면 delta 변환이 필요한 매칭을 놓쳐
  적중이 78.2% → 37.3% 로 반토막 났다(실측).

### 3.2 rewrite

```
redexes ← goal 과 모든 가설 타입의 부분항 중
             경직 머리 ∧ 닫힘 ∧ 중복 제거
for st in redexes:
    for (i, tag) in dn_rw.lookup(st):                       # ① 트리로 상한
        (sg, t) ← descend(타입(i), tag/2)
        (l, r)  ← rw_sides(t)
        d ← (tag mod 2 = 0) ? l : r
        if same_head(d, st) ∧ unify1(d, st)                 # ② keyed + 커널
           ∧ abstract_ok(goal, st):                         # ③ 추상이 타입이 맞나
            통과 → 신호(z, lcp, nm, ing) 기록
```

<details><summary><b>기호 설명</b></summary>

| 기호 | 뜻 |
|---|---|
| **`redex`** | 치환될 자리. `rewrite L` 이 goal 안에서 바꿔치기할 부분항 |
| **경직 머리** | 머리가 `Const`·`Ind`·`Construct`·`Var`. `Rel`·`Evar`·`Sort` 는 뺀다 |
| **닫힘** | 자유 de Bruijn 인덱스가 없다 (`Vars.closed0`). 바인더 아래 항은 바깥에서 뜻이 없다 |
| `st` | subterm. 지금 보고 있는 redex 후보 |
| `tag` | rw 색인의 키 뒷부분. `깊이*2 + 변`. `tag/2`=깊이, `tag mod 2`=좌0/우1 |
| `(l, r)` | 그 깊이의 결론이 `a = b` 면 `l=a`, `r=b` |
| **`same_head`** | **keyed matching**. Coq 8.5+ 의 `rewrite` 는 redex 머리가 delta 없이 맞아야 한다 |
| `unify1` | 기본 플래그 `w_unify`. apply 와 달리 `elim_flags` 를 안 쓴다 |
| **`abstract_ok`** | `λx.C[x]` 를 만들어 타입검사. redex 가 의존 자리면 `rewrite` 가 실패한다 |
| `z`·`nm`·`ing` | redex 크기 · 맞은 redex 개수 · goal 안인가(가설 아니라) |

</details>

**코드**: [`:848` redex 고르기](../../../../ocaml/applic/applic_main.ml) ·
[`:868` `side_matches`](../../../../ocaml/applic/applic_main.ml) ·
[`:532` `abstract_ok`](../../../../ocaml/applic/applic_main.ml) ·
[`:129` `rw_sides`](../../../../ocaml/applic/applic_main.ml) ·
[`:364` `dig_sides`](../../../../ocaml/applic/applic_main.ml) (지역 가설용)

### 3.3 apply … in H

```
prop_hyps ← 가설 중 타입이 Prop 인 것
for h in prop_hyps:
    for (i, d) in dn_prem.lookup(h):
        (sg, t) ← descend(타입(i), d)
        if t 가 Prod (_, a, _) ∧ unify_ap(a, h): 통과
```

<details><summary><b>기호 설명</b></summary>

| 기호 | 뜻 |
|---|---|
| `prop_hyps` | `Retyping.get_sort_of` 가 `Prop` 인 가설만. `A : Type`·`i : positive` 는 제외 |
| `h` | 그 가설의 **타입** (명제) |
| `Prod (_, a, _)` | `a -> …` 의 `a`. 그 깊이의 **전제** |
| 왜 `Prop` 제한 | 없으면 데이터 가설로 조회해 그 타입을 받는 lemma 가 전부 나온다. 실측 **4,820** 폭발 |

</details>

**코드**: [`:805` `prop_hyps`](../../../../ocaml/applic/applic_main.ml) ·
[`:479` `is_prop`](../../../../ocaml/applic/applic_main.ml)

### 3.4 unfold · destruct · decide — goal 만 보면 결정된다

> ⚠ **r11 에서 기본 꺼짐.** `ApplicWideChannels 1` 로만 나온다.

```
unfold    goal·가설의 상수 중 const_body = Def _        →  4~7개
destruct  닫힌 부분항의 타입 머리가 Ind                  →  ~3개
decide    결론이 귀납형이고, 그 인자가 goal 부분항과 unify1 →  ~91개
```

<details><summary><b>기호 설명</b></summary>

| 기호 | 뜻 |
|---|---|
| `const_body = Def _` | **본체가 있다** = δ-환원 가능 = `unfold` 할 수 있다. `Undef`(공리)·`OpaqueDef` 는 못 편다 |
| `타입 머리가 Ind` | 그 항의 타입이 귀납형 = `destruct` 할 수 있다 |
| `decide` 의 `unify1` | r9 에서 조인 부분. 머리만 겹치면 통과시키던 것을 **실제 단일화**로 바꿨다 (490 → 91) |

</details>

**코드**: [`:561` `unfold_cands`](../../../../ocaml/applic/applic_main.ml) ·
[`:575` `destruct_cands`](../../../../ocaml/applic/applic_main.ml) ·
[`:612` `decide_cands`](../../../../ocaml/applic/applic_main.ml)

앞의 둘은 **추측이 없다.** 그래서 후보가 한 자릿수다.

## 4. [D] 신호

통과한 후보마다 붙인다.

| 신호 | 계산 | 뜻 |
|---|---|---|
| `lgg` | `lgg_size(goal, 결론)` | 포섭 격자의 meet 크기 |
| `lcp` | `lcp(preorder goal, preorder 결론)` | 트라이에서 갈라지는 깊이 |
| `e` | 맞을 때까지 벗긴 바인더 수 | `eapply` 가 찍어야 할 인자 수 |
| `z` | `term_size(맞은 redex)` | rewrite 가 건드리는 크기 |
| `nm` | 맞은 redex 개수 | 적을수록 특정적 |
| `ing` | redex 가 goal 안인가 | `rewrite L` 이 기본형 |
| `occ` | 상수가 goal 에 몇 번 | unfold 용 |
| `g` | `term_size(goal)` | 정규화 분모 |

---

## 5. 출력

```
APPLIC PTree.gso lgg=15 e=6 lcp=15 g=20 :: (forall (A:Type) (i j:positive) …)
APPLICIN <이름> lgg= e= lcp= g= :: …
DNRW   PTree.gso z=5 d=6 lcp=4 nm=1 ing=1 g=20 :: …
UNFOLD PTree.set occ=2 z=6 g=20 :: …
DESTRUCT PTree.tree
DECIDE Nat.zero_one lgg=4 lcp=1 g=20 :: …
HYPS   H m x j i A                      ← 지역 가설 이름
GBIND  l n                              ← goal 바인더 이름
APPLIC_STAT ver=r9 cand=12652 pat=87139 build=0.83 hyps=6 redex=20
            raw=34461 keypass=5821 apply=349 applyin=456 rewrite=310
            unfold=4 destruct=3 decide=91 sec=0.47
```

- `HYPS`·`GBIND` 는 **평가용**이다. `destruct l` 의 `l` 은 지역 변수라 검색 대상이 아니다.
  이걸 안 내보내면 미검출로 잘못 세어 재현율이 12pp 낮게 나온다(실측).
- `::` 뒤 진술문은 `ApplicPrintTypes 1` 일 때만 나온다. 랭킹에 바로 쓴다.

---

## 6. [E] 랭킹 — 파이썬 쪽

```
말뭉치 전체에서:
    idf[L] ← −log P(L 이 필터를 통과)               # applic-idf
    특징 구간화: lcp/g · lgg/g · e · z/g · nm · idf · 채널 · lex · nov · std
    w[f] ← log₂ P(f|gold) / P(f|¬gold)              # 나이브 베이즈 (5겹 교차검증)

지점마다:
    score(L) ← Σ_f w[f(L)]
    채널별로 자기 순위를 매긴다
```

<details><summary><b>기호 설명</b></summary>

| 기호 | 뜻 |
|---|---|
| `L` | 후보 lemma 하나 |
| **`idf[L]`** | **applic-idf**. `L` 이 몇 %의 지점에서 필터를 통과하나. 어디서나 통과하면 0비트 |
| `f` | **특징** 하나. `("lcp", 4)` 처럼 (이름, 구간번호) 쌍 |
| **구간화** | 연속값을 몇 칸으로 나눈다. `lcp/g` 를 `<0.05, <0.15, <0.3, <0.5, <0.75, 그 이상` 6칸 |
| `g` | goal 크기(노드 수). 나누어 정규화한다 |
| `lex` | 진술문과 goal 의 **토큰** 겹침 (idf 가중) |
| `nov` | **이름** 어휘 겹침. `repr_canonical` ↔ goal 의 `repr_*` |
| `std` | stdlib 인가 (이름 접두사로 판정) |
| `w[f]` | 그 특징의 **로그 가능도비**. gold 에서 얼마나 더 자주 나오나 |
| **5겹 교차검증** | 정리를 5조각으로 나눠, 한 조각을 빼고 학습해 그 조각만 채점. 과적합 방지 |

</details>

**코드**: [`scripts/applic_rank.py`](../../../../scripts/applic_rank.py) —
`build_idf` · `feats` · `train_nb` · `nb_score_fn` · `lex_overlap` · `_name_toks`

## 7. [F] 배분 — 물채우기

```
b ← {채널: 0}
K 번 반복:
    각 채널의 한계이득  Δ_c = p_c × [F_c(b_c+1) − F_c(b_c)]
    가장 큰 채널에 한 칸
채널을 번갈아 가며 b_c 개씩 뽑아 하나의 목록으로
```

<details><summary><b>기호 설명</b></summary>

| 기호 | 뜻 |
|---|---|
| `K` | 프롬프트에 실을 premise 개수 (토큰 예산이 정한다) |
| `b_c` | 채널 `c` 에 준 슬롯 수 |
| **`p_c`** | 그 채널에 해당하는 tactic 이 나올 **사전확률**. apply 0.32 · rewrite 0.22 … |
| **`F_c(b)`** | 채널 `c` 에서 **상위 b개 안에 gold 이 있을 확률**. 실측 CDF(@10/@20/@50/@100)를 로그 보간 |
| **`Δ_c`** | **한계이득**. 한 칸 더 줬을 때 목표가 오르는 양 |
| 왜 번갈아 뽑나 | 앞쪽이 토큰 절단에서 살아남는다. 한 채널을 몰아 넣으면 뒤 채널이 잘린다 |

</details>

**코드**: [`scripts/channel_budget.py`](../../../../scripts/channel_budget.py) (배분 계산) ·
[`scripts/inject_wf.py`](../../../../scripts/inject_wf.py) — `waterfill` · `pick`

합쳐서 정렬하면 `unfold`(4~7개)이 슬롯 0칸을 받는다.
E[gold 프롬프트에 실림] **58.0% → 69.5%**.

## 8. 실행 예시 — 처음부터 끝까지

**입력**
```coq
Lemma probe : forall (A: Type) (i j: positive) (x: A) (m: PTree.t A),
  i <> j -> PTree.get i (PTree.set j x m) = PTree.get i m.
Proof. intros A i j x m H. applic_filter.
```

**[A] 색인** — 12,652 후보 → 87,139 패턴, 0.83s

**[B]+[C] 채널**

| 채널 | 상한 | 판정 통과 |
|---|---|---|
| apply | 선별 5,821 | **349** |
| apply…in | 트리 조회 | 456 |
| rewrite | redex 20개 × 트리 | 310 |
| unfold | goal 의 상수 | **4** (`PTree.t` · `PTree.set` · `PTree.get` · `not`) |
| destruct | 부분항 타입 | **3** (`PTree.tree` · `positive` · `option`) |
| decide | 귀납형 결론 | 91 |
| **합집합** | | **1,019** — 12,652 대비 **12.4배 축소** |

**[D] 신호**
```
APPLIC PTree.gso lgg=15 e=6 lcp=15 g=20      ← 정답. goal 20칸 중 15칸 공유
APPLIC Ring_polynom.PEeval lgg=1 e=14 lcp=1  ← 적용은 되지만 정보 없음
```

**[E] 랭킹** — `gso` 가 상위. `('e',0)` +12.07bit · `('nov',3)` +8.04bit 등이 작동

**[F] 배분** — K=100 이면 `apply 20 · rewrite 20 · destruct 33 · unfold 10 · …`

**최종 출력** — 순서 있는 premise 목록. `[PREMISES]` 에 그대로 실린다.

---

## 9. 비용

| 단계 | 비용 |
|---|---|
| [A] 색인 | 0.6~1.0s · **파일당 1회** |
| [B]+[C] 채널 | 0.3~0.5s / 지점 |
| [D] 신호 | 위에 포함 |
| [E] 랭킹 | 오프라인 학습 1회 + 지점당 무시 가능 |
| [F] 배분 | 무시 가능 |

노드 예산 300ms 를 넘는다. 색인 재사용과 채널 축소로 줄일 여지가 있다.

---

## 10. 판본별로 달라지는 것

| 단계 | 판본 간 차이 |
|---|---|
| [A] | r2 는 색인 없음(선형만) · r3 부터 트리 · r6 에 `max_arrows` 8→20 |
| [B] | r4 에 지역 가설 · r7 에 unfold/destruct/decide · r9 에 decide 조임 |
| [C] | r5 에 `elim_flags`·keyed · r6 에 결론 분해 |
| [D] | r8 에 신호 전면 도입 |
| [E] | r8 에 나이브 베이즈 |
| [F] | 아직 프롬프트에 배선 안 됨 |

자세한 것은 [../versions/](../versions/README.md).
