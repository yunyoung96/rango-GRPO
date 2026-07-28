#!/usr/bin/env python3
"""REPLUG-LSR 신호 probe (라벨 불필요, 저비용).

가설: retrieval을 정책 신호로 학습할 여지가 있으려면, 실제 (state, 성공 tactic)에서
후보 premise들에 대한 LM-likelihood 목표분포 Q_LM 가
  (a) 뾰족해야(uniform 아님) = 어떤 premise가 더 도움된다는 신호가 존재,
  (b) TF-IDF 순서와 달라야 = 재랭킹이 실제 입력을 바꿈(개선 여지).
둘 다 참이면 REPLUG-LSR 리랭커 학습이 정당화된다. 아니면 값싸게 기각.

eval 로그(retrieval 디버그)에서 (goal, top-K premise, 성공 tactic)을 파싱 →
정책 모델로 logP(tactic | premise_i ⊕ goal) 계산 → Q_LM 분석.
사용: python3 scripts/replug_lsr_probe.py <log_glob> [--n 20] [--model ckpt]
★OCaml 무관.
"""
import sys, os, re, glob, argparse, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import torch

BASE = "models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500"

def parse_premise_blocks(txt):
    """각 [Premise Retrieval] 블록 → (goal, [premise_text...], tactic, result)."""
    lines = txt.split("\n")
    out = []
    i = 0
    while i < len(lines):
        if "[Premise Retrieval" in lines[i]:
            goal = None; prems = []
            j = i + 1
            # goal: '쿼리 focused_goal ⊢ ...'
            while j < len(lines) and "[Premise Retrieval" not in lines[j] and "[Proof Retrieval" not in lines[j]:
                m = re.search(r"쿼리 focused_goal\s*(⊢.*)", lines[j])
                if m and goal is None:
                    goal = m.group(1).strip()
                mt = re.match(r"\s*Top\d+:", lines[j])
                if mt:
                    # 다음 비어있지 않은 라인 = lemma 텍스트
                    k = j + 1
                    while k < len(lines) and not lines[k].strip():
                        k += 1
                    if k < len(lines):
                        prems.append(lines[k].strip())
                # 이 블록의 선택 tactic + 결과
                mtac = re.search(r"→ 후보 tactic:\s*'(.*)'", lines[j])
                if mtac:
                    tactic = mtac.group(1)
                    result = None
                    for k in range(j, min(j + 4, len(lines))):
                        mr = re.search(r"→ 결과:\s*TacticResult\.(\w+)", lines[k])
                        if mr: result = mr.group(1)
                    if goal and prems and tactic:
                        # 중복 제거(로그가 Top을 중복 표기)
                        uniq = list(dict.fromkeys(prems))
                        out.append((goal, uniq, tactic, result))
                    break
                j += 1
            i = j
        else:
            i += 1
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log_glob")
    ap.add_argument("--n", type=int, default=20, help="분석할 스텝 수")
    ap.add_argument("--model", default=BASE)
    ap.add_argument("--beta", type=float, default=1.0)
    args = ap.parse_args()

    from premise_selection.replug_lsr import lm_target_distribution

    # 1) 로그 파싱 → 성공(VALID/COMPLETE) & premise≥3 스텝
    samples = []
    for f in sorted(glob.glob(args.log_glob)):
        for goal, prems, tactic, result in parse_premise_blocks(open(f, errors="ignore").read()):
            if result in ("VALID", "COMPLETE") and len(prems) >= 3 and tactic.strip() not in ("Proof.", "Qed.", "auto."):
                samples.append((goal, prems, tactic))
            if len(samples) >= args.n: break
        if len(samples) >= args.n: break
    print(f"파싱된 유효 스텝: {len(samples)}개 (premise≥3, 성공 tactic)")
    if not samples:
        print("샘플 없음 — 로그 형식 확인 필요"); return

    # 2) 모델 로드 (bf16, 스코어링 전용)
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained("deepseek-ai/deepseek-coder-1.3b-instruct")
    print("모델 로드 중...")
    base = AutoModelForCausalLM.from_pretrained(args.model, torch_dtype=torch.bfloat16).to(dev).eval()

    from tactic_gen.grpo_train import build_completion_batch, sequence_token_logprobs

    def build_prompt(premise, goal):
        # (근사) Rango 포매터의 핵심: retrieved premise + 현재 goal → next tactic.
        return f"[PREMISE]\n{premise}\n[GOAL]\n{goal}\n[NEXT TACTIC]\n"

    # 3) 각 스텝: 후보 premise별 logP(tactic) → Q_LM 분석
    entropies_ratio = []   # 실제 엔트로피 / uniform 엔트로피 (1=uniform, <1=뾰족)
    reorder_top1 = 0       # LM top1 ≠ TFIDF top1 (재랭킹이 입력 바꿈)
    lm_gain = []           # 최선 premise logp − 최악 premise logp (신호 크기)
    for goal, prems, tactic in samples:
        prompts = [build_prompt(p, goal) for p in prems]
        comps = [tactic] * len(prems)
        ids, attn, cmask = build_completion_batch(tok, prompts, comps, 1024, dev)
        with torch.no_grad():
            tl = sequence_token_logprobs(base, ids, attn)
        logp = (tl * cmask.float()).sum(dim=1)              # (M,)
        q = lm_target_distribution(logp.float().cpu(), beta=args.beta)
        M = len(prems)
        H = -(q * q.clamp_min(1e-9).log()).sum().item()
        Hu = math.log(M)
        entropies_ratio.append(H / Hu if Hu > 0 else 1.0)
        if q.argmax().item() != 0:   # TFIDF top1 = index 0
            reorder_top1 += 1
        lm_gain.append((logp.max() - logp.min()).item())

    import statistics
    n = len(samples)
    print(f"\n=== REPLUG-LSR 신호 분석 (n={n}) ===")
    print(f"(a) Q_LM 뾰족함: 엔트로피/uniform 평균 {statistics.mean(entropies_ratio):.3f} "
          f"(1.0=uniform=신호없음, 낮을수록 뾰족=신호강함)")
    print(f"(b) 재랭킹 효과: LM top1 ≠ TFIDF top1 = {reorder_top1}/{n} "
          f"({100*reorder_top1/n:.0f}%)  (높을수록 입력이 바뀜)")
    print(f"(c) 신호 크기: 최선−최악 premise의 logP(tactic) 차이 평균 {statistics.mean(lm_gain):.2f} nats")
    print(f"\n판정: {'신호 있음 → 리랭커 학습 정당화' if statistics.mean(entropies_ratio)<0.97 and reorder_top1>0 else '신호 약함 → 재검토'}")

if __name__ == "__main__":
    main()
