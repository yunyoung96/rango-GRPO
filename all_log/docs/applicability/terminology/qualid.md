# qualid / Nametab — lemma 이름을 어떻게 쓰나

```ocaml
Nametab.shortest_qualid_of_global Id.Set.empty gr : qualid
```

전역 참조(`GlobRef.t`)를 **지금 문맥에서 통하는 가장 짧은 이름**으로 바꾼다.

```
전체 이름                         현재 통하는 가장 짧은 이름
compcert.lib.Maps.PTree.gso   →   PTree.gso
Coq.Init.Peano.plus_n_O       →   plus_n_O
```

## 왜 필요했나 — 모듈 안의 lemma

풀에 든 premise 의 **34.7%** 가 모듈 안에 있었다.
짧은 이름만 뽑으면 `gso` 가 되어 프롬프트에 넣어도 Coq 이 못 찾는다.
반대로 전체 이름을 쓰면 모델이 본 적 없는 문자열이 된다.

`shortest_qualid_of_global` 은 **`Import` 상태를 반영**해서 그 지점에서
실제로 쓸 수 있는 이름을 준다. → [../versions/r8.md](../versions/r8.md)

## 반대 방향

```ocaml
Smartlocate.global_with_alias : qualid -> GlobRef.t
```

`ApplicCheck PTree.gso` 처럼 사용자가 이름을 줄 때 쓴다. 별칭(`Notation`
으로 만든 이름)까지 따라간다.

## 관련

[[globref]]
