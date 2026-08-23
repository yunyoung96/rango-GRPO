#!/usr/bin/env python3
"""★ **실제 CompCert 프롬프트**로 생성 지연을 재고, 양자화가 도움이 되는지 본다.

합성 프롬프트로 잰 값은 길이가 고정이라 현실을 못 본다. CompCert 는 프롬프트가
길다(TEST 길이 중앙 2,016 · p99 2,714). 프롬프트가 길면 prefill 이 늘고, 노드마다
길이가 다르므로 **분포**로 봐야 한다.

또 "느리면 양자화하면 되지 않나" 를 확인한다. BitsAndBytes 4bit 는 **메모리**를
줄이지만 역양자화 비용 때문에 **생성이 더 느려지는** 경우가 흔하다 — 재서 판단한다.

사용: PYTHONPATH=src python3 scripts/bench_gen_compcert.py [모델] [n] [프롬프트수]
"""
import collections
import copy
import logging
import os
import random
import sys
import time

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("CACHE_MAX_PAGE", "0")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")
os.environ["CUT_DROP_HOPELESS"] = "0"
os.environ["DROP_HALLUC"] = "0"
sys.path.insert(0, "src")
sys.path.insert(0, "scripts")
logging.disable(logging.CRITICAL)

MODEL = sys.argv[1] if len(sys.argv) > 1 else "Qwen/Qwen2.5-Coder-3B-Instruct"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 8
NP = int(sys.argv[3]) if len(sys.argv) > 3 else 24
QUANT = os.environ.get("QUANT", "bf16")            # bf16 | 4bit

import torch  # noqa: E402
import yaml  # noqa: E402
from transformers import AutoModelForCausalLM  # noqa: E402
from data_management.splits import Split  # noqa: E402
from tactic_gen.tactic_data import (TacticDataConf, LmDataset,  # noqa: E402
                                    example_collator_from_conf, get_tokenizer)

cc = yaml.safe_load(open("all_log/ft_qwen3b_v9_conf.yaml"))
_td = copy.deepcopy(cc["tactic_data"])
_td["cache_loc"] = "/tmp/roundtrip"
conf = TacticDataConf.from_yaml(_td)
tok = get_tokenizer(MODEL)
ds = LmDataset.from_conf(conf, Split.TEST, None)
coll = example_collator_from_conf(conf.collator_conf)
TOTAL = ds.shuffled_idx.split_length(Split.TEST)

print(f"■ CompCert 프롬프트 {NP}개 수집 …", flush=True)
prompts = []
random.seed(31)
tried = 0
while len(prompts) < NP and tried < 20000:
    i = random.randrange(TOTAL)
    tried += 1
    try:
        ex = ds.resolved_example(i)
    except Exception:
        continue
    if "AbsInt-CompCert" not in (getattr(ex, "file_name", "") or ""):
        continue
    try:
        p = coll.collate_input(tok, ex, normalize=True)
    except Exception:
        continue
    prompts.append(p)
lens = sorted(len(tok(p, add_special_tokens=False)["input_ids"]) for p in prompts)
print(f"   길이 중앙 {lens[len(lens)//2]} · 최소 {lens[0]} · 최대 {lens[-1]}\n", flush=True)

kw_load = dict(dtype=torch.bfloat16)
if QUANT == "4bit":
    from transformers import BitsAndBytesConfig
    kw_load = dict(quantization_config=BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True))
t0 = time.time()
model = AutoModelForCausalLM.from_pretrained(MODEL, **kw_load)
if QUANT != "4bit":
    model = model.cuda()
model.eval()
print(f"■ {MODEL} · {QUANT} · 로드 {time.time()-t0:.0f}s · "
      f"메모리 {torch.cuda.memory_allocated()/2**30:.1f}GiB · n={N}\n", flush=True)

GEN = 24                                   # 현실적 tactic 길이


@torch.no_grad()
def once(p):
    ids = tok(p, add_special_tokens=False, return_tensors="pt")["input_ids"].cuda()
    t = time.time()
    model.generate(ids, max_new_tokens=GEN, num_return_sequences=N,
                   do_sample=True, temperature=1.0, num_beams=1,
                   pad_token_id=tok.pad_token_id or tok.eos_token_id)
    torch.cuda.synchronize()
    return (time.time() - t) * 1000, ids.shape[1]


once(prompts[0])                            # 워밍업
rows = [once(p) for p in prompts]
ms = sorted(r[0] for r in rows)
q = lambda v, p: v[min(len(v) - 1, int(len(v) * p))]
print(f"■ 생성 {GEN}토큰 · n={N} (CompCert 실프롬프트 {len(rows)}개)")
print(f"   중앙 {q(ms,.5):6.0f} ms · p75 {q(ms,.75):6.0f} · p90 {q(ms,.9):6.0f} · 최대 {ms[-1]:6.0f}")
print(f"   노드(=Coq 300 + 검색 25 + 생성)  중앙 {325+q(ms,.5):6.0f} ms"
      f"   생성 비중 {q(ms,.5)/(325+q(ms,.5))*100:4.1f}%")
# 길이 의존성
rows.sort(key=lambda r: r[1])
h = len(rows) // 2
print(f"   짧은 절반(프롬프트 중앙 {rows[h//2][1]}) {sum(r[0] for r in rows[:h])/h:6.0f} ms"
      f"  ·  긴 절반(중앙 {rows[h+h//2][1]}) {sum(r[0] for r in rows[h:])/(len(rows)-h):6.0f} ms")
