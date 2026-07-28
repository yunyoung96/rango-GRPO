#!/usr/bin/env python3
"""Leakage-free probe: premise를 넣었을 때 모델의 next-tactic 엔트로피(gold tactic 無)로
점수. gold=성공 tactic이 쓴 premise. score가 tactic을 안 보므로 이름 누출 없음.
recall@k: 엔트로피 재랭킹 vs TF-IDF.
"""
import sys, os, glob, argparse, statistics
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import torch
from replug_lsr_recall import parse_blocks, lemma_name, tactic_refs  # 재사용

BASE = "models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log_glob"); ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--model", default=BASE)
    a = ap.parse_args()
    from premise_selection.replug_lsr import recall_at_k
    samples = []
    for f in sorted(glob.glob(a.log_glob)):
        for goal, prems, tactic, result in parse_blocks(open(f, errors="ignore").read()):
            if result not in ("VALID", "COMPLETE") or len(prems) < 3: continue
            refs = tactic_refs(tactic)
            gold = {i for i, p in enumerate(prems) if (lemma_name(p) or "\x00") in refs}
            if gold: samples.append((goal, prems, gold))
            if len(samples) >= a.n: break
        if len(samples) >= a.n: break
    print(f"gold 스텝: {len(samples)}")
    if not samples: return
    from transformers import AutoModelForCausalLM, AutoTokenizer
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained("deepseek-ai/deepseek-coder-1.3b-instruct")
    print("로드..."); m = AutoModelForCausalLM.from_pretrained(a.model, torch_dtype=torch.bfloat16).to(dev).eval()
    ks = [1, 3, 5]; tf = {k: [] for k in ks}; en = {k: [] for k in ks}
    for goal, prems, gold in samples:
        # 각 premise: [premise ⊕ goal ⊕ 프롬프트] 마지막 위치 next-token 엔트로피 (tactic 無)
        ents = []
        for p in prems:
            txt = f"[PREMISE]\n{p}\n[GOAL]\n{goal}\n[NEXT TACTIC]\n"
            ids = tok(txt, return_tensors="pt", truncation=True, max_length=1024).to(dev)
            with torch.no_grad():
                lg = m(**ids).logits[0, -1].float()
            pr = torch.softmax(lg, -1)
            ents.append(-(pr * (pr + 1e-12).log()).sum().item())
        en_order = sorted(range(len(prems)), key=lambda i: ents[i])   # 낮은 엔트로피=확신↑
        tf_order = list(range(len(prems)))
        for k in ks:
            tf[k].append(recall_at_k(tf_order, gold, k)); en[k].append(recall_at_k(en_order, gold, k))
    print(f"\n=== leakage-free recall@k (n={len(samples)}) ===")
    print(f"{'k':>3} {'TFIDF':>7} {'엔트로피':>9} {'Δ':>7}")
    for k in ks:
        t, e = statistics.mean(tf[k]), statistics.mean(en[k])
        print(f"{k:>3} {t:>7.3f} {e:>9.3f} {e-t:>+7.3f}")
    d = statistics.mean(en[1]) - statistics.mean(tf[1])
    print(f"\n판정: {'엔트로피 재랭킹이 gold 상향 → 신호 有' if d > 0.02 else '신호 없음/미미 → REPLUG 이 규모선 무효'}")

if __name__ == "__main__":
    main()
