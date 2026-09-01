# `lex` — 어휘 겹침 (goal 텍스트 ↔ 후보 진술문)

> tf-idf 가 재던 것을 **특징 하나로** 넣은 것. 랭커 전체가 아니다.
> 코드: `scripts/applic_rank.py` `lex_overlap`(272)

---

## 0. 한 줄

```
   lex(L) = "goal 에 나오는 단어가 L 의 진술문에 얼마나 겹치나"
            (희소한 단어일수록 크게, 진술문이 길수록 깎아서)
```

---

## 1. 정의

```python
_TOK = re.compile(r"[A-Za-z_][\w']*")          # 식별자만 뽑는다

def lex_overlap(stmt, goal_toks, tok_idf):
    ts = set(_TOK.findall(stmt))               # 후보 진술문의 토큰
    inter = ts & goal_toks                     # goal 과 겹치는 것
    num = sum(tok_idf.get(t, 1.0) for t in inter)
    return num / (len(ts) ** 0.5)
```

```
              Σ  idf(t)
            t ∈ 겹침
   lex(L) = ──────────────
             √|L 의 토큰 수|
```

### 세 조각

| | 무엇 | 왜 |
|---|---|---|
| **분자** | 겹친 토큰의 idf 합 | 흔한 단어(`forall`·`x`)는 거의 0점 |
| **√ 분모** | 진술문 길이의 제곱근 | 긴 lemma 가 무작정 유리해지는 것을 막는다 |
| `set()` | 중복 제거 | 같은 단어를 여러 번 써도 한 번만 센다 |

> 분모가 `len` 이 아니라 `√len` 인 이유: `len` 이면 짧은 lemma 가 과하게 유리해지고,
> 나누지 않으면 긴 lemma 가 이긴다. 정보검색의 길이 정규화와 같은 자리다.

### `tok_idf` — 말뭉치는 "후보 진술문 전체"

```python
_df = Counter()                                # 토큰이 몇 개 진술문에 나오나
for r in rows:
    for stmt in r["stmts"].values():
        for t in set(_TOK.findall(stmt)): _df[t] += 1
tok_idf = {t: log((ndoc + 1) / (df + 1)) for t, df in _df.items()}
```

**문서 = lemma 진술문 하나.** 그래서 `forall`·`x`·`Type` 은 idf 가 0에 가깝고,
`Int64`·`eqm` 같은 것은 크다. → [tf-idf.md](tf-idf.md)

---

## 2. 손으로 따라가기

```
   goal :  … Int.eqm (Int.unsigned x) y …
           토큰 = { Int, eqm, unsigned, x, y }

   후보 :  Int.eqm_samerepr
   진술문:  (forall x y : Z, Int.eqm x y -> Int.repr x = Int.repr y)
           토큰 = { forall, x, y, Z, Int, eqm, repr }        |ts| = 7
```

```
   겹침 = { Int, eqm, x, y }

   idf(Int)   낮다   (거의 모든 CompCert lemma 에 있다)      ≈ 0.4
   idf(eqm)   높다   (드물다)                                ≈ 4.1
   idf(x)     0에 가깝다                                     ≈ 0.1
   idf(y)     0에 가깝다                                     ≈ 0.1
                                                             ─────
   분자 ≈ 4.7        분모 = √7 ≈ 2.65        lex ≈ 1.77
```

**점수를 만든 건 사실상 `eqm` 하나다.** `x`·`y`·`Int` 는 있으나 마나다 —
idf 가 알아서 지운다. 불용어 목록을 손으로 만들 필요가 없다.

---

## 3. 구간과 가중치

```python
out.append(("lex", _bucket(lex.get(nm, 0.0), (0.3, 1.0, 2.5, 5.0, 9.0))))
```

```
   lex   0 ──── 0.3 ──── 1.0 ──── 2.5 ──── 5.0 ──── 9.0 ────▶
   구간    0       1        2        3        4        5
```

학습된 가중치 (CompCert 450지점):

```
   ('lex', 5)   +6.94 bit    ← 강하게 겹친다. 가중치 **3위**
   ('lex', 4)   +5.24 bit
   ('lex', 0)   −1.45 bit    ← 하나도 안 겹치면 감점
```

**있으면 크게 밀어주고 없으면 조금 깎는다.** 비대칭이다 —
`lex=0` 이라고 gold 이 아닌 건 아니기 때문이다(이름만 겹치는 lemma 도 있다).

---

## 4. ★ 이걸 빼면 얼마나 손해인가

실제로 빼고 재봤다 (실수였다).

```
   lex·nov 를 붙이고 잰 값   ~72%   (r10, apply/rewrite)
   빼고 잰 값               59.0%
                            ─────
   두 특징만으로 약 13pp
```

`('nov',3) +8.19` 와 `('lex',5) +6.94` 는 **가중치 2·3위**다.
구조 신호(`lcp`·`lgg`)가 못 보는 것을 본다.

---

## 5. 왜 랭커 전체로 쓰면 안 되나

tf-idf 를 **단독 랭커**로 쓰면 우리 모집단에서 무너진다.

```
   필터 후 top10 의  43% 가 stdlib
                     19% 가 보편 lemma (f_equal · eq_sym 부류)
```

이유는 [tf-idf.md](tf-idf.md) — 어휘가 겹치는 것과 **실제로 적용되는 것**은 다르다.
그래서 버리지 않고 **12개 특징 중 하나로** 넣어 다른 신호와 비트 단위로 경쟁시킨다.
→ [naive-bayes.md](naive-bayes.md)

---

## 6. 한계

- **goal 텍스트가 있어야 계산된다.** 플러그인은 goal 을 문자열로 안 내보내므로
  파이썬 쪽에서 sentence DB 를 읽어 붙인다 (`build_prompt_pool.enrich`).
  이걸 빠뜨리면 조용히 특징이 사라진다.
- 진술문이 없는 후보(`stmts` 가 빈 것)는 `lex = 0.0` 이 된다 — "안 겹침" 과
  "모름" 이 구분되지 않는다.
- 토큰화가 순진하다. `Int.eqm` 은 `Int` 와 `eqm` 으로 갈리는데,
  이게 좋을 때도 나쁠 때도 있다.

## 관련

[[nov]] · [[tf-idf]] · [[naive-bayes]] · [[applic-idf]]
