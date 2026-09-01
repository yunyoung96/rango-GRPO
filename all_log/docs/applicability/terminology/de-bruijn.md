# de Bruijn 인덱스 — 이름 없는 변수

커널은 변수를 **이름이 아니라 번호**로 쓴다. `Rel n` = "밖으로 `n` 번째 바인더".

```coq
fun x => fun y => x
        ↓ 커널
Lambda(x, _, Lambda(y, _, Rel 2))
                              ↑ 2칸 밖 = x
```

```
   Lambda x  ──┐  Rel 2 는 여기를 가리킨다
     Lambda y ─┼┐ Rel 1 은 여기
       Rel 2 ──┘│
                │
   안쪽으로 들어갈수록 같은 변수의 번호가 커진다
```

## 왜 이렇게 하나

- **α-동등이 구문 동등이 된다.** `fun x => x` 와 `fun y => y` 가 **같은 항**이다.
  이름 바꾸기(capture-avoiding renaming)를 할 필요가 없다.
- 판별트리에 넣을 때도 이름이 안 끼어든다.

## 대가 — 이동(lift)과 치환(subst)

바인더를 하나 벗기면 안쪽 번호가 전부 하나씩 줄어야 한다.

```ocaml
EConstr.Vars.subst1 v b     (* b 안의 Rel 1 을 v 로 바꾸고 나머지를 1 내린다 *)
EConstr.Vars.lift n t       (* 전부 n 올린다 *)
EConstr.Vars.closed0 t      (* 자유 Rel 이 하나도 없나 *)
```

우리 `descend` 가 바인더를 벗길 때 쓰는 게 `subst1` 이다:

```ocaml
let (sg, ev) = Evarutil.new_evar env sg a in
descend (n+1) sg (EConstr.Vars.subst1 ev b)
```

## `closed0` 이 왜 필터인가

`rewrite` 후보를 모을 때 goal 의 **닫힌** 부분항만 본다. `Rel` 이 들어 있는
부분항은 그 바인더 안에서만 뜻이 있어서 바깥에서 못 쓴다.

## 관련

[[noccurn]] · [[prod]] · [[evar]]
