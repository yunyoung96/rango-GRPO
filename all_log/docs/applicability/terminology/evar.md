# evar — 아직 안 정해진 항

**존재 변수(existential variable).** "여기에 뭔가 들어갈 건데 아직 모른다."
화면에는 `?x` 나 `?Goal` 로 보인다.

```coq
eapply PTree.gso.
(* goal 이 두 개로: 본체와  ?j : positive  같은 미정 인자 *)
```

## de Bruijn 과 뭐가 다른가

| | `Rel n` | `Evar e` |
|---|---|---|
| 뜻 | **묶인** 변수 | **미정**인 항 |
| 정해지나 | 안 정해진다 | 단일화가 정한다 |
| 어디 있나 | 항 안 | 값은 [[sigma]] 안 |
| 치환 | `subst1` | 단일화가 sigma 에 기록 |

## 우리가 만드는 곳

`apply` 후보를 볼 때 Π-바인더를 벗기면서 그 자리에 evar 를 넣는다.
**`eapply` 가 하는 일을 그대로 흉내내는 것**이다.

```ocaml
let (sg, ev) = Evarutil.new_evar env sg a in
```

## 판별트리에서

```ocaml
| Evar _ -> Everything
```

evar 는 무엇이든 될 수 있으므로 **가름을 포기**한다. → [../concepts/btermdn.md](../concepts/btermdn.md)

## 랭킹 신호로도 쓴다

단일화가 끝나고 **안 정해진 채 남은 evar 개수**가 특징 `e` 다.

```
('e', 0)  +12.07 bit   ← 0개면 goal 이 lemma 를 완전히 결정했다는 뜻. 가장 강한 신호
```

## 관련

[[sigma]] · [[w-unify]] · [[de-bruijn]]
