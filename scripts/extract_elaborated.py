#!/usr/bin/env python3
"""★ **elaborate 된 lemma 타입**을 뽑는다 — `Set Printing All` 로.

## 왜 필요한가

검색·색인이 맞춰야 하는 것은 **Coq 이 보는 항**이지 사람이 쓴 텍스트가 아니다.
`sentences.db` 의 선언문은 elaborate **전** 형태라 아래가 전부 불일치로 나온다:

    암묵 인자   nth_error nil n        →  @nth_error A (@nil A) n
    notation    dm!id = Some gd        →  @eq (option globdef) (PTree.get id dm) (Some gd)
    coercion    IZR z + r              →  Rplus (IZR z) r
    섹션 변수    reachable n1 n3        →  reachable code make_predecessors n1 n3

`Set Printing All` 은 이 넷을 전부 펼친다.

## 방법

모듈마다 한 번씩:

    Set Printing All.
    Require Import <M>.
    Search _ inside <M>.        (* 그 모듈의 lemma 전부를 타입과 함께 덤프 *)

`.vo` 가 있어야 `Require Import` 가 된다 — **미리 빌드된 프로젝트에만 쓸 수 있다.**
실측(CompCert): 모듈당 중앙 0.56s · 149모듈 1.5분(직렬).

사용: EE_ROOT=CoqStoq/test-repos/compcert EE_OUT=data/elab_compcert.jsonl \
      EE_JOBS=8 python3 scripts/extract_elaborated.py
"""
import concurrent.futures as cf
import glob, json, os, re, subprocess, sys, tempfile, time

ROOT = os.environ.get("EE_ROOT", "CoqStoq/test-repos/compcert")
OUT = os.environ.get("EE_OUT", "data/elab_compcert.jsonl")
JOBS = int(os.environ.get("EE_JOBS", "8"))
TIMEOUT = int(os.environ.get("EE_TIMEOUT", "120"))
NAME = os.environ.get("EE_NAME", os.path.basename(ROOT.rstrip("/")))

def coq_args(root):
    """`_CoqProject` 의 -R/-Q 를 절대경로로. 없으면 루트를 통째로 -R 한다."""
    a, pr = [], os.path.join(root, "_CoqProject")
    if os.path.exists(pr):
        t = open(pr, errors="ignore").read().split()
        i = 0
        while i < len(t):
            if t[i] in ("-R", "-Q") and i + 2 < len(t):
                a += [t[i], os.path.abspath(os.path.join(root, t[i + 1])), t[i + 2]]
                i += 3
            else:
                i += 1
    if not a:
        a = ["-R", os.path.abspath(root), NAME.replace("-", "_")]
    return a

ARGS = coq_args(ROOT)
PREF = {}
for i in range(0, len(ARGS), 3):
    PREF[ARGS[i + 1]] = ARGS[i + 2]

def modules():
    out = []
    for vo in sorted(glob.glob(os.path.join(ROOT, "**", "*.vo"), recursive=True)):
        d, b = os.path.abspath(os.path.dirname(vo)), os.path.splitext(os.path.basename(vo))[0]
        # 가장 긴(=가장 구체적인) 접두사에 붙인다
        best = max((p for p in PREF if d == p or d.startswith(p + os.sep)), key=len, default=None)
        if best is None:
            continue
        rel = os.path.relpath(d, best).replace(os.sep, ".")
        out.append(f"{PREF[best]}.{rel}.{b}" if rel != "." else f"{PREF[best]}.{b}")
    return out

# `Search` 출력 한 항목 = "이름:\n  타입" 또는 "이름\n     : 타입"
ITEM = re.compile(r"^(\S[\w'.]*?):?\s*$\n((?:^[ \t]+.*$\n?)+)", re.M)

def run(mod):
    short = mod.split(".")[-1]
    src = f"Set Printing All.\nRequire Import {mod}.\nSearch _ inside {short}.\n"
    with tempfile.NamedTemporaryFile("w", suffix=".v", delete=False) as f:
        f.write(src); path = f.name
    try:
        t = time.time()
        p = subprocess.run(["coqc", "-q"] + ARGS + [path],
                           capture_output=True, text=True, timeout=TIMEOUT)
        dt = time.time() - t
        if p.returncode != 0:
            return mod, [], dt, (p.stderr or "")[:200]
        recs = []
        for m in ITEM.finditer(p.stdout or ""):
            nm = m.group(1).rstrip(":")
            ty = " ".join(m.group(2).split())
            if nm and ty and not nm.startswith("("):
                recs.append({"name": nm, "type": ty, "module": mod})
        return mod, recs, dt, None
    except subprocess.TimeoutExpired:
        return mod, [], TIMEOUT, "timeout"
    except Exception as e:
        return mod, [], 0.0, str(e)[:150]
    finally:
        for ext in (".v", ".vo", ".vok", ".vos", ".glob"):
            try: os.unlink(os.path.splitext(path)[0] + ext)
            except OSError: pass

if __name__ == "__main__":
    mods = modules()
    print(f"■ {NAME} · 빌드된 모듈 {len(mods)} · 병렬 {JOBS}", flush=True)
    if not mods:
        print("  (.vo 없음 — 빌드가 안 된 프로젝트다)"); sys.exit(0)
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    n_ok = n_rec = 0; fails = []
    t0 = time.time()
    with open(OUT, "w") as fo, cf.ThreadPoolExecutor(JOBS) as ex:
        for i, (mod, recs, dt, err) in enumerate(ex.map(run, mods)):
            if err:
                fails.append((mod, err))
            else:
                n_ok += 1
                for r in recs:
                    r["project"] = NAME
                    fo.write(json.dumps(r, ensure_ascii=False) + "\n")
                n_rec += len(recs)
            if (i + 1) % 25 == 0:
                print(f"   … {i+1}/{len(mods)} · 항목 {n_rec:,}", flush=True)
    print(f"\n  모듈 {n_ok}/{len(mods)} 성공 · 항목 {n_rec:,} · {time.time()-t0:.1f}s → {OUT}")
    for m, e in fails[:5]:
        print(f"    실패 {m}: {e[:110]}")
