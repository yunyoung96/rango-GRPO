#!/usr/bin/env python3
"""SRFT / Unified SFT+RL 단일스테이지 학습 (arXiv:2506.19767, 2509.04419 계열).

SFT와 GRPO를 **한 최적화 스테이지**에서 결합:
  L = L_GRPO(rollout 그룹, 그룹상대 advantage) + λ · L_SFT(전문가 성공궤적 MLE)
  - GRPO 항: on-policy 탐색 신호(dead group은 std=0으로 스킵).
  - SFT 항: BFS/expert 성공궤적(state,tactic)을 데모로 anchor → RL 붕괴 방지 + 데이터효율.
순차 SFT→GRPO(2스테이지)와 달리 매 스텝 두 신호를 동시 backward = "single-stage".

grpo_train의 flatten_group/토크나이즈/logp + grpo.py의 grpo_batch_loss/sft_batch_loss 재사용.
독립 파일(grpo_train.py 미변경) → 병행 실행중인 다른 학습에 무영향. ★OCaml 무관.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

import torch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tactic_gen.grpo_train import (  # noqa: E402
    build_completion_batch, sequence_token_logprobs, flatten_group, _flatten_prompt,
)
from tactic_gen.grpo import grpo_batch_loss, sft_batch_loss  # noqa: E402


def load_groups(path: Path) -> list[dict]:
    out = []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def load_sft_rows(path: Path, collate_fn) -> list[tuple[str, str]]:
    """BFS/expert 성공 rollout(그룹) → (prompt, tactic) 행. reward≥1 궤적만."""
    rows = []
    for g in load_groups(path):
        for a in g.get("attempts", []):
            if a.get("reward", 0) >= 1.0:
                for st in a.get("steps", []):
                    rows.append((_flatten_prompt(st, collate_fn), st["tactic"]))
    return rows


def train(groups, sft_rows, model, ref_model, tokenizer, max_len, epochs, lr,
          clip_eps, kl_beta, sft_coef, micro_bsz, device, save_dir, collate_fn=None):
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=lr)
    si = 0  # SFT 데이터 회전 포인터
    nsft = len(sft_rows)
    for ep in range(epochs):
        tot_g = tot_s = n = 0.0
        for group in groups:
            prompts, comps, advs, _advp, _golds = flatten_group(group, collate_fn)
            # dead group(그룹상대 신호 0)이면 GRPO 항은 끄되(grpo_off), SFT 데모는 계속 소비.
            #   (rollout의 ~65%가 dead라 여기서 continue하면 SFT 데이터가 거의 안 쓰임 → U 약화.)
            grpo_off = (not prompts) or all(abs(a) < 1e-8 for a in advs)
            nmb = 1 if grpo_off else ((len(prompts) + micro_bsz - 1) // micro_bsz)
            for s_i in range(nmb):
                s = s_i * micro_bsz
                loss_g = torch.zeros((), device=device)
                if not grpo_off:
                    bp, bc = prompts[s:s+micro_bsz], comps[s:s+micro_bsz]
                    ba = torch.tensor(advs[s:s+micro_bsz], device=device)
                    ids, attn, cmask = build_completion_batch(tokenizer, bp, bc, max_len, device)
                    with torch.no_grad():
                        logp_ref = sequence_token_logprobs(ref_model, ids, attn)
                        logp_old = logp_ref
                    logp_new = sequence_token_logprobs(model, ids, attn)
                    loss_g, _kl = grpo_batch_loss(logp_new, logp_old, logp_ref, ba, cmask,
                                                  clip_eps=clip_eps, kl_beta=kl_beta)
                # ── SFT 항(단일스테이지 결합): 회전 포인터로 SFT micro-batch (dead group에서도 소비) ──
                loss_s = torch.zeros((), device=device)
                if nsft and sft_coef > 0:
                    sb = [sft_rows[(si + k) % nsft] for k in range(micro_bsz)]
                    si = (si + micro_bsz) % nsft
                    sp = [x[0] for x in sb]; sc = [x[1] for x in sb]
                    sids, sattn, scmask = build_completion_batch(tokenizer, sp, sc, max_len, device)
                    with torch.no_grad():
                        slogp_ref = sequence_token_logprobs(ref_model, sids, sattn)
                    slogp_new = sequence_token_logprobs(model, sids, sattn)
                    loss_s, _ = sft_batch_loss(slogp_new, slogp_ref, scmask, kl_beta=0.0)
                loss = loss_g + sft_coef * loss_s
                if float(loss) == 0.0 and not loss.requires_grad:
                    continue  # 신호 전무(dead+SFT없음) 방어
                opt.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], 1.0)
                opt.step()
                tot_g += float(loss_g); tot_s += float(loss_s); n += 1
        print(f"[srft] epoch {ep}: grpo_loss={tot_g/max(n,1):.4f} sft_loss={tot_s/max(n,1):.4f} "
              f"(λ={sft_coef}) steps={int(n)}")
    if save_dir is not None:
        save_dir = Path(save_dir); save_dir.mkdir(parents=True, exist_ok=True)
        model.save_pretrained(str(save_dir))
        print(f"[srft] adapter 저장 → {save_dir}")


def main():
    ap = argparse.ArgumentParser(description="SRFT: single-stage SFT+GRPO")
    ap.add_argument("--rollouts", required=True, help="GRPO rollout jsonl(그룹상대 advantage용)")
    ap.add_argument("--sft_data", required=True, help="expert 성공 rollout jsonl(SFT 데모 항)")
    ap.add_argument("--model_name", required=True)
    ap.add_argument("--init_adapter", default=None)
    ap.add_argument("--save_dir", default="models/rango-srft/adapter")
    ap.add_argument("--collator_conf", default=None)
    ap.add_argument("--max_len", type=int, default=3072)
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--lr", type=float, default=1e-6)
    ap.add_argument("--clip_eps", type=float, default=0.2)
    ap.add_argument("--kl_beta", type=float, default=0.04)
    ap.add_argument("--sft_coef", type=float, default=1.0, help="λ: SFT 항 가중.")
    ap.add_argument("--micro_bsz", type=int, default=2)
    args = ap.parse_args()

    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel, LoraConfig, get_peft_model
    import copy

    device = "cuda" if torch.cuda.is_available() else "cpu"
    tokenizer = AutoTokenizer.from_pretrained(args.model_name)

    collate_fn = None
    if args.collator_conf:
        import yaml
        from tactic_gen.tactic_data import example_collator_conf_from_yaml, example_collator_from_conf
        from tactic_gen.lm_example import LmExample
        cc = yaml.safe_load(Path(args.collator_conf).read_text())
        collator = example_collator_from_conf(example_collator_conf_from_yaml(cc["example_collator"]))
        collate_fn = lambda ej: collator.collate_input(tokenizer, LmExample.from_json(ej))

    base = AutoModelForCausalLM.from_pretrained(args.model_name, torch_dtype=torch.bfloat16).to(device)
    if args.init_adapter:
        model = PeftModel.from_pretrained(base, args.init_adapter, is_trainable=True).to(device)
    else:
        lora = LoraConfig(r=64, lora_alpha=16, lora_dropout=0.1, bias="none",
                          task_type="CAUSAL_LM", target_modules="all-linear")
        model = get_peft_model(base, lora).to(device)
    ref_model = copy.deepcopy(model).eval()
    for p in ref_model.parameters():
        p.requires_grad_(False)

    groups = load_groups(Path(args.rollouts))
    sft_rows = load_sft_rows(Path(args.sft_data), collate_fn)
    print(f"[srft] GRPO 그룹 {len(groups)} · SFT 행 {len(sft_rows)} 로드 (λ={args.sft_coef})")
    train(groups, sft_rows, model, ref_model, tokenizer, args.max_len, args.epochs,
          args.lr, args.clip_eps, args.kl_beta, args.sft_coef, args.micro_bsz, device,
          Path(args.save_dir), collate_fn=collate_fn)


if __name__ == "__main__":
    main()
