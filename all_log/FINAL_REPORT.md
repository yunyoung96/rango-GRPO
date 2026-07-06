# Rango 성능 개선 조사 — 종합 리포트 (2026-07-06)

> 목표: 단순 retrieval 기반 Rango(DeepSeek-Coder 1.3B + LoRA, BM25/TFIDF retrieval, CompCert)의 성능을 올리는 방법 찾기.
> 벤치마크: CompCert test 앞 20개(공정 비교 @600 baseline=11/20, @300 baseline=10/20). 검증은 40개로 확대.
> 방법: 로그 분석 → 논문 조사 → 창의적 구현 → 실험 → 반복. 모든 실험 자동화(overnight 드라이버, 완료마다 analysis.md).

## 한 줄 결론
**시도한 어떤 inference-time 방법도 straight-line baseline을 견고하게 넘지 못했다.** 유일한 "+1"(portfolio@20)도 40개 확대에서 −1로 뒤집혀 **노이즈로 판명**. 이는 최신 문헌의 합의("verifier가 있으면 diverse full-budget sampling이 지배적이고, 예산을 분산/변형하는 tweak은 진다")와 정확히 일치한다.

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

## 교훈
- **inference-time tweak으로는 강한 sampling baseline을 못 넘는다** (문헌+실험 일치). reranking/voting은 verifier 있으면 무용, search-order tweak은 진다.
- 개선하려면 **baseline이 원천적으로 못 푸는 정리를 새로 따야** 하는데, 시도한 도구(sauto)는 그걸 못 했다.

## 권장 (진짜 레버)
1. **built-in premise: Coq `Search`** (미완, 유망): BM25가 못 찾는 stdlib lemma를 Search로 찾아 sauto use에 먹이면 자동화형 하드코어 일부 구제 가능. coqpyt 지원 확인됨. ← **다음 시도할 것.**
2. **학습(MR2 expert iteration)**: 큰 작업 + payoff 불확실(성공증명 대부분 학습분포 내). 진짜 이득은 sauto/Search가 딴 *새* 증명을 학습셋에 넣을 때.
3. **더 큰 base 모델** 또는 **더 어려운/많은 학습 데이터 + curriculum**: 구조형 하드코어엔 이게 필요.
4. **완전 hammer(외부 ATP: z3/eprover)**: 현재 sauto-tactics만 설치. ATP 추가하면 자동화형에 더 강력.

## 산출물
- 코드: 모든 방법이 alias로 `run_thm.py`에 (rango-best-beam/mem/align/apply/apply-sl/ensemble/divsample/sauto/portfolio…). classical searcher memo, portfolio searcher, sauto 통합(coq-hammer-tactics), 공정 baseline 자동선택 등.
- 인프라: run_all(resume/description/original_success), make_report(공정 비교), overnight 드라이버, collect_successes(MR2용).
- 문서: JOURNAL(반복 저널), ROADMAP(설계), LITERATURE/LITERATURE2/RL_LITERATURE(논문조사), analysis.md(방법별).
