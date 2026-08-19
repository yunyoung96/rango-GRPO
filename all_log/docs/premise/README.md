# premise 검색 — 문서 색인

> **결론부터**: 랭커 `structural` + 담기 `hybrid` + `cut` 으로
> 목표지표(프롬프트 기준 ALL)가 **TRAIN 95.6 · TEST 95.3 · VAL 96.5%**.
> 본학습에 넣는 최종 스펙은 **[final.md §10](final.md)** 하나만 보면 된다.

## 어디부터 읽나

| 목적 | 문서 |
|---|---|
| **본학습 설정만 알고 싶다** | [final.md §10](final.md) — 환경변수·성능·판정규칙 |
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
