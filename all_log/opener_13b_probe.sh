#!/bin/bash
# 1.3B capacity probe: DeepSeek-Coder-1.3B(rango와 같은 base)를 opener로 학습 → compound 인자 일치율 측정.
#   질문: 1.3B도 compound destruct(인자 포함)를 여는 capacity가 있나? (7B 92% / 32B추론 14% 대비)
cd /app/coq-modeling || exit 1
LOG=all_log/opener_13b_probe.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" >> "$LOG"; }
: > "$LOG"
M13=deepseek-ai/deepseek-coder-1.3b-instruct
SAVE=models/opener-1.3b-tac/adapter

# ── 학습 (opener-tac 데이터 동일, 동일 recipe) ──
say "Stage1: opener-tac SFT on 1.3B (deepseek-coder-1.3b-instruct)"
HF_HUB_OFFLINE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_VISIBLE_DEVICES=1 \
  python3 scripts/train_opener_tac.py --model "$M13" --save "$SAVE" --epochs 5 --max_len 3072 >> "$LOG" 2>&1
[ -f "$SAVE/adapter_model.safetensors" ] || { say "SFT 실패 — 중단"; exit 1; }
say "Stage1 완료: OK"

# ── 인자 일치율 측정 (7B와 동일 방식) ──
say "Stage2: compound 인자 일치율 측정"
HF_HUB_OFFLINE=1 CUDA_VISIBLE_DEVICES=1 python3 - >> "$LOG" 2>&1 <<'PY'
import sys, json, re, random, torch
sys.path.insert(0,'src')
from model_deployment.planner_client import PlannerClient, PlannerConf, _OPENER_TAC_SYSTEM
NMD="No More Decomposition"
def kw(t):
    m=re.match(r'\s*([a-z_]+)',(t or '').strip().lstrip('\n'));return m.group(1) if m else ''
def norm(t):
    t=(t or '').strip().lstrip('\n').split(' as ')[0]
    t=re.sub(r'\s+eqn:\S+','',t);t=t.split(';')[0].strip().rstrip('.')
    return re.sub(r'\s+',' ',t)
rows=[json.loads(l) for l in open('data/grpo_rollouts/opener_tac.jsonl')]
struct=[r for r in rows if r['target']!=NMD]; nmd=[r for r in rows if r['target']==NMD]
pc=PlannerClient(PlannerConf(model_name='deepseek-ai/deepseek-coder-1.3b-instruct',
    init_adapter='models/opener-1.3b-tac/adapter', tac_mode=True, device='cuda:0', temperature=0.0))
pc._ensure_loaded()
def gen(inp):
    m=[{"role":"system","content":_OPENER_TAC_SYSTEM},{"role":"user","content":inp}]
    prompt=pc._tok.apply_chat_template(m,tokenize=False,add_generation_prompt=True)
    ii=pc._tok(prompt,return_tensors="pt").to('cuda:0')
    with torch.no_grad():
        o=pc._model.generate(**ii,max_new_tokens=80,do_sample=False,pad_token_id=pc._tok.eos_token_id)
    return pc._tok.decode(o[0][ii['input_ids'].shape[1]:],skip_special_tokens=True).strip()
random.Random(0).shuffle(struct)
exact=kwm=n=0
for r in struct[:60]:
    p=gen(r['input']); n+=1
    if norm(p)==norm(r['target']): exact+=1
    if kw(p)==kw(r['target']): kwm+=1
nc=nn=0
for r in nmd[:40]:
    if NMD.lower() in gen(r['input']).lower(): nc+=1
    nn+=1
print(f"[1.3B opener capacity probe]")
print(f"  ★인자까지 정확 일치: {exact}/{n} = {100*exact/n:.0f}%   (7B 92% / 32B추론 14%)")
print(f"  종류(destruct 등) 일치: {kwm}/{n} = {100*kwm/n:.0f}%   (7B 95%)")
print(f"  NMD 인식: {nc}/{nn} = {100*nc/max(nn,1):.0f}%   (7B 92%)")
PY
say "=== PROBE 완료 PROBE13_DONE ==="
