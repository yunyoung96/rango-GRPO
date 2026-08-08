#!/bin/bash
# on-policy 에러 수집 — gold prefix 상태에서 **실제 1-step 예측 → Coq 실행 → 진짜 에러** 수집.
#
# ★ 왜 (합성 에러의 결함):
#   기존 ERROR_COND 는 gold 에서 분기 수를 역산해 에러 문장을 **직접 써넣었다**(Coq 미호출).
#     · [ATTEMPT] 가 가짜 — 모델이 낸 적 없는 tactic
#     · 에러가 gold 에서 나옴 = **정답이 프롬프트에 새어듦**
#     · 실패의 3%(분기수)만 커버. 이름없음 45%·문법 5.8%·타입불일치는 못 만듦
#
# ★ 실측 확인(정리 1개 시험 수집): INVALID 8 / VALID 2, coq_error 8건 전부 기록.
#   실제로 나온 에러들 — 합성이 못 만들던 종류가 대부분이다:
#     The variable even was not found in the current environment.
#     Syntax Error: Lexer: Undefined token
#     Syntax error: [input_fun] expected after 'fun' (in [binder_tactic]).
#     In environment / beta : radix / ...   (타입 불일치)
#
# 산출: data/grpo_rollouts/onpolicy_err.jsonl
#   각 step 에 {example, tactic, result, coq_error} → 학습 데이터로 바로 변환 가능
cd /app/coq-modeling || exit 1
set -u
NUM=${NUM:-400}                 # 정리 수
WPG=${WPG:-6}                   # GPU 당 워커
TIMEOUT=${TIMEOUT:-240}         # 정리당(수집이 목적이라 짧게 — 완결이 아니라 실패가 필요)
OUT=${OUT:-data/grpo_rollouts/onpolicy_err.jsonl}
LOG=all_log/collect_onpolicy_errors.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }

exec 9>/tmp/.rango_eval.lock
flock -n 9 || { echo "다른 평가/수집 실행 중 — 취소"; exit 1; }

say "===== on-policy 에러 수집 (정리 $NUM, ${TIMEOUT}s, g2×w${WPG}) ====="
say "  ※ 에러는 coq-lsp 가 실제로 낸 것만 기록(합성 아님)"

# train split 에서 eval 과 겹치지 않는 정리를 고른다
python3 - "$NUM" > /tmp/onpolicy_idx.txt <<'PY'
import sys, random
n = int(sys.argv[1])
random.seed(7)
# CoqStoq train 은 인덱스가 크다 — eval(rand200)과 분리되도록 오프셋 이후에서 뽑는다
idx = sorted(random.sample(range(1000, 9000), n))
print("\n".join(map(str, idx)))
PY
say "  대상 정리: $(wc -l < /tmp/onpolicy_idx.txt)개"

HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONPATH=src \
RECORD_ERROR=1 ROLLOUT_OUT="$OUT" \
AUGMENT_V2=1 RERANK_PREMISES=1 INJECT_TYPES=1 INJECT_DEFS=1 \
HARD_SEQ_LEN=4096 TYPES_TOKENS=300 DEFS_TOKENS=300 FUNC_DEFS_PATH=data/func_defs_v3.json \
  python3 scripts/run_all.py --alias grpo-rollout-cur --idx-file /tmp/onpolicy_idx.txt \
    --timeout "$TIMEOUT" --gpus 0,1 --workers "$WPG" \
    --out all_results/onpolicy_err_collect \
    --description "on-policy error collection (gold prefix, 1-step, real Coq)" >> "$LOG" 2>&1
ps -eo pid,cmd | grep "[t]actic_gen_server" | awk '{print $1}' | xargs -r kill -9 2>/dev/null
sleep 5

python3 - <<'PY' 2>&1 | tee -a "$LOG"
import json, collections, os
p = os.environ.get("OUT", "data/grpo_rollouts/onpolicy_err.jsonl")
if not os.path.exists(p):
    p = "data/grpo_rollouts/rollouts.jsonl"
c = collections.Counter(); n_err = 0; kinds = collections.Counter()
for line in open(p):
    try: g = json.loads(line)
    except Exception: continue
    for a in g.get("attempts", []):
        for st in a.get("steps", []):
            c[st.get("result", "?")] += 1
            e = st.get("coq_error")
            if e:
                n_err += 1
                if "was not found" in e: kinds["이름없음"] += 1
                elif "Syntax" in e: kinds["문법"] += 1
                elif "disjunctive pattern" in e: kinds["분기수"] += 1
                elif "Not an inductive" in e: kinds["inductive아님"] += 1
                elif "In environment" in e or "has type" in e: kinds["타입불일치"] += 1
                else: kinds["기타"] += 1
print(f"\n■ 수집 결과: {dict(c)}")
print(f"   진짜 coq_error {n_err:,}건")
for k, v in kinds.most_common():
    print(f"     {k:12s} {v:>6,} ({v/max(n_err,1)*100:.1f}%)")
PY
say "===== 수집 종료 ====="
