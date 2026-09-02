#!/bin/bash
# ★ v11 4회차 — 확장 캠페인(상위 340) 완료 후 전체 우주 재수집 → 물질화 → 검사 → 60k 학습.
cd /app/coq-modeling
set -o pipefail
say(){ echo "[$(date '+%m-%d %H:%M') KST] $*"; }
fail(){ say "★ 실패: $* — 중단"; echo "V11_PIPELINE_FAIL: $*"; exit 1; }

say "확장 캠페인(상위 340) 완료 대기"
until grep -q 'CAMPAIGN_DONE' all_log/au_research/build_campaign_expand.log 2>/dev/null; do sleep 900; done
BUILT=$(python3 scripts/train_repos.py 2>/dev/null | tr ',' '\n' | grep -c .)
say "캠페인 종료 · 빌드된 저장소 $BUILT개"

# 진행 중이던 수집(있으면) 종료 대기 — 동시 쓰기 방지
until ! pgrep -f 'train_pool.py 100000[0]' >/dev/null; do sleep 300; done
say "전체 우주 재수집 (resume — 새 저장소·새 정리만 추가)"
bash scripts/collect_all.sh > all_log/au_research/r19_v3_train_all.log 2>&1
TARGET=306000   # 데이터 충분성 게이트 (rango 1.53M 의 20%) — 사용자: 부족하면 위험감수하고 더 컴파일
for GX in 1 2; do
  NPOOL=$(wc -l < all_log/r11_pool_train_all.jsonl)
  say "데이터 포인트 $NPOOL · rango 대비 $(python3 -c "print(f'{$NPOOL/1530000*100:.1f}%')")"
  [ "$NPOOL" -ge "$TARGET" ] && { say "목표(20%) 달성 — 물질화로"; break; }
  say "목표 미달 → 2차 확장 $GX: Omega 패치 + 캠페인 940 + 재수집"
  bash scripts/omega_shim.sh > all_log/au_research/omega_shim_$GX.log 2>&1
  python3 scripts/train_build_campaign.py 940 1200 > all_log/au_research/campaign_940_$GX.log 2>&1 || say "캠페인 940 비정상 — 계속"
  bash scripts/collect_all.sh > all_log/au_research/r19_v3_train_all.log 2>&1
done
NPOOL=$(wc -l < all_log/r11_pool_train_all.jsonl); say "최종 데이터 포인트 $NPOOL"
[ "$NPOOL" -ge 100000 ] || fail "데이터 포인트 $NPOOL < 100k"

say "물질화 (8샤드)"
NS=8; rm -f all_log/sft2_pairs_train.jsonl.part*
for i in $(seq 0 $((NS-1))); do
  python3 scripts/sft_build_v2.py train 10000000 all_log/r11_pool_train_all.jsonl --shard $i/$NS > all_log/au_research/sft2_r4_$i.log 2>&1 &
done
wait
for i in $(seq 0 $((NS-1))); do grep -q SFTBUILD2_SHARD_DONE all_log/au_research/sft2_r4_$i.log || fail "물질화 샤드 $i"; done
python3 scripts/sft_merge_shuffle.py all_log/sft2_pairs_train.jsonl > all_log/au_research/sft2_r4_merge.log 2>&1 || fail "병합"
cat all_log/au_research/sft2_r4_merge.log

say "정적 검사 (+프루닝 ≤2)"
ok=0
for r in 1 2; do
  if python3 scripts/sft_check.py all_log/sft2_pairs_train.jsonl 5120 --drop-out all_log/sft2_drop.idx > all_log/au_research/sft2_r4_check.log 2>&1; then ok=1; break; fi
  say "검사 실패 → 프루닝 $r"; python3 scripts/sft_prune.py all_log/sft2_pairs_train.jsonl all_log/sft2_drop.idx 0.01 > all_log/au_research/sft2_r4_prune.log 2>&1 || fail "프루닝 상한"
done
[ "$ok" = 1 ] || python3 scripts/sft_check.py all_log/sft2_pairs_train.jsonl 5120 > all_log/au_research/sft2_r4_check.log 2>&1 || fail "정적 검사"
say "동적 검증"; python3 scripts/sft_dyncheck.py all_log/sft2_pairs_train.jsonl 30 > all_log/au_research/sft2_r4_dyncheck.log 2>&1 || fail "동적 검증"

say "conf 60k"; python3 - <<'PY' || exit 1
import yaml
c=yaml.safe_load(open("all_log/ft_qwen3_4b_v11_conf.yaml")); rows=sum(1 for _ in open("all_log/sft2_pairs_train.jsonl"))
eff=int(c["per_device_train_batch_size"])*int(c["gradient_accumulation_steps"])*2
c.update(max_steps=60000, warmup_steps=1800, save_steps=1000, eval_steps=1000, sample_steps=500, milestone_steps=5000, num_eval_examples=200)
yaml.safe_dump(c, open("all_log/ft_qwen3_4b_v11_conf.yaml","w"), allow_unicode=True, sort_keys=False)
print(f"■ 데이터 포인트 {rows} · 60,000 step ≈ {60000*eff/max(rows,1):.1f} epoch")
PY
rm -f all_log/sft2_pairs_train_valcut.jsonl all_log/sft2_pairs_train_traincut.jsonl
say "DDP 스모크"; rm -rf models/ft_qwen3_4b_v11_smoke
CUDA_VISIBLE_DEVICES=0,1 torchrun --nproc_per_node 2 --master_port 29572 scripts/sft_train.py all_log/ft_qwen3_4b_v11_conf.yaml --smoke 6 > all_log/au_research/v11_r4_smoke.log 2>&1 || fail "스모크"
grep -q '스모크 통과' all_log/au_research/v11_r4_smoke.log || fail "스모크 마커"
say "본학습 착수"; rm -rf models/ft_qwen3_4b_v11; mkdir -p models/ft_qwen3_4b_v11
CUDA_VISIBLE_DEVICES=0,1 nohup torchrun --nproc_per_node 2 --master_port 29573 scripts/sft_train.py all_log/ft_qwen3_4b_v11_conf.yaml --resume > all_log/au_research/v11_train.log 2>&1 < /dev/null &
echo $! > models/ft_qwen3_4b_v11/train.pid
nohup bash scripts/train_watch.sh > all_log/au_research/train_watch.log 2>&1 < /dev/null &
nohup bash scripts/gate15k.sh > all_log/au_research/gate15k.log 2>&1 < /dev/null &
say "본학습 시작 pid $(cat models/ft_qwen3_4b_v11/train.pid)"
echo "V11_PIPELINE_TRAIN_STARTED"
