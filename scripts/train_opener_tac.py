#!/usr/bin/env python3
"""tactic-단위 opener SFT (신규). 입력=goal+후보+lemma/proof retrieval, 출력=다음 분해 tactic 1개 or NMD.
데이터: data/grpo_rollouts/opener_tac.jsonl {input, target}. Qwen2.5-Coder-7B LoRA(bf16). ★OCaml 무관."""
import json, sys, argparse
from pathlib import Path
import torch

SYSTEM = ("You are a Coq proof strategist. Given the GOAL, enumerated CANDIDATE decompositions, "
          "and retrieved RELEVANT LEMMAS/PROOFS, output the SINGLE next opening tactic that decomposes "
          "the goal (induction/destruct/inversion on the right target, with the right argument — use a "
          "candidate or a retrieved lemma when it fits). If the goal is already sufficiently decomposed "
          'and needs no further structural step, output exactly "No More Decomposition". No prose.')

def build(tok, inp, target, max_len):
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": inp}]
    prompt = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    full = prompt + target + tok.eos_token
    pids = tok(prompt, add_special_tokens=False)["input_ids"]
    fids = tok(full, add_special_tokens=False)["input_ids"]
    labels = [-100] * len(pids) + fids[len(pids):]
    return fids[:max_len], labels[:max_len]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/grpo_rollouts/opener_tac.jsonl")
    ap.add_argument("--model", default="Qwen/Qwen2.5-Coder-7B-Instruct")
    ap.add_argument("--save", default="models/opener-7b-tac/adapter")
    ap.add_argument("--epochs", type=int, default=4)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--max_len", type=int, default=3072)
    args = ap.parse_args()
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import LoraConfig, get_peft_model
    dev = "cuda:0"
    tok = AutoTokenizer.from_pretrained(args.model, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(args.model, dtype=torch.bfloat16,
                                                 device_map={"": dev}, local_files_only=True)
    lora = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, bias="none",
                      task_type="CAUSAL_LM", target_modules="all-linear")
    model = get_peft_model(model, lora); model.train()
    # ★ gradient checkpointing: activation 메모리 대폭↓ (max_len 3072 + 7B가 48GB 초과 OOM 방지).
    #   LoRA+checkpointing은 입력에 grad 필요 → enable_input_require_grads. use_cache=False.
    model.config.use_cache = False
    model.enable_input_require_grads()
    model.gradient_checkpointing_enable()
    rows = [json.loads(l) for l in open(args.data)]
    data = [build(tok, r["input"], r["target"], args.max_len) for r in rows]
    n0 = len(data)
    data = [(f, l) for f, l in data if any(x != -100 for x in l)]  # 완성 잘려 전부-마스킹 → NaN 방지
    print(f"[opener-tac] {len(data)}예시(마스킹-only {n0-len(data)} 제외), {args.epochs}ep, lr{args.lr}, max_len{args.max_len}", flush=True)
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=args.lr)
    for ep in range(args.epochs):
        import random; random.Random(ep).shuffle(data)
        tot = 0.0; n = 0
        for fids, labels in data:
            ids = torch.tensor([fids], device=dev); lab = torch.tensor([labels], device=dev)
            out = model(input_ids=ids, labels=lab); loss = out.loss
            if torch.isnan(loss) or torch.isinf(loss):
                continue
            opt.zero_grad(); loss.backward()
            torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], 1.0)
            opt.step(); tot += float(loss); n += 1
        print(f"[opener-tac] ep{ep}: loss={tot/max(n,1):.4f}", flush=True)
    Path(args.save).mkdir(parents=True, exist_ok=True)
    model.save_pretrained(args.save); tok.save_pretrained(args.save)
    print(f"[opener-tac] 저장 → {args.save}", flush=True)

if __name__ == "__main__":
    main()
