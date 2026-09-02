#!/bin/bash
# ★ v11 2회차(규칙표 v3 데이터) 자동 체인 — 변형 6샤드 종료 대기 → 병합 → 재물질화(8샤드) → 검사(+프루닝)
#   → 동적 검증 → steps → DDP 스모크 → 본학습 재착수 + 감시자 재가동.
cd /app/coq-modeling
set -o pipefail
say(){ echo "[$(date '+%m-%d %H:%M') KST] $*"; }
fail(){ say "★ 실패: $* — 중단"; echo "V11_PIPELINE_FAIL: $*"; exit 1; }

say "변형 v3 6샤드 종료 대기"
until [ "$(grep -l 'VARGEN_DONE' all_log/au_research/vargen_v3_s[0-5].log 2>/dev/null | wc -l)" -ge 6 ]; do
  if [ "$(grep -l 'Traceback' all_log/au_research/vargen_v3_s[0-5].log 2>/dev/null | wc -l)" -gt 0 ]; then fail "변형 샤드 오류"; fi
  sleep 300
done
cat all_log/sft_variants.jsonl.s[0-5] > all_log/sft_variants.jsonl
NV=$(wc -l < all_log/sft_variants.jsonl); say "변형 병합 $NV 행"
[ "$NV" -ge 20000 ] || fail "변형 행 $NV < 20000 (v2 는 27,761 이었다)"

say "① 재물질화 (8샤드)"
NS=8; rm -f all_log/sft2_pairs_train.jsonl.part*
for i in $(seq 0 $((NS-1))); do
  python3 scripts/sft_build_v2.py train 10000000 all_log/r11_pool_train_all.jsonl --shard $i/$NS > all_log/au_research/sft2_r2_$i.log 2>&1 &
done
wait
for i in $(seq 0 $((NS-1))); do grep -q SFTBUILD2_SHARD_DONE all_log/au_research/sft2_r2_$i.log || fail "물질화 샤드 $i"; done
python3 scripts/sft_merge_shuffle.py all_log/sft2_pairs_train.jsonl > all_log/au_research/sft2_r2_merge.log 2>&1 || fail "병합·셔플"
cat all_log/au_research/sft2_r2_merge.log

say "② 정적 검사 C1~C16 (+프루닝 ≤1% 1회)"
if ! python3 scripts/sft_check.py all_log/sft2_pairs_train.jsonl 5120 --drop-out all_log/sft2_drop.idx > all_log/au_research/sft2_r2_check.log 2>&1; then
  say "검사 실패 → 프루닝"
  python3 scripts/sft_prune.py all_log/sft2_pairs_train.jsonl all_log/sft2_drop.idx 0.01 > all_log/au_research/sft2_r2_prune.log 2>&1 || fail "프루닝 상한 초과"
  cat all_log/au_research/sft2_r2_prune.log
  python3 scripts/sft_check.py all_log/sft2_pairs_train.jsonl 5120 > all_log/au_research/sft2_r2_check.log 2>&1 || fail "정적 검사(프루닝 후)"
fi
say "③ 동적 검증 D1~D3 (표본 30)"
python3 scripts/sft_dyncheck.py all_log/sft2_pairs_train.jsonl 30 > all_log/au_research/sft2_r2_dyncheck.log 2>&1 || fail "동적 검증"

say "④ steps 산정"
python3 - <<'PY' || exit 1
import yaml, math
p="all_log/ft_qwen3_4b_v11_conf.yaml"; c=yaml.safe_load(open(p))
rows=sum(1 for _ in open("all_log/sft2_pairs_train.jsonl")); rows_tr=rows-max(1,rows//50)
eff=int(c["per_device_train_batch_size"])*int(c["gradient_accumulation_steps"])*2
steps=math.ceil(rows_tr/eff*3); warm=max(100, steps*3//100)
c.update(max_steps=steps, warmup_steps=warm, save_steps=max(200, min(1000, steps//10)), eval_steps=max(200, min(1000, steps//10)),
         sample_steps=max(100, min(500, steps//20)), num_eval_examples=200)
yaml.safe_dump(c, open(p,"w"), allow_unicode=True, sort_keys=False)
print(f"■ steps 산정: 행 {rows} (train {rows_tr}) · 유효배치 {eff} · 3 epoch = {steps} step · warmup {warm}")
PY

rm -f all_log/sft2_pairs_train_valcut.jsonl all_log/sft2_pairs_train_traincut.jsonl
say "⑤ DDP 스모크 (6 step)"
rm -rf models/ft_qwen3_4b_v11_smoke
CUDA_VISIBLE_DEVICES=0,1 torchrun --nproc_per_node 2 --master_port 29572 scripts/sft_train.py all_log/ft_qwen3_4b_v11_conf.yaml --smoke 6 > all_log/au_research/v11_r2_smoke.log 2>&1 || fail "DDP 스모크"
grep -q '스모크 통과' all_log/au_research/v11_r2_smoke.log || fail "스모크 마커 없음"

say "⑥ 본학습 v11(데이터 v3) 재착수"
rm -rf models/ft_qwen3_4b_v11; mkdir -p models/ft_qwen3_4b_v11
CUDA_VISIBLE_DEVICES=0,1 nohup torchrun --nproc_per_node 2 --master_port 29573 scripts/sft_train.py all_log/ft_qwen3_4b_v11_conf.yaml --resume > all_log/au_research/v11_train.log 2>&1 < /dev/null &
echo $! > models/ft_qwen3_4b_v11/train.pid
nohup bash scripts/train_watch.sh > all_log/au_research/train_watch.log 2>&1 < /dev/null &
say "본학습 시작 pid $(cat models/ft_qwen3_4b_v11/train.pid) · 감시자 재가동"
echo "V11_PIPELINE_TRAIN_STARTED"
