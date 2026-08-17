#!/usr/bin/env python3
"""SFT 없는 모델의 **다음 tactic 생성 능력** 비교 — Coq 실행 없이 gold 대조로 빠르게.

## 왜 Coq 없이 하나

rand200 전체를 돌리면 정리당 600초라 모델 하나에 3시간이다. 모델 5~6종을 비교하려면 하루가 넘는다.
대신 **gold 다음 tactic 과 대조**하면 GPU 만으로 수십 분에 끝난다. 완결(QED) 여부는 못 보지만
"다음 한 수를 얼마나 맞히나"는 잴 수 있고, 모델 간 **상대 비교**에는 충분하다.

## 측정 항목

  G1 exact match     : 생성한 첫 tactic 이 gold 와 정확히 일치
  G2 head match      : tactic 이름(destruct/apply/…)이 gold 와 일치 — 방향은 맞았나
  G3 파싱 가능       : Coq tactic 한 줄로 잘라낼 수 있나(마크다운·설명 범벅이면 실패)
  G4 gold NLL        : gold tactic 의 평균 NLL(낮을수록 gold 를 그럴듯하게 봄)

★ SFT 없는 모델은 tactic 하나가 아니라 **증명 전체·설명·마크다운**을 뱉는다(실측).
  그래서 첫 tactic 만 잘라내는 정규화를 거쳐 비교한다 — 안 하면 전부 0점이라 비교가 안 된다.

사용:
    CUDA_VISIBLE_DEVICES=0 python3 scripts/probe_zeroshot_gen.py \
        --model Qwen/Qwen2.5-Coder-3B-Instruct --n 100
"""
import argparse
import json
import logging
import os
import re
import statistics
import sys

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("AUGMENT_V2", "1")
os.environ.setdefault("RERANK_PREMISES", "1")
os.environ.setdefault("INJECT_TYPES", "1")
os.environ.setdefault("INJECT_DEFS", "1")
os.environ.setdefault("HARD_SEQ_LEN", "4096")
os.environ.setdefault("TYPES_TOKENS", "300")
os.environ.setdefault("DEFS_TOKENS", "300")
os.environ.setdefault("FUNC_DEFS_PATH", "data/func_defs_v3.json")
sys.path.insert(0, "src")
logging.disable(logging.CRITICAL)

import torch  # noqa: E402
import yaml  # noqa: E402
from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: E402
from tactic_gen.lm_example import LmExample  # noqa: E402
from tactic_gen.tactic_data import (  # noqa: E402
    example_collator_conf_from_yaml, example_collator_from_conf)

_FENCE = re.compile(r"^\s*```[a-zA-Z]*\s*$")
_HEAD = re.compile(r"^\s*[-+*{}]*\s*([A-Za-z_][\w']*)")


def first_tactic(text: str):
    """생성문에서 **첫 Coq tactic 한 줄**만 잘라낸다. 못 찾으면 None.

    SFT 없는 모델은 설명·마크다운·증명 전체를 뱉으므로 정규화가 필수다.
    """
    if not text:
        return None
    for raw in text.split("\n"):
        ln = raw.strip()
        if not ln or _FENCE.match(raw):
            continue
        if ln.startswith("(*") or ln.startswith("*") and not ln.startswith("*)"):
            continue
        if ln.startswith("[") and ln.endswith("]"):     # [SCRIPT] 같은 섹션 헤더 모방
            continue
        if ln in ("Proof.", "Qed.", "Defined.", "Admitted."):
            return ln
        # tactic 처럼 보이는 줄: 영문자로 시작하고 '.' 또는 ';' 로 끝남
        if re.match(r"^[A-Za-z_\-+*{}\[]", ln) and ("." in ln or ";" in ln):
            m = re.match(r"^(.*?\.)(\s|$)", ln)
            return (m.group(1) if m else ln).strip()
    return None


def head_of(t):
    if not t:
        return None
    m = _HEAD.match(t)
    return m.group(1) if m else None


def norm(t):
    return re.sub(r"\s+", " ", (t or "").strip()).rstrip(".").strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--samples", type=int, default=4, help="상태당 생성 후보 수(pass@k)")
    args = ap.parse_args()

    print(f"모델: {args.model}")
    tok = AutoTokenizer.from_pretrained(args.model)
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token
    tok.truncation_side = "left"
    model = AutoModelForCausalLM.from_pretrained(
        args.model, torch_dtype=torch.bfloat16).cuda().eval()

    cc = yaml.safe_load(open(
        "models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml"))
    col = example_collator_from_conf(example_collator_conf_from_yaml(cc["example_collator"]))

    steps = []
    for line in open("data/grpo_rollouts/goldsft_bs2.jsonl"):
        g = json.loads(line)
        for a in g["attempts"]:
            if a["reward"] < 1.0:
                continue
            for st in a["steps"]:
                if st.get("example") and st.get("tactic"):
                    e = LmExample.from_json(st["example"])
                    e.next_steps = [st["tactic"]]
                    steps.append(e)
                    if len(steps) >= args.n:
                        break
            if len(steps) >= args.n:
                break
        if len(steps) >= args.n:
            break

    n_exact = n_head = n_parse = 0
    nlls = []
    for e in steps:
        prompt = col.collate_input(tok, e)
        gold = e.next_steps[0]
        enc = tok(prompt, return_tensors="pt", truncation=True, max_length=3800).to("cuda")
        with torch.no_grad():
            out = model.generate(**enc, max_new_tokens=64, do_sample=True, temperature=1.0,
                                 num_return_sequences=args.samples,
                                 pad_token_id=tok.pad_token_id)
        gens = tok.batch_decode(out[:, enc["input_ids"].shape[1]:], skip_special_tokens=True)
        cands = [first_tactic(g) for g in gens]
        cands = [c for c in cands if c]
        if cands:
            n_parse += 1
        if any(norm(c) == norm(gold) for c in cands):
            n_exact += 1
        if any(head_of(c) == head_of(gold) for c in cands):
            n_head += 1
        # gold NLL
        pi = enc["input_ids"]
        ti = tok(gold, return_tensors="pt", add_special_tokens=False)["input_ids"].cuda()
        ids = torch.cat([pi, ti], dim=1)
        lab = ids.clone()
        lab[:, : pi.shape[1]] = -100
        with torch.no_grad():
            nlls.append(float(model(ids, labels=lab).loss))

    n = len(steps)
    print(f"\n■ zero-shot 다음 tactic 생성  (예제 {n}개, 상태당 {args.samples}회 샘플)")
    print(f"   G3 파싱 가능       {n_parse:>4}/{n} = {n_parse/n*100:>5.1f}%   (tactic 한 줄로 잘림)")
    print(f"   G2 head 일치       {n_head:>4}/{n} = {n_head/n*100:>5.1f}%   (destruct/apply… 방향)")
    print(f"   G1 exact match     {n_exact:>4}/{n} = {n_exact/n*100:>5.1f}%   (pass@{args.samples})")
    print(f"   G4 gold NLL        {statistics.mean(nlls):.4f}")


if __name__ == "__main__":
    main()
