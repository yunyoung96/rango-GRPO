#!/usr/bin/env python3
"""cut 을 **실제 Coq 에 넣어** 컴파일되는지 검증한다 — 파일 단위 배치로.

## 왜 배치인가

스텝마다 따로 검증하면 **같은 파일의 앞부분을 cut 개수만큼 반복 컴파일**한다.
파일당 cut 이 평균 6개 정도이므로 그만큼 낭비다. 파일 하나를 열어 그 안의 cut 을
**한꺼번에** 치환하고 한 번만 컴파일하면 된다.

    단순:  290,000 cut × 6s = 483시간 (12병렬 40시간)
    배치:   45,000 파일 × 6s =  75시간 (12병렬  6시간)

## 어떻게 판정하나

  ① 파일 전체를 cut 치환본으로 만들어 컴파일 → 오류 0 이면 **그 파일의 cut 전부 통과**
  ② 오류가 있으면 **이분 탐색**으로 범인을 좁힌다(cut 을 절반씩만 적용해 재컴파일).
     오류 위치(line)로 바로 찍을 수도 있지만 Coq 의 위치 보고가 늘 정확하진 않다.
  ③ 원본도 컴파일 실패하면 그 파일은 **판정 불가**로 뺀다 — 우리 잘못이 아니다.

## 결과

    {"sid": …, "coq": "ok"}                       그대로 써도 된다
    {"sid": …, "coq": "fail", "err": "…"}         hopeless 로 내려야 한다
    {"sid": …, "coq": "skip", "why": "소스 없음"}   판정 불가 (레포 미다운 등)

사용: PYTHONPATH=src python3 scripts/verify_cuts_coq.py <plan.jsonl> <out.jsonl> [파일수] [시작]
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

PLAN = sys.argv[1]
OUT = sys.argv[2]
NFILE = int(sys.argv[3]) if len(sys.argv) > 3 else 10 ** 9
FSTART = int(sys.argv[4]) if len(sys.argv) > 4 else 0

import yaml  # noqa: E402
from coqpyt.coq.base_file import CoqFile  # noqa: E402
from data_management.splits import Split  # noqa: E402
from data_management.dataset_file import DatasetFile  # noqa: E402
from data_management.sentence_db import SentenceDB  # noqa: E402
from tactic_gen.tactic_data import TacticDataConf, LmDataset  # noqa: E402

REPOS = Path("/tmp/coq-dataset/repos")
cc = yaml.safe_load(open("all_log/ft_qwen3b_v9_conf.yaml"))
conf = TacticDataConf.from_yaml(copy.deepcopy(cc["tactic_data"]))
ds = LmDataset.from_conf(conf, Split.TRAIN, None)
sdb = SentenceDB.load(conf.sentence_db_loc)

# ── 계획을 읽고 sid → (tac, cut) ─────────────────────────────────────────
plans = {}
for path in ([PLAN] if os.path.isfile(PLAN) else
             [os.path.join(PLAN, f) for f in sorted(os.listdir(PLAN))
              if f.endswith(".jsonl")]):
    for ln in open(path, errors="ignore"):
        try:
            d = json.loads(ln)
        except Exception:
            continue
        # 새 계획(`plan`)과 옛 cut 파일(`step`)을 **둘 다** 받는다 —
        # 검증기는 형식이 아니라 `cut` 문자열을 본다.
        if d.get("kind") in ("plan", "step") and d.get("cut"):
            plans[d["sid"]] = (d.get("tac", ""), d["cut"])
print(f"■ cut {len(plans):,}개를 Coq 으로 검증", flush=True)

# ── sid → 그 증명의 **선언문** (치환 위치를 좁히는 데 쓴다) ────────────────
#   `Theorem foo : …` 한 줄. DatasetFile 을 파일당 한 번만 읽는다(캐시된다).
decls = {}
prefixes = {}          # sid → 그 스텝 **앞까지**의 증명 텍스트 (위치 특정용)
_dpname = {}
for _sid in plans:
    _path, _, _st2 = _sid.rpartition(":")
    _p2, _, _pi = _path.rpartition(":")
    _dpname.setdefault(_p2, []).append((_sid, int(_pi)))
print(f"   증명 선언문 수집 중… ({len(_dpname):,} 파일)", flush=True)
_dpfiles = {}
for _f in os.listdir(conf.data_loc / "data_points"):
    _dpfiles[_f] = True
for _p2, _lst in _dpname.items():
    _key = _p2.replace("repos/", "").replace("/", "-")
    if _key not in _dpfiles:
        continue
    try:
        _dp = DatasetFile.load(conf.data_loc / "data_points" / _key, sdb)
    except Exception:
        continue
    for _sid, _pi in _lst:
        try:
            _pr = _dp.proofs[_pi]
            decls[_sid] = _pr.theorem.term.text.strip().split("\n")[0].strip()
            _si = int(_sid.rpartition(":")[2])
            prefixes[_sid] = _pr.proof_prefix_to_string(_pr.steps[_si])
        except Exception:
            pass
print(f"   선언문 {len(decls):,}/{len(plans):,}개 확보", flush=True)

# ── sid → 소스 파일 · 그 안에서의 위치 ───────────────────────────────────
#    sid 는 `repos/<proj>/<rel>:<proof>:<step>` 이다.
byfile = collections.defaultdict(list)
for sid in plans:
    path, _, rest = sid.rpartition(":")
    path2, _, pidx = path.rpartition(":")
    byfile[path2].append(sid)
files = sorted(byfile)[FSTART:FSTART + NFILE]
print(f"   파일 {len(files):,}개 (전체 {len(byfile):,})", flush=True)

st = collections.Counter()
fo = open(OUT, "w")
t0 = time.time()


def compile_ok(vf: Path, ws: str, text: str):
    """텍스트를 원본 이름으로 써서 컴파일. 오류 메시지 목록을 돌려준다."""
    bak = vf.parent / (vf.name + ".vbak")
    try:
        vf.rename(bak)
        vf.write_text(text)
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


def norm(x):
    return re.sub(r"\s+", " ", x or "").strip()


def find_decl(src: str, decl: str) -> int:
    """`hunt_assert_errors.find_decl` 과 같은 규칙 — 공백 차이를 흡수한다."""
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


def proof_end(src: str, at: int) -> int:
    """증명 끝(Qed/Defined/Admitted) 다음 위치."""
    end = -1
    for kw in ("\nQed.", "\nDefined.", "\nAdmitted.", " Qed.", " Defined."):
        i = src.find(kw, at)
        if i >= 0 and (end < 0 or i < end):
            end = i + len(kw)
    return end


def locate_step(src: str, at: int, end: int, prefix: str, tac: str) -> int:
    """증명 [at, end) 안에서 **그 스텝**의 절대 위치.

    ★ `src.find(tac, at)` 로는 안 된다 — 같은 증명 안에 `auto.` 가 여러 번 나오면
      전부 같은 자리로 잡힌다(실측: 겹침 199건). `proof_prefix_to_string` 이 주는
      **그 스텝 앞까지의 텍스트**를 정규화 길이로 되짚어 위치를 정한다.
    """
    body = src[at:end]
    target = len(norm(prefix))
    if target <= 0:
        k = body.find(tac)
        return at + k if k >= 0 else -1
    acc = []
    for k, ch in enumerate(body):
        acc.append(ch)
        if len(norm("".join(acc))) >= target:
            break
    else:
        return -1
    # 그 지점 이후 **가장 가까운** tac 을 집는다 (공백 차이 흡수)
    j = body.find(tac, k)
    if j < 0:
        j = body.find(tac.strip(), k)
    if j < 0 or j - k > 400:
        return -1
    return at + j


for fno, fpath in enumerate(files):
    sids = byfile[fpath]
    mm = re.match(r"repos/([^/]+)/(.+)$", fpath)
    if not mm:
        st["경로 파싱 실패"] += len(sids)
        continue
    vf = REPOS / mm.group(1) / mm.group(2)
    if not vf.exists():
        for s_ in sids:
            fo.write(json.dumps({"sid": s_, "coq": "skip", "why": "소스 없음"}) + "\n")
        st["소스 없음"] += len(sids)
        continue
    ws = str((REPOS / mm.group(1)).resolve())
    try:
        src = vf.read_text(errors="ignore")
    except Exception:
        st["읽기 실패"] += len(sids)
        continue

    # ── 각 cut 의 정확한 치환 구간 ──────────────────────────────────────
    subs = []
    for s_ in sids:
        tac, cut = plans[s_]
        decl = decls.get(s_, "")
        if not norm(tac) or not decl:
            fo.write(json.dumps({"sid": s_, "coq": "skip", "why": "선언문 없음"}) + "\n")
            st["선언문 없음"] += 1
            continue
        at = find_decl(src, decl)
        if at < 0:
            fo.write(json.dumps({"sid": s_, "coq": "skip", "why": "선언문 못 찾음"}) + "\n")
            st["선언문 못 찾음"] += 1
            continue
        end = proof_end(src, at)
        if end <= at:
            fo.write(json.dumps({"sid": s_, "coq": "skip", "why": "증명 끝 못 찾음"}) + "\n")
            st["증명 끝 못 찾음"] += 1
            continue
        pos = locate_step(src, at, end, prefixes.get(s_, ""), tac)
        if pos < 0:
            fo.write(json.dumps({"sid": s_, "coq": "skip", "why": "스텝 위치 못 찾음"}) + "\n")
            st["스텝 위치 못 찾음"] += 1
            continue
        subs.append((pos, pos + len(tac), s_, cut, end))
    if not subs:
        continue
    subs.sort()
    # 겹치면 뒤엣것을 뺀다
    keep, last = [], -1
    for a, b, s_, cut, end in subs:
        if a < last:
            fo.write(json.dumps({"sid": s_, "coq": "skip", "why": "치환 구간 겹침"}) + "\n")
            st["치환 구간 겹침"] += 1
            continue
        keep.append((a, b, s_, cut, end))
        last = b
    subs = keep
    if not subs:
        continue

    # ★ **잘라낸다.** 파일 전체를 컴파일하면 뒷부분 의존성 때문에 원본조차 실패한다
    #   (실측 41%). `hunt_assert_errors` 가 잘 도는 이유가 이 잘라내기다.
    #   마지막 cut 이 든 증명의 끝에서 자르면, 그 앞의 cut 을 **한 번에** 검증할 수 있다.
    TRUNC = max(x[4] for x in subs)
    head = src[:TRUNC]

    def apply(sel):
        out, last2 = [], 0
        for a, b, s2, cut, _ in subs:
            if s2 not in sel:
                continue
            out.append(head[last2:a])
            out.append(cut)
            last2 = b
        out.append(head[last2:])
        return "".join(out)

    if compile_ok(vf, ws, head):
        for _, _, s_, _, _ in subs:
            fo.write(json.dumps({"sid": s_, "coq": "skip", "why": "원본도 컴파일 실패"}) + "\n")
        st["원본 컴파일 실패(스킵)"] += len(subs)
        fo.flush()
        continue

    allsel = {x[2] for x in subs}
    if not compile_ok(vf, ws, apply(allsel)):
        for s_ in allsel:
            fo.write(json.dumps({"sid": s_, "coq": "ok"}) + "\n")
        st["통과"] += len(allsel)
    else:
        good, bad = set(), set()
        stack = [sorted(allsel)]
        while stack:
            grp = stack.pop()
            if not grp:
                continue
            if not compile_ok(vf, ws, apply(set(grp))):
                good |= set(grp)
                continue
            if len(grp) == 1:
                bad.add(grp[0])
                continue
            h = len(grp) // 2
            stack.append(grp[:h])
            stack.append(grp[h:])
        for s_ in good:
            fo.write(json.dumps({"sid": s_, "coq": "ok"}) + "\n")
        for s_ in bad:
            fo.write(json.dumps({"sid": s_, "coq": "fail"}) + "\n")
        st["통과"] += len(good)
        st["실패"] += len(bad)
    fo.flush()
    if (fno + 1) % 10 == 0:
        el = time.time() - t0
        done = st["통과"] + st["실패"]
        print(f"   파일 {fno+1}/{len(files)} · 판정 {done} "
              f"(통과 {st['통과']} 실패 {st['실패']}) · {el:.0f}s", flush=True)

fo.close()
print(f"\n■ 결과 ({time.time()-t0:.0f}s)")
for k, v in st.most_common():
    print(f"   {k:28s} {v:8,}")
d = st["통과"] + st["실패"]
if d:
    print(f"\n   Coq 통과율 {st['통과']/d*100:.1f}%  ({st['통과']:,}/{d:,})")
