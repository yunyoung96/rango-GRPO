#!/usr/bin/env python3
"""★ ④ TRAIN 저장소 빌드 캠페인 — SFT 데이터 규모의 진짜 병목은 '빌드된 저장소 수'다.

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
import train_build_v2 as V
from train_build_probe import db_projects, match_commit, sh

N = int(sys.argv[1]) if len(sys.argv) > 1 else 60
PER = int(sys.argv[2]) if len(sys.argv) > 2 else 1500
V.PER = PER
WORK = "/app/coq-modeling/tmp/tr"
OUT = "all_log/train_build_campaign.jsonl"
JOBS = 3
EXCL = {"HoTT-Coq-HoTT", "Priyanka-Mondal-Coq", "AbsInt-CompCert"}
EXCL_RE = re.compile(r"coq-?art", re.I)          # coq-art 사본류 (coq-community 본판만 허용)
KEEP = {"coq-community-coq-art"}


def kst(): return time.strftime("%H:%M", time.localtime())


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
        try:
            cause, msg, nv, nvo, route = V.build(d, proj)
        except subprocess.TimeoutExpired:
            cause, msg, nv, nvo, route = "빌드 timeout", "", len(V.vfiles(d)), len(V.vofiles(d)), ["timeout"]
        except Exception as e:
            cause, msg, nv, nvo, route = f"예외 {type(e).__name__}", str(e)[:200], 0, 0, ["exc"]
        # 절단 방지 교차검증 (v2 교훈): find 로 다시 센다
        _vo = int(subprocess.run("find . -name '*.vo' | wc -l", shell=True, cwd=d, capture_output=True, text=True).stdout.strip() or 0)
        assert abs(_vo - nvo) <= 2, f"vo 수 불일치 {nvo} vs find {_vo}"
        if nvo == 0: shutil.rmtree(d, ignore_errors=True)     # 0vo 는 디스크만 먹는다
        TOTV += nv; TOTVO += nvo
        cls = "완전" if nv and nvo >= nv else ("≥50%" if nv and nvo >= 0.5 * nv else ("부분" if nvo else "0vo"))
        C[cls] += 1
        row = {"proj": proj, "repo": repo, "cause": cause, "v": nv, "vo": nvo, "route": route, "sec": int(time.time() - t0), "err": msg[-300:]}
        open(OUT, "a").write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"   {k:3d}/{len(cands)} {proj[:36]:36s} vo={nvo:4d}/{nv:4d} {cls:4s} {int(time.time()-t0):4d}s  {cause[:40]}  [{kst()}]", flush=True)
    print(f"\n■ 캠페인 종료 {int(time.time()-t_all)}s: {dict(C)} · vo {TOTVO}/{TOTV} ({TOTVO/max(TOTV,1)*100:.1f}%)")
    assert sum(C.values()) == len(cands)
    print("CAMPAIGN_DONE")
