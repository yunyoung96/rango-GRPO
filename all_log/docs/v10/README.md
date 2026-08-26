# v10 — gold lemma 를 프롬프트에 **끼워 넣어** 조립을 가르친다

> v9 와 다른 것은 하나뿐이다: `assert` 를 버리고, **정답이 항상 프롬프트 안에 있게** 한다.
> 구현: `src/tactic_gen/v10_inject.py` · 배선 `src/tactic_gen/tactic_data.py` `collate()` ①-a′
> 설정: `src/rango_defaults.py` (단일 출처 · §5) · 학습 conf `all_log/ft_qwen3b_v10_conf.yaml`
> 사전점검: `scripts/v10_dryrun.py` · 모의학습 결과 §5.5

---

## 0. 왜 바꾸나 — v9 의 `assert` 가 독이었다

v9 는 gold lemma 가 검색에 안 잡히면 `assert (P) as H` 로 **명제를 세우는 법**을 가르쳤다
(`CUT_SUBSTEP`). 실측 결과:

| 관찰 | 수치 | 출처 |
|---|---|---|
| 모델이 만든 assert 의 명제 ↔ gold signature 겹침 | **중앙 43%**, ≥80% 가 15.8% | [assert_reality.md](../v9/checkpoint25000/assert_reality.md) |
| assert 뒤에 `{ exact L }` 로 이어지는 비율 | **18.3%** | 위 |
| assert 뒤가 `Proof.` 무의미 반복 | **54.2%** | 위 |
| 오라클: 이름만 정해 주면 조립 성공 | **70~74%** | [checkpoint47000/experiment.md](../v9/checkpoint47000/experiment.md) |
| 오라클: 같은 이름을 premise 에 꽂으면 | **13~34%** | 위 |
| `NO_ASSERT=1` A/B (25k, rand200) | 30.0% → 30.5%, b=0 c=1, **p=1.000** | 위 |

**핵심 관찰** — 모델은 **명제를 안다. 이름을 못 부른다.**
`bitwise_binop_shl` 의 signature 를 100% 그대로 assert 해 놓고, 바로 다음 줄에서
`exact bitwise_binop_shl.` 로 닫는 사례가 실제로 있다 — 이름을 알면서 우회한 것이다.

그리고 **못하는 것은 조립이 아니라 고르기**다(오라클 70% vs 13%).
그러면 학습에서 할 일은 하나다 — **고를 것이 반드시 거기 있는 예제를 주는 것.**

---

## 1. 알고리즘

```
스텝 하나마다:

  (1) 외부 lemma 참조가 없다              → 그대로 fine-tuning
  (2) 외부 lemma 참조가 있다
      (2-a) gold lemma 가 이미 프롬프트에 보인다   → 그대로 fine-tuning
            (잘못된 게 아니다 — 검색이 제 일을 한 예제다)
      (2-b) gold lemma 가 안 보인다
            → 프롬프트에 **실제로 실리는** premise 중 하나를 무작위로 빼고
              그 자리에 **gold 의 선언문**을 끼운다
```

`assert` 는 만들지 않는다. `CUT_SUBSTEP` 은 v10 에서 강제로 꺼진다.

### 왜 "실리는 것 중에서" 빼나

`example.premises` 는 100개지만 프롬프트 예산(`premise_tokens=896`)에 실제로 담기는 것은
**20~40개**다. 목록 뒤쪽에서 빼면 **아무것도 안 바뀐다** — 어차피 안 실리던 것이다.
반드시 `whole_number_allocate` 가 고른 인덱스 안에서 빼야 한 자리가 실제로 난다.

그리고 창을 계산할 때 `rerank_premises` 를 **먼저 걸어야** 한다 — collator 가 예산 적용
전에 재정렬하므로, 빼먹으면 모델이 보는 것과 다른 목록으로 판정하게 된다.

### 끼운 뒤 검증한다

끼우고 나서 창을 **다시 계산**해 gold 가 정말 들어왔는지 본다. 안 들어왔으면
(1) 맨 앞으로 옮기고 → (2) 창 안의 가장 긴 것을 하나씩 빼면서 자리를 만든다. 최대 6회.

### 한정이름 처리

정답이 `Operators_Properties.clos_trans_tn1` 이라고 부르는데 계획은 bare 이름
`clos_trans_tn1` 을 준다. bare 로 끼우면 **프롬프트에 그 이름이 없는 것과 같다**
— 정확히 [functor-names.md](../premise/functor-names.md) 의 문제다.
정답이 쓰는 형태를 그대로 쓴다.

### 결정성

무작위는 **스텝 키(sid)로 시드된 결정적 난수**다. 같은 스텝은 언제 돌려도 같은 premise 를
뺀다 — 캐시·재개·재현이 어긋나면 안 된다.

---

## 2. gold 선언문은 어디서 오나

두 단계다.

1. **`data/cut_plans_all.jsonl` 의 `plan` 레코드** — v9 의 cut 이 쓰던 바로 그 재료다.
   `{"sid": …, "tac": …, "lem": [[이름, 명제], …], "fn": […]}`. 358,977개.
   v10 은 이것으로 **assert 를 만들지 않고 premise 를 끼운다.**
2. **`sentences.db` 폴백** (`V10_DB_FALLBACK=1`) — 계획이 없는 스텝의 **6.7%** 는
   정답이 실제 프로젝트 lemma 를 부른다(`build_cuts` 가 Coq `Check` 실패로 못 만든 것).
   그대로 두면 v10 이 가장 필요한 예제를 놓친다. 이름으로 선언문을 찾아 메운다.
   한정자가 있으면 module 컬럼으로 먼저 좁힌다(맨 이름 조회는 모호하다 — `gso` 는
   PTree/PMap/IMap/EMap 에 전부 있다).

---

## 3. v9 에서 버리던 것을 v10 은 버리지 않는다

v9 는 두 가지로 예제를 **버렸다**:

| | v9 | v10 |
|---|---|---|
| `CUT_DROP_HOPELESS` — gold 가 풀에 없어 cut 도 못 세운 스텝 | 버림 (6.7%) | **안 버림** — 끼워 넣으면 배울 수 있다 |
| `DROP_HALLUC` — 정답이 프롬프트에 없는 이름을 쓰는 스텝 | 버림 (외부참조 예제의 17.4%) | 주입 후 판정 → 대부분 통과 |
| 정규화 예외 — hopeless 스텝은 `NORMALIZE_NAMES` 를 껐다 | 껐음 | **켬** (안 그러면 그 스텝만 다른 분포가 된다) |

**v9 가 버리던 6.7% 가 v10 에서는 가장 값진 예제다** — 검색이 못 찾는 상황에서
조립하는 법을 가르치는 유일한 표본이기 때문이다.

---

## 4. 사전점검 실측

```bash
python3 scripts/v10_dryrun.py all_log/ft_qwen3b_v10_conf.yaml
```

TRAIN 200 표본 (스텝 410 — 예제 하나가 collate 를 두 번 거친다):

| 분기 | 비율 |
|---|---|
| (1) 외부 참조 없음 | **86.5%** |
| (2-a) gold 이미 보임 | **10.5%** |
| (2-b) gold 끼워 넣음 | **2.5%** |
| (2-b) 실패(포기) | 0.5% |
| 명제 아님(제외) | 1.5% |

**검증** — (2-b) 예제에서 **v10 이 공급한 lemma** 가 절단·정규화 후 프롬프트에 보이는가:
**5/5 = 100%**

> ★ 검증은 **정규화 후** 이름으로 해야 한다. `NORMALIZE_NAMES` 가 프롬프트와 정답에
> 같은 매핑을 걸어 `map_expand` → `_L0` 가 된다. 원래 이름으로 찾으면 항상 실패한다
> (실측: 이 실수로 5/11 이 "누락"으로 잘못 잡혔다).
>
> ★ 지표를 **v10 이 공급한 것**으로 한정한다. 정답은 정의·생성자(`fn` 범주)도 부르는데
> 그건 주입 대상이 아니다(§6.3). 안 가르면 범위 밖 이름 때문에 v10 이 실패한 것처럼 보인다.

### (2-b) 예제 표본

```
idx 1075136 · gold lemma ['le_S_n']                  · 정답: apply le_S_n in H.
idx 120576  · gold lemma ['omega_nz']                · 정답: have onz := omega_nz.
idx 1316288 · gold lemma ['Rmult_1_l','Rmult_1_r']   · 정답: rewrite Rmult_1_l; unfold pow; rewrite Rmult_1_r.
                                                       ← `pow` 는 함수라 제외됐다(§4.1)
```

### 4.1. 사전점검에서 잡은 버그 셋

사전점검을 돌리지 않았으면 **전부 조용히 학습에 섞였을 것들**이다.

**① `plan["lem"]` 에 명제가 아닌 것이 섞여 있다**

`pow` 의 계획값이 `R → Z → R` 였다 — **함수 타입**이다(정답은 `unfold pow` 로 쓴다).
그대로 끼우면 `Lemma pow : R → Z → R.` — **문법은 유효하지만 거짓인 선언**이
프롬프트에 들어간다. 모델에게 거짓을 가르치는 것이 최악이다.
→ `is_prop()` 로 **결론**을 보고 거른다(화살표로 쪼갠 마지막 조각이 맨 타입이름이면 제외).
실측 제외율 1.5%.

**② SQLite `LIKE` 가 대소문자를 구분하지 않는다**

`pow` 로 조회하니 **`Definition Pow : Set := Ssig Desc.`** 가 잡혔다. 엉뚱한 선언문을
gold 이름으로 끼우는 셈이다. → 이름이 **정확히** 일치하는지 확인한다.

**③ 선언문을 재조립하면 문법이 깨진다**

`Lemma le_S_n n m : S n <= S m -> n <= m.` 처럼 바인더가 콜론 앞에 오거나
`Definition … := 본문` 이면, 콜론으로 쪼개 `Lemma X : …` 로 다시 감싸는 순간 깨진다.
→ DB 에서 온 것은 **원문 그대로** 쓰고 이름만 갈아 끼운다(풀의 premise 도 원문 그대로다).

---

## 5. 설정 — **파이썬이 단일 출처다**

`src/rango_defaults.py` 의 `PROD_DEFAULTS` 에 있다. **shell 로 export 하지 않는다.**

| 키 | v10 기본 | 뜻 |
|---|---|---|
| `V10_PREMISE_INJECT` | **`1`** | 주입 ON (cut/assert 는 자동으로 꺼진다) |
| `CUT_SUBSTEP` | **`0`** | assert(cut) 안 씀 — v10 의 핵심 |
| `V10_INJECT_MAX` | `3` | 한 스텝에 끼워 넣을 gold 개수 상한 |
| `V10_DB_FALLBACK` | `1` | 계획이 없으면 sentence DB 로 선언문 조회 |
| `V10_SENTENCE_DB` | `/tmp/coq-dataset/sentences.db` | 폴백 DB 위치 |
| `V10_INJECT_STATS` | `0` | 분기 통계 출력 |

나머지는 v9 프로덕션 기본값 그대로다.

### 왜 env 가 아니라 파이썬인가

shell env 는 구조적으로 불안정하다 — `source` 를 잊거나, 다른 진입점으로 새거나,
한 스크립트가 덮어쓰면 **조용히 다른 설정으로 돈다.** v9 에서 두 번 당했다
(`RERANK_PREMISES` 가 꺼진 채 돌았고, `NORMALIZE_INFERENCE` 가 학습 경로로 샜다).
결과만 보고는 **설정이 빠진 건지 알고리즘이 나쁜 건지 구분할 수 없다** — 그게 최악이다.

`all_log/v10_env.sh` 는 아무것도 export 하지 않는다. `v9_env.sh` 를 불러
`PYTHONPATH`·`HF_HUB_OFFLINE` 같은 **환경 자체**만 세팅하고, 설정값은 주석으로
`[파이썬으로 이관]` 표시만 남긴다(v9 와 같은 관례).

```bash
# 그냥 이걸로 돈다 — env 를 안 줘도 v10 이 기본이다
python3 src/tactic_gen/train_decoder.py all_log/ft_qwen3b_v10_conf.yaml
```

`scripts/v10_dryrun.py` 는 각 값이 **env 에서 온 것인지 기본값인지** 찍는다 —
`source` 를 잊은 실행을 눈으로 잡을 수 있게:

```
■ v10 사전점검 · V10_PREMISE_INJECT=1(기본) CUT_SUBSTEP=0(기본) V10_DB_FALLBACK=1
```

### v9 재현 (절제 실험)

```bash
V10_PREMISE_INJECT=0 CUT_SUBSTEP=1 python3 src/tactic_gen/train_decoder.py <conf>
```

---

## 5.5. 모의학습 (스모크) — 동작 확인

본학습은 다른 서버에서 한다. 여기서는 **돌아가는지만** 본다.
30스텝, 나머지는 v10 conf 와 동일 (`all_log/ft_qwen3b_v10_smoke_conf.yaml`).

| | v10 | v9 대조 |
|---|---|---|
| 시간 | 1,285s | 1,257s (**+2.2%**) |
| `train_loss` | 2.793 | 2.878 |
| loss 곡선 | 4.676 → 3.879 → 2.885 → 2.004 → 1.729 → **1.585** | 4.896 → 3.886 → 2.875 → 2.118 → 1.849 → **1.642** |
| GPU | 45.9GB | 동일 |

**둘 다 정상 하강. 비용 차이 +2.2% (노이즈 수준).**
주입 때문에 프롬프트가 깨지거나 정답이 어긋나면 loss 가 안 내려간다.
30스텝 loss 차이(2.793 vs 2.878)는 **표본이 작아 의미 없다** — 같은 크기에서
같은 속도로 내려간다는 것만 확인한 것이다.

```bash
# v10
python3 src/tactic_gen/train_decoder.py all_log/ft_qwen3b_v10_smoke_conf.yaml
# v9 대조 (절제)
V10_PREMISE_INJECT=0 CUT_SUBSTEP=1 \
  python3 src/tactic_gen/train_decoder.py all_log/ft_qwen3b_v9_smoke_conf.yaml
```

---

## 6. 무엇을 기대하나 / 무엇을 확인해야 하나

**기대** — (2-b) 3.7% 는 작아 보이지만, 그 3.7% 가 **v9 가 못 배우던 바로 그 구간**이다.
그리고 (2-a) 8.7% 와 합치면 **외부 참조를 쓰는 예제의 100%** 가 "정답이 보이는" 예제가 된다.
v9 에서는 그 비율이 8.7/(8.7+3.7) = **70%** 였다.

**확인해야 할 것**

1. **분포 이동 위험** — (2-b) 예제는 "gold 가 항상 최근접에 있는" 프롬프트다.
   추론 시에는 그렇지 않다. 검색이 못 찾으면 여전히 못 푼다.
   → v10 이 고치는 것은 **"보이는데 못 고르는"** 구간이지 **"안 보이는"** 구간이 아니다.
   오라클 기준으로 상한은 A 31.5% → B 34.4% 근처다.
2. **빼낸 premise 의 손실** — 무작위로 뺀 것이 하필 필요한 것이었을 수 있다.
   실측 26회 중 문제 사례는 안 보였지만, 규모를 키우면 봐야 한다.
3. **`fn`(정의·생성자·필드) 은 안 다룬다** — 선언문이 명제가 아니라 `Lemma` 로 못 쓴다
   (§4.1 ①). `plan["fn"]` 도 주입 대상이 아니다. `DROP_HALLUC` 이 계속 그 몫을 거른다.
   정답이 `unfold pow` 처럼 정의를 부르는 경우는 v10 이 못 돕는다 —
   `[DEFINITIONS]` 주입(`INJECT_DEFS`)이 그쪽 통로다.

---

## 7. 관련 문서

- [assert 실태 — 전체 proof 비교](../v9/checkpoint25000/assert_reality.md) — 왜 assert 를 버리나
- [gold 를 줘도 실패하는 이유](../v9/checkpoint47000/what-instead.md) — 왜 "고르기"가 병목인가
- [checkpoint-47000 오라클](../v9/checkpoint47000/experiment.md) — 70% vs 13% 의 근거
- [functor-names.md](../premise/functor-names.md) — 한정이름 문제
