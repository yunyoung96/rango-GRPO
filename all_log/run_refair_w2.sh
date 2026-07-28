#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# 공정 재측정 (w2) — cascade-s0 / cascade-s0r2 를 baseline과 "동일 밀도(GPU당 2정리)"로 rand200 재평가.
#   문제: 기존 cascade는 g2w4(GPU당 4정리, 2배 밀도) → tail 정리(500~600s)가 자원경쟁으로 600s 벽 넘어
#         타임아웃 실패 → 성공률 저평가. baseline/sftgrpo/leaf 는 w2(GPU당 2정리)라 비교 불공정.
#   해법: s0=GPU0, s0r2=GPU1 각각 --workers 2 (GPU당 2정리 = baseline과 동일) 병렬 → 두 GPU 다 사용.
#   검증: 성공 elapsed p90 이 w2 baseline(~398s) 수준이면 오염 없음(공정) 확인.
# ══════════════════════════════════════════════════════════════════════════════
set -u
LOG=all_log/refair.log
RAND=data/compcert_bs2_rand200_idx.txt
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
ev(){  # $1=alias $2=gpu $3=outdir
  local d="all_results/$3"
  [ -s "$d/summary.json" ] && [ "$(python3 -c "import json;print(len(json.load(open('$d/summary.json'))['results']))" 2>/dev/null||echo 0)" -ge "$(wc -l < "$RAND")" ] && { say "  [$3] 이미 완료 — 스킵"; return; }
  python3 scripts/run_all.py --alias "$1" --idx-file "$RAND" --timeout 600 --gpus "$2" --workers 2 \
    --out "$d" --description "fair w2 $3 (GPU당 2정리)" >> "$LOG" 2>&1
}
say "════════ 공정 재측정 (w2, GPU당 2정리 = baseline 동일) ════════"
[ -f models/rango-grpo-cascade-s0/adapter/adapter_model.safetensors ]   || { say "✗ s0 모델 없음"; exit 1; }
[ -f models/rango-grpo-cascade-s0r2/adapter/adapter_model.safetensors ] || { say "✗ s0r2 모델 없음"; exit 1; }

ev rango-grpo-cascade-s0   0 rand200_cascade_s0_w2   &
P0=$!
ev rango-grpo-cascade-s0r2 1 rand200_cascade_s0r2_w2 &
P1=$!
wait "$P0"; wait "$P1"

say "════════ 결과 (전부 rand200 w2 = GPU당 2정리, 공정) ════════"
for pair in "cascade_s0:cascade-s0(g2w4=33.5%였음)" "cascade_s0r2:cascade-s0r2(harvest)"; do
  c="${pair%%:*}"; lbl="${pair#*:}"
  RD="all_results/rand200_${c}_w2"
  python3 -c "
import json,statistics as st
r=json.load(open('$RD/summary.json'))['results']
su=sorted(x['elapsed_sec'] for x in r if x['success'])
n=len(r); s=len(su)
p90=su[int(0.9*s)] if s else 0
print(f'  [$lbl] = {s}/{n} = {100*s/n:.1f}%  (성공 elapsed med={st.median(su) if su else 0:.0f}s p90={p90:.0f}s)')
" 2>/dev/null || say "  [$c] 결과 파싱 실패"
done
say "  ── 대조군(w2, 동일조건) ── baseline=33.5% · SFT→GRPO=37.5% · leafsubgoal=37.0%"
say "  ※ 성공 p90 이 baseline w2(~398s) 수준이면 오염 없음(공정) 확인."
say "════════ 완료 ════════"
