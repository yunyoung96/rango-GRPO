# 🧭 타입 구조를 "학습론"으로 익히게 하는 법 — 논문 조사 (2026-08-06)

> ⚙️ **근거 데이터의 학습률: lr=3e-4** (실험 `tst1000tr5091_bc_lr3e-4_...`, b000~b039 롤아웃 36 gz). 이 문서의 병목 진단·설계는 그 실험 기반. 요약=[[../grpo/BC_LR3E-4_RESULT]].
> **동기**: 우리 실증([[MIXED_FAILURE_ANALYSIS_lr3e-4]]) — 실패의 ~50%가 apply/rewrite에서 **타입 안 맞는 lemma 인자 선택 → INVALID**.
> **질문**: 프롬프트 타입 주입(input augmentation/[TYPES]) 말고, **training/objective/representation 수준**에서 타입 정합성을 학습시키는 법?
> *(deep-research 워크플로 실패 → WebSearch 직접 조사. 모든 논문 venue 빡세게 확인.)*

**범례**: 🟢 정식게재·최상위(A\*) · 🟡 게재(A/저널/신생) · 🔴 preprint(미검증) · ⭐ 추천 · ⚠️ 주의/정정

---

# 🔬 7방향 × 대표 논문

## (1) Type-constrained / grammar-constrained generation
- 🟢 **Type-Constrained Code Generation with LMs** — **PLDI 2025**.
  - *메커니즘*: 부분 프로그램이 well-typed로 완성 가능한지 판정하는 sound 알고리즘(prefix automata + inhabitable type search)으로 타입 안 맞는 토큰을 **생성 단계에서 차단**.
  - *결과*: HumanEval/MBPP 컴파일오류 절반↓, 여러 크기 모델서 검증.
  - ⚠️ 주로 **디코딩 제약**(학습 loss 아님). STLC→TypeScript 형식화라 **Coq dependent type엔 미적용**.

## (2) 타입 예측 auxiliary objective / multi-task
- 🟢 **Graph2Tac (definition task)** — **ICML 2024**.
  - *메커니즘*: next-tactic 외에 **정의/개념 표현을 예측**하는 보조 task 공동학습. 17.4%→**26.1%**(definition task가 핵심 기여).
  - *적용*: aux objective는 decoder에 이식 가능(next-tactic + "goal 타입/head 예측"). 값쌈. 단 수치는 GNN 것이라 그대로 아님.

## (3) 타입 호환 premise contrastive / hard-negative retrieval  ⭐
- 🟢 **Magnushammer** — **ICLR 2024**.
  - *메커니즘*: **contrastive 학습** premise 검색(SELECT 1024→RERANK). PISA 38.3%(Sledgehammer)→**59.5%**.
- 🔴 **Premise Selection for a Lean Hammer (LeanHammer)** — **preprint**(2025 초안/2026 리비전).
  - *메커니즘*: dependent type theory용 neural premise selection, 문맥 적응 + 심볼검색·재구성. 기존 대비 **+21% goal**.
  - ⭐ **우리 병목 직공**: "타입 호환 lemma=positive, 불일치=hard-neg" = apply INVALID 겨냥. 별도 소형 encoder(1.3B 독립, 단일GPU).

## (4) 타입-인지 representation / embedding
- 🟢 **Graph2Tac** — **ICML 2024**. Coq term의 faithful 그래프 + 정의 의존 그래프로 hierarchical 표현. 미학습 정의도 온라인(1.5× vs offline).
- 🟢 **Passport** — **TOPLAS 2023**(+PLDI'23 발표). identifier/타입 구조 3-인코딩(category/subword/path). 기존 대비 **+29% 정리**.
  - ⚠️ 둘 다 GNN/RNN 기반이라 **decoder LLM 이식은 아키텍처 공사**.

## (5) Neurosymbolic — type checker/elaborator in the loop  ⭐
- 🟡 **Process-Supervised RL for Code Gen** — **EMNLP 2025 (main)**.
  - *메커니즘*: 컴파일로 **line별 라벨** → process reward model. outcome-only 능가. mutation/refactoring-execution으로 자동 라벨.
- 🔴 **RLCSF: RL from Compiler & Language Server Feedback** — **preprint**(저자 "Yifan Zhang, Lanser Contributors", 소속 미명시=개인/오픈소스성).
  - *메커니즘*: "에이전트가 **API hallucinate·틀린 심볼 drift**"(=우리 `apply plus_two/three/four`)를 diagnostics로 shaped process reward.
  - ⚠️ **프레이밍 참고일 뿐 검증된 근거 아님.** 근거는 위 Process-RL(EMNLP)·potential-shaping 고전(Ng 1999)으로.
- 🔴 **Beyond Binary: dense verifiable rewards** — **preprint**(2026). 부분 성공을 dense reward로.
  - ⭐ 우리 coq-lsp의 INVALID/goal-닫힘을 **potential-based process reward**로([[../grpo/DENSE_GUIDES_SPARSE]]). `--process` 인프라 있음.

## (6) GNN 구조 학습 → decoder 이식
- 🟢 **Graph2Tac** — **ICML 2024** (위와 동일). 순수 GNN은 우리 decoder 트랙과 별개, 이식은 대공사. 장기 옵션.

## (7) reward에 타입 정합성 직접 (RL/RFT)
- 🟢 **CodeRL** — **NeurIPS 2022**. critic network로 functional correctness 예측 → dense feedback.
- 🟡 **PPOCoder** — **TMLR 2023**(저널). PPO로 CodeT5 학습, 실행 기반.
- 🔴 **RLTF: RL from Unit Test Feedback** — **preprint/arXiv 2023**. 컴파일러 에러 메시지·위치로 fine-grained 피드백.
- (+ RLCSF, Process-RL, Beyond Binary = (5)와 겹침)
  - ⚠️ "INVALID=−"만으론 앞서 본 GRPO 정체를 못 넘을 수 있음(선택 능력 일반화가 근본).

---

# 📊 우리 상황 종합 판정 (1.3B, CompCert, apply lemma selection)

> 별점(★1~5): **병목적합**=우리 선택실패 직공도 · **기대효과**=성능개선 크기 · **난이도**(쉬움=★↑) · **비용**(낮음=★↑) · **검증도**=근거 tier

| 방향 | 병목적합 | 기대효과 | 난이도 | 비용 | 검증도 | 종합 |
|---|:--:|:--:|:--:|:--:|:--:|---|
| **(3) contrastive premise retriever** ⭐ | ★★★★★ | ★★★★☆ | ★★★☆☆ | ★★★★☆ | ★★★★★ | 🟢🥇 **1순위** |
| **(5)(7) type-checker process reward** ⭐ | ★★★★☆ | ★★★☆☆ | ★★★★☆ | ★★★★☆ | ★★★★☆ | 🟡🥈 **빠른 착수** |
| **(2) type-prediction aux task** | ★★★☆☆ | ★★☆☆☆ | ★★★★★ | ★★★★★ | ★★★☆☆ | 🟢 곁들임(가성비) |
| **(1) type-constrained decoding** | ★★★★★ | ★★★★☆ | ★★☆☆☆ | ★★☆☆☆ | ★★★★★ | 🟢 이상적이나 Coq서 비쌈 |
| **(4)(6) GNN 표현(Graph2Tac)** | ★★★☆☆ | ★★★★☆ | ★☆☆☆☆ | ★☆☆☆☆ | ★★★★★ | 🟢 장기(아키공사) |

**💡 읽는 법**
- 🥇 **(3) contrastive retriever = 최고 밸런스** — 병목직공★5·검증도★5(Magnushammer ICLR'24 +21pp)·비용낮음(소형 encoder). 난이도 중간(hard-neg 데이터). **1순위.**
- 🥈 **(5) process reward = 빠름** — `--process` 재사용(난이도★4). 단 기대효과★3(근본벽 부분해결), 핵심 최신근거 일부 preprint.
- **(2) aux = 가성비** — 효과 작지만(★2) 거의 공짜(★5/★5). (3)에 곁들이기.
- **(1) type-constrained = 이상적이나 비쌈** — Coq dependent elaborator를 디코딩 루프에(비용★2). candidate 필터 수준만.
- **(4)(6) GNN = 검증됐으나 이질** — decoder 이식 대공사(난이도★1). 장기.

---

# 🎯 결론 / 추천 (정직)

- **⚠️ 핵심 진단**: 병목은 "타입 맞는 lemma 선택". 소형 decoder가 이걸 **파라미터로 일반화 학습하긴 용량상 어렵다**(우리 GRPO 정체 = 33 batch 학습해도 apply INVALID율 62→65% 불변, [[MIXED_FAILURE_ANALYSIS_lr3e-4]]). → 순수 SFT/RL로 "타입 감각"을 심는 건 **낙관 금물**.
- **⭐ 가장 승산 있는 2개(병행)**:
  1. 🥇 **Contrastive premise retriever**(3) — 타입 호환/불일치 hard-neg로 별도 encoder 학습. apply/rewrite 후보를 타입으로 걸러 입력. 🟢Magnushammer(ICLR'24)/🟢Passport(TOPLAS'23) 뒷받침.
  2. 🥈 **Type-checker process reward**(5)(7) — coq-lsp INVALID/goal-닫힘을 potential-based process reward로. 🟡Process-RL(EMNLP'25)+Ng1999 고전. `--process` 인프라 有.
- **💡 소형모델엔 "모델이 다 학습"보다 "후보를 밖에서 타입으로 좁혀주기"(retriever)가 현실적.**

---

# 📚 출처 — 전체 논문 게재처 / tier / 연도 / 링크

| # | 논문 | 게재처 | tier | 연도 | 링크 |
|---|---|---|:--:|:--:|---|
| 1 | Type-Constrained Code Generation with LMs | **PLDI** (PACMPL v9) | 🟢 A\* | 2025 | [dl.acm](https://dl.acm.org/doi/10.1145/3729274) · [PLDI25](https://pldi25.sigplan.org/details/pldi-2025-papers/25/) · [code](https://github.com/eth-sri/type-constrained-code-generation) |
| 2 | Graph2Tac | **ICML** (PMLR v235) | 🟢 A\* | 2024 | [arXiv 2401.02949](https://arxiv.org/abs/2401.02949) · [PMLR](https://proceedings.mlr.press/v235/blaauwbroek24a.html) |
| 3 | Magnushammer | **ICLR** | 🟢 A\* | 2024 | [arXiv 2303.04488](https://arxiv.org/abs/2303.04488) · [OpenReview](https://openreview.net/forum?id=WgaVCqZeIU) |
| 4 | Passport (identifier/타입 인코딩) | **TOPLAS** 저널 (+PLDI'23) | 🟢 A\* | 2023 | [arXiv 2204.10370](https://arxiv.org/abs/2204.10370) · [TOPLAS](https://dl.acm.org/doi/10.1145/3593374) |
| 5 | Process-Supervised RL for Code Gen | **EMNLP** (main) | 🟡 A | 2025 | [arXiv 2502.01715](https://arxiv.org/abs/2502.01715) · [ACL Anthology](https://aclanthology.org/2025.emnlp-main.719.pdf) |
| 6 | CodeRL | **NeurIPS** | 🟢 A\* | 2022 | [arXiv 2207.01780](https://arxiv.org/abs/2207.01780) · [code](https://github.com/salesforce/CodeRL) |
| 7 | PPOCoder (execution-based RL) | **TMLR** 저널 | 🟡 저널 | 2023 | [arXiv 2301.13816](https://arxiv.org/abs/2301.13816) |
| 8 | Premise Selection for a Lean Hammer | arXiv preprint (OpenReview 심사흔적) | 🔴 preprint | 2025/26 | [arXiv 2506.07477](https://arxiv.org/abs/2506.07477) · [site](https://cmu-l3.github.io/lean-hammer/) |
| 9 | RLTF (RL from Unit Test Feedback) | arXiv preprint | 🔴 preprint | 2023 | [arXiv 2307.04349](https://arxiv.org/abs/2307.04349) |
| 10 | RLCSF (Compiler+LSP feedback) | arXiv preprint (소속 미명시) | 🔴 preprint | 2025 | [arXiv 2510.22907](https://arxiv.org/abs/2510.22907) |
| 11 | Beyond Binary: dense verifiable rewards | arXiv preprint | 🔴 preprint | 2026 | [arXiv 2601.03525](https://arxiv.org/abs/2601.03525) |
| 12 | DL4TP (Survey on DL for Theorem Proving) | **COLM** | 🟡 신생(≈A-) | 2024 | [github](https://github.com/zhaoyu-li/DL4TP) |
| — | Ng, Harada & Russell (potential-based shaping, 이론근거) | **ICML** | 🟢 A\* (고전) | 1999 | (표준 인용) |

**🟢 정식·최상위(A\*)**: Type-Constrained(PLDI'25)·Graph2Tac(ICML'24)·Magnushammer(ICLR'24)·Passport(TOPLAS'23)·CodeRL(NeurIPS'22).
**🟡 게재(A/저널/신생)**: Process-RL(EMNLP'25)·PPOCoder(TMLR'23)·DL4TP(COLM'24).
**🔴 preprint(미검증, 인용 시 명시)**: LeanHammer·RLTF·RLCSF·Beyond Binary.

> ⚠️ 우리 추천 근거 강도: **(3)은 🟢A\* 2편(Magnushammer·Passport)로 단단**. **(5)는 이론(Ng1999 🟢)+EMNLP(🟡)은 단단하나 최신 적용례(RLCSF·Beyond Binary)는 🔴preprint.** → 근거 확실성은 (3) > (5).

관련: [[MIXED_FAILURE_ANALYSIS_lr3e-4]] · [[../grpo/DENSE_GUIDES_SPARSE]] · [[../grpo/rango_augmented/AUGMENTED_FINAL]] · [[../grpo/TOKEN_VS_TACTIC_CREDIT]]

---
---

# 🏗️ 우리 코드베이스 적응 설계 도안 (2026-08-06)

> "만약 우리 방향(Rango: 1.3B DeepSeek-Coder + LoRA + BM25/dense retrieval, CompCert eval)에 적응하면 어떻게 되나 — 함수·학습 파이프라인 설계".
> **조사 결론(코드 실측)**: 추천 2방향 모두 **인프라가 이미 상당 부분 존재**. from-scratch가 아니라 **기존 위에 얹기**다.

## 🟢 이미 있는 것 (설계의 출발점) — 코드 실측

| 방향 | 이미 있는 인프라 | 파일:줄 |
|---|---|---|
| (A) contrastive retriever | 🟢 **bi-encoder** `PremiseRetriever`(OPT-125m, 2-tower) | `src/premise_selection/model.py:31` |
| | 🟢 **InfoNCE 대조학습** `CrossEntTrainer`(temp 0.1, multi-positive, in-batch neg) | `train_select.py:74` |
| | 🟢 **학습예제** `PremiseTrainingExample`{context,pos_premise,neg_premises,all_pos_premises} | `premise_example.py:16` |
| | 🟢 **serving** VectorDB(precompute)+select_server, 프롬프트 `[PREMISES]` 주입 | `premise_vector_db.py` · `lm_example.py:399` · `tactic_data.py:290` |
| | 🟢 **타입지향 재랭킹** 이미 존재(BM25+α×conclusion match, +11~18pp 검증) | `tactic_data.py:87` `rerank_premises` |
| (B) process reward | 🟢 **`--process` end-to-end 배선** (test까지 통과) | `grpo_train.py:768` · `test_prm_grpo.py` |
| | 🟢 **checker φ**: COMPLETE +1.0 / VALID −0.05 / INVALID −0.10, 재샘플 안전처리 | `process_reward.py:77` `checker_process_rewards` |
| | 🟢 **per-token PRM loss** `grpo_batch_loss_perstep`(first-token credit, Dr.GRPO length-bias) | `grpo.py:359` |
| 공통 자원 | 🟢 **보존 롤아웃 36개 gz**(=batch b000~b035, 파일1개=batch1개) (state_key·tactic·result 포함) = 학습신호 원천 | `data/grpo_rollouts/*.gz` |

**💡 함의**: "타입 학습" 신규 구현량은 생각보다 작다. (A)는 **negative 샘플링을 타입기반으로 교체**, (B)는 **φ를 타입에러에 특화**하는 게 핵심 기여다.

---

## 🥇 방향 A — 타입 hard-negative Contrastive Premise Retriever  ⭐1순위

### A.1 핵심 아이디어 (한 줄)
현재 negative는 **in-file/out-of-file 랜덤**(`premise_example.py:57-97`) → 타입과 무관. 이걸 **"goal에 apply 불가능한(타입 불일치) lemma"를 hard-negative**로 바꾼다. 그러면 retriever가 *"lexical하게 비슷하지만 타입 안 맞는"* premise를 밀어내도록 학습 → apply/rewrite INVALID 직공.

### A.2 🔑 킬러 포인트 — 우리 롤아웃이 곧 ground-truth 타입 라벨
우리는 [[../../memory: preserve-all-rollouts]]로 **36개 gz**(파일1개=batch1개, b000~b035)를 보존했다. 각 step은 `{tactic, result(VALID/INVALID/COMPLETE), state_key}`.
- `apply L` → **INVALID** = Coq이 거부 = **(goal=state_key, L) 타입 불일치** = 검증된 hard-negative.
- `apply L` → **COMPLETE/VALID-progress** = 타입 맞음 = positive.
- 모델이 실제로 뽑은 lemma라 **"그럴듯하지만 틀린"**(=최고 난이도 hard-neg). 랜덤 negative가 절대 못 주는 신호.

### A.3 신규 함수 설계
```python
# scripts/mine_hard_negs.py  (신규)
ARG_TACTICS = ("apply", "eapply", "rewrite", "erewrite", "apply ->", "rewrite <-")

def mine_type_hard_negatives(rollout_gz_dir: str) -> dict[str, dict]:
    """보존 롤아웃 gz → state_key별 타입 positive/hard-neg lemma 집합.
    반환: { state_key: {"pos": set[str], "hard_neg": set[str]} }"""
    table = defaultdict(lambda: {"pos": set(), "hard_neg": set()})
    for step in iter_rollout_steps(rollout_gz_dir):        # gz 스트리밍(초대형 skip)
        lem = extract_lemma_arg(step["tactic"], ARG_TACTICS)   # "apply plus_two" → "plus_two"
        if lem is None:
            continue
        sk = step["state_key"]
        if step["result"] == "INVALID":
            table[sk]["hard_neg"].add(lem)      # Coq 거부 = 타입 불일치
        elif step["result"] in ("COMPLETE", "VALID"):
            table[sk]["pos"].add(lem)
    # pos ∩ hard_neg 충돌 제거(다른 문맥서 둘 다 나온 lemma는 애매 → 제외)
    return resolve_conflicts(table)
```
```python
# premise_example.py 확장 — 기존 스키마에 필드 하나 추가(하위호환)
@dataclass
class PremiseTrainingExample:
    context: str
    pos_premise: str
    neg_premises: list[str]        # (유지) 랜덤 easy negative
    hard_neg_premises: list[str]   # ★신규: 타입 불일치 hard negative (롤아웃 채굴)
    all_pos_premises: list[str]
```

### A.4 loss 수정 (`train_select.py:74` `CrossEntTrainer`)
기존 InfoNCE 분모에 **hard-neg 항을 가중 λ로 추가**:
```
             exp(s⁺/τ)
L = − log ─────────────────────────────────────────────────
          exp(s⁺/τ) + Σ_random exp(s⁻/τ) + λ·Σ_hard exp(s_hard/τ)
```
- τ=0.1(기존), λ≈2~4(hard-neg 강조). λ는 hyperparam.
- 코드상: `collate`(`select_data.py:58`)가 만드는 label matrix에 hard-neg 열 추가 + 그 열에 λ 스케일.

### A.5 학습 파이프라인 (단계별)
```
1. MINE     scripts/mine_hard_negs.py  data/grpo_rollouts/  →  hard_negs.jsonl
              (36 gz → state_key별 pos/hard_neg. 단일 CPU, 코어 소수)
2. BUILD    dataset_worker.select_examples_from_step + hard_neg 주입  →  ExampleDB
              (기존 gold pos + 롤아웃 hard-neg 병합)
3. TRAIN    train_select.py --hard_neg_lambda 3   (OPT-125m, 단일 GPU1, 몇 시간)
4. ENCODE   premise_vector_db.create_premise_db  (새 ckpt로 전 premise 재임베딩)
5. SERVE    select_server ← 새 VectorDB;  lm_example [PREMISES]에 자동 반영
6. EVAL     rand200 @600s + apply/rewrite INVALID율 재측정 (성공지표)
```

### A.6 성공 판정 · 리스크
- 📊 **1차 지표 = apply/rewrite INVALID율** ([[MIXED_FAILURE_ANALYSIS_lr3e-4]]의 62→65% 벽이 내려가나). 2차 = rand200 pass율.
- ⚠️ **리스크**: ① hard-neg 수집량 — apply INVALID가 롤아웃에 충분? (있음: 성공 rollout도 6.7%, 실패 24% INVALID). ② 같은 lemma가 문맥에 따라 pos/neg 둘 다 → `resolve_conflicts`로 제외(신호 순도↓ 대가). ③ OPT-125m 용량 — Magnushammer(🟢ICLR'24)가 유사 규모로 38→59% 성공, 용량 우려 낮음.
- ⭐ **왜 1순위**: 병목(선택) 직공 + 근거 🟢A\*(Magnushammer/Passport) + 우리 롤아웃이 공짜 라벨 + 1.3B 본체 안 건드림(독립 소형 encoder).

### A.7 ⭐ LLM 인코더 승급판 — "시작 전에 한 번 contrastive 돌리기"(warm-start)
**질문(사용자 2026-08-06)**: apply에 hallucination+틀린 lemma가 많은데, **LLM으로 premise contrastive를 한 번 돌리고 시작하면** 도움 되나?
**답 — 조건부 YES**:
- ✅ **병목 직공**: apply 실패의 **최소 56%가 실존 lemma를 틀린 타입/문맥에**([[MIXED_FAILURE_ANALYSIS_lr3e-4]] 하단), 나머지도 대개 실존인데 retrieval이 안 띄운 것 → **타입 맞는 lemma를 `[PREMISES]`에 올려주면** 추측할 필요 자체가 줆.
- ✅ **우리 근거**: 타입지향 재랭킹만으로 top-1 **+11~18pp**([[../grpo/rango_augmented/AUGMENTED_FINAL]]) + 🟢Magnushammer(ICLR'24) 38→59%.
- ⚠️ **한계**: retriever는 **후보를 올릴 뿐 1.3B가 쓰도록 강제 못 함**(단 재랭킹 +11~18pp가 무시 안 함을 시사). **hallucination 자체는 직접 못 막음**(디코딩 제약=방향1 몫, 단 우리 데이터선 소수). **selection 벽엔 직공·closing/reachability 벽엔 무효.**

**모의 코드 (LLM 인코더 bi-encoder + 타입 hard-neg InfoNCE)**:
```python
# STEP 0. 롤아웃에서 타입 hard-neg 채굴 (apply→INVALID = 검증된 hard-neg)  scripts/mine_hard_negs.py
ARG_HEADS = ("apply","eapply","rewrite","erewrite")
def lemma_arg(tac):                       # "apply Zle_trans in H" -> "Zle_trans"
    t=re.sub(r'^[\-\+\*\d\.\)\s]+','',tac.strip())
    m=re.match(r'(?:e?r?e?write|e?apply)\s+(?:<-\s*)?([A-Za-z_][\w\.\']*)', t)
    return m.group(1) if m else None
def mine(rollout_glob):
    tbl=defaultdict(lambda:{"goal":None,"pos":set(),"neg":set()})
    for gz in glob.glob(rollout_glob):
        for line in gzip.open(gz,"rt"):
            g=json.loads(line)
            for att in g.get("attempts",[]):
                for st in att.get("steps",[]):
                    lem=lemma_arg(st["tactic"])
                    if lem is None: continue
                    e=tbl[st["state_key"]]; e["goal"]=st["example"]["proof_state"]
                    if st["result"]=="INVALID":            e["neg"].add(lem)  # ★ Coq거부=타입불일치
                    elif st["result"] in ("VALID","COMPLETE"): e["pos"].add(lem)
    out=[]
    for sk,e in tbl.items():
        pos,neg=e["pos"]-e["neg"], e["neg"]-e["pos"]        # pos∩neg(문맥의존)은 제외
        if pos and neg: out.append({"goal":e["goal"],"pos":sorted(pos),"hard_neg":sorted(neg)})
    return out    # → data/type_contrastive.jsonl (+ gold: step.step.context 를 pos로 병합)

# STEP 1. LLM 인코더 (bi-encoder, LoRA 경량화; goal/premise 를 같은 LLM+역할프리픽스로 임베딩)
class LlmPremiseEncoder(torch.nn.Module):
    def __init__(self, base="deepseek-ai/deepseek-coder-1.3b-base", dim=768):
        super().__init__()
        self.tok=AutoTokenizer.from_pretrained(base)
        enc=AutoModel.from_pretrained(base, torch_dtype=torch.bfloat16)
        self.enc=get_peft_model(enc, LoraConfig(r=16,lora_alpha=32,
                 target_modules=["q_proj","v_proj"],task_type="FEATURE_EXTRACTION"))  # 본체 동결
        self.proj=torch.nn.Linear(enc.config.hidden_size, dim)
    def embed(self, texts, role):                            # role: "goal"|"premise"
        pfx="[GOAL]\n" if role=="goal" else "[LEMMA]\n"
        b=self.tok([pfx+t for t in texts],padding=True,truncation=True,max_length=512,
                   return_tensors="pt").to(self.enc.device)
        h=self.enc(**b).last_hidden_state; mask=b.attention_mask.unsqueeze(-1)
        pooled=(h*mask).sum(1)/mask.sum(1).clamp(min=1)      # mean-pool
        return F.normalize(self.proj(pooled.float()),dim=-1) # L2 정규화

# STEP 2. InfoNCE + 가중 hard-neg loss (분모 = 정답 + in-batch easy-neg + λ·타입 hard-neg)
def contrastive_loss(enc, goals, pos, hard_negs, tau=0.05, lam=3.0):
    g=enc.embed(goals,"goal"); p=enc.embed(pos,"premise")
    sim_pos=(g*p).sum(-1)/tau; sim_ib=g@p.t()/tau
    loss=0.0
    for i in range(len(goals)):
        hn=enc.embed(hard_negs[i],"premise"); sim_hard=(g[i:i+1]@hn.t()).squeeze(0)/tau
        denom=torch.cat([sim_pos[i:i+1],
                         sim_ib[i][torch.arange(len(goals))!=i],          # in-batch easy neg
                         sim_hard+torch.log(torch.tensor(lam))])          # λ가중 hard neg
        loss+=-(sim_pos[i]-torch.logsumexp(denom,0))
    return loss/len(goals)

# STEP 3. 학습(단일 GPU, 어댑터만)  →  STEP 4. 코퍼스 인코딩→VectorDB 교체(select_server ckpt 스왑, 코드변경0)
#   추론: goal 임베딩→matmul→top-k→ lm_example.py:399 get_ranked_premises 가 [PREMISES] 채움
```

**warm-start 순서("시작 전에 한 번")**: ① `mine("data/grpo_rollouts/*.gz")`+gold 병합 → ② `train`(GPU1, LoRA, 수시간) → ③ 코퍼스 재임베딩·VectorDB 교체 → ④ 그 위에서 롤아웃→GRPO 재개, apply INVALID율 probe 측정.

**인코더 선택 (현실적 순서)**:
| | OPT-125m (기존 `PremiseRetriever`) | LLM 인코더(위 모의코드) |
|---|---|---|
| 표현력 | 보통 | ↑(타입/의미) |
| 코퍼스 인코딩·서빙 | 쌈(precompute 有) | ⚠️ 무거움 |
| 착수 | **즉시**(loss에 hard-neg 항만) | 신설 |
| 권장 | **1차 검증** | 효과 확인 후 승급 |
> 💡 먼저 기존 OPT-125m `CrossEntTrainer`에 **hard-neg 항만 추가**(A.4)해 싸게 검증 → 효과 있으면 **LLM 인코더로 승급**(A.7). A.7은 그 승급판.

---

## 🥈 방향 B — 타입 특화 Process Reward  (빠른 착수, 이미 배선됨)

### B.1 현황 — 새로 만들 게 아니다
`--process`가 이미 `checker_process_rewards`(`process_reward.py:77`)→`grpo_batch_loss_perstep`(`grpo.py:359`)로 **완전 배선**. 지금도 `grpo_train.py --process` 하나면 돈다. 따라서 설계 = **확장/튜닝**.

### B.2 현재 한계 & 우리 확장
현 φ는 `INVALID`를 전부 −0.10으로 뭉갬 — **"타입 안 맞음"과 "문법 오타"를 구분 못 함.** 우리 병목은 전자다. → **타입 불일치 에러에 더 강한 음수 φ**를 준다:
```python
# process_reward.py 확장 (하위호환: 인자 기본값 None이면 기존과 동일)
PHI_TYPE_ERROR = -0.20      # 타입 불일치엔 더 강한 벌점

def is_type_error(msg: str | None) -> bool:
    if not msg: return False
    return any(k in msg for k in
        ("unable to unify", "not convertible", "has type", "expected", "cannot unify"))

def checker_process_rewards(attempt, propagate_first_error=False, type_aware=False):
    ...
    if is_err:
        phi = (PHI_TYPE_ERROR if type_aware and is_type_error(st.get("coq_error"))
               else PHI_ERROR)
    ...
```
- ⚠️ **선결조건**: 이걸 쓰려면 롤아웃에 `coq_error`가 있어야 하는데 **현재 보존 gz엔 없다**(RECORD_ERROR 꺼져 있었음 — 실측 확인). → **앞으로 롤아웃부터 `RECORD_ERROR=1`**(`grpo_rollout.py:265`). 소급 적용은 재롤아웃 필요.
- ➕ **potential-based 형태**(Ng 1999, [[../grpo/DENSE_GUIDES_SPARSE]]): φ를 potential 차분 `Φ(s')−Φ(s)`로 주면 **최적 정책 불변** 보장. `--shape_gold`(`grpo_train.py:807`) 로직 재사용 가능.

### B.3 파이프라인
```
1. 롤아웃  RECORD_ERROR=1 로 재수집 (coq_error 기록)
2. 학습    grpo_train.py --process --type_aware   (단일 GPU, 기존 인프라)
3. 측정    probe100 flywheel(이미 있음)로 apply INVALID율 시계열
4. 비교    --process 없는 baseline 대비 (우리 rango만, no published)
```

### B.4 ⚠️ 정직한 리스크 — B는 "확실한 해결"이 아니다
[[MIXED_FAILURE_ANALYSIS_lr3e-4]] 실측: **GRPO를 33 batch 돌려도 apply INVALID율 62→65% 안 내려갔다.** φ를 타입특화로 더 잘 줘도, 근본이 *1.3B 용량·선택능력 일반화* 문제면 여전히 안 될 수 있다. → **B는 싸고 빠른 시도이지 병목의 근본 해결은 A(retriever)**다.

---

## 🔗 두 방향 조합 = 권장 최종 그림 (플라이휠)

```
   [보존 롤아웃 gz 36]  ──mine_hard_negs──▶  타입 hard-neg
            │                                     │
            │                            (A) contrastive retriever 학습
            │                                     │
            │                              premise VectorDB / select_server
            │                                     │
            │                          lm_example [PREMISES] = 타입정합 후보만
            │                                     │
            │                              1.3B tactic 생성 (apply L)
            │                                     │
            │                                 coq-lsp 검증
            │                                     │
            │                     VALID / INVALID / (type-error) ──(B) process reward
            │                                     │
            └──────────────새 롤아웃 축적◀── GRPO 업데이트
```
- **A가 근본**(입력에서 타입 안 맞는 후보 제거) → 생성 정확도↑.
- **B가 보조**(그 위에서 타입에러에 미세 벌점) → 남은 실수 조정.
- 둘 다 **우리 보존 롤아웃**을 연료로 씀 = flywheel([[research-direction-2026-07]]).

## 🎯 착수 순서 추천
1. 🥇 **(A) mine_hard_negs.py 먼저** — 신규 코드 최소(채굴 스크립트 1개+예제 필드 1개+loss 1항), 학습 대상이 1.3B 본체가 아닌 OPT-125m라 싸고 빠름. 실패해도 본체 무해.
2. 🥈 **(B)는 (A)와 병행** — `--process`가 이미 있으니 `RECORD_ERROR=1` 재롤아웃 + `--type_aware` 한 줄. 단 기대는 보수적으로.
3. 두 산출물을 조합해 rand200 재평가 → 벽(apply INVALID율) 실측 하락 여부로 판정.

---

## 🧩 지금 파이프라인의 "어디에" 끼어드나 (SFT→롤아웃→GRPO→…)

> 핵심: 두 개입은 **새 단계를 추가하는 게 아니라, 지금 루프 안에서 이미 매 프롬프트마다 돌고 있는 두 호출점의 내용물을 바꾼다.**

### 현재 루프를 함수 단위로 (개입점 ★)
```
① SFT (rango fine-tuning)  train_decoder.py
     프롬프트 만들 때 ──▶ 【retrieval 호출】 get_ranked_premises → [PREMISES]      ★A
                                              ↓ (LoRA 학습)
② 롤아웃  grpo_rollout.py  rollout_attempt
     정리마다 G=8 시도, 시도의 매 step:
        example_from_step ──▶ 【retrieval 호출】 get_ranked_premises → [PREMISES]  ★A  (매 step)
             (grpo_rollout.py:185,455,527,613,688 → lm_example.py:399)
        1.3B 생성 → coq-lsp 검증 ──▶ 【결과 기록】 result: VALID/INVALID/COMPLETE   ★B  (매 step)
     시도 끝 ──▶ 【reward】 Qed면 1, 아니면 0
③ GRPO  grpo_train.py
        롤아웃 로드 ──▶ 【reward→advantage】 group_advantages                        ★B
                     ──▶ clipped surrogate loss → LoRA 업데이트
     → 다시 ②로 (룰아웃↔grpo 반복)
```
**`[PREMISES]` 만드는 retrieval(★A)과 reward 계산(★B)은 이미 루프 안에 있는 지점.** 개입 = 이 지점 교체.

### 🥇 (A) retriever = "두 번째 루프"로 끼어든다
retriever는 **1.3B 정책과 별개 모델(OPT-125m)** → 정책 루프 *옆에* 도는 오프라인 루프.
- **소비(swap)**: ①②의 `get_ranked_premises`가 보는 **VectorDB/select_server ckpt만 교체**. 코드 변경 0, 인덱스만 바뀜 → 그 순간부터 모든 `[PREMISES]`가 타입정합 후보 위주.
- **생산(별도 루프)**: 롤아웃 gz → `mine_hard_negs` → `train_select.py`(대조학습) → `premise_vector_db` 재인코딩 → 위 swap으로 복귀.
```
   [②가 뱉는 롤아웃 gz] ──mine──▶ (state, pos, 타입 hard-neg) ──▶ train_select(OPT-125m)
                                                                        ↓ 재인코딩
                                                          select_server ckpt 교체(★A swap)
```
- **운용 (a) 앞에서 1회(권장·단순)**: GRPO 전 기존 36 gz로 1회 학습→swap→이후는 개선된 `[PREMISES]` 위에서 진행.
- **운용 (b) 플라이휠**: K 라운드마다 재학습(hard-neg 누적). 강력하나 ⚠️ 입력분포가 흔들려 정책 재적응 필요.

### 🥈 (B) process reward = "③ 내부 + ② 한 줄"로 끼어든다
정책 루프 **안**에서, 새 데이터 없이 **이미 있는 롤아웃 결과의 해석만 바꿈.**
- **③ GRPO reward 계산 교체**: 지금은 시도당 스칼라 1개(Qed=1) 브로드캐스트 → `--process` 경로로 **step별 φ**(`checker_process_rewards`, 확장 시 타입에러 −0.20)+`grpo_batch_loss_perstep`. **이미 배선, 플래그만.**
- **② 롤아웃 한 줄**: 타입에러 구분엔 `coq_error` 필요한데 **현재 gz엔 없음(실측)** → ②를 **`RECORD_ERROR=1`**로 돌려 기록. 유일하게 롤아웃 쪽 건드리는 부분.
- **발화 시점**: ③ **매 GRPO 업데이트마다**(reward 함수라 상시).

### 합쳐서 (개입 표시)
```
 SFT ──▶ 롤아웃 ──────────────▶ GRPO ──▶ 롤아웃 ──▶ GRPO ──▶ ...
          │   ▲                  │         │
   [A]swap│   │RECORD_ERROR=1[B] │[B]φ     │(반복)
   retrieval  └─coq_error 기록    perstep
   ([PREMISES])
          │
          └──롤아웃 gz──▶ mine_hard_negs ──▶ [A]retriever 학습 ──▶ (swap으로 복귀)
                          (별도 오프라인 루프)
```
- **A = 입력 개입**(retrieval 호출점): 정책이 *보는 후보*를 타입으로 좁힘. 별도 소형모델 루프.
- **B = 보상 개입**(reward 계산점): 정책이 *받는 신호*를 타입에러에 세분화. 같은 루프, 플래그.

### 착수 순서 (입력분포 이동 주의)
1. **A를 (a)방식으로 GRPO 시작 전 1회 확정** → 입력 안정화.
2. 그 위에서 롤아웃→GRPO 반복하되 **B(`--process`+`RECORD_ERROR=1`)** 켜기.
3. 벽 지표(apply/rewrite INVALID율)를 probe flywheel로 추적.
⚠️ A를 GRPO **도중** 스왑하면 `[PREMISES]`가 갑자기 바뀌어 정책 재적응 비용 → 가능하면 **라운드 경계에서만**.

관련: [[MIXED_FAILURE_ANALYSIS_lr3e-4]] · [[../grpo/DENSE_GUIDES_SPARSE]] · [[../grpo/rango_augmented/AUGMENTED_FINAL]] · [[research-direction-2026-07]]
