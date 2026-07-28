# SFT→bottom-up-subgoal-GRPO — 앞으로 해야 할 실험 목록

작성 2026-07-25. 관련: [[sft-subgoal-grpo-naming]], `SUBGOAL_PAPER_ASSESSMENT.md`, `LEAF_SUBGOAL_METHOD.md`.
현재: 본 실험 진행 중(s0 롤아웃 ~245/300, 학습셋 root ~35%). held-out 1191(비교 A) 미확정.

우선순위 = 논문화에 필요한 순. **P0(지금)** → **P1(핵심, 없으면 논문 안 됨)** → **P2(강화)** → **P3(탑티어)**.

---

## P0. 현재 실행 완주 (진행 중)
- [ ] s0 롤아웃 완주(300) → **비교 B 확정**(root 롤아웃 성공률 vs GRPO 22% / SFT→GRPO 26%)
- [ ] s0 GRPO 학습 → 최종 모델(rango-grpo-subgoal-bs2-s0)
- [ ] **평가 A**: rand200@600s + 1191@120s → vs baseline 322 / GRPO 328 / **SFT→GRPO 338**
- **관문**: held-out 1191이 338을 노이즈 넘게 이기는가? 이게 안 되면 아래는 무의미.

---

## P0.5 GRPO 최적화 재실행 (§9 로그분석 발) — 싸고 근거 확실, 우선
로그 실측 병목: **낭비 63~73%**(dead+all-solved) · **entropy 0.11**(collapse) · **std-정규화 편향**. 장치는 대부분 이미 코드에 있고 이번 subgoal run에서 안 켜졌을 뿐 → 거의 무-구현으로 재실행.
- [ ] **dynamic sampling ON** (`dyn_resample>0`, 롤아웃 수집 시) — mixed 그룹 찰 때까지 이어 롤아웃 → 배치 낭비 제거. (DAPO)
- [ ] **clip-higher ON** (`--clip_eps_high 0.28`, gtrain) — 저엔트로피 collapse 완화(낮은 확률 tactic이 자라게). (DAPO)
- [ ] **RLOO baseline**(std-정규화 off) — 무편향 advantage. (Dr.GRPO, §6 T2 / 실험 E3)
- [ ] (무료) **epoch 2→1** — off-policy drift(max_ρ 4.1→) 축소.
- **정직한 주의**: dynamic sampling은 **신호를 만들지 못함**(0/6 dead는 리샘플해도 skip) → 탐색강화(clip-higher)·dense 보상과 **함께** 켜야 근본 개선.
- **불필요(로그근거)**: overlong shaping·length-norm — `len_adv_corr≈0`이라 우리 세팅엔 무효.
- **출력**: 각 토글의 held-out +/− 기여표 → §9 진단·예측 검증. 상세 = `SUBGOAL_PAPER_ASSESSMENT.md` §9.

---

## P1. Ablation — "무엇이 이득인가" 분리 (논문 필수)
같은 bigscale·평가로, 한 컴포넌트씩 끄고 비교.
- [ ] **per-subgoal 보상 OFF**(Qed 보상만) — subgoal 단위 보상의 기여 분리. (엔진 `SUBGOAL_REWARD=0`)
- [ ] **bottom-up 순서 OFF**(랜덤/역순 스테이지) — 커리큘럼 순서의 기여.
- [ ] **s0 단계 OFF**(subgoal만, root 학습 없음) — root 직접학습의 기여. (이미 s3 모델 있음 → 그걸 평가만)
- [ ] **SFT init OFF**(checkpoint-54500 init) — SFT 발판의 기여.
- [ ] **subgoal 소스: gold vs self-harvest**(§B) — gold 필요성.
- **출력**: 각 컴포넌트의 held-out +/− 기여 표. 논문의 ablation 절.

## P1. Baseline/대조 (논문 필수)
같은 bigscale로 대조군을 채워 비교표 완성.
- [ ] **Expert iteration / STaR**(가장 깨끗한 대조) — s0 성공만 SFT 반복. subgoal이 이걸 이겨야 정당화. (§4-②)
- [ ] **기존 방법 bigscale 이식**: LUFFY, backward, DAPG, vDPO, PPO, DAPO, VAPO, revcurr — 이미 작은 scale 있음, bigscale 재현으로 종합 대조표.
- **출력**: 10+ 방법 × 1191 held-out 대조표.

---

## P2. 더 나은 방법 축 (성능 강화, §4)
- [ ] **검색 유도 학습 = GRPO×MCTS**(천장 가장 높음, SOTA 방식) — 우리 병목(dead 63~73% + entropy 0.11 collapse)에 정확히 적합. 상세 = `SUBGOAL_PAPER_ASSESSMENT.md` §4-①-심층. 순서:
    - [ ] **(a) search-for-data**: RMaxTS/BFS로 **dead 정리 증명 찾아** positive 데이터 추가(가장 싸고 proven, expert-iteration과 결합). alias 있음.
    - [ ] **(b) tree-MC-advantage GRPO**: 트리 `mc_value`(있음)를 step-level advantage로(VinePPO식) → credit↑, GRPO 그룹-baseline 편향 회피.
    - [ ] **(b′) subgoal-seed × Tree-GRPO 융합**(Tree-GRPO 2509.21240): 각 subgoal seed에서 flat G 대신 트리 전개 → intra-tree process advantage로 **all-solved 41%·dead 동시 살림**. per-subgoal 보상=**verifier-exact process reward**(PRM 불필요, ReST-MCTS* 대비 강점). few-sim이면 **Gumbel**(Danihelka 2022) 개선보장. 상세 §4 ①-심층2.
    - [ ] (스케일 후) **(c) full MCTS-in-loop**(AlphaZero류) — 1.3B·단일GPU엔 과함, 7B/멀티GPU 확보 시.
    - **주의**: coq-lsp 호출 비용↑ · idiosyncratic tail엔 무력(subgoal이 답) · **코어(subgoal) ablation과 분리**해 "검색 얹으면 +얼마"로.
- [ ] **Dense/process 보상**(s0 dead 74% 살리기) — goals-closed 부분크레딧. 엔진 value_fn/shaping 훅 있음. 가장 싼 개선.
- [ ] **적응형 난이도(§C, adapt_prefix)** — 성공률~0.5 seed 자동선택 → all-solved 42%+dead 22% 낭비 제거.
- [ ] **이중 소스(§B, gold+self-harvest HER)** — `harvest_subgoals.py`로 실패 롤아웃의 닫힌 subgoal 추가.
- [ ] **decompose 제안 학습(§A, headline novelty)** — 첫 tactic 생성 → 자식 solvability 보상(`mc_value` 재사용). "만들기+닫기" 2수준.

## P2. 이론 실증 (§D+ 검증)
- [ ] **p_reach 측정**: s0 롤아웃에서 각 subgoal state 통과 비율 → transfer 이득과 상관(정리1).
- [ ] **εT²/k 스케일링**: 배포 오차 vs 분할수 k(정리2).
- [ ] canonical vs idiosyncratic seed의 p_reach 비교.

---

## P3. 스케일/일반성 (탑티어 진입)
- [ ] **all-CoqStoq**(CompCert 넘어 전 Coq 프로젝트) — 다중 도메인 일반성.
- [ ] **다양한 방법 × all-CoqStoq 대조** — 종합성.
- [ ] **cross-domain 1개**: Lean/miniF2F 또는 **더 큰 모델(7B)** — "Coq-only, 1.3B-only" 리스크 닫기.
- [ ] published SOTA 포지셔닝(참고용, 우리 비교는 our-baselines 유지).

---

## 이론 강화 (§D+ 별도, 논문 강도)
- [ ] 정식 정리화(가정 A1~A3 + suboptimality ≤ O(ε_sub·T²/k + δ·V_max·T))
- [ ] Lower bound(sparse full-theorem RL은 T에 지수적 → 분할 필수)
- [ ] HER unbiasedness(canonical+verifier면 무편향)
- [ ] 단조개선(policy iteration) / perfect-verifier 프레이밍

---

## 실행 메모
- **GPU 1개 순차**: 위 실험은 한 번에 하나(오염 방지). 현재 실행 완주 후 P1(ablation·expert-iteration)부터.
- **재사용 코드**: adapt_prefix / mc_value / harvest_subgoals / RMaxTS·BFS alias / value_fn·shaping 훅 — 대부분 이미 있음.
- **관문 게이트**: P0(held-out 338 초과)이 안 되면 P1 ablation으로 원인 규명(어느 컴포넌트가 죽였나) 후 재설계.
