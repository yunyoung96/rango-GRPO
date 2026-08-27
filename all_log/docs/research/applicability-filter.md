# 적용가능성으로 먼저 거르고 점수를 매기면 gold 가 더 실리나 — **음성 결과** (2026-08-27)

> 제안: tf-idf 로 점수를 매기기 **전에** 판별트리(discrimination tree) 류 색인으로
> "실제로 적용 가능한" premise 만 남기고, 그 안에서만 점수를 매긴다.
>
> 답: **발상은 맞다. 그런데 지금 우리 데이터로는 손해다.**
> 두 가지로 구현해 CompCert 74 스텝에 걸었고 **둘 다 top-100 진입률이 떨어졌다.**
> 이유는 자료구조가 아니라 **elaboration** 이다(§2).
>
> 문헌 쪽 배경은 [classical-lemma-retrieval.md](classical-lemma-retrieval.md) §3 —
> 거기서 지문색인을 **1순위**로 꼽았었다. 이 문서가 그 권고의 실측이다.
> 재현: `scripts/applic_filter_eval.py` · `scripts/fingerprint_filter_eval.py`

---

## 0. 결과 한 장

CompCert rand200 · `apply`/`eapply`/`rewrite`/`erewrite` 스텝 74개
(gold lemma 가 후보 풀 안에 있는 것만 — 없는 경우는 §4).

| | ① 재현율<br>(gold 생존) | ② 축소율 | ③ **gold 이 top-100 에** |
|---|---|---|---|
| 현행 (tf-idf + afh70) | — | — | **90.5%** |
| **A. 정밀 매처** (일차 단일화) | **83.8%** | 2,204 → 862 (2.6배) | **79.7%** (−10.8pp) |
| **B. 건전 지문** (머리기호, 확실할 때만) | **94.6%** | 2,204 → 1,102 (2.0배) | **89.2%** (−1.4pp) |

순위가 **오른** 스텝은 A 24건 · B 23건(≈32%, 중앙 8계단) 있다.
그런데 **gold 를 떨어뜨리는 손해가 그 이득을 넘는다.**

> **읽는 순서가 중요하다.** ①이 100% 가 아니면 ②③은 볼 필요가 없다.
> 검색 필터에서 위음성(gold 를 떨어뜨림)은 **치명적**이고 위양성(쓰레기 통과)은 싸다.
> 랭커가 어차피 뒤에서 순위를 매기기 때문이다.

---

## 1. 무엇을 어떻게 걸었나

### A. 정밀 매처 — `tactic_gen/applicable.py`

이미 있던 것이다. premise 를 `forall x…, H₁ → … → C` 로 파싱해 바인더를 메타변수로 두고
C 를 goal 결론과 **일차 단일화(one-way matching)** 한다.

```
apply     : C 가 goal 결론 전체와 매칭되나
rewrite   : C 가 `L = R` 일 때 L 이 goal 의 어떤 부분항과 매칭되나
rewrite <-: 같은 것을 R 로
```

판별트리가 **색인으로** 하는 일(유니피케이션 가능 후보만 꺼내기)을 선형탐색으로 하는 것이라
**품질은 같고 속도만 다르다.** 지금 재는 것은 품질이므로 이걸로 충분하다.

### B. 건전 지문 — 확실히 불가능할 때만 쳐낸다

A 가 gold 를 16% 떨어뜨려서, 지문색인(Schulz 2012)의 핵심인 **건전성(soundness)** 만
살린 최소판을 따로 만들었다 — 불일치가 **비유니피케이션의 필요조건**일 때만 쳐낸다.

```
apply   : goal 결론 머리기호와 lemma 결론 머리기호가 **둘 다 경직(rigid)** 이고
          다를 때만 쳐낸다. 한쪽이 변수·evar·미지면 통과.
rewrite : lemma 좌·우변 머리기호가 goal 의 **어떤 부분항 머리에도** 없을 때만 쳐낸다.
```

재현율은 83.8% → 94.6% 로 올랐지만 **여전히 100% 가 아니고**, 축소율이 2.6배 → 2.0배로
떨어져 순이득이 사라졌다.

---

## 2. ★ 왜 떨어뜨리나 — **elaboration** 때문이다

### elaboration 이 무엇인가

Coq 에서 **사람이 쓴 것**과 **커널이 보는 것**은 다르다. 그 사이를 메우는 단계가
**elaboration**(정련·구체화)이다. 다섯 가지를 한다:

| 하는 일 | 사람이 쓴 것 | elaborate 후 |
|---|---|---|
| **암묵 인자 채우기** | `nth_error nil n` | `@nth_error A (@nil A) n` |
| **notation 전개** | `a <= b` | `Z.le a b` · `le a b` (스코프에 따라) |
| **강제변환(coercion) 삽입** | `IZR z + r` | `Rplus (IZR z) r` |
| **섹션 변수 방출** | `reachable n1 n3` (섹션 안) | `reachable code make_predecessors n1 n3` |
| **evar 도입** | `eapply L` | `imm_safe ?e0 ?e1 k a ?e2` |

Coq 의 매칭은 **elaborate 된 항끼리** 일어난다. 게다가 그 위에서 **변환(conversion)** —
`delta`(정의 펼치기)·`iota`(match 계산)·`beta` — 까지 허용한다.

우리는 `sentences.db` 에 담긴 **출력된 선언문 텍스트**를 매칭한다.
즉 **elaborate 되기 전 형태끼리** 비교하는 것이라, 위 다섯 가지가 전부 불일치로 나온다.

### 실제로 떨어뜨린 사례 넷 — 전부 elaboration

```coq
(* ① 섹션 변수 — 결론에 p 가 있는데 goal 은 tp 를 쓴다 *)
Lemma in_prog_defmap: (prog_defmap p)!id = Some g -> In (id, g) (prog_defs p).
goal                :                                In (id, g) (prog_defs tp)
                                                                 ^^^^^^^^^^^^  p vs tp
   → tf-idf 0위였다. 필터가 버렸다.

(* ② 암묵/섹션 인자 — 인자 개수가 안 맞는다 *)
Lemma reachable_right: … -> reachable n1 n3.                            (2개)
goal                :       reachable make_predecessors (fun l0 => l0) n3 n1   (4개)
   → tf-idf 1위였다.

(* ③ @-표기 *)
Lemma nth_error_nil: nth_error (@nil A) idx = None.
goal              :  nth_error nil n = option_map f (nth_error nil n)
                               ^^^  @nil A vs nil
   → tf-idf 0위였다.

(* ④ evar — eapply 가 만든 ?Goal *)
Lemma imm_safe_t_imm_safe: imm_safe_t k a m -> imm_safe ge e k a m.
goal                     :                     imm_safe ?Goal ?Goal0 k a ?Goal1
   → tf-idf 0위였다.
```

**넷 다 tf-idf 가 이미 0~1위에 올려놓은 것을 필터가 버렸다.** 최악의 실패 방식이다.

### 그래서 자료구조를 바꿔도 안 된다

판별트리든 치환트리든 경로색인이든 지문색인이든, **같은 항을 색인하면 같은 결과**다.
차이는 속도와 유지비지 정확도가 아니다.

| 색인 | 간선에 두는 것 | 성질 |
|---|---|---|
| **판별트리** | 항 전위순회의 **기호 하나** (변수는 `*` 로 뭉갬) | 단순·빠름. 변수를 뭉개 위양성 많고 크기 폭발 |
| **치환트리** | **치환** 자체. 잎의 항 = 경로상 치환의 합성 | 구조를 공유해 훨씬 작음. 정적인 큰 규칙집합에 유리 |
| **경로색인** | 뿌리→잎 **경로 하나씩** | 검색 = 집합 교집합. 삽입·삭제가 쌈 |
| **지문색인** | 고정 위치 몇 곳의 자질 벡터 (얕은 trie) | 판별트리와 성능 대등(6,000.2s vs 6,082.2s)한데 유지비가 쌈 |

그리고 **속도는 우리 병목이 아니다** — 검색 25ms 대 노드 300ms.
색인 자료구조를 고르는 것은 지금 우리가 풀 문제가 아니다.

Coq 자신의 `Hint` DB `discriminated` 모드가 바로 이 색인을 하는데,
**elaborate 된 항**을 색인한다. 우리한테 없는 것이 그것이다.

---

## 3. §36 에서 기각된 것과 무엇이 다른가

[experiment.txt §36](../premise/experiment.txt) 은 `sig_applicable` 을 **점수 보너스**(커널)로
더했다가 단조 악화를 확인하고 접었다. 이번은 **하드 필터**라 다른 실험이다 —
커널은 순위를 흔들고 필터는 경쟁자를 없애므로 결과가 같을 이유가 없었다.

그런데 **결론이 같은 곳으로 수렴했다.** §36 의 문장이 그대로 성립한다:

> A 국면에는 값싼 **결정적** 술어가 없다.
> 진짜 결정적 술어는 "apply 가 실제로 성공하는가" → **Coq 을 돌려야** 안다.

이번 실측이 그 이유를 한 단계 더 밝힌다 — **Coq 을 돌려야 하는 이유가 elaboration 이다.**
`sig_applicable`(시그니처)이든 일차 단일화든 머리기호 지문이든, 전부 elaborate 전 텍스트를
보므로 같은 벽에 부딪힌다.

---

## 4. ★ 더 큰 문제가 따로 있다 — gold 이 풀에 **아예 없다**

같은 측정에서 나온 부수 숫자:

```
gold 이 후보 풀(avail_premises)에 아예 없음:  56 / 130 = 43.1%
```

**필터로도 랭킹으로도 손댈 수 없는 구간이 43%** 다. 원인은 이미 문서화돼 있다:

- `PremiseFilter` 가 구조적으로 빼는 종류 — 정의·생성자·필드·프로젝트 Ltac
- **펑터 인스턴스** — `Module N := F(A).` 로 생기는 `N.member` 는 선언이 없다
  ([functor-names.md](../premise/functor-names.md), CompCert 한정참조의 27%)
- stdlib — 풀에 안 들어온다

> 색인을 아무리 잘 만들어도 **없는 것은 못 찾는다.**
> 표적의 우선순위는 (1) 풀 구성 결손 43% → (2) 순위 개선 순이다.

**주의(측정 한계)**: "풀에 없음" 판정은 선언 키워드 정규식(`Lemma|Theorem|Definition|…`)으로
이름을 뽑아 맞춘 것이다. 정규식이 못 잡는 선언 형태가 있으면 **과대 계상**된다.
방향은 확실하나 43.1% 라는 값 자체는 상한으로 읽는 것이 안전하다.

---

## 4.5. ★ stdlib 을 풀에 넣으면 — 필터로 감당되나

"stdlib 은 검색 대상이 너무 많아서 뺀 것이니, 판별트리로 잘 거르면 넣을 수 있지 않나"
를 따로 쟀다. **TEST 409 스텝 · TRAIN 380 스텝.**

> 먼저 확인한 사실: `PROJ_THM_FILTER_CONF.coq_excludes` 가 `lib/coq/theories` 경로의
> 선언을 **종류 불문 전부** 뺀다(`THEOREM`·`LEMMA` 포함). stdlib 은 100% 제외다.
> 원저자가 왜 뺐는지는 코드에 안 적혀 있다 — 아래는 넣었을 때 무슨 일이 나는지의 실측이다.

### ① 풀이 얼마나 커지나

| | 지금 (proj-thm) | stdlib 포함 | 배수 | stdlib 비중 |
|---|---|---|---|---|
| TEST (CompCert) | 1,890 | **14,132** | **7.5배** | 80% |
| TRAIN | 684 | **6,562** | **9.5배** | 85% |

### ② gold 이 풀에 들어오나 — **들어온다**

| | 지금 | stdlib 포함 | Δ |
|---|---|---|---|
| TEST | 60.4% | **77.3%** | **+16.9pp** |
| TRAIN | 33.7% | **53.2%** | **+19.5pp** |

**gold 의 약 18% 가 stdlib 이라 지금은 원리적으로 못 찾는다.** 상금은 진짜 있다.

### ③ 그런데 **순위**로 이어지나 — 스플릿이 갈린다

gold 이 top-k 에 드는 비율(전체 스텝 기준):

| TEST (CompCert) | @10 | @50 | @100 |
|---|---|---|---|
| 지금 | 42.1% | 51.6% | 55.3% |
| stdlib 포함 | 41.8% | 52.8% | **55.7%** (+0.4pp) |
| stdlib + 필터 | 37.4% | 49.1% | 51.8% (−3.5pp) |

| TRAIN | @10 | @50 | @100 |
|---|---|---|---|
| 지금 | 18.4% | 25.8% | 27.1% |
| stdlib 포함 | 22.1% | 35.0% | **39.7%** (**+12.6pp**) |
| stdlib + 필터 | 17.6% | 26.1% | 27.6% (+0.5pp) |

**TRAIN 은 +12.6pp 로 크게 오르는데 TEST(CompCert)는 사실상 제자리다(+0.4pp).**

이유는 ①②를 겹쳐 보면 나온다 — CompCert 는 gold 이 **+16.9pp 더 도달 가능**해졌는데
순위가 안 따라온다. **stdlib 방해꾼 11,356개에 묻힌다.** CompCert 는 원래 풀이
1,890 으로 크고 프로젝트 로컬 lemma 경쟁이 이미 치열해서, 새로 들어온 stdlib gold 가
top-100 까지 못 올라온다. TRAIN 은 풀이 684 로 작아 같은 추가가 순위로 이어진다.

> **평가 대상이 CompCert 라는 점이 결정적이다.** 우리가 개선하려는 바로 그 스플릿에서
> 이득이 0 이다.

### ④ 필터는 구제하지 못한다 — **오히려 되돌린다**

| | 통과율 | gold 생존 | top-100 |
|---|---|---|---|
| TEST | 52.7% | **83.5%** | 55.7% → 51.8% |
| TRAIN | 54.0% | **64.9%** | 39.7% → 27.6% |

**필터가 남기는 것이 절반뿐인데(2배 축소) gold 은 16~35% 를 떨어뜨린다.**
축소가 약한 이유는 §2 그대로다 — 건전하게(확실할 때만) 쳐내면 조금밖에 못 쳐내고,
세게 쳐내면 elaboration 때문에 gold 이 함께 날아간다. **TRAIN 에서는 필터가
+12.6pp 이득을 통째로 지운다.**

### ⑤ 비용 — 검색이 노드 예산의 3분의 1을 먹는다

CompCert · 검색 1회(캐시 워밍 후) · n=23:

| | 중앙 | 평균 | p90 | 노드 예산 300ms 대비 |
|---|---|---|---|---|
| 지금 (proj-thm) | **10.3ms** | 23.5ms | 45.2ms | **3.4%** |
| stdlib 포함 | **114.1ms** | 147.9ms | 181.7ms | **38.0%** |

**11.1배.** 노드 하나당 300ms 인데 그중 114ms 를 검색이 먹는다.
600초 timeout 안에서 탐색할 수 있는 노드 수가 줄어든다는 뜻이고,
[worker-timeout confound](../../docs/premise/experiment.txt) 에서 봤듯 실패의 대부분이
timeout 인 상황에서 이건 직접적인 손해다.

### 결론 — 그냥 넣으면 안 된다

| | |
|---|---|
| 도달성 | **+16.9pp (TEST)** — 상금은 진짜 있다 |
| 순위 (TEST) | **+0.4pp** — 이득이 순위로 안 바뀐다 |
| 순위 (TRAIN) | +12.6pp — 여기선 되는데 평가 대상이 아니다 |
| 필터로 구제 | **안 된다** — 축소 2배뿐, gold 16~35% 손실 |
| 비용 | **11.1배**, 노드 예산의 3.4% → 38.0% |

우려가 맞았다. **stdlib 은 "너무 많아서" 가 맞고, 판별트리 계열 필터로는 못 줄인다.**
줄이려면 §5 의 전제조건(elaborate 된 항)이 먼저다.

다만 **TRAIN 의 +12.6pp 는 따로 쓸 데가 있을 수 있다** — 추론 비용이 안 걸리는
**학습 데이터 구성**에서는 stdlib 포함 풀로 gold 도달성을 올릴 수 있다.
v10 은 이미 sentence DB 폴백으로 stdlib gold 를 찾아 끼우므로
([v10/README.md §2](../v10/README.md)) 그 몫은 이미 받고 있다.

---

## 5. 그래도 하려면 — 전제조건

**elaborate 된 타입을 확보해야 한다.** 지금은 원본 `.v` 13GB 를 복구해 뒀으므로
([train-dataset-recovery.md](train-dataset-recovery.md)) 오프라인으로 Coq 을 한 번 돌려

```coq
Set Printing All.      (* notation·암묵인자·coercion 전부 펼침 *)
Check @in_prog_defmap.
```

를 lemma 마다 뽑아 두면 **색인할 항이 생긴다.** 그 뒤에야 §2 의 표에서 자료구조를 고르는
문제가 되고, 그때는 지문색인이 제격이다 — 판별트리와 성능이 대등한데 유지비가 싸고,
**불일치가 비유니피케이션의 필요조건일 때만 쳐내는 건전성**이 설계에 들어 있어
gold 를 안 떨어뜨린다.

비용과 한계를 분명히 해 둔다:

- `build_cuts` 규모의 작업이다 — 프로젝트마다 Coq 을 돌려야 한다(2,182개)
- `Set Printing All` 은 항을 길게 만든다. 프롬프트에 그대로 실을 수는 없고
  **색인 전용**으로 따로 둬야 한다
- 그래도 §4 의 43% 는 **안 풀린다**. 풀에 없는 것은 여전히 없다
- 변환(delta/iota)까지는 여전히 못 따라간다 — `Set Printing All` 은 펼쳐 주지만
  "정의를 펼치면 같아지는" 경우는 별개다

---

## 6. 결론

0. **stdlib 을 풀에 넣는 것도 CompCert 에서는 안 된다** (§4.5).
   도달성은 +16.9pp 오르는데 top-100 은 +0.4pp 뿐이고(방해꾼 11,356개에 묻힌다),
   비용은 **11.1배**(노드 예산의 3.4% → 38.0%)다. 필터로 줄이려 하면 gold 을
   16~35% 잃는다. TRAIN 에서는 +12.6pp 로 되지만 평가 대상이 아니다.
1. **발상은 맞다.** 문헌이 이 방향을 지지하고([classical-lemma-retrieval.md](classical-lemma-retrieval.md) §3),
   실제로 순위가 오르는 스텝이 32% 있다.
2. **그런데 지금 데이터로는 손해다.** 두 구현 모두 top-100 진입률이 떨어졌다
   (−10.8pp / −1.4pp). gold 를 83.8% / 94.6% 밖에 못 지킨다.
3. **원인은 자료구조가 아니라 elaboration** 이다. 출력된 텍스트끼리 맞추는 한
   판별트리·치환트리·지문색인 어느 것을 써도 같은 벽이다.
4. **전제조건은 elaborate 된 항**이고, 그건 Coq 을 프로젝트마다 돌려야 얻는다.
5. **그보다 먼저 볼 표적**은 gold 이 풀에 아예 없는 **43%** 다.

---

## 7. 재현

```bash
# A. 정밀 매처
for s in 0 1 2; do
  AF_N=60 AF_SHARD=$s AF_NSHARD=3 AF_OUT=all_log/applic_filter_s$s.jsonl \
    python3 scripts/applic_filter_eval.py &
done; wait

# B. 건전 지문
for s in 0 1 2; do
  FP_N=60 FP_SHARD=$s FP_NSHARD=3 python3 scripts/fingerprint_filter_eval.py &
done; wait
```

```bash
# C. stdlib 을 풀에 넣으면 (§4.5)
for s in 0 1 2 3; do
  SP_SPLIT=TEST SP_N=200 SP_SHARD=$s SP_NSHARD=4 python3 scripts/stdlib_pool_eval.py &
done; wait
SP_SPLIT=TRAIN SP_N=150 python3 scripts/stdlib_pool_eval.py
```

원자료: `all_log/applic_filter_s{0,1,2}.jsonl` · `all_log/sprank2_{test,train}_s*.jsonl`
로그: `all_log/au_research/{afilt,fp,spr2}_*.log`
