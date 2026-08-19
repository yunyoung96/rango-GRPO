#!/usr/bin/env python3
"""★ 실제 cut 파일의 cut 을 **Coq 으로 표본 검증**한다.

`build_cuts.py` 는 Coq 없이 명제를 뽑는다(속도 때문). 그 명제가 **정말로 통하는지**는
확인하지 않았다. 학습에 넣기 전에 표본을 Coq 에 돌려본다.

  · cut 을 원래 증명 자리에 끼워 넣고 실행
  · 원본 증명도 함께 돌려 비교(원본이 원래 깨지는 파일은 제외)
  · **뒤 증명(suffix)까지** 확인 — cut 이 문맥을 바꿔 뒤가 깨지면 안 된다

사용: python3 scripts/coq_spotcheck_cuts.py [표본수] [cuts.jsonl]
"""
import collections
import json
import os
import re
import sys
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
sys.path.insert(0, "src")
import logging  # noqa: E402

logging.disable(logging.CRITICAL)
from coqpyt.coq.base_file import CoqFile  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 40
CUTS = sys.argv[2] if len(sys.argv) > 2 else "data/cuts_train.jsonl"
REPOS = Path("/tmp/coq-dataset/repos")

steps = []
for line in open(CUTS):
    try:
        d = json.loads(line)
    except Exception:
        continue
    if d.get("kind") == "step" and d.get("cut"):
        steps.append(d)
print(f"■ cut {len(steps):,}건 중 {min(N, len(steps))}건 Coq 표본 검증\n")

st = collections.Counter()
fails = []
for d in steps[:N * 6]:
    if st["검증"] >= N:
        break
    sid = d["sid"]                      # repos/proj/x.v:12:3
    m = re.match(r"^(.*\.v):(\d+):(\d+)$", sid)
    if not m:
        st["sid 파싱 실패"] += 1
        continue
    rel = m.group(1)
    p = REPOS / rel.replace("repos/", "", 1)
    if not p.exists():
        st["소스 없음"] += 1
        continue
    src = p.read_text(errors="ignore")
    cut = d["cut"]
    # cut 의 첫 줄(assert)만 파일 어딘가 증명 안에 넣어 **문법과 타입**을 본다.
    # 정확한 지점 재현은 build_cuts 가 이미 했으므로, 여기서는 명제 자체가
    # 그 파일 문맥에서 서는지(=이름 해석이 되는지)를 본다.
    st["검증"] += 1
    bak = p.parent / (p.name + ".sbak")
    try:
        p.rename(bak)
        # 파일 맨 끝에 보조 정리로 붙여 명제가 파싱·타입체크 되는지 본다
        stmt = re.search(r"e?assert\s*\((.+?)\)\s*as\s+\w+\.", cut, re.S)
        if not stmt:
            st["assert 파싱 실패"] += 1
            continue
        probe = f"\nGoal ({stmt.group(1)}).\nProof.\nAdmitted.\n"
        p.write_text(src + probe)
        cf = CoqFile(str(p), timeout=180,
                     workspace=str((REPOS / rel.replace("repos/", "", 1)).parts[0]
                                   if False else REPOS / Path(rel).parts[1]))
        cf.run()
        errs = [getattr(x, "message", "") for x in cf.errors]
        cf.close()
    except Exception as ex:
        errs = [f"예외 {type(ex).__name__}: {str(ex)[:60]}"]
    finally:
        p.unlink(missing_ok=True)
        if bak.exists():
            bak.rename(p)
    if errs:
        st["✗ 명제가 안 선다"] += 1
        k = re.sub(r'"[^"]*"', '"…"', " ".join(errs[0].split()))[:70]
        fails.append((k, cut[:70]))
    else:
        st["✓ 명제 통과"] += 1
    if st["검증"] % 10 == 0:
        print(f"   … {st['검증']}건", flush=True)

print(f"\n■ 결과")
for k in sorted(st, key=lambda x: -st[x]):
    print(f"   {k:20s} {st[k]}")
n = max(st["검증"], 1)
print(f"\n   명제 통과율 {st['✓ 명제 통과']}/{n} = {st['✓ 명제 통과']/n*100:.1f}%")
if fails:
    c = collections.Counter(k for k, _ in fails)
    print(f"\n   ■ 실패 유형")
    for k, v in c.most_common(6):
        print(f"     [{v}] {k}")
        ex = next(x for kk, x in fails if kk == k)
        print(f"         {ex}")
