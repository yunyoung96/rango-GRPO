#!/usr/bin/env python3
"""베이스 모델(SFT 없음)의 Coq 이해 능력 프로브 — 순전파만으로 측정.

## 왜

ablation 은 "SFT 된 모델이 [TYPES] 를 안 읽는다"를 보였다(clean vs wrong 차이 ±0, p=1.000).
그런데 그게 **학습 레시피 탓인지, 애초에 1.3B 가 못 읽는 것인지** 구분이 안 됐다.
베이스 모델로 같은 것을 재면 그 구분이 된다:

  · 베이스도 clean ≈ wrong  →  1.3B 가 이 형식의 타입 정보를 **애초에 못 쓴다**
                               → 프롬프트 주입 방향 자체를 접어야 한다
  · 베이스는 clean < wrong  →  정보는 쓸 수 있는데 **SFT 가 그 능력을 죽였다**
                               → 학습 레시피(정규화 등)로 되살릴 여지가 있다

## 무엇을 재나 (전부 생성 없이 NLL — 빠르고 결정적)

  P1. gold tactic 의 NLL을 조건별로: base / +clean / +wrong / +empty
      (프롬프트 형식은 고정하고 [TYPES] 내용만 바꾼다 = 정보의 기여만 분리)
  P2. destruct 분기수: `destruct x as [` 다음에 올 `|` 개수의 확률
      정답 분기수의 NLL vs 틀린 분기수의 NLL — 낮으면 arity 를 안다는 뜻
  P3. 생성자 이름 회상: [TYPES] 에 있는 생성자 이름의 NLL (읽으면 낮아야)

사용:
    CUDA_VISIBLE_DEVICES=1 python3 scripts/probe_base_coq.py --n 120
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
sys.path.insert(0, "src")
logging.disable(logging.CRITICAL)

import torch  # noqa: E402
from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: E402
from tactic_gen.lm_example import LmExample  # noqa: E402
from tactic_gen.augment import types_v2, definitions_v2, project_of  # noqa: E402

DEFAULT_MODEL = "deepseek-ai/deepseek-coder-1.3b-instruct"


def nll(model, tok, prompt: str, target: str) -> float:
    """target 토큰들의 평균 NLL(자연로그). 낮을수록 모델이 그 답을 그럴듯하게 본다."""
    pi = tok(prompt, return_tensors="pt", truncation=True, max_length=3800)["input_ids"]
    ti = tok(target, return_tensors="pt", add_special_tokens=False)["input_ids"]
    ids = torch.cat([pi, ti], dim=1).cuda()
    labels = ids.clone()
    labels[:, : pi.shape[1]] = -100          # 프롬프트에는 loss 안 걸음
    with torch.no_grad():
        out = model(ids, labels=labels)
    return float(out.loss)


_CTOR = re.compile(r"(\|\s*)([A-Za-z_][\w']*)")


def corrupt_types(block: str) -> str:
    """생성자 **이름만** 같은 길이의 가짜로 바꾼다. 형식·구분자·토큰수를 그대로 유지.

    ★ 왜 길이까지 맞추나(자체검증에서 잡힌 결함): 처음엔 '|' 를 지우고 재조립해
      `:= |` 가 `:=` 로 바뀌고 프롬프트 길이가 최대 28토큰 달라졌다. NLL 은 길이·형식에
      민감해서, 그러면 '내용의 기여'가 아니라 '형식 차이'를 재게 된다.
      → 구분자는 손대지 않고 이름 문자만 치환하며, **같은 글자수**로 만든다.
    """
    def rep(m):
        name = m.group(2)
        fake = ("Zq" + name[2:]) if len(name) > 2 else "Zq"[: len(name)]
        return m.group(1) + fake
    out = _CTOR.sub(rep, block)
    # 첫 생성자가 '|' 없이 오는 표기(`:= foo : T | ...`)도 바꾼다
    out = re.sub(r"(:=\s*)([A-Za-z_][\w']*)",
                 lambda m: m.group(1) + (("Zq" + m.group(2)[2:]) if len(m.group(2)) > 2
                                         else "Zq"[: len(m.group(2))]), out, count=1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=120)
    ap.add_argument("--model", default=DEFAULT_MODEL,
                    help="비교 대상 모델. 크기가 커지면 타입을 읽는지 보려면 7B 지정")
    args = ap.parse_args()

    print(f"모델: {args.model}")
    tok = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForCausalLM.from_pretrained(
        args.model, torch_dtype=torch.bfloat16).cuda().eval()
    idx = json.load(open("data/func_defs_v3.json"))

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
    # 타입이 결정적인 스텝(destruct/induction)을 우선으로 고른다
    key = [s for s in steps if re.search(r"\b(destruct|induction)\b", s.next_steps[0])]
    other = [s for s in steps if s not in key]
    sel = (key[: args.n // 2] + other[: args.n - len(key[: args.n // 2])])[: args.n]
    print(f"프로브 예제 {len(sel)}개 (타입결정적 {len(key[:args.n//2])}개 포함)\n")

    # ★ 정규화 조건 추가: 이름을 T0/C0 로 바꾸면 **암기 경로가 끊겨** 읽을 수밖에 없다.
    #   앞선 프로브에서 clean ≈ wrong (차이 -0.005) 이 나온 건 "이름 암기로 답이 나오므로
    #   정의를 볼 이유가 없었다"로도 설명된다. 정규화하면 그 설명이 검증된다:
    #     norm_clean < norm_wrong  →  이름이 막히면 정의를 읽는다 (v4 방향이 맞다)
    #     norm_clean ≈ norm_wrong  →  이름과 무관하게 못 읽는다  (v4 도 소용없다)
    from tactic_gen.normalize_names import build_mapping, apply_mapping
    res = {k: [] for k in ("base", "clean", "wrong", "empty", "norm_clean", "norm_wrong")}
    n_typed = 0
    for e in sel:
        goal = e.proof_state or ""
        tgt = e.next_steps[0]
        tl = types_v2(goal, idx, project=e.file_name, budget_tok=300)
        dl = definitions_v2(goal, idx, project=e.file_name, budget_tok=300)
        if not tl and not dl:
            continue
        n_typed += 1
        blk = "\n".join(l for _, l in (tl + dl))
        cor = corrupt_types(blk)
        if cor == blk:
            continue          # 조작이 안 되는 정의(생성자 없음) — 조건 대비가 성립 안 함
        head = f"[STATE]\n{goal}\n[SCRIPT]\n{e.proof_script or ''}\n"
        conds = {
            "base": head,
            "clean": head + f"[TYPES]\n{blk}\n",
            "wrong": head + f"[TYPES]\n{cor}\n",
            "empty": head + "[TYPES]\n(none)\n",
        }
        # 정규화: goal·정의·정답에 **같은 매핑**을 적용(이름 암기 차단)
        inj = dict(tl + dl)
        mp = build_mapping(inj, str(e.file_name), avoid_text=head + blk + tgt)
        if mp:
            nb, nc = apply_mapping(blk, mp), apply_mapping(cor, mp)
            nh, ntg = apply_mapping(head, mp), apply_mapping(tgt, mp)
            conds["norm_clean"] = nh + f"[TYPES]\n{nb}\n"
            conds["norm_wrong"] = nh + f"[TYPES]\n{nc}\n"
        for k, p in conds.items():
            t = ntg if k.startswith("norm_") else tgt
            res[k].append(nll(model, tok, p + "[TACTIC]\n", t))

    print(f"■ P1. gold tactic NLL (예제 {n_typed}개, 낮을수록 그럴듯)")
    base = statistics.mean(res["base"])
    for k in ("base", "clean", "wrong", "empty", "norm_clean", "norm_wrong"):
        if not res[k]:
            continue
        m = statistics.mean(res[k])
        print(f"   {k:11s} {m:.4f}   (n={len(res[k])})")
    d = statistics.mean(res["clean"]) - statistics.mean(res["wrong"])
    print(f"\n   ★ clean − wrong      = {d:+.4f}   (원래 이름)")
    if res["norm_clean"] and res["norm_wrong"]:
        dn = statistics.mean(res["norm_clean"]) - statistics.mean(res["norm_wrong"])
        print(f"   ★ norm_clean − norm_wrong = {dn:+.4f}   (이름 정규화)")
        print("\n   해석:")
        print("     정규화에서도 ≈0  → 이름과 무관하게 못 읽는다. v4 방향도 소용없다.")
        print("     정규화에서 음수  → 이름이 막히면 정의를 읽는다. v4 방향이 맞다.")


if __name__ == "__main__":
    main()
