# `nov` — 이름 겹침 (goal 의 이름 조각 ↔ 후보 **이름**)

> Coq 프로젝트의 **명명 관습**을 그대로 신호로 쓴다.
> 코드: `scripts/applic_rank.py` `_name_toks`(279) · `feats`(292)

---

## 0. 한 줄

```
   nov(L) = "goal 에 등장하는 이름들의 조각과 L 의 **이름** 이 몇 개 겹치나"
```

[lex](lex.md) 는 **진술문**을 보고, `nov` 는 **이름**을 본다.

---

## 1. 왜 이름을 따로 보나

Coq 프로젝트는 이름을 규칙적으로 짓는다.

```coq
   repr_canonical      ← goal 에 `repr_*` 가 여럿 있으면
   repr_involutive        이름만 보고도 관련 lemma 를 짚을 수 있다
   repr_unsigned
```

```
   goal :  … Int.repr (Int.unsigned x) = x …
   gold :  Int.repr_unsigned
                 └──┬──┘ └───┬───┘
              goal 에 있다  goal 에 있다
```

**진술문을 안 봐도 이름만으로 답이 보인다.** 사람이 실제로 쓰는 단서다.

---

## 2. `_name_toks` — 이름을 조각으로

```python
def _name_toks(x):
    x = x.split(".")[-1]                    # 모듈 접두사를 버린다
    parts = re.split(r"[_']+", x)           # 밑줄·프라임으로 자른다
    out = set()
    for p in parts:
        out.add(p.lower())
        for q in re.findall(r"[A-Z]?[a-z0-9]+", p):   # 낙타표기도 자른다
            if len(q) > 2: out.add(q.lower())
    return out
```

세 단계다.

```
   Int64.lt_sub_overflow
        │ ① 모듈 버림      →  lt_sub_overflow
        │ ② 밑줄로 자름     →  {lt, sub, overflow}
        │ ③ 낙타표기 분해   →  (해당 없음)
        ▼
   {lt, sub, overflow}
```

실측 예:

```
   repr_canonical         → {repr, canonical}
   PTree.gso              → {gso}                    ← 모듈 PTree 는 버린다
   Int64.lt_sub_overflow  → {lt, sub, overflow}
   agree_regs_invariant   → {agree, invariant, regs}
   Zle_bool_imp_le        → {zle, bool, imp, le}
   bpow_gt_0              → {bpow, gt, 0}
   eq_sym                 → {eq, sym}
   sep_swap23             → {sep, swap23}
```

> **`len(q) > 2` 조건**은 낙타표기 분해에만 걸린다. `le`·`gt` 같은 두 글자는
> 밑줄 분해(②)에서 이미 들어오므로 살아남는다. 반면 `PTree` 를 `P`+`Tree` 로
> 쪼갤 때의 `P` 같은 부스러기는 버린다.

---

## 3. goal 쪽은 어떻게 만드나

goal **텍스트의 모든 식별자**를 각각 `_name_toks` 로 쪼개 합집합을 만든다.

```python
_gt = set(_TOK.findall(goal_text))          # goal 의 식별자들
_gn = set()
for _x in _gt: _gn |= _name_toks(_x)        # 각각을 조각내어 합친다
r["gnames"] = sorted(_gn)
```

```
   goal :  Int.repr (Int.unsigned x) = x
   식별자:  {Int, repr, unsigned, x}
        │ 각각 _name_toks
        ▼
   gnames = {int, repr, unsigned, x}
```

---

## 4. 특징 값

```python
nt = _name_toks(nm)                          # 후보 이름의 조각
out.append(("nov", _bucket(len(nt & gname), (1, 2, 3))))
```

**겹친 조각의 개수**다. 구간은 넷:

```
   겹침   0    1    2    3 이상
   구간   0    1    2    3
```

```
   후보 Int.repr_unsigned  →  {repr, unsigned}
   gnames                  =  {int, repr, unsigned, x}
   겹침 = {repr, unsigned} = 2개   →  ('nov', 2)
```

학습된 가중치:

```
   ('nov', 3)   +8.19 bit    ← 세 조각 이상 겹친다. **전체 2위**
   ('nov', 2)   +6.32 bit
   ('nov', 0)   −1.85 bit    ← 하나도 안 겹치면 감점
```

`('e',0) +12.32` 다음으로 강하다. **이름이 겹치면 거의 답이다.**

---

## 5. `lex` 와 무엇이 다른가

| | `lex` | `nov` |
|---|---|---|
| 보는 것 | 후보의 **진술문** | 후보의 **이름** |
| 상대 | goal 텍스트 토큰 | goal 이름들의 **조각** |
| 값 | idf 가중 합 / √길이 (실수) | 겹친 조각 **개수** (정수) |
| 가중치 최고 | +6.94 | **+8.19** |
| 강한 경우 | 진술문 구조가 비슷 | 명명 관습이 같은 계열 |

**둘은 서로 못 보는 걸 본다.**

```
   진술문은 겹치는데 이름이 안 겹침
       goal: a + 0 = a      gold: plus_n_O
       lex 높음 (`plus`? 아니고 `+` 는 토큰이 아니다) · nov 0

   이름은 겹치는데 진술문이 안 겹침
       goal: … repr_canonical …    gold: repr_involutive
       nov 높음 (repr) · lex 낮을 수 있음
```

---

## 6. 한계

- **명명 관습에 기댄다.** 규칙적으로 이름 짓는 프로젝트(CompCert·mathcomp)에서
  잘 듣고, 그렇지 않으면 무의미하다. 프로젝트 간 이식성이 없다.
- **모듈 접두사를 버린다.** `PTree.gso` → `{gso}` 라 `PTree` 가 goal 에
  있어도 못 쓴다. 의도한 것이지만(모듈명이 흔해서 잡음), 손해도 있다.
- `lex` 와 같이 **goal 텍스트가 있어야** 계산된다. 안 붙이면 조용히 사라진다 —
  실제로 그렇게 재서 @10 을 13pp 낮게 봤다.
- 숫자 조각(`bpow_gt_0` 의 `0`)이 그대로 남는다. `0`·`1`·`2` 는 흔해서 잡음이다.

## 관련

[[lex]] · [[naive-bayes]] · [[tf-idf]]
