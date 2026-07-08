# 기법별 unique-solve & 강점 분석

> baseline = 1000-run(379/1000). **unique solve = baseline 실패 정리를 이 기법이 성공** = 그 기법의 실증 강점.

> 주의: straight-line은 sampling 변동 있음 → unique 1~2개는 변동일 수 있음. 반복/자동화형 unique가 신뢰도 높음.


| 기법 | 성공 | timeout | **unique** | unique idx | 회귀 | dir |
|---|---|---|---|---|---|---|
| `rango-portfolio` | 26/57 | 600 | **3** | 27,43,55 | 1 | 20260708-080851 |
| `rango-sauto` | 19/60 | 600 | **3** | 27,43,76 | 9 | 20260708-045704 |
| `rango-mem-wide` | 10/20 | 300 | **1** | 27 | 2 | 20260705-175027 |
| `rango-psauto` | 10/20 | 600 | **1** | 27 | 2 | 20260707-032044 |
| `rango-alignapply` | 9/20 | 300 | **1** | 27 | 3 | 20260705-162547 |
| `rango-apply-sl` | 9/20 | 300 | **1** | 27 | 3 | 20260705-203453 |
| `rango-vguided` | 9/20 | 600 | **1** | 27 | 3 | 20260707-114603 |
| `rango-mem` | 8/20 | 600 | **1** | 27 | 4 | 20260705-082853 |
| `rango-apply` | 8/20 | 300 | **1** | 27 | 4 | 20260705-154028 |
| `rango-search` | 7/20 | 600 | **1** | 27 | 5 | 20260707-021008 |
| `rango-hybrid` | 2/20 | 600 | **1** | 27 | 10 | 20260707-222538 |
| `rango-hybrid-v` | 2/20 | 600 | **1** | 27 | 10 | 20260707-231803 |
| `rango-vlog` | 19/100 | 150 | **0** | - | 15 | 20260707-083505 |
| `rango` | 10/20 | 300 | **0** | - | 1 | 20260705-143126 |
| `rango-ensemble` | 10/20 | 600 | **0** | - | 1 | 20260706-042725 |
| `rango-divsample` | 10/20 | 600 | **0** | - | 1 | 20260706-094959 |
| `rango-align` | 9/20 | 600 | **0** | - | 2 | 20260705-104531 |
| `rango-best-beam` | 8/20 | 600 | **0** | - | 3 | 20260705-072250 |
| `rango-hprobe` | 8/20 | 600 | **0** | - | 3 | 20260707-051332 |
| `no-retrieval` | 5/14 | 600 | **0** | - | 3 | 20260706-064226 |

## baseline이 못 푼 걸 푼 정리 (union) — 어떤 기법이 강점 있나

| idx | 푼 기법들 |
|---|---|
| 27 | rango-mem, rango-apply, rango-alignapply, rango-mem-wide, rango-apply-sl, rango-portfolio, rango-sauto, rango-search, rango-psauto, rango-vguided, rango-hybrid, rango-hybrid-v |
| 43 | rango-portfolio, rango-sauto |
| 55 | rango-portfolio |
| 76 | rango-sauto |

**총 4개 정리**가 baseline 실패인데 어떤 기법이 성공(=inference 기법들의 종합 강점).
