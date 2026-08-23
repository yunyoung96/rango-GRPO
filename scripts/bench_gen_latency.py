#!/usr/bin/env python3
"""★ **노드당 생성 지연** — 모델을 바꿔도 탐색이 감당되는가.

증명 탐색 한 노드의 비용은 셋이다.
    Coq 실행    ~300 ms   (지배적, experiment.txt §19-3)
    검색        ~25 ms    (afh70 · CompCert 실측)
    모델 생성   ?         ← 이걸 아무도 안 쟀다

`max_branch` 개 tactic 을 `max_new_tokens=128` 로 뽑는 비용을 실측한다.
같은 프롬프트·같은 dtype(bf16)으로 모델만 갈아 끼운다.

사용: PYTHONPATH=src python3 scripts/bench_gen_latency.py <model> [n] [반복]
"""
import os
import sys
import time

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.insert(0, "src")
import logging  # noqa: E402
logging.disable(logging.CRITICAL)
import torch  # noqa: E402
from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: E402

MODEL = sys.argv[1] if len(sys.argv) > 1 else "Qwen/Qwen2.5-Coder-3B-Instruct"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 8
REP = int(sys.argv[3]) if len(sys.argv) > 3 else 5
PROMPT_TOK = int(os.environ.get("PROMPT_TOK", "2000"))

tok = AutoTokenizer.from_pretrained(MODEL)
t0 = time.time()
model = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.bfloat16).cuda().eval()
load_s = time.time() - t0
nparam = sum(p.numel() for p in model.parameters()) / 1e9
print(f"■ {MODEL}\n   파라미터 {nparam:.2f}B · 로드 {load_s:.0f}s · "
      f"메모리 {torch.cuda.memory_allocated()/2**30:.1f}GiB", flush=True)

# 현실적 길이의 프롬프트 (실제 [PREMISES]…[TACTIC] 모양)
body = ("[PREMISES]\n" + "\n".join(
    f"Lemma _L{i} : forall (x y : nat), x + y = y + x." for i in range(40))
    + "\n[STATE]\nn, m: nat\nH: n <= m\n\nn + 0 = n\n[SCRIPT]\nProof.\nintros.\n[TACTIC]\n")
ids = tok(body, add_special_tokens=False)["input_ids"]
while len(ids) < PROMPT_TOK:
    ids = ids[:1] + ids[1:2] * (PROMPT_TOK - len(ids)) + ids[1:]
ids = ids[-PROMPT_TOK:]
inp = torch.tensor([ids]).cuda()
print(f"   프롬프트 {inp.shape[1]} 토큰 · n={N} · max_new_tokens=128\n", flush=True)


@torch.no_grad()
def run(beam):
    kw = dict(max_new_tokens=128, num_return_sequences=N,
              output_scores=True, return_dict_in_generate=True,
              pad_token_id=tok.pad_token_id or tok.eos_token_id)
    if beam:
        kw.update(num_beams=N, length_penalty=0)
    else:
        kw.update(do_sample=True, temperature=1.0, num_beams=1)
    model.generate(inp, **kw)                      # 워밍업
    torch.cuda.synchronize()
    ts = []
    for _ in range(REP):
        t = time.time()
        o = model.generate(inp, **kw)
        torch.cuda.synchronize()
        ts.append(time.time() - t)
    ts.sort()
    return ts[len(ts) // 2], o.sequences.shape[1] - inp.shape[1]


for beam in (False, True):
    ms, newtok = run(beam)
    tag = "beam" if beam else "sample"
    node = 300 + 25 + ms * 1000
    print(f"   {tag:7s} 생성 {ms*1000:7.0f} ms (생성 토큰 {newtok})"
          f"   →  노드 {node:6.0f} ms  (Coq 300 + 검색 25 + 생성 {ms*1000:.0f})"
          f"   생성 비중 {ms*1000/node*100:4.1f}%", flush=True)

# ── 현실적 길이: tactic 은 보통 10~25 토큰이다 ──────────────────────────────
print()
for L in (16, 32, 64):
    kw = dict(max_new_tokens=L, num_return_sequences=N, do_sample=True,
              temperature=1.0, num_beams=1,
              pad_token_id=tok.pad_token_id or tok.eos_token_id)
    with torch.no_grad():
        model.generate(inp, **kw)
        torch.cuda.synchronize()
        ts = []
        for _ in range(REP):
            t = time.time(); model.generate(inp, **kw); torch.cuda.synchronize()
            ts.append(time.time() - t)
    ts.sort(); ms = ts[len(ts)//2]*1000
    print(f"   sample  {L:3d}토큰  {ms:6.0f} ms  ({ms/L:5.1f} ms/토큰)"
          f"   →  노드 {300+25+ms:6.0f} ms · 생성 비중 {ms/(325+ms)*100:4.1f}%", flush=True)
