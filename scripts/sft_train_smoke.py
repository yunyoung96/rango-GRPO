#!/usr/bin/env python3
"""★ 모의 학습 테스트 — 물질화 표본으로 실제 forward/backward 몇 step.

본학습은 다른 서버(규칙) — 여기선 동작확인만:
  ① 토크나이즈: 길이 분포 · hard_seq_len 초과율 (프롬프트 잘림 감시)
  ② 손실 마스크: 프롬프트 -100 · target 만 학습 — 마스크 assert
  ③ 6 step 학습: loss 유한 + 하강 추세 assert
사용: python3 scripts/sft_train_smoke.py [pairs.jsonl] [n]
"""
import json, os, sys
os.environ.setdefault("HF_HUB_OFFLINE", "1")
import yaml, torch
from transformers import AutoModelForCausalLM, AutoTokenizer

SRC = sys.argv[1] if len(sys.argv) > 1 else "all_log/sft_pairs_val.jsonl"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 24
HARD = 4096   # 실측: 3072→target잘림 23%, 4096→2%, 5120→0% (VAL 60지점, 2026-09-01)
cc = yaml.safe_load(open("all_log/ft_qwen3b_v10_conf.yaml"))
name = cc["model_name"]
tok = AutoTokenizer.from_pretrained(name)
rows = [json.loads(l) for l in open(SRC)][:N]
assert rows, "표본 없음"

# ① 길이 분포
lens = []
feats = []
skipped = 0
for r in rows:
    p_ids = tok(r["prompt"] + "\n[TACTIC]\n", add_special_tokens=False).input_ids
    t_ids = tok(r["target"] + tok.eos_token, add_special_tokens=False).input_ids
    ids = p_ids + t_ids
    lens.append(len(ids))
    if len(p_ids) > HARD - 24:          # target 자리가 없다 → 통계만 남기고 건너뜀
        skipped += 1; continue
    lab = [-100] * len(p_ids) + t_ids[:]
    ids, lab = ids[:HARD], lab[:HARD]
    if len(ids) > 2048: ids, lab = ids[-2048:], lab[-2048:]   # 스모크 메모리 컷(target 은 끝쪽이라 보존)
    assert any(x != -100 for x in lab)
    feats.append((ids, lab))
import statistics as st
over = sum(1 for L in lens if L > HARD)
print(f"■ ① 길이: 중앙 {st.median(lens):.0f} · p90 {sorted(lens)[int(len(lens)*.9)]}"
      f" · 최대 {max(lens)} · {HARD} 초과 {over}/{len(lens)} · 학습불가(잘림) {skipped}")
assert feats, "전 표본이 HARD 초과 — seq_len 재설계 필요"

# ② 마스크 검증 표본
ids0, lab0 = feats[0]
n_learn = sum(1 for x in lab0 if x != -100)
print(f"■ ② 마스크: 총 {len(ids0)} tok 중 학습대상 {n_learn} (target 만) ✓")
assert 0 < n_learn < len(ids0)

# ③ 6 step
dev = "cuda" if torch.cuda.is_available() else "cpu"
model = AutoModelForCausalLM.from_pretrained(name, torch_dtype=torch.bfloat16).to(dev)
model.gradient_checkpointing_enable(); model.train()
opt = torch.optim.SGD(model.parameters(), lr=3e-4)   # 스모크: 옵티마이저 상태 0GB
pad = tok.pad_token_id or tok.eos_token_id
losses = []
B = 2
for step in range(6):
    batch = feats[(step * B) % len(feats):][:B] or feats[:B]
    L = max(len(i) for i, _ in batch)
    x = torch.full((len(batch), L), pad, dtype=torch.long)
    y = torch.full((len(batch), L), -100, dtype=torch.long)
    for bi, (i, l) in enumerate(batch):
        x[bi, :len(i)] = torch.tensor(i); y[bi, :len(l)] = torch.tensor(l)
    out = model(input_ids=x.to(dev), labels=y.to(dev))
    out.loss.backward(); opt.step(); opt.zero_grad()
    losses.append(float(out.loss))
    print(f"   step {step}: loss {losses[-1]:.4f}", flush=True)
assert all(torch.isfinite(torch.tensor(losses))), "loss 발산"
assert losses[-1] < losses[0] * 1.05, f"하강 추세 없음: {losses[0]:.3f}→{losses[-1]:.3f}"
print(f"■ ③ 학습 스모크: {losses[0]:.3f} → {losses[-1]:.3f} ✓")
print("TRAIN_SMOKE_DONE")
