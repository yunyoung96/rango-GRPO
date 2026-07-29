#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# BFS-Prover (arXiv:2502.03438) 논문 그대로 구현 — expert-iteration + DPO(컴파일러피드백).
#   π_0 = rango SFT baseline(checkpoint-54500). train-300 위 EI, 최종 rand200 BFS 평가.
#   라운드 r:
#     1) Beam Filtering: 결정론적 beam(bfs-prover-beam)로 쉬운 정리 식별→ hard만 남김(쉬운 것 데이터 미추가).
#     2) Data Collection: BFS temperature 샘플(bfs-prover-trace)로 hard 탐색→ 트리 덤프.
#     3) 추출: 성공경로(state,tactic)=SFT 누적, 컴파일에러 tactic=DPO negative.
#     4) SFT: baseline 위에 **누적 성공 코퍼스** 전체로 SFT(grpo_train --sft).
#     5) DPO: 그 위에 라운드 에러쌍으로 DPO(dpo_train) → 다음 라운드 탐색정책.
#   최종: baseline vs 학습정책 모두 rand200 BFS 탐색으로 평가(학습 기여 분리).
# ══════════════════════════════════════════════════════════════════════════════
set -u
LOG=all_log/bfsprover.log
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
INIT=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500   # π_0 = rango SFT baseline
TRAIN=data/compcert_bs2_train_idx.txt      # 300
RAND=data/compcert_bs2_rand200_idx.txt     # 200
WORK=data/bfs_expert_iter
GPUS="${GPUS:-1}"; SW="${SW:-20}"    # 검색 워커. 평가 워커(EVALW)는 아래 eval 섹션에서 기본6(공정성).
BEAMT="${BEAMT:-120}"; BFST="${BFST:-300}"; EVALT="${EVALT:-600}"
NROUNDS="${NROUNDS:-2}"
CUMSFT="$WORK/cum_sft.jsonl"
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
TS="taskset -c 0-127"
# ★ 서버(탐색/평가)는 어댑터의 부모 dir에서 training_conf.yaml/lm-example-conf.yaml 을 읽는다.
#   학습(grpo_train/dpo_train)은 안 만들어주므로 저장 후 반드시 복사(안 하면 서버 FileNotFound 크래시).
cpconf(){ cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml "$1/" 2>/dev/null; }

[ -f "$INIT/adapter_model.safetensors" ] || { say "✗ baseline(checkpoint-54500) 없음: $INIT"; exit 1; }
mkdir -p "$WORK"
say "════ BFS-Prover(2502.03438) EI — π_0=rango baseline, $NROUNDS 라운드, GPU$GPUS w$SW ════"

adapter="$INIT"
for r in $(seq 1 "$NROUNDS"); do
  RD="$WORK/round$r"; mkdir -p "$RD"
  say "──── Round $r (탐색정책 adapter=$adapter) ────"

  # 1) Beam Filtering (결정론적) — 쉬운 정리 식별. run_all이 --out으로 내부 resume(완료 idx skip).
  BFS_ADAPTER="$adapter" $TS python3 scripts/run_all.py --alias bfs-prover-beam \
    --idx-file "$TRAIN" --timeout "$BEAMT" --gpus "$GPUS" --workers "$SW" \
    --out "$RD/beam" --description "bfs r$r beam filter" >> "$LOG" 2>&1
  python3 -m tactic_gen.bfs_dpo_data hard "$RD/beam/summary.json" "$TRAIN" "$RD/hard.txt" | tee -a "$LOG"

  # 2) Data Collection — BFS temperature 샘플 + 트리 덤프. (collect 미시작일때만 trace 초기화)
  [ -s "$RD/collect/summary.json" ] || rm -f "$RD"/trees.jsonl.* "$RD/trees_all.jsonl"
  BFS_ADAPTER="$adapter" BFS_TRACE_OUT="$RD/trees.jsonl" $TS python3 scripts/run_all.py --alias bfs-prover-trace \
    --idx-file "$RD/hard.txt" --timeout "$BFST" --gpus "$GPUS" --workers "$SW" \
    --out "$RD/collect" --description "bfs r$r collect" >> "$LOG" 2>&1
  cat "$RD"/trees.jsonl.* > "$RD/trees_all.jsonl" 2>/dev/null
  BSOLVE=$(python3 -c "import json;r=json.load(open('$RD/collect/summary.json'))['results'];print(sum(1 for x in r if x['success']),len(r))" 2>/dev/null||echo '? ?')
  say "  BFS 수집: 성공정리/hard = $BSOLVE"

  # 3) 추출: SFT(누적 append) + DPO쌍. ★재시작 중복방지: 이 라운드 추출을 아직 안 했을 때만 append.
  if [ ! -f "$RD/.extracted" ]; then
    python3 -m tactic_gen.bfs_dpo_data extract "$RD/trees_all.jsonl" "$CUMSFT" "$RD/pairs.jsonl" | tee -a "$LOG"
    touch "$RD/.extracted"
  fi

  # 4) SFT (baseline 위, 누적 성공 코퍼스 전체)
  if [ ! -f "$RD/sft/adapter/adapter_model.safetensors" ]; then
    CUDA_VISIBLE_DEVICES="${GPUS%%,*}" $TS python3 -m tactic_gen.grpo_train --sft \
      --rollouts "$CUMSFT" --model_name "$BASE" --init_adapter "$INIT" \
      --collator_conf "$CONF" --max_len 3072 --save_dir "$RD/sft/adapter" \
      --epochs 2 --lr 1e-5 --micro_bsz 4 >> "$LOG" 2>&1
  fi
  cpconf "$RD/sft"
  # 5) DPO (sft 위, 라운드 on-policy 에러쌍)
  if [ ! -f "$RD/dpo/adapter/adapter_model.safetensors" ] && [ -s "$RD/pairs.jsonl" ]; then
    CUDA_VISIBLE_DEVICES="${GPUS%%,*}" $TS python3 src/tactic_gen/dpo_train.py \
      --pairs "$RD/pairs.jsonl" --model_name "$BASE" --init_adapter "$RD/sft/adapter" \
      --save_dir "$RD/dpo/adapter" --collator_conf "$CONF" --max_len 3072 \
      --epochs 1 --lr 5e-7 --beta 0.1 --micro_bsz 2 >> "$LOG" 2>&1
  fi
  cpconf "$RD/dpo"
  # 다음 라운드 탐색정책 = DPO(있으면) 아니면 SFT
  if [ -f "$RD/dpo/adapter/adapter_model.safetensors" ]; then adapter="$RD/dpo/adapter"
  else adapter="$RD/sft/adapter"; fi
  say "  Round $r 완료 → 정책=$adapter"
done

# ── 최종 평가: rand200 BFS 탐색 (baseline vs 학습정책) ──
#   ★ test: GPU1·w6 (새 HW는 96GB·128코어라 w6도 자원 포화 없음 — search GPU util 0%, CPU 여유 100코어).
#     baseline도 같은 새 HW·w6로 재측정 → 서로 공정(같은 config). 각 실험 학습완료 후 전용 GPU에서
#     돌아 밀도 오염 없음. 사후에 성공 p90로 오염 검증(≈400s면 clean, 470s+면 오염→w 낮춰 재측정).
EVALW="${EVALW:-6}"
evalbfs(){ local ad="$1" name="$2" out="$3"
  local n=$(python3 -c "import json;print(len(json.load(open('$out/summary.json'))['results']))" 2>/dev/null || echo 0)
  [ "$n" -ge 200 ] && return   # 200개 완료만 skip; 부분은 run_all --out 이 resume
  rm -f "$out"/trace.jsonl.*
  BFS_ADAPTER="$ad" BFS_TRACE_OUT="$out/trace.jsonl" $TS python3 scripts/run_all.py --alias bfs-prover \
    --idx-file "$RAND" --timeout "$EVALT" --gpus 1 --workers "$EVALW" \
    --out "$out" --description "$name rand200 GPU1 w$EVALW" >> "$LOG" 2>&1
}
say "════ 최종 rand200 BFS 평가 (GPU1 w$EVALW, p90 검증) ════"
evalbfs "$INIT"    "baseline+BFS"  "all_results/rand200_bfs_baseline"
evalbfs "$adapter" "bfsprover-EI"  "all_results/rand200_bfs_ei"
python3 - <<PY | tee -a "$LOG"
import json
def sr(p):
    try:
        r=json.load(open(p))['results']; s=sum(1 for x in r if x['success'])
        su=sorted(x['elapsed_sec'] for x in r if x['success']); p90=su[int(0.9*len(su))] if su else 0
        flag="clean" if p90<430 else "⚠오염의심"
        return f"{s}/{len(r)} ({100*s/max(len(r),1):.1f}%)  p90={p90:.0f}s [{flag}]"
    except Exception as e: return f"?({e})"
print("  baseline+BFS  rand200:", sr("all_results/rand200_bfs_baseline/summary.json"))
print("  bfsprover-EI  rand200:", sr("all_results/rand200_bfs_ei/summary.json"))
PY
say "════ [BFS-Prover 완료] ════"
