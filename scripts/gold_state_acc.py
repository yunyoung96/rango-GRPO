#!/usr/bin/env python3
"""**gold 상태에서 다음 한 수를 맞히는가** — SFT 가 실제로 무엇을 바꿨는지 잰다.

## 왜 이 실험인가

탐색 실패는 두 원인이 섞여 있다: ① gold 궤적을 벗어나 표류 ② 그 자리에서의 선택 실패.
gold prefix 를 준 채로 **한 수만** 물으면 ①이 제거되고 ②만 남는다. Coq 실행도 탐색도
필요 없어 값싸고, 모델 간 비교가 깨끗하다.

데이터는 `goldsft_bs2.jsonl` 의 gold step (CompCert). 프롬프트가 이미 만들어져 있어
검색·주입이 학습 때와 동일하다.

## 재는 것

  E  exact       생성한 첫 tactic == gold (공백·마침표 정규화 후)
  H  head        tactic 이름 일치 (rewrite/apply/destruct …) — 방향은 맞았나
  L  lemma       gold 가 lemma 를 쓰는 경우, **같은 lemma** 를 골랐나  ← 핵심
  P  in-prompt   고른 이름이 프롬프트 안에 있나 (환각률의 역)

사용: CUDA_VISIBLE_DEVICES=0 python3 scripts/gold_state_acc.py <이름> <어댑터|base> <conf> [n] [k]
"""
import json
import os
import re
import sys

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.insert(0, "src")
import logging  # noqa: E402

logging.disable(logging.CRITICAL)
import torch  # noqa: E402
import yaml  # noqa: E402
from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: E402
from tactic_gen.lm_example import LmExample  # noqa: E402
from tactic_gen.tactic_data import (  # noqa: E402
    example_collator_conf_from_yaml, example_collator_from_conf)

TAG = sys.argv[1]
ADAPTER = sys.argv[2]                    # "base" 면 SFT 없음
CONF = sys.argv[3]
N = int(sys.argv[4]) if len(sys.argv) > 4 else 200
K = int(sys.argv[5]) if len(sys.argv) > 5 else 1

cc = yaml.safe_load(open(CONF))
MODEL = cc["model_name"]
col = example_collator_from_conf(example_collator_conf_from_yaml(cc["example_collator"]))

_ID = re.compile(r"\b([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)\b")
_KW = {"rewrite", "apply", "eapply", "erewrite", "in", "with", "by", "at", "using",
       "auto", "eauto", "lia", "now", "intros", "intro", "destruct", "simpl", "unfold",
       "induction", "exact", "left", "right", "split", "constructor", "reflexivity"}
_FENCE = re.compile(r"^\s*```")


def first_tactic(text: str) -> str:
    """생성문에서 첫 tactic 한 줄. SFT 모델은 보통 한 줄만 내지만 base 는 설명을 뱉는다."""
    for raw in (text or "").split("\n"):
        ln = raw.strip()
        if not ln or _FENCE.match(raw) or re.match(r"^\[[A-Z][A-Z_ -]*\]$", ln):
            continue
        if ln.startswith("(*") or ln.startswith("*"):
            continue
        if re.match(r"^[a-zA-Z_\-+*{}\[]", ln):
            m = re.match(r"^(.*?\.)(\s|$)", ln)
            return (m.group(1) if m else ln).strip()
    return (text or "").strip()[:120]


def norm(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").strip()).rstrip(".").strip()


def head_of(t: str) -> str:
    m = re.match(r"^\s*[-+*{}]*\s*([A-Za-z_][\w']*)", t or "")
    return m.group(1).lower() if m else ""


def lemma_of(t: str) -> str:
    """rewrite/apply 계열의 첫 인자(= 고른 lemma). 없으면 ''."""
    h = head_of(t)
    if h not in ("rewrite", "apply", "eapply", "erewrite"):
        return ""
    rest = (t or "")[len(h):] if (t or "").lower().startswith(h) else t
    for x in _ID.findall(rest or ""):
        if x not in _KW and not x.isdigit():
            return x
    return ""


# ── gold step 로드 (CompCert) ──
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
                if len(steps) >= N:
                    break
        if len(steps) >= N:
            break
    if len(steps) >= N:
        break

tok = AutoTokenizer.from_pretrained(MODEL)
tok.truncation_side = "left"
if tok.pad_token_id is None:
    tok.pad_token = tok.eos_token
model = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.bfloat16)
if ADAPTER != "base":
    from peft import PeftModel
    model = PeftModel.from_pretrained(model, ADAPTER)
model = model.cuda().eval()

E = H = L = P = 0
n_lem = n = 0
for e in steps:
    prompt = col.collate_input(tok, e)
    gold = e.next_steps[0].strip()
    enc = tok(prompt, return_tensors="pt", truncation=True, max_length=3000).to("cuda")
    with torch.no_grad():
        out = model.generate(**enc, max_new_tokens=48, do_sample=(K > 1),
                             temperature=(1.0 if K > 1 else None),
                             num_return_sequences=K, pad_token_id=tok.pad_token_id)
    gens = [first_tactic(x) for x in
            tok.batch_decode(out[:, enc["input_ids"].shape[1]:], skip_special_tokens=True)]
    n += 1
    E += any(norm(g) == norm(gold) for g in gens)
    H += any(head_of(g) == head_of(gold) for g in gens)
    gl = lemma_of(gold)
    if gl:
        n_lem += 1
        L += any(lemma_of(g) == gl for g in gens)
        # 고른 이름이 프롬프트 안에 있나 (하나라도)
        picked = [lemma_of(g) for g in gens if lemma_of(g)]
        P += any(re.search(r"\b" + re.escape(p.split(".")[-1]) + r"\b", prompt) for p in picked)

print(f"\n■ {TAG}  (gold step {n}개, pass@{K})")
print(f"   E exact        {E:4d}/{n:<4d} = {E/max(n,1)*100:5.1f}%")
print(f"   H head 일치     {H:4d}/{n:<4d} = {H/max(n,1)*100:5.1f}%")
print(f"   L lemma 일치    {L:4d}/{n_lem:<4d} = {L/max(n_lem,1)*100:5.1f}%   (gold 가 lemma 쓰는 {n_lem}건)")
print(f"   P 고른 이름이 프롬프트에 {P:4d}/{n_lem:<4d} = {P/max(n_lem,1)*100:5.1f}%")
