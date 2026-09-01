# premise 검색 — 문서 색인

> **결론부터**: 랭커 `structural` + 담기 `hybrid` + `cut` 으로
> 목표지표(프롬프트 기준 ALL)가 **TRAIN 95.6 · TEST 95.3 · VAL 96.5%**.
> 본학습에 넣는 최종 스펙은 **[final.md §10](final.md)** 하나만 보면 된다.

## 어디부터 읽나

| 목적 | 문서 |
|---|---|
| **본학습 설정만 알고 싶다** | [final.md §10](final.md) — 환경변수·성능·판정규칙 |
| **환각을 어떻게 없앴나** | [repair.md](repair.md) — 가망없는 예제 제외 + 판정 수정 |
| **이름 정규화 / rango 와의 차별점** | [normalize.md](normalize.md) — 타입·함수·lemma 정규화, 정의 주입, 역매핑 |
| **검색 랭커 이론** | [retrieval-theory.md](retrieval-theory.md) — 격자 유도 · 국면 게이트 모형 · EQ_W 를 특수해로 |
| **★ 적용가능성 기반 검색 (OCaml 플러그인)** | [../applicability/](../applicability/README.md) — 커널 단일화 필터 · 판별트리 · 적용가능 IDF · tactic 별 채널 |
| **학습이 왜 느렸나 / rango 와 뭐가 다른가** | [speed.md](speed.md) — 의존 로드 132배 최적화, 원본 대비 차이표 |
| 왜 이렇게 됐나 (처음부터) | [diagnose.md](diagnose.md) — 진단·시도·실패 |
| 학습에 어떻게 반영되나 | [details.md](details.md) — 정규화·collate 구현 디테일 |
| 프롬프트에 뭘 담나 | [packing.md](packing.md) — greedy/skip/knapsack/**hybrid** |
| 실험 원본 기록 | [experiment.txt](experiment.txt) — A/B/C/D 실측 로그 |
| 학습 타깃 설계 | [how-to-learn.txt](how-to-learn.txt) — cut 과 3단계 판정 |
| 다음에 해볼 것 | [future-idea.md](future-idea.md) |
| 머신 이관 | [vast-ai.md](vast-ai.md) |

**안 쓰기로 한 방법** — [gbdt.md](gbdt.md)(상세 설명) ·
[problem_of_gbdt.md](problem_of_gbdt.md)(왜 안 쓰나) · [contrastive.md](contrastive.md)

## 지표 정의 (모든 문서 공통)

분모는 **gold lemma 를 쓰고 그 lemma 가 후보 풀에 실제로 있는 스텝** 이다.

### ① 무엇을 "찾았다"로 볼 것인가 — 두 기준

| 기준 | 뜻 | 언제 쓰나 |
|---|---|---|
| `@k[순위]` | 검색 점수 **상위 k** 안에 있다 (토큰 예산 무관) | 랭커끼리 비교 |
| **`[프롬프트]`** | **토큰 예산 안에 살아남아 실제로 들어간다** | **모델이 실제로 볼 수 있는가** ← 실제 기준 |

둘이 크게 벌어진다. 검색은 100개를 넘기지만 896토큰 예산에는 10~22개만 들어간다
(**70~80% 가 잘린다**). 랭킹만 보면 좋아 보여도 프롬프트에 없으면 의미가 없다.

### ② 몇 개를 찾아야 하는가

| 지표 | 뜻 |
|---|---|
| `R` | 필요한 gold 중 **하나라도** |
| **`ALL`** | 필요한 gold 를 **전부** ← 실제 기준 |

tactic 이 lemma 를 2개 쓰는데 하나만 들어가면 모델은 나머지를 **지어내야** 하므로
불가능하다. lemma 를 2개 이상 쓰는 스텝이 TEST 22% · VAL 40% 라 차이가 크다.

**그래서 본문서의 대표 지표는 `ALL[프롬프트]` 다.**

### ③ 목표지표

```
A + (1-A) × C
```

`A` = 그냥 검색해서 gold 가 프롬프트에 들어간 비율.
`C` = 못 들어간 경우 `assert (P)` 로 명제를 세우고 **그 명제를 goal 삼아 재검색**했을 때 성공률.
`experiment.txt` 가 요구한 목표는 **90~95%**.

## 코드 위치

**실제 파이프라인** — 고치면 학습·추론에 반영된다

| 파일 | 역할 |
|---|---|
| `src/premise_selection/premise_client.py` `SparseClient.get_premise_scores` | 랭킹 진입점. `RETRIEVAL_MODE` 로 랭커 선택 |
| `src/tactic_gen/tier_rank.py` `structural_scores` | **확정 랭커**. RRF + 구조 신호 |
| `src/tactic_gen/tactic_data.py` `whole_number_allocate` | 담기. `PREMISE_PACK` |
| `src/tactic_gen/tactic_data.py` `collate` | 프롬프트 조립 + cut 치환 + 정규화 |
| `src/tactic_gen/cut_lookup.py` | 미리 만든 cut 조회 (학습 머신에 Coq 불필요) |
| `src/tactic_gen/normalize_names.py` | α-이름 정규화 + 역매핑 |
| `src/tactic_gen/applicable.py` | Coq 항 파서 + 단방향 유니피케이션 |
| `src/tactic_gen/assert_split.py` | cut tactic 조립 |

**도구**

| 파일 | 역할 |
|---|---|
| `scripts/build_cuts.py` | cut 사전생성 (Coq 필요) |
| `scripts/exp_abcd.py` | A/B/C/D 실험 |
| `scripts/preflight_train.py` | cut 파일 무결성 점검 |
| `scripts/verify_cut_collate.py` | collate 가 cut 을 실제로 쓰는지 |
| `scripts/preflight_all.py` | 학습 전 종합 검증 |
| `scripts/premise_packing.py` | 담기 방식 비교 |
| `scripts/probe_known_lemmas.py` | 모델이 lemma 를 아는지 프로브 |

**연구용** — 채택하지 않음

| 파일 | 역할 |
|---|---|
| `src/tactic_gen/gbdt_rank.py` · `scripts/train_ranker_gbdt.py` | GBDT 랭커 |
| `src/tactic_gen/contrastive_rank.py` | 크로스인코더 |
| `scripts/research_structural.py` | 신호 A~K 실험대 |

- [eqx.md](eqx.md) — α-동치 랭커. 포섭 선순서의 표준 몫 ⊑∩⊒ 로 유도되고 `exact` 성공 조건과 일치한다. 프로덕션 기본값(`RETRIEVAL_MODE=eqx`).

- [halluc-limits.md](halluc-limits.md) — **환각의 원리적 한계와 cut 의 위치**. 왜 프롬프트 구성으로는 못 없애나(이름의 임의성 · goal 의 손실 렌더링 · lemma 가 goal 의 함수가 아님), 분모/분자를 명시한 구성표, **출처별(gold 88.4% vs cut 11.6%)** 분류, gold 원본 환각의 **원인별 실제 사례(프롬프트 전문 + gold tactic, 토글)**, `[TYPES]`/`[DEFINITIONS]` 주입이 왜 못 잡나(`IsPullback`/`isequiv_adjointify` 완전 사례), cut 이 무엇을 풀고 무엇을 못 푸는가.

- [terms.md](terms.md) — IR 용어 전부(tf-idf · IDF · BM25 · 코사인 · **RRF** · 재현율 · McNemar). 어디까지가 IR 표준이고 어디부터가 우리 기여인지.

- [metric-retrieval.md](metric-retrieval.md) — 구조 정보만으로 하는 검색. 경로집합 Jaccard 가 **진짜 metric** 임을 보이고(Theorem 1), MinHash+LSH 로 속도를 잰다. ATP 의 path/fingerprint indexing 과 수렴.
