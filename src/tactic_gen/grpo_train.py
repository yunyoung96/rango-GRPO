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

from tactic_gen.grpo import group_advantages, grpo_batch_loss  # noqa: E402


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


def load_groups(path: Path) -> list[dict]:
    """rollout jsonl: 각 줄 = {theorem, attempts:[{steps:[{prompt,tactic}], reward}]}."""
    groups = []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if line:
            groups.append(json.loads(line))
    return groups


def flatten_group(group: dict, collate_fn=None):
    """그룹 → (prompts, completions, adv_per_step). advantage는 그룹상대(시도 보상 기반).
    step이 'prompt'(문자열)를 가지면 그대로, 'example'(json)를 가지면 collate_fn으로
    서버와 동일한 prompt 문자열 재현(collate_fn(example_json) → str)."""
    attempts = group["attempts"]
    rewards = torch.tensor([a["reward"] for a in attempts], dtype=torch.float)
    adv = group_advantages(rewards)                      # (G,)
    prompts, comps, advs = [], [], []
    for i, a in enumerate(attempts):
        for st in a["steps"]:
            if "prompt" in st:
                prompts.append(st["prompt"])
            else:
                assert collate_fn is not None, "example 기반 rollout엔 collate_fn 필요"
                prompts.append(collate_fn(st["example"]))
            comps.append(st["tactic"])
            advs.append(float(adv[i]))
    return prompts, comps, advs


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
):
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=lr)
    for ep in range(epochs):
        tot_loss = tot_kl = n = 0.0
        for group in groups:
            prompts, comps, advs = flatten_group(group, collate_fn)
            if not prompts or all(abs(a) < 1e-8 for a in advs):
                continue  # 그룹 내 보상 균일 → 학습 신호 없음(스킵)
            for s in range(0, len(prompts), micro_bsz):
                bp = prompts[s : s + micro_bsz]
                bc = comps[s : s + micro_bsz]
                ba = torch.tensor(advs[s : s + micro_bsz], device=device)
                ids, attn, cmask = build_completion_batch(tokenizer, bp, bc, max_len, device)
                with torch.no_grad():
                    logp_ref = sequence_token_logprobs(ref_model, ids, attn)
                    logp_old = logp_ref  # 온폴리시 첫 라운드: old=ref(시작 정책)
                logp_new = sequence_token_logprobs(model, ids, attn)
                loss, kl = grpo_batch_loss(
                    logp_new, logp_old, logp_ref, ba, cmask,
                    clip_eps=clip_eps, kl_beta=kl_beta,
                )
                opt.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(
                    [p for p in model.parameters() if p.requires_grad], 1.0
                )
                opt.step()
                tot_loss += float(loss); tot_kl += float(kl); n += 1
        print(f"[grpo] epoch {ep}: loss={tot_loss/max(n,1):.4f} kl={tot_kl/max(n,1):.4f} steps={int(n)}")
    if save_dir is not None:
        save_dir.mkdir(parents=True, exist_ok=True)
        model.save_pretrained(str(save_dir))
        print(f"[grpo] adapter 저장 → {save_dir}")


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
    ap.add_argument("--micro_bsz", type=int, default=4)
    ap.add_argument("--collator_conf", default=None,
                    help="example_collator yaml(rango training_conf). example 기반 rollout 재현용.")
    args = ap.parse_args()

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
    ref_model = copy.deepcopy(policy).eval()
    for p in ref_model.parameters():
        p.requires_grad_(False)

    groups = load_groups(Path(args.rollouts))
    print(f"[grpo] 그룹 {len(groups)}개 로드")
    train(groups, policy, ref_model, tokenizer, args.max_len, args.epochs, args.lr,
          args.clip_eps, args.kl_beta, args.micro_bsz, device, Path(args.save_dir),
          collate_fn=collate_fn)


if __name__ == "__main__":
    main()
