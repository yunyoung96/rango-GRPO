# sigma (evar_map) — 미지수 장부

`sigma : Evd.evar_map`. 코드에서 거의 항상 `sigma` 나 `sg` 로 쓴다.

**증명 도중의 "아직 안 정해진 것들" 장부**다. 항 자체에는 `?e1` 같은 **구멍 번호**만
들어 있고, 그 번호가 무엇인지는 전부 `sigma` 가 들고 있다.

```
항       :  PTree.get ?e1 (PTree.set ?e2 ?e3 ?e4) = PTree.get ?e1 ?e4
                     └─ 번호일 뿐 ─┘
sigma    :  ?e1 : positive     (미정)
            ?e2 : positive     (미정)
            ?e3 : A            (미정)
            ?e4 : tree A       ↦ m        ← 정해졌다
            + universe 제약 (Type_i < Type_j …)
```

## 왜 항상 같이 다니나

`EConstr` 의 함수는 대부분 `sigma` 를 받는다. `kind sigma t`, `noccurn sigma n t`,
`Vars.subst1` … 항을 **읽으려면** 정해진 evar 를 먼저 펼쳐 봐야 하기 때문이다.
`sigma` 없이 보면 `?e4` 가 그냥 구멍으로 보이고, 있으면 `m` 으로 보인다.

## 불변식 — 단일화는 sigma 를 **갱신**한다

`w_unify` 는 성공하면 **새 sigma** 를 돌려준다. 옛것을 계속 쓰면 안 된다.

```ocaml
let sg' = Unification.w_unify env sg Conversion.CONV a b in
(* 여기서부터 sg 가 아니라 sg' 를 써야 한다 *)
```

우리가 실제로 당한 버그다 — `depth_of` 가 `new_evar` 로 만든 sigma 를 버리고
바깥 sigma 로 재귀해서 `Anomaly "in retyping: Unknown evar"` 가 났다.
**새로 만든 evar 가 장부에 없는 sigma 로 그 evar 를 읽으려 한 것**이다.
고친 뒤 sigma 를 인자로 실어 나른다. → [../versions/r5.md](../versions/r5.md)

## 관련

[[evar]] · [[econstr]] · [[w-unify]] · [[noccurn]]
