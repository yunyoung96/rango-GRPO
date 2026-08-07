#!/usr/bin/env python3
"""Teacher-forced 평가: gold proof-state에서 (BASE+adapter) 모델이 greedy로 생성한 tactic이
gold tactic과 일치(EXACT-MATCH)하는지 측정한다. Coq 불필요(순수 생성+문자열 비교).

한 adapter에 대해:
  - gold jsonl(각 줄=그룹, attempts[].steps[]{example, tactic})에서 **결정적**으로 first-N non-trivial
    (state, gold_tactic) 쌍을 뽑고,
  - 각 state를 학습과 **동일한** collator(collate_input)로 [PREMISES][PROOFS][STATE][SCRIPT][TACTIC]
    프롬프트로 만들고,
  - BASE(deepseek-coder-1.3b-instruct) + LoRA adapter 를 얹어 greedy(do_sample=False) 생성,
  - 생성 tactic vs gold tactic 을 strict/normalized 로 비교.

PRE(rango baseline)와 POST(sft) 를 **같은 N개 state** 로 두 번 실행하면 동일 state를 본다(샘플이 결정적).

사용:
  CUDA_VISIBLE_DEVICES=0 python scripts/eval_sft_gold.py \
      --adapter models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500 \
      --n 300 --gpu 0 --out /tmp/eval_pre.jsonl
  (POST 는 --adapter models/rango-tst1000tr5091-sft/adapter)

GPU0만 사용(GPU1은 GRPO 중, 절대 건드리지 않음).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--adapter", required=True, help="LoRA adapter dir (adapter_config.json 포함)")
    ap.add_argument("--base", default="deepseek-ai/deepseek-coder-1.3b-instruct")
    ap.add_argument("--gold", default="data/grpo_rollouts/tst1000tr5091_gold.jsonl")
    ap.add_argument("--n", type=int, default=300, help="비-trivial (state,tactic) 쌍 개수")
    ap.add_argument("--gpu", default="0", help="CUDA_VISIBLE_DEVICES (반드시 0)")
    ap.add_argument("--training_conf", default=None,
                    help="collator conf yaml. 미지정 시 adapter의 부모(또는 부모의 부모)에서 training_conf.yaml 탐색")
    ap.add_argument("--batch_size", type=int, default=16)
    ap.add_argument("--max_new_tokens", type=int, default=64)
    ap.add_argument("--include_trivial", action="store_true",
                    help="trivial('Proof.'/빈값) step도 포함")
    ap.add_argument("--out", default=None, help="per-example 결과 jsonl 저장 경로")
    return ap.parse_args()


TRIVIAL = {"", "Proof."}


def is_trivial(tac: str) -> bool:
    return (tac or "").strip() in TRIVIAL


def load_pairs(gold_path: str, n: int, include_trivial: bool):
    """gold jsonl에서 결정적(파일순서) first-N (example_json, gold_tactic, meta) 쌍."""
    pairs = []
    with open(gold_path) as f:
        for line in f:
            g = json.loads(line)
            for att in g.get("attempts", []):
                for st in att.get("steps", []):
                    ex = st.get("example")
                    tac = st.get("tactic")
                    if ex is None or tac is None:
                        continue
                    if (not include_trivial) and is_trivial(tac):
                        continue
                    pairs.append((ex, tac, {
                        "theorem": g.get("theorem"),
                        "file_name": ex.get("file_name"),
                        "proof_idx": ex.get("proof_idx"),
                        "step_idx": ex.get("step_idx"),
                        "result": st.get("result"),
                    }))
                    if len(pairs) >= n:
                        return pairs
    return pairs


def find_training_conf(adapter: str) -> str:
    p = Path(adapter)
    for cand in (p / "training_conf.yaml", p.parent / "training_conf.yaml",
                 p.parent.parent / "training_conf.yaml"):
        if cand.exists():
            return str(cand)
    raise FileNotFoundError(f"training_conf.yaml 못 찾음 (adapter={adapter})")


def main():
    args = parse_args()
    # GPU0 강제 — torch import 전에 설정
    os.environ["CUDA_VISIBLE_DEVICES"] = str(args.gpu)
    sys.path.insert(0, "src")

    import yaml
    import torch
    from transformers import AutoModelForCausalLM
    from peft import PeftModel

    from tactic_gen.lm_example import LmExample
    from tactic_gen.tactic_data import (
        get_tokenizer,
        example_collator_conf_from_yaml,
        example_collator_from_conf,
    )

    conf_path = args.training_conf or find_training_conf(args.adapter)
    with open(conf_path) as f:
        tconf = yaml.safe_load(f)
    hard_seq_len = int(tconf["hard_seq_len"])
    collator = example_collator_from_conf(
        example_collator_conf_from_yaml(tconf["example_collator"])
    )
    print(f"[eval] collator={type(collator).__name__} hard_seq_len={hard_seq_len} conf={conf_path}")

    # 프롬프트에 EOS 붙이지 않음(추론 경로와 동일: model_wrapper get_tokenizer add_eos=False)
    tokenizer = get_tokenizer(args.base, add_eos=False)
    tokenizer.padding_side = "left"  # batched generation → left padding

    print(f"[eval] loading base {args.base} (bf16) + adapter {args.adapter}")
    base = AutoModelForCausalLM.from_pretrained(args.base, torch_dtype=torch.bfloat16).to("cuda")
    model = PeftModel.from_pretrained(base, args.adapter).to("cuda")
    model.eval()

    pairs = load_pairs(args.gold, args.n, args.include_trivial)
    print(f"[eval] {len(pairs)} (state,gold) 쌍 (trivial 포함={args.include_trivial})")

    # 프롬프트 사전 생성(결정적)
    prompts, golds, metas = [], [], []
    for ex_json, gtac, meta in pairs:
        ex = LmExample.from_json(ex_json)
        prompts.append(collator.collate_input(tokenizer, ex))
        golds.append(gtac)
        metas.append(meta)

    results = []
    bs = args.batch_size
    for i in range(0, len(prompts), bs):
        bp = prompts[i:i + bs]
        enc = tokenizer(bp, return_tensors="pt", padding=True, truncation=True,
                        max_length=hard_seq_len)
        input_ids = enc["input_ids"].to("cuda")
        attn = enc["attention_mask"].to("cuda")
        with torch.no_grad():
            out = model.generate(
                input_ids=input_ids,
                attention_mask=attn,
                max_new_tokens=args.max_new_tokens,
                do_sample=False,
                num_beams=1,
                pad_token_id=tokenizer.pad_token_id,
            )
        gen = out[:, input_ids.shape[1]:]
        texts = tokenizer.batch_decode(gen, skip_special_tokens=True)
        for j, g in enumerate(texts):
            results.append((golds[i + j], g, metas[i + j]))
        print(f"  [gen] {min(i+bs, len(prompts))}/{len(prompts)}", flush=True)

    # 집계
    def norm(s):
        return (s or "").strip()

    def loose(s):
        return (s or "").strip().rstrip(".").strip()

    n = len(results)
    strict = sum(1 for gold, gen, _ in results if gen == gold)
    normd = sum(1 for gold, gen, _ in results if norm(gen) == norm(gold))
    loosed = sum(1 for gold, gen, _ in results if loose(gen) == loose(gold))

    print("\n================ RESULT ================")
    print(f"adapter        : {args.adapter}")
    print(f"n              : {n}")
    print(f"exact strict   : {strict}/{n} = {100*strict/n:.1f}%")
    print(f"exact normalized: {normd}/{n} = {100*normd/n:.1f}%")
    print(f"exact loose(.−) : {loosed}/{n} = {100*loosed/n:.1f}%")
    print("========================================\n")

    if args.out:
        outp = Path(args.out)
        outp.parent.mkdir(parents=True, exist_ok=True)
        with outp.open("w") as f:
            f.write(json.dumps({
                "_summary": True, "adapter": args.adapter, "n": n,
                "strict": strict, "normalized": normd, "loose": loosed,
            }) + "\n")
            for k, (gold, gen, meta) in enumerate(results):
                f.write(json.dumps({
                    "idx": k, "gold": gold, "gen": gen,
                    "strict": gen == gold, "normalized": norm(gen) == norm(gold),
                    **meta,
                }, ensure_ascii=False) + "\n")
        print(f"[eval] per-example 결과 → {outp}")


if __name__ == "__main__":
    main()
