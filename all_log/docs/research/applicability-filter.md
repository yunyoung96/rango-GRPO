# 적용가능성으로 먼저 거르고 점수를 매기면 gold 가 더 실리나 — **음성 결과** (2026-08-27)

> 제안: tf-idf 로 점수를 매기기 **전에** 판별트리(discrimination tree) 류 색인으로
> "실제로 적용 가능한" premise 만 남기고, 그 안에서만 점수를 매긴다.
>
> 답: **발상은 맞다. 여덟 판본(색인 4종 포함)을 만들었지만 전부 gold 을 흘린다.**
> 최종 실측(§4.10, 양쪽 elaborate): **판별트리 45.1% / 치환트리 44.7% / 지문 FP6M 47.6%**
> — 셋 다 축소 5.7배. 깊이 0 이면 88.2% / 2.6배.
> **깨끗한 정밀도/재현율 곡선**이고, 어느 지점도 재현율 100% 가 아니다.
>
> ★ **§2 의 초기 진단은 정정됐다** — 앞선 실패의 90%는 elaboration 이 아니라
> **내 필터의 버그**(전칭 변수를 경직 상수로 취급, notation 미전개)였다(§4.7).
> `Set Printing All` 로 elaborate 색인을 실제로 만들어(CompCert 18초, §4.9)
> 버그를 고쳐 가며 세 번 다시 쟀지만, **gold 생존 87.0% · 축소 2.0배**로
> 텍스트 기준(94.6%)을 못 넘었다(§4.8). 남은 벽은 **Coq 의 tactic 의미론**과
> **goal 이 여전히 출력 형태라는 점**이다.
>
> ★★ **§4.11 이 길을 연다** — Coq 자신의 `SearchPattern`/`SearchRewrite` 를 쓰면
> 변환까지 포함해 커널이 판정한다. 질의 **35ms** · 결과 **6.9개**(현행 풀 2,100 대비 300배).
> 다만 goal 보다 **일반적인** lemma(`Rle_trans` 류)는 구체 패턴으로 안 잡히므로
> **구체→추상 사다리**로 질의해야 한다. 첫 실측 39.2%는 그 사다리 없이 1단만 쏜 결과다.
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

## 4.6. ★ stdlib gold 를 빼고 — 필터가 다룰 수 있는 스텝만 놓고 보면

§4.5 에서 stdlib gold 는 지금 풀에 아예 없어 필터로 손댈 수 없다는 것이 드러났다.
그 몫을 빼고 **필터가 실제로 다룰 수 있는 스텝만** 남기면 판정이 달라지는지 봤다.

> stdlib 판정은 **선언의 `file_path`**(`lib/coq/theories`)로 한다 — `PremiseFilter` 가
> 쓰는 것과 같은 기준이다. 이름 집합(`data/stdlib_names.json`)으로 하면 프로젝트가
> 같은 이름을 재선언한 경우와 안 갈린다.

스텝 구성: **TEST 비-stdlib 76% · stdlib 24%** / **TRAIN 비-stdlib 71% · stdlib 29%**

### ① 남는 비율 — 절반쯤이다

| | 풀 | 후보 | 필터 후 | **남음** |
|---|---|---|---|---|
| **TEST · 비-stdlib gold** | 지금 (proj-thm) | 2,081 | 1,014 | **48.7%** |
| | stdlib 포함 | 14,559 | 7,629 | 52.4% |
| **TRAIN · 비-stdlib gold** | 지금 | 1,385 | 513 | **37.1%** |
| | stdlib 포함 | 7,603 | 4,130 | 54.3% |

**2.0~2.7배 축소**다. 후보를 10배로 줄이는 그림이 아니다 —
건전하게(확실할 때만) 쳐내면 이 정도가 한계다.

### ② gold 생존 — **여전히 100% 가 아니다**

| | 지금 풀 | stdlib 포함 풀 |
|---|---|---|
| **TEST · 비-stdlib gold** | **91.2%** (218/239) | 91.2% (219/240) |
| TEST · stdlib gold | 87.5% (7/8)\* | **59.2%** (45/76) |
| **TRAIN · 비-stdlib gold** | **70.3%** (90/128) | 70.8% (102/144) |
| TRAIN · stdlib gold | — (0/0)\* | **50.0%** (29/58) |

\* 지금 풀에는 stdlib 이 없으므로 판정 대상이 거의 없다.

**stdlib gold 를 빼도 gold 을 9%(TEST) · 30%(TRAIN) 떨어뜨린다.**
stdlib gold 쪽이 훨씬 나쁜 것(59.2% / 50.0%)은 예상대로다 —
stdlib lemma 는 다형성이 강하고 암묵 인자가 많아 §2 의 elaboration 격차가 더 크다.

### ③ 떨어뜨린 비-stdlib gold — 순위가 이미 최상위였다

```
TEST                                              TRAIN
  lookup_helper_correct_1   apply    tf-idf 0위     fin_transpose_last_with_last  rewrite  0위
  bitwise_binop_shl         apply           2위     diamond                       apply    1위
  record_globdefs_sound     apply           4위     fin_transpose_last_with_last  apply    1위
  Genv.find_funct_ptr_iff   rewrite        55위     exd_not_nil                   apply    5위
  val_inject_list_lessdef   rewrite       110위     gpaco12_base                  apply    8위
```

§2 와 같은 그림이다 — **tf-idf 가 이미 0~5위에 올려놓은 것을 필터가 버린다.**
`bitwise_binop_shl` 은 [assert_reality.md](../v9/checkpoint25000/assert_reality.md) 에서
모델이 signature 를 100% 그대로 베껴 assert 했던 바로 그 lemma다.

### 결론 — stdlib 을 빼도 쓸 수 없다

| | 목표 | 실측 |
|---|---|---|
| gold 생존 | **100%** | 91.2% (TEST) · 70.3% (TRAIN) |
| 축소 | 클수록 좋음 | 2.0~2.7배 |

**"stdlib 때문에 필터가 안 되는 것"이 아니다.** stdlib gold 를 빼도 TEST 9% ·
TRAIN 30% 를 떨어뜨리고, 축소는 절반에 그친다. §2 의 진단이 그대로 유효하다 —
**출력된 텍스트로는 elaboration 격차를 못 넘는다.**

---

## 4.7. ★★ **정정** — 앞선 실패의 90%는 elaboration 이 아니라 내 구현 버그였다

§2 에서 "원인은 elaboration 이라 자료구조를 바꿔도 안 된다" 고 썼다. **과했다.**
떨어뜨린 gold 를 하나씩 분류하니 대부분 **내가 만든 필터의 버그**였다.

### 원인 분류 (TEST · 비-stdlib gold 중 떨어뜨린 21건)

| 원인 | 건수 | |
|---|---|---|
| **① 결론 머리가 전칭 변수인데 경직 상수로 봤다** | 10 | **47.6%** |
| **② 중위 notation — 진짜 머리를 못 뽑았다** | 9 | **42.9%** |
| ④ 진짜 elaboration 불일치 | 2 | 9.5% |

**90% 가 구현 버그다.**

### ① 전칭 변수 vs 경직 상수 — 단일화의 기본

단일화에서 이름은 두 종류로 갈린다.

```coq
Lemma bitwise_binop_shl:
  forall f f' x y n,        ← 여기 묶인 f, f', x, y, n = 전칭 변수
    (...) -> f' false false = false ->
    f (shl x n) (shl y n) = shl (f x y) n
    ^                              ^
    │                              └ shl = 경직 상수 (전역 Definition)
    └ f = 전칭 변수
```

| | 뜻 | 매칭 규칙 |
|---|---|---|
| **전칭 변수** (`forall` 로 묶인 것) | Coq 이 **자유롭게 골라 채울 자리**. 메타변수 | **무엇과도 매칭** |
| **경직 상수** (전역 정의·생성자) | Coq 이 **바꿀 수 없는 것** | **똑같아야 매칭** |

goal 이 `and (shl x n) (shl y n) = shl (and x y) n` 일 때 Coq 은 `f := and` 로 채운다.
**`f` 가 전칭 변수라 `and` 든 `or` 든 된다.**

판별트리가 하는 일이 정확히 이 구분이다 — **전칭 변수는 `*`(와일드카드)로 색인**하고
`*` 는 무엇과도 매칭된다. 경직 상수만 정확히 맞춰 본다.
**내 필터는 이 구분을 안 했다.** `f` 를 경직 상수로 보고 "goal 머리는 `and` 인데
lemma 머리는 `f` 니 불가능" 이라며 버렸다. tf-idf 2위였던 것을.

### ② notation — 진짜 머리는 `=` 다

```coq
Lemma record_globdefs_sound: forall dm id gd,
  (record_globdefs dm)!id = Some gd -> dm!id = Some gd.
                                       ^^^^^^^^^^^^^^^ 결론은 **등식**
```

진짜 머리는 `eq` 인데 내 코드는 첫 식별자 `dm`(전칭 변수!)을 머리로 잡았다.
`!` 는 `PTree.get` 의 notation 이다. `Set Printing All` 을 걸면 펼쳐진다:

```coq
@eq (option globdef) (@Maps.PTree.get globdef id (record_globdefs dm)) (@Some globdef gd)
^^^ 머리 = eq
```

### elaborate 색인은 실제로 만들었다

`scripts/extract_elaborated.py` — 모듈마다 `Set Printing All. Require Import M.
Search _ inside M.` 한 번. **CompCert 179/179 모듈 · 22,163 항목 · 18초.**

```coq
Int.and_shl
  : forall x y n : Int.int,
    @eq Int.int (Int.and (Int.shl x n) (Int.shl y n)) (Int.shl (Int.and x y) n)
```

앞서 떨어뜨린 것들의 머리가 전부 제대로 나온다:

| lemma | 텍스트 기준 머리 | **elaborate 기준 머리** |
|---|---|---|
| `bitwise_binop_shl` | `f` (전칭 변수) | **`eq`** |
| `record_globdefs_sound` | `dm` (전칭 변수) | **`eq`** |
| `lookup_helper_correct_1` | `globs` (전칭 변수) | **`eq`** |
| `reachable_right` | (인자 개수 불일치) | 섹션 변수가 **명시 바인더**로 방출됨 |

---

## 4.8. 고쳐서 다시 재 봤다 — **그래도 못 쓴다**

elaborate 색인으로 필터를 다시 짜고 버그를 하나씩 잡아 가며 세 번 측정했다
(TEST 247 스텝, 같은 조건).

| | gold 생존 | 축소 | 고친 것 |
|---|---|---|---|
| A 정밀 매처 (텍스트) | 83.8% | 2.6배 | — |
| B 건전 지문 (텍스트) | **94.6%** | 2.0배 | — |
| C elaborate v1 | 78.9% | 1.8배 | 바인더 추적 + notation 펼침 |
| D elaborate v2 | 77.7% | 2.4배 | `rewrite` 는 **좌·우변** 매칭 (`eq`/`iff` 자체가 아니라) |
| E elaborate v3 | **87.0%** | 2.0배 | `apply L in H`(전방추론) 면제 + 스코프별 notation 표 |

**세 번 고쳐도 텍스트 기준 B(94.6%)를 못 넘고, 축소는 어느 판본이든 ~2배다.**

### 왜 계속 새나 — 남은 실패가 말해 준다

```
떨굼 forward_simulation_star_wf   apply    요구키={eq}
떨굼 senv_preserved               apply    요구키={equiv}
떨굼 val_inject_lessdef           apply    요구키={iff}
떨굼 ZofB_range_Bconv             rewrite  요구키={sig}
```

`val_inject_lessdef` 의 결론은 `iff A B` 다. **`apply` 로 `iff` 를 쓰면 Coq 이 쪼개
준다** — goal 은 `A` 나 `B` 지 `iff` 가 아니다. 즉 "결론 머리가 goal 에 있어야 한다"는
규칙 자체가 이 경우 **틀렸다.** `equiv`(setoid), `sig`(의존합), 변환(`delta`/`iota`)도
각각 다른 규칙을 요구한다.

> **올바른 필터를 쓰는 것은 Coq 의 tactic 의미론을 다시 구현하는 일이다.**
> `apply` · `apply … in` · `rewrite` · `rewrite … in` · `eapply` 가 전부 다른 매칭
> 규칙을 쓰고, 그 위에 변환·coercion·타입클래스 해소가 얹힌다.
> Coq 자신이 `Hint` DB 색인을 **Coq 안에서** 하는 이유가 이것이다 —
> elaboration 과 conversion 에 접근할 수 있는 곳이 거기뿐이다.

### 그리고 아직 **goal 은 출력 형태**다

elaborate 한 것은 **lemma 타입뿐**이다. goal 은 증명 상태에서 오므로 여전히
`dm!id = Some gd` 같은 출력 형태다. 색인은 `@eq (option globdef) (@Maps.PTree.get …)`
인데 goal 은 `!` 표기라, 그 경계를 넘는 비교는 본질적으로 헐겁다.
제대로 하려면 **탐색 중 goal 도 `Set Printing All` 로 받아야** 한다
(라이브 Coq 세션이라 가능은 하다 — `ProofManager` 가 이미 Coq 과 말한다).
그러면 프롬프트에 실을 goal 과 색인용 goal 을 **따로** 관리해야 한다.

---

## 4.9. `Set Printing All` 추출 견적 — 생각보다 싸다

| 대상 | 규모 | 실측 |
|---|---|---|
| **CompCert** (평가 대상) | 179 모듈 | **18초** · 22,163 항목 |
| 모듈당 | — | 중앙 0.56s · 최대 1.0s |
| TEST+VAL+CUTOFF 20 프로젝트 | ~700 모듈 | ~1분 (6병렬) |

### TRAIN 은 빌드가 관문인데 — **98% 가 뚫린다**

2,182 저장소가 2023-11 커밋에 고정돼 제각기 다른 Coq 을 요구하는데 여기는 8.18 하나뿐이다.
그래서 **"일부라도"** 전략을 썼다 — `make` 를 짧은 timeout 으로 걸고, 실패하면
**의존이 적은 `.v` 부터 개별 `coqc`**. 프로젝트당 몇 파일이라도 `.vo` 가 생기면
그 모듈의 elaborate 타입은 뽑힌다(색인은 lemma 단위라 부분 성공이 그대로 값이 된다).

실측(`scripts/build_train_projects.py` · 프로젝트당 90초 상한 · 5병렬):

| | |
|---|---|
| **`.vo` 가 하나라도 생긴 프로젝트** | **98.1%** (1,087/1,108, 진행 중) |
| `make` 로 성공 | 437 |
| 개별 `coqc` 로 일부만 | 650 |
| **`.v` 커버리지** | **14.2%** (9,124 / 64,177) |

프로젝트는 거의 다 뚫리는데 **파일은 14%** 다 — 의존이 깊은 파일이 안 된다.
전량(2,182)은 **약 6시간**(5병렬, 프로젝트당 90초 상한) 규모다.

---

## 4.10. ★★★ **양쪽 elaborate + 진짜 색인 4종** — 최종 실측

앞선 다섯 판본은 전부 **깊이 0**(머리기호 하나)이었다 — 제 조사 문서 §3-3 이
Coq 의 `auto` 힌트 DB 를 두고 "최상위 기호 색인 1단계뿐, discrimination tree 아님"
이라고 적은 바로 그 수준이다. **판별트리도 지문색인도 아니었다.**

이번에 준비를 갖췄다:

| 준비물 | 방법 | 비용 |
|---|---|---|
| lemma 를 elaborate | `Set Printing All. Require Import M. Search _ inside M.` | CompCert 179모듈 **18초** · 22,163 항목 |
| **goal 을 elaborate** | 원본 `.v` 를 정리 지점까지 잘라 `idtac "@@@k". Show.` 삽입 | 정리당 **중앙 1초** · 156정리 198초 · goal 405개 |

> goal 추출은 처음에 (정리, 스텝)마다 파일을 처음부터 재컴파일해서 **건당 4~5분**이었다.
> 한 정리의 목표 스텝을 **한 파일에 몰아** 넣으니 정리당 1초가 됐다.

### 색인 4종 — 무엇이 다른가

| | 색인하는 것 | 변수 처리 |
|---|---|---|
| **지문색인** (Schulz) | 고정 위치 몇 곳의 자질 벡터 | `A`(변수) · `B`(변수 아래) · `N`(존재 불가) |
| **판별트리** | 전위순회 **문자열 전체** | `*` — 부분항 통째로 접음 |
| **치환트리** | 간선이 **치환**. 잎의 항 = 경로 치환의 합성 | 변수 **일관성** 유지 |
| 경로색인 | 뿌리→잎 경로 하나씩 | 집합 교집합 |

우리는 후보를 전수 스캔하므로 **트리 자료구조 자체는 필요 없다** — 필요한 것은
**retrieval 판정**이고, 그것만 구현했다(`src/premise_selection/fingerprint.py`).

판별트리와 치환트리의 실질 차이는 **변수 일관성** 하나다:

```
판별트리   f X X  ~  f a b   →  True    ← X 를 독립적으로 접어 위양성
치환트리   f X X  ~  f a b   →  False   ← 같은 X 는 같은 항이어야 한다
치환트리   f X X  ~  f a a   →  True
```

### 결과 — TEST 246 스텝 (양쪽 elaborate)

| 방식 | gold 생존 | 축소 | `apply` gold | `rewrite` gold |
|---|---|---|---|---|
| 깊이 0 (머리기호, 포함검사) | **88.2%** | 2.6배 | 86.1% | 90.8% |
| 지문 ε 만 | 64.2% | 4.6배 | — | — |
| 지문 1 만 | 81.3% | 2.1배 | — | — |
| 지문 1,2 | 67.9% | 2.7배 | — | — |
| 지문 1,2,3,1.1,1.2 | 59.8% | 3.3배 | — | — |
| **지문 FP6M** (ε,1,2,3,1.1,1.2) | 47.6% | **5.7배** | 39.4% | 57.8% |
| **판별트리** (전 경로) | 45.1% | 5.7배 | 35.0% | 57.8% |
| **치환트리** (변수 일관성) | 44.7% | 5.7배 | 34.3% | 57.8% |

**깨끗한 정밀도/재현율 곡선이 나온다** — 위치를 늘릴수록 축소가 커지고 gold 가 샌다.
판별트리·치환트리·FP6M 이 사실상 같은 지점(45~48% / 5.7배)에 모인다.

### ★ 이것이 말해 주는 것

**건전한(sound) 색인이라면 깊이를 늘려도 gold 를 안 잃는다.**
지문 불일치가 비유니피케이션의 **필요조건**이기 때문이다.
그런데 우리 구현은 깊이를 늘릴수록 잃는다 — **아직 건전하지 않다는 뜻**이다.

남은 불건전성의 출처(진단된 것):

| | 예 |
|---|---|
| **변환(conversion)** — `delta`/`iota`/`beta` | `apply` 는 정의를 펼쳐 가며 맞춘다. 구문 매칭은 못 따라간다 |
| **`eapply` 의 evar** | goal 에 `?Goal` 이 있으면 그 자리는 무엇이든 될 수 있다 |
| **강제변환(coercion)** | 자동 삽입돼 항 모양이 바뀐다 |
| **tactic 변종** | `apply L with x` · `apply L; auto` · `apply L in H` 가 매칭 규칙이 다르다 |

`bpow_lt`(`apply`)는 네 방식 **전부에서** 떨어졌다 — 이 잔여 격차의 대표 사례다.

**그리고 이건 고칠 수 있는 버그가 아니다.** 변환까지 따라가려면 Coq 의 커널이 필요하고,
그게 Coq 이 `Hint` DB 색인을 **Coq 안에서** 하는 이유다.

### 실제로 고친 버그들 (참고 — 매 판본마다 하나씩 나왔다)

1. **결론 머리가 전칭 변수인데 경직 상수로 취급** (§4.7 ①)
2. **중위 notation 미전개** (§4.7 ②)
3. **`rewrite` 를 결론 머리로 판정** — 좌·우변을 봐야 한다
4. **`apply L in H`(전방추론)를 결론 매칭으로 판정** — 결론이 goal 과 맞을 이유가 없다
5. **바인더 안쪽 쉼표를 결론 경계로 오인** — `forall (rs' : forall _ : preg, val) …, C` 에서
   결론이 `val) (_ : …` 같은 쓰레기가 됐다. 괄호 깊이 0 에서 잘라야 한다

각 수정이 수치를 크게 바꿨다. **필터 하나를 제대로 만드는 데 Coq 의 tactic 의미론을
그만큼 다시 구현해야 한다**는 것이 이 실험의 실질적 교훈이다.

---

## 4.11. ★★★ **Coq 안에서 하는 방법** — `SearchPattern` / `SearchRewrite`

바깥에서 만든 색인 8판본이 전부 gold 를 흘렸고, 남은 벽이 **변환(delta/iota/beta)**
이었다(§4.10). 그건 Coq 커널이 있어야 넘는다. 그런데 **Coq 이 이미 그 색인을 갖고 있다.**

```coq
SearchPattern <패턴>   결론이 패턴과 매칭되는 lemma   → `apply` 후보
SearchRewrite <항>     한 변이 그 항과 매칭되는 등식  → `rewrite` 후보
```

elaboration·변환·강제변환·타입클래스가 **전부 적용된 상태로** 판정한다.
우리가 재구현하려던 것을 Coq 이 커널을 갖고 한다.

### 비용 — 감당된다

| | |
|---|---|
| 모듈 로드(`Require`) | 468ms (한 번) |
| **질의 1회** | **35ms** |
| 질의당 결과 | 6.9개 |
| 노드 예산 300ms 대비 | **11.7%** |

지금 풀이 스텝당 ~2,100개인 것과 비교하면 **300배 축소**다.

### 규칙 ① — goal 의 **지역변수를 `_`/`?x` 로** 바꿔야 한다

```coq
✗ SearchPattern (Int.and (Int.shl x n) (Int.shl y n) = Int.shl (Int.and x y) n).
    → 아무것도 안 나옴 (지역 x y n 이 경직이라)
✓ SearchPattern (Int.and (Int.shl _ _) (Int.shl _ _) = Int.shl (Int.and _ _) _).
    → Int.and_shl
```

지역 이름(가설 목록)이 곧 lemma 의 전칭 변수가 채울 자리다.

### 규칙 ② — `_` 는 독립, `?x` 는 **일관성**을 건다

바깥에서 치환트리로 구현했던 "변수 일관성"이 **Coq 검색 문법에 이미 있다**:

```coq
SearchPattern (Z.add _ _ = Z.add _ _).
  → Z.add_comm · Z.add_assoc · Z.add_shuffle0/1/2/3 · OMEGA10~15 · … 20건 이상 (사실상 전부)

SearchPattern (Z.add ?x ?y = Z.add ?y ?x).      ← 같은 이름 = 같은 항
  → Z.add_comm                                  ★ 교환법칙 하나만

SearchPattern (Z.add ?x ?x = _).
  → Z.add_diag · Zred_factor1 · Zplus_diag_eq_mult_2   ★ 멱등형만
```

### 규칙 ③ — **화살표 접미사는 공짜다**

`apply L` 은 `L : X -> Y -> Z` 를 goal `Z` 에도 `Y -> Z` 에도 쓸 수 있다.
`SearchPattern` 이 **모든 접미사를 자동으로** 본다 — 패턴을 여러 개 만들 필요가 없다.

`L3 : forall n, P n -> Q n -> R n` 로 실측:

| 질의 패턴 | 결과 |
|---|---|
| `R _` (결론만) | **찾음** |
| `Q _ -> R _` (가설 1 + 결론) | **찾음** |
| `P _ -> Q _ -> R _` (전부) | **찾음** |
| `Q _` (중간 가설만) | 못 찾음 |
| `P _` (첫 가설만) | 못 찾음 |
| `Search concl:(R _)` | 찾음 (결론만 — 접미사 안 봄) |

`apply` 의 의미론과 정확히 일치한다.

### 규칙 ④ — ★ **추상화 사다리는 필요하다** (`SearchPattern` 은 단일화가 아니라 매칭)

`SearchPattern` 은 **lemma 결론이 패턴의 인스턴스**인 것을 찾는다.
그래서 goal 보다 **더 일반적인** lemma 는 구체 패턴으로 **절대 안 나온다**:

```coq
goal : Pos.succ a <> Pos.succ b

SearchPattern (Pos.succ ?a <> Pos.succ ?b).   →   0건
SearchPattern (?x <> ?y).                     →  77건 · not_eq_sym ★ · Plt_ne ★
```

`not_eq_sym : x <> y -> y <> x` 의 결론 `y <> x` 는 `Pos.succ ?a <> Pos.succ ?b` 의
인스턴스가 아니다. **구조적 lemma**(`not_eq_sym`·`Rle_trans`·`eq_sym`·`f_equal`·`proj1`)가
통째로 이 부류다 — 그리고 오라클 실험에서 `모호` 칸의 상위를 차지하던 바로 그것들이다
([checkpoint47000/experiment.md §4](../v9/checkpoint47000/experiment.md)).

> 조사 문서 §3-3 이 적은 **"결론 색인의 구조적 한계"** 와 같은 뿌리다 —
> 전제의 변수가 결론에 안 나오는 lemma 는 결론만 보는 색인이 못 잡는다.

**→ goal 하나당 구체→추상 **사다리**로 몇 개를 질의하고 합집합을 쓴다:**

```
① goal 전체            (지역 → ?x)      구체 lemma
② 잎 부분항을 ?x 로                      한 단계 일반
③ 머리만 남기고                          더 일반
④ 관계만 (?x <> ?y)                      구조적 lemma
```

질의당 35ms 이므로 4단이면 140ms — 노드 예산 300ms 안에 든다.

### 첫 실측 — 아직 나쁘다. **배선이 틀렸다**

97 질의지점(`scripts/coq_search_eval.py`, 지역변수를 전부 `_` 로만 바꾼 1단 질의):

| | gold 적중 | 후보 수 |
|---|---|---|
| `apply` | 26/59 = 44.1% | 644.8개 |
| `rewrite` | 12/38 = 31.6% | 402.1개 |
| **전체** | **39.2%** | **549.7개** |

**두 증상이 규칙 ②④ 로 정확히 설명된다:**

- 후보 550개 → `_` 가 서로 독립이라 패턴이 헐겁다. `?x` 로 바꾸면 위 `Z.add` 예처럼 급감한다.
- 후보 **0개**로 놓친 것이 다수(`not_eq_sym`·`Plt_ne`·`range_split_2`·`compare_refl`)
  → 전부 **goal 보다 일반적인 lemma** 다. 사다리 없이 1단만 질의해서 못 잡았다.

즉 이 수치는 **Coq 검색의 한계가 아니라 내 패턴 생성의 한계**다. 고칠 것:

| | |
|---|---|
| `_` → `?x` | 같은 지역변수는 같은 이름으로 |
| **추상화 사다리** | 구체→추상 4단 질의 후 합집합 |
| `apply` 변종 | `eapply` · `apply … with` · `apply … in H` 별로 질의를 달리 |

---

## 4.12. ★★★ **`?x` + 사다리로 고쳐 재측정** — CompCert 집중

§4.11 의 첫 실측(39.2%)이 배선 탓이었으므로 규칙 ②④ 를 적용해 다시 만들었다.
구현: `src/premise_selection/coq_query.py` · 평가 `scripts/coq_search_eval.py`

### 궤적 — 고칠 때마다 올랐다

| 판본 | gold 복원 | 후보/지점 | 고친 것 |
|---|---|---|---|
| v1 (1단 · `_`) | 39.2% | 550 | — |
| v2 (사다리 3단) | 54.3% | 2,062 | 구체→추상 사다리 |
| v3 (지역이름 수정) | 55.9% | 1,302 | **가설 접힘줄 오인** 수정 |
| v4 (+전방추론) | 51.6% | 1,970 | 가설 질의 추가 · rewrite 대상 선택 **역효과** |
| **v5 (기호결합)** | **60.3%** | 1,989 | `rewrite` 를 **기호 결합 질의**로 |

`rewrite` 만 보면 27.6% → **49.5%** 로 크게 올랐다.

### 고친 버그 넷 (전부 실측으로 드러남)

**① 가설이 여러 줄로 접히면 연속행 이름을 전부 지역으로 오인**

```
'H: m'                                     → H                       (정상)
'|= range sp 0 (fe_stack_data fe) **'      → range, sp, fe_stack_data ★오인
'   range sp (…) (fe_size fe) ** P'        → range, fe_size …        ★오인
```

그러면 패턴이 `?m |= ?range ?sp …` 가 되어 **6,667건**을 긁고 gold 는 못 잡는다.
→ **선언 형태(`이름[, 이름…] : 타입`)로 시작하는 줄만** 본다.

**② 바깥 괄호와 `%Z`·`%R` 스코프를 안 벗겼다**

출력형 goal 은 `(0 <= m)%Z` 처럼 통째로 괄호+스코프인 경우가 많다. 그대로 두면
최상위 중위 연산이 깊이 1 에 있어 안 잡히고 **사다리 2·3단이 아예 안 만들어진다**
(`후보 0` 의 주범).

**③ 이미 evar 인 것을 다시 `?` 로 감쌌다** — `add_needs rl ?nvl ne` → `??nvl` 로 패턴 파손.

**④ `Int.testbit` 을 `Int` + `testbit` 로 쪼갬** — 한정이름 정규식이 없어
`Search Int (?a = ?b)` 같은 무의미 질의가 됐다.

### ★ `rewrite` 는 **기호 결합**이 낫다

`SearchRewrite <부분항>` 은 **정확한 redex** 를 알아야 하는데, 출력형 goal 에서
redex 를 짚는 것은 추측이다. 대신 goal 이 **어떤 기호를 쓰는가**로 좁힌다:

```coq
SearchRewrite (Int.testbit (Int.and ?x ?y) ?i).   →  1건 · Int.bits_and ★
Search Int.testbit Int.and (?a = ?b).             →  1건 · Int.bits_and ★
SearchRewrite (Int.and ?x ?y).                    → 25건 · Int.bits_and 없음
```

기호가 많을수록 좁고 적을수록 넓다 — **그대로 사다리가 된다.**

### ★★ tactic 형태별 복원율 (CompCert 252 지점)

| 형태 | 지점 | **복원율** | 후보 |
|---|---|---|---|
| `eapply` (연쇄/수식) | 24 | **91.7%** | 2,104 |
| `apply` (연쇄/수식) | 21 | **71.4%** | 2,459 |
| `apply … in H` | 5 | 60.0% | 4,730 |
| **`apply` (순수)** | 54 | **59.3%** | 2,300 |
| `apply … with` | 19 | 57.9% | 1,817 |
| `rewrite` (연쇄/수식) | 18 | 55.6% | 1,098 |
| **`rewrite` (순수)** | 52 | **53.8%** | 1,209 |
| `rewrite … in H` | 12 | **25.0%** | 888 |
| `eapply … with` · `eapply`(순수) · `erewrite` | 5 | 100% | — |
| *지역가설* (`apply Hd` — **검색 대상 아님**) | 42 | 54.8% | 2,911 |
| **전체** | **252** | **60.3%** | 1,989 |
| **전체 (지역가설 제외)** | 210 | **61.4%** | — |

**읽는 법:**

- **`rewrite … in H` 25.0%** 가 최악이다 — 전방추론이라 lemma 결론이 goal 과 맞을
  이유가 없는데, 가설 질의만으로는 부족하다.
- **`apply`/`rewrite` 순수형이 54~59%** 로 중간이다. 이 둘이 표본의 42% 를 차지한다.
- `eapply` 계열이 높은 것은 표본이 작아서다(24·3·1 지점).

### 남은 40% 의 원인

| | | |
|---|---|---|
| ⑤ **후보는 있는데 gold 만 없음** | 41.0% | `sep_swap23`(후보 14,473) · `Rmult_le_compat_r`(559) |
| ④ **후보 0** | 19.0% | `ZMap.gi` · `dec_eq_true` — 패턴이 아직 안 맞음 |
| ⓪ **gold 이 지역 가설** | 19.0% | `apply Hd` · `rewrite P` — **검색으로 찾을 대상이 아니다** |
| ① `… in H` | 11.0% | 전방추론 |
| ③ `… with` | 8.0% | 인자 지정 |
| ② `eapply` | 2.0% | evar |

**⓪ 는 애초에 대상이 아니다** — `apply Hd` 의 `Hd` 는 그 증명의 지역 가설이라
전역 검색에 있을 수가 없다. 이 19% 를 빼면 실질 상한은 그만큼 올라간다.

**⑤ 가 최대 잔여분(41%)** 이다. `sep_swap23` 은 후보가 14,473개나 나왔는데도
gold 가 없다 — 질의가 **넓기만 하고 엉뚱한 방향**이라는 뜻이다.
`sep_swap23 : P ** Q ** R ** S = P ** R ** Q ** S` 같은 프로젝트 고유 notation(`**`)
lemma 는 `Search` 의 기호 결합으로는 잘 안 좁혀진다.

> **왜 100% 가 아닌가** — Coq 이 "그대로 찾아 주는" 것은 맞지만, **무엇을 물을지**를
> 우리가 정해야 한다. goal 은 출력 형태이고, 거기서 (a) 무엇이 지역이고 (b) 어디가
> redex 이고 (c) 어느 추상화 단계가 맞는지를 **추측**해야 한다. 그 추측이 틀리면
> Coq 은 정확히 "그 잘못된 질문"에 정확히 답한다.
>
> 이건 §4.10 의 벽(변환)과는 **다른 종류**다 — 그건 원리적이었고 이건 배선이다.
> 실제로 v1 39.2% → v5 60.3% 로 배선을 고칠 때마다 올랐고, 아직 위 목록이 남아 있다.

---

## 4.13. ★★★ 계속 올렸다 — CompCert **39.2% → 74.0%**

### 궤적

| 판본 | 전체 | `apply` | `rewrite` | 고친 것 |
|---|---|---|---|---|
| v1 | 39.2% | 44.1% | 31.6% | 1단 질의 · `_` |
| v2 | 54.3% | — | — | 구체→추상 사다리 |
| v3 | 55.9% | — | — | **가설 접힘줄 오인** 수정 |
| v4 | 51.6% | 68.2% | 27.6% | 전방추론 추가 · rewrite 대상 선택 역효과 |
| v5 | 60.3% | 67.8% | 49.5% | `rewrite` → **기호 결합 질의** |
| v6 | 62.3% | 67.6% | 54.5% | **관계 무제약** + notation 문자열 |
| v7 | 69.5% | **80.1%** | 54.0% | **스코프 보존** |
| **v8** | **74.0%** | 80.0% | **64.9%** | **elaborate goal 로 기호 추출** |

### tactic 형태별 (v8 · 242 지점)

| 형태 | 지점 | 복원율 |
|---|---|---|
| `eapply` | 25 | **92.0%** |
| `apply` | 74 | **81.1%** |
| `apply … with` | 18 | 77.8% |
| `rewrite` | 66 | **71.2%** |
| `apply … in H` | 5 | 60.0% |
| `rewrite … in H` | 11 | **45.5%** |
| `eapply … with` · `erewrite` | 4 | 100% |
| *지역가설* (`apply Hd`) | 39 | *검색 대상 아님* |
| **전체** | **242** | **74.0%** |
| **지역가설 제외** | 203 | **76.8%** |

### v5~v8 에서 고친 것

**⑤ 의 정체 — 관계를 `=` 로 못 박으면 안 된다** (v6)

```coq
sep_swap23 : massert_eqv (sepconj P (sepconj Q (sepconj R S))) (…)
```

`rewrite sep_swap23` 은 **setoid 재작성**이라 결론이 등식이 아니다.
`Search … (?a = ?b)` 로는 **원리적으로** 못 찾는다 — 놓친 것의 41% 를 차지하던 부류다.
→ 관계 무제약 질의를 **먼저** 쓴다. `Search "**"` 로 notation 문자열도 직접 묻는다.

**★ 스코프를 벗기면 뜻이 바뀐다** (v7 — 가장 큰 도약, +7.2pp)

```coq
(0 <= ?x)%R   →  Rle (IZR Z0) ?x      ← 맞다
(0 <= ?x)     →  Nat.le 0 ?x          ← nat 의 0! Rle 계열을 하나도 못 찾는다
```

`bpow_ge_0`·`Rmult_le_compat_r`·`le_F2R` 등 Flocq/Reals 계열이 통째로 누락되고 있었다.
`apply` 가 67.6% → **80.1%** 로 뛴 것이 이 한 줄이다.

**★ notation 이 진짜 이름을 가린다 — elaborate goal 로 뽑는다** (v8, +4.5pp)

출력형 goal 은 `P ** Q` 라고 찍지만 실제 상수는 `sepconj` 다. 기호로 좁히는 질의에서
그 차이가 그대로 복원율이 된다. §4.10 에서 만든 **elaborate goal**
(`scripts/elab_goals_batch.py` · 정리당 1초)을 여기서 다시 쓴다.
`rewrite` 가 54.0% → **64.9%**, 순수형은 **71.2%**.

### `rewrite` 가 `apply` 보다 어려운 이유 — **redex 를 짚어야 한다**

**redex**(REDucible EXpression) = 재작성 규칙이 실제로 물리는 부분항.

```coq
rewrite Int.and_shl.
  규칙  Int.and (Int.shl x n) (Int.shl y n) = Int.shl (Int.and x y) n
        └────────── 좌변(lhs) ──────────┘
  goal  … testbit (Int.and (Int.shl a m) (Int.shl b m)) i …
                  └────────── 이것이 redex ──────────┘
```

`SearchRewrite t` 는 **t 를 곧 redex 로 간주**한다. goal 전체를 넣으면 안 되고 정확한
부분항을 짚어야 하는데, 출력형 goal 에서 그건 **추측**이다:

```
rewrite ZMap.gi     → 후보 0        redex 가 `if … then … else` 깊숙이 있다
rewrite sep_swap23  → 후보 14,606 있는데 gold 없음  (`**`=sepconj 를 notation 이 가림)
```

**`SearchRewrite` 만으로 모든 부분항 패턴을 볼 수는 없다.** 그래서 기호 결합 질의로
우회했고(v5), elaborate goal 로 기호를 정확히 뽑아(v8) 71.2% 까지 왔다.

### 참고 — 부분항 패턴을 한 번에 푸는 고전 알고리즘

"모든 부분항 × 모든 규칙"은 **트리 패턴 매칭**의 고전 문제다:

| | |
|---|---|
| **Hoffmann–O'Donnell** (JACM 1982) | **상향식 트리 패턴 매칭**. 규칙집합을 전처리하면 대상 항을 **한 번 상향 순회**하며 모든 위치에 매칭 규칙을 라벨링 — 전처리 후 **O(\|t\|)**. 문자열의 Aho–Corasick 에 해당 |
| **Chase 알고리즘** | 위 표 압축 (표 폭발 해결) |
| **판별망**(discrimination net) | Maude·ELAN 표준. 부분항마다 조회 — O(\|t\| × lookup) |
| **지문색인 backward 모드** | 조회를 싸게. Schulz 논문의 backward rewriting **58배**가 이것 |

핵심은 **부분항마다 따로 조회하지 않고 규칙 색인을 대상 항과 동시에 걸어간다**는 것이다.

**그런데 우리가 직접 못 쓴다** — 매칭을 Coq 바깥에서 재구현해야 하고, 그건 §4.10 에서
8판본으로 실패했다(변환을 못 따라감). 그리고 **Coq 자신도 안 쓴다** —
`autorewrite` 는 색인 없이 베이스 전체를 소진적으로 반복한다(§3-3).

### 남은 26% (47건, 지역가설 제외)

| | | |
|---|---|---|
| ⑤ 후보는 있는데 gold 없음 | 59.6% | `sep_swap23`(14,606) · `Zmult_1_r`(5,706) · `Raw.In_node_iff`(7) |
| ④ 후보 0 | 40.4% | `ZMap.gi` · `dec_eq_true` · `Z.shiftl_mul_pow2` |

`Zmult_1_r` 은 `rewrite <- (Zmult_1_r …)` 로 **역방향+항 적용**이고,
`Z.shiftl_mul_pow2` 는 `rewrite … by now apply …` 로 **부수 goal 이 딸린** 형태다.
남은 것은 대체로 **tactic 변종**이고, 각각 질의 형태를 달리해야 한다.

---

## 4.14. ★ 질의를 어떻게 만드나 — 사다리와 부분항의 실제

goal: `Int.testbit (Int.and (Int.shl x n) (Int.shl y n)) i = Int.testbit (Int.shl (Int.and x y) n) i`

**【사다리】 `ladder()` — goal 전체를 구체→추상으로**

```
L0: Int.testbit (Int.and (Int.shl ?x ?n) (Int.shl ?y ?n)) ?i = Int.testbit (Int.shl (Int.and ?x ?y) ?n) ?i
L1: (Int.testbit ?a0 ?a1) = (Int.testbit ?b0 ?b1)     ← 각 변의 **인자**만 ? (머리 유지)
L2: ?zl = ?zr                                          ← 변을 통째로 ? (관계만)
```

최상위 중위 연산을 **괄호 깊이 0** 에서 찾아 좌·우변으로 쪼갠 뒤 단계적으로 흐린다.

**【부분항】 — 출력형에서 뽑으면 셋을 놓친다**

처음에는 출력된 goal 문자열의 `(`…`)` 짝을 모아 썼다. 세 가지가 새어 나갔다:

| | |
|---|---|
| 괄호 안 친 최상위 적용 | `Int.and x y` 는 조각이 안 나온다 |
| **notation 이 가린 구조** | `P ** Q` 는 괄호가 없다 — 실은 `sepconj P Q` |
| `if … then … else` 안쪽 | `rewrite ZMap.gi` 가 후보 0 이던 원인 |

→ **elaborate 된 goal 에서 뽑는다**(`elab_subterms`). 완전히 괄호가 쳐진 적용이라 셋이 다 풀린다:

```
(eq bool (Int.testbit (Int.and (Int.shl x n) (Int.shl y n)) i) (Int.testbit …))
(eq ?z0 ?z1 ?z2)
(Int.testbit (Int.and (Int.shl x n) (Int.shl y n)) i)
(Int.testbit ?z0 ?z1)
(Int.and (Int.shl x n) (Int.shl y n))
(Int.and ?z0 ?z1)
```

적용 노드마다 **구체형 + 인자를 흐린 1단 추상**을 같이 낸다(redex 는 대개 인자가 구체적이지 않다).
`rewrite` 가 64.9% → **68.0%**.

**【합집합】** 한 지점의 질의를 **전부 합친다** — 사다리 + 부분항 + 기호결합 +
notation 문자열 + elaborate 기호/부분항 + 가설질의. **하나라도 잡으면 살린다.**
그래서 §4.12 의 사다리 표가 **누적** 곡선이다.

> 100% 가 안 되는 것은 "필터가 죽여서"가 아니라 **어떤 질의도 그 lemma 를 안 돌려줘서**다 —
> 남은 실패의 40%가 **후보 0**(합집합이 공집합)이었다.

---

## 4.15. ★★ 필터링 비율 — 지금은 **필터가 아니라 확장**이다

복원율은 **gold lemma 가 후보 집합에 들어 있는 비율**(recall)이다. 후보 규모는 이렇다
(CompCert 120 지점 · 선언 이름 기준):

| | 후보 수 | **gold 포함** |
|---|---|---|
| ① 현행 rango 풀 | 1,333 | 51.7% |
| ② **Coq Search 결과** | 3,077 | **69.2%** |
| ③ **①∩②** (필터로 쓸 때) | **321** | 35.8% |
| ④ ①∪② (둘 다 쓸 때) | 4,090 | **85.0%** |

**읽는 법 — 세 가지가 한꺼번에 보인다:**

1. **② 가 ① 보다 넓고 더 잘 찾는다.** Coq Search 는 **전역 환경 전체**에서 뽑으므로
   rango 풀(프로젝트 한정)보다 크다. 그런데도 gold 포함이 51.7% → **69.2%** 다.
   즉 지금 이것은 **축소 도구가 아니라 도달성 도구**다.
2. **③ 필터로 쓰면 4.2배 축소되지만 gold 를 31% 잃는다**(51.7% → 35.8%).
   ② 가 ① 밖의 것을 많이 찾기 때문이다 — 교집합은 양쪽 다 있는 것만 남긴다.
3. **④ 합치면 85.0%** 다. 후보는 4,090 으로 늘지만 **도달성이 가장 높다.**

> **결론: 필터가 아니라 ①∪② 로 써야 한다.** 랭커가 순위를 매기는 구조이므로
> 후보가 늘어나는 비용보다 **gold 가 아예 없는 것**(현행 48.3%)이 훨씬 비싸다.
> [checkpoint47000/experiment.md](../v9/checkpoint47000/experiment.md) 가 보인
> "커버리지 개선만 값을 낸다(+6.2pp)" 와 정확히 같은 방향이다.

### 최종 궤적 (CompCert 242 지점)

| 판본 | 전체 | `apply` | `rewrite` |
|---|---|---|---|
| v1 | 39.2% | 44.1% | 31.6% |
| v5 | 60.3% | 67.8% | 49.5% |
| v7 (스코프) | 69.5% | **80.1%** | 54.0% |
| v8 (elaborate 기호) | 74.0% | 80.0% | 64.9% |
| **v10 (elaborate 부분항)** | **75.2%** | 80.0% | **68.0%** |

---

## 4.16. Coq 안쪽을 더 파려면 — `Print Hint` 와 OCaml 플러그인

**`Print Hint`** 는 현재 goal 에 적용 가능한 힌트를 Coq **자기 판별망**으로 계산해 준다.
등록된 힌트만 보므로, `data/elab_compcert.jsonl` 의 이름을 `Hint Resolve … : rango.` 로
전부 등록하고 물어봤다:

```
263개 등록 → 적용가능 133개 = 2.0배 축소   (Int.and_shl 은 ★ 들어 있다)
```

**2.0배뿐이다.** `Print Hint` 는 얕은 필터다 — 깊은 판별은 `auto` 의 **탐색 안쪽**에서
일어나고 밖으로 안 나온다. §4.10 에서 내가 손으로 만든 것들과 같은 2배 천장인 것이
우연이 아니다.

더 파려면:

| 방법 | 접근하는 것 |
|---|---|
| **Coq 플러그인 (OCaml)** | `Hints.Hint_db` · `Unification.w_unify` 를 직접 호출 — **커널 단일화 그대로**. 후보마다 `apply` 성공 여부를 실제로 시험할 수도 있다(§36 이 말한 "진짜 결정적 술어") |
| SerAPI / coq-lsp 확장 | 프로토콜에 질의 추가 |
| `Print Hint` | 얕은 필터 (2.0배) |
| `SearchPattern` / `Search` | 지금 쓰는 것 (75.2%) |

**비용이 관건이다** — 후보 2,100개에 `w_unify` 를 다 돌리면 노드 예산 300ms 를
넘길 수 있다. 다만 Coq 이 `auto` 에서 이미 그 일을 하므로 실측해 봐야 안다.

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

0. **stdlib gold 를 빼고 봐도 못 쓴다** (§4.6) — gold 생존 91.2%(TEST) · 70.3%(TRAIN),
   축소는 2.0~2.7배. 떨어뜨리는 것이 tf-idf 0~5위였던 것들이다.
   즉 "stdlib 때문에 안 되는 것"이 아니다.
0'. **stdlib 을 풀에 넣는 것도 CompCert 에서는 안 된다** (§4.5).
   도달성은 +16.9pp 오르는데 top-100 은 +0.4pp 뿐이고(방해꾼 11,356개에 묻힌다),
   비용은 **11.1배**(노드 예산의 3.4% → 38.0%)다. 필터로 줄이려 하면 gold 을
   16~35% 잃는다. TRAIN 에서는 +12.6pp 로 되지만 평가 대상이 아니다.
1. **발상은 맞다.** 문헌이 이 방향을 지지하고([classical-lemma-retrieval.md](classical-lemma-retrieval.md) §3),
   실제로 순위가 오르는 스텝이 32% 있다.
2. **다섯 판본 전부 못 쓴다.** 최선이 gold 생존 87.0% · 축소 2.0배다(§4.8).
   축소가 ~2배에 묶이는 것은 판본과 무관하다 — 건전하게 쳐내면 그 정도가 한계다.
3. **초기 진단(§2)은 틀렸다.** 실패의 90%는 elaboration 이 아니라 **내 구현 버그**였다
   (전칭 변수를 경직 상수로 취급 47.6% · notation 미전개 42.9%, §4.7).
4. **elaborate 색인은 싸게 만들어진다** — CompCert 179모듈 18초(§4.9).
   TRAIN 도 "일부라도" 전략으로 **프로젝트 98.1%** 가 뚫린다(파일은 14.2%).
5. **그런데 색인을 만들어도 안 됐다.** 남은 벽 둘:
   · **Coq 의 tactic 의미론** — `apply`/`apply … in`/`rewrite`/`eapply` 가 매칭 규칙이
     전부 다르고, `iff` 결론을 `apply` 하면 Coq 이 쪼갠다. 올바른 필터 = Coq 재구현.
   · **goal 이 여전히 출력 형태** — lemma 만 elaborate 했다. 제대로 하려면 탐색 중
     goal 도 `Set Printing All` 로 받아야 하고, 프롬프트용 goal 과 색인용 goal 을
     따로 관리해야 한다.
6. **그보다 먼저 볼 표적**은 gold 이 풀에 아예 없는 **43%** 다(§4).

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

# D. stdlib gold 를 빼고 (§4.6)
for s in 0 1 2 3; do
  FN_SPLIT=TEST FN_N=200 FN_SHARD=$s FN_NSHARD=4 python3 scripts/filter_nonstdlib_eval.py &
done; wait
```

원자료: `all_log/applic_filter_s{0,1,2}.jsonl` · `all_log/sprank2_{test,train}_s*.jsonl`
로그: `all_log/au_research/{afilt,fp,spr2}_*.log`
