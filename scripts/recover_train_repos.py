#!/usr/bin/env python3
"""TRAIN split 의 원본 .v 저장소를 **커밋 해시에 고정해** 복구한다.

## 왜 가능한가

`splits/commits.json` 이 `owner/repo → 40-hex 커밋 해시` 를 2,955개 담고 있다.
sentences.db 의 경로 `repos/<owner>-<repo>/…` 를 하이픈 분할로 매칭하면
**2,268/2,270 프로젝트(99.9%) · 18,531/18,911 파일(98.0%)** 이 대응된다.

검증: `superwalter/French-thesis` 를 핀된 커밋으로 체크아웃하니 `dev/Term.v` 의
**줄 번호까지 db 와 일치**했다(line 10 Inductive sort · line 14 Inductive term …).
즉 데이터 생성 당시의 스냅샷을 정확히 재현한다.

## 왜 필요한가

TRAIN 에서 assert 변환을 **실제 Coq 으로 검증**하려면 원본 .v 가 있어야 한다.
지금은 VAL/TEST(20개 프로젝트)에서만 검증 가능해 TRAIN 에는 정적 규칙만 적용하고 있다.

## 주의

  · 클론만 한다. **빌드는 별개 문제**다(opam 의존성 · Coq 버전).
    검증 목적이라면 그 파일이 참조하는 정의가 컴파일돼 있어야 하므로 빌드도 필요하다.
  · `--filter=blob:none --no-checkout` 로 받아 필요한 커밋만 체크아웃한다(대역폭 절약).
  · coq-community/corn·gaia 는 해시가 없다 → 기본 브랜치를 쓰거나 건너뛴다.

사용: python3 scripts/recover_train_repos.py [개수] [출력디렉토리] [--dry]
      LIST=파일  파일에 적힌 프로젝트만 (한 줄에 owner-repo)
"""
import collections
import json
import os
import re
import subprocess
import sqlite3
import sys
from pathlib import Path

# ★ VS Code 원격 컨테이너의 git 인증 헬퍼가 깨져 있어(`Cannot find module
#   /tmp/vscode-remote-containers-*.js`) 없거나 비공개인 저장소에서 clone 이 실패한다.
#   인증 프롬프트를 완전히 끄면 즉시 실패하고 다음으로 넘어간다.
_ENV = dict(os.environ)
for k in ("GIT_ASKPASS", "SSH_ASKPASS", "GIT_CREDENTIAL_HELPER",
          "VSCODE_GIT_ASKPASS_NODE", "VSCODE_GIT_ASKPASS_MAIN",
          "VSCODE_GIT_ASKPASS_EXTRA_ARGS", "VSCODE_GIT_IPC_HANDLE"):
    _ENV.pop(k, None)
_ENV["GIT_TERMINAL_PROMPT"] = "0"
_ENV["GIT_CONFIG_COUNT"] = "1"
_ENV["GIT_CONFIG_KEY_0"] = "credential.helper"
_ENV["GIT_CONFIG_VALUE_0"] = ""

N = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 20
DEST = Path(sys.argv[2]) if len(sys.argv) > 2 and not sys.argv[2].startswith("-") \
    else Path("/tmp/coq-dataset/repos")
DRY = "--dry" in sys.argv
DB = os.environ.get("SDB", "/tmp/coq-dataset/sentences.db")
COMMITS = os.environ.get("COMMITS", "splits/commits.json")

cm = json.load(open(COMMITS))
keys = set(cm)


def to_slug(name: str):
    """`owner-repo` → `owner/repo`. 하이픈 위치가 애매하므로 모든 분할을 시도한다."""
    parts = name.split("-")
    for k in range(1, len(parts)):
        cand = "/".join(["-".join(parts[:k]), "-".join(parts[k:])])
        if cand in keys:
            return cand
    return None


db = sqlite3.connect(DB)
cnt: collections.Counter = collections.Counter()
for (fp,) in db.execute("select distinct file_path from sentence "
                        "where file_path like '%coq-dataset/repos%'"):
    m = re.search(r"repos/([^/]+)/", fp)
    if m:
        cnt[m.group(1)] += 1

want = None
if os.environ.get("LIST"):
    want = {x.strip() for x in open(os.environ["LIST"]) if x.strip()}

targets = []
for name, nf in cnt.most_common():
    if want and name not in want:
        continue
    slug = to_slug(name)
    if slug:
        targets.append((name, slug, cm[slug], nf))

print(f"매칭된 프로젝트 {len(targets)}개 (파일 {sum(t[3] for t in targets)})")
print(f"대상: 상위 {N}개 · 목적지 {DEST}" + ("  [DRY RUN]" if DRY else ""))

DEST.mkdir(parents=True, exist_ok=True)
ok = fail = skip = 0
for name, slug, sha, nf in targets[:N]:
    d = DEST / name
    if (d / ".git").exists():
        skip += 1
        continue
    if DRY:
        print(f"  [dry] {name:44s} ← {slug}@{sha[:8]} ({nf}파일)")
        ok += 1
        continue
    try:
        # blob 을 지연 받아 대역폭을 아끼고, 필요한 커밋만 체크아웃한다
        subprocess.run(["git", "clone", "-q", "--filter=blob:none", "--no-checkout",
                        f"https://github.com/{slug}.git", str(d)],
                       check=True, capture_output=True, timeout=900, env=_ENV)
        subprocess.run(["git", "-C", str(d), "checkout", "-q", sha],
                       check=True, capture_output=True, timeout=900, env=_ENV)
        n_v = len(list(d.rglob("*.v")))
        print(f"  ✓ {name:44s} {slug}@{sha[:8]}  .v {n_v}개 (db {nf})", flush=True)
        ok += 1
    except subprocess.CalledProcessError as ex:
        err = " ".join((ex.stderr or b"").decode(errors="ignore").split())[:90]
        print(f"  ✗ {name:44s} {err}", flush=True)
        fail += 1
    except subprocess.TimeoutExpired:
        print(f"  ✗ {name:44s} timeout", flush=True)
        fail += 1

print(f"\n성공 {ok} · 실패 {fail} · 이미있음 {skip}")
