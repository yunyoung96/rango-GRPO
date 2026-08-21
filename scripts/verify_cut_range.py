#!/usr/bin/env python3
"""cut 파일이 학습이 도달하는 **모든 인덱스**를 덮는지 증명한다. 표본이 아니라 전수.

## 왜 이 스크립트가 필요한가

cut 파일은 **범위 제한 산출물**이다 — `build_cuts.py N` 은 인덱스 `[START, START+N)`
만 훑는다. 그런데 조회 쪽은 범위 밖 스텝에 **조용히 `None`/`False`** 를 준다:

    cut_for(sid)     → None    (cut 치환 안 됨)
    is_hopeless(sid) → False   (CUT_DROP_HOPELESS 도 함께 죽음)

오류도 경고도 없다. 그래서 파일럿 규모(60,000) 산출물이 본번(640,000 소비)에
들어간 채로 학습이 4시간 넘게 돌았고, step 1,875 이후 cut 이 전혀 작동하지 않았다.

## 필요 범위 계산이 순환이라는 점

    도달 인덱스 = 소비 예제 수 + (건너뛴 hopeless 수)
    건너뛴 수   = 도달 범위 안의 hopeless 수      ← 서로를 참조한다

그래서 **실제로 시뮬레이션**한다: 인덱스를 0부터 돌면서 hopeless 면 건너뛰고,
소비량이 목표에 닿을 때까지 진행해 **도달 인덱스를 구한다.**
그 값이 파일의 `scan_end` 이하여야 한다.

사용: PYTHONPATH=src python3 scripts/verify_cut_range.py [conf] [cuts]
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, "src")
import logging

logging.disable(logging.CRITICAL)
os.environ.setdefault("HF_HUB_OFFLINE", "1")

import yaml  # noqa: E402
from data_management.splits import Split  # noqa: E402
from tactic_gen.tactic_data import ShuffledIndex  # noqa: E402

CONF = sys.argv[1] if len(sys.argv) > 1 else "all_log/ft_qwen3b_v9_conf.yaml"
CUTS = sys.argv[2] if len(sys.argv) > 2 else os.environ.get(
    "CUTS_PATH", "data/cuts_train.jsonl")

cc = yaml.safe_load(open(CONF))
si = ShuffledIndex.load(Path(cc["tactic_data"]["shuffled_index_loc"]))
TOTAL = si.split_length(Split.TRAIN)
PER = cc["per_device_train_batch_size"] * cc["gradient_accumulation_steps"] * 2
NEED = cc["max_steps"] * PER

# ── cut 파일 적재 ──────────────────────────────────────────────────────────
hope, cov, scan_end = set(), set(), 0
n_cut = 0
for line in open(CUTS):
    d = json.loads(line)
    k = d.get("kind")
    if k == "meta":
        scan_end = max(scan_end, int(d.get("scan_end", 0)))
        continue
    if k != "step":
        continue
    a, b, c = d["sid"].rsplit(":", 2)
    key = (a.split("repos/", 1)[-1].replace("/", "-"), int(b), int(c))
    cov.add(key)
    if d.get("cut"):
        n_cut += 1
    else:
        hope.add(key)

print(f"■ cut 범위 검증")
print(f"   conf              {CONF}")
print(f"   cuts              {CUTS}")
print(f"   TRAIN 전체         {TOTAL:,}")
print(f"   step 당 예제       {PER}  (batch {cc['per_device_train_batch_size']} "
      f"× accum {cc['gradient_accumulation_steps']} × GPU 2)")
print(f"   소비 예제          {NEED:,}  ({cc['max_steps']:,} step)")
print(f"   기록 스텝          {len(cov):,}  (cut {n_cut:,} · hopeless {len(hope):,})")

fail = []
if scan_end == 0:
    print("\n   ★ 파일에 스캔 범위(meta)가 없다 — 커버리지를 보장할 수 없다.")
    print("     build_cuts.py 를 최신 버전으로 다시 돌려라(meta 레코드를 쓴다).")
    fail.append("meta 없음")
else:
    print(f"   파일 스캔 범위      [0, {scan_end:,})")

# ── 도달 인덱스 시뮬레이션 (CUT_DROP_HOPELESS 반영) ─────────────────────────
drop = os.environ.get("CUT_DROP_HOPELESS", "1") == "1"
i = consumed = skips = 0
while consumed < NEED and i < TOTAL:
    s = si.get_idx(Split.TRAIN, i)
    if drop and (s.file, s.proof_idx, s.step_idx) in hope:
        skips += 1
        i += 1
        continue
    consumed += 1
    i += 1
reach = i
print(f"\n   CUT_DROP_HOPELESS  {'켬' if drop else '끔'}")
print(f"   건너뛴 hopeless     {skips:,}")
print(f"   ★ 도달 인덱스        {reach:,}   (소비 {NEED:,} + 건너뛰기 {skips:,})")

if scan_end and reach > scan_end:
    print(f"\n   ★★ 빈틈: 인덱스 {scan_end:,} ~ {reach:,} 에 cut 이 없다 "
          f"({(reach-scan_end)/reach*100:.1f}%)")
    print(f"      그 구간에서는 cut 치환도 CUT_DROP_HOPELESS 도 작동하지 않는다.")
    print(f"      메우려면:  python3 scripts/build_cuts.py {reach-scan_end+20000} "
          f"train <out> {scan_end}")
    fail.append(f"범위 부족 {scan_end:,} < {reach:,}")
elif scan_end:
    print(f"   ✓ 스캔 범위가 도달 인덱스를 덮는다 "
          f"(여유 {scan_end-reach:,})")

# ── 전수 확인: 도달 범위 안에서 기록이 끊기는 지점이 있는가 ────────────────
#   (표본이 아니라 전 구간을 1,000 단위 창으로 훑어 **0% 창**을 찾는다)
print(f"\n   ■ 전수 스캔 — 적중률 0% 인 구간이 있는가 (창 2,000)")
W = 2000
zero = []
rates = []
for s in range(0, min(reach, TOTAL), W):
    h = t = 0
    for j in range(s, min(s + W, TOTAL)):
        x = si.get_idx(Split.TRAIN, j)
        t += 1
        h += (x.file, x.proof_idx, x.step_idx) in cov
    r = h / max(t, 1)
    rates.append(r)
    if r == 0:
        zero.append(s)
if rates:
    rs = sorted(rates)
    print(f"      창 {len(rates):,}개 · 적중률 중앙 {rs[len(rs)//2]*100:.1f}% "
          f"· 최소 {rs[0]*100:.1f}% · 최대 {rs[-1]*100:.1f}%")
if zero:
    print(f"      ★★ 적중률 0% 인 창 {len(zero)}개 — 시작 인덱스: {zero[:8]}")
    fail.append(f"0% 구간 {len(zero)}개")
else:
    print(f"      ✓ 0% 인 구간 없음")

print("\n" + "=" * 60)
if fail:
    print("★ 검증 실패 — 학습을 시작하면 안 된다")
    for f in fail:
        print(f"   · {f}")
    sys.exit(1)
print("✓ cut 범위 검증 통과")
