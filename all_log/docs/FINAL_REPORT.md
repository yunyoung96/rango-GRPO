# Rango 성능 개선 조사 — 종합 리포트 (2026-07-06)

> 목표: 단순 retrieval 기반 Rango(DeepSeek-Coder 1.3B + LoRA, BM25/TFIDF retrieval, CompCert)의 성능을 올리는 방법 찾기.
> 벤치마크: CompCert test 앞 20개(공정 비교 @600 baseline=11/20, @300 baseline=10/20). 검증은 40개로 확대.
> 방법: 로그 분석 → 논문 조사 → 창의적 구현 → 실험 → 반복. 모든 실험 자동화(overnight 드라이버, 완료마다 analysis.md).

## 한 줄 결론
**시도한 어떤 inference-time 방법도 straight-line baseline을 견고하게 넘지 못했다.** 유일한 "+1"(portfolio@20)도 40개 확대에서 −1로 뒤집혀 **노이즈로 판명**. 이는 최신 문헌의 합의("verifier가 있으면 diverse full-budget sampling이 지배적이고, 예산을 분산/변형하는 tweak은 진다")와 정확히 일치한다. 또한 **sauto/hammer가 "baseline이 못 푸는 정리를 새로 딴다"는 초기 기대(idx840)도 실측에서 거짓으로 판명**(24 run 중 idx840 성공 로그 0개, hprobe 재시도도 실패). sauto가 유일하게 기여한 idx27조차 24회 중 1회(rare-sampling). → **inference-time·hammer 레버는 소진. 진짜 레버는 학습/더 큰 모델/외부 ATP.**

## 시도한 방법과 결과 (공정 비교)

| 방법 | 아이디어 | 결과 | 순증감 |
|------|---------|------|--------|
| **baseline** rango | StraightLine 재시작(diverse sampling) | 11/20 @600, 10/20 @300 | 0 (기준) |
| rango-best-beam | best-first backtracking (M1) | 8/20 | −3 |
| rango-mem | + transposition/실패메모/cycle guard (M2) | 8/20 | −3 |
| rango-mem-wide | classical+memo, 분기16 | 10/20 @300 | +0 (동률) |
| rango-align | retrieval sibling의 aligned tactic 힌트 (M3) | 9/20 | −2 |
| rango-apply | top premise apply/exploit 강제 (M4') | 8/20 | −3 |
| rango-alignapply | align+apply 조합 | 9/20 | −1 |
| rango-apply-sl | premise 강제를 straight-line에 | 9/20 | −1 |
| rango-ensemble | retrieval + no-retrieval 모델 번갈아 (A1) | 10/20 | −1 |
| rango-divsample | 같은 모델 retrieval on/off 토글 (A1개선) | 10/20 | −1 |
| rango-sauto | retrieval-guided hammer (`sauto use:<premise>`) | 9/20 | −2 |
| **rango-portfolio** | straight∪classical (예산 70/30) | **12/20 @20** → **-1 @40** | **노이즈** |

## 헤비 레버 결과 (2026-07-07, 사용자 4→1→3→2 + 하이브리드)
inference-time 소진 후 "진짜 레버"(학습/큰모델/RL)로 전환. 진행 결과:

| 레버 | 방법 | 결과 | 순증감 |
|------|------|------|--------|
| **1. raw 6.7B 추론** | DeepSeek-Coder-6.7B-instruct(LoRA X) + Rango 프롬프트 | **0/20** | −11 |
| **4. RL value-guided** | 학습된 critic(val_acc 0.94)으로 best-first 유도 | **9/20**(신규 idx27) | −2 |
| **hybrid** | retrieval-신뢰도 게이팅 adaptive-width(사용자 아이디어) | 진행중 | ? |
| 3. expert-iter / 2. 6.7B 파인튜닝 | SFT 데이터 재생성 필요(gate) | 대기 | ? |

- **6.7B(item1)**: 로드·생성은 되나 **포맷 드리프트**(파인튜닝 안 돼서 [STATE]/환각/C++ 텍스트로 샘)로 baseline이 푸는 쉬운 정리도 실패. **용량이 아니라 포맷이 병목** → item2(파인튜닝)의 근거.
- **RL value-guided(item4)**: value 모델은 잘 학습됨(pos-neg gap 0.85). 그러나 약한 classical 탐색을 유도해선 강한 straight-line baseline 못 넘음(−2). idx27은 획득. "학습된 search-order도 diverse sampling에 진다" 재확인.
- **공통**: 탐색/순서 조정(학습 유무 무관)으로는 baseline 초과 실패. **유일 유망 레버 = 모델을 이 포맷+데이터로 파인튜닝(item 2/3).**

## 왜 실패했나 (핵심 인과)
1. **straight-line baseline이 매우 강함**: 다양한 재시작(diverse sampling)이 1.3B 모델의 사정권을 full 예산으로 잘 훑는다. 문헌(Large Language Monkeys 등): verifier 있으면 coverage@k가 지배적.
2. **탐색 기법(backtracking/memory/classical)**: 예산을 systematic 탐색에 쓰면 diverse 재시작보다 좁아져 진다. (−2~−3)
3. **retrieval 힌트(align/apply)**: 작은 효과, 오히려 회귀. 모델은 이미 retrieval을 프롬프트로 보고 있어 추가 이득 적음.
4. **A1 다양성(ensemble/divsample)**: rango가 retrieval과 *함께* 학습돼 retrieval-off attempt가 OOD로 약함 → 다양성 얻어도 절반이 약해져 회귀.
5. **retrieval-guided sauto**: sauto가 raw goal + BM25 premise로는 하드코어(부동소수/결정가능성/정수) 0개 해결. classical 기반이라 페널티도 상속. (BM25는 stdlib built-in lemma를 못 찾음 — Search 미시도.)
6. **portfolio**: straight-line phase(420s)가 baseline(600s)보다 짧아 timeout-민감 정리를 굶김. "timeout-민감 ↔ classical-findable"을 트레이드 → 세트 구성에 따라 ±. @20 +1은 운.

## 미해결 하드코어 (아무 방법도 못 푼 8개)
- **자동화형** [4,8,15,22,25]: 부동소수 반올림·정수 부등식·비트·결정가능성·어셈블리. sauto로 겨냥했으나 실패(premise 부족 or 부적절 setup).
- **구조형** [0,20,21]: 긴 시뮬레이션/불변식 증명. 1.3B 사정권 밖.

## ★정정 (2026-07-07): "sauto가 idx840을 푼다=새 capability" 주장은 미검증이었음
- 전 실험(24개 run)의 로그를 grep한 결과 **idx840을 성공시킨 로그는 어디에도 없음** (baseline 포함 전부 실패). "sauto가 idx840을 푼다"는 초기 *가설*이 검증 없이 사실처럼 저널·요약에 전파된 것. **철회한다.**
- 새 설계 rango-hprobe(값싼 sauto probe + full straight-line)로 idx840 재시도 → **역시 실패**. sauto는 idx840에 대해 유효 tactic조차 못 냄.
- **결론 강화**: sauto/hammer는 *지금까지* baseline이 못 푸는 정리를 **단 하나도 재현가능하게** 못 땄다.
- 유일한 예외: **idx27** — 24개 run 중 오직 rango-psauto phase2(classical+sauto, 트레이스에 `sauto use: bind_inversion, mmap_inversion`)만 1회 성공. 그러나 24회 중 1회라 **robust capability가 아니라 rare-sampling에 가깝다**(net은 여전히 −1: idx9,11 회귀).

## 교훈
- **inference-time tweak으로는 강한 sampling baseline을 못 넘는다** (문헌+실험 일치). reranking/voting은 verifier 있으면 무용, search-order tweak은 진다.
- 개선하려면 **baseline이 원천적으로 못 푸는 정리를 새로 따야** 하는데, 시도한 도구(sauto)는 그걸 **재현가능하게 하지 못했다**(idx840 실패, idx27은 1/24 운).

## 권장 (진짜 레버)
1. ~~built-in premise: Coq `Search`~~ **(시도함 → 실패)**: rango-search 최종 7/20(net −4). Search+sauto의 per-node coqc 오버헤드가 탐색 예산을 굶겨 오히려 크게 회귀. 자동화형 하드코어 0개 구제. **이 레버는 이 구현에선 죽음.**
2. **학습(MR2 expert iteration)**: 큰 작업 + payoff 불확실(성공증명 대부분 학습분포 내). 진짜 이득은 sauto/Search가 딴 *새* 증명을 학습셋에 넣을 때.
3. **더 큰 base 모델** 또는 **더 어려운/많은 학습 데이터 + curriculum**: 구조형 하드코어엔 이게 필요.
4. **완전 hammer(외부 ATP: z3/eprover)**: 현재 sauto-tactics만 설치. ATP 추가하면 자동화형에 더 강력.

## 산출물
- 코드: 모든 방법이 alias로 `run_thm.py`에 (rango-best-beam/mem/align/apply/apply-sl/ensemble/divsample/sauto/portfolio…). classical searcher memo, portfolio searcher, sauto 통합(coq-hammer-tactics), 공정 baseline 자동선택 등.
- 인프라: run_all(resume/description/original_success), make_report(공정 비교), overnight 드라이버, collect_successes(MR2용).
- 문서: JOURNAL(반복 저널), ROADMAP(설계), LITERATURE/LITERATURE2/RL_LITERATURE(논문조사), analysis.md(방법별).

---

# [업데이트 2026-07-12 KST] 학습 실험 완료 — 최종 종합

논문 4편 구현 + 실제 학습·평가 전부 완료. eval셋 40정리, baseline=published Rango 12/40.

## 전체 종합 @40

| 방법 | 성공 | vs base | unique | regress |
|---|---|---|---|---|
| baseline(Rango) | 12 | — | — | — |
| portfolio | 15 | +3 | 3 [2,27,55] | 0 |
| RMaxTS full | 11 | −1 | 3 | 4 |
| BFS α=1.0 | 16 | +4 | 5 | 1 |
| **GRPO(RL)** | **16** | **+4** | 4 [2,10,11,55] | **0** |
| BFS-full(DPO) | 13 | +1 | 3 | 2 |
| QED product | 11 | −1 | 2 | 3 |
| Quarry | 0 | −12 | 0 | 12 |

## 결론
1. 모델 학습이 진짜 레버 — GRPO가 straight-line 탐색만으로 최고 탐색법 동급(16), regress 0. 극소량 RL로 baseline 완전 지배.
2. 탐색 정교화(RMaxTS MCTS/reward/merge)는 무효~유해. length-norm/union만 효과.
3. BFS-full DPO(+1, 선호쌍 35개로 신호 부족), QED value(−1, 약함), Quarry(0, 1.3B 분해불가+CoqHammer 부재)는 데이터·전제 미충족.
- 상세: all_log/GRPO_RESULT.md
