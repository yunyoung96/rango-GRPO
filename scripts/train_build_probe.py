#!/usr/bin/env python3
"""★ TRAIN 저장소 복구·빌드 성공률 표본 측정.

## 왜

TRAIN 에 필터를 쓰려면 저장소가 컴파일(.vo)돼 있어야 한다. 소스 복구는 검증됐고
(`splits/commits.json` · 98.0%), 의존성도 stdlib 뿐이라는 실측이 있다.
남은 것은 **Coq 8.18 로 실제로 빌드되는가** 다.

## 무엇을 하나

    1. commits.json 에서 프로젝트를 뽑는다 (db 에 실제로 있는 것만)
    2. git clone --depth 1 후 그 커밋으로 되돌린다
    3. coq_makefile 로 Makefile 을 만들고 make 한다
    4. .vo 가 몇 개 생겼나 · 어디서 깨졌나

## 주의

    · 클론은 네트워크가 필요하다. 안 되면 그 사실이 결과다.
    · opam switch 는 건드리지 않는다. 기존 Coq 8.18 로만 시도한다.
    · 저장소마다 타임아웃을 건다 — 큰 프로젝트 하나가 전체를 잡아먹지 않게.

사용: python3 scripts/train_build_probe.py [프로젝트수] [프로젝트당초]
"""
import json, os, re, shutil, subprocess, sys, sqlite3, collections, random, signal

N = int(sys.argv[1]) if len(sys.argv) > 1 else 24
PER = int(sys.argv[2]) if len(sys.argv) > 2 else 240
WORK = "/tmp/train_probe"
OUT = "all_log/train_build_probe.jsonl"


def sh(cmd, cwd=None, timeout=120):
    """셸 한 줄. (성공?, 출력 꼬리) 를 준다."""
    try:
        p = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True,
                           text=True, timeout=timeout, start_new_session=True)
        return p.returncode == 0, ((p.stdout or "") + (p.stderr or ""))[-400:]
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, str(e)[:200]


def db_projects():
    """sentences.db 의 경로에서 프로젝트 이름을 뽑는다 — `owner-repo` 꼴."""
    con = sqlite3.connect("raw-data/coq-dataset/sentences.db")
    cur = con.cursor()
    cur.execute("SELECT DISTINCT file_path FROM sentence")
    c = collections.Counter()
    for (p,) in cur.fetchall():
        m = re.match(r'.*?/repos/([^/]+)/', p or '')
        if m: c[m.group(1)] += 1
    return c


def match_commit(proj, commits):
    """`owner-repo` 를 `owner/repo` 로 되돌린다. 하이픈 위치가 모호하므로 다 시도."""
    parts = proj.split("-")
    for i in range(1, len(parts)):
        cand = "/".join(["-".join(parts[:i]), "-".join(parts[i:])])
        if cand in commits:
            return cand, commits[cand]
    return None, None


if __name__ == "__main__":
    commits = json.load(open("splits/commits.json"))
    projs = db_projects()
    assert projs, "sentences.db 에서 프로젝트를 못 뽑았다"
    # 파일이 많은 것부터 — 실제 학습 데이터를 많이 덮는 것 위주
    cands = []
    for p, n in projs.most_common():
        owner_repo, sha = match_commit(p, commits)
        if owner_repo: cands.append((p, owner_repo, sha, n))
    print(f"■ db 프로젝트 {len(projs)} · 커밋 매칭 {len(cands)}", flush=True)
    random.seed(0)
    top = cands[:60]
    sample = top[:N//2] + random.sample(cands[60:], min(N - N//2, max(0, len(cands)-60)))
    os.makedirs(WORK, exist_ok=True)
    S = collections.Counter(); rows = []
    for k, (proj, owner_repo, sha, nfile) in enumerate(sample, 1):
        d = os.path.join(WORK, proj)
        shutil.rmtree(d, ignore_errors=True)
        rec = {"proj": proj, "repo": owner_repo, "sha": sha[:8], "files": nfile}
        # ★ `--depth 1` 은 HEAD 만 받는다. 우리는 **핀된 커밋**이 필요하므로
        #   그 커밋 하나만 fetch 한다 — 전체 이력을 안 받아 훨씬 빠르다.
        os.makedirs(d, exist_ok=True)
        ok = (sh("git init -q .", cwd=d, timeout=30)[0]
              and sh(f"git remote add origin https://github.com/{owner_repo}.git",
                     cwd=d, timeout=30)[0])
        msg = ""
        if ok:
            ok, msg = sh(f"git fetch -q --depth 1 origin {sha}", cwd=d, timeout=300)
            if ok:
                ok, msg = sh("git checkout -q FETCH_HEAD", cwd=d, timeout=120)
        if not ok:
            rec["stage"] = "clone"; rec["err"] = msg[-160:]; S["클론 실패"] += 1
            rows.append(rec)
            print(f"   {k:3d}/{len(sample)} {proj[:34]:34s} 클론X {msg[-50:]}", flush=True)
            shutil.rmtree(d, ignore_errors=True); continue
        vs = sh("find . -name '*.v' | head -1", cwd=d)[1].strip()
        if not vs:
            rec["stage"] = "no_v"; S[".v 없음"] += 1; rows.append(rec); continue
        # _CoqProject 가 없으면 만든다
        if not os.path.exists(os.path.join(d, "_CoqProject")):
            sh("find . -name '*.v' -not -path './.git/*' > _CoqProject_files && "
               "{ echo '-R . Top'; cat _CoqProject_files; } > _CoqProject", cwd=d)
        ok, msg = sh("coq_makefile -f _CoqProject -o Makefile", cwd=d, timeout=120)
        if not ok:
            rec["stage"] = "coq_makefile"; rec["err"] = msg[-160:]; S["makefile 실패"] += 1
            rows.append(rec); print(f"   {k:3d}/{len(sample)} {proj[:38]:38s} makefile✗", flush=True)
            continue
        ok, msg = sh(f"make -j2 -k", cwd=d, timeout=PER)
        nvo = int(sh("find . -name '*.vo' | wc -l", cwd=d)[1].strip() or 0)
        nv = int(sh("find . -name '*.v' -not -path './.git/*' | wc -l", cwd=d)[1].strip() or 0)
        rec.update(stage="make", vo=nvo, v=nv,
                   ratio=(nvo / nv if nv else 0.0), err=("" if ok else msg[-160:]))
        if nvo == 0: S["빌드 0"] += 1; tag = "빌드✗"
        elif nvo >= nv * 0.9: S["완전 빌드"] += 1; tag = "완전✓"
        elif nvo >= nv * 0.3: S["부분 빌드"] += 1; tag = f"부분 {nvo}/{nv}"
        else: S["소량"] += 1; tag = f"소량 {nvo}/{nv}"
        rows.append(rec)
        print(f"   {k:3d}/{len(sample)} {proj[:38]:38s} {tag}", flush=True)
        shutil.rmtree(d, ignore_errors=True)
    with open(OUT, "w") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    n = max(1, len(rows))
    print(f"\n■ TRAIN 빌드 성공률 (표본 {len(rows)})")
    for k, v in S.most_common():
        print(f"   {k:14s} {v:4d}  {v/n*100:5.1f}%")
    good = S["완전 빌드"] + S["부분 빌드"]
    print(f"\n   ★ 쓸 만한 것 (완전+부분) {good}/{n} = {good/n*100:.1f}%")
    fv = sum(r.get("vo", 0) for r in rows); ft = sum(r.get("v", 0) for r in rows)
    if ft: print(f"   파일 기준 컴파일률 {fv}/{ft} = {fv/ft*100:.1f}%")
