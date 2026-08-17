#!/usr/bin/env python3
"""체크포인트의 **eval_loss 를 독립적으로 재측정**한다 (학습을 건드리지 않음).

왜: 학습 중 eval 은 표본 500 개라 ±0.02 정도 노이즈가 있다. 10000→14000 의
    +0.032 상승이 진짜 추세인지 노이즈인지 가리려면 표본을 키워 다시 재야 한다.
    학습과 **완전히 같은** 데이터셋(Split.VAL)·콜레이터·마스킹을 쓴다.

사용: CUDA_VISIBLE_DEVICES=0 python3 scripts/eval_ckpt.py <checkpoint> [N]
"""
import os, sys, yaml, statistics
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.insert(0, "src")
import logging; logging.disable(logging.CRITICAL)
import torch
from torch.utils.data import DataLoader
from transformers import AutoModelForCausalLM
from peft import PeftModel
from tactic_gen.tactic_data import TacticDataConf, LmDataset
from data_management.splits import Split

ckpt = sys.argv[1]
N = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
conf = yaml.safe_load(open("all_log/ft_qwen3b_v5_conf.yaml"))
dsc = TacticDataConf.from_yaml(conf["tactic_data"])
ds = LmDataset.from_conf(dsc, Split.VAL, N)
dl = DataLoader(ds, batch_size=1, collate_fn=ds.collator, num_workers=4)

base = AutoModelForCausalLM.from_pretrained(conf["model_name"], torch_dtype=torch.bfloat16)
model = PeftModel.from_pretrained(base, ckpt).cuda().eval()

tot, n, masked = 0.0, 0, 0
with torch.no_grad():
    for b in dl:
        b = {k: v.cuda() for k, v in b.items() if hasattr(v, "cuda")}
        if int((b["labels"] != -100).sum()) == 0:
            masked += 1
            continue
        tot += float(model(**b).loss); n += 1
print(f"{os.path.basename(ckpt)}  eval_loss = {tot/max(n,1):.4f}   (표본 {n}개"
      + (f", 라벨없음 {masked}개 제외" if masked else "") + ")")
