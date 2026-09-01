#!/usr/bin/env python3
"""★ ①+ TRAIN 저장소 빌드 캠페인 — SFT 데이터 규모의 진짜 병목은 '빌드된 저장소 수'다.

현재 빌드된 TRAIN(coq-art·undecidability)은 TRAIN 파일 18,911 의 2.6% 뿐. 파일 수 상위
프로젝트부터 splits/commits.json 커밋으로 클론·빌드해 tmp/tr/<owner-repo> 에 영속 보관한다.
v2 하네스(train_build_v2.build)를 그대로 재사용 — 자기 빌드계 우선, 없으면 -Q 생성.

  · 이어하기: all_log/train_build_campaign.jsonl 에 있는 프로젝트는 건너뜀
  · 배제: HoTT(Type 이론)·Priyanka(Coq 사본)·CompCert(held-out)·coq-art 사본(중복 데이터)
  · 부분 빌드도 보관 (train_pool 은 파일별 .vo 존재로 거른다)
  · 12코어 공유 서버 — 한 번에 1 프로젝트, make -j3

사용: python3 scripts/train_build_campaign.py [상위N=60] [프로젝트당 초=1500]
"""
import collections, json, os, re, shutil, subprocess, sys, time
sys.path.insert(0, "scripts")
_A = sys.argv[:]; sys.argv = ["train_build_v2.py"]     # v2 는 import 시 argv[1] 을 정수로 읽는다
import train_build_v2 as V
sys.argv = _A
from train_build_probe import db_projects, match_commit, sh

N = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 60
PER = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 1500
V.PER = PER
WORK = "/app/coq-modeling/tmp/tr"
OUT = "all_log/train_build_campaign.jsonl"
JOBS = 3
EXCL = {"HoTT-Coq-HoTT", "Priyanka-Mondal-Coq", "AbsInt-CompCert"}
EXCL_RE = re.compile(r"coq-?art", re.I)          # coq-art 사본류 (coq-community 본판만 허용)
KEEP = {"coq-community-coq-art"}


def kst(): return time.strftime("%H:%M", time.localtime())


def qflags_of(d, proj):
    """coqdep 에 줄 논리경로 플래그 — 저장소 _CoqProject 의 -Q/-R/-I 가 있으면 그것, 없으면
    V.build 의 생성 규칙과 동일하게 최상위 디렉토리마다 -Q."""
    cp = os.path.join(d, "_CoqProject")
    if os.path.exists(cp):
        fl = [l.strip() for l in open(cp, errors="ignore") if l.strip().startswith(("-Q", "-R", "-I"))]
        if fl: return " ".join(fl)
    files = [f for f in V.vfiles(d) if V.legal_path(f)]
    tops = sorted({f.split("/")[0] if "/" in f else "." for f in files})
    base = V.sanitize(proj.split("-")[-1] or proj)
    return " ".join(f"-Q {t} {base if t == '.' else base + '_' + V.sanitize(t)}" for t in tops)


_BAD = re.compile(r'(?:File "([^"]+)"|in file ([^,\s]+),)')


def prescreen(d, proj, cap=80):
    """★ coqdep 전수 사전검사 — 파일 하나의 구문 오류로 coqdep 전체가 죽으면 .Makefile.d 가
    안 생겨 프로젝트 전부가 0vo 가 된다 (possientis-Prog 실측). 죽게 만드는 파일을 찾아
    `.v.badv` 로 치워 둔다 (기록 보존·vfiles 에서 제외). 제거한 파일 수를 돌려준다."""
    qf = qflags_of(d, proj)
    removed = []
    for rnd in range(cap):
        files = [f for f in V.vfiles(d) if V.legal_path(f)]
        if not files: break
        p = subprocess.run(f"coqdep {qf} " + " ".join(files), shell=True, cwd=d,
                           capture_output=True, text=True, timeout=600)
        if p.returncode == 0: break
        # Error 줄만 본다 — "Warning: in file X, library … not found" 는 경고라 제외하면 과잉 제거
        bad = set()
        for ln in p.stderr.splitlines():
            if "Error" in ln:
                for a, b in _BAD.findall(ln): bad.add(a or b)
        bad &= set(files)
        if not bad:
            # 파일을 못 짚으면 개별 검사로 전환 (느리지만 확실)
            for f in files:
                q = subprocess.run(f"coqdep {qf} {f}", shell=True, cwd=d, capture_output=True, text=True, timeout=60)
                if q.returncode != 0: bad.add(f)
            if not bad: break
        for f in bad:
            os.rename(os.path.join(d, f), os.path.join(d, f + ".badv")); removed.append(f)
        if len(bad) > 0 and not _BAD.findall(p.stderr): break   # 개별검사 1회면 충분
    return removed


assert _BAD.search('*** Error: File "coq/systemF/subst.v",characters 266-266: Syntax error').group(1) == "coq/systemF/subst.v"
assert _BAD.search("*** Warning: in file coq/a.v, library term is required").group(2) == "coq/a.v"


def excluded(p):
    if p in KEEP: return False
    return p in EXCL or bool(EXCL_RE.search(p))


assert excluded("HoTT-Coq-HoTT") and excluded("haoyang9804-coq-Art") and not excluded("coq-community-coq-art")
assert not excluded("coq-community-corn")

# make -j 를 캠페인 값으로 (v2 는 -j2 고정)
_orig_run = subprocess.run
def _run(cmd, *a, **k):
    if isinstance(cmd, str) and cmd.startswith("make -j2 -k"): cmd = f"make -j{JOBS} -k"
    return _orig_run(cmd, *a, **k)
V.subprocess.run = _run

if __name__ == "__main__" and len(sys.argv) > 2 and sys.argv[1] == "--prescreen-test":
    d = sys.argv[2]; proj = os.path.basename(d.rstrip("/"))
    t0 = time.time(); bad = prescreen(d, proj)
    print(f"사전검사 {proj}: 제외 {len(bad)} {bad[:5]} ({int(time.time()-t0)}s)"); sys.exit(0)

if __name__ == "__main__":
    commits = json.load(open("splits/commits.json"))
    projs = db_projects()
    done = {}
    if os.path.exists(OUT):
        for l in open(OUT):
            try: r = json.loads(l); done[r["proj"]] = r
            except Exception: pass
    cands = []
    for p, n in projs.most_common():
        if excluded(p): continue
        o, sha = match_commit(p, commits)
        if not o: continue
        cands.append((p, o, sha, n))
        if len(cands) >= N: break
    print(f"■ 캠페인: 후보 {len(cands)} (상위 {N}, 배제 규칙 적용) · 기완료 {len(done)} · {kst()} KST", flush=True)
    os.makedirs(WORK, exist_ok=True)
    C = collections.Counter(); TOTV = TOTVO = 0; t_all = time.time()
    for k, (proj, repo, sha, nf) in enumerate(cands, 1):
        d = os.path.join(WORK, proj)
        if proj in done:
            r = done[proj]; C["기완료"] += 1; TOTV += r.get("v", 0); TOTVO += r.get("vo", 0); continue
        if os.path.isdir(d) and V.vofiles(d):
            nv, nvo = len(V.vfiles(d)), len(V.vofiles(d))
            row = {"proj": proj, "repo": repo, "cause": "기빌드", "v": nv, "vo": nvo, "route": ["기존"], "sec": 0}
            open(OUT, "a").write(json.dumps(row, ensure_ascii=False) + "\n")
            C["기빌드"] += 1; TOTV += nv; TOTVO += nvo
            print(f"   {k:3d}/{len(cands)} {proj[:36]:36s} 기빌드 vo={nvo}/{nv}", flush=True); continue
        t0 = time.time()
        shutil.rmtree(d, ignore_errors=True); os.makedirs(d, exist_ok=True)
        ok = False
        for attempt in range(V.CLONE_TRY):
            sh("git init -q .", cwd=d, timeout=60)
            sh(f"git remote add origin https://github.com/{repo}.git", cwd=d, timeout=60)
            ok, msg = sh(f"git fetch -q --depth 1 origin {sha}", cwd=d, timeout=V.CLONE_T)
            if ok: ok, msg = sh("git checkout -q FETCH_HEAD", cwd=d, timeout=300)
            if ok: break
        if not ok:
            C["클론 실패"] += 1; shutil.rmtree(d, ignore_errors=True)
            row = {"proj": proj, "repo": repo, "cause": "클론 실패", "v": 0, "vo": 0, "route": [], "sec": int(time.time() - t0)}
            open(OUT, "a").write(json.dumps(row, ensure_ascii=False) + "\n")
            print(f"   {k:3d}/{len(cands)} {proj[:36]:36s} 클론✗", flush=True); continue
        # ★ 순환/깨진 심볼릭 링크 제거 — coqdep 가 -Q 디렉토리를 재귀로 따라가다
        #   "Too many levels of symbolic links" 로 죽어 .Makefile.d 가 안 생긴다
        #   (possientis-Prog·TacTok 0vo 원인). 파일형 심링크는 남긴다.
        nl = subprocess.run("find . -type l \\( -xtype d -o -xtype l \\) -print -delete | wc -l",
                            shell=True, cwd=d, capture_output=True, text=True).stdout.strip()
        if nl and nl != "0": print(f"      심링크 제거 {nl}", flush=True)
        try:
            bad = prescreen(d, proj)
        except Exception as e:
            bad = []; print(f"      사전검사 예외 {type(e).__name__}: {str(e)[:80]}", flush=True)
        if bad: print(f"      coqdep 사전검사: 구문오류 파일 {len(bad)}개 제외 (예: {bad[0]})", flush=True)
        def _build():
            try: return V.build(d, proj)
            except subprocess.TimeoutExpired:
                return "빌드 timeout", "", len(V.vfiles(d)), len(V.vofiles(d)), ["timeout"]
            except Exception as e:
                return f"예외 {type(e).__name__}", str(e)[:200], 0, 0, ["exc"]
        cause, msg, nv, nvo, route = _build()
        # ★ 자기 빌드계가 0vo (예: possientis-Prog 의 .Makefile.d 의존 생성 실패) →
        #   빌드계를 치우고 우리 -Q 생성 경로로 한 번 더. 더 나은 쪽을 채택.
        if nvo == 0 and nv > 0 and any(r.startswith("자기") or r.startswith("configure") for r in route):
            for f in ("Makefile", "makefile", "GNUmakefile", "Makefile.coq", "_CoqProject", "configure", "dune-project"):
                fp = os.path.join(d, f)
                if os.path.exists(fp): os.rename(fp, fp + ".orig")
            sh("find . -name 'Makefile.coq*' -delete", cwd=d, timeout=60)
            cause2, msg2, nv2, nvo2, route2 = _build()
            route = route + ["→생성재시도"] + route2
            if nvo2 > nvo: cause, msg, nv, nvo = cause2, msg2, nv2, nvo2
        # 절단 방지 교차검증 (v2 교훈): find 로 다시 센다
        _vo = int(subprocess.run("find . -name '*.vo' | wc -l", shell=True, cwd=d, capture_output=True, text=True).stdout.strip() or 0)
        assert abs(_vo - nvo) <= 2, f"vo 수 불일치 {nvo} vs find {_vo}"
        if nvo == 0: shutil.rmtree(d, ignore_errors=True)     # 0vo 는 디스크만 먹는다
        TOTV += nv; TOTVO += nvo
        cls = "완전" if nv and nvo >= nv else ("≥50%" if nv and nvo >= 0.5 * nv else ("부분" if nvo else "0vo"))
        C[cls] += 1
        row = {"proj": proj, "repo": repo, "cause": cause, "v": nv, "vo": nvo, "route": route, "sec": int(time.time() - t0), "err": msg[-300:], "badv": len(bad), "symlink_rm": int(nl or 0)}
        open(OUT, "a").write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"   {k:3d}/{len(cands)} {proj[:36]:36s} vo={nvo:4d}/{nv:4d} {cls:4s} {int(time.time()-t0):4d}s  {cause[:40]}  [{kst()}]", flush=True)
    print(f"\n■ 캠페인 종료 {int(time.time()-t_all)}s: {dict(C)} · vo {TOTVO}/{TOTV} ({TOTVO/max(TOTV,1)*100:.1f}%)")
    assert sum(C.values()) == len(cands)
    print("CAMPAIGN_DONE")
