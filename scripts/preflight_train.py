#!/usr/bin/env python3
"""★ 학습 전 안전 점검 — 돌리기 전에 잡아야 할 것들.

20,000 step 을 돌리고 나서 데이터가 잘못됐다는 걸 알면 며칠을 버린다. 그 전에 잡는다.

## 검사 항목

  ① cut 파일 무결성   깨진 줄 · 중복 sid · 키 형식 · 필수 필드
  ② 키 매칭률         cut 의 sid 가 실제 데이터셋의 예제와 맞물리는가
                      (키 형식이 어긋나면 조회가 **조용히 0% 적중**한다 — 실제로 당했다)
  ③ 메모리            워커마다 cut 사전을 복사한다. 8워커면 8배다
  ④ 로딩 시간         워커 시작마다 jsonl 파싱 — 느리면 학습 시작이 지연된다
  ⑤ cut 내용 위생     assert 형태 · 이름 규칙 · 길이 이상치
  ⑥ hopeless 비율     정규화를 끄는 스텝이 얼마나 되는가

사용: python3 scripts/preflight_train.py [cuts.jsonl] [샘플수]
"""
import collections
import copy
import json
import os
import re
import resource
import sys
import time

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.insert(0, "src")
import logging  # noqa: E402

logging.disable(logging.CRITICAL)

CUTS = sys.argv[1] if len(sys.argv) > 1 else "data/cut_plans_all.jsonl"
NS = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
_KEY = re.compile(r"^.+:\d+:\d+$")

print(f"■ 학습 전 안전 점검 — {CUTS}\n")

# ── ① 무결성 ────────────────────────────────────────────────────────────
if not os.path.exists(CUTS):
    print(f"  ★ 파일이 없다: {CUTS}")
    sys.exit(2)
rss0 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
t0 = time.time()
steps, stmts = {}, {}
bad = collections.Counter()
dup = 0
nline = 0
lens = []
for line in open(CUTS):
    nline += 1
    try:
        d = json.loads(line)
    except Exception:
        bad["JSON 파싱 실패"] += 1
        continue
    k = d.get("kind")
    if k == "step":
        sid = d.get("sid")
        if not sid:
            bad["sid 없음"] += 1
            continue
        if not _KEY.match(sid):
            bad["★ 키 형식 이상(file:proof:step 이어야 함)"] += 1
        if sid in steps:
            dup += 1
        steps[sid] = d
        if d.get("cut"):
            lens.append(len(d["cut"]))
    elif k == "stmt":
        if not d.get("name") or not d.get("ty"):
            bad["stmt 필드 누락"] += 1
            continue
        stmts[d["name"]] = d["ty"]
    else:
        bad[f"알 수 없는 kind={k}"] += 1
t_load = time.time() - t0
rss1 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

n_cut = sum(1 for d in steps.values() if d.get("cut"))
n_hope = sum(1 for d in steps.values() if d.get("hopeless"))
print(f"① 무결성")
print(f"   줄 {nline:,} · step {len(steps):,} · stmt {len(stmts):,}")
print(f"   cut 있음 {n_cut:,} · hopeless {n_hope:,} · 중복 sid {dup}")
for k, v in bad.most_common():
    print(f"   ★ {k}: {v}")
if not bad and not dup:
    print(f"   ✓ 문제 없음")

# ── ③④ 메모리·시간 ──────────────────────────────────────────────────────
mb = (rss1 - rss0) / 1024
print(f"\n③④ 로딩  {t_load:.1f}초 · 메모리 +{mb:.0f} MB")
nw = 8
print(f"   dataloader 워커 {nw}개면 약 {mb*nw:.0f} MB (워커마다 복사한다)")
if mb * nw > 8000:
    print(f"   ★ 8 GB 초과 — 워커 수를 줄이거나 공유 저장소를 쓸 것")
else:
    print(f"   ✓ 감당 가능")

# ── ⑤ 내용 위생 ─────────────────────────────────────────────────────────
print(f"\n⑤ cut 내용")
bad2 = collections.Counter()
samp = []
for sid, d in steps.items():
    c = d.get("cut")
    if not c:
        continue
    if not re.search(r"e?assert\s*\(.+\)\s*as\s+\w+\.", c, re.S):
        bad2["assert 형태 아님"] += 1
        if len(samp) < 3:
            samp.append(c[:80])
    if not re.search(r"as\s+H_asrt\w*\d+", c):
        bad2["★ 이름 규칙 위반(H_asrt<n> 아님)"] += 1
    if "{" not in c or "}" not in c:
        bad2["중괄호 없음"] += 1
    # ★ evar 는 **assert 의 타입 부분**에만 있으면 문제다. 후속 tactic 의
    #   `rewrite ?H` 는 evar 가 아니라 **0회 이상 반복** 플래그다(실측 26건 전부 이것).
    #   문자열 전체를 보면 정상 tactic 을 결함으로 잡는다.
    _ty = re.match(r"^e?assert\s*\((.*?)\)\s*as\s+H_asrt", c, re.S)
    if _ty and re.search(r"\?[A-Za-z_]", _ty.group(1)):
        bad2["★ evar(?x) 가 남아 있음"] += 1
if lens:
    lens.sort()
    print(f"   길이  평균 {sum(lens)/len(lens):.0f}자 · 중앙 {lens[len(lens)//2]}자 "
          f"· 최대 {lens[-1]}자")
for k, v in bad2.most_common():
    print(f"   ★ {k}: {v}")
if not bad2:
    print(f"   ✓ 형태·이름 규칙 모두 정상")
for s_ in samp:
    print(f"     예: {s_}")

# ── ② 키 매칭률 (가장 중요) ─────────────────────────────────────────────
print(f"\n② 키 매칭 — 실제 데이터셋 예제와 맞물리는가")
import yaml  # noqa: E402
from data_management.splits import Split  # noqa: E402
from tactic_gen.tactic_data import TacticDataConf, LmDataset  # noqa: E402
cc = yaml.safe_load(open("all_log/ft_qwen3b_v8_conf.yaml"))
conf = TacticDataConf.from_yaml(copy.deepcopy(cc["tactic_data"]))
ds = LmDataset.from_conf(conf, Split.TRAIN, 10 ** 9)
hit = miss = 0
for i in range(NS):
    try:
        e = ds.raw_example(i)
    except Exception:
        continue
    k = f"{e.file_name}:{e.proof_idx}:{e.step_idx}"
    if k in steps:
        hit += 1
    else:
        miss += 1
print(f"   샘플 {hit+miss:,} 중 cut 파일에 있는 것 {hit:,} ({hit/max(hit+miss,1)*100:.1f}%)")
if hit == 0:
    print(f"   ★★ 적중 0 — 키 형식이 어긋났다. 학습이 조용히 cut 없이 돈다")
    print(f"      cut 파일 키 예: {next(iter(steps), '?')}")
    print(f"      데이터셋 키 예: {k}")
else:
    print(f"   ✓ 키가 맞물린다")

print(f"\n⑥ hopeless(정규화 끄는 스텝)  {n_hope:,} / step {len(steps):,} "
      f"({n_hope/max(len(steps),1)*100:.1f}%)")
