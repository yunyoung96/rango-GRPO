# `Btermdn` — Coq 의 판별트리


---

## 0. 이름 — `b` + `term` + `dn`

```
   b        term       dn
   │         │          │
 bounded    term    discrimination net
 (깊이 제한) (항 위에서)  (판별망)
```

- **`dn` = discrimination net (판별망).** 자동정리증명 쪽 오래된 용어다.
  많은 패턴을 트라이에 넣고 **한 번 훑어 후보를 한꺼번에 좁히는** 색인이다.
  OTTER·E·Vampire 가 다 갖고 있고 "discrimination tree" 라고도 부른다.
- **`term`**: 일반 `dn` 은 아무 트리에나 쓰지만 `termdn` 은 **Coq 항** 전용이다.
  항을 라벨로 바꾸는 함수(`constr_val_discr`)가 이 층에 있다.
- **`b` = bounded.** 항은 임의로 깊을 수 있어 색인이 무한정 커진다.
  그래서 `dnet_depth` 층에서 자른다. 파일 머리말이 그대로 그렇게 쓰여 있다:

  ```ocaml
  (* Discrimination nets with bounded depth.
     See the module dn.ml for further explanations.
     Eduardo (5/8/97). *)
  ```

  Eduardo Giménez, 1997년 5월 8일. **30년 가까이 Coq 안에 있던 코드**다.

- 옛 Coq 에는 깊이 제한 없는 `termdn.ml` 도 있었다. 지금은 `btermdn` 만 남았다.

---
> `auto`/`eauto` 의 hint DB 가 쓰는 자료구조. 우리는 그걸 그대로 가져온다.
> 소스: `coq-core/tactics/btermdn.ml` · `dn.ml`

---

## 1. 세 층

```
   Btermdn        항(EConstr) → 라벨 열                 ← constr_val_discr
      │
   Dn (Trie)      라벨 열 → 저장된 값들                  ← lookup / add
      │
   Trie           일반 트라이 (Coq stdlib)
```

- **Btermdn** 은 "항을 어떻게 라벨로 쪼갤까" 만 정한다.
- **Dn** 은 그 라벨 열을 트라이에 넣고 빼는 일반 기계다.

---

## 2. `constr_val_discr` — 항 하나를 라벨로
### 트라이는 어떻게 생겼나 (`clib/trie.ml`)

배열도 해시도 아니다. **노드마다 (데이터 집합 × 라벨→자식 맵)** 이다.

```ocaml
module T_codom = Map.Make(Y)              (* 균형 이진트리 맵 *)
type t = Node of X.t * t T_codom.t
              │        └─ 라벨 → 자식 노드
              └─ 이 노드에 놓인 데이터 집합
```

```
        Node( {}, {c:PTree.get ↦ ●, c:Z.add ↦ ●, None ↦ ●} )
                        │              │           │
                        ●              ●           ●
                Node({}, {…})    Node({},{…})   Node({f_equal, eq_sym}, {})
                                                        ↑
                                            와일드카드 가지 끝에 놓인 데이터
```

- `next t lbl` = 자식 하나 (`Map.find`). **없으면 `Not_found`** → `tm_of` 가 `[]` 로 받는다.
- `get t` = 그 노드의 데이터 집합.
- 데이터는 `Grp` 시그니처(`nil`/`add`/`sub`)로 추상화돼 있고 `Dn` 이 **집합 합/차**를 끼운다.
  같은 경로에 여러 lemma 가 놓이면 **한 노드에 모인다**.

### 라벨의 진짜 타입 — 이름 + **인자 개수**

```ocaml
module Y_tries = struct type t = (Y.t * int) option end
                                 ↑      ↑      ↑
                              라벨   인자수   None = 와일드카드 `*`
```

**인자 개수가 키의 일부다.** `f a b` 와 `f a b c` 는 다른 가지로 간다.
그리고 이 숫자 덕분에 `skip_arg` 가 "부분항 하나를 통째로 건너뛰기" 를 할 수 있다:

```ocaml
let rec skip_arg n tm =
  if n = 0 then [tm]
  else Trie.labels tm |> map (function
    | None        -> skip_arg (n-1) (next tm None)      (* `*` 는 자식 0개 *)
    | Some (_, m) -> skip_arg (n-1+m) (next tm lbl))    (* 자식 m개가 더 생긴다 *)
```

### 전위 순회로 펴는 법 (`path_of`)

재귀가 아니라 **미룬 목록(deferred)** 을 쓴다 — 형제를 뒤로 미루고 첫 자식으로 내려간다.

```ocaml
and pathrec deferred t = match dna t with
  | None            -> None :: path_of_deferred deferred
  | Some (lbl, [])  -> Some(lbl,0) :: path_of_deferred deferred
  | Some (lbl, h::rest) -> Some(lbl, 개수) :: pathrec (rest @ deferred) h
```

```
      f
     / \        전위 순회 열:  [f/2, g/1, a/0, b/0]
    g   b                       │     │     │    │
    │                          머리  첫자식 그자식 미뤄둔 형제
    a
```

---

## 2. `constr_val_discr` — 항 하나를 라벨로

```ocaml
let constr_val_discr env sigma ts t =
  let c, l = decomp sigma t in          (* t = c l₁ l₂ … 로 쪼갠다 *)
  match kind sigma c with
  | Const (c,_)  -> if 펼칠 수 있으면 Everything else Label(GRLabel c, l)
  | Ind  (i,_)   -> Label(GRLabel i, l)
  | Construct k  -> Label(GRLabel k, l)
  | Var id       -> if 펼칠 수 있으면 Everything else Label(GRLabel id, l)
  | Prod (_,d,c) -> Label(ProdLabel, [d; c])      (* ★ Prod 도 라벨이다 *)
  | Sort _       -> Label(SortLabel, [])
  | Evar _       -> Everything
  | Case _       -> Everything                    (* 과대근사 *)
  | Lambda _     -> Nothing 또는 Everything
  | _            -> Nothing
```

### 세 가지 결과

```
Label (라벨, 자식들)   이 자리는 라벨로 가른다.  자식으로 재귀한다
Everything            가름 포기. 트라이의 그 자리 아래를 전부 반환한다
Nothing               막다른 길. 아무것도 안 준다
```

**`Everything` 이 핵심이다.** `evaluable_constant` 이 참이면 — 즉 그 상수를 **펼칠 수
있으면** — 이름으로 가르는 것이 위험하므로 가름을 포기한다.

```ocaml
let evaluable_constant c env ts =
  … (match ts with None -> true | Some ts -> is_transparent_constant ts c)
```

| `ts` | 뜻 | 결과 |
|---|---|---|
| `None` | **전부 펼칠 수 있다** | 모든 상수가 `Everything` → **트리가 거의 안 거름** |
| `Some empty` | 아무것도 못 편다 | 모든 상수가 `Label` → **최대 판별력** |
| `Some {f, g}` | `f`·`g` 만 편다 | 그 둘만 `Everything` |

우리는 `Some empty` 를 쓴다. `None` 으로 하면 실측 raw 29,381 → **518,546**, 0.7s → **28.7s**.

---

## 3. 항이 라벨 열이 되는 과정

```
t = PTree.get i (PTree.set j x m)

  ┌─ decomp ─────────────────────────────┐
  │  머리 = PTree.get                     │
  │  인자 = [ i , PTree.set j x m ]        │
  └───────────────────────────────────────┘
                 │
     Label( GRLabel PTree.get , [i ; PTree.set j x m] )
                 │
        ┌────────┴────────┐
        │                 │
        i                 PTree.set j x m
        │                 │
   Var i → 펼칠수있음?     decomp → 머리 PTree.set, 인자 [j;x;m]
   보통 지역변수라          Label( GRLabel PTree.set , [j;x;m] )
   Everything                       │
                          ┌────┬────┴────┐
                          j    x         m
                          (전부 Everything)

전위 순회 열:
  [ c:PTree.get , * , c:PTree.set , * , * , * ]
                 ↑                 ↑   ↑   ↑
              Everything 은 트라이에서 "아무 가지나" 로 취급된다
```

**`*` 는 문자가 아니라 "가름 포기" 표시다.** 트라이를 내려갈 때 그 자리에서는
모든 가지를 다 따라간다.

---

## 4. `Dn` — 트라이 조회

```ocaml
let lookup tm dna t =
  let rec lookrec t tm = match dna t with
    | Nothing     -> tm_of tm None                    (* 와일드카드 가지만 *)
    | Label(l,v)  -> tm_of tm None                    (* 와일드카드 가지 +   *)
                     @ (v 를 따라 재귀)                (*  그 라벨 가지      *)
    | Everything  -> skip_arg 1 tm                    (* 한 인자 통째로 건너뜀 *)
  in …
```

```
저장된 패턴들 (트라이)                 조회 항
  ┌ c:PTree.get ─ * ─ c:PTree.set …    c:PTree.get
  ├ c:PTree.get ─ * ─ c:PTree.remove …       │
  ├ c:Z.add ─ …                        여기서 두 가지가 살아남고
  └ * (좌변이 변수인 lemma)              Z.add 가지는 죽는다
                                       `*` 가지는 **항상** 살아남는다
```

- **`*` 가지가 항상 살아남는 것**이 `f_equal`·`eq_sym` 같은 보편 lemma 가
  어느 조회에나 나오는 이유다. 그래서 **applic-idf** 가 그걸 눌러야 한다.
- 반환값은 **상한**이다. 실제 적용 여부는 커널이 정한다.

---

## 5. `dnet_depth` — 몇 층까지 가를까

```ocaml
let dnet_depth = ref 8          (* Coq 기본값 *)
Dn.pattern mk (pat, !dnet_depth)
Dn.lookup dn ... (t, !dnet_depth)
```

깊이를 넘어가면 그 아래는 안 본다.

```
depth=1   [ c:PTree.get ]                     머리만
depth=2   [ c:PTree.get , * , c:PTree.set ]   머리 + 1층
depth=3   … 인자의 인자까지
```

**우리는 2 로 쓰고 있다.** Coq 기본은 8이다. 실측해 보니 **2로 충분하다.**

### 실측 — CompCert, 같은 goal 에서 깊이만 바꿈

```
  깊이   pat      raw      keypass   apply  applyin  rewrite  rewriteh   build
 ─────  ───────  ───────  ────────  ─────  ───────  ───────  ────────  ──────
   2    87,139   34,461     5,821    349     456      268      147     1.130s
   4    87,139   33,886     5,821    349     456      268      147     1.333s
   8    87,139   33,886     5,821    349     456      268      147     1.433s
        └─동일─┘  └─1.7%─┘  └─동일─┘  └────────── 전부 동일 ──────────┘  └─더 느림─┘
```

`gold PTree.gso` 는 깊이 2·8 양쪽에서 `ap=1 in=1 rw=1` 로 살아남는다.

**깊이 4 와 8 은 완전히 같다.** 이유는 [tree-shape.md](tree-shape.md) 의 그림 그대로다 —
우리가 색인하는 것은 결론과 등식 양변인데, **2층 아래는 거의 전부 `*`(evar·변수)** 라
더 내려가도 가를 것이 없다. 최종 채널 크기는 한 개도 안 변한다.

```
   [ get/2 , * , set/3 , * , * , * ]
     └─2층까지가 판별력 전부─┘ └── 이 아래는 전부 와일드카드 ──┘
```

→ 깊이를 올리면 **빌드만 27% 느려지고 얻는 게 없다.** 2가 맞다.

---

## 6. 우리가 쓰는 법

```ocaml
module Key = struct type t = int * int  …  end     (* (후보번호, 깊이·변) *)
module DN = Btermdn.Make (Key)

DN.constr_pattern env sigma ts t     (* 항 → 패턴 *)
DN.add idx pattern (id, tag)         (* 색인에 넣기 *)
DN.lookup env sigma ts idx term      (* 조회 — 상한 *)
```

색인 셋을 만든다:

```
dn_apply   결론(과 /\·<-> 분해분)  →  (후보, 깊이)
dn_prem    비의존 전제              →  (후보, 깊이)
dn_rw      등식 좌·우변             →  (후보, 깊이*2+변)
```


### 우리는 Coq 을 고치지 않았다

```
Coq 것 (호출만)                       우리 것 (새로 씀)
──────────────────────────────    ──────────────────────────────
Trie          자료구조             Key           트리에 넣을 값의 타입
Dn            add / lookup        dn_apply/prem/rw  세 색인 셋
Btermdn       constr_val_discr    index_cand    무엇을 넣을지
dnet_depth    깊이 손잡이          6채널 조회     무엇을 뺄지
```

`btermdn.ml`·`dn.ml`·`trie.ml` 은 **한 줄도 안 고쳤다.**
자세히는 [../code/plugin.md](../code/plugin.md) §0.

**코드**: [`applic_main.ml:61` `module DN`](../../../../ocaml/applic/applic_main.ml) ·
[`:215` `index_cand`](../../../../ocaml/applic/applic_main.ml) ·
[`:72` `ts ()`](../../../../ocaml/applic/applic_main.ml)

---

## 7. 왜 이걸 쓰는가

| | |
|---|---|
| **커널 항 위에서 돈다** | elaboration·notation·암묵인자가 이미 해소돼 있다. 파이썬 8판본이 못 넘던 벽이 여기서 사라진다 |
| **Coq 이 검증했다** | `auto`/`eauto` 가 매일 쓰는 코드다 |
| **거리도 준다** | 같은 트라이가 Baire 초거리를 준다 → [baire.md](baire.md) |

한계는 [limits.md](limits.md) — 색인은 구문적이고 적용가능성은 의미적이다.
