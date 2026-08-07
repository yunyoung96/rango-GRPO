#!/usr/bin/env python3
"""GRPO 학습 루프 — DeepSeek-Prover-V1.5 방식으로 rango 정책을 RL fine-tune.

우리 모델은 next-tactic 정책 → **tactic-level GRPO**로 충실 적응:
  · rollout(grpo_rollout.py)이 정리마다 G개 증명 시도를 생성·Coq검증 → 그룹.
    각 시도 = step들[(LmExample, tactic)] + proof-level 보상 r∈{0,1}.
  · 그룹 상대 advantage Â_i = (r_i−mean)/std (같은 정리의 시도끼리).
  · 시도의 모든 (state,tactic) step에 Â_i 부여 → 클립 대리목적 − β·KL(π‖π_ref).
  · π_ref = RL 시작 시점 정책(스냅샷 logp). π_old = 같은(온폴리시 첫 epoch).

rollout(서버+retrieval+Coq)과 학습(GPU)을 **분리**: 이 스크립트는 rollout jsonl을 읽어
로컬 학습 가능 모델(base+LoRA, rango 초기화)로 logp를 재계산해 업데이트한다.
라운드마다 갱신 adapter를 서버에 sync해 다음 rollout에 반영.

★제약: OCaml 무관(순수 PyTorch/PEFT). 코어 손실은 grpo.py에서 단위테스트 완료.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Optional

import torch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tactic_gen.grpo import (  # noqa: E402
    group_advantages,
    group_advantages_with_gold,
    grpo_batch_loss,
    grpo_batch_loss_perstep,
    luffy_batch_loss,
    luffy_kl_batch_loss,
    dapo_batch_loss,
    overlong_shaped_rewards,
    sft_batch_loss,
    dapg_demo_loss,
    ppo_batch_loss,
    awac_batch_loss,
    dpo_batch_loss,
)
from tactic_gen.process_reward import (  # noqa: E402
    checker_process_rewards,
    normalize_process,
)


# ── 토크나이즈: prompt(=collate_input) + completion(=tactic) → ids + completion 마스크 ──
def build_completion_batch(
    tokenizer,
    prompts: list[str],
    completions: list[str],
    max_len: int,
    device: str = "cpu",
):
    """반환 input_ids(B,T), attn(B,T), comp_mask(B,T): completion 토큰=1(=학습 대상).
    prompt 길이로 마스크 경계 산정(response-template 탐색 불필요)."""
    input_ids_list, mask_list = [], []
    for p, c in zip(prompts, completions):
        # prompt/completion 따로 토크나이즈 후 이어붙임 → subword 경계 보장(RLHF 표준).
        p_ids = tokenizer(p, add_special_tokens=False)["input_ids"]
        c_ids = tokenizer(c, add_special_tokens=False)["input_ids"]
        if not c_ids:
            c_ids = [tokenizer.eos_token_id or 0]
        # prompt가 max_len 초과하면 앞을 자름(completion은 보존).
        keep_p = max(0, max_len - len(c_ids))
        p_ids = p_ids[-keep_p:] if keep_p else []
        full_ids = (p_ids + c_ids)[:max_len]
        n_p = min(len(p_ids), len(full_ids))
        mask = [0] * n_p + [1] * (len(full_ids) - n_p)
        input_ids_list.append(full_ids)
        mask_list.append(mask)
    T = max(len(x) for x in input_ids_list)
    pad_id = tokenizer.pad_token_id or tokenizer.eos_token_id or 0
    B = len(input_ids_list)
    input_ids = torch.full((B, T), pad_id, dtype=torch.long)
    attn = torch.zeros((B, T), dtype=torch.long)
    comp_mask = torch.zeros((B, T), dtype=torch.long)
    for i, (ids, m) in enumerate(zip(input_ids_list, mask_list)):
        input_ids[i, : len(ids)] = torch.tensor(ids, dtype=torch.long)
        attn[i, : len(ids)] = 1
        comp_mask[i, : len(m)] = torch.tensor(m, dtype=torch.long)
    return input_ids.to(device), attn.to(device), comp_mask.to(device)


def sequence_token_logprobs(
    model, input_ids: torch.Tensor, attn: torch.Tensor
) -> torch.Tensor:
    """각 위치의 '실제 다음 토큰' log-prob. 반환 (B,T): 위치 t = logp(token_t | <t).
    위치 0은 예측 대상 없음 → 0. (shift 정렬 후 comp_mask도 같은 좌표계 사용)"""
    out = model(input_ids=input_ids, attention_mask=attn)
    logits = out.logits[:, :-1, :]                       # (B,T-1,V): t는 t+1 예측
    logp = torch.log_softmax(logits.float(), dim=-1)
    tgt = input_ids[:, 1:]                                # (B,T-1)
    tok_logp = logp.gather(-1, tgt.unsqueeze(-1)).squeeze(-1)  # (B,T-1)
    pad = torch.zeros((input_ids.shape[0], 1), device=tok_logp.device)
    return torch.cat([pad, tok_logp], dim=1)             # (B,T): 위치 t=token_t logp


_RENDER: dict = {}


def _render_one(ex_json):
    return _RENDER["fn"](ex_json)


def prerender_prompts(groups: list[dict], collate_fn, workers: int, sft: bool = False) -> int:
    """step 의 example → prompt 문자열을 **학습 전에 병렬 렌더**해 st['prompt'] 에 채운다.

    _flatten_prompt 이 'prompt' 를 우선 사용하므로 (a) GPU 루프에서 CPU 렌더링이 사라지고
    (b) epoch 마다 같은 프롬프트를 다시 렌더하지 않는다. 문자열은 순차 렌더와 동일
    (RERANK_PREMISES/INJECT_TYPES 는 fork 로 자식에 상속 → 규칙 동일) → 학습 결과 불변."""
    targets = []
    for g in groups:
        for a in g["attempts"]:
            if sft and float(a.get("reward", 0)) < 1.0:
                continue                       # SFT 는 성공궤적만 학습 → 나머지 렌더 낭비
            for st in a.get("steps", []):
                if "prompt" not in st and st.get("example") is not None and not st.get("planner_opening"):
                    targets.append(st)
    if not targets:
        return 0
    import multiprocessing as mp
    import time
    t0 = time.time()
    _RENDER["fn"] = collate_fn
    if workers <= 1:
        outs = [collate_fn(st["example"]) for st in targets]
    else:
        with mp.get_context("fork").Pool(workers) as pool:   # 자식은 CPU(토크나이저)만 사용
            outs = pool.map(_render_one, [st["example"] for st in targets], chunksize=8)
    for st, s in zip(targets, outs):
        st["prompt"] = s
    print(f"[grpo] 프롬프트 사전렌더 {len(targets)}개 (workers={workers}, {time.time()-t0:.1f}s)")
    return len(targets)


def load_groups(path: Path) -> list[dict]:
    """rollout jsonl: 각 줄 = {theorem, attempts:[{steps:[{prompt,tactic}], reward}]}."""
    groups = []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if line:
            groups.append(json.loads(line))
    return groups


def build_value_head(hidden: int, arch: str, device: str):
    """PPO critic(value head) 아키텍처. 입력 (B, hidden) → 출력 (B, 1) 스칼라 V(s).
    전부 policy backbone 공유(마지막 hidden state 위 head). 표준 RLHF(a1) 방식.
      linear : Linear(H→1)              — 현행. TRL AutoModelForCausalLMWithValueHead 기본.
      mlp    : H→512→GELU→1             — 1-hidden MLP. 비선형 표현력 추가.
      mlp2   : H→512→GELU→128→GELU→1    — 2-hidden MLP. 더 깊은 critic.
      tanh   : H→512→Tanh→1             — Tanh(제한된 출력범위, value 안정화 통설).
      sigmoid: H→512→GELU→1→Sigmoid     — 출력 [0,1] 강제 = V(s)=P(provable). BCE loss 와 결합
               (reward∈{0,1} 이면 확률 추정이 정합적, GPT-f/HTPS provability 방식).
    """
    import torch.nn as nn
    if arch == "linear":
        head = nn.Linear(hidden, 1)
    elif arch == "mlp":
        head = nn.Sequential(nn.Linear(hidden, 512), nn.GELU(), nn.Linear(512, 1))
    elif arch == "mlp2":
        head = nn.Sequential(nn.Linear(hidden, 512), nn.GELU(),
                             nn.Linear(512, 128), nn.GELU(), nn.Linear(128, 1))
    elif arch == "tanh":
        head = nn.Sequential(nn.Linear(hidden, 512), nn.Tanh(), nn.Linear(512, 1))
    elif arch == "sigmoid":
        head = nn.Sequential(nn.Linear(hidden, 512), nn.GELU(), nn.Linear(512, 1), nn.Sigmoid())
    else:
        raise ValueError(f"unknown value_arch: {arch}")
    return head.float().to(device)


def _flatten_prompt(st, collate_fn):
    if "prompt" in st:
        return st["prompt"]
    assert collate_fn is not None, "example 기반 rollout엔 collate_fn 필요"
    return collate_fn(st["example"])


def flatten_group(group: dict, collate_fn=None, process: bool = False, luffy: bool = False,
                  vine: bool = False, dapo: bool = False,
                  overlong_cap: float = 18.0, overlong_buffer: float = 4.0,
                  sft: bool = False, ppo: bool = False,
                  shape_gold: bool = False, shape_coef: float = 0.3,
                  dpo: bool = False, dpo_max_per_state: int = 2):
    """그룹 → (prompts, completions, adv_outcome, adv_process, golds).

    adv_outcome : 시도(attempt) 단위 그룹상대 advantage를 그 시도의 모든 step에 broadcast(기존 동작).
    adv_process : (process=True 일 때) **checker 기반 per-tactic advantage**(2606.20068).
                  그룹 안 모든 step의 φ를 모아 표준화한다. process=False면 전부 0.
    golds       : (luffy=True 일 때) step 이 off-policy gold 궤적에서 왔는지(bool). 학습 루프가
                  gold row 는 luffy_batch_loss(clip 없이 shaping), 나머지는 표준 GRPO 로 처리.

    ★ dead group 이 살아나는 지점: 그룹의 모든 시도가 실패하면 outcome reward가 전부 0 →
      adv_outcome 이 전부 0 → 기존 GRPO는 그 그룹을 통째로 버렸다(40개 중 28개가 이 경우).
      process reward는 같은 실패 안에서도 '에러 난 tactic(-0.10)' vs '유효했지만 못 끝낸 tactic(-0.05)'
      를 구분하므로 **신호가 남는다**. LUFFY 는 대신 gold(정답, r=1) 를 dead group 에 섞어 신호를 만든다.

    step이 'prompt'(문자열)를 가지면 그대로, 'example'(json)를 가지면 collate_fn으로
    서버와 동일한 prompt 문자열 재현(collate_fn(example_json) → str)."""
    # ★ 빈 시도(steps=[], reward=0: 초기검사 실패/추천 없음) 제외.
    #   이들은 gradient row 를 하나도 안 내면서 reward=0 으로 그룹 baseline(mean)만 낮춰
    #   실제 row 들의 advantage 를 왜곡한다(양수는 부풀고 음수는 깊어짐). GRPO 대칭성 위반.
    attempts = [a for a in group["attempts"] if a["steps"]]
    if not attempts:
        return [], [], [], [], []

    # ★ validity DPO(BFS-Prover 2502.03438 식): **같은 proof state** 에서
    #   chosen=VALID tactic / rejected=INVALID(Coq 에러) tactic 인접쌍을 만든다.
    #   반환 리스트는 [chosen0, rejected0, chosen1, rejected1, ...] 순서(짝=chosen).
    #   ★ dead group 에서도 쌍이 나온다 — 증명을 못 찾아도 "에러 tactic" 사실은 남으므로.
    #   prompt 는 VALID step 의 것을 양쪽에 써서 두 row 의 prompt 를 동일하게 보장(DPO 전제).
    if dpo:
        import re as _re
        _ws = _re.compile(r"\s+")
        def _n(s): return _ws.sub(" ", s or "").strip()
        st_valid: dict = {}   # state -> {tactic: step}
        st_inval: dict = {}
        for a in attempts:
            if a.get("off_policy"):
                continue
            for st in a.get("steps", []):
                k = _n(st.get("state_key", ""))
                if not k:
                    continue
                d = st_inval if st.get("result") == "INVALID" else st_valid
                d.setdefault(k, {}).setdefault(st.get("tactic", ""), st)
        prompts, comps = [], []
        for k, vmap in st_valid.items():
            bad = {t: s for t, s in st_inval.get(k, {}).items() if t not in vmap}
            if not bad:
                continue
            pr = _flatten_prompt(next(iter(vmap.values())), collate_fn)
            made = 0
            for vt in vmap:
                for bt in bad:
                    if made >= dpo_max_per_state:
                        break
                    prompts += [pr, pr]        # 동일 prompt (DPO 전제)
                    comps += [vt, bt]          # 짝=chosen(VALID), 홀=rejected(INVALID)
                    made += 1
                if made >= dpo_max_per_state:
                    break
        n = len(prompts)
        # advs 는 안 씀(DPO는 선호쌍만) — 스킵 가드 통과용으로 1.0
        return prompts, comps, [1.0] * n, [0.0] * n, [False] * n

    # ★ Potential-based shaping(Ng 1999): gold 중간상태 집합으로 Φ(s)∈{0,1} 정의,
    #   per-step advantage = A_outcome + coef·(Φ(s_{t+1})−Φ(s_t)).
    #   ★ 이론 보장: potential 형태(F=γΦ'−Φ, γ=1, Φ(terminal)=0)라 **최적 정책 불변** —
    #   gold 신호를 정책 왜곡 없이 dense 하게 주입. gold(off_policy) 궤적은 **학습에서 제외**
    #   (Φ 상태셋 공급용만) → 순수 on-policy, covariate shift 없음.
    if shape_gold:
        import re as _re
        _ws = _re.compile(r"\s+")
        def _n(s): return _ws.sub(" ", s or "").strip()
        gold_states = set()
        for a in attempts:
            if a.get("off_policy"):
                for st in a["steps"]:
                    gold_states.add(_n(st.get("state_key", "")))
        onp = [a for a in attempts if not a.get("off_policy")]
        if not onp:
            return [], [], [], [], []
        rewards_o = torch.tensor([a["reward"] for a in onp], dtype=torch.float)
        adv_o = group_advantages(rewards_o)
        prompts, comps, advs_out = [], [], []
        for i, a in enumerate(onp):
            steps = a["steps"]
            for t, st in enumerate(steps):
                phi_cur = 1.0 if _n(st.get("state_key", "")) in gold_states else 0.0
                if st.get("result") == "COMPLETE":
                    phi_next = 0.0                       # terminal: Φ=0 (정책 불변 조건)
                elif t + 1 < len(steps):
                    phi_next = 1.0 if _n(steps[t+1].get("state_key", "")) in gold_states else 0.0
                else:
                    phi_next = phi_cur                   # 관측 없음(cutoff/INVALID) → F=0 안전
                prompts.append(_flatten_prompt(st, collate_fn))
                comps.append(st["tactic"])
                advs_out.append(float(adv_o[i]) + shape_coef * (phi_next - phi_cur))
        n = len(prompts)
        return prompts, comps, advs_out, [0.0] * n, [False] * n

    # ★ PPO(actor-critic): 모든 attempt 의 step 을 쓰되 return=그 attempt 의 proof 보상(0/1).
    #   그룹정규화 없음(critic V(s) 가 baseline). advantage=return−V 는 train 에서. dead group 도 학습(−V 신호).
    if ppo:
        prompts, comps, returns = [], [], []
        for a in attempts:
            if a.get("off_policy"):
                continue  # ★ PPO는 on-policy — gold(off_policy) 시도 제외
            for st in a["steps"]:
                prompts.append(_flatten_prompt(st, collate_fn))
                comps.append(st["tactic"])
                returns.append(float(a["reward"]))
        n = len(prompts)
        return prompts, comps, returns, [0.0] * n, [False] * n

    # ★ RFT/expert-iteration(SFT): 성공 궤적(reward≥1)의 step 만 뽑아 순수 MLE.
    #   advantage/group 없음. self-RFT(모델 성공)=on-policy=shift 없음. gold(off_policy)도 성공이면 포함.
    if sft:
        prompts, comps = [], []
        for a in attempts:
            if a["reward"] >= 1.0:
                for st in a["steps"]:
                    prompts.append(_flatten_prompt(st, collate_fn))
                    comps.append(st["tactic"])
        n = len(prompts)
        return prompts, comps, [1.0] * n, [0.0] * n, [True] * n

    # ★ VinePPO: step 별 MC advantage(adv_vine)를 그 예제의 advantage 로 직접 쓴다.
    #   그룹정규화 없음(MC advantage V(s')−V(s) 자체가 proper advantage). process/luffy 미사용.
    if vine:
        prompts, comps, advs_out = [], [], []
        for a in attempts:
            for st in a["steps"]:
                prompts.append(_flatten_prompt(st, collate_fn))
                comps.append(st["tactic"])
                advs_out.append(float(st.get("adv_vine", 0.0)))
        n = len(prompts)
        return prompts, comps, advs_out, [0.0] * n, [False] * n

    rewards = torch.tensor([a["reward"] for a in attempts], dtype=torch.float)
    # ★ DAPO overlong reward shaping(4기법 중 ④): 그룹상대 advantage 계산 **전에** 보상을 길이로 감점.
    #   length=시도의 step 수. 짧게 끝난 성공은 무해, 한계까지 끌고간 장황한 시도만 눌러 신호 품질↑.
    if dapo:
        lengths = torch.tensor([len(a["steps"]) for a in attempts], dtype=torch.float)
        rewards = overlong_shaped_rewards(rewards, lengths, overlong_cap, overlong_buffer)
    # ★ LUFFY: gold(off-policy) 시도가 섞여 있으면 std-floor advantage 를 쓴다.
    #   dead group(전부 0)+gold(1) 는 std 가 극히 작아 표준 표준화 시 advantage 가 폭발한다.
    has_gold = luffy and any(a.get("off_policy") for a in attempts)
    adv = group_advantages_with_gold(rewards) if has_gold else group_advantages(rewards)

    phis: list[float] = []
    if process:
        for a in attempts:
            phis.extend(checker_process_rewards(a))
        phis = normalize_process(phis)                    # 그룹 단위 표준화

    prompts, comps, advs_out, advs_proc, golds = [], [], [], [], []
    k = 0
    for i, a in enumerate(attempts):
        attempt_gold = bool(a.get("off_policy"))       # LUFFY: gold 시도 전체가 off_policy
        for st in a["steps"]:
            # ★ opener(pre-loop planner_opening) step 은 example=None (opener가 낸 것, frozen).
            #   executor GRPO 대상 아님 → 건너뜀. (안 그러면 collate_fn(None) 크래시.)
            if st.get("example") is None or st.get("planner_opening"):
                continue
            prompts.append(_flatten_prompt(st, collate_fn))
            comps.append(st["tactic"])
            advs_out.append(float(adv[i]))
            advs_proc.append(float(phis[k]) if process and k < len(phis) else 0.0)
            # ★ off_policy 는 step 단위 우선(BREAD: 한 궤적 안 gold 다리 step 만 off_policy),
            #   없으면 attempt 단위(LUFFY: gold 시도 전체).
            golds.append(bool(st.get("off_policy", attempt_gold)))
            k += 1
    return prompts, comps, advs_out, advs_proc, golds


def train(
    groups: list[dict],
    model,
    ref_model,
    tokenizer,
    max_len: int,
    epochs: int,
    lr: float,
    clip_eps: float,
    kl_beta: float,
    micro_bsz: int,
    device: str,
    save_dir: Optional[Path],
    collate_fn=None,
    process: bool = False,
    denom_const: Optional[float] = None,
    luffy: bool = False,
    luffy_gamma: float = 0.1,
    vine: bool = False,
    luffy_kl: bool = False,
    dapo: bool = False,
    clip_eps_high: Optional[float] = None,
    curriculum_anneal: bool = False,
    overlong_cap: float = 18.0,
    overlong_buffer: float = 4.0,
    sft: bool = False,
    dapg: bool = False,
    dapg_l0: float = 0.1,
    dapg_l1: float = 0.999,
    ppo: bool = False,
    value_head=None,
    value_coef: float = 0.5,
    value_arch: str = "linear",
    awac: bool = False,
    awac_lam: float = 1.0,
    shape_gold: bool = False,
    shape_coef: float = 0.3,
    dpo: bool = False,
    dpo_beta: float = 0.1,
    value_pretrain: int = 0,
    save_every: int = 0,
    ckpt_dir: Optional[Path] = None,
    keep_every: int = 5000,
    log_every: int = 50,
    loss_log: Optional[Path] = None,
    resume_state: Optional[dict] = None,
    opt_state: Optional[dict] = None,
):
    if dpo and micro_bsz % 2 != 0:
        micro_bsz += 1  # ★ DPO는 (chosen,rejected) 인접쌍 — 마이크로배치가 짝수여야 쌍이 안 갈림
        print(f"[grpo] DPO: micro_bsz 를 짝수 {micro_bsz} 로 조정(쌍 정렬)")
    _opt_params = [p for p in model.parameters() if p.requires_grad]
    if ppo and value_head is not None:
        _opt_params = _opt_params + list(value_head.parameters())  # critic 도 함께 업데이트
    opt = torch.optim.AdamW(_opt_params, lr=lr)
    if opt_state is not None:                       # ★ resume: optimizer(Adam moment) 복원
        try:
            opt.load_state_dict(opt_state)
            print("[ckpt] optimizer state 복원")
        except (ValueError, KeyError) as e:
            print(f"[ckpt] optimizer state 복원 실패({e}) — 새 optimizer 로 계속")

    # ── ★ 중간 체크포인트(save_every step) + 마일스톤 보존 정리 ──
    #   GPU 가 끊겨도 최대 save_every step 만 잃는다. keep_every(기본 5000) 배수는 영구 보존,
    #   그 사이 중간본은 다음 마일스톤 도달 시 삭제(디스크 관리). ckpt_rotate 를 학습 안에서 수행.
    import shutil as _shutil

    def _prune_ckpts(cur: int):
        if ckpt_dir is None or keep_every <= 0 or cur % keep_every:
            return
        gone = []
        for d in sorted(ckpt_dir.glob("step-*")):
            try:
                s = int(d.name.split("-")[1])
            except (IndexError, ValueError):
                continue
            if s < cur and s % keep_every:          # 마일스톤(5000배수) 아닌 중간본만 삭제
                _shutil.rmtree(d, ignore_errors=True)
                gone.append(s)
        if gone:
            print(f"[ckpt] 마일스톤 {cur} 도달 → 중간 체크포인트 삭제: {gone}")

    def _save_ckpt(cur: int, ep_i: int, gi: int, tag: str = ""):
        if ckpt_dir is None:
            return
        d = ckpt_dir / f"step-{cur}"
        d.mkdir(parents=True, exist_ok=True)
        model.save_pretrained(str(d))
        torch.save(opt.state_dict(), d / "optimizer.pt")
        (d / "trainer_state.json").write_text(json.dumps(
            {"step": cur, "epoch": ep_i, "group_idx": gi, "epochs": epochs}), encoding="utf-8")
        (ckpt_dir / "latest.json").write_text(json.dumps(
            {"step": cur, "epoch": ep_i, "group_idx": gi, "path": str(d)}), encoding="utf-8")
        print(f"[ckpt] step {cur} 저장 → {d}{tag}", flush=True)
        _prune_ckpts(cur)

    # resume: 저장 시점(epoch, group_idx) 까지 건너뛴다(그룹 순서 결정적).
    _rs_ep = int(resume_state.get("epoch", 0)) if resume_state else 0
    _rs_gi = int(resume_state.get("group_idx", -1)) if resume_state else -1
    _rs_step = int(resume_state.get("step", 0)) if resume_state else 0
    if resume_state:
        print(f"[ckpt] resume: step {_rs_step} (epoch {_rs_ep}, group_idx {_rs_gi} 이후부터)")
    _loss_fp = None
    if loss_log is not None:
        loss_log.parent.mkdir(parents=True, exist_ok=True)
        _loss_fp = open(loss_log, "a", encoding="utf-8")
    _win: list[float] = []          # 최근 log_every step loss(추세 확인용)
    _pending_save = False           # save_every 도달 표식(저장은 그룹 경계에서)
    # ── ★ VAPO value-pretraining: 정책 업데이트 전에 critic(value head)만 먼저 fit ──
    #   single-round PPO 는 V 가 랜덤에서 출발해 안 여무는 문제(→ easy-완화 효과 약함).
    #   VAPO(2504.05118) 의 핵심 = value-pretraining. 정책 freeze, MSE(V,return)만 warmup.
    if ppo and value_pretrain > 0 and value_head is not None:
        v_opt = torch.optim.AdamW(value_head.parameters(), lr=lr * 20)  # head만이라 lr↑
        for vp in range(value_pretrain):
            vl_sum = 0.0; vn = 0
            for group in groups:
                pr, co, ret, _, _ = flatten_group(group, collate_fn, ppo=True)
                if not pr:
                    continue
                for s in range(0, len(pr), micro_bsz):
                    ids, attn, cmask = build_completion_batch(
                        tokenizer, pr[s:s+micro_bsz], co[s:s+micro_bsz], max_len, device)
                    rt = torch.tensor(ret[s:s+micro_bsz], device=device)
                    with torch.no_grad():
                        out = model(input_ids=ids, attention_mask=attn, output_hidden_states=True)
                        h = out.hidden_states[-1].float()
                    m0 = cmask.float(); fc = m0.argmax(dim=1); sp = (fc-1).clamp(min=0)
                    rows = torch.arange(ids.size(0), device=ids.device)
                    V = value_head(h[rows, sp]).squeeze(-1)
                    if value_arch == "sigmoid":                       # 확률 → BCE
                        _v = V.clamp(1e-6, 1 - 1e-6)
                        vloss = -(rt * torch.log(_v) + (1 - rt) * torch.log(1 - _v)).mean()
                    else:
                        vloss = ((rt - V) ** 2).mean()
                    v_opt.zero_grad(); vloss.backward(); v_opt.step()
                    vl_sum += float(vloss); vn += 1
            print(f"[grpo] value-pretrain epoch {vp}: value_loss={vl_sum/max(vn,1):.4f}")
    n_dead_revived = 0
    n_gold_rows = 0
    gstep = _rs_step  # DAPG 감쇠용 전역 step 카운터 (λ₁^gstep) / resume 시 이어서 셈
    # ★ (1) anneal-to-s0 (R³/Florensa): 학습 순서를 near-goal(작은 remaining) → s0(전체) 로.
    #   시작상태 분포를 점진적으로 s0 까지 넓혀 커버 → endgame 스킬을 s0 전이로 잇는다.
    #   start 라벨에서 remaining 파싱: "curr_r3"/"adapt_r3"→3, "s0"→∞(맨 뒤). 정적 revcurr 의 개선.
    if curriculum_anneal:
        import re as _re
        def _remaining(g):
            lab = str(g.get("start", "s0"))
            m = _re.search(r"_r(\d+)", lab)
            if m:
                return int(m.group(1))
            return 10**9  # s0/기타 = 가장 멀리(맨 뒤에서 학습)
        groups = sorted(groups, key=_remaining)  # 오름차순: 근접상태 먼저
        bands = [_remaining(g) for g in groups]
        print(f"[grpo] anneal-to-s0: {len(groups)}그룹 near-goal→s0 정렬 "
              f"(remaining {min(bands)}~{'s0' if max(bands)>=10**9 else max(bands)})")
    for ep in range(epochs):
        if ep < _rs_ep:                     # ★ resume: 이미 끝난 epoch 건너뜀
            print(f"[ckpt] epoch {ep} 는 체크포인트 이전 — 건너뜀")
            continue
        tot_loss = tot_kl = n = 0.0
        tot_margin = 0.0; n_pairs = 0  # ★ DPO margin 진단
        tot_clip = tot_maxr = 0.0  # ★ ratio clip 진단: clip 밖 토큰 비율 + max ρ
        # ── ★ 통합 진단 로거(어떤 알고리즘이 이 문제셋에 맞나 판단용) ──
        #   dead: DAPO(dynamic sampling)/GRPO std편향 판단 | clip 상/하 분리: DAPO clip-higher
        #   value/EV: PPO/VAPO critic 유효성 | entropy: collapse | len-adv: GRPO 토큰길이 편향
        dg_n = dg_dead = dg_mixed = 0          # 그룹 수 / dead / mixed
        dg_std_sum = 0.0                       # group std 합(avg 용)
        dg_solve_hist = [0]*9                  # 그룹당 성공 attempt 수 히스토그램(0..8+)
        m_cliphi = m_cliplo = 0.0              # clip 상/하 프랙션 합
        m_vloss_sum = 0.0; m_v_sum = 0.0; m_v_sq = 0.0; m_v_n = 0  # value 통계
        m_ret_sum = 0.0; m_ret_sq = 0.0; m_rv_sq = 0.0            # EV(explained var) 용
        m_ent_sum = 0.0; m_ent_n = 0           # policy entropy
        m_len_sum = 0; m_len_n = 0             # 응답(tactic) 토큰 길이
        m_la_x = m_la_y = m_la_xy = m_la_xx = m_la_yy = 0.0; m_la_n = 0  # corr(len, adv)
        for _gi, group in enumerate(groups):
            if ep == _rs_ep and _gi <= _rs_gi:   # ★ resume: 저장 시점 그룹까지 건너뜀
                continue
            # ── 진단: 그룹 단위 통계(학습 스킵 여부와 무관하게 관측) ──
            _onp = [a for a in group["attempts"] if a.get("steps") and not a.get("off_policy")]
            if _onp:
                _rs = [float(a["reward"]) for a in _onp]
                _sv = sum(1 for r in _rs if r >= 1)
                dg_n += 1
                if all(r < 1 for r in _rs): dg_dead += 1
                elif _sv < len(_rs): dg_mixed += 1
                dg_solve_hist[min(_sv, 8)] += 1
                if len(_rs) >= 2:
                    import statistics as _st
                    dg_std_sum += _st.pstdev(_rs)
            prompts, comps, advs, advs_p, golds = flatten_group(
                group, collate_fn, process, luffy or awac, vine, dapo,
                overlong_cap, overlong_buffer, sft=sft, ppo=ppo,
                shape_gold=shape_gold, shape_coef=shape_coef, dpo=dpo
            )
            if not prompts:
                continue
            if sft:
                n_gold_rows += len(prompts)  # SFT: 학습한 성공-궤적 step 수
            outcome_dead = all(abs(a) < 1e-8 for a in advs)
            process_dead = all(abs(a) < 1e-8 for a in advs_p)
            # ★ PPO 는 dead group(전부 실패)도 학습한다 — advantage=return−V(s)=−V≠0(critic 신호). 스킵 안 함.
            if outcome_dead and process_dead and not any(golds) and not ppo:
                continue  # 신호 전무 → 스킵 (gold 있으면 LUFFY 신호, ppo 면 −V 신호로 유지)
            if outcome_dead and ep == 0 and (process or luffy):
                n_dead_revived += 1  # outcome은 죽었지만 process/gold 가 살린 그룹
            for s in range(0, len(prompts), micro_bsz):
                bp = prompts[s : s + micro_bsz]
                bc = comps[s : s + micro_bsz]
                ba = torch.tensor(advs[s : s + micro_bsz], device=device)
                bg = golds[s : s + micro_bsz]   # bool per row
                ids, attn, cmask = build_completion_batch(tokenizer, bp, bc, max_len, device)
                with torch.no_grad():
                    logp_ref = sequence_token_logprobs(ref_model, ids, attn)
                    logp_old = logp_ref  # 온폴리시 첫 라운드: old=ref(시작 정책)
                if ppo:
                    # ★ PPO: 한 forward 에서 logp + V(s) 동시 계산(hidden state 필요).
                    out = model(input_ids=ids, attention_mask=attn, output_hidden_states=True)
                    _logits = out.logits[:, :-1, :]
                    _lp = torch.log_softmax(_logits.float(), dim=-1)
                    _tok = _lp.gather(-1, ids[:, 1:].unsqueeze(-1)).squeeze(-1)
                    _pad = torch.zeros((ids.shape[0], 1), device=_tok.device)
                    logp_new = torch.cat([_pad, _tok], dim=1)          # (B,T)
                    h = out.hidden_states[-1].float()                 # (B,T,H)
                    m0 = cmask.float()
                    first_comp = m0.argmax(dim=1)                     # 첫 completion 위치
                    state_pos = (first_comp - 1).clamp(min=0)         # 그 직전=state(프롬프트 끝)
                    rows = torch.arange(ids.size(0), device=ids.device)
                    V = value_head(h[rows, state_pos]).squeeze(-1)    # (B,) critic V(s)
                    loss, kl = ppo_batch_loss(
                        logp_new, logp_old, V, ba, cmask,
                        clip_eps=clip_eps, value_coef=value_coef,
                        value_bce=(value_arch == "sigmoid"),          # sigmoid critic → BCE
                    )  # kl 자리에 value_loss 반환(모니터링)
                    with torch.no_grad():
                        _r = torch.exp(logp_new - logp_old); _mf = cmask.float()
                        _hi = ((_r > 1.0 + clip_eps) * _mf).sum() / _mf.sum().clamp(min=1)
                        _lo = ((_r < 1.0 - clip_eps) * _mf).sum() / _mf.sum().clamp(min=1)
                        tot_clip += float(_hi + _lo)
                        m_cliphi += float(_hi); m_cliplo += float(_lo)
                        tot_maxr = max(tot_maxr, float((_r * _mf + (1 - _mf)).max()))
                        # ★ critic 진단: value_loss / V분포 / EV(explained variance) 재료
                        m_vloss_sum += float(kl)                       # ppo는 kl자리=value_loss
                        m_v_sum += float(V.sum()); m_v_sq += float((V**2).sum()); m_v_n += V.numel()
                        m_ret_sum += float(ba.sum()); m_ret_sq += float((ba**2).sum())
                        m_rv_sq += float(((ba - V)**2).sum())          # Var(return−V) 재료
                        # entropy / 길이 (collapse·길이편향 진단)
                        _p = torch.exp(logp_new); _ent = -(logp_new * _p * _mf).sum() / _mf.sum().clamp(min=1)
                        m_ent_sum += float(_ent); m_ent_n += 1
                        m_len_sum += int(_mf.sum()); m_len_n += _mf.shape[0]
                    opt.zero_grad(); loss.backward()
                    torch.nn.utils.clip_grad_norm_(_opt_params, 1.0)
                    opt.step()
                    tot_loss += float(loss); tot_kl += float(kl); n += 1; gstep += 1
                    continue
                logp_new = sequence_token_logprobs(model, ids, attn)
                if dpo:
                    # ★ validity DPO: 짝=VALID(chosen) / 홀=INVALID(rejected) 인접쌍.
                    loss, margin = dpo_batch_loss(logp_new, logp_ref, cmask, beta=dpo_beta)
                    kl = torch.zeros((), device=device)
                    tot_margin += float(margin); n_pairs += 1
                elif awac:
                    # ★ AWAC/AWR: exp(A/λ) 가중 BC — KL-제약 정책개선의 닫힌 해(OOD 차단).
                    #   gold 포함 모든 데이터 row 를 가중 모방. clip/ratio/KL 없음.
                    loss = awac_batch_loss(logp_new, ba, cmask, lam=awac_lam)
                    kl = torch.zeros((), device=device)
                    n_gold_rows += int(sum(bg))
                elif sft:
                    # ★ RFT/expert-iteration: 순수 MLE(+ KL anchor). 성공 궤적 completion 최대화.
                    loss, kl = sft_batch_loss(logp_new, logp_ref, cmask, kl_beta=kl_beta)
                elif dapg:
                    # ★ DAPG: on-policy row → 표준 GRPO, gold(off_policy) row → 감쇠 BC(λ₀·λ₁^gstep).
                    #   gold 기여가 학습 진행에 따라 소멸 → LUFFY 회귀(무제약 gold 견인) 방지.
                    gmask = torch.tensor(bg, device=device)
                    w_k = dapg_l0 * (dapg_l1 ** gstep)
                    kl = torch.zeros((), device=device)
                    terms = []
                    if (~gmask).any():
                        oi = (~gmask).nonzero(as_tuple=True)[0]
                        loss_on, kl = grpo_batch_loss(
                            logp_new[oi], logp_old[oi], logp_ref[oi], ba[oi], cmask[oi],
                            clip_eps=clip_eps, kl_beta=kl_beta,
                        )
                        terms.append(loss_on)
                    if gmask.any():
                        gi = gmask.nonzero(as_tuple=True)[0]
                        terms.append(dapg_demo_loss(logp_new[gi], cmask[gi], w_k))
                        n_gold_rows += int(gi.numel())
                    loss = sum(terms)
                elif luffy and any(bg):
                    # ★ LUFFY 혼합 목적: 한 micro-batch 안에서
                    #   - gold(off-policy) row → luffy_batch_loss(clip 없음 + shaping, KL 없음)
                    #   - 나머지 on-policy row → 표준 clipped GRPO
                    #   두 항을 더한다(각자 tactic-토큰 평균으로 정규화됨 — LUFFY 원논문과 동일).
                    gmask = torch.tensor(bg, device=device)
                    kl = torch.zeros((), device=device)
                    terms = []
                    if (~gmask).any():
                        oi = (~gmask).nonzero(as_tuple=True)[0]
                        # ★ (2) LUFFY exploration 보존: on-policy 항에 clip-higher 적용(entropy collapse 방지).
                        loss_on, kl = grpo_batch_loss(
                            logp_new[oi], logp_old[oi], logp_ref[oi], ba[oi], cmask[oi],
                            clip_eps=clip_eps, kl_beta=kl_beta, clip_eps_high=clip_eps_high,
                        )
                        terms.append(loss_on)
                    gi = gmask.nonzero(as_tuple=True)[0]
                    if luffy_kl:
                        # ★ Conservative: gold 항에 KL(π_θ‖fix) 복원 → 회귀 방지
                        loss_g, kl_g = luffy_kl_batch_loss(
                            logp_new[gi], logp_ref[gi], ba[gi], cmask[gi],
                            gamma=luffy_gamma, kl_beta=kl_beta,
                        )
                        terms.append(loss_g)
                    else:
                        terms.append(
                            luffy_batch_loss(logp_new[gi], ba[gi], cmask[gi], gamma=luffy_gamma)
                        )
                    n_gold_rows += int(gi.numel())
                    loss = sum(terms)
                elif dapo:
                    # ★ (3) DAPO: clip-higher(비대칭) + token-level loss + KL 제거.
                    #   dynamic sampling(rollout dyn_resample)·overlong shaping(flatten)은 이미 반영됨.
                    #   ★ KL 은 DAPO 정의상 제거 → 전역 kl_beta(기본 0.04) 무시하고 0 고정(리뷰 #2).
                    loss, kl = dapo_batch_loss(
                        logp_new, logp_old, logp_ref, ba, cmask,
                        clip_eps_low=clip_eps,
                        clip_eps_high=clip_eps_high if clip_eps_high is not None else 0.28,
                        kl_beta=0.0,
                    )
                elif process:
                    bap = torch.tensor(advs_p[s : s + micro_bsz], device=device)
                    # A = A_outcome (완성 토큰 전체) + 1[첫 토큰] · A_process
                    #   논문 검증: first-token 59.2 > all-tokens 57.8 > last-token 57.5.
                    #   tactic 의 첫 토큰(=전략을 고르는 키워드)에만 process credit 을 건다.
                    #   outcome 항은 유지한다 — 논문의 negative result: tactic-only 보상은
                    #   조기수렴을 부른다.
                    m = cmask.float()
                    first = torch.zeros_like(m)
                    idx = m.argmax(dim=1)                     # 행별 첫 완성토큰 위치
                    rows = torch.arange(m.size(0), device=m.device)
                    first[rows, idx] = m[rows, idx]           # 완성토큰이 없는 행은 0 유지

                    # ★ 길이 보정 (없으면 PRM 이 조용히 무력화된다):
                    #   grpo_batch_loss* 는 시퀀스 목적을 **토큰 평균**(Σ/|a|)으로 낸다(grpo.py:80-83).
                    #   process advantage 는 첫 토큰 1개에만 걸리므로, 평균을 거치면 유효 가중치가
                    #   bap/|a| 가 되어 **tactic 길이에 반비례해 희석**된다.
                    #     3토큰 tactic → 1/3 = 0.333 | 13토큰 → 1/13 = 0.077  (4배 차이)
                    #   실측: Coq이 거부한 tactic 은 통과한 것보다 평균 2.10배 길다(18.7 vs 8.9 토큰).
                    #   즉 **가장 강하게 벌줘야 할 tactic 에서 PRM 신호가 가장 약해진다.**
                    #   → |a| 를 곱해 상쇄한다. 평균을 거친 뒤 유효 가중치가 정확히 bap 이 된다.
                    n_tok = m.sum(dim=1).clamp(min=1.0)       # |a|
                    # ★ 곱하는 scale 은 perstep 의 분모와 반드시 일치해야 유효 가중치가 bap 이 된다.
                    #   denom_const=None → 분모 |a| → n_tok 곱함(상쇄).
                    #   denom_const=C    → 분모 C  → C 곱해야 상쇄(n_tok 곱하면 길이비례로 재편향).
                    scale = (
                        n_tok if denom_const is None
                        else torch.full_like(n_tok, float(denom_const))
                    )
                    adv_tokens = (
                        ba.unsqueeze(1) * m
                        + (bap * scale).unsqueeze(1) * first
                    )
                    loss, kl = grpo_batch_loss_perstep(
                        logp_new, logp_old, logp_ref, adv_tokens, cmask,
                        clip_eps=clip_eps, kl_beta=kl_beta, denom_const=denom_const,
                    )
                else:
                    if denom_const is not None:
                        # outcome-only 경로도 상수 정규화를 쓰려면 perstep 로 우회(동일 일반화)
                        adv_tokens = ba.unsqueeze(1) * cmask.float()
                        loss, kl = grpo_batch_loss_perstep(
                            logp_new, logp_old, logp_ref, adv_tokens, cmask,
                            clip_eps=clip_eps, kl_beta=kl_beta, denom_const=denom_const,
                        )
                    else:
                        # ★ clip_eps_high 전달: LUFFY 의 gold-없는 micro-batch(=on-policy row 대부분)도
                        #   clip-higher 를 받아야 (2) 가 실효(리뷰 #1). 일반 GRPO 는 None → 대칭(무변화).
                        loss, kl = grpo_batch_loss(
                            logp_new, logp_old, logp_ref, ba, cmask,
                            clip_eps=clip_eps, kl_beta=kl_beta, clip_eps_high=clip_eps_high,
                        )
                # ★ ratio clip 진단(로깅): clip 밖 토큰 비율(상/하 분리) + max ρ. sft 는 clip 없어 참고용.
                with torch.no_grad():
                    _r = torch.exp(logp_new - logp_old); _mf = cmask.float()
                    _hi = ((_r > 1.0 + clip_eps) * _mf).sum() / _mf.sum().clamp(min=1)
                    _lo = ((_r < 1.0 - clip_eps) * _mf).sum() / _mf.sum().clamp(min=1)
                    tot_clip += float(_hi + _lo)
                    m_cliphi += float(_hi); m_cliplo += float(_lo)
                    tot_maxr = max(tot_maxr, float((_r * _mf + (1 - _mf)).max()))
                    # entropy / 길이 / len-adv 상관 (collapse·GRPO 토큰길이 편향 진단)
                    _p = torch.exp(logp_new); _ent = -(logp_new * _p * _mf).sum() / _mf.sum().clamp(min=1)
                    m_ent_sum += float(_ent); m_ent_n += 1
                    _lens = _mf.sum(dim=1)                          # (B,) row별 tactic 토큰수
                    m_len_sum += int(_lens.sum()); m_len_n += _lens.shape[0]
                    _x = _lens.float(); _y = ba.float()             # corr(길이, advantage) 재료
                    m_la_x += float(_x.sum()); m_la_y += float(_y.sum())
                    m_la_xy += float((_x*_y).sum()); m_la_xx += float((_x**2).sum())
                    m_la_yy += float((_y**2).sum()); m_la_n += _x.numel()
                opt.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(
                    [p for p in model.parameters() if p.requires_grad], 1.0
                )
                opt.step()
                tot_loss += float(loss); tot_kl += float(kl); n += 1; gstep += 1
                # ── ★ step 단위 loss 로깅(추세 확인) + 중간 체크포인트 ──
                _win.append(float(loss))
                if log_every > 0 and gstep % log_every == 0:
                    _w = sum(_win) / max(len(_win), 1)
                    print(f"[step] gstep={gstep} ep={ep} loss(win{len(_win)})={_w:.4f} "
                          f"loss(ep평균)={tot_loss/max(n,1):.4f} kl={tot_kl/max(n,1):.4f}", flush=True)
                    if _loss_fp is not None:
                        _loss_fp.write(json.dumps({"step": gstep, "epoch": ep,
                                                   "loss_win": round(_w, 5),
                                                   "loss_ep": round(tot_loss/max(n, 1), 5),
                                                   "kl": round(tot_kl/max(n, 1), 5)}) + "\n")
                        _loss_fp.flush()
                    _win = []
                if save_every > 0 and gstep % save_every == 0:
                    _pending_save = True     # ★ 실제 저장은 그룹 끝에서(=resume 이 그룹경계로 정확)
            if _pending_save:
                _save_ckpt(gstep, ep, _gi)
                _pending_save = False
        print(f"[grpo] epoch {ep}: loss={tot_loss/max(n,1):.4f} kl={tot_kl/max(n,1):.4f} "
              f"steps={int(n)} clip_frac={tot_clip/max(n,1):.3f} max_ρ={tot_maxr:.2f}"
              + (f" dpo_margin={tot_margin/max(n_pairs,1):.3f}" if dpo else ""))
        # ── ★ 통합 진단 metrics(한 줄 JSON) — 어떤 알고리즘이 이 문제셋에 맞나 판단용 ──
        #   [metrics] 로 grep 하면 epoch별 지표 시계열 추출. PPO 아닌 경로는 value/EV=null.
        _nb = max(n, 1)
        _mn = max(m_v_n, 1)
        def _var(sq, s, cnt):  # population variance
            return sq/cnt - (s/cnt)**2 if cnt else 0.0
        _ev = None
        if m_v_n:
            _rv = _var(m_ret_sq, m_ret_sum, m_v_n)   # Var(return)
            _ev = 1.0 - (m_rv_sq/m_v_n)/_rv if _rv > 1e-9 else 0.0   # 1 − Var(ret−V)/Var(ret)
        _la = None
        if m_la_n > 1:
            _cov = m_la_xy/m_la_n - (m_la_x/m_la_n)*(m_la_y/m_la_n)
            _sx = (_var(m_la_xx, m_la_x, m_la_n))**0.5
            _sy = (_var(m_la_yy, m_la_y, m_la_n))**0.5
            _la = _cov/(_sx*_sy) if _sx > 1e-9 and _sy > 1e-9 else 0.0
        _algo = ("ppo" if ppo else "dpo" if dpo else "awac" if awac else "sft" if sft
                 else "dapo" if dapo else "shape_gold" if shape_gold else "luffy" if luffy
                 else "vine" if vine else "grpo")
        _metrics = {
            "algo": _algo, "epoch": ep, "steps": int(n),
            "loss": round(tot_loss/_nb, 4), "kl": round(tot_kl/_nb, 4),
            "dead_frac": round(dg_dead/max(dg_n, 1), 3),
            "mixed_frac": round(dg_mixed/max(dg_n, 1), 3),
            "avg_group_std": round(dg_std_sum/max(dg_n, 1), 4),
            "solve_hist": dg_solve_hist,
            "clip_hi": round(m_cliphi/_nb, 4), "clip_lo": round(m_cliplo/_nb, 4),
            "max_rho": round(tot_maxr, 2),
            "value_loss": (round(m_vloss_sum/_nb, 4) if ppo else None),
            "v_mean": (round(m_v_sum/_mn, 4) if m_v_n else None),
            "v_std": (round(_var(m_v_sq, m_v_sum, m_v_n)**0.5, 4) if m_v_n else None),
            "explained_var": (round(_ev, 4) if _ev is not None else None),
            "entropy": round(m_ent_sum/max(m_ent_n, 1), 4),
            "avg_len": round(m_len_sum/max(m_len_n, 1), 1),
            "len_adv_corr": (round(_la, 4) if _la is not None else None),
        }
        print(f"[metrics] {json.dumps(_metrics, ensure_ascii=False)}")
    if process:
        print(f"[grpo] process reward가 살린 dead group: {n_dead_revived}개 "
              f"(outcome advantage=0 이라 기존 GRPO는 버렸을 그룹)")
    if luffy:
        print(f"[grpo] LUFFY: gold row {n_gold_rows}개 학습, dead group 부활 {n_dead_revived}개 "
              f"(outcome=0 인데 gold 로 신호 생성)")
    if dapo:
        chi = clip_eps_high if clip_eps_high is not None else 0.28
        print(f"[grpo] DAPO: clip-higher(하한 {clip_eps}/상한 {chi}) + token-level loss + "
              f"KL{'제거' if kl_beta==0 else f'={kl_beta}'} + overlong(cap {overlong_cap}/buf {overlong_buffer})")
    if save_dir is not None:
        save_dir.mkdir(parents=True, exist_ok=True)
        model.save_pretrained(str(save_dir))
        print(f"[grpo] adapter 저장 → {save_dir}")
    if ckpt_dir is not None:                      # 마지막 step 체크포인트(+resume 표식 갱신)
        _save_ckpt(gstep, epochs - 1, len(groups) - 1, tag="  (final)")
        (ckpt_dir / "DONE").write_text(json.dumps({"step": gstep, "epochs": epochs}), encoding="utf-8")
    if _loss_fp is not None:
        _loss_fp.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rollouts", required=True, help="rollout jsonl (grpo_rollout.py 출력)")
    ap.add_argument("--model_name", required=True, help="base 모델(deepseek-coder-1.3b)")
    ap.add_argument("--init_adapter", default=None, help="rango LoRA adapter(시작 정책)")
    ap.add_argument("--save_dir", default="models/rango-grpo/adapter")
    ap.add_argument("--max_len", type=int, default=2048)
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--lr", type=float, default=1e-6)
    ap.add_argument("--clip_eps", type=float, default=0.2)
    ap.add_argument("--kl_beta", type=float, default=0.04)
    ap.add_argument("--ref_adapter", default=None,
        help="KL 기준 정책(고정). 지정 시 ref_model을 이 어댑터(예 π₀)에서 로드 → EI 누적 drift 차단. "
             "미지정 시 init_adapter(직전 라운드) 동결 복사=기존 동작.")
    ap.add_argument("--micro_bsz", type=int, default=4)
    ap.add_argument("--collator_conf", default=None,
                    help="example_collator yaml(rango training_conf). example 기반 rollout 재현용.")
    ap.add_argument("--denom_const", type=float, default=None,
                    help="length bias 제거(Dr.GRPO 2503.20783). 지정하면 시퀀스 목적을 토큰평균(Σ/|a|) "
                         "대신 **상수**로 나눈다. 미지정=기존 토큰평균. 권장값 16(평균 tactic 길이).")
    ap.add_argument("--process", action="store_true",
                    help="PRM-GRPO(2606.20068): coq-lsp 검증결과 기반 per-tactic process reward를 "
                         "각 tactic의 첫 토큰에 추가로 건다. outcome 항은 유지. "
                         "rollout에 step['result']가 있어야 한다.")
    ap.add_argument("--luffy", action="store_true",
                    help="LUFFY(2504.14945): rollout 그룹에 섞인 gold(off_policy=True) 궤적을 "
                         "clip 없이 shaping f(π_θ)=π_θ/(π_θ+γ) 로 학습(dead group 부활). "
                         "on-policy row 는 표준 GRPO. gold 주입은 grpo_rollout gold_file 로.")
    ap.add_argument("--luffy_gamma", type=float, default=0.1, help="LUFFY shaping γ.")
    ap.add_argument("--vine", action="store_true",
                    help="VinePPO(2410.01679): step 별 MC advantage(rollout 의 adv_vine)를 "
                         "그 예제 advantage 로. on-policy state MC value 라 gold 전이문제 없음. "
                         "rollout 을 vine_k>0 으로 수집해야 한다.")
    ap.add_argument("--luffy_kl", action="store_true",
                    help="Conservative LUFFY: gold 항에 KL(π_θ‖fix) 복원(회귀 방지). --luffy 와 함께.")
    ap.add_argument("--dapo", action="store_true",
                    help="DAPO(2503.14476) 4기법: clip-higher(비대칭) + token-level loss + KL제거 + "
                         "overlong reward shaping. dynamic sampling 은 rollout 을 dyn_resample>0 로 수집.")
    ap.add_argument("--clip_eps_high", type=float, default=None,
                    help="clip-higher 상한(1+ε_high). DAPO 기본 0.28. --luffy 와 쓰면 on-policy 항에 적용.")
    ap.add_argument("--curriculum_anneal", action="store_true",
                    help="(1) anneal-to-s0: 학습 순서를 near-goal(작은 remaining)→s0 로 정렬. "
                         "revcurr/adaptprefix 처럼 start 라벨에 remaining 이 있는 rollout 에 사용.")
    ap.add_argument("--overlong_cap", type=float, default=18.0,
                    help="DAPO overlong shaping: 이 step 수까지 감점 없음(≈max_steps). 초과분 선형 감점.")
    ap.add_argument("--overlong_buffer", type=float, default=4.0,
                    help="DAPO overlong shaping: cap 아래 buffer 구간에서 선형 감점 시작.")
    ap.add_argument("--sft", action="store_true",
                    help="RFT/expert-iteration: rollout 의 성공 궤적(reward≥1)만 골라 순수 MLE(SFT). "
                         "advantage/clip/group 없음. self-성공=on-policy(shift 없음). "
                         "--kl_beta>0 이면 fix anchor. dead group(성공 0)은 자동 스킵.")
    ap.add_argument("--dpo", action="store_true",
                    help="validity DPO(BFS-Prover 2502.03438): 같은 state에서 VALID tactic(chosen) vs "
                         "INVALID(Coq에러, rejected) 선호쌍 학습. dead group에서도 쌍이 나옴.")
    ap.add_argument("--dpo_beta", type=float, default=0.1, help="DPO 온도 β.")
    ap.add_argument("--awac", action="store_true",
                    help="AWAC/AWR: exp(A/λ) 가중 BC. KL-제약 정책개선의 닫힌 해 — OOD 차단(이론보장). "
                         "gold 주입 rollout(luffy.jsonl)과 함께 쓰면 gold 를 안전하게 활용.")
    ap.add_argument("--awac_lam", type=float, default=1.0, help="AWAC 온도 λ.")
    ap.add_argument("--shape_gold", action="store_true",
                    help="Potential-based shaping(Ng 1999): gold 중간상태 Φ 로 per-step dense 신호. "
                         "최적정책 불변(이론보장). gold 는 Φ 공급만, 학습은 순수 on-policy.")
    ap.add_argument("--shape_coef", type=float, default=0.3, help="shaping 계수.")
    ap.add_argument("--ppo", action="store_true",
                    help="PPO(actor-critic): 학습된 value head V(s) baseline. advantage=return−V. "
                         "GRPO(그룹평균)와 달리 dead group(전부실패)도 −V 신호로 학습. rollout 은 GRPO 와 동일.")
    ap.add_argument("--value_coef", type=float, default=0.5, help="PPO value(critic) loss 계수.")
    ap.add_argument("--value_arch", type=str, default="linear",
                    choices=["linear", "mlp", "mlp2", "tanh", "sigmoid"],
                    help="PPO critic 아키텍처(build_value_head). linear=현행, mlp/mlp2=깊은 MLP, tanh=제한출력.")
    ap.add_argument("--value_pretrain", type=int, default=0,
                    help="VAPO: 정책 업데이트 전 critic만 warmup할 epoch 수(0=끔). single-round V 성숙 문제 완화.")
    ap.add_argument("--dapg", action="store_true",
                    help="DAPG(Rajeswaran 2018): on-policy GRPO + gold(off_policy) demo 항을 "
                         "감쇠가중 λ₀·λ₁^step 으로 합산. gold 기여가 학습 진행에 소멸 → LUFFY 회귀 방지. "
                         "gold 주입 rollout(luffy.jsonl) 사용.")
    ap.add_argument("--dapg_l0", type=float, default=0.1, help="DAPG demo 초기 가중 λ₀.")
    ap.add_argument("--dapg_l1", type=float, default=0.999, help="DAPG 감쇠율 λ₁ (step 당). 0.999≈완만.")
    # ── 중단복구(GPU 끊김 대비) / 진행 관측 / CPU 병목 제거 ──
    ap.add_argument("--save_every", type=int, default=0,
                    help="N step 마다 중간 체크포인트 저장(0=끔). 끊겨도 최대 N step 손실.")
    ap.add_argument("--ckpt_dir", default=None,
                    help="중간 체크포인트 디렉토리(기본 <save_dir>/checkpoints). step-N/ 마다 adapter+optimizer.")
    ap.add_argument("--keep_every", type=int, default=5000,
                    help="마일스톤 간격. 이 배수 step 도달 시 그 이전의 비-배수 중간본 삭제(영구보존=배수).")
    ap.add_argument("--log_every", type=int, default=50, help="N step 마다 loss 출력(추세 확인).")
    ap.add_argument("--loss_log", default=None, help="step 별 loss jsonl 경로(기본 <ckpt_dir>/loss.jsonl).")
    ap.add_argument("--resume", action="store_true",
                    help="ckpt_dir/latest.json 에서 이어서 학습(adapter+optimizer+step 위치 복원).")
    ap.add_argument("--render_workers", type=int, default=0,
                    help="프롬프트(collate_input)를 학습 전에 N개 프로세스로 미리 렌더(0=끔). "
                         "GPU 루프에서 CPU 렌더링을 제거 + epoch 마다 재렌더 안 함.")
    args = ap.parse_args()

    # ── 중간 체크포인트 위치 결정 + resume(끊긴 학습 이어가기) ──
    ckpt_dir = None
    if args.ckpt_dir:
        ckpt_dir = Path(args.ckpt_dir)
    elif args.save_every > 0:
        ckpt_dir = Path(args.save_dir) / "checkpoints"
    resume_state = opt_state = None
    if args.resume:
        latest = ckpt_dir / "latest.json" if ckpt_dir is not None else None
        if latest is not None and latest.exists():
            st = json.loads(latest.read_text())
            p = Path(st["path"])
            if (p / "adapter_model.safetensors").exists():
                args.init_adapter = str(p)          # ★ 정책을 체크포인트에서 시작
                resume_state = st
                if (p / "optimizer.pt").exists():
                    opt_state = torch.load(p / "optimizer.pt", map_location="cpu", weights_only=False)
                print(f"[ckpt] resume: {p} (step {st['step']}, epoch {st['epoch']})")
            else:
                print(f"[ckpt] resume 대상 손상({p}) — 처음부터 학습")
        else:
            print("[ckpt] resume 요청됐지만 latest.json 없음 — 처음부터 학습")

    # example 기반 rollout이면 서버와 동일한 collate_input 재현 함수 구성.
    collate_fn = None
    if args.collator_conf:
        import yaml
        from tactic_gen.tactic_data import (
            example_collator_conf_from_yaml, example_collator_from_conf,
        )
        from tactic_gen.lm_example import LmExample
        cc = yaml.safe_load(Path(args.collator_conf).read_text())
        collator = example_collator_from_conf(
            example_collator_conf_from_yaml(cc["example_collator"])
        )
        _tok_holder = {}

        def collate_fn(example_json):
            return collator.collate_input(_tok_holder["tok"], LmExample.from_json(example_json))

    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel, LoraConfig, get_peft_model
    import copy

    device = "cuda" if torch.cuda.is_available() else "cpu"
    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    if collate_fn is not None:
        _tok_holder["tok"] = tokenizer
    base = AutoModelForCausalLM.from_pretrained(args.model_name, torch_dtype=torch.bfloat16).to(device)

    # 정책 = base + LoRA(rango 초기화). 레퍼런스 = 시작 정책 동결 복사.
    if args.init_adapter:
        policy = PeftModel.from_pretrained(base, args.init_adapter, is_trainable=True).to(device)
    else:
        lora = LoraConfig(r=64, lora_alpha=16, lora_dropout=0.1, bias="none",
                          task_type="CAUSAL_LM", target_modules="all-linear")
        policy = get_peft_model(base, lora).to(device)
    # ★ 버그수정: LoRA dropout(0.1)이 policy(train모드)엔 켜지고 ref(eval)엔 꺼져 있어
    #   logp_new vs logp_ref/old 의 ratio·KL 이 dropout 노이즈로 편향(첫 epoch ratio≈1 이 깨짐).
    #   RL logp 는 결정적이어야 하므로 policy 의 dropout 을 0 으로 끈다(ref 는 이미 eval).
    for _mod in policy.modules():
        if isinstance(_mod, torch.nn.Dropout):
            _mod.p = 0.0
    if args.ref_adapter:
        # ★ KL 앵커를 고정 base(π₀)에 — EI 누적 drift 차단(init_adapter=직전 라운드와 별개).
        _ref_base = AutoModelForCausalLM.from_pretrained(args.model_name, torch_dtype=torch.bfloat16).to(device)
        ref_model = PeftModel.from_pretrained(_ref_base, args.ref_adapter).eval()
        for _mod in ref_model.modules():
            if isinstance(_mod, torch.nn.Dropout):
                _mod.p = 0.0
    else:
        ref_model = copy.deepcopy(policy).eval()
    for p in ref_model.parameters():
        p.requires_grad_(False)

    # ★ PPO: critic(value head) = base hidden → V(s) 스칼라. LoRA 어댑터와 별도로 학습(eval 배포엔 불필요).
    value_head = None
    if args.ppo:
        hidden = base.config.hidden_size
        value_head = build_value_head(hidden, args.value_arch, device)
        n_p = sum(p.numel() for p in value_head.parameters())
        print(f"[grpo] PPO 모드 — value head(critic) arch={args.value_arch} "
              f"({n_p} params) 생성. advantage=return−V(s).")

    groups = load_groups(Path(args.rollouts))
    print(f"[grpo] 그룹 {len(groups)}개 로드")
    if args.render_workers > 0 and collate_fn is not None:
        prerender_prompts(groups, collate_fn, args.render_workers, sft=args.sft)
    if args.process:
        n_res = sum(
            1 for g in groups for a in g["attempts"] for s in a["steps"] if "result" in s
        )
        n_all = sum(1 for g in groups for a in g["attempts"] for s in a["steps"])
        if n_res == 0:
            raise SystemExit(
                "--process 인데 rollout step에 'result'가 없습니다. "
                "grpo_rollout.py 를 고친 뒤 rollout을 다시 수집하세요."
            )
        print(f"[grpo] process reward 모드 — result 기록된 step {n_res}/{n_all}")
    if args.luffy:
        n_gold = sum(
            1 for g in groups for a in g["attempts"] if a.get("off_policy")
        )
        print(f"[grpo] LUFFY 모드 — gold(off-policy) 시도 {n_gold}개 주입된 그룹 학습")
    if args.vine:
        n_vs = sum(1 for g in groups for a in g["attempts"] for s in a["steps"] if "adv_vine" in s)
        print(f"[grpo] VinePPO 모드 — adv_vine 기록된 step {n_vs}")
    if args.luffy_kl:
        print("[grpo] Conservative LUFFY (KL-LUFFY) — gold 항에 KL(π_θ‖fix) 복원")
    if args.dapo:
        print(f"[grpo] DAPO 모드 — clip-higher/token-level/KL제거/overlong, "
              f"dynamic sampling 은 rollout(dyn_resample) 에서")
    if args.sft:
        n_succ = sum(1 for g in groups for a in g["attempts"] if a.get("steps") and a["reward"] >= 1.0)
        print(f"[grpo] RFT/SFT 모드 — 성공 궤적(reward≥1) {n_succ}개 지도학습(MLE). "
              f"KL anchor β={args.kl_beta}")
    if args.dapg:
        n_gold = sum(1 for g in groups for a in g["attempts"] if a.get("off_policy"))
        print(f"[grpo] DAPG 모드 — gold demo {n_gold}개, 감쇠 λ₀={args.dapg_l0} λ₁={args.dapg_l1} "
              f"(step 당). on-policy=GRPO 합산")
    train(groups, policy, ref_model, tokenizer, args.max_len, args.epochs, args.lr,
          args.clip_eps, args.kl_beta, args.micro_bsz, device, Path(args.save_dir),
          collate_fn=collate_fn, process=args.process, denom_const=args.denom_const,
          luffy=args.luffy, luffy_gamma=args.luffy_gamma, vine=args.vine,
          luffy_kl=args.luffy_kl, dapo=args.dapo, clip_eps_high=args.clip_eps_high,
          curriculum_anneal=args.curriculum_anneal,
          overlong_cap=args.overlong_cap, overlong_buffer=args.overlong_buffer,
          sft=args.sft, dapg=args.dapg, dapg_l0=args.dapg_l0, dapg_l1=args.dapg_l1,
          ppo=args.ppo, value_head=value_head, value_coef=args.value_coef,
          value_arch=args.value_arch,
          awac=args.awac, awac_lam=args.awac_lam,
          shape_gold=args.shape_gold, shape_coef=args.shape_coef,
          dpo=args.dpo, dpo_beta=args.dpo_beta,
          value_pretrain=args.value_pretrain,
          save_every=args.save_every, ckpt_dir=ckpt_dir, keep_every=args.keep_every,
          log_every=args.log_every,
          loss_log=(Path(args.loss_log) if args.loss_log
                    else (ckpt_dir / "loss.jsonl" if ckpt_dir is not None else None)),
          resume_state=resume_state, opt_state=opt_state)


if __name__ == "__main__":
    main()
