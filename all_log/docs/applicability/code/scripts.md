# 파이썬 스크립트

모두 `scripts/` 밑. 출력은 `all_log/*.jsonl` 과 `all_log/au_research/*.log`.

## 주력

### `dn_rank_eval.py` — 필터 → 랭킹 → 프롬프트

가장 중요한 측정기. 두 단계로 돈다.

```
1단  coqtop 으로 applic_filter → 채널별 이름 + 진술문 + 신호   → all_log/dn_pool.jsonl
2단  네 풀에 같은 랭커를 걸고 순위·프롬프트 진입을 잰다        → all_log/dn_rank.jsonl
       현행 / 필터후 / 합집합 / 적용가능
```

- 출력: 전체 + `gold=apply` · `gold=rewrite` · `gold=unfold` · `gold=destruct` 표
- 각 표에 `@10/@20/@50/@100` · 순위중앙 · **프롬프트 진입** 을 같이 낸다
- 지역 변수를 인자로 쓰는 스텝은 분모에서 뺀다 (`HYPS`+`GBIND`)
- 설정: `N`(정리 수) · `JOBS` · `MAX_PT`(정리당 지점)

### `applic_rank.py` — 랭커

```
python3 scripts/applic_rank.py [pool.jsonl]
```

- **applic-idf** 계산 (`build_idf`)
- 신호별 변별력 비교 — 무작위 / IDF / lgg / LCP / evar / 비트합 / 나이브베이즈
- **나이브 베이즈** 는 정리 단위 5겹 교차검증 (`train_nb` · `nb_score_fn`)
- 정보 예산 (비트) 리포트 (`budget_report`)
- tactic 별 표

### `dn_why.py` — gold 생존 진단

지점마다 `applic_check <gold>` 를 돌린다. 사슬 단계별로 어디서 끊겼는지 본다.

```
CHECK ver=r9 <이름> ap= in= rw= dnA= dnR= indexed= sides= headm= unifm= …
REAL 1/0            ← 그 자리에서 실제 tactic 이 되기는 하나
```

`REAL` 이 분모를 가른다 — 재구성한 상태가 어긋나면 정답도 안 먹고,
그건 필터의 미검출이 아니다.

### `dn_verify.py` — 실제 구문 실행

필터가 통과시킨 이름으로 **진짜 tactic 을 돌린다**.

```
1단  applic_filter 로 통과 목록 + applic_sample 로 우주 표본
2단  assert_succeeds (eapply L | apply L | rewrite L | …) 실행
```

- **정밀도**: 통과시킨 것 중 실제로 도는 비율 (거짓 양성)
- **위음성**: **거부한** 표본 중 실제로 도는 비율

### `dn_multi_eval.py` — 프로젝트를 넘어선 일반성

```
python3 scripts/dn_multi_eval.py VAL 25       # 6 프로젝트
python3 scripts/dn_multi_eval.py TEST 20      # 12 프로젝트
python3 scripts/dn_multi_eval.py CUTOFF 30    # 2 프로젝트
```

프로젝트마다 `_CoqProject` 를 읽어 로드 경로를 만든다. 컴파일된 `.vo` 가 있어야 한다.

## 랭킹·배분

| 스크립트 | 하는 일 |
|---|---|
| `channel_budget.py` | 물채우기 배분 계산. 균등/비례/합침과 비교 |
| `inject_wf.py` | 채널별 물채우기 주입기 (`waterfill` · `pick`) |
| `why_rank_drop.py` | 필터 후 @10 이 왜 떨어지나 — top10 의 stdlib·보편 비율 |
| `rw_analyze.py` | `dn_why` 결과를 tactic 별로 갈라 본다 |

## 절제 실험

| 스크립트 | 무엇을 쓸어보나 |
|---|---|
| `arrows_sweep.py` | `max_arrows` 4/8/12/20 — 한 파일에서 짝지어 |
| `dn_sweep.py` | `rigid` × `exact` 네 조합 |
| `dn_eval.py` | 전체 재현율 (rand200) |

## 모델 평가 (GPU)

| 스크립트 | 하는 일 |
|---|---|
| `next_step_eval.py` | gold prefix → 다음 한 수. `INJECT_GOLD` 로 정답 강제 주입 |
| `next_step_eval_base.py` | 주입 없는 사본 (기준선) |
| `next_step_eval_pool.py` | `POOL_FILE` 로 필터 풀 주입 |

## 구판 (r1~r2 계열)

| 스크립트 | 하는 일 |
|---|---|
| `apply_verify_eval.py` | `assert_succeeds` 배터리 (플러그인 이전) |
| `coq_search_eval.py` | Coq 내장 `SearchPattern`/`SearchRewrite` 질의 |
| `search_demo.py` | 한 지점의 질의·출력 전사 |
| `killer_query.py` | 어느 질의가 파일을 죽였나 |
| `applic_filter_eval.py` | 파이썬 판별트리 (실패한 8판본) |

## 공통 함정

- **정규식은 `\s+`** — OCaml 문자열 줄바꿈이 공백을 남긴다.
- **시동 자가검사** — 실제 출력 표본을 상수로 박고 `assert` 로 검사한다.
  ```python
  assert WHY.search(_SAMPLE_CHECK), "CHECK 정규식이 실제 출력과 어긋난다"
  ```
- **조기 중단** — 앞 10개 정리에서 0지점이면 즉시 멈춘다.
  ```python
  assert not (n >= 9 and not _first_ok), "정리 10개를 돌았는데 지점이 0"
  ```
- **`_coqtop` 헬퍼** — 자식을 프로세스 그룹으로 묶어 `killpg`.
  안 그러면 파이썬을 죽여도 `coqtop` 이 살아남는다 (실측 좀비 17개 · RSS 116GB).
  `capture_output` 은 `Popen` 이 모르니 걷어내야 한다.
