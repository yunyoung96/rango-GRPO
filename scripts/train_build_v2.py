#!/usr/bin/env python3
"""★ TRAIN 빌드 하네스 2판 — 1판이 잰 4.6% 는 **데이터가 아니라 하네스**였다.

1판(`train_build_probe.py`)의 문제:
    `_CoqProject` 가 없으면 `-R . Top` 을 지어 붙였다. 그러면 모듈 이름이
    `Top.coq.pierce-lem` 이 되고 **하이픈은 Coq 식별자가 아니다** → 즉사.
    실측 표본 12개 중 10개가 `_CoqProject` 없이 이 경로를 탔다.

2판이 고치는 것:
    ① 저장소의 **자기 빌드계**를 먼저 쓴다 — `./configure` → `Makefile`
       → `_CoqProject`. 없을 때만 만들고, 그때도 `-Q <dir> <합법식별자>` 로.
    ② 경로 성분에 **Coq 식별자가 아닌 것**(하이픈·공백·숫자시작)이 있으면
       그 파일을 논리경로에서 뺀다.
    ③ 클론 timeout 을 늘리고 재시도한다 (1판 표본의 25%가 여기서 죽었다).
    ④ 그러고도 안 되는 것만 **진짜 버전 드리프트**로 센다.

사용: python3 scripts/train_build_v2.py [표본수]
"""
import collections, json, os, random, re, shutil, subprocess, sys

N = int(sys.argv[1]) if len(sys.argv) > 1 else 20
WORK = "/tmp/claude-0/-app-coq-modeling/e02d0688-7cb1-43a8-aa0e-ee8afd60ce19/scratchpad/tb2"
PER = 1200          # 빌드 상한(초)
CLONE_T = 900       # ★ 1판은 300 이었다 — 25%가 여기서 죽었다
CLONE_TRY = 2
OUT = "all_log/train_build_v2.jsonl"

sys.path.insert(0, "scripts")
from train_build_probe import db_projects, match_commit, sh

#: Coq 식별자 — 문자/밑줄로 시작, 이어서 문자·숫자·밑줄·프라임
_ID = re.compile(r"^[A-Za-z_][A-Za-z0-9_']*$")
#: 논리경로에 못 쓰는 예약어 (극히 일부만 실제로 문제가 된다)
_KW = {"Type", "Set", "Prop", "forall", "fun", "let", "in", "match", "with", "end"}


def legal_path(rel):
    """`a/b/c.v` 의 모든 성분이 Coq 식별자인가."""
    parts = rel[:-2].split("/") if rel.endswith(".v") else rel.split("/")
    return all(_ID.match(p) and p not in _KW for p in parts if p not in (".", ""))


def sanitize(name):
    """저장소 이름을 논리경로 이름으로 — 불법 문자를 밑줄로."""
    s = re.sub(r"[^A-Za-z0-9_']", "_", name)
    if not s or not re.match(r"[A-Za-z_]", s[0]):
        s = "P" + s
    return s


def _sh_full(cmd, cwd=None, timeout=300):
    """★ `sh` 는 출력을 **400자로 자른다**(원래 오류 꼬리용). 파일 목록을
    받으려면 안 된다 — 잘린 목록으로 세면 파일 수가 엉터리가 된다."""
    p = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True,
                       text=True, timeout=timeout)
    return p.returncode == 0, (p.stdout or "")


def vfiles(d):
    _, out = _sh_full("find . -name '*.v' -not -path './.git/*' -not -path './_opam/*'", cwd=d)
    return [x[2:] if x.startswith("./") else x for x in out.split() if x.endswith(".v")]


def vofiles(d):
    _, out = _sh_full("find . -name '*.vo' -not -path './_opam/*'", cwd=d)
    return [x for x in out.split() if x.endswith(".vo")]


#: 원인 분류 — 첫 Coq 오류 문구로 가른다
def classify(msg):
    m = msg
    if "Invalid character" in m and "identifier" in m:
        return "하네스: 파일명이 Coq 식별자가 아님"
    if re.search(r"Unable to locate library|Cannot find library", m):
        lib = re.search(r"library (\S+)", m)
        return f"의존성 없음: {(lib.group(1) if lib else '?').split('.')[0]}"
    if "Cannot find a physical path" in m:
        return "하네스: 논리경로 매핑 불일치"
    if "The reference" in m and "was not found" in m:
        return "★버전 드리프트: 이름 사라짐"
    if re.search(r"Illegal tactic application|Syntax error|Unexpected token", m):
        return "★버전 드리프트 또는 소스 깨짐: 구문/전술"
    if re.search(r"Universe inconsistency|Cannot infer", m):
        return "★버전 드리프트: 우주/추론"
    if "deprecated" in m.lower():
        return "폐기 경고가 오류로"
    return "기타: " + m[:60]


ERR = re.compile(r'File "([^"]+)", line (\d+)[^\n]*\n(?:[^\n]*\n)?Error:\s*(.+)')
ERR2 = re.compile(r'^Error:\s*(.+)', re.M)

# ── ★ 시동 자가검사 ──────────────────────────────────────────────────────
#   1판이 `-R . Top` 으로 `Top.coq.pierce-lem` 을 만들어 즉사했다.
assert not legal_path("coq/pierce-lem.v"), "하이픈 경로를 걸러야 한다"
assert not legal_path("a b/c.v") and not legal_path("2foo/x.v")
assert legal_path("theories/CFG/CFG_undec.v") and legal_path("Foo.v")
assert sanitize("coq-HoTT") == "coq_HoTT" and sanitize("2x").startswith("P")
assert ERR.search('File "a.v", line 3, characters 1-2:\nError: boom'), "ERR 정규식 어긋남"
assert classify("Invalid character '-' in identifier \"x\".").startswith("하네스")
assert classify("The reference foo was not found").startswith("★")
assert classify("Unable to locate library Coq.Bar").startswith("의존성")


def build(d, proj):
    """저장소 자기 빌드계를 우선한다. 어떤 경로를 탔는지 함께 돌려준다."""
    route = []
    nv = len(vfiles(d))
    # ★ `sh` 는 출력을 400자로 자른다. 그걸로 파일을 세면 조용히 틀린다 —
    #   실제로 673개짜리 저장소를 12개로 셌다. 교차검증한다.
    _n2 = int(subprocess.run("find . -name '*.v' -not -path './.git/*' | wc -l",
                             shell=True, cwd=d, capture_output=True,
                             text=True).stdout.strip() or 0)
    assert nv == _n2 or abs(nv - _n2) <= 2, \
        f"파일 수가 안 맞는다 vfiles={nv} wc={_n2} — 출력 절단을 의심하라"
    has_cfg = os.path.exists(os.path.join(d, "configure"))
    has_mk = any(os.path.exists(os.path.join(d, f))
                 for f in ("Makefile", "makefile", "GNUmakefile"))
    has_cp = os.path.exists(os.path.join(d, "_CoqProject"))
    has_dune = os.path.exists(os.path.join(d, "dune-project"))

    # ── ① 저장소 자기 빌드계 ──────────────────────────────────────────
    if has_cfg:
        ok, msg = sh("chmod +x ./configure && ./configure", cwd=d, timeout=600)
        route.append("configure" + ("" if ok else "✗"))
    if has_mk:
        route.append("자기 Makefile")
    elif has_cp:
        ok, msg = sh("coq_makefile -f _CoqProject -o Makefile", cwd=d, timeout=180)
        route.append("자기 _CoqProject" + ("" if ok else "✗"))
        if not ok: return "makefile 실패", "", nv, 0, route
    elif has_dune:
        route.append("dune (미지원)")
        return "미지원: dune", "", nv, 0, route
    else:
        # ── ② 우리가 만든다 — 합법 경로만, `-Q` 로 ────────────────────
        files = [f for f in vfiles(d) if legal_path(f)]
        dropped = nv - len(files)
        route.append(f"생성 _CoqProject (제외 {dropped}개)")
        if not files:
            return "전부 불법 경로", "", nv, 0, route
        # 최상위 디렉토리마다 -Q 를 건다. 루트 파일은 -Q . <이름>
        tops = sorted({f.split("/")[0] if "/" in f else "." for f in files})
        lines = []
        base = sanitize(proj.split("-")[-1] or proj)
        for t in tops:
            nm = base if t == "." else f"{base}_{sanitize(t)}"
            lines.append(f"-Q {t} {nm}")
        lines += files
        open(os.path.join(d, "_CoqProject"), "w").write("\n".join(lines) + "\n")
        ok, msg = sh("coq_makefile -f _CoqProject -o Makefile", cwd=d, timeout=180)
        if not ok: return "makefile 실패", msg, nv, 0, route

    p = subprocess.run("make -j2 -k", shell=True, cwd=d, capture_output=True,
                       text=True, timeout=PER + 120)
    out = (p.stdout or "") + (p.stderr or "")
    nvo = len(vofiles(d))
    causes = collections.Counter()
    for f, ln, msg in ERR.findall(out): causes[classify(msg)] += 1
    if not causes:
        for msg in ERR2.findall(out): causes[classify(msg)] += 1
    if nvo >= nv and nv > 0: return "완전 빌드", "", nv, nvo, route
    top = causes.most_common(1)[0][0] if causes else "오류 없음/미상"
    return top, out[-400:], nv, nvo, route


if __name__ == "__main__":
    commits = json.load(open("splits/commits.json"))
    projs = db_projects()
    cands = []
    for p, n in projs.most_common():
        o, sha = match_commit(p, commits)
        if o: cands.append((p, o, sha, n))
    print(f"■ db 프로젝트 {len(projs)} · 커밋 매칭 {len(cands)}", flush=True)
    random.seed(0)
    sample = cands[:N // 2] + random.sample(cands[60:], N - N // 2)
    os.makedirs(WORK, exist_ok=True)
    C = collections.Counter(); rows = []; TOTV = TOTVO = 0
    for k, (proj, repo, sha, nf) in enumerate(sample, 1):
        d = os.path.join(WORK, proj); shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d, exist_ok=True)
        # ── ③ 클론 — 길게, 재시도 ─────────────────────────────────────
        ok = False
        for attempt in range(CLONE_TRY):
            sh("git init -q .", cwd=d, timeout=60)
            sh(f"git remote add origin https://github.com/{repo}.git", cwd=d, timeout=60)
            ok, msg = sh(f"git fetch -q --depth 1 origin {sha}", cwd=d, timeout=CLONE_T)
            if ok:
                ok, msg = sh("git checkout -q FETCH_HEAD", cwd=d, timeout=300)
            if ok: break
        if not ok:
            C["클론 실패"] += 1
            rows.append({"proj": proj, "cause": "클론 실패"})
            print(f"   {k:3d}/{len(sample)} {proj[:34]:34s} 클론✗", flush=True)
            shutil.rmtree(d, ignore_errors=True); continue
        try:
            cause, msg, nv, nvo, route = build(d, proj)
        except subprocess.TimeoutExpired:
            cause, msg, nv, nvo, route = "빌드 timeout", "", 0, 0, ["timeout"]
        except Exception as e:
            cause, msg, nv, nvo, route = f"예외: {type(e).__name__}", "", 0, 0, []
        C[cause] += 1; TOTV += nv; TOTVO += nvo
        rows.append({"proj": proj, "repo": repo, "cause": cause,
                     "v": nv, "vo": nvo, "route": route, "err": msg[-200:]})
        print(f"   {k:3d}/{len(sample)} {proj[:34]:34s} {nvo:5d}/{nv:<6d} "
              f"[{' → '.join(route)}] {cause[:44]}", flush=True)
        shutil.rmtree(d, ignore_errors=True)
    with open(OUT, "w") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n■ 2판 결과 (표본 {len(sample)})")
    for c, v in C.most_common(): print(f"   {v:3d}  {c}")
    full = C["완전 빌드"]
    print(f"\n   완전 빌드      {full}/{len(sample)} = {full/len(sample)*100:.1f}%")
    print(f"   파일 컴파일률   {TOTVO}/{TOTV} = {TOTVO/max(TOTV,1)*100:.1f}%"
          f"   (1판 4.6%)")
    drift = sum(v for c, v in C.items() if c.startswith("★"))
    harn = sum(v for c, v in C.items() if c.startswith("하네스") or c == "클론 실패")
    dep = sum(v for c, v in C.items() if c.startswith("의존성"))
    print(f"\n   ④ 원인 갈래:  하네스·클론 {harn} · 의존성 {dep} · ★버전드리프트 {drift}")
    print("TRAIN_V2_DONE", flush=True)
