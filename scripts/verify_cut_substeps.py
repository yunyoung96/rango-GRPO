#!/usr/bin/env python3
"""계획 청크의 cut 을 **하위스텝 형태 그대로** Coq 에 넣어 검증한다.

## 왜 하위스텝 형태인가

학습이 실제로 쓰는 것은 중괄호 형태(`assert (P) as H. { exact L. } tac`)가 아니라
쪼갠 하위스텝을 이어 붙인 것이다.

    assert (P) as H_asrt0.
    exact L.
    tac'

중괄호가 없으면 focus 규칙이 달라질 수 있으므로 **실제로 쓸 형태**로 검증해야 한다.

## 왜 파일 배치를 안 쓰나

파일 전체를 컴파일하면 뒷부분 의존성 때문에 **원본조차** 73% 가 실패한다(실측).
검증된 `hunt_assert_errors` 는 파일을 **그 증명에서 잘라내고** 앞부분만 컴파일해서
원본 실패가 15% 에 그친다. 같은 방식을 쓴다.

    src[:증명시작] + (앞 증명 + cut + 뒤 증명)  →  컴파일

## 판정

    ok      원본도 되고 cut 도 된다
    fail    원본은 되는데 cut 이 깨진다      → hopeless 로 내려야 한다
    skip    원본부터 안 된다 / 소스 없음      → 우리 잘못이 아니다

사용: PYTHONPATH=src python3 scripts/verify_cut_substeps.py <plan.jsonl> <out.jsonl>
"""
import collections
import copy
import json
import logging
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, "src")
logging.disable(logging.CRITICAL)
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ["CUTS_PATH"] = ""

PLAN, OUT = sys.argv[1], sys.argv[2]
LIMIT = int(os.environ.get("VERIFY_LIMIT", "0"))     # 0 = 전부

import yaml  # noqa: E402
from coqpyt.coq.base_file import CoqFile  # noqa: E402
from data_management.dataset_file import DatasetFile  # noqa: E402
from data_management.sentence_db import SentenceDB  # noqa: E402
from tactic_gen.tactic_data import TacticDataConf, _split_substeps  # noqa: E402

REPOS = Path("/tmp/coq-dataset/repos")
cc = yaml.safe_load(open("all_log/ft_qwen3b_v9_conf.yaml"))
# ★ `LmDataset` 은 로드하지 않는다 — 여기서는 `DatasetFile` 만 쓰는데,
#   `LmDataset.from_conf` 는 200만개 shuffled index 를 읽느라 8분이 든다.
#   청크마다 부르므로 81번 = 10시간을 그냥 버리는 셈이었다.
conf = TacticDataConf.from_yaml(copy.deepcopy(cc["tactic_data"]))
sdb = SentenceDB.load(conf.sentence_db_loc)

plans = []
for ln in open(PLAN, errors="ignore"):
    try:
        d = json.loads(ln)
    except Exception:
        continue
    if d.get("kind") == "plan" and d.get("cut"):
        plans.append(d)
if LIMIT:
    plans = plans[:LIMIT]
print(f"■ cut {len(plans):,}개 검증 ({os.path.basename(PLAN)})", flush=True)


def find_decl(src, decl):
    key = re.sub(r"\\ ", r"\\s+", re.escape(decl.strip()))
    m = re.search(key, src)
    if m:
        return m.start()
    mm = re.match(r"\s*\w+\s+([A-Za-z_][\w']*)", decl)
    if mm:
        m2 = re.search(r"^[ \t]*\w+\s+" + re.escape(mm.group(1)) + r"\b", src, re.M)
        if m2:
            return m2.start()
    return -1


def compile_body(vf, ws, src, at, body):
    """`src[:at] + body` 를 원본 이름으로 써서 컴파일. 오류 목록을 돌려준다."""
    bak = vf.parent / (vf.name + f".sbak{os.getpid()}")
    try:
        vf.rename(bak)
        vf.write_text(src[:at] + body + "\n")
        cf = CoqFile(str(vf), timeout=300, workspace=ws)
        cf.run()
        errs = [getattr(d, "message", "") for d in cf.errors]
        cf.close()
        return errs
    except Exception as ex:
        return [f"예외: {ex}"]
    finally:
        vf.unlink(missing_ok=True)
        if bak.exists():
            bak.rename(vf)


st = collections.Counter()
fo = open(OUT, "w")
t0 = time.time()
_dp_cache = {}

for k, d in enumerate(plans):
    sid = d["sid"]
    path, _, si = sid.rpartition(":")
    fpath, _, pi = path.rpartition(":")
    pi, si = int(pi), int(si)
    mm = re.match(r"repos/([^/]+)/(.+)$", fpath)
    if not mm:
        st["경로 파싱 실패"] += 1
        continue
    vf = REPOS / mm.group(1) / mm.group(2)
    if not vf.exists():
        fo.write(json.dumps({"sid": sid, "coq": "skip", "why": "소스 없음"}) + "\n")
        st["소스 없음"] += 1
        continue
    ws = str((REPOS / mm.group(1)).resolve())
    dpname = fpath.replace("repos/", "").replace("/", "-")
    dp = _dp_cache.get(dpname)
    if dp is None:
        try:
            dp = DatasetFile.load(conf.data_loc / "data_points" / dpname, sdb)
        except Exception:
            st["DatasetFile 실패"] += 1
            continue
        _dp_cache.clear()
        _dp_cache[dpname] = dp
    try:
        proof = dp.proofs[pi]
        step = proof.steps[si]
    except Exception:
        st["스텝 없음"] += 1
        continue
    try:
        src = vf.read_text(errors="ignore")
    except Exception:
        st["읽기 실패"] += 1
        continue
    decl = proof.theorem.term.text.strip().split("\n")[0].strip()
    at = find_decl(src, decl)
    if at < 0:
        fo.write(json.dumps({"sid": sid, "coq": "skip", "why": "선언문 못 찾음"}) + "\n")
        st["선언문 못 찾음"] += 1
        continue
    script = proof.proof_prefix_to_string(step)
    tac = step.step.text or ""
    suffix = "".join(s2.step.text or "" for s2 in proof.steps[si + 1:])

    # ① 원본이 되나
    if compile_body(vf, ws, src, at, script + tac + suffix):
        fo.write(json.dumps({"sid": sid, "coq": "skip", "why": "원본도 컴파일 실패"}) + "\n")
        st["원본 실패(스킵)"] += 1
        continue
    # ② cut 을 **하위스텝 형태로** 이어 붙여 넣는다 (실제 학습이 쓰는 형태)
    subs = _split_substeps(d["cut"])
    body = script + "\n" + "\n".join(t for t, _, _, _ in subs) + "\n" + suffix
    errs = compile_body(vf, ws, src, at, body)
    if errs:
        fo.write(json.dumps({"sid": sid, "coq": "fail",
                             "err": " ".join(errs)[:200]}) + "\n")
        st["실패"] += 1
    else:
        fo.write(json.dumps({"sid": sid, "coq": "ok", "nsub": len(subs)}) + "\n")
        st["통과"] += 1
    if (k + 1) % 25 == 0:
        fo.flush()
        el = time.time() - t0
        print(f"   {k+1}/{len(plans)} · 통과 {st['통과']} 실패 {st['실패']} "
              f"스킵 {st['원본 실패(스킵)']+st['소스 없음']} · {el:.0f}s", flush=True)

fo.close()
print(f"\n■ 결과 ({time.time()-t0:.0f}s)")
for kk, v in st.most_common():
    print(f"   {kk:24s} {v:7,}")
d_ = st["통과"] + st["실패"]
if d_:
    print(f"\n   Coq 통과율 {st['통과']/d_*100:.1f}%  ({st['통과']:,}/{d_:,})")
