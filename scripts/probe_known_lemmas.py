#!/usr/bin/env python3
"""★ 베이스 모델이 **실제로 아는 lemma 이름**이 무엇인지 프로브한다.

## 왜

"stdlib 경로에 있다" 와 "모델이 안다" 는 다르다. 실측 표본을 보면 gold 의 62.1% 가
stdlib 경로지만 그 안에는 `Nat.add_comm`(누구나 아는 것)과 `nztail`·`to_lu_succ`
(Decimal 내부 보조정리)가 섞여 있다.

**어느 쪽인지 알아야** "이 lemma 는 검색 없이도 모델이 떠올릴 수 있으니 cut 이 불필요"
같은 판단을 근거 있게 할 수 있다.

## 방법

이름만 주고 **진술(statement)을 생성**하게 한 뒤, 실제 진술과 비교한다.

    프롬프트:  Lemma Nat.add_comm :
    생성:      forall n m : nat, n + m = m + n.
    실제:      forall n m : nat, n + m = m + n.
    → 안다

채점은 **토큰 집합 F1** 로 한다(공백·괄호 차이를 흡수). 0.8 이상이면 '안다'.

## 대조군

  · stdlib 이름 (경로 기반)
  · 프로젝트 전용 이름
  · **뒤섞은 가짜 이름**(예: `add_comm` → `comm_add`) — 우연히 맞히는 정도를 잰다

사용: python3 scripts/probe_known_lemmas.py [샘플수]
"""
import collections
import json
import os
import random
import re
import sqlite3
import sys

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.insert(0, "src")
import logging  # noqa: E402

logging.disable(logging.CRITICAL)
import torch  # noqa: E402
from transformers import AutoTokenizer, AutoModelForCausalLM  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 200
MODEL = os.environ.get("PROBE_MODEL", "Qwen/Qwen2.5-Coder-3B-Instruct")
DB = "/tmp/coq-dataset/sentences.db"
_STD = re.compile(r"(opam/[^/]*/lib/coq/theories/|/coq/theories/|coq_projects/coq/theories/)",
                  re.I)
_DECL = re.compile(r"^\s*(?:Lemma|Theorem|Corollary|Fact|Proposition|Remark)\s+"
                   r"([A-Za-z_][\w']*)\s*(?::|\s)(.*)$", re.S)

rng = random.Random(0)
std, proj = [], []
con = sqlite3.connect(DB)
for text, path in con.execute("select text, file_path from sentence limit 400000"):
    m = _DECL.match(text or "")
    if not m:
        continue
    name, body = m.group(1), " ".join(m.group(2).split())
    body = body.lstrip(": ").rstrip(".")
    if len(body) < 15 or len(body) > 200:
        continue
    (std if _STD.search(path or "") else proj).append((name, body, path))
rng.shuffle(std)
rng.shuffle(proj)
print(f"■ 후보: stdlib {len(std):,} · 프로젝트 {len(proj):,}", flush=True)

tok = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.bfloat16,
                                             device_map="cuda")
model.eval()


def f1(a: str, b: str) -> float:
    ta = collections.Counter(re.findall(r"[A-Za-z_][\w']*|\S", a))
    tb = collections.Counter(re.findall(r"[A-Za-z_][\w']*|\S", b))
    inter = sum((ta & tb).values())
    if not inter:
        return 0.0
    p = inter / max(sum(ta.values()), 1)
    r = inter / max(sum(tb.values()), 1)
    return 2 * p * r / (p + r)


def scramble(nm: str) -> str:
    """`add_comm` → `comm_add`. 존재하지 않을 이름을 만든다."""
    parts = nm.split("_")
    if len(parts) < 2:
        return nm[::-1]
    rng.shuffle(parts)
    return "_".join(parts)


@torch.no_grad()
def gen(prompts):
    out = []
    for i in range(0, len(prompts), 8):
        b = prompts[i:i + 8]
        enc = tok(b, return_tensors="pt", padding=True, truncation=True,
                  max_length=128).to("cuda")
        o = model.generate(**enc, max_new_tokens=48, do_sample=False,
                           pad_token_id=tok.eos_token_id)
        for j in range(len(b)):
            g = tok.decode(o[j][enc["input_ids"].shape[1]:], skip_special_tokens=True)
            out.append(" ".join(g.split()).split(".")[0])
    return out


tok.padding_side = "left"
if tok.pad_token is None:
    tok.pad_token = tok.eos_token

groups = {
    "stdlib": std[:N],
    "프로젝트": proj[:N],
    "가짜이름(대조군)": [(scramble(n), b, p) for n, b, p in std[N:2 * N]],
}
res = {}
for label, items in groups.items():
    prompts = [f"Lemma {n} :" for n, _, _ in items]
    gens = gen(prompts)
    scores = [f1(g, b) for g, (_, b, _) in zip(gens, items)]
    known = sum(1 for x in scores if x >= 0.8)
    part = sum(1 for x in scores if 0.5 <= x < 0.8)
    res[label] = (known / max(len(items), 1) * 100, part / max(len(items), 1) * 100,
                  sum(scores) / max(len(scores), 1), items, gens, scores)
    print(f"   {label:16s} 안다(F1≥0.8) {res[label][0]:5.1f}% · "
          f"부분(0.5~0.8) {res[label][1]:5.1f}% · 평균F1 {res[label][2]:.3f}", flush=True)

print(f"\n■ 베이스 모델이 아는 lemma ({MODEL}, 각 {N}개)")
print(f"\n   {'그룹':18s} {'안다(F1≥0.8)':>13s} {'부분(0.5~)':>12s} {'평균 F1':>9s}")
for label in groups:
    k, p, f, *_ = res[label]
    print(f"   {label:18s} {k:12.1f}% {p:11.1f}% {f:9.3f}")

print(f"\n   ■ stdlib 표본 (F1 높은 순)")
items, gens, scores = res["stdlib"][3], res["stdlib"][4], res["stdlib"][5]
order = sorted(range(len(items)), key=lambda i: -scores[i])
for i in order[:5]:
    print(f"     [{scores[i]:.2f}] {items[i][0]}")
    print(f"           실제: {items[i][1][:78]}")
    print(f"           생성: {gens[i][:78]}")
print(f"\n   ■ stdlib 인데 모르는 것 (F1 낮은 순)")
for i in order[-4:]:
    print(f"     [{scores[i]:.2f}] {items[i][0]:24s} {items[i][2][-46:]}")
