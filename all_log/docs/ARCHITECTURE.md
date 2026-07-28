# 시스템 아키텍처 — rango GRPO 파이프라인 (코드 단위)

> 모델 로딩 → 서버/클라이언트 → **생성(token→tactic→proof)** → rollout 수집 → GRPO 학습 → adapter sync
> 의 전체 데이터 흐름을 코드 `file:line` 으로 설명. (이론/수식은 [IMPLEMENTATION.md] §0~6, 이 문서는 시스템/배관)
> π(정책확률)가 **어디서 어떻게** 계산되는지에 초점.

---

## 0. 한 장 요약 — 데이터 흐름

```
 [정리(Theorem)]  ─ CoqStoq/coq-lsp 로 goal state 확보
      │
      ▼
┌──────────────────────── rollout (GPU 생성, 서버) ────────────────────────┐
│ grpo_rollout.py : rollout_attempt                                        │
│   반복: get_recs(state) ──HTTP──▶ tactic_gen_server ──▶ model.generate    │
│          └ 토큰 여러 개 생성 → batch_decode → tactic 문자열 1개           │
│        check_proof(tactic) ──▶ coq-lsp 검증 → 새 state (VALID/INVALID/COMPLETE)│
│   COMPLETE 또는 max_steps 까지 → 궤적 1개, reward∈{0,1}                    │
│   한 정리당 G(=8)개 궤적 = 그룹 → rollouts.jsonl (tactic 텍스트만 저장)    │
└──────────────────────────────────────────────────────────────────────────┘
      │  (rollout jsonl: {theorem, attempts:[{steps:[{example|prompt, tactic}], reward}]})
      ▼
┌──────────────────────── 학습 (GPU 업데이트) ─────────────────────────────┐
│ grpo_train.py : train                                                    │
│   저장된 tactic 텍스트를 모델에 **다시 통과**(teacher forcing)            │
│     → logp_new(π_θ, gradient) / logp_ref(동결 시작정책)                   │
│   그룹상대 advantage = (r−mean)/std → clip 대리목적 − β·KL → adam step     │
│   → adapter 저장                                                          │
└──────────────────────────────────────────────────────────────────────────┘
      │  (adapter sync)
      └──▶ 다음 rollout 라운드의 서버가 이 adapter 로드
```

핵심: **생성(rollout)과 gradient 업데이트(학습)는 프로세스가 분리**돼 있고, 그 사이는 **tactic 텍스트 jsonl** 로만 오간다. 정책확률 π 는 두 곳에서 각각 계산된다(§4, §6).

---

## 1. 모델 = base + LoRA adapter

- **base**: `deepseek-ai/deepseek-coder-1.3b-instruct` (LlamaForCausalLM, vocab 32256).
- **정책 π_θ** = base + **LoRA adapter**(r=64). rango 학습분이 이 adapter 에 들어있다.
- **추론(서버)**: `train_decoder.py:92 get_model` — 4bit(nf4) 양자화 로드(추론 메모리 절약), compute dtype bf16.
- **학습**: `grpo_train.py:440` — base 를 bf16 로 로드 후 `PeftModel.from_pretrained(base, init_adapter, is_trainable=True)` (`grpo_train.py:444`). 레퍼런스 `ref_model` = 정책의 **동결 deepcopy**(`grpo_train.py:449-451`).
- 우리 실험은 전부 `init_adapter = models/rango-grpo-fix/adapter`(=fix) 위에서 이어 학습(on-fix).

## 2. 서버 / 클라이언트 (생성 원격화)

생성은 **별도 프로세스(서버)** 가 GPU 에서 담당하고, rollout 루프(클라이언트)는 HTTP(JSON-RPC)로 tactic 을 요청한다.

- **서버** `tactic_gen_server.py`: `run_thm.py` 가 `python3 tactic_gen_server.py decoder-local <adapter> <id> <ppid>` 로 띄운다. werkzeug `run_simple` 로 서빙(`:96`), 자기 ip/port 를 **port map 파일**에 기록해 부모에 알린다(`:90-94`).
  - RPC 메서드: `get_recs`(next-tactic 생성, `:32`), `generate_raw`(자유형, `:47`), `set_model_seed`(재현성, `:58`).
- **클라이언트** `tactic_gen_client.py`: `urls` 리스트에서 `random.choice(self.urls)` 로 서버 선택(`:470`) 후 POST.
  - ⚠️ **주의**(deep-research/코드리뷰에서 지적): 서버가 2개↑면 `set_seed` 와 `get_recs` 가 서로 다른 서버로 갈 수 있어 seeding 이 깨진다. 단일 서버면 무해.
- **결정성**: `set_model_seed(seed)` → `transformers.set_seed`(torch/numpy/random 전역). 같은 (seed, 입력) → 같은 생성. rollout 의 시드 다양화(그룹 G개 서로 다른 궤적)가 여기 의존.

## 3. 생성: 토큰 여러 개 → tactic 하나 → 증명 하나

### 3-A. `get_recs` — 프롬프트 조립 (`model_wrapper.py:140-164`)
```python
collated_input = self.collator.collate_input(self.tokenizer, example)  # state+retrieval → prompt
inputs = self.tokenizer(collated_input, max_length=hard_seq_len, truncation=True, ...)
```
`example`(LmExample) = goal state + BM25 검색 증명 + TF-IDF premise. collator 가 이걸 하나의 프롬프트 문자열로 만든다.

### 3-B. autoregressive 루프는 `model.generate()` 안 (`model_wrapper.py:166-184`)
```python
generate_kwargs = dict(max_new_tokens=128, num_return_sequences=n,
                       do_sample=True, temperature=1.0, num_beams=1, ...)
outputs = self.model.generate(inputs["input_ids"].cuda(), **generate_kwargs)
```
"토큰을 여러 번 생성"하는 루프를 HuggingFace 가 내부에서 돌린다: 다음토큰 분포(softmax)→온도 1.0 샘플링으로 1토큰→붙임→재입력→반복. **EOS 또는 128토큰**에서 정지.

### 3-C. 토큰 id → tactic 문자열 "합침" (`model_wrapper.py:185-187`) ★
```python
input_num_tokens = inputs["input_ids"].shape[1]
generated_seqs = outputs.sequences[:, input_num_tokens:]   # 프롬프트 잘라내고 생성분만
tactics = self.tokenizer.batch_decode(generated_seqs, skip_special_tokens=True)
```
`batch_decode` 가 토큰 id 시퀀스를 subword 경계 붙여 **`"intros x; apply H."` 같은 tactic 문자열 1개**로 만든다. 바로 여기가 "여러 토큰 → tactic 하나".

### 3-D. 이 tactic 의 π값 (logπ) (`model_wrapper.py:197-207`)
```python
transition_scores = self.model.compute_transition_scores(
    generated_seqs, outputs.scores, normalize_logits=True)   # 토큰별 logπ (log_softmax)
scores = transition_scores.where(...!=-inf, 0.0).sum(axis=1).tolist()  # Σ_t logπ = log π(tactic)
```
tactic 전체 정책확률 = `exp(Σ_t logπ_t)`. (생성 시점 π_old 값. 학습엔 재계산해 씀 — §6)

### 3-E. tactic 여러 개 → 증명 하나 (`grpo_rollout.py rollout_attempt`)
`get_recs` 한 번 = tactic 1개(= 한 step). rollout 루프가 반복: `get_recs → tactic → check_proof(coq-lsp) → 새 state → get_recs …` → COMPLETE(reward=1) 또는 max_steps(reward=0).

## 4. rollout 수집 → jsonl

- `grpo_rollout.py`: 정리 하나에 G(=8)개 `rollout_attempt` → **그룹**. 각 궤적의 step = `{example(or prompt), tactic, [result]}`, 궤적 단위 `reward∈{0,1}`.
- 저장(`append_group`)은 **tactic 텍스트만**(π 값 저장 안 함). 그룹 jsonl 한 줄 = `{theorem, start, attempts:[...]}`.
- 시작점 변형: s0(기본), `curr_r{N}`(revcurr 중간상태), gold 주입(LUFFY), MC value(VinePPO) 등은 이 수집 단에서 갈린다(alias 별 `GRPORolloutSearchConf`).

## 5. 학습: GRPO 업데이트 (`grpo_train.py`)

1. `load_groups` 로 jsonl 로드 → `flatten_group` 으로 (prompt, tactic, advantage, gold여부) 행으로 펼침.
   - **advantage** = 그룹상대 `(r−mean)/std` (`grpo.py:21 group_advantages`). value network 없음 — **그룹 평균이 baseline**.
2. micro-batch 마다:
   - `build_completion_batch`: prompt+tactic 토크나이즈, completion(tactic) 토큰만 mask=1 (`grpo_train.py:44`).
   - `sequence_token_logprobs(model, …)` → **logp_new**(π_θ, gradient 흐름), `sequence_token_logprobs(ref_model,…)` → **logp_ref**(동결). 첫 라운드 on-policy 라 `logp_old=logp_ref`.
   - 손실: `grpo_batch_loss` = clip 대리목적 − β·KL (`grpo.py:155`). (변형: LUFFY/VinePPO/PRM/DAPO 는 다른 loss 분기)
3. adam step → 반복 → `model.save_pretrained(save_dir)` 로 adapter 저장.
4. 저장된 adapter 를 다음 rollout 라운드 서버가 로드(sync).

## 6. π(정책확률)는 두 번 계산된다 — 헷갈리기 쉬운 지점

| 시점 | 무엇 | 코드 | 용도 |
|---|---|---|---|
| **생성(rollout)** | π_old (샘플링 정책) | `model_wrapper.py:198 compute_transition_scores` | 샘플링·(참고 score). **저장 안 함** |
| **학습** | π_θ (현재 정책) | `grpo_train.py:81 sequence_token_logprobs` (logp_new) | ratio ρ·surrogate gradient |
| **학습** | π_ref (동결 시작정책) | 같은 함수, `ref_model` | KL(π_θ‖π_ref) 정규화 |

즉 rollout 은 **tactic 텍스트만** 남기고, 학습이 그 텍스트를 teacher-forcing 으로 다시 통과시켜 **logp 를 재계산**한다(생성 때 값을 신뢰·재사용하지 않음). 그래서 rollout(서버 생성)과 gradient(학습)를 완전히 분리할 수 있다.

## 7. 코드 파일 맵

| 파일 | 역할 |
|---|---|
| `src/model_deployment/model_wrapper.py` | DecoderLocalWrapper: 로딩·`get_recs`·`model.generate`·decode·logπ |
| `src/model_deployment/tactic_gen_server.py` | JSON-RPC 서버(get_recs/generate_raw/set_model_seed) |
| `src/model_deployment/tactic_gen_client.py` | 클라이언트(url 선택, POST) |
| `src/tactic_gen/grpo_rollout.py` | rollout_attempt·collect_group·시작점 변형(revcurr/luffy/vine/bread/dapo) |
| `src/tactic_gen/grpo_train.py` | GRPO 학습 루프(logp 재계산·advantage·loss·저장) |
| `src/tactic_gen/grpo.py` | 순수 텐서 손실 코어(group_advantages·grpo/luffy/dapo_batch_loss·KL) |
| `src/tactic_gen/train_decoder.py` | `get_model`(4bit 로딩) 등 SFT 유틸 |

## 8. 관련 문서
- 이론/수식(정책경사·baseline·clip·KL 유도): `IMPLEMENTATION.md` §0~6
- GRPO 개량 계보(gold/curriculum/on-policy): `IMPLEMENTATION.md` §11
- gold/curriculum 문헌 조사: `RESEARCH_GOLD_CURRICULUM.md`
