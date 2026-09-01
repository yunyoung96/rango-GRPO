#!/usr/bin/env python3
"""★ TRAIN 빌드가 **왜** 실패하나 — make 꼬리가 아니라 **첫 Coq 오류**를 잡는다.

앞선 `train_build_probe.py` 는 실패 사유로 `make: *** Error 2` 같은 꼬리만
남겼다. 그걸로는 "Coq 버전이 안 맞아서" 인지 "우리 하네스가 틀려서" 인지
구분할 수 없다. 실제로 표본 하나를 열어 보니 둘 다 **버전 문제가 아니었다**:

    Invalid character '-' in identifier "pierce-lem"
        → `-R . Top` 이 `Top.coq.pierce-lem` 을 만든다. **하네스 탓**이다.
    Illegal tactic application: got 1 extra argument
        → 소스에 `cut` 다음 인자가 비어 있다. **저장소에 깨진 파일**이 커밋돼 있다.

그래서 원인을 다시 센다. 사용: python3 scripts/train_build_why.py [표본수]
"""
import collections, json, os, random, re, shutil, subprocess, sys

N = int(sys.argv[1]) if len(sys.argv) > 1 else 12
WORK = "/tmp/claude-0/-app-coq-modeling/e02d0688-7cb1-43a8-aa0e-ee8afd60ce19/scratchpad/why"
PER = 900
OUT = "all_log/train_build_why.jsonl"

sys.path.insert(0, "scripts")
from train_build_probe import db_projects, match_commit, sh   # 클론·매칭은 재사용

#: 첫 오류만 뽑는다 — `File "…", line N …  Error: …`
ERR = re.compile(r'File "([^"]+)", line (\d+)[^\n]*\n(?:[^\n]*\n)?Error:\s*(.+)')
ERR2 = re.compile(r'^Error:\s*(.+)', re.M)

#: 원인 분류 — 문구로 가른다
def classify(msg, path):
    m = msg
    if "Invalid character" in m and "identifier" in m:
        return "하네스: 파일명이 Coq 식별자가 아님(-R . Top)"
    if "Cannot find a physical path" in m or "cannot find" in m.lower() and ".vo" in m:
        return "하네스: 논리경로 매핑 불일치"
    if re.search(r"Unable to locate library|Cannot find library", m):
        lib = re.search(r"library (\S+)", m)
        return f"의존성 없음: {lib.group(1) if lib else '?'}"
    if "The reference" in m and "was not found" in m:
        return "이름 없음(버전 드리프트 또는 의존성)"
    if re.search(r"Illegal tactic application|Syntax error|Unexpected token", m):
        return "구문/전술 오류(소스 깨짐 또는 버전 드리프트)"
    if "deprecated" in m.lower():
        return "폐기 경고가 오류로"
    return "기타: " + m[:60]

if __name__ == "__main__":
    commits = json.load(open("splits/commits.json"))
    projs = db_projects()
    cands = []
    for p, n in projs.most_common():
        o, sha = match_commit(p, commits)
        if o: cands.append((p, o, sha, n))
    random.seed(1)
    sample = cands[:N // 2] + random.sample(cands[60:], N - N // 2)
    os.makedirs(WORK, exist_ok=True)
    C = collections.Counter(); rows = []
    for k, (proj, repo, sha, nf) in enumerate(sample, 1):
        d = os.path.join(WORK, proj); shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d, exist_ok=True)
        ok = (sh("git init -q .", cwd=d, timeout=30)[0]
              and sh(f"git remote add origin https://github.com/{repo}.git", cwd=d, timeout=30)[0])
        if ok: ok, msg = sh(f"git fetch -q --depth 1 origin {sha}", cwd=d, timeout=420)
        if ok: ok, msg = sh("git checkout -q FETCH_HEAD", cwd=d, timeout=180)
        if not ok:
            C["클론 실패"] += 1; rows.append({"proj": proj, "cause": "클론 실패"})
            print(f"   {k:3d}/{len(sample)} {proj[:36]:36s} 클론✗", flush=True)
            shutil.rmtree(d, ignore_errors=True); continue
        had_cp = os.path.exists(os.path.join(d, "_CoqProject"))
        if not had_cp:
            sh("find . -name '*.v' -not -path './.git/*' > _f && "
               "{ echo '-R . Top'; cat _f; } > _CoqProject", cwd=d)
        okm, _ = sh("coq_makefile -f _CoqProject -o Makefile", cwd=d, timeout=120)
        if not okm:
            C["makefile 실패"] += 1; rows.append({"proj": proj, "cause": "makefile 실패"})
            shutil.rmtree(d, ignore_errors=True); continue
        # -k 로 끝까지 가서 **모든** 오류를 모은다
        p = subprocess.run("make -j2 -k", shell=True, cwd=d, capture_output=True,
                           text=True, timeout=PER + 60) if True else None
        out = (p.stdout or "") + (p.stderr or "")
        nv = int(sh("find . -name '*.v' -not -path './.git/*' | wc -l", cwd=d)[1].strip() or 0)
        nvo = int(sh("find . -name '*.vo' | wc -l", cwd=d)[1].strip() or 0)
        causes = collections.Counter()
        for f, ln, msg in ERR.findall(out):
            causes[classify(msg, f)] += 1
        if not causes:
            for msg in ERR2.findall(out): causes[classify(msg, "")] += 1
        top = causes.most_common(1)[0][0] if causes else ("완전 빌드" if nvo >= nv else "오류 없음/미상")
        C[top] += 1
        rows.append({"proj": proj, "repo": repo, "had_coqproject": had_cp,
                     "v": nv, "vo": nvo, "cause": top,
                     "causes": dict(causes)})
        print(f"   {k:3d}/{len(sample)} {proj[:36]:36s} {nvo:4d}/{nv:<5d} {top[:52]}", flush=True)
        shutil.rmtree(d, ignore_errors=True)
    with open(OUT, "w") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n■ 실패 원인 분포 (표본 {len(sample)})")
    for k, v in C.most_common():
        print(f"   {v:3d}  {k}")
    nhad = sum(1 for r in rows if r.get("had_coqproject"))
    print(f"\n   _CoqProject 가 원래 있던 프로젝트 {nhad}/{len(rows)}"
          f"  (없으면 우리가 `-R . Top` 으로 만든다 — 그 자체가 실패 원인이 된다)")
    print("TRAIN_WHY_DONE", flush=True)
