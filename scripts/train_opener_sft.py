#!/usr/bin/env python3
"""7B opener SFT — goal → gold opening(첫 분해) 생성 학습. Qwen2.5-Coder-7B LoRA(bf16, GPU1).
데이터: data/grpo_rollouts/opener_gen.jsonl {goal, opening:[tactics]}. ★OCaml 무관."""
import json, re, sys, argparse
from pathlib import Path
import torch

SYSTEM = ("You are a Coq proof strategist. Given the current GOAL, output ONLY a JSON array "
          "of the opening Coq tactics that decompose it (induction/destruct/inversion on the "
          "right target), most-promising first. No prose.")

def build(tok, goal, opening):
    # Proof. 제거, JSON 타겟
    op = [t for t in opening if t.strip() != 'Proof.']
    target = json.dumps(op, ensure_ascii=False)
    msgs = [{"role":"system","content":SYSTEM},{"role":"user","content":f"GOAL:\n{goal}"}]
    prompt = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    full = prompt + target + tok.eos_token
    pids = tok(prompt, add_special_tokens=False)["input_ids"]
    fids = tok(full, add_special_tokens=False)["input_ids"]
    labels = [-100]*len(pids) + fids[len(pids):]
    return fids, labels

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data", default="data/grpo_rollouts/opener_gen.jsonl")
    ap.add_argument("--model", default="Qwen/Qwen2.5-Coder-7B-Instruct")
    ap.add_argument("--save", default="models/opener-7b/adapter")
    ap.add_argument("--epochs", type=int, default=4)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--max_len", type=int, default=1024)
    args=ap.parse_args()
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import LoraConfig, get_peft_model
    dev="cuda:0"
    tok=AutoTokenizer.from_pretrained(args.model, local_files_only=True)
    model=AutoModelForCausalLM.from_pretrained(args.model, dtype=torch.bfloat16,
            device_map={"":dev}, local_files_only=True)
    lora=LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, bias="none",
            task_type="CAUSAL_LM", target_modules="all-linear")
    model=get_peft_model(model, lora); model.train()
    rows=[json.loads(l) for l in open(args.data)]
    data=[build(tok, r["goal"], r["opening"]) for r in rows]
    data=[(f[:args.max_len], l[:args.max_len]) for f,l in data]
    n_before=len(data)
    data=[(f,l) for f,l in data if any(x!=-100 for x in l)]  # 완성 잘려 label 전부 -100 → NaN 방지
    print(f"[opener-sft] {len(data)}예시(마스킹-only {n_before-len(data)}개 제외), {args.epochs}ep, lr{args.lr}", flush=True)
    opt=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=args.lr)
    for ep in range(args.epochs):
        import random; random.Random(ep).shuffle(data)
        tot=0.0
        for i,(fids,labels) in enumerate(data):
            ids=torch.tensor([fids],device=dev); lab=torch.tensor([labels],device=dev)
            out=model(input_ids=ids, labels=lab); loss=out.loss
            if torch.isnan(loss) or torch.isinf(loss): continue  # 방어: 나쁜 배치 건너뜀
            opt.zero_grad(); loss.backward()
            torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad],1.0)
            opt.step(); tot+=float(loss)
        print(f"[opener-sft] ep{ep}: loss={tot/len(data):.4f}", flush=True)
    Path(args.save).mkdir(parents=True, exist_ok=True)
    model.save_pretrained(args.save); tok.save_pretrained(args.save)
    print(f"[opener-sft] 저장 → {args.save}", flush=True)

if __name__=="__main__": main()
