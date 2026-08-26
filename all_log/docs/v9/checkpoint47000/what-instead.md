# gold lemma 를 넣어 줘도 실패하는 이유 — 그럼 모델은 대신 뭘 쓰나

> 대상: `checkpoint-47000` · CompCert rand200 오라클 실험 382 스텝
> 원자료: `all_log/what_instead_47k_s{0,1,2}.jsonl` · 스크립트 `scripts/what_instead.py`
> 방법: 저장된 **A 팔 생성물**을 읽고, 같은 스텝의 **검색된 100 premise 목록을 재구성**해서
> 생성물 안의 이름이 어디서 왔는지 가른다. GPU 불필요(생성 없음, 재구성만).

---

## 0. 세 줄 답

1. **"다른 검색된 lemma 를 쓴다"는 아니다.** 12.6% 뿐이다.
2. **가장 흔한 건 이름을 아예 안 쓰는 것** — 인자 없는 tactic 31.9% + **`assert` 도피 17.5%**.
3. **`assert` 는 무작위가 아니다.** gold lemma 의 **명제를 그대로 베껴 쓴다.**
   상위 17.5% 는 gold 선언문과 토큰 커버리지 80% 이상, 여러 건은 **100% 일치**다.
   → **모델은 명제를 안다. 그 명제에 붙은 *이름*을 모른다.**

---

## 1. 분류 결과

A 팔 첫 후보 기준. gold 는 정의상 `apply`/`rewrite` + 이름 있는 lemma 다.

| 무엇을 썼나 | 전체 (382) | gold 가 검색됨 (225) | gold 가 검색 안 됨 (157) |
|---|---|---|---|
| **인자 없는 tactic** | 122 (31.9%) | 72 (32.0%) | 91 (58.0%)\* |
| **gold** | 96 (25.1%) | 81 (36.0%) | 15 (9.6%) |
| **`assert` 도피** | 67 (17.5%) | 27 (12.0%) | 40 (25.5%) |
| **검색된 다른 것** | 48 (12.6%) | 33 (14.7%) | 15 (9.6%) |
| 검색 밖 실재 | 36 (9.4%) | 19 (8.4%) | 17 (10.8%) |
| 가설/지역이름 | 17 (4.5%) | 8 (3.6%) | 9 (5.7%) |
| **환각** | 13 (3.4%) | 5 (2.2%) | 8 (5.1%) |

\* 우측 두 열은 `assert` 를 "인자 없는 tactic" 에 합산한 조기 집계라 합이 다르다. 왼쪽 열이 최종 분류다.

**읽는 법:**

- **질문 "다른 검색된 lemma 를 쓰나" → 12.6% 다.** gold 가 검색 목록에 없을 때도 9.6% 뿐이다.
  틀린 lemma 를 **골라서** 실패하는 게 아니다.
- **환각도 아니다 — 3.4%.** 없는 이름을 지어내는 문제가 아니다.
- **압도적으로 흔한 건 "이름을 아예 안 쓰는 것"** 이다.
  인자 없는 tactic(31.9%) + `assert`(17.5%) + 가설(4.5%) = **53.9%**.
  gold 가 검색 목록에 **없을 때** 이 비율은 더 올라간다.

---

## 2. ★ `assert` 도피 — 이름 대신 명제를 베낀다

`assert` 는 인자 없는 tactic 중 압도적 1위다(163건 중 67건). 그리고 **무작위가 아니다.**

세운 명제와 gold lemma 선언문의 토큰 커버리지(gold 선언 토큰 중 assert 가 담은 비율):

| | |
|---|---|
| 중앙값 | **43%** |
| coverage ≥ 80% | **10/57 = 17.5%** |
| coverage ≥ 60% | 20/57 = 35.1% |
| coverage ≥ 40% | 32/57 = 56.1% |

### 완전 일치 사례

```
gold lemma : IZR_le
  선언       forall n m:Z, (n <= m)%Z -> IZR n <= IZR m.
  gold 스텝  apply IZR_le.
  모델 생성  assert (forall n m, (n <= m)%Z -> IZR n <= IZR m) as H_asrt0.
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ 선언문과 100% 동일
```

```
gold lemma : Rabs_mult
  선언       forall x y:R, Rabs (x * y) = Rabs x * Rabs y.
  gold 스텝  rewrite Rabs_mult.
  모델 생성  assert (forall x y:R, Rabs (x * y) = Rabs x * Rabs y) as H_asrt0.
```

```
gold lemma : Int.bits_or
  선언       forall x y i, 0 <= i < zwordsize -> testbit (or x y) i = testbit x i || testbit y i.
  gold 스텝  rewrite Int.bits_or.
  모델 생성  assert (forall x y i, 0 <= i < zwordsize ->
                     testbit (Int.or x y) i = testbit x i || testbit y i) as H_asrt0.
```

```
gold lemma : Z.gt_lt
  gold 스텝  now apply Z.gt_lt.
  모델 생성  assert (forall p q, p > q -> q < p) as H_asrt0.
```

```
gold lemma : Rle_not_lt
  gold 스텝  apply Rle_not_lt with (1 := H).
  모델 생성  assert (forall n m, n < m -> ~ m <= n) as H_asrt0.
```

**모델은 명제를 정확히 안다.** 파라메트릭 기억에 들어 있다.
그런데 **그 명제에 붙은 이름을 부르지 못한다.** 그래서 이름 대신 명제를 베껴 쓴다.

이게 [assert_effectiveness.md](../checkpoint25000/assert_effectiveness.md) 의 결론
("assert 는 자명한 명제만 만든다")를 **뒤집는다** — 자명한 명제도 만들지만,
**절반 이상은 gold lemma 의 재진술**이다. 그리고 그게 더 나쁘다:
`assert` 를 세우면 **그 명제를 스스로 증명해야 하는데**, 이름을 몰라서 assert 를 세운 것이므로
당연히 못 닫는다. rand200 실측에서 `assert` 뒤 `close` 가 99.8% "name not found" 로
INVALID 였던 것과 정확히 맞물린다.

> `CUT_SUBSTEP` 이 모델에게 준 것은 **이름을 모를 때 빠져나갈 구멍**이었다.
> 구멍이 없었으면 틀린 이름이라도 시도했을 텐데, 구멍이 있으니 명제를 베끼고 만다.

---

## 3. 실패 유형별 — 이름만 알려주면(C) 되는가

| 무엇을 썼나 | n | **okC** (이름 줌) | **okB** (premise 에 꽂음) | gold 가 검색됨 |
|---|---|---|---|---|
| 인자 없는 tactic | 122 | **66.4%** | 19.8% | 49.2% |
| gold | 96 | 80.2% | 62.5% | 84.4% |
| **`assert` 도피** | 67 | **70.1%** | 28.1% | 40.3% |
| 검색된 다른 것 | 48 | **75.0%** | 29.5% | 68.8% |
| 검색 밖 실재 | 36 | **77.8%** | 31.2% | 52.8% |
| 환각 | 13 | 61.5% | 12.5% | 38.5% |

**모든 유형에서 okC 가 okB 의 2~3배다.**

`assert` 로 도피한 67건 중 **70.1% 는 이름만 정해 줬으면 성공**했다.
그런데 그 이름을 **premise 목록 맨 앞에 꽂아 주면 28.1%** 밖에 안 된다.

> 정보를 **주는 것**(B)과 **지정하는 것**(C) 사이에 42pp 가 있다.
> 이 격차가 "고르기" 의 크기다.

---

## 4. 나머지 유형 실례

### 검색된 다른 것 (12.6%) — 이건 진짜 오선택이다

```
gold  : rewrite Z.add_comm.
생성  : rewrite Int.repr_unsigned.        ← 검색 목록에 있는 다른 lemma
gold 검색: X · okC=O
```
```
gold  : apply Rnot_le_lt.
생성  : now apply Rcompare_Lt_inv.        ← 검색 목록에 있는 다른 lemma
gold 검색: X · okB=O okC=O
```

gold 가 목록에 **없어서** 근처의 다른 걸 집은 경우가 많다 — 순수 오선택보다는 **대체**에 가깝다.

### 검색 밖 실재 (9.4%) — 파라메트릭 기억에서 꺼낸다

```
gold  : now apply Zmult_lt_0_compat.
생성  : apply Zmult_gt_0_compat.          ← 검색엔 없지만 실재하는 이름 (형제 lemma)
```
```
gold  : rewrite zlt_true by lia.
생성  : destruct (zlt (i - (Y - Z)) (zwordsize - Y)); auto.   ← zlt 는 실재
```

검색이 안 준 이름도 **기억에서 꺼낸다.** 다만 대개 **형제 lemma**(`lt`↔`gt`)라 틀린다.

### 환각 (3.4%) — 드물다

```
gold  : erewrite match_prog_def by eauto.
생성  : apply TRANSF; trivial.            ← TRANSF 는 어디에도 선언 없음
```

---

## 5. 그래서 뭘 해야 하나

| 후보 | 근거 | 판정 |
|---|---|---|
| **랭커 순위 개선** | 재정렬 효과 47k 에서 소멸(+1.0pp, p=0.880) | ✗ 이득 없음 |
| **랭커 커버리지 확대** | 진짜 주입 +6.2pp (p=0.118) | △ 방향은 맞으나 천장 13.3% |
| **`assert` 금지 (`NO_ASSERT`)** | 25k A/B 무효과 (b=0 c=1, p=1.000) | ✗ 후보에서 지워도 대체 행동이 똑같음 |
| **`CUT_SUBSTEP=0` 학습** | assert 도피 자체를 안 배우게 함 | ◯ 학습 필요 — 다른 서버 |
| **★ assert 명제로 되찾기** | assert 의 43~100% 가 gold 선언문과 겹침 | **◎ 즉시 구현 가능** |
| **GRPO** | okC 70% vs okB 28% = 아는데 못 부름. SFT 는 벌이 없음 | ◎ 근본 |

### ★ 즉시 해 볼 것 — "assert 명제로 되찾기"

모델이 `assert (P)` 를 세우면, **그 `P` 를 질의문으로 삼아 premise pool 을 다시 검색**한다.
`P` 는 이미 gold 선언문과 중앙값 43% (상위 17.5% 는 80% 이상) 겹치므로,
**모델이 스스로 만든 최고 품질의 검색 질의**다.

```
모델: assert (forall n m, (n <= m)%Z -> IZR n <= IZR m) as H_asrt0.
       ↓ 이 명제로 premise 재검색
찾음: IZR_le : forall n m:Z, (n <= m)%Z -> IZR n <= IZR m.
       ↓ assert 를 버리고 이름으로 치환
결과: apply IZR_le.
```

지금 랭커는 **goal** 로 검색한다. `assert` 명제로 검색하면 질의가 완전히 다르다 —
goal 은 "무엇을 증명해야 하나"고, assert 명제는 "무엇이 필요한가"다.
후자가 lemma 검색에는 훨씬 직접적이다.

구현은 검색 단계만 건드리면 되고 **재학습이 필요 없다.**

---

## 6. 한계

- **B 팔 생성물은 저장돼 있지 않았다** (`rB` 를 계산만 하고 버림).
  위 분류는 **A 팔** 기준이다. B 는 premise 하나가 맨 앞에 추가된 것뿐이고
  이름 언급률이 45.7% → 55.8% 로 10pp 차이라, 행동 분포는 대체로 같을 것으로 본다.
  다만 **직접 확인은 아니다.**
  → `scripts/oracle_lemma_eval.py` 에 `B=rB[:3]` 저장을 추가해 뒀다. 다음 실행부터 잡힌다.
- 검색 목록 재구성은 랭커가 결정적이라는 가정에 기댄다. `gold_in_prem` 58.9% vs
  오라클이 기록한 `in_prompt` 66.2% 의 차이는 **선언명이 아닌 형태로 프롬프트에 등장**하는
  경우(본문 인용, 다른 premise 의 진술 안) 때문이다.
- `assert` 커버리지는 토큰 집합 겹침이지 의미 동치가 아니다. 상위 사례는 육안 확인했다.

---

## 7. 재현

```bash
# GPU 불필요 · 3 샤드 약 20분
for s in 0 1 2; do
  WI_SHARD=$s WI_NSHARD=3 WI_OUT=all_log/what_instead_47k_s$s.jsonl \
    python3 scripts/what_instead.py all_log/oracle47k_s0.jsonl all_log/oracle47k_s1.jsonl &
done; wait
```
