#!/usr/bin/env python3
"""TRAIN 프로젝트를 **최대한 다양하게, 일부라도** 빌드한다 — elaborate 색인용.

## 왜 "일부라도" 인가

2,182개 저장소가 2023-11 커밋에 고정돼 있고 제각기 다른 Coq 버전을 요구하는데
여기는 Coq 8.18 하나뿐이다(opam 버전은 못 바꾼다). 전부 빌드하는 건 불가능하다.
그런데 **프로젝트당 몇 파일이라도 `.vo` 가 생기면 그 모듈의 elaborate 타입은 뽑힌다.**
색인은 lemma 단위라 부분 성공도 그대로 값이 된다.

## 방법 — 싼 것부터

  1) `make -j` 를 짧은 timeout 으로 (있으면). 성공하면 제일 많이 얻는다
  2) 실패하면 **의존 없는 .v 부터 개별 `coqc`** — 다른 파일을 Require 안 하는 것들은
     혼자 컴파일된다. 이게 "일부라도" 의 실체다

`-R <root> <Name>` 는 `_CoqProject` 가 있으면 거기서, 없으면 루트를 통째로 잡는다.

사용: BT_N=200 BT_JOBS=6 BT_TIMEOUT=90 python3 scripts/build_train_projects.py
"""
import concurrent.futures as cf
import glob, json, os, random, re, subprocess, sys, time

ROOTS = os.environ.get("BT_ROOT", "/tmp/coq-dataset/repos")
N = int(os.environ.get("BT_N", "200"))
JOBS = int(os.environ.get("BT_JOBS", "6"))
TMO = int(os.environ.get("BT_TIMEOUT", "90"))
MAXF = int(os.environ.get("BT_MAX_FILES", "25"))
OUT = os.environ.get("BT_OUT", "all_log/train_build_survey.jsonl")
REQ = re.compile(r"^\s*(?:From\s+\S+\s+)?Require\s+(?:Import|Export)?\s*(.+?)\.", re.M)

def coq_args(root):
    a, pr = [], os.path.join(root, "_CoqProject")
    if os.path.exists(pr):
        t = open(pr, errors="ignore").read().split()
        i = 0
        while i < len(t):
            if t[i] in ("-R", "-Q") and i + 2 < len(t):
                a += [t[i], os.path.abspath(os.path.join(root, t[i + 1])), t[i + 2]]; i += 3
            else:
                i += 1
    if not a:
        nm = re.sub(r"[^A-Za-z0-9_]", "_", os.path.basename(root.rstrip("/")))
        a = ["-R", os.path.abspath(root), nm]
    return a

def local_deps(path, names):
    """이 파일이 **같은 프로젝트의 다른 파일**을 Require 하는 개수."""
    try:
        s = open(path, errors="ignore").read()
    except OSError:
        return 99
    s = re.sub(r"\(\*.*?\*\)", " ", s, flags=re.S)
    d = 0
    for m in REQ.finditer(s):
        for tok in m.group(1).split():
            if tok.split(".")[-1] in names:
                d += 1
    return d

def do(root):
    t0 = time.time()
    vs = glob.glob(os.path.join(root, "**", "*.v"), recursive=True)
    if not vs:
        return None
    names = {os.path.splitext(os.path.basename(v))[0] for v in vs}
    args = coq_args(root)
    rec = dict(project=os.path.basename(root.rstrip("/")), n_v=len(vs),
               make=False, vo=0, mode=None)
    # ① make (있으면) — 제일 많이 얻는다
    if os.path.exists(os.path.join(root, "Makefile")):
        try:
            subprocess.run(["make", "-j2"], cwd=root, capture_output=True,
                           text=True, timeout=TMO)
            rec["make"] = True
        except Exception:
            pass
    n = len(glob.glob(os.path.join(root, "**", "*.vo"), recursive=True))
    if n:
        rec.update(vo=n, mode="make", sec=round(time.time() - t0, 1))
        return rec
    # ② 의존 적은 파일부터 개별 coqc — "일부라도"
    cand = sorted(vs, key=lambda p: (local_deps(p, names), os.path.getsize(p)))[:MAXF]
    ok = 0
    for v in cand:
        if time.time() - t0 > TMO:
            break
        try:
            p = subprocess.run(["coqc", "-q"] + args + [v], cwd=root,
                               capture_output=True, text=True, timeout=25)
            ok += (p.returncode == 0)
        except Exception:
            pass
    rec.update(vo=len(glob.glob(os.path.join(root, "**", "*.vo"), recursive=True)),
               mode="coqc" if ok else None, ok_files=ok,
               sec=round(time.time() - t0, 1))
    return rec

if __name__ == "__main__":
    dirs = sorted(d for d in glob.glob(os.path.join(ROOTS, "*")) if os.path.isdir(d))
    random.seed(0)
    pick = random.sample(dirs, min(N, len(dirs)))
    print(f"■ TRAIN 저장소 {len(dirs)} 중 {len(pick)} 표본 · 병렬 {JOBS} · 프로젝트당 {TMO}s", flush=True)
    res = []
    t0 = time.time()
    with open(OUT, "w") as fo, cf.ThreadPoolExecutor(JOBS) as ex:
        for i, r in enumerate(ex.map(do, pick)):
            if r:
                res.append(r); fo.write(json.dumps(r, ensure_ascii=False) + "\n"); fo.flush()
            if (i + 1) % 20 == 0:
                got = sum(1 for x in res if x["vo"])
                print(f"   … {i+1}/{len(pick)} · .vo 생긴 프로젝트 {got}", flush=True)
    got = [r for r in res if r["vo"]]
    print(f"\n■ 결과 ({time.time()-t0:.0f}s)")
    print(f"   .vo 가 하나라도 생긴 프로젝트  {len(got)}/{len(res)} = {len(got)/max(len(res),1)*100:.1f}%")
    print(f"   make 로 성공                 {sum(1 for r in got if r['mode']=='make')}")
    print(f"   개별 coqc 로만 일부           {sum(1 for r in got if r['mode']=='coqc')}")
    tv = sum(r["n_v"] for r in res); tvo = sum(r["vo"] for r in res)
    print(f"   .v {tv:,} 중 .vo {tvo:,} = {tvo/max(tv,1)*100:.1f}%")
