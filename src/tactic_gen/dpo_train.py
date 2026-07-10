#!/usr/bin/env python3
"""DPO 학습 루프 — BFS-Prover full 학습의 선호학습 단계.

선호쌍 {state, chosen, rejected} → 정책/레퍼런스 log-prob → DPO 손실로 LoRA 업데이트.
grpo_train의 토크나이즈/logp 헬퍼 + dpo.py 코어 재사용.
π_ref = 시작 정책 동결 복사. β=0.1 기본.
★OCaml 무관.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

import torch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tactic_gen.grpo_train import build_completion_batch, sequence_token_logprobs  # noqa: E402
from tactic_gen.dpo import dpo_loss, masked_sum_logprob  # noqa: E402


def _seq_logp(model, tokenizer, prompts, comps, max_len, device):
    ids, attn, cmask = build_completion_batch(tokenizer, prompts, comps, max_len, device)
    tok_logp = sequence_token_logprobs(model, ids, attn)
    return masked_sum_logprob(tok_logp, cmask)


def load_pairs(path: Path, collate_fn=None) -> list[dict]:
    pairs = []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        p = json.loads(line)
        st = p["state"]
        prompt = collate_fn(st) if (collate_fn and isinstance(st, dict)) else st
        pairs.append({"prompt": prompt, "chosen": p["chosen"], "rejected": p["rejected"]})
    return pairs


def train(
    pairs: list[dict],
    model,
    ref_model,
    tokenizer,
    max_len: int,
    epochs: int,
    lr: float,
    beta: float,
    micro_bsz: int,
    device: str,
    save_dir: Optional[Path],
):
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=lr)
    for ep in range(epochs):
        tot_loss = tot_acc = n = 0.0
        for s in range(0, len(pairs), micro_bsz):
            batch = pairs[s : s + micro_bsz]
            prompts = [b["prompt"] for b in batch]
            chosen = [b["chosen"] for b in batch]
            rejected = [b["rejected"] for b in batch]
            with torch.no_grad():
                w_ref = _seq_logp(ref_model, tokenizer, prompts, chosen, max_len, device)
                l_ref = _seq_logp(ref_model, tokenizer, prompts, rejected, max_len, device)
            w_pol = _seq_logp(model, tokenizer, prompts, chosen, max_len, device)
            l_pol = _seq_logp(model, tokenizer, prompts, rejected, max_len, device)
            loss, acc = dpo_loss(w_pol, l_pol, w_ref, l_ref, beta=beta)
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(
                [p for p in model.parameters() if p.requires_grad], 1.0
            )
            opt.step()
            tot_loss += float(loss); tot_acc += float(acc); n += 1
        print(f"[dpo] epoch {ep}: loss={tot_loss/max(n,1):.4f} acc={tot_acc/max(n,1):.3f} steps={int(n)}")
    if save_dir is not None:
        save_dir.mkdir(parents=True, exist_ok=True)
        model.save_pretrained(str(save_dir))
        print(f"[dpo] adapter 저장 → {save_dir}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", required=True, help="선호쌍 jsonl (bfs_dpo_data.extract_dpo_pairs)")
    ap.add_argument("--model_name", required=True)
    ap.add_argument("--init_adapter", default=None)
    ap.add_argument("--save_dir", default="models/bfs-dpo/adapter")
    ap.add_argument("--collator_conf", default=None)
    ap.add_argument("--max_len", type=int, default=2048)
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--lr", type=float, default=5e-7)
    ap.add_argument("--beta", type=float, default=0.1)
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
        from tactic_gen.tactic_data import (
            example_collator_conf_from_yaml, example_collator_from_conf,
        )
        from tactic_gen.lm_example import LmExample
        cc = yaml.safe_load(Path(args.collator_conf).read_text())
        collator = example_collator_from_conf(
            example_collator_conf_from_yaml(cc["example_collator"])
        )
        collate_fn = lambda ej: collator.collate_input(tokenizer, LmExample.from_json(ej))

    base = AutoModelForCausalLM.from_pretrained(args.model_name, torch_dtype=torch.bfloat16).to(device)
    if args.init_adapter:
        policy = PeftModel.from_pretrained(base, args.init_adapter, is_trainable=True).to(device)
    else:
        lora = LoraConfig(r=64, lora_alpha=16, lora_dropout=0.1, bias="none",
                          task_type="CAUSAL_LM", target_modules="all-linear")
        policy = get_peft_model(base, lora).to(device)
    ref_model = copy.deepcopy(policy).eval()
    for p in ref_model.parameters():
        p.requires_grad_(False)

    pairs = load_pairs(Path(args.pairs), collate_fn)
    print(f"[dpo] 선호쌍 {len(pairs)}개 로드")
    train(pairs, policy, ref_model, tokenizer, args.max_len, args.epochs, args.lr,
          args.beta, args.micro_bsz, device, Path(args.save_dir))


if __name__ == "__main__":
    main()
