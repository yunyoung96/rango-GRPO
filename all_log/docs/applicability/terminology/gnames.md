# `gnames` — goal 쪽 이름 조각 집합

> [`nov`](nov.md) 가 후보 이름과 대조하는 **상대편**. 이것 없이는 `nov` 가 계산 안 된다.
> 코드: `scripts/applic_rank.py` `_name_toks`(279) · `build_prompt_pool.enrich`

---

## 0. 한 줄

```
   gnames = goal 텍스트의 **모든 식별자**를 조각내어 합친 집합
```

```
   goal   :  Int.repr (Int.unsigned x) = x
        │ ① 식별자 추출
   식별자 :  {Int, repr, unsigned, x}
        │ ② 각각을 _name_toks 로 조각냄
   gnames :  {int, repr, unsigned, x}
```

---

## 1. 만드는 법

```python
_gt = set(_TOK.findall(goal_text))       # ① goal 의 식별자들
_gn = set()
for _x in _gt:
    _gn |= _name_toks(_x)                # ② 각각을 조각냄
r["gnames"] = sorted(_gn)
```

`_TOK = re.compile(r"[A-Za-z_][\w']*")` — 식별자만 뽑는다. 연산자·괄호·숫자는 버린다.

`_name_toks` 는 [nov.md](nov.md) 에 있다 — 모듈 접두사를 버리고, 밑줄·프라임으로
자르고, 낙타표기를 분해한다.

```
   Int.repr        → {repr}
   Int.unsigned    → {unsigned}
   PTree.get       → {get}
   agree_regs      → {agree, regs}
```

---

## 2. 왜 goal **텍스트**인가

플러그인은 goal 을 **항(term)** 으로 다루지 커널 밖으로 문자열을 안 내보낸다.
그래서 `gnames` 는 파이썬 쪽에서 CoqStoq 의 증명 상태 텍스트를 읽어 만든다.

```
   플러그인 (OCaml)     항 → 채널·신호 (lcp·lgg·e·z…)      goal 문자열 없음
   파이썬               goal 텍스트 → lex·gnames           ← 여기서만 만든다
```

**이게 조용히 빠지는 지점이다.** 풀만 있으면 `nov`·`lex` 가 계산이 안 되는데,
`feats` 는 그냥 특징을 **덜 만들고** 넘어간다. 실측으로 그렇게 재서 @10 을
13pp 낮게 봤다. 그래서 지금은 개수를 assert 로 강제한다:

```python
_want = 10 + (lex is not None) + (gname is not None)
assert len(out) == _want, f"특징이 {len(out)}개 (기대 {_want})"
```

---

## 3. 무엇에 쓰나

`nov` 특징 하나뿐이다. 후보 이름의 조각과 **교집합 크기**를 센다.

```python
nt = _name_toks(nm)                        # 후보 이름 조각
out.append(("nov", _bucket(len(nt & gname), (1, 2, 3))))
```

```
   gnames             = {int, repr, unsigned, x}
   Int.repr_unsigned  → {repr, unsigned}
   교집합 2개          → ('nov', 2)  → +6.32 bit
```

학습된 가중치에서 `('nov',3) +8.19` 는 **전체 2위**다.

---

## 4. 크기

```
   goal 하나당 gnames  중앙 20~40개
   대부분이 짧은 조각 (get · set · int · repr …)
```

goal 이 클수록 커지고, 그만큼 **우연한 겹침**도 는다. `nov` 를 개수로만 재는 게
아니라 조각의 희소도로 가중하면 나을 수 있는데, 아직 안 해봤다 —
`lex` 는 idf 가중을 하는데 `nov` 는 안 한다.

---

## 5. 한계

- **goal 텍스트가 있어야 한다.** 플러그인만으로는 못 만든다. 파이프라인이
  끊기면 `nov` 가 통째로 사라진다.
- **명명 관습에 기댄다.** CompCert·mathcomp 처럼 규칙적으로 이름 짓는 코드에서
  잘 듣고, 그렇지 않으면 무의미하다. 프로젝트 간 이식성이 없다.
- **숫자·한 글자 조각이 잡음이다.** `bpow_gt_0` 의 `0`, 변수 `x`·`y` 가
  gnames 에 그대로 들어간다. 걸러내지 않는다.
- 모듈 접두사를 버려서 `PTree` 가 goal 에 있어도 못 쓴다.

## 관련

[[nov]] · [[lex]] · [[naive-bayes]] · [[tf-idf]]
