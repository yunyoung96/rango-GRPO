# 채널이 실제로 어떻게 채워지나 — 지점 하나를 끝까지

> 실측 전사. 지어낸 예가 아니다. CompCert rand200 의 실제 지점이다.
> 코드: `applic_main.ml` `compute`(740) · `scripts/build_prompt_pool.py`

---

## 0. 전체 흐름 한 장

```
   ┌ 색인 (파일당 1회) ─────────────────────────────────────────┐
   │  후보 12,652  →  A·P·R 세 트리에 패턴 87,139개              │
   └────────────────────────────────────────────────────────────┘
                              │  goal 이 온다
   ┌ 조회 (스텝마다) ──────────▼────────────────────────────────┐
   │  ap  ← goal 결론으로 조회                                   │
   │  in  ← 가설마다 조회                                        │
   │  rw  ← goal 부분항마다 조회                                 │
   │  rwh ← 가설 부분항마다 조회                                 │
   └────────────────────────────────────────────────────────────┘
                              │  네 개의 후보 집합
   ┌ 랭킹 ────────────────────▼────────────────────────────────┐
   │  채널마다 **따로** 나이브베이즈로 정렬                        │
   └────────────────────────────────────────────────────────────┘
                              │
   ┌ 배분 ────────────────────▼────────────────────────────────┐
   │  비율대로 번갈아 뽑는다  ap 15 · rw 4 · rwh 2 · in 1         │
   └────────────────────────────────────────────────────────────┘
                              │
                        프롬프트 [PREMISES]
```

---

## 1. 잘 된 지점 — `idx=21 k=40`

```
   gold tactic :  apply agree_regs_invariant
   우주        :  12,652
```

### ① 채널이 채워진다

```
   ap   1,612개   ← goal 결론으로 A 트리 조회 + 커널 단일화
   in       ?개   ← 각 명제 가설로 P 트리 조회
   rw       ?개   ← goal 부분항으로 R 트리 조회
   rwh      ?개   ← 가설 부분항으로 R 트리 조회

   gold `agree_regs_invariant` 은  ap 와 in **둘 다**에 들었다
```

같은 lemma 가 여러 채널에 드는 건 흔하다 — 전체의 14.6%가 그렇다.
결론도 goal 과 맞고, 비의존 전제도 어떤 가설과 맞았다는 뜻이다.

### ② 신호가 붙는다

```
   agree_regs_invariant   lgg=5  e=7  lcp=5  g=6
                          ────────────────────────
                          lgg 5 / goal 6  = 0.83   구조를 거의 다 공유
                          lcp 5 / goal 6  = 0.83   트라이에서 끝까지 붙어 왔다
                          e   7                    evar 7개는 아직 미정
```

`lgg/g` 와 `lcp/g` 가 둘 다 0.83 — **최상위 구간**이다.

### ③ 나이브베이즈가 점수를 낸다

```
   ('lcp', 5)  ← 0.83 은 마지막 구간          큰 가점
   ('lgg', 5)  ← 마찬가지                    +4.79
   ('e',   4)  ← evar 7개는 중간 구간         작은 감점
   ('ch','ap') ← apply 채널
   ('idf', ?)  ← 이 lemma 의 희소도
   …12개 특징의 가중치 합
```

### ④ 결과

```
   최종 순위  1 / 1,612
```

---

## 2. 안 된 지점 — `idx=38 k=3`

```
   gold tactic :  rewrite Int64.lt_sub_overflow
```

```
   ap    416개      gold 없음
   in      0개
   rw    575개      gold 있음  ✓
   uf     10 · ds 4 · dc 23    (r11 에서 뺀 채널)
```

**필터는 맞혔다** — gold 이 `rw` 에 있다. 문제는 신호다.

```
   Int64.lt_sub_overflow   z=6  d=2  lcp=1  nm=1  ing=1  g=36
                           ──────────────────────────────────
                           lcp 1 / goal 36 = 0.03   ← 거의 안 겹친다
                           z    6 / 36     = 0.17   redex 가 작다
```

`lcp=1` 은 **트라이 1층에서 갈라졌다**는 뜻이다. 판별력이 거의 없다.

```
   최종 순위  127 / 934
```

**필터가 찾아도 랭커가 못 올리는 경우다.** rewrite 가 apply 보다 @10 이 낮은
이유가 여기 있다 — rewrite redex 는 작아서(`z` 중앙 6) 구조 신호가 약하다.

---

## 3. 배분 — 하드 선택이 아니라 번갈아 뽑기

### 왜 하드 선택은 위험한가

추론 시점에는 다음 스텝이 `apply` 인지 `rewrite` 인지 **모른다.**
찍어서 한 채널만 쓰면 틀렸을 때 gold 을 통째로 잃는다.

```
   예측 정확도   gold 포함    @10
   ───────────  ─────────   ──────
   100%           94.9%     60.7%
    90%           86.0%     55.6%
    80%           76.4%     49.4%    ← 손익분기
    70%           69.1%     43.8%    ← 합치는 것보다 나쁘다
   (합침)         94.9%     47.8%
```

**회수율 손실은 랭킹으로 못 되찾는다.** 그래서 하드 선택은 정확도 80% 아래에서
손해다. 기저율이 apply 68% / rewrite 32% 라 아무 예측기나 되는 게 아니다.

### 소프트 배분 — 어느 채널도 0칸이 안 된다

```python
WEIGHT = {"ap": 15, "rw": 4, "rwh": 2, "in": 1}

def interleave(per_chan, weight=WEIGHT):
    it = {c: iter(v) for c, v in per_chan.items() if v}
    out, seen = [], set()
    while it:
        for c in list(it):
            for _ in range(weight[c]):        # 비율만큼 연속으로 뽑는다
                nxt = next(it[c], None)
                if nxt is None: it.pop(c); break
                if nxt not in seen: seen.add(nxt); out.append(nxt)
    return out
```

```
   ap 정렬:  a1 a2 a3 … a15 | a16 …
   rw 정렬:  r1 r2 r3 r4    | r5 …
   rwh:      h1 h2          | h3 …
   in:       i1             | i2 …
        ↓ 번갈아
   최종:  a1…a15  r1…r4  h1 h2  i1  a16…a30  r5…r8  h3 h4  i2  …
          └────────── 앞 22칸 ──────────┘
```

- **상위 20칸 안에 네 채널이 다 들어간다** → 회수율 94.9% 유지
- 비율은 물채우기를 K=20 에서 적합한 값이다 (`ap 15 · rw 4 · in 1`)
- 하드 선택과 달리 **예측이 틀려도 안 죽는다**

### 실측 (447지점 · gold 이 풀에 있는 179지점)

```
   최종 순위 중앙 16 · @10 44.7% · @20 65.4% · @100 81.0%
```

---

## 4. 프롬프트로 나가는 형태

```json
{"idx": 38, "k": 3,
 "order": ["Int.eqm_samerepr", "Smallstep.sd_final_determ",
           "Decidableplus.Decidable_eq_obligation_1", "Pregmap.init", …],
 "stmts": {"Int.eqm_samerepr":
             "(forall x y : Z, Int.eqm x y -> Int.repr x = Int.repr y)", …}}
```

`next_step_eval` 이 `POOL_MODE = "ordered"` 로 받아 **이 순서를 그대로** 쓴다.

```python
if POOL_MODE == "ordered":
    ex.premises = [getattr(p, "text", "") for p in extra]
    return ex                      # ← tf-idf 재랭킹을 건너뛴다
```

> ★ 이게 없으면 `_pc.get_ranked_premises` 가 **tf-idf 로 다시 정렬**한다.
> 우리 랭킹을 통째로 버리는 것이고, 실측으로 top8 39.2% → 37.0% 였다.
> 필터를 붙이고도 손해가 났던 원인이 이것이다.

---

## 5. 정리 — 세 단계가 서로 다른 일을 한다

| | 하는 일 | 실패하면 |
|---|---|---|
| **필터** | 12,652 → 채널별 수백 개 | 회수율 손실. **되돌릴 수 없다** |
| **랭킹** | 채널 안에서 순서 | 아래로 밀린다. 회수율은 유지 |
| **배분** | 채널 사이에 슬롯 | 한 채널이 다른 채널을 덮는다 |

```
   필터 실패    gold 이 아예 없다        ← 5.1%
   랭킹 실패    gold 이 127위           ← §2 의 경우
   배분 실패    ap 가 rw 를 다 덮는다    ← 합쳐서 정렬할 때
```

---

## 관련

[channels.md](channels.md) · [three-indexes.md](three-indexes.md) ·
[budget.md](budget.md) · [../terminology/naive-bayes.md](../terminology/naive-bayes.md)
