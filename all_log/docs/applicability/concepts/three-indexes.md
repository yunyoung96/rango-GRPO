# 세 트리 — A · P · R

> lemma 하나를 **세 군데**에 나눠 넣는다. 채널이 넷인데 트리가 셋인 이유도 여기 있다.
> 코드: `applic_main.ml` — `index_cand`(237) · `add_pat`(197)

---

## 0. 왜 하나가 아닌가

`apply` · `apply…in` · `rewrite` 는 **lemma 의 서로 다른 부위**를 본다.

```coq
PTree.gso : forall (A:Type) (i j:positive) (x:A) (m:tree A),
              i <> j  ->  PTree.get i (PTree.set j x m) = PTree.get i m
              └──┬──┘     └──────────────┬──────────────────────────┘
              전제                       결론
                                    └────┬────┘   └───┬───┘
                                        좌변          우변
```

| 트리 | 넣는 부위 | 쓰는 tactic |
|---|---|---|
| **A** | 결론 | `apply` |
| **P** | 비의존 전제 | `apply … in` |
| **R** | 관계의 좌·우변 | `rewrite` / `rewrite … in` |

한 트리에 다 넣으면 조회할 때 **어느 부위로 맞았는지 알 수 없다.**

```ocaml
let add_pat which p key = match which with
  | `A -> idx.apply <- DN.add idx.apply p key
  | `P -> idx.prem  <- DN.add idx.prem  p key
  | `R -> idx.rw    <- DN.add idx.rw    p key
```

---

## 1. 공통 뼈대 — Π 를 벗기며 내려간다

세 트리 모두 **같은 하강**에서 채워진다. 전제를 evar 로 하나씩 채우며 깊이를 센다.

```
   깊이 0 :  forall A i j x m, i<>j -> get i (set j x m) = get i m
   깊이 1 :  forall i j x m,   i<>j -> …          (A 를 evar 로)
   깊이 2 :  forall j x m,     i<>j -> …
   깊이 3 :  forall x m,       i<>j -> …
   깊이 4 :  forall m,         i<>j -> …
   깊이 5 :  i<>j -> get i (set j x m) = get i m
   깊이 6 :  get i (set j x m) = get i m           ← 진짜 결론
```

**깊이마다 세 트리에 다 넣는다.** `apply` 가 몇 개를 벗겨서 쓸지 미리 모르기 때문이다.
`max_arrows`(=20)까지 내려간다 → [pi-binder.md](pi-binder.md)

```ocaml
let rec go n sigma t =
  … A 넣기 … R 넣기 … P 넣기 …
  match EConstr.kind sigma t with
  | Constr.Prod (_, a, b) ->
      let (sigma, ev) = Evarutil.new_evar env sigma a in
      go (n + 1) sigma (EConstr.Vars.subst1 ev b)      (* 벗기고 재귀 *)
```

접미사마다 새로 만들지 않으므로 **evar 는 바인더 수만큼만** 생긴다.

---

## 2. A 트리 — 결론

```ocaml
List.iter (fun part -> add_pat `A (pat part) (id, n))
  (concl_parts sigma t);
```

- **키**: `(후보번호, 깊이)`
- **질의**: goal 의 결론
- **술어**: `∃d ≤ max_arrows. unify(concl_d(L), goal)`

### `concl_parts` — `∧` 와 `↔` 를 뚫는다

```ocaml
let rec concl_parts sigma t =
  … if nm = "and" || nm = "iff" then
      t :: (concl_parts args.(n-2) @ concl_parts args.(n-1))
    else [t]
```

```
   L : A <-> B
        │
   ┌────┼────┐
   L 전체   A     B          ← 셋 다 A 트리에 넣는다
```

`apply L`·`apply <- L` 이 `A` 나 `B` 하나만 맞춰도 통하기 때문이다.

> ★ **`iff` 는 귀납형이 아니라 `Definition`** 이다 (`iff A B := (A->B)/\(B->A)`).
> `Ind` 만 보다가 `apply Liff` 를 통째로 놓쳤다. → [../terminology/prod.md](../terminology/prod.md)

### ★ 지금 apply 는 이 트리를 **안 쓴다**

```ocaml
let apply_dn = ref false        (* 기본값 *)

if not !apply_dn then
  Array.iteri (fun i c ->
     if suffix_compat sigma (rawty i) concl then (incr keypass; try_apply i c))
    idx.cands                                   (* ← 선형 훑기 *)
else … (lookup idx.apply concl)
```

경직 트리로 좁혔더니 **apply 적중이 78.2% → 37.3% 로 반토막**났다.
`apply` 는 delta 를 허용하는데 트리는 구문적이라서다.
그래서 `suffix_compat`(값싼 머리-라벨 비교)로 12,652 → 4,812 만 걸러 낸 뒤 선형으로 돈다.
`ApplicApplyDN 1` 로 트리 경로를 켤 수 있다. → [limits.md](limits.md)

---

## 3. P 트리 — 비의존 전제

```ocaml
if EConstr.Vars.noccurn sigma 1 b then          (* b 가 그 바인더를 안 쓰나 *)
  add_pat `P (pat a) (id, n);
```

- **키**: `(후보번호, 깊이)`
- **질의**: **각 명제 가설**의 타입 (가설 6개면 조회 6번)
- **술어**: `∃H, d. unify(전제_d(L), type(H))`

### `noccurn` 이 핵심이다

Coq 매뉴얼: `apply L in H` 는 **비의존** 전제를 오른쪽부터 맞춘다.

```
   PTree.gso 의 Prod 들
   ─────────────────────────────
   forall A : Type    의존   ✗   ← 첫 Prod 이지만 전제가 아니다
   forall i           의존   ✗
   forall j           의존   ✗
   forall x           의존   ✗
   forall m           의존   ✗
   i <> j ->          비의존 ✓   ← P 트리에 들어가는 건 이것뿐
```

**첫 `Prod` 만 보면 `A : Type` 을 전제로 착각한다.** 실측으로 걸렸다.
→ [../terminology/noccurn.md](../terminology/noccurn.md) · [../versions/r4.md](../versions/r4.md)

### 조회는 가설마다

```ocaml
let prop_hyps = List.filter (fun (_, ty) -> is_prop env sigma ty) hyps in
List.iter (fun (_, hty) ->
    List.iter (fun (i, d) -> … unify_ap env sg a hty …)
      (lookup idx.prem hty))          (* ← 가설 하나당 lookup 1회 *)
  prop_hyps;
```

`is_prop` 로 **명제인 가설만** 본다. `n : nat` 같은 데이터 가설은 대상이 아니다.

---

## 4. R 트리 — 관계의 좌·우변

```ocaml
match rw_sides env sigma t with
| Some (l, r) ->
    List.iteri (fun i d -> add_pat `R (pat d) (id, n * 2 + i)) [l; r]
| None -> ()
```

- **키**: `(후보번호, 깊이*2 + 변)` — `변` 은 0=좌, 1=우
- **질의**: goal·가설의 **닫힌 부분항** 전부
- **술어**: `∃t, 변. same_head ∧ unify ∧ abstract_ok`

### 왜 태그에 `*2+i` 를 넣나

조회가 맞았을 때 **좌변이었는지 우변이었는지** 복원해야 하기 때문이다.
그래야 `descend` 를 몇 단 할지(`tag / 2`)와 어느 변인지(`tag mod 2`)를 안다.

```ocaml
match descend env sg ty (tag / 2) with
| Some (sg, t) -> match rw_sides env sg t with
    | Some (l, r) -> let d = if tag mod 2 = 0 then l else r in …
```

**이 하나로 `rewrite ->` 와 `rewrite <-` 를 다 덮는다.** 채널을 더 안 만들어도 된다.

```coq
Lonly_l : z + 0 = z * 1     goal 에 z+0  →  rewrite Lonly_l     OK
Lonly_r : z * 1 = z + 0     goal 에 z+0  →  rewrite <- Lonly_r  OK
                                            rewrite Lonly_r     NO
둘 다 CHECK rw=1 로 잡힌다 (실측 확인).
```

### `rw_sides` — 무엇을 관계로 볼까

```ocaml
let direct = (nm = "Coq.Init.Logic.eq" || nm = "Coq.Init.Logic.iff") in
if direct then Some (args.(n-2), args.(n-1))
else if not !use_setoid then None
else … Rewrite.is_applied_rewrite_relation env sigma [] t …    (* 캐시 *)
```

- `eq`·`iff` 는 **직접** 안다.
- 그 밖은 **Coq 에게 물어본다** — `Rle`·`Znumtheory.rel_prime` 처럼
  `Proper` 인스턴스가 있는 사용자 관계도 `rewrite` 대상이다.
- 물어보는 건 비싸서 머리 이름으로 **캐시**한다.

### 깊이를 다 본다

```
   PTree.gso : i <> j -> get i (set j x m) = get i m
                          └── 등식이 **깊이 6** 에 있다
```

rewrite lemma 는 대개 전제가 있어 등식이 깊이 ≥1 에 있다.
그래서 깊이를 끝까지 훑는다. `use_setoid` 는 **깊이와 무관**하고
"eq/iff 밖의 관계를 볼지"만 정한다.

---

## 5. 트리는 셋, 채널은 넷

```
   A 트리  ──────────────▶  ap
   P 트리  ──────────────▶  in
   R 트리  ──┬───────────▶  rw    (맞은 redex 가 goal 것)
             └───────────▶  rwh   (맞은 redex 가 가설 것)
```

`rw`/`rwh` 는 **같은 트리, 같은 스캔**을 쓰고 출력만 가른다.

```ocaml
let goal_sub = CH.create 97 in
let rec mark t = CH.replace goal_sub (Unsafe.to_constr t) (); EConstr.iter sigma mark t in
mark concl;                                       (* goal 부분항에 표시 *)
…
(if CH.mem goal_sub (EConstr.Unsafe.to_constr st)
 then Hashtbl.replace out_rw  nm ()
 else Hashtbl.replace out_rwh nm ());
```

가르는 이유는 실측이다 — goal redex 로 통과 163 · **가설 redex 로만** 통과 147 ·
**교집합 0**. 비중도 6배 다르다(22.1% vs 3.8%).

---

## 6. 규모

```
   후보 lemma   12,652개
        │  index_cand — 깊이마다 A·P·R
        ▼
   패턴        87,139개        (후보당 평균 6.9개)
        │  빌드 1.13초 · 파일당 1회
        ▼
   조회 raw    34,461개  →  선별 5,821  →  진짜 후보 596
```

색인은 `nb_globals` 가 바뀔 때만 다시 만든다 (`idx.nglob <> nb_globals env`).
`Require` 가 없으면 파일 하나당 한 번이다.

---

## 관련

[btermdn.md](btermdn.md) · [tree-shape.md](tree-shape.md) · [channels.md](channels.md) ·
[pi-binder.md](pi-binder.md) · [../terminology/noccurn.md](../terminology/noccurn.md)
