#!/bin/bash
# ★ v11 3회차 — rango 식 (무상한 수집 · 60,000 step 고정 · 증강 포함). 수집 종료 대기 → 병합 → 물질화(8샤드)
#   → 검사(≤2 프루닝) → 동적 검증 → conf(60k) → 스모크 → 본학습 착수 + 감시자.
cd /app/coq-modeling
set -o pipefail
say(){ echo "[$(date '+%m-%d %H:%M') KST] $*"; }
fail(){ say "★ 실패: $* — 중단"; echo "V11_PIPELINE_FAIL: $*"; exit 1; }

say "무상한 수집(r19_v2) 종료 대기"
until grep -q 'COLLECT_ALL_DONE' all_log/au_research/r19_v2_train_all.log 2>/dev/null; do sleep 600; done
NPOOL=$(wc -l < all_log/r11_pool_train_all.jsonl); say "수집 종료 · 풀 행 $NPOOL"
[ "$NPOOL" -ge 100000 ] || fail "풀 행 $NPOOL < 100k (무상한인데 너무 적다 — 수집 점검)"

say "① 물질화 (8샤드 · 변형 63,237 저장소 조인)"
NS=8; rm -f all_log/sft2_pairs_train.jsonl.part*
for i in $(seq 0 $((NS-1))); do
  python3 scripts/sft_build_v2.py train 10000000 all_log/r11_pool_train_all.jsonl --shard $i/$NS > all_log/au_research/sft2_r3_$i.log 2>&1 &
done
wait
for i in $(seq 0 $((NS-1))); do grep -q SFTBUILD2_SHARD_DONE all_log/au_research/sft2_r3_$i.log || fail "물질화 샤드 $i"; done
python3 scripts/sft_merge_shuffle.py all_log/sft2_pairs_train.jsonl > all_log/au_research/sft2_r3_merge.log 2>&1 || fail "병합·셔플"
cat all_log/au_research/sft2_r3_merge.log

say "② 정적 검사 C1~C17 (+프루닝 ≤2회, 회당 상한 1%)"
ok=0
for r in 1 2; do
  if python3 scripts/sft_check.py all_log/sft2_pairs_train.jsonl 5120 --drop-out all_log/sft2_drop.idx > all_log/au_research/sft2_r3_check.log 2>&1; then ok=1; break; fi
  say "검사 실패 → 프루닝 $r"
  python3 scripts/sft_prune.py all_log/sft2_pairs_train.jsonl all_log/sft2_drop.idx 0.01 > all_log/au_research/sft2_r3_prune.log 2>&1 || fail "프루닝 상한 초과"
  cat all_log/au_research/sft2_r3_prune.log
done
if [ "$ok" != 1 ]; then
  python3 scripts/sft_check.py all_log/sft2_pairs_train.jsonl 5120 > all_log/au_research/sft2_r3_check.log 2>&1 || fail "정적 검사(프루닝 2회 후)"
fi
say "③ 동적 검증 D1~D3 (표본 30)"
python3 scripts/sft_dyncheck.py all_log/sft2_pairs_train.jsonl 30 > all_log/au_research/sft2_r3_dyncheck.log 2>&1 || fail "동적 검증"

say "④ conf — rango 식 60,000 step 고정"
python3 - <<'PY' || exit 1
import yaml
p="all_log/ft_qwen3_4b_v11_conf.yaml"; c=yaml.safe_load(open(p))
rows=sum(1 for _ in open("all_log/sft2_pairs_train.jsonl"))
eff=int(c["per_device_train_batch_size"])*int(c["gradient_accumulation_steps"])*2
c.update(max_steps=60000, warmup_steps=1800, save_steps=1000, eval_steps=1000, sample_steps=500, milestone_steps=5000, num_eval_examples=200)
yaml.safe_dump(c, open(p,"w"), allow_unicode=True, sort_keys=False)
print(f"■ conf: 행 {rows} · 유효배치 {eff} · 60,000 step ≈ {60000*eff/max(rows,1):.1f} epoch · warmup 1800 · milestone 5000")
PY

rm -f all_log/sft2_pairs_train_valcut.jsonl all_log/sft2_pairs_train_traincut.jsonl
say "⑤ DDP 스모크 (6 step)"
rm -rf models/ft_qwen3_4b_v11_smoke
CUDA_VISIBLE_DEVICES=0,1 torchrun --nproc_per_node 2 --master_port 29572 scripts/sft_train.py all_log/ft_qwen3_4b_v11_conf.yaml --smoke 6 > all_log/au_research/v11_r3_smoke.log 2>&1 || fail "DDP 스모크"
grep -q '스모크 통과' all_log/au_research/v11_r3_smoke.log || fail "스모크 마커 없음"

say "⑥ 본학습 v11-rango(60k) 착수"
rm -rf models/ft_qwen3_4b_v11; mkdir -p models/ft_qwen3_4b_v11
CUDA_VISIBLE_DEVICES=0,1 nohup torchrun --nproc_per_node 2 --master_port 29573 scripts/sft_train.py all_log/ft_qwen3_4b_v11_conf.yaml --resume > all_log/au_research/v11_train.log 2>&1 < /dev/null &
echo $! > models/ft_qwen3_4b_v11/train.pid
nohup bash scripts/train_watch.sh > all_log/au_research/train_watch.log 2>&1 < /dev/null &
say "본학습 시작 pid $(cat models/ft_qwen3_4b_v11/train.pid) · 감시자 가동"
echo "V11_PIPELINE_TRAIN_STARTED"
