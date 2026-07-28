# Interleaved SFT↔GRPO for Coq — 문헌 + 우리 실측으로 본 비판적 종합

작성 2026-07-27. 출처: (1) 다른 Claude 세션의 문헌조사, (2) 우리 프로젝트 실측(`SUBGOAL_PAPER_ASSESSMENT.md` §10, `MIXED_GROUP_SUMMARY.md`, `GOLD_PROOF_METHODS.md` 6-gold 전멸). 관련: `IDEAS.md`, `DECOMPOSITION_IDEAS.md`.

> ⚠ 아래 §1·§2의 논문 인용은 **다른 Claude 조사분**. 우리 검색으로 교차확인된 것: DSP-V1.5(2408.08152)·DSP-V2(2504.21801)·ReST-EM(2312.06585)·Tree-GRPO(2509.21240)·process-verified RL(2606.20068). **나머지 arXiv ID/학회는 논문화 전 재확인 필요.**

---

## 0. 한 문단 요약

"SFT↔GRPO 교대"는 일반 reasoning(ReLIFT/BRIDGE)·정리증명(Goedel expert-iteration/STP)에서 이미 성숙. **단 Coq/Rocq은 공백.** 다른 Claude의 개선안(variance-스케줄·hammer-potential·lemma flywheel)은 우리 실측과 강하게 정렬. **그러나 그들이 all-zero 정리의 SFT 데이터로 제안한 "human proof backward 분해/임의 corpus state 승급"은 우리가 §10에서 이미 실패로 실증한 covariate-shift 함정.** → 그 자리를 **reachable 데이터(invertible 분해·hammer-closed·자기증명)**로 바꾸는 게 우리 고유 기여.

---

## 1. 문헌 3갈래 (다른 Claude 조사)

### A. SFT↔RL 교대 — 일반 reasoning (방법론 직계)
- **ReLIFT** (2506.07527, ICLR 2026): 가장 직접적 선행. RL=능력 범위 내 유지·향상, SFT=능력 밖 진전. **핵심 경고: 단순 교대만으론 무효 — 스케줄링·FT데이터 선택이 결정.** 초기에 FT 자주+가장 어려운 문제. demo 13%로 RL·SFT 단독 능가(+5.2 평균).
- **BRIDGE** (2509.06948): 순진 교대를 baseline으로 — 그것만으로 수렴효율·최종성능↑ 하나 **모든 SFT업데이트가 RL에 유익하진 않아 RL-only 대비 개선 보장 못함** → bilevel 최적화.
- **동계열**: SRFT·Prefix-RFT(2507.01679)·CHORD·SASR(2505.13026)·AMFT(2508.06944) — 단일스테이지 혼합/재가중.

### B. 정리증명 expert iteration (Lean, 성숙)
- **Goedel-Prover** (2502.07640, COLM 2025): iter-k 생성→Lean 검증→통과분 SFT→iter-(k+1). = 교대 그 자체. 164만 statement, 80만+ 증명 확보.
- **Goedel-V2** (2508.03613): + scaffolded data synthesis(적정난이도 합성) + **model averaging(후반 다양성 감소 완화)** + 컴파일러 자기수정.
- **STP** (2502.00212, ICML 2025): **교대의 한계 정면 지적** — sparse reward로 몇 라운드 후 정체(LeanWorkbook pass 13.2%). conjecturer+prover 자기대전으로 "가까스로 풀 난이도" conjecture 생성해 정체 돌파.

### C. Coq/Rocq — 공백
- **Reinforced LLM prover** (2502.08908): 2단계 RL로 SFT 대비↑. 짧은 미출판 preprint.
- **Putnam-Rocq** (2603.20405, Inria): 서베이 — 특화 prover(DeepSeek/Kimina/Goedel/Seed/Aristotle) 전부 **Lean 타깃**, Rocq은 주목 적음. **Opus 4.6+MCP+compile-first 멀티에이전트로 Putnam 12중 10** → "학습 없는 에이전트도 잘함" = **우리 baseline이자 반론 상대.**
- **Quarry**(2606.17981, PACMPL 2026): planning-then-execution, LLM이 sublemma 분해 제안→CoqHammer 처리. 벤치 CoqGym100·Wigderson100·TransBench58.
- **AutoRocq**(FSE 2026), **LLM4Rocq**(Inria, 인프라 툴박스 — **GRPO 롤아웃 검증 인프라 가져다 쓸 것**).

---

## 2. 다른 Claude의 7개 개선안 (요약)
1. 교대 스케줄을 난이도 대신 **group reward variance**로(>0→RL, all-zero→SFT큐, all-one→드롭).
2. all-zero SFT데이터원: (a) **CoqHammer expert**(잔여 subgoal에 hammer), (b) backward proof-state 분해(human), (c) 프론티어 에이전트 증류.
3. **심볼릭 potential 보상**: "hammer로 닫히나/몇 초" = potential(학습불필요·무편향·Coq전용) + goal수·hyp소진·term size.
4. 다양성 붕괴 방지: model averaging(soup)·LoRA merge α 스케줄·**pass@1/32/1024 곡선 보고**.
5. **Granularity 교대**: whole-proof(RL outcome)↔next-tactic(SFT 조밀)↔sublemma.
6. **STP-Coq 커리큘럼**: 중간 proof state를 독립 lemma로 승급(무한·타입체크 보장·난이도 등급).
7. **뉴로심볼릭 flywheel**(Strat2Rocq): 모델 발견 lemma→hammer 라이브러리 편입→hammer↑→보상 조밀↑→모델↑. **학습이 리워드함수를 개선.**

---

## 3. ★ 우리 실측으로 본 비판 (핵심 기여)

### 3.1 동의 — 우리 데이터가 뒷받침
- **①variance 스케줄** = 우리 **§9 dynamic sampling + DSP-V1.5 moderate-success 선택**. 우리 실측 **dead 62%/mixed 30%/all-solved 8%**(MIXED_GROUP_SUMMARY)가 정확히 그 라우팅 신호. "verifiable domain은 스케줄을 롤아웃 통계에서 공짜로 읽는다"는 프레이밍 좋음.
- **③hammer-potential dense** = 우리 IDEAS① + Coq twist. 학습불필요·무편향이라 goal-count보다 reward-hacking에 강함.
- **④다양성 붕괴** — 우리 **entropy 0.11 collapse**가 위험 실증. pass@k 곡선 보고 옳음.
- **⑦flywheel** = 우리 IDEAS⑤(lemma 라이브러리) + 보상개선 루프. 가장 논문답고 우리와 정렬.

### 3.2 ⚠ 결정적 반박 — all-zero의 SFT 데이터원 (그들 ②b, ⑥)
그들은 all-zero 정리에 **human/corpus 유래** SFT를 제안: ②b(human proof backward 분해→(goal, 남은 tactic)) · ⑥(임의 corpus 중간 state를 lemma 승급).
- **우리 §10 실측: gold 분해 subgoal은 완전체 풀이서 16.7%만 도달(성공경로 9.4%), 레벨끼리 0% 중첩. gold-injection 6종(LUFFY·KL-LUFFY·backward·revcurr·DAPG·RFT-gold) 전멸. mixed%↑≠test↑.**
- → **all-zero에 gold-유래 SFT를 먹이는 건 정확히 우리가 빠진 covariate-shift 함정.** ②b(=우리 leaf/cascade의 backward 분해)와 ⑥(=우리 subgoal 승급)은 **우리가 이미 해보고 회귀시킨 것.**
- **고치는 법(우리 기여)**: all-zero의 SFT를 **reachable/on-policy**로 생성 —
  - (a) **invertible 분해**(`DECOMPOSITION_IDEAS.md`): canonical·결정적·모델이 스스로 도달 → 갭 0.
  - (b) **hammer-closed** subgoal: 모델이 hammer를 호출 가능하니 reachable.
  - (c) 자기증명/에이전트 trace: 인간증명보다 스타일 호환↑(덜 off-policy).
  - **raw human backward-분해·임의 corpus state 금지.**

### 3.3 그 외 조율
- **②c 에이전트 증류**: 에이전트 Coq증명은 human보다 on-distribution → human-gold보다 낫지만 1.3B엔 여전히 off-policy → **SFT-then-onpolicy-RL(밀도정합)**로, covariate shift 감시.
- **⑥ STP-Coq**: 승급할 state를 **자기 도달가능**(모델 자기증명/모델이 가까스로 푸는 conjecture)으로 — STP 원본도 "현 prover가 가까스로 풀" 난이도(on-policy-ish). 임의 corpus state면 §10 재현.
- **⑤ granularity**: 우리 분해 작업과 정렬 — 구조적 정당화 좋음.

---

## 4. 종합 — 두 분석의 상보성 + 추천 파이프라인

**상보성**: 다른 Claude = 스케줄/보상/flywheel/문헌(강). 우리 = **왜 gold 실패(§10) + reachability-safe 데이터생성(invertible 분해)**(강). 합쳐야 작동.

**추천 파이프라인 (합본):**
1. **variance 라우팅**(①): 롤아웃 그룹 → mixed=GRPO / all-zero=SFT큐 / all-one=드롭·승급.
2. **all-zero SFT데이터 = reachable** (우리 3.2 고침): invertible 분해 + hammer-closed + 자기/에이전트 trace. (gold backward-분해 ✗)
3. **dense = hammer-potential**(③) + reward-hacking 가드(Print Assumptions, timeout 마스킹).
4. **flywheel**(⑦/IDEAS⑤): 발견 lemma → hammer 라이브러리 → 보상 조밀화.
5. **EI 반복**(B) + 다양성 방지(④ model soup / LoRA α 스케줄) + **pass@k 곡선**.

---

## 5. 논문 프레이밍 + 공격지점 방어
- **프레이밍**: "verifiable·극희소보상 Coq 도메인에서 interleaved SFT-GRPO를 **롤아웃-variance로 스케줄**하되, all-zero의 SFT를 **reachability-보존(invertible 분해/hammer)**으로 공급 + **lemma flywheel로 보상함수를 자기개선**." → 우리 §10(왜 gold 실패)이 방법의 이론적 정당화.
- **방어**: (i) STP의 sparse-reward 정체 → flywheel이 보상을 조밀화해 정체 완화. (ii) Putnam-Rocq "에이전트가 이미 잘함" → "경쟁 아니라 **에이전트를 reachable하게 증류**"(②c) + cost/latency 이점 + flywheel은 에이전트도 강화.

## 6. 평가/함정 (반드시)
- 벤치: CoqGym100·Wigderson100·TransBench58·miniF2F-Rocq. Ablation: RL-only / SFT-then-RL / **naive alternating(BRIDGE baseline)** / 제안.
- 에이전트 baseline을 **비용/wall-clock 매칭**.
- **Coq reward-hacking**: `admit`/`Admitted`/`Axiom`/`Obligation Tactic` 오염/기존 lemma `Require Import` → **`Print Assumptions` 필수 체크**. timeout을 실패로 채점 금지(마스킹).
- **버전 고정**(8.10 vs 8.13 리워드 노이즈원) — 컨테이너 분리([[no-ocaml-version-change]]).

## 7. 다음 액션
1. **variance 라우팅 + reachable-SFT** 최소 구현: mixed→GRPO / all-zero→(invertible 분해 or hammer)→RFT. (우리 §9 dyn_resample + DECOMPOSITION 훅 결합.)
2. hammer-potential dense reward 훅(§4-③).
3. lemma flywheel 프로토타입(harvest→premise DB).
4. 우선순위(다른 Claude): **1+2(variance+reachable) + 4(다양성)** = 워크숍, **+7(flywheel)** = 메인컨퍼런스급.

**참고문헌(재확인 요)**: ReLIFT 2506.07527 · BRIDGE 2509.06948 · Goedel 2502.07640 · Goedel-V2 2508.03613 · STP 2502.00212 · Putnam-Rocq 2603.20405 · Quarry 2606.17981 · Strat2Rocq · [DSP-V1.5 2408.08152](https://arxiv.org/abs/2408.08152) · [DSP-V2 2504.21801](https://arxiv.org/abs/2504.21801) · [ReST-EM 2312.06585](https://arxiv.org/abs/2312.06585).
