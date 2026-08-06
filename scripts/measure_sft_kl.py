#!/usr/bin/env python3
"""step 모델이 SFT에서 얼마나 멀어졌나 (SFT 대비 KL 근사). GPU1 전용.
   KL(π_step ‖ π_SFT) ≈ mean over (s,a)~π_step rollout of [logp_step(a|s) − logp_SFT(a|s)].
   (rollout이 그 정책 샘플이라 forward-KL 근사로 유효.)
용법: python3 scripts/measure_sft_kl.py <step_adapter> <rollout.jsonl(.gz)> [n_groups]
"""
import sys, json, gzip, torch, os
from transformers import AutoModelForCausalLM
from peft import PeftModel
sys.path.insert(0, "src")
from tactic_gen.grpo_train import sequence_token_logprobs, build_completion_batch
from transformers import AutoTokenizer

BASE = "deepseek-ai/deepseek-coder-1.3b-instruct"
SFT = "models/rango-tst1000tr5091-sft/adapter"
CONF = "models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml"

def load_rollout(path, ncap):
    op = gzip.open if path.endswith(".gz") else open
    groups = []
    for l in op(path, "rt"):
        try: groups.append(json.loads(l))
        except: pass
        if len(groups) >= ncap: break
    return groups

def collect_pairs(groups, collate, tok):
    prompts, comps = [], []
    for g in groups:
        for a in g["attempts"]:
            if a.get("off_policy") or not a.get("steps"): continue
            for st in a["steps"]:
                ex = st.get("example"); tac = st.get("tactic")
                if ex is None or tac is None: continue
                try:
                    p = collate.collate_input(tok, ex if isinstance(ex, dict) else json.loads(ex))
                except Exception:
                    continue
                prompts.append(p); comps.append(tac)
    return prompts, comps

def main():
    step_adapter = sys.argv[1]
    roll = sys.argv[2]
    ncap = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    dev = "cuda"
    tok = AutoTokenizer.from_pretrained(BASE)
    import yaml
    from tactic_gen.tactic_data import collator_from_conf
    collate = collator_from_conf(yaml.safe_load(open(CONF)))
    groups = load_rollout(roll, ncap)
    prompts, comps = collect_pairs(groups, collate, tok)
    if not prompts:
        print("샘플 없음"); return
    base = AutoModelForCausalLM.from_pretrained(BASE, torch_dtype=torch.bfloat16).to(dev)
    m_step = PeftModel.from_pretrained(base, step_adapter).eval()
    diffs = []
    B = 4
    with torch.no_grad():
        for s in range(0, len(prompts), B):
            bp, bc = prompts[s:s+B], comps[s:s+B]
            ids, attn, cmask = build_completion_batch(tok, bp, bc, 3072, dev)
            lp_step = sequence_token_logprobs(m_step, ids, attn)
            m = cmask.float()
            step_tok = (lp_step * m).sum(1) / m.sum(1).clamp(min=1)
            diffs.append((step_tok, m.sum(1)))
    # SFT logp
    m_step = m_step.unload() if hasattr(m_step, "unload") else None
    base2 = AutoModelForCausalLM.from_pretrained(BASE, torch_dtype=torch.bfloat16).to(dev)
    m_sft = PeftModel.from_pretrained(base2, SFT).eval()
    tot_diff = tot_n = 0.0
    with torch.no_grad():
        for i, (s) in enumerate(range(0, len(prompts), B)):
            bp, bc = prompts[s:s+B], comps[s:s+B]
            ids, attn, cmask = build_completion_batch(tok, bp, bc, 3072, dev)
            lp_sft = sequence_token_logprobs(m_sft, ids, attn)
            m = cmask.float()
            sft_tok = (lp_sft * m).sum(1) / m.sum(1).clamp(min=1)
            step_tok = diffs[i][0]
            tot_diff += float((step_tok - sft_tok).sum()); tot_n += step_tok.numel()
    print(f"  {os.path.basename(step_adapter.rstrip('/adapter'))}: SFT대비 KL근사 = {tot_diff/max(tot_n,1):.4f}  (n={int(tot_n)} 시퀀스)")

if __name__ == "__main__":
    main()
