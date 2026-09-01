#!/bin/bash
# ★ v11 자동 파이프라인 — 전 지점 수집 종료를 기다렸다가: 대량 물질화(v2) → 정적 검사(C1~C15) → 동적 검증(D1~D3)
#   → DDP 스모크 → steps 산정·conf 갱신 → 본학습(DDP 2 GPU) 착수. 어느 단계든 실패하면 거기서 멈추고 로그를 남긴다.
# 사용: nohup bash scripts/v11_pipeline.sh > all_log/au_research/v11_pipeline.log 2>&1 &
cd /app/coq-modeling
set -o pipefail
say(){ echo "[$(date '+%m-%d %H:%M') KST] $*"; }
fail(){ say "★ 실패: $* — 파이프라인 중단"; echo "V11_PIPELINE_FAIL: $*"; exit 1; }

until grep -q 'COLLECT_ALL_DONE' all_log/au_research/r19_v1_train_all.log 2>/dev/null; do sleep 300; done
say "수집 종료 — 변형 생성(전 저장소) 종료 대기 (최대 90분; 실측 19정리/분이라 전량은 ~9h → 기한 후 중단하고 채택분으로 진행)"
DEADLINE=$(( $(date +%s) + 5400 ))
until grep -q 'VARGEN_DONE\|Traceback' all_log/au_research/vargen_full3.log 2>/dev/null || [ $(date +%s) -ge $DEADLINE ]; do sleep 120; done
if ! grep -q 'VARGEN_DONE' all_log/au_research/vargen_full3.log; then
  say "변형 생성 기한 도달 → 중단 (정리 단위 flush 라 채택분·.done 사이드카는 일관; 학습 후 재개 가능)"
  for p in $(pgrep -f 'variant_gen.py 100000[0]'); do kill $p; done; sleep 5
fi
say "변형 행 $(wc -l < all_log/sft_variants.jsonl)"
grep -q 'COLLECT_ALL_DONE rc=0' all_log/au_research/r19_v1_train_all.log || say "수집 종료코드 ≠ 0 (생존률 assert 가능) — 산출은 보존되므로 계속"
NPOOL=$(wc -l < all_log/r11_pool_train_all.jsonl); say "수집 종료 · 풀 행 $NPOOL"
[ "$NPOOL" -ge 1000 ] || fail "풀 행 $NPOOL < 1000"

say "① 대량 물질화 v2 시작"
python3 scripts/sft_build_v2.py train 10000000 all_log/r11_pool_train_all.jsonl > all_log/au_research/sft2_full.log 2>&1 || fail "물질화"
grep -q SFTBUILD2_DONE all_log/au_research/sft2_full.log || fail "물질화 완료 마커 없음"
NROWS=$(wc -l < all_log/sft2_pairs_train.jsonl); say "물질화 행 $NROWS"
[ "$NROWS" -ge 1000 ] || fail "행 $NROWS < 1000"

say "② 정적 검사 C1~C15"
python3 scripts/sft_check.py all_log/sft2_pairs_train.jsonl 5120 > all_log/au_research/sft2_full_check.log 2>&1 || fail "정적 검사"
say "③ 동적 검증 D1~D3 (표본 30)"
python3 scripts/sft_dyncheck.py all_log/sft2_pairs_train.jsonl 30 > all_log/au_research/sft2_full_dyncheck.log 2>&1 || fail "동적 검증"

say "④ steps 산정 → conf 갱신 (유효배치 = 4×4×2GPU = 32 · 3 epoch · warmup 3%)"
python3 - <<'PY' || exit 1
import yaml, math
p="all_log/ft_qwen3_4b_v11_conf.yaml"; c=yaml.safe_load(open(p))
rows=sum(1 for _ in open("all_log/sft2_pairs_train.jsonl")); rows_tr=rows-max(1,rows//50)
eff=int(c["per_device_train_batch_size"])*int(c["gradient_accumulation_steps"])*2
steps=math.ceil(rows_tr/eff*3); warm=max(100, steps*3//100)
c.update(max_steps=steps, warmup_steps=warm, save_steps=max(200, min(1000, steps//10)), eval_steps=max(200, min(1000, steps//10)),
         sample_steps=max(100, min(500, steps//20)), num_eval_examples=200)
yaml.safe_dump(c, open(p,"w"), allow_unicode=True, sort_keys=False)
print(f"■ steps 산정: 행 {rows} (train {rows_tr}) · 유효배치 {eff} · 1 epoch {rows_tr/eff:.0f} step · 3 epoch = {steps} step · warmup {warm} · ≈{steps*20/3600:.1f}h(1GPU 환산 20s/step 기준 DDP 시 절반)")
PY

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
