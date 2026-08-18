#!/usr/bin/env python3
"""CoqStoq VAL/TEST 의 **삭제된 .v 파일을 복원**한다.

## 왜 필요했나

`scripts/hunt_assert_errors.py` 에 치명적 버그가 있었다. `Check`/증명 검증을 원본과 **같은
파일 이름**으로 해야 모듈 경로가 안 어긋나므로 원본을 잠시 옮기고 그 자리에 임시본을 쓰는데,
그 경로를 `tmp_files` 에 넣어 두고 **스크립트 끝에서 전부 unlink** 했다. 결과적으로 원본
소스가 삭제됐다(VAL 의 "소스 파일 없음" 이 493 → 2,926 으로 늘어난 원인).

버그는 고쳤고, 이 스크립트가 피해를 복구한다.

## 어떻게

`splits/commits.json` 에 VAL/TEST 프로젝트도 핀된 커밋으로 들어 있다. 그 커밋으로 clone 해
**.v 파일만** 덮어쓴다 — 빌드 산출물(.vo/.glob/.aux)은 그대로 두므로 재빌드가 필요 없다.

사용: python3 scripts/restore_coqstoq_sources.py [val|test|both] [--dry]
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

WHICH = (sys.argv[1] if len(sys.argv) > 1 else "both").lower()
DRY = "--dry" in sys.argv
CM = json.load(open("splits/commits.json"))

_ENV = dict(os.environ)
for k in ("GIT_ASKPASS", "SSH_ASKPASS", "VSCODE_GIT_ASKPASS_NODE",
          "VSCODE_GIT_ASKPASS_MAIN", "VSCODE_GIT_ASKPASS_EXTRA_ARGS",
          "VSCODE_GIT_IPC_HANDLE"):
    _ENV.pop(k, None)
_ENV["GIT_TERMINAL_PROMPT"] = "0"

# CoqStoq 디렉토리명 → commits.json 키. 대부분 coq-community 소속이다.
KNOWN = {
    "graph-theory": "coq-community/graph-theory",
    "bertrand": "coq-community/bertrand",
    "qarith-stern-brocot": "coq-community/qarith-stern-brocot",
    "sudoku": "coq-community/sudoku",
    "stalmarck": "coq-community/stalmarck",
    "coqeal": "coq-community/coqeal",
    "compcert": "AbsInt/CompCert",
    "huffman": "coq-community/huffman",
    "poltac": "thery/PolTac",
    "buchberger": "thery/buchberger",
    "dblib": "fpottier/dblib",
    "ext-lib": "coq-community/coq-ext-lib",
    "fourcolor": "coq-community/fourcolor",
    "math-classes": "coq-community/math-classes",
    "reglang": "coq-community/reglang",
    "zfc": "coq-community/zfc",
    "zorns-lemma": "coq-community/zorns-lemma",
    "hoare-tut": "coq-community/hoare-tut",
}

dirs = []
for split in (["val", "test"] if WHICH == "both" else [WHICH]):
    root = Path(f"CoqStoq/{split}-repos")
    if root.is_dir():
        dirs += [p for p in root.iterdir() if p.is_dir()]

print(f"대상 {len(dirs)}개 프로젝트" + ("  [DRY]" if DRY else ""))
tot_new = tot_skip = 0
for d in dirs:
    name = d.name
    slug = KNOWN.get(name)
    if not slug or slug not in CM:
        # commits.json 에서 이름으로 찾아본다
        cand = [k for k in CM if k.split("/")[-1].lower() == name.lower()]
        slug = cand[0] if cand else None
    if not slug or slug not in CM:
        print(f"  ? {name:24s} commits.json 에서 못 찾음 — 건너뜀")
        continue
    n_v = len(list(d.rglob("*.v")))
    n_vo = len(list(d.rglob("*.vo")))
    if n_v >= n_vo:
        tot_skip += 1
        continue                                    # 온전하다
    print(f"  · {name:24s} .v {n_v} / .vo {n_vo} → {slug}@{CM[slug][:8]}", flush=True)
    if DRY:
        continue
    with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
        try:
            subprocess.run(["git", "clone", "-q", f"https://github.com/{slug}.git", tmp],
                           check=True, capture_output=True, timeout=1200, env=_ENV)
            subprocess.run(["git", "-C", tmp, "checkout", "-q", CM[slug]],
                           check=True, capture_output=True, timeout=600, env=_ENV)
        except Exception as ex:
            print(f"    ✗ clone 실패: {str(ex)[:70]}")
            continue
        new = 0
        for src in Path(tmp).rglob("*.v"):
            rel = src.relative_to(tmp)
            dst = d / rel
            if dst.exists():
                continue                            # 남아 있는 것은 건드리지 않는다
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            new += 1
        tot_new += new
        print(f"    ✓ .v {new}개 복원 (총 {len(list(d.rglob('*.v')))}개)", flush=True)

print(f"\n복원한 .v {tot_new}개 · 온전했던 프로젝트 {tot_skip}개")
