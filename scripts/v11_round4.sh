#!/bin/bash
# ★ v11 4회차 — 확장 캠페인(상위 340) 완료 후 전체 우주 재수집 → 물질화 → 검사 → 60k 학습.
cd /app/coq-modeling
set -o pipefail
say(){ echo "[$(date '+%m-%d %H:%M') KST] $*"; }
fail(){ say "★ 실패: $* — 중단"; echo "V11_PIPELINE_FAIL: $*"; exit 1; }

say "확장 캠페인(상위 340) 완료 대기"
until grep -q 'CAMPAIGN_DONE' all_log/au_research/build_campaign_expand.log 2>/dev/null; do sleep 900; done
BUILT=$(python3 scripts/train_repos.py 2>/dev/null | tr ',' '\n' | grep -c .)
say "상위 340 배치 종료 · 컴파일된 저장소 $BUILT개"
# ★ 사용자 2026-09-02: 전체 프로젝트 다 살리기 → 나머지 전 TRAIN 프로젝트 clone·컴파일 (resume=기처리 건너뜀, ~하루)
say "전체 프로젝트 clone·컴파일 배치 착수 (파일수 상위 전부 ≈ 후보 소진까지)"
python3 scripts/train_build_campaign.py 3000 1200 > all_log/au_research/build_campaign_all.log 2>&1 || say "전체 배치 비정상 종료 — 그때까지분으로 계속"
BUILT=$(python3 scripts/train_repos.py 2>/dev/null | tr ',' '\n' | grep -c .)
say "전체 배치 종료 · 컴파일된 저장소 $BUILT개"

# 진행 중이던 수집(있으면) 종료 대기 — 동시 쓰기 방지
until ! pgrep -f 'train_pool.py 100000[0]' >/dev/null; do sleep 300; done
say "전체 우주 재수집 (resume — 새 저장소·새 정리만 추가)"
bash scripts/collect_all.sh > all_log/au_research/r19_v3_train_all.log 2>&1

# 전체 프로젝트를 이미 시도했으므로 추가 확장은 Omega 패치 1회만(위험 감수) 후 최종 재수집.
NPOOL=$(wc -l < all_log/r11_pool_train_all.jsonl)
say "데이터 포인트 $NPOOL · rango 대비 $(python3 -c "print(f'{$NPOOL/1530000*100:.1f}%')")"
bash scripts/omega_shim.sh > all_log/au_research/omega_shim_final.log 2>&1
python3 scripts/train_build_campaign.py 3000 1200 > all_log/au_research/build_campaign_all2.log 2>&1 || true
bash scripts/collect_all.sh > all_log/au_research/r19_v3b_train_all.log 2>&1

# ★ 신규 저장소 apply/rewrite 변형 증강 (≥120k 일 때). v3 규칙 resume(.done4=신규 정리만) → sft_variants.jsonl.
NPOOL=$(wc -l < all_log/r11_pool_train_all.jsonl)
if [ "$NPOOL" -ge 120000 ]; then
  say "데이터 충분($NPOOL≥120k) → 신규 저장소 변형 증강 (apply/rewrite 등, resume)"
  REPOS=$(python3 scripts/train_repos.py 2>/dev/null)
  NB=6; for i in $(seq 0 $((NB-1))); do
    python3 scripts/variant_gen.py 1000000 "$REPOS" --shard $i/$NB > all_log/au_research/vargen_v4_s$i.log 2>&1 &
  done
  wait
  say "변형 증강 종료 · 채택 변형 총 $(wc -l < all_log/sft_variants.jsonl)"
else
  say "데이터 부족($NPOOL<120k) → 변형 증강 생략, 사용자 판단 대기"
fi
NPOOL=$(wc -l < all_log/r11_pool_train_all.jsonl)
python3 - <<PYIN > all_log/au_research/DATA_REPORT.md 2>&1
import json, collections
rows=[json.loads(l) for l in open("all_log/r11_pool_train_all.jsonl")]
np=len(rows); pj=collections.Counter(r["proj"] for r in rows); ext=sum(1 for r in rows if r.get("gold"))
import os
nvar=sum(1 for _ in open("all_log/sft_variants.jsonl")) if os.path.exists("all_log/sft_variants.jsonl") else 0
print(f"# 데이터 양 보고 (재수집+변형증강 종료)\n\n- 데이터 포인트(수집 지점): {np:,}\n- 그중 외부참조: {ext:,} · 무참조: {np-ext:,}\n- 저장소 수: {len(pj)}\n- 채택 변형(저장소): {nvar:,}\n- rango(≈1.53M) 대비: {np/1530000*100:.1f}% (원지점) · 변형 포함 예상 ≈{(np+min(nvar,np))/1530000*100:.1f}%\n\n상위 저장소: {pj.most_common(10)}")
PYIN
say "★ 데이터 양 보고 준비 완료 → all_log/au_research/DATA_REPORT.md (데이터 포인트 $NPOOL). 물질화·학습은 사용자 판단 대기."
echo "DATA_READY_FOR_REVIEW"
exit 0

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
