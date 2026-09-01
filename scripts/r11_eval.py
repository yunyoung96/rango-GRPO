#!/usr/bin/env python3
"""★★ **프로젝트를 넘어서 재현율이 유지되는가** — CompCert 밖에서 잰다.

지금까지 모든 수치는 CompCert 하나였다. 그런데 CompCert 는 rango 의 **held-out**
이고 스타일도 특수하다(대규모 컴파일러 검증, 무거운 모듈·notation). 방법이
프로젝트에 특화된 것인지 일반적인지는 **다른 프로젝트에서 재야** 안다.

컴파일된 저장소가 있는 것만 잰다:
    VAL     graph-theory · coqeal · qarith-stern-brocot · stalmarck · sudoku · bertrand
    CUTOFF  pnvrocqlib · bb5
    TEST    compcert 외 fourcolor · math-classes · buchberger · reglang · poltac · huffman · zfc

지점마다 `applic_check <gold>` 를 돌려 **실제 파이프라인**에서 정답이 살아남는지 본다.

사용: python3 scripts/dn_multi_eval.py [split] [프로젝트당_정리수]
"""
import concurrent.futures as cf
import collections, json, os, re, signal, subprocess, sys, tempfile, logging
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")
os.environ["CUDA_VISIBLE_DEVICES"] = ""
sys.path.insert(0, "src"); sys.path.insert(0, "CoqStoq")
logging.disable(logging.CRITICAL)
from pathlib import Path
from coqstoq import Split, get_theorem_list
from data_management.sentence_db import SentenceDB
from evaluation.find_coqstoq_idx import get_thm_desc

SPLIT_NAME = sys.argv[1] if len(sys.argv) > 1 else "VAL"
PER_PROJ = int(sys.argv[2]) if len(sys.argv) > 2 else 25
JOBS = 2
TIMEOUT = 2400
MAX_PT = 3
#: ★ `-in` 표적 표집 — 세 번째 인자로 켠다 (`… VAL 25 focus_in`)
FOCUS_IN = (sys.argv[3] if len(sys.argv) > 3 else "") == "focus_in"
#: ★★ `only_in` — **`-in` 스텝이 있는 정리만** 모은다. apply-in·rewrite-in 은
#   전체의 2~6% 라 focus_in(정리는 균등, 스텝만 -in 우선)으로도 VAL 7건이
#   전부였다. 표본을 불리려면 정리 선별부터 -in 으로 걸러야 한다.
ONLY_IN = (sys.argv[3] if len(sys.argv) > 3 else "") == "only_in"
if ONLY_IN: FOCUS_IN = True
#: ★ 프로젝트 필터 — 네 번째 인자. `-coqeal,-graph-theory` 면 제외,
#   `coqeal,fourcolor` 면 그것만. mathcomp 은 후보 ~35,000개라 정리당
#   30분+ 걸려 나머지를 막는다(실측: 2시간 40분 정체). 나눠서 돌린다.
_PF = (sys.argv[4] if len(sys.argv) > 4 else "").strip()
_ONLY = {x for x in _PF.split(",") if x and not x.startswith("-")}
_SKIP = {x[1:] for x in _PF.split(",") if x.startswith("-")}


def proj_ok(name):
    if _ONLY: return name in _ONLY
    return name not in _SKIP
_TAG = ("onlyin" if ONLY_IN else "in" if FOCUS_IN else "") \
    + ("_" + _PF.replace(",", "").replace("-", "") if _PF else "")
OUT = f"all_log/r11_pool{_TAG}_{SPLIT_NAME.lower()}.jsonl"
PLUG = os.path.abspath("ocaml/applic")

_SPLIT = {"VAL": Split.VAL, "CUTOFF": Split.CUTOFF, "TEST": Split.TEST}[SPLIT_NAME]
_DIR = {"VAL": "val-repos", "CUTOFF": "cutoff-repos", "TEST": "test-repos"}[SPLIT_NAME]
_DATA = {"VAL": "raw-data/coqstoq-val", "CUTOFF": "raw-data/coqstoq-cutoff",
         "TEST": "raw-data/coqstoq-test"}[SPLIT_NAME]
_SDB = {"VAL": "raw-data/coqstoq-val/coqstoq-val-sentences.db",
        "CUTOFF": "raw-data/coqstoq-cutoff/coqstoq-cutoff-sentences.db",
        "TEST": "raw-data/coqstoq-test/coqstoq-test-sentences.db"}[SPLIT_NAME]

sdb = SentenceDB.load(Path(_SDB))
NAMED = re.compile(r"\b(?:e?apply|e?rewrite|unfold|destruct|induction|case|elim"
                   r"|e?exact)\s+(?:<-\s*)?\(?\s*"
                   r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
HEADT = re.compile(r"^\s*(?:now\s+|try\s+|repeat\s+)?([A-Za-z_][\w']*)")
CHK = re.compile(r"CHECK\s+ver=(\S+)\s+(\S+)\s+ap=(\d)\s+in=(\d)\s+rw=(\d)")
HYPL = re.compile(r"(?m)^HYPS ?(.*)$")
GBL = re.compile(r"(?m)^GBIND ?(.*)$")
_SAMPLE = "CHECK ver=r9 PTree.gso ap=1 in=1 rw=1 dnA=1"
assert CHK.search(_SAMPLE), "CHECK 정규식이 실제 출력과 어긋난다"


def proj_args(pdir):
    """프로젝트의 `_CoqProject` 에서 로드 경로를 만든다.

    ★ 루트에 없으면 **한 단계 아래도** 찾는다 — undecidability 는
    `theories/_CoqProject` (`-Q . Undecidability`) 다. 예전 폴백 `-R . ""` 은
    `From Undecidability Require` 를 조용히 죽여 head 의 정의가 실종되고,
    이후 증명이 열린 채 다음 정리로 흘러 **오염된 상태**를 수집했다
    (실측: four_squares_zero 지점의 문맥이 Zsquare_bound 내부였다)."""
    cands = [os.path.join(pdir, "_CoqProject")]
    try:
        for d in sorted(os.listdir(pdir)):
            sub = os.path.join(pdir, d, "_CoqProject")
            if os.path.isdir(os.path.join(pdir, d)) and os.path.exists(sub):
                cands.append(sub)
    except OSError: pass
    args = []
    for cp in cands:
        if not os.path.exists(cp): continue
        base = os.path.dirname(cp)
        t = open(cp).read().split(); i = 0
        while i < len(t):
            if t[i] in ("-R", "-Q") and i + 2 < len(t):
                args += [t[i], os.path.abspath(os.path.join(base, t[i+1])), t[i+2]]
                i += 3
            else: i += 1
        if args: break
    if not args:
        args = ["-R", os.path.abspath(pdir), ""]
    # ★ 매핑 경로는 실존해야 한다 — 깨진 -Q/-R 은 Require 전멸(조용)로 이어진다
    for j in range(0, len(args), 3):
        assert os.path.isdir(args[j + 1]), f"논리경로 대상 없음: {args[j+1]}"
    return args + ["-R", PLUG, "Applic", "-I", PLUG]


# ── ★ 자식 coqtop 메모리 상한 ────────────────────────────────────────────
#   실측: CompCert `backend/Kildall.v` 의 `reachable_predecessors` 하나가
#   coqtop 을 112GB 까지 키워 기계를 마비시켰다(45정리 중 1건뿐).
#   상한을 걸면 그 정리만 죽고 나머지는 정상 수집된다.
_MEM_CAP_GB = 12


def _memcap():
    import resource
    b = _MEM_CAP_GB * 1024 ** 3
    resource.setrlimit(resource.RLIMIT_AS, (b, b))


def _coqtop(cmd, stdin=None, env=None, timeout=None, with_err=False):
    """★ stderr 를 **버리지 않는다** — undec 오염 사태의 공범이 stderr 폐기였다
    (Require 전멸·destruct 실패가 전부 stderr 로 가서 무증상). 기본 반환은
    기존 호환(out)이고, with_err=True 면 (out, err) 를 준다."""
    p = subprocess.Popen(cmd, stdin=stdin, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True, env=env,
                         start_new_session=True, preexec_fn=_memcap)
    try:
        out, err = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try: os.killpg(os.getpgid(p.pid), signal.SIGKILL)
        except Exception: pass
        p.wait(); raise
    return (out or "", err or "") if with_err else (out or "")


def head_by_pos(orig, thm):
    ln = getattr(getattr(thm, "theorem_start_pos", None), "line", None)
    if not ln: return None
    parts = orig.splitlines(keepends=True)
    return "".join(parts[:ln - 1]) if ln - 1 <= len(parts) else None



# ── ★ 채널 라인 파싱 (r11: ap · in · rw · rwh) ───────────────────────────
#   ★ `DNRWH` 를 `DNRW` 보다 **앞**에 둔다 — 뒤에 두면 정규식이 `DNRW` 로
#     맞춘 뒤 공백을 못 찾아 줄 전체를 버린다(실측: 가설 rewrite 147개 실종).
LINE = re.compile(r"(?m)^(APPLICIN|APPLIC|DNRWH|DNRW|UNFOLD|DESTRUCT|DECIDE) ([\w'.]+)"
                  r"((?: \w+=-?\d+)*)(?: :: (.*))?$")
_CH = {"APPLIC": "ap", "APPLICIN": "in", "DNRW": "rw", "DNRWH": "rwh",
       "UNFOLD": "uf", "DESTRUCT": "ds", "DECIDE": "dc"}
STAT = re.compile(r"APPLIC_STAT\s+ver=(\S+)\s+cand=(\d+)")
# ── ★ 시동 자가검사 — 조용한 0 을 막는다 ─────────────────────────────────
for _t, _c in _CH.items():
    _m = LINE.search(f"{_t} PTree.gso lgg=15 g=20")
    assert _m and _CH[_m.group(1)] == _c, f"{_t} 파싱 실패 — 교대 순서를 의심하라"
assert STAT.search("APPLIC_STAT ver=r11 cand=989 pat=5636"), "STAT 정규식 어긋남"
assert CHK.search("CHECK ver=r11 x ap=1 in=0 rw=1 dnA=1"), "CHECK 정규식 어긋남"


#: ★ gold 를 **네 형태**로 나눈다. `apply L` 과 `apply L in H` 는 **다른 채널**이
#   답을 갖고 있으므로 뭉뚱그리면 어느 쪽이 약한지 안 보인다.
#     apply      → ap    결론을 goal 과 맞춘다
#     apply-in   → in    비의존 전제를 **가설**과 맞춘다
#     rewrite    → rw    등식 한 변이 **goal** 부분항과 맞는다
#     rewrite-in → rwh   등식 한 변이 **가설** 부분항과 맞는다
_INRE = re.compile(r"\bin\b\s+[A-Za-z_*]")


def _strip_parens(t):
    """괄호 안을 지운다 — `rewrite x by (auto in H).` 의 `in` 은 절이 아니다."""
    out = []; d = 0
    for ch in t:
        if ch == "(": d += 1
        elif ch == ")": d = max(0, d - 1)
        elif d == 0: out.append(ch)
    return "".join(out)


def tac_form(text):
    t = " ".join((text or "").split())
    h = HEADT.match(t)
    h = h.group(1) if h else ""
    # ★ `in` 절은 **최상위**에서, 첫 `;`·` by ` 앞에서만 본다.
    #   괄호 안(`by (auto in H)`)이나 뒤 전술(`; rewrite y in H`)의 `in` 은
    #   이 스텝의 형태와 무관하다. assert 가 실제로 이 오분류를 잡았다.
    seg = _strip_parens(t).split(";")[0].split(" by ")[0]
    has_in = bool(_INRE.search(seg))
    if h.endswith("rewrite"):
        return "rewrite-in" if has_in else "rewrite"
    if h in ("apply", "eapply"):
        return "apply-in" if has_in else "apply"
    return h


#: gold 형태 → 그 답이 있어야 할 채널 (조인 매핑)
FORM_CH = {"apply": ("ap",), "apply-in": ("in",),
           "rewrite": ("rw",), "rewrite-in": ("rwh",)}
#: 검색 시점에는 형태를 모른다 — 넷을 다 쓴다
ALL4 = ("ap", "in", "rw", "rwh")

assert tac_form("apply foo.") == "apply"
assert tac_form("apply foo in H.") == "apply-in"
assert tac_form("rewrite bar.") == "rewrite"
assert tac_form("rewrite <- bar in H1.") == "rewrite-in"
assert tac_form("eapply baz; eauto.") == "apply"
assert tac_form("rewrite x by (auto in H).") == "rewrite"     # 괄호 안은 무시
assert tac_form("rewrite x in H by auto.") == "rewrite-in"    # 진짜 in 절
assert tac_form("apply L; rewrite y in H.") == "apply"        # 뒤 전술은 무시
assert tac_form("rewrite foo in *.") == "rewrite-in"


#: ★ mathcomp 계열 — 등식을 `associative`·`commutative` 같은 **정의 뒤에 숨긴다**.
#   `ApplicDelta 1` 로 열어야 잡히는데 점당 2초 → 46초로 비싸다.
#   그래서 **이 프로젝트들에서만** 켠다. 나머지는 그대로 빠르다.
#   (mathcomp 은 VAL/TEST 의 각 ~20%, TRAIN 엔 0%다.)
#   ★ 실측으로 **껐다.** δ 는 조회뿐 아니라 **색인 구축**을 터뜨린다 —
#   mathcomp 은 후보가 ~35,000개고 타입마다 `whd_all` 을 하면 정리당 25분+.
#   VAL 150 · TEST 236 정리를 이 속도로는 못 돈다(며칠).
#   단일 지점 효과는 확인됐다(`inE`·`mulrA` 잡힘) — 규모가 문제다.
MATHCOMP = set()


def run(job):
    proj, path, head, thm_text, chunks, ks, golds, tacs, texts, tpath, thmi = job
    env = dict(os.environ)
    env["OCAMLPATH"] = os.path.join(PLUG, "findlib") + ":" + env.get("OCAMLPATH", "")
    # ★ 진술문을 켠다. 이게 없으면 `stmts` 가 비고 → `lex`·`slen`·`nbind`·`nsym`
    #   특징이 통째로 죽는다(실측: 167지점 전부 stmts 0개).
    body = ["Require Import Applic.", "ApplicPrintTypes 1."]
    if os.path.basename(proj) in MATHCOMP:
        body.append("ApplicDelta 1.")
    body += [head, thm_text]; prev = 0
    for k in ks:
        body.append(chunks[prev]); body.append(f'idtac "@@@{k}".')
        body.append("try applic_filter.")
        if golds.get(k): body.append(f"try applic_check {golds[k]}.")   # 무참조 스텝(gold 없음)은 필터만
        prev = k
    body.append("Admitted.")
    d = os.path.dirname(os.path.abspath(path))
    with tempfile.NamedTemporaryFile("w", suffix=".v", dir=d, delete=False) as f:
        f.write("\n".join(body) + "\n"); tmp = f.name
    try:
        out, oerr = _coqtop(["coqtop", "-q"] + proj_args(proj), stdin=open(tmp),
                            env=env, timeout=TIMEOUT, with_err=True)
        #: ★ 재생 오류 수 — 0 이 아니면 그 정리의 지점들은 상태가 이탈했을 수
        #   있다. 행에 실어 분석에서 걸러낼 수 있게 한다 (undec 오염 교훈).
        nerr = oerr.count("Error:")
        blocks = re.split(r"@@@(\d+)\s*", out); recs = []
        for a in range(1, len(blocks) - 1, 2):
            k = int(blocks[a]); seg = blocks[a + 1]
            chan, sig, stmts = collections.defaultdict(list), {}, {}
            # ★ 채널별 신호 — 한 lemma 가 ap·rw 에 다 나오면 예전엔 마지막
            #   줄이 **통째로 덮어써** ap 의 lgg 가 사라졌다. 채널별로 보관하고
            #   `sig` 는 병합(update)으로 남긴다(구버전 호환).
            sigc = collections.defaultdict(dict)
            for tag, nm, sg, ty in LINE.findall(seg):
                c_ = _CH[tag]
                chan[c_].append(nm)
                if ty: stmts[nm] = ty.strip()
                if sg.strip():
                    d_ = dict(x.split("=") for x in sg.split())
                    sigc[c_][nm] = d_
                    sig.setdefault(nm, {}).update(d_)
            st = STAT.search(seg); m = CHK.search(seg)
            hm = HYPL.search(seg); gm = GBL.search(seg)
            loc = ((hm.group(1).split() if hm else [])
                   + (gm.group(1).split() if gm else []))
            if not chan and not m: continue
            # ★ 일관성: CHECK 비트가 1 인데 해당 채널 목록에 gold 가 없으면
            #   파싱이 깨진 것이다 (DNRWH 교대 순서 사고의 재발 방지).
            if m:
                for bit, cname in ((int(m.group(3)), "ap"),
                                   (int(m.group(4)), "in")):
                    if bit:
                        _cl = set(chan.get(cname, []))
                        _gb = golds[k].split(".")[-1]
                        assert (golds[k] in _cl
                                or any(x.split(".")[-1] == _gb for x in _cl)), \
                            f"CHECK {cname}=1 인데 채널에 gold 없음: {golds[k]}"
            recs.append({"proj": os.path.basename(proj), "k": k,
                         "rerr": nerr,
                         "ver": st.group(1) if st else (m.group(1) if m else "?"),
                         "cand": int(st.group(2)) if st else 0,
                         "gold": golds[k], "local": golds[k] in set(loc),
                         "tac": tacs.get(k, "?"),
                         "gold_text": texts.get(k, ""),
                         "thm": tpath, "thmi": thmi,
                         "chan": {c: sorted(set(v)) for c, v in chan.items()},
                         "sig": sig, "sigc": dict(sigc), "stmts": stmts,
                         "ap": int(m.group(3)) if m else 0,
                         "in": int(m.group(4)) if m else 0,
                         "rw": int(m.group(5)) if m else 0})
        return recs
    except Exception as e:
        return []
    finally:
        b = os.path.splitext(tmp)[0]
        for e in (".v", ".vo", ".vok", ".vos", ".glob"):
            try: os.unlink(b + e)
            except OSError: pass

if __name__ == "__main__":
    thms = get_theorem_list(_SPLIT, Path("CoqStoq"))
    byp = collections.defaultdict(list)
    for t in thms: byp[str(t.project.dir_name)].append(t)
    jobs = []
    for proj, ts in sorted(byp.items()):
        if not proj_ok(proj): continue
        pdir = os.path.join("CoqStoq", _DIR, proj)
        if not os.path.isdir(pdir): continue
        if not any(True for _ in Path(pdir).rglob("*.vo")): continue
        got = 0
        for i0, thm in enumerate(ts):
            if got >= PER_PROJ: break
            try:
                d = get_thm_desc(thm, Path(_DATA), sdb)
                if d is None: continue
                proof = d.dp.proofs[d.idx]
                path = os.path.join(pdir, str(thm.path))
                orig = open(path, errors="ignore").read()
                head = head_by_pos(orig, thm)
            except Exception:
                continue
            if head is None: continue
            ks = [k for k, s in enumerate(proof.steps)
                  if HEADT.match(s.step.text or "")
                  and HEADT.match(s.step.text).group(1) in (
                      "apply", "eapply", "rewrite", "erewrite", "unfold",
                      "destruct", "induction", "case", "elim", "exact", "eexact")
                  and NAMED.search(s.step.text or "") and s.goals]
            if not ks: continue
            if ONLY_IN:
                _ins = [k for k in ks if tac_form(proof.steps[k].step.text or "")
                        in ("apply-in", "rewrite-in")]
                if not _ins: continue
                ks = _ins[:6]          # -in 스텝만, 정리당 최대 6
            # ★ `-in` 표적 표집 — `apply … in H` · `rewrite … in H` 는 전체의
            #   2~6% 뿐이라(VAL/TEST 전수), 균등 표집으로는 표본이 안 모인다.
            #   실측: CompCert 178지점에서 apply-in 3건 · rewrite-in 5건.
            #   `FOCUS_IN=1` 이면 `-in` 스텝을 **먼저** 채우고 남는 자리를 균등으로.
            if len(ks) > MAX_PT:
                if FOCUS_IN:
                    _in = [k for k in ks if tac_form(proof.steps[k].step.text or "")
                           in ("apply-in", "rewrite-in")]
                    _rest = [k for k in ks if k not in set(_in)]
                    take = _in[:MAX_PT]
                    if len(take) < MAX_PT and _rest:
                        need = MAX_PT - len(take)
                        stp = len(_rest) / need
                        take += [_rest[int(x * stp)] for x in range(need)]
                    ks = sorted(set(take))
                else:
                    stp = len(ks)/MAX_PT; ks = [ks[int(x*stp)] for x in range(MAX_PT)]
            steps = [s.step.text for s in proof.steps]
            chunks, prev = {}, 0
            for k in ks: chunks[prev] = "".join(steps[prev:k]); prev = k
            golds = {k: NAMED.search(proof.steps[k].step.text).group(1) for k in ks}
            # ★ gold tactic 을 **작업과 함께** 실어 보낸다.
            #   전역 dict 에 스텝 번호로만 넣으면 정리끼리 덮어쓴다.
            tacs = {}; texts = {}
            for _k in ks:
                _t = proof.steps[_k].step.text or ""
                texts[_k] = " ".join(_t.split())
                tacs[_k] = tac_form(_t)
            jobs.append((pdir, path, head, proof.theorem.term.text,
                         chunks, ks, golds, tacs, texts, str(thm.path), i0))
            got += 1
    assert jobs, "정리를 하나도 못 골랐다 — 컴파일된 저장소가 있는지 확인하라"
    print(f"■ {SPLIT_NAME} · 정리 {len(jobs)} · 프로젝트 "
          f"{len({j[0] for j in jobs})} · 병렬 {JOBS}", flush=True)
    S = collections.defaultdict(collections.Counter); nrec = 0
    with open(OUT, "w") as fo, cf.ThreadPoolExecutor(JOBS) as ex:
        for n, recs in enumerate(ex.map(run, jobs)):
            for r in recs:
                nrec += 1
                if r["local"]:
                    S[r["proj"]]["지역"] += 1; continue
                S[r["proj"]]["지점"] += 1
                S[r["proj"]]["생존"] += bool(r["ap"] or r["in"] or r["rw"])
                fo.write(json.dumps(r, ensure_ascii=False) + "\n")
            if (n+1) % 10 == 0:
                print(f"   … {n+1}/{len(jobs)} · 기록 {nrec}", flush=True)
            fo.flush()
    print(f"\n■ 프로젝트별 gold 생존 (실제 파이프라인 · 지역변수 인자 제외)")
    print(f"   {'프로젝트':24s}{'지점':>7s}{'생존':>9s}{'지역제외':>9s}")
    tot = collections.Counter()
    for p, c in sorted(S.items(), key=lambda x: -x[1]["지점"]):
        n = max(1, c["지점"])
        print(f"   {p:24s}{c['지점']:7d}{c['생존']/n*100:8.1f}%{c['지역']:9d}")
        tot["지점"] += c["지점"]; tot["생존"] += c["생존"]; tot["지역"] += c["지역"]
    n = max(1, tot["지점"])
    print(f"   {'—— 합계':24s}{tot['지점']:7d}{tot['생존']/n*100:8.1f}%{tot['지역']:9d}")

    # ── ★ 2단: 필터링 비율 · gold 포함 · 랭킹 @K ────────────────────────────
    #   ★ only_in 보강 수집에선 건너뛴다 — -in 형태만 있어 겹 양성이 0인
    #     겹이 생기고 train_nb assert 가 (맞게) 발화한다. 분석은 pretty_rank 가.
    if ONLY_IN:
        print(f"R11_{SPLIT_NAME}_DONE", flush=True); sys.exit(0)
    #   ★ gold 를 **네 형태**로 나눠 본다 (apply / apply-in / rewrite / rewrite-in).
    #     검색 시점에는 형태를 모르므로 **풀은 항상 네 채널 합집합**이다.
    #     형태별 표는 "어느 형태가 약한가" 를 보려는 진단이다.
    import statistics as _st
    sys.path.insert(0, "scripts")
    import applic_rank as AR
    rows = [json.loads(l) for l in open(OUT)]
    rows = [r for r in rows if r.get("gold") and not r.get("local")]
    assert rows, "2단: 평가할 행이 없다"
    FORMS = ("apply", "apply-in", "rewrite", "rewrite-in")
    # ★★ `idf` 를 여기서 굽지 않는다 — **겹마다** 학습 겹으로만 만든다.
    #   `build_idf` 는 gold 을 안 보지만 "각 lemma 가 몇 %의 지점에서 필터를
    #   통과하나" 를 세므로, 평가 지점까지 세면 **평가 데이터를 훑는 것**이다.
    #   실측(VAL): 전체 idf 로 재면 @10 74.5%, 겹 idf 로 재면 **36.4%**.
    #   그 38pp 가 통째로 누출이었다.
    idf_all, cnt, nidf = AR.build_idf(rows)   # ① 필터 표 출력용(랭킹엔 안 씀)

    # ★ `lex`·`nov` 를 붙인다 — 학습 가중치 **2·3위** 특징이라 빠지면 크게 손해다.
    #   goal 텍스트가 필요해서 여기서만 만들 수 있다(플러그인은 항만 다룬다).
    #   토큰 idf 는 겹마다 다시 구우므로 여기서는 **goal 토큰만** 저장한다.
    _byp = collections.defaultdict(list)
    for _t in get_theorem_list(_SPLIT, Path("CoqStoq")):
        _byp[str(_t.project.dir_name)].append(_t)
    _cache = {}; _ok = 0
    for r in rows:
        try:
            _key = (r["proj"], r["thmi"])
            if _key not in _cache:
                _cache[_key] = get_thm_desc(_byp[r["proj"]][r["thmi"]],
                                            Path(_DATA), sdb)
            _d = _cache[_key]
            _gs = _d.dp.proofs[_d.idx].steps[r["k"]].goals if _d else None
            _gl = _gs[0] if _gs else ""
            _gl = _gl if isinstance(_gl, str) else (getattr(_gl, "goal", "") or "")
        except Exception:
            _gl = ""
        _gt = set(AR._TOK.findall(_gl))
        r["_gt"] = sorted(_gt)
        _gn = set()
        for _x in _gt: _gn |= AR._name_toks(_x)
        r["gnames"] = sorted(_gn)
        if _gt: _ok += 1
    assert _ok >= 0.5 * len(rows), f"goal 텍스트를 {_ok}/{len(rows)} 에만 붙였다"
    print(f"■ goal 토큰 부착 {_ok}/{len(rows)}", flush=True)

    def chan_of_row(r):
        d = {}
        for ch in AR.ALL_CH:
            for x in (r.get("chan") or {}).get(ch, []): d.setdefault(x, ch)
        return d

    def has(r, chs):
        g = r["gold"]; gb = g.split(".")[-1]
        for c in chs:
            for x in (r.get("chan") or {}).get(c, []):
                if x == g or x.split(".")[-1] == gb: return True
        return False

    def pool_of(r, chs=ALL4):
        s = set()
        for c in chs: s |= set((r.get("chan") or {}).get(c, []))
        return s

    # ── ① 필터 — 형태별 회수율 + **자기 채널** 회수율 ──────────────────
    print(f"\n■ {SPLIT_NAME} · r11 필터 (풀 = 네 채널 합집합 {'/'.join(ALL4)})")
    print(f"   {'gold 형태':12s}{'지점':>6s}{'우주중앙':>9s}{'필터후':>8s}{'축소':>7s}"
          f"{'합집합회수':>10s}{'자기채널':>9s}   자기채널")
    tot = collections.Counter()
    for f in FORMS + ("기타",):
        sub = [r for r in rows if (r.get("tac") == f if f != "기타"
                                   else r.get("tac") not in FORMS)]
        if not sub: continue
        chs = FORM_CH.get(f, ALL4)
        u = [len(pool_of(r)) for r in sub]
        uni = [r["cand"] for r in sub if r.get("cand")] or [0]
        hu = sum(1 for r in sub if has(r, ALL4))
        ho = sum(1 for r in sub if has(r, chs))
        tot["n"] += len(sub); tot["hu"] += hu
        print(f"   {f:12s}{len(sub):6d}{_st.median(uni):9,.0f}{_st.median(u):8,.0f}"
              f"{(_st.median(uni)/max(_st.median(u),1)):6.1f}배"
              f"{hu/len(sub)*100:9.1f}%{ho/len(sub)*100:8.1f}%   {'/'.join(chs)}")
    print(f"   {'—— 4형태 합':12s}{tot['n']:6d}{'':9s}{'':8s}{'':7s}"
          f"{tot['hu']/max(tot['n'],1)*100:9.1f}%")

    # ── ② 랭킹 — 프로젝트 단위 leave-one-out ────────────────────────────
    projs = sorted({r["proj"] for r in rows})
    RK = collections.defaultdict(list); N = collections.Counter()
    for p in projs:
        tr = [r for r in rows if r["proj"] != p]
        te = [r for r in rows if r["proj"] == p]
        if not tr or not te: continue
        idf, _, _ = AR.build_idf(tr)          # ★ 학습 겹만
        # ★ 토큰 idf 도 학습 겹 진술문만으로
        _df = collections.Counter(); _nd = 0
        for _r in tr:
            for _s in (_r.get("stmts") or {}).values():
                if _s:
                    _nd += 1
                    for _t in set(AR._TOK.findall(_s)): _df[_t] += 1
        import math as _m
        _tidf = {t: _m.log((_nd + 1.0) / (v + 1.0)) for t, v in _df.items()}
        for _r in rows:
            _g2 = set(_r.get("_gt") or [])
            _r["lex"] = {n2: AR.lex_overlap(s2, _g2, _tidf)
                         for n2, s2 in (_r.get("stmts") or {}).items() if s2}
        assert idf, f"겹 {p}: 학습 겹 idf 가 비었다"
        W, _np, _ = AR.train_nb(tr, idf, lambda t: ALL4)
        assert _np > 0, f"겹 {p}: 양성 표본 0"
        for r in te:
            f = r.get("tac")
            if f not in FORMS: continue
            N[f] += 1; N["전체"] += 1
            # ★★ **채널 안에서** 정렬한다. 합쳐서 정렬하면 큰 채널이 작은
            #   채널을 덮는다 — 실측(CompCert) rewrite @10 75.4% → 38.6%.
            #   프롬프트도 채널별 블록으로 나갈 것이므로 이게 맞는 측정이다.
            g = r["gold"]; gb = g.split(".")[-1]
            sig = r.get("sig") or {}
            SC = AR.sig_by_chan(r)                  # ★ 채널별 신호로 정렬
            gsz = float((list(sig.values()) or [{}])[0].get("g", 1) or 1)
            sc = AR.nb_score_fn(W, idf, chan_of_row(r), r.get("lex"),
                                set(r.get("gnames") or []))
            best = None
            for c in ALL4:
                _cs = SC.get(c, sig)
                v = sorted(set((r.get("chan") or {}).get(c, [])),
                           key=lambda x: (-sc(x, _cs, idf, gsz), x))
                p_ = next((i + 1 for i, x in enumerate(v)
                           if x == g or x.split(".")[-1] == gb), None)
                if p_ is not None and (best is None or p_ < best): best = p_
            if best is not None:
                RK[f].append(best); RK["전체"].append(best)
    print(f"\n■ {SPLIT_NAME} · 나이브베이즈 · **채널 안에서 정렬** "
          f"(프로젝트 leave-one-out · 분모=전체지점)")
    print(f"   {'gold 형태':12s}{'지점':>6s}{'@5':>8s}{'@10':>8s}{'@20':>8s}"
          f"{'@50':>8s}{'@100':>8s}{'순위중앙':>9s}")
    for f in ("전체",) + FORMS:
        v = RK[f]; n = N[f]
        if not n: continue
        print(f"   {f:12s}{n:6d}"
              + "".join(f"{sum(1 for x in v if x <= K)/n*100:7.1f}%" for K in (5,10,20,50,100))
              + f"{(_st.median(v) if v else 0):9,.0f}")
    print(f"\nR11_{SPLIT_NAME}_DONE", flush=True)
