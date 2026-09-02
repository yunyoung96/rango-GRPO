#!/bin/bash
# ★ v11 파이프라인 재개 — 물질화는 완료(78,311행, 병리 퍼지·재셔플 완료) 상태에서
#   정적 검사(수정판) → 동적 검증 → steps 산정 → DDP 스모크 → 본학습 착수만 다시 수행한다.
cd /app/coq-modeling
set -o pipefail
say(){ echo "[$(date '+%m-%d %H:%M') KST] $*"; }
fail(){ say "★ 실패: $* — 중단"; echo "V11_PIPELINE_FAIL: $*"; exit 1; }

say "② 정적 검사 C1~C16 (+실패 시 지점 단위 프루닝 1회, 상한 1%)"
if ! python3 scripts/sft_check.py all_log/sft2_pairs_train.jsonl 5120 --drop-out all_log/sft2_drop.idx > all_log/au_research/sft2_full_check.log 2>&1; then
  say "검사 실패 → 프루닝 시도"
  python3 scripts/sft_prune.py all_log/sft2_pairs_train.jsonl all_log/sft2_drop.idx 0.01 > all_log/au_research/sft2_prune.log 2>&1 || fail "프루닝(상한 초과 = 체계적 문제)"
  cat all_log/au_research/sft2_prune.log
  python3 scripts/sft_check.py all_log/sft2_pairs_train.jsonl 5120 > all_log/au_research/sft2_full_check.log 2>&1 || fail "정적 검사(프루닝 후에도 실패)"
fi
say "③ 동적 검증 D1~D3 (표본 30)"
python3 scripts/sft_dyncheck.py all_log/sft2_pairs_train.jsonl 30 > all_log/au_research/sft2_full_dyncheck.log 2>&1 || fail "동적 검증"

say "④ steps 산정 → conf 갱신 (유효배치 2×8×2GPU=32 · 3 epoch · warmup 3%)"
python3 - <<'PY' || exit 1
import yaml, math
p="all_log/ft_qwen3_4b_v11_conf.yaml"; c=yaml.safe_load(open(p))
rows=sum(1 for _ in open("all_log/sft2_pairs_train.jsonl")); rows_tr=rows-max(1,rows//50)
eff=int(c["per_device_train_batch_size"])*int(c["gradient_accumulation_steps"])*2
steps=math.ceil(rows_tr/eff*3); warm=max(100, steps*3//100)
c.update(max_steps=steps, warmup_steps=warm, save_steps=max(200, min(1000, steps//10)), eval_steps=max(200, min(1000, steps//10)),
         sample_steps=max(100, min(500, steps//20)), num_eval_examples=200)
yaml.safe_dump(c, open(p,"w"), allow_unicode=True, sort_keys=False)
print(f"■ steps 산정: 행 {rows} (train {rows_tr}) · 유효배치 {eff} · 1 epoch {rows_tr/eff:.0f} step · 3 epoch = {steps} step · warmup {warm}")
PY

rm -f all_log/sft2_pairs_train_valcut.jsonl all_log/sft2_pairs_train_traincut.jsonl
say "⑤ DDP 스모크 (전량 데이터, 6 step)"
rm -rf models/ft_qwen3_4b_v11_smoke
CUDA_VISIBLE_DEVICES=0,1 torchrun --nproc_per_node 2 --master_port 29572 scripts/sft_train.py all_log/ft_qwen3_4b_v11_conf.yaml --smoke 6 > all_log/au_research/v11_full_smoke.log 2>&1 || fail "DDP 스모크"
grep -q '스모크 통과' all_log/au_research/v11_full_smoke.log || fail "스모크 통과 마커 없음"

say "⑥ 본학습 v11 착수 (DDP 2 GPU)"
mkdir -p models/ft_qwen3_4b_v11
CUDA_VISIBLE_DEVICES=0,1 nohup torchrun --nproc_per_node 2 --master_port 29573 scripts/sft_train.py all_log/ft_qwen3_4b_v11_conf.yaml --resume > all_log/au_research/v11_train.log 2>&1 < /dev/null &
echo $! > models/ft_qwen3_4b_v11/train.pid
say "본학습 시작 pid $(cat models/ft_qwen3_4b_v11/train.pid)"
echo "V11_PIPELINE_TRAIN_STARTED"
