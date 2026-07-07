# MR-Hybrid: retrieval-신뢰도 게이팅 하이브리드 탐색 (사용자 아이디어)

> 사용자: "suffix까지 도달하는 게 오래 걸린다. retrieval 점수 낮을 땐 naive search로 탐색,
> 높을 땐 rango 기법(greedy)으로. 이렇게 hybrid하면 더 좋을 수 있다."
> 근거: `results/compcert_report/suffix_transplant_analysis.md` — rango 실패의 80건이 "prefix 발산 / suffix 공유",
> 모델이 긴 동일 suffix를 토큰단위 재생성하다 drift(valid-but-stuck). 즉 **공통 상태 도달이 병목**.

## 핵심 설계: adaptive-width best-first
각 탐색 노드에서 **모델 확신도**로 분기 width를 동적 조절:
- **확신 높음**(top tactic log-prob ≥ threshold, 분포 peaky) → **width 1 = greedy commit**(=rango 기법, 빠르게 깊이). retrieval이 좋게 매치돼 모델이 확신 → 그대로 진행. suffix 구간이 여기(확신 급상승 → 그리디 replay).
- **확신 낮음**(top log-prob 낮음/평탄) → **width K = 탐색**(best-first 분기·백트랙). prefix 발산 구간에서 대안 탐색.

### 왜 모델 확신도를 retrieval 신뢰도의 대리로 쓰나
- rango 모델은 retrieval(BM25 proof + TFIDF premise)을 **프롬프트로 보고 학습**됨. retrieval이 잘 매치되면 모델 top-prob이 뾰족(확신), 안 맞으면 평탄(불확신).
- 즉 top log-prob = "retrieval+모델이 이 스텝을 아는가"의 직접 신호. raw BM25 점수 threading보다 깔끔하고 결정에 더 직접적.
- v2(선택): 실제 BM25 top-score를 ModelResult에 실어 순수 retrieval-gating도 비교.

## 구현
- `ClassicalSearchConf`: `hybrid_conf: bool`, `conf_threshold: float`(top log-prob 기준), `hybrid_lowN`(불확신시 width).
- `search_step` 확장 루프: `top=max(score_list)`; `top≥threshold`면 argmax 1개만 push(greedy), 아니면 max_branch개 push(explore).
- alias `rango-hybrid`(ClassicalSearchConf hybrid_conf=True, use_memo=True) + 표준 rango client.
- 조합 가능: MR1 value(value_weight)와 결합 → 불확신 구간을 value로 더 잘 정렬.

## 평가
- rango-hybrid vs baseline(11/20 @600). conf_threshold sweep. 목표: suffix-drift 케이스(valid-but-stuck) 구제 → 순증.

## 정직한 리스크
- 저확신 구간은 결국 best-first(=classical, baseline에 -3)로 탐색 → 그 구간 이득이 confident-greedy 구간 손해를 넘어야.
- 단, 이 방법은 "확신 높으면 baseline과 동일(greedy)"이라 **하방이 baseline에 가깝고**, 저확신 구간에서만 탐색 추가 → 이론상 하방 방어가 이전 방법들보다 나음. 실측 필요.
