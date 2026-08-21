#!/bin/bash
# 밤새 도는 체인 — 계획 완성 → 병합 → 검증 4종 → **스모크 학습**.
#
# ★ 각 단계가 실패하면 **거기서 멈춘다.** 실패를 안고 다음으로 가면 무엇이 원인인지
#   아침에 알 수 없다. 로그 한 곳(all_log/overnight.log)에 다 남긴다.
set -u
cd /app/coq-modeling || exit 1
L=all_log/overnight.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$L"; }
fail(){ say "★★ 중단: $*"; exit 1; }

say "===== 밤샘 체인 시작 ====="

# ① 계획 생성 완료 대기 (TRAIN 81 + VAL 3)
while [ "$(ls data/cut_plan_chunks_train/p_*.jsonl 2>/dev/null | wc -l)" -lt 81 ]; do sleep 120; done
say "TRAIN 계획 81/81"
while [ "$(ls data/cut_plan_chunks_val/p_*.jsonl 2>/dev/null | wc -l)" -lt 3 ]; do sleep 120; done
say "VAL 계획 완료"

# ② 병합 — TRAIN+VAL 을 **한 파일**로 (cut_lookup 은 CUTS_PATH 하나를 읽는 싱글턴)
: > data/cut_plans_all.jsonl.new
for f in data/cut_plan_chunks_train/p_*.jsonl data/cut_plan_chunks_val/p_*.jsonl; do
  [ -s "$f" ] && cat "$f" >> data/cut_plans_all.jsonl.new
done
mv -f data/cut_plans_all.jsonl.new data/cut_plans_all.jsonl
say "병합 완료 → data/cut_plans_all.jsonl ($(du -h data/cut_plans_all.jsonl | cut -f1))"

export CUTS=data/cut_plans_all.jsonl
source all_log/v9_env.sh
export CUTS_PATH="$CUTS"

# ③ 검증 4종 — 하나라도 실패하면 학습을 시작하지 않는다
say "── 검증 ①  전 인덱스 질의 (cut/hopeless/무기록 + cut 형태)"
PYTHONPATH=src python3 -u scripts/verify_cut_all.py train >> "$L" 2>&1 || fail "전 인덱스 검증"
say "── 검증 ②  학습 시점 결정 규칙 (1)(2)(3)"
PYTHONPATH=src python3 -u scripts/verify_cut_wiring.py >> "$L" 2>&1 || fail "배선 검증"
say "── 검증 ③  하위스텝 분해 (G2~G8)"
PYTHONPATH=src python3 -u scripts/verify_substep.py >> "$L" 2>&1 || fail "하위스텝 검증"
say "── 검증 ④  ★ 랜덤·큰 인덱스 400건 (학습은 RandomSampler 로 전 구간을 돈다)"
PYTHONPATH=src python3 -u scripts/preflight_random.py 400 >> "$L" 2>&1 || fail "랜덤 인덱스 사전점검"
say "검증 4종 전부 통과"

# ④ 스모크 학습 — **동작 확인용**. 본학습은 다른 서버에서 한다.
#    max_steps 를 작게 잡아 파이프라인이 실제로 도는지만 본다.
say "── 스모크 학습 (동작 확인용 · max_steps=200)"
python3 - <<'PYX'
import yaml, copy
c = yaml.safe_load(open('all_log/ft_qwen3b_v9_conf.yaml'))
c['max_steps'] = 200
c['save_steps'] = 100000          # 체크포인트 안 남긴다
c['eval_steps'] = 100
c['logging_steps'] = 10
c['num_eval_examples'] = 50
c['output_dir'] = 'models/rango-qwen3b-v9-smoke'
yaml.safe_dump(c, open('all_log/ft_qwen3b_v9_smoke.yaml', 'w'), allow_unicode=True)
print('스모크 설정 → all_log/ft_qwen3b_v9_smoke.yaml')
PYX
CONF=all_log/ft_qwen3b_v9_smoke.yaml
NPROC=$(python3 -c "import torch;print(torch.cuda.device_count() or 1)" 2>/dev/null || echo 1)
say "GPU $NPROC개로 스모크 학습 시작"
# ★ 실행 방식은 run_qwen3b_v9.sh 와 **같게** 한다 (torch.distributed.run · 랜덤 포트).
#   방식이 다르면 "스모크는 됐는데 본학습은 안 되는" 상황이 생긴다.
PYTHONPATH=src timeout 7200 python3 -m torch.distributed.run \
    --nproc_per_node="$NPROC" --master_port=$((29500 + RANDOM % 400)) \
    src/tactic_gen/train_v5.py "$CONF" >> all_log/smoke_train.log 2>&1
rc=$?
if [ $rc -eq 0 ]; then say "✓ 스모크 학습 완료 — 파이프라인 정상"
else say "★ 스모크 학습 종료코드 $rc → all_log/smoke_train.log 확인"; fi
tail -30 all_log/smoke_train.log >> "$L"
say "===== 밤샘 체인 종료 ====="
