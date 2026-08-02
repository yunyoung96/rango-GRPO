#!/usr/bin/env python3
"""하이브리드 선택형 opener SFT — 입력=goal+열거후보, 출력=gold. Qwen-7B LoRA(bf16). ★OCaml 무관."""
import json, sys, argparse
from pathlib import Path
import torch
SYSTEM=("You are a Coq proof strategist. Given the GOAL and enumerated CANDIDATE decompositions, "
 "output ONLY a JSON array with the best opening Coq tactic(s). Pick a candidate if one fits, "
 "otherwise write your own. No prose.")
def build(tok,goal,cands,gold,max_len):
    cand_txt="\n".join(f"- {c}" for c in cands) if cands else "(none)"
    user=f"GOAL:\n{goal}\n\nCANDIDATES:\n{cand_txt}"
    target=json.dumps([gold],ensure_ascii=False)
    prompt=tok.apply_chat_template([{"role":"system","content":SYSTEM},{"role":"user","content":user}],tokenize=False,add_generation_prompt=True)
    full=prompt+target+tok.eos_token
    p=tok(prompt,add_special_tokens=False)["input_ids"];f=tok(full,add_special_tokens=False)["input_ids"]
    return f[:max_len], ([-100]*len(p)+f[len(p):])[:max_len]
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",default="data/grpo_rollouts/opener_sel2.jsonl")
    ap.add_argument("--model",default="Qwen/Qwen2.5-Coder-7B-Instruct")
    ap.add_argument("--save",default="models/opener-sel-7b/adapter")
    ap.add_argument("--epochs",type=int,default=4); ap.add_argument("--lr",type=float,default=1e-4); ap.add_argument("--max_len",type=int,default=1536)
    args=ap.parse_args()
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import LoraConfig, get_peft_model
    tok=AutoTokenizer.from_pretrained(args.model,local_files_only=True)
    model=AutoModelForCausalLM.from_pretrained(args.model,dtype=torch.bfloat16,device_map={"":"cuda:0"},local_files_only=True)
    model=get_peft_model(model,LoraConfig(r=16,lora_alpha=32,lora_dropout=0.05,bias="none",task_type="CAUSAL_LM",target_modules="all-linear")); model.train()
    rows=[json.loads(l) for l in open(args.data)]
    data=[build(tok,r["goal"],r["candidates"],r["gold"],args.max_len) for r in rows]
    print(f"[opener-sel] {len(data)}예시 {args.epochs}ep",flush=True)
    opt=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=args.lr)
    import random
    for ep in range(args.epochs):
        random.Random(ep).shuffle(data); tot=0.0
        for f,l in data:
            ids=torch.tensor([f],device="cuda:0");lab=torch.tensor([l],device="cuda:0")
            loss=model(input_ids=ids,labels=lab).loss; opt.zero_grad();loss.backward()
            torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad],1.0);opt.step();tot+=float(loss)
        print(f"[opener-sel] ep{ep}: loss={tot/len(data):.4f}",flush=True)
    Path(args.save).mkdir(parents=True,exist_ok=True); model.save_pretrained(args.save); tok.save_pretrained(args.save)
    print(f"[opener-sel] 저장 → {args.save}",flush=True)
if __name__=="__main__": main()
