#!/usr/bin/env python3
"""경량 @20 테스트: gold-premise recall@k (TF-IDF vs LM-reranked).

성공 tactic이 실제로 사용한 premise(=tactic에 등장하는 lemma 이름)를 gold로 잡고,
TF-IDF 순위 vs LM-likelihood 재랭킹 순위에서 gold의 recall@k를 비교.
LM 재랭킹이 gold를 더 위로 올리면 → 리랭커가 실제 증명 입력을 개선 → full 정당화.
사용: python3 scripts/replug_lsr_recall.py <log_glob> [--n 40]
★OCaml 무관.
"""
import sys, os, re, glob, argparse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import torch

BASE = "models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500"

def lemma_name(text):
    """premise 텍스트에서 lemma 이름 추출: 'Lemma foo:' → foo."""
    m = re.search(r"\b(?:Lemma|Theorem|Definition|Fixpoint|Remark|Corollary)\s+([A-Za-z0-9_'.]+)", text)
    return m.group(1) if m else None

def tactic_refs(tactic):
    """tactic이 참조하는 식별자들(apply/rewrite/exact/unfold/... 뒤 이름)."""
    return set(re.findall(r"[A-Za-z_][A-Za-z0-9_'.]*", tactic))

def parse_blocks(txt):
    lines = txt.split("\n"); out = []; i = 0
    while i < len(lines):
        if "[Premise Retrieval" in lines[i]:
            goal = None; prems = []; j = i + 1
            while j < len(lines) and "[Premise Retrieval" not in lines[j] and "[Proof Retrieval" not in lines[j]:
                m = re.search(r"쿼리 focused_goal\s*(⊢.*)", lines[j])
                if m and goal is None: goal = m.group(1).strip()
                if re.match(r"\s*Top\d+:", lines[j]):
                    k = j + 1
                    while k < len(lines) and not lines[k].strip(): k += 1
                    if k < len(lines): prems.append(lines[k].strip())
                mt = re.search(r"→ 후보 tactic:\s*'(.*)'", lines[j])
                if mt:
                    tactic = mt.group(1); result = None
                    for k in range(j, min(j + 4, len(lines))):
                        mr = re.search(r"→ 결과:\s*TacticResult\.(\w+)", lines[k])
                        if mr: result = mr.group(1)
                    if goal and prems: out.append((goal, list(dict.fromkeys(prems)), tactic, result))
                    break
                j += 1
            i = j
        else: i += 1
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log_glob"); ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--model", default=BASE); ap.add_argument("--beta", type=float, default=1.0)
    args = ap.parse_args()
    from premise_selection.replug_lsr import lm_target_distribution, recall_at_k

    # gold이 후보에 있는 스텝만 수집 (tactic이 참조한 lemma == 후보 lemma 이름)
    samples = []
    for f in sorted(glob.glob(args.log_glob)):
        for goal, prems, tactic, result in parse_blocks(open(f, errors="ignore").read()):
            if result not in ("VALID", "COMPLETE") or len(prems) < 3: continue
            refs = tactic_refs(tactic)
            gold = {i for i, p in enumerate(prems) if (lemma_name(p) or "∅") in refs}
            if gold: samples.append((goal, prems, tactic, gold))
            if len(samples) >= args.n: break
        if len(samples) >= args.n: break
    print(f"gold 식별된 스텝: {len(samples)}개")
    if not samples: print("샘플 없음"); return

    from transformers import AutoModelForCausalLM, AutoTokenizer
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained("deepseek-ai/deepseek-coder-1.3b-instruct")
    print("모델 로드..."); model = AutoModelForCausalLM.from_pretrained(args.model, torch_dtype=torch.bfloat16).to(dev).eval()
    from tactic_gen.grpo_train import build_completion_batch, sequence_token_logprobs
    bp = lambda p, g: f"[PREMISE]\n{p}\n[GOAL]\n{g}\n[NEXT TACTIC]\n"

    ks = [1, 3, 5]
    tfidf_r = {k: [] for k in ks}; lm_r = {k: [] for k in ks}
    for goal, prems, tactic, gold in samples:
        ids, attn, cm = build_completion_batch(tok, [bp(p, goal) for p in prems], [tactic]*len(prems), 1024, dev)
        with torch.no_grad(): tl = sequence_token_logprobs(model, ids, attn)
        logp = (tl * cm.float()).sum(dim=1)
        lm_order = sorted(range(len(prems)), key=lambda i: -logp[i].item())
        tfidf_order = list(range(len(prems)))   # 로그의 Top 순서 = TF-IDF 순위
        for k in ks:
            tfidf_r[k].append(recall_at_k(tfidf_order, gold, k))
            lm_r[k].append(recall_at_k(lm_order, gold, k))
    import statistics
    print(f"\n=== gold-premise recall@k (n={len(samples)}) ===")
    print(f"{'k':>3} {'TF-IDF':>8} {'LM재랭킹':>10} {'Δ':>7}")
    for k in ks:
        t, l = statistics.mean(tfidf_r[k]), statistics.mean(lm_r[k])
        print(f"{k:>3} {t:>8.3f} {l:>10.3f} {l-t:>+7.3f}")
    d1 = statistics.mean(lm_r[1]) - statistics.mean(tfidf_r[1])
    print(f"\n판정: {'LM 재랭킹이 gold를 더 위로 → full 정당화' if d1 > 0.02 else '개선 미미 → 재검토'}")

if __name__ == "__main__":
    main()
