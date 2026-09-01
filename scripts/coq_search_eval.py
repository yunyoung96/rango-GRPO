#!/usr/bin/env python3
"""★★★ **Coq 안에서** 적용가능성 색인을 쓴다 — `SearchPattern` / `SearchRewrite`.

## 왜 이것인가

바깥에서 만든 색인 8판본이 전부 gold 를 흘렸다(applicability-filter.md §4.10).
남은 벽이 **변환(delta/iota/beta)** 이었고, 그건 Coq 커널이 있어야 넘는다.
그런데 **Coq 이 이미 그 색인을 갖고 있다**:

    SearchPattern <패턴>   결론이 패턴과 매칭되는 lemma  → `apply` 후보
    SearchRewrite <항>     한 변이 그 항과 매칭되는 등식 → `rewrite` 후보

elaboration·변환·강제변환·타입클래스가 전부 적용된 상태로 판정한다.

## 핵심 규칙 — goal 의 **지역변수를 `_` 로** 바꿔야 한다

    ✗  SearchPattern (Int.and (Int.shl x n) … )   지역 x n 이 경직이라 아무것도 안 나옴
    ✓  SearchPattern (Int.and (Int.shl _ _) … )   → Int.and_shl

지역 이름(가설 목록)이 곧 lemma 의 전칭 변수가 채울 자리다.

## 방법

정리마다 한 파일 — 증명 접두사를 실행하다가 목표 스텝에서 질의를 끼운다:

    <스텝 0 … k-1>
    idtac "@@@k".
    SearchPattern (<추상화한 goal>).
    SearchRewrite (<추상화한 부분항>).      (rewrite 스텝이면)

사용: CS_N=120 CS_JOBS=4 python3 scripts/coq_search_eval.py
"""
import concurrent.futures as cf
import collections, json, os, re, subprocess, sys, tempfile, time, logging
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ["CUDA_VISIBLE_DEVICES"] = ""
sys.path.insert(0, "src"); sys.path.insert(0, "CoqStoq")
logging.disable(logging.CRITICAL)
from pathlib import Path
from coqstoq import Split as CSSplit, get_theorem
from data_management.sentence_db import SentenceDB
from evaluation.find_coqstoq_idx import get_thm_desc
from premise_selection.coq_query import ladder, rewrite_targets, local_names, hyp_queries, symbol_queries, hyp_rewrite_queries, elab_subterms, wide_queries, notation_queries

N = int(os.environ.get("CS_N", "120"))
JOBS = int(os.environ.get("CS_JOBS", "4"))
TMO = int(os.environ.get("CS_TIMEOUT", "300"))
MAXPT = int(os.environ.get("CS_MAX_PER_THM", "3"))
LEVELS = int(os.environ.get("CS_LEVELS", "3"))   # 사다리 단수
RWN = int(os.environ.get("CS_RWN", "4"))
FWD = os.environ.get("CS_FWD", "1") == "1"    # 전방추론 질의
FWDN = int(os.environ.get("CS_FWDN", "3"))
WIDE = os.environ.get("CS_WIDE", "1") == "1"   # 최대 재현율 모드
WIDEN = int(os.environ.get("CS_WIDEN", "8"))         # rewrite 부분항 개수
OUT = os.environ.get("CS_OUT", "all_log/coq_search.jsonl")
#: 질의 드라이버. "coqtop" 은 오류가 나도 다음 질의를 계속 실행한다.
DRIVER = "coqtop"
CC = "CoqStoq/test-repos/compcert"
t = open(os.path.join(CC, "_CoqProject"), errors="ignore").read().split()
ARGS, i = [], 0
while i < len(t):
    if t[i] in ("-R", "-Q") and i + 2 < len(t):
        ARGS += [t[i], os.path.abspath(os.path.join(CC, t[i + 1])), t[i + 2]]; i += 3
    else:
        i += 1
HEADT = re.compile(r"^\s*(?:now\s+|try\s+|repeat\s+)?([A-Za-z_][\w']*)")
NAMED = re.compile(r"\b(?:e?apply|e?rewrite)\s+(?:<-\s*)?\(?\s*"
                   r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
sdb = SentenceDB.load(Path("raw-data/coqstoq-test/coqstoq-test-sentences.db"))

# ★ elaborate 된 goal — notation 이 펼쳐져 있어 **진짜 상수 이름**이 보인다.
#   출력형은 `P ** Q` 라 `sepconj` 를 못 뽑는데, elaborate 형은 `sepconj P Q` 다.
#   `rewrite` 질의는 기호로 좁히므로 이 차이가 그대로 복원율이 된다.
ELABG = {}
for _f in os.environ.get("CS_ELABG", "all_log/elab_goals_batch.jsonl").split(","):
    _p = Path(_f.strip())
    if _p.exists():
        for _ln in _p.open():
            _ln = _ln.strip()
            if _ln:
                _d = json.loads(_ln)
                ELABG[(_d["idx"], _d["k"])] = _d["goal_elab"]
print(f"■ elaborate goal {len(ELABG):,}", flush=True)

def elab_concl(g):
    """elaborate goal 의 **첫 goal 결론**."""
    b = g.split("============================")
    if len(b) < 2:
        return g.strip()
    out, blank = [], False
    for ln in b[1].split("\n"):
        if not ln.strip():
            if out: blank = True
            continue
        if blank: break
        out.append(ln)
    return " ".join(" ".join(out).split())

def head_by_pos(orig, thm):
    """★ CoqStoq 가 **정확한 줄번호**를 준다 — 텍스트 검색보다 이걸 먼저 쓴다.

    `Maps.v` 에는 `Theorem gso` 가 **셋**(PTree·PMap·…) 있어서 텍스트로 찾으면
    첫 번째(Module PTree 안)에 걸린다. 거기서는 `PTree.gso` 가 아직 존재하지
    않으므로 질의도 검증도 통째로 어긋난다. 실측 199 중 1건(0.5%).
    """
    ln = getattr(getattr(thm, "theorem_start_pos", None), "line", None)
    if not ln:
        return None
    parts = orig.splitlines(keepends=True)
    if ln - 1 > len(parts):
        return None
    return "".join(parts[:ln - 1])


def head_of_file(orig, thm_text):
    j = orig.find(thm_text.strip()[:60])
    if j >= 0: return orig[:j]
    m0 = re.match(r"\s*\w+\s+([\w']+)", thm_text)
    if m0:
        m = re.search(r"(?m)^\s*(?:Lemma|Theorem|Remark|Corollary|Proposition|Fact|Definition)\s+"
                      + re.escape(m0.group(1)) + r"\b", orig)
        if m: return orig[:m.start()]
    return None

def run(job):
    i, path, thm_text, chunks, ks, queries = job
    try:
        orig = open(path, errors="ignore").read()
    except OSError:
        return i, [], "파일 없음"
    head = head_of_file(orig, thm_text)
    if head is None:
        return i, [], "정리 위치 못 찾음"
    body = [head, thm_text]
    prev = 0
    for k in ks:
        body.append(chunks[prev])
        body.append(f'idtac "@@@{k}".')
        for qi, q in enumerate(queries[k]):
            body.append(f'idtac "@@@{k}#L{qi}".')
            body.append(q)
        prev = k
    body.append("Admitted.")
    src = "\n".join(body) + "\n"
    d = os.path.dirname(os.path.abspath(path))
    with tempfile.NamedTemporaryFile("w", suffix=".v", dir=d, delete=False) as f:
        f.write(src); tmp = f.name
    try:
        t0 = time.time()
        if DRIVER == "coqtop":
            # ★★ **드라이버를 coqtop 으로.** `coqc` 는 vernacular 오류에서 파일
            #   처리를 **중단**한다 — 실측으로 지점당 21.7 질의(전체 4,080개)를
            #   그렇게 잃었다. `coqtop` 은 오류를 찍고 **다음 명령을 계속 실행**한다.
            #   질의 생성기의 문법 오류·미해결 이름을 하나하나 막는 대신 구조로 푼다.
            p = subprocess.run(["coqtop", "-q"] + ARGS,
                               stdin=open(tmp), capture_output=True,
                               text=True, timeout=TMO)
        else:
            p = subprocess.run(["coqc", "-q"] + ARGS + [tmp],
                               capture_output=True, text=True, timeout=TMO)
        dt = time.time() - t0
        out = p.stdout or ""
        # ★ 질의가 **하나라도 오류**를 내면 Coq 이 그 시점에 파일 처리를 중단한다 —
        #   뒤 질의가 전부 죽어 `후보 0` 이 된다. 몇 개가 실행됐는지와 오류를 남긴다.
        _emitted = sum(len(v) for v in queries.values())
        _ran = len(re.findall(r"@@@\d+#L\d+", out))
        _err = " ".join((p.stderr or "").split())[:300]
        blocks = re.split(r"@@@(\d+)#L(\d+)\s*", out)
        per = {}
        for a in range(1, len(blocks) - 2, 3):
            k, lv = int(blocks[a]), int(blocks[a + 1])
            # ★ 이름만 뽑지 말고 **타입까지** 가져간다.
            #   `Search` 출력이 `name: type` 이라 선언문이 이미 거기 있다.
            #   이름만 두면 나중에 sentence DB 로 되찾아야 하는데, 검색은 전역 환경
            #   (Coq stdlib 포함)에서 뽑으므로 **대부분 못 찾는다**
            #   (실측: 5,000개 중 189개만 복원 = 병목이 검색이 아니라 조회였다).
            blk = blocks[a + 2]
            items = {}
            for m2 in re.finditer(r"(?m)^(\w[\w'.]*):[ \t]*(.*(?:\n[ \t]+.*)*)", blk):
                nm2, ty2 = m2.group(1), " ".join(m2.group(2).split())
                if nm2 and nm2 not in items:
                    items[nm2] = ty2
            per.setdefault(k, {})[lv] = items
        recs = [{"idx": i, "k": k, "levels": v, "sec": dt,
                 "ran": _ran, "emitted": _emitted, "err": _err} for k, v in per.items()]
        return i, recs, None if recs else (p.stderr or "")[:150]
    except subprocess.TimeoutExpired:
        return i, [], "timeout"
    except Exception as e:
        return i, [], str(e)[:120]
    finally:
        b = os.path.splitext(tmp)[0]
        for ext in (".v", ".vo", ".vok", ".vos", ".glob"):
            try: os.unlink(b + ext)
            except OSError: pass

if __name__ == "__main__":
    ids = [int(x) for x in Path("data/compcert_bs2_rand200_idx.txt").read_text().split()][:N]
    jobs, meta = [], {}
    for i in ids:
        try:
            thm = get_theorem(CSSplit.TEST, i, Path("CoqStoq"))
            d = get_thm_desc(thm, Path("raw-data/coqstoq-test"), sdb)
            if d is None: continue
            proof = d.dp.proofs[d.idx]
            path = os.path.join(CC, str(thm.path))
            orig = open(path, errors="ignore").read()
        except Exception:
            continue
        if head_of_file(orig, proof.theorem.term.text) is None:
            continue
        ks = [k for k, st in enumerate(proof.steps)
              if HEADT.match(st.step.text or "")
              and HEADT.match(st.step.text).group(1) in ("apply", "eapply", "rewrite", "erewrite")
              and NAMED.search(st.step.text or "") and st.goals]
        if not ks: continue
        if len(ks) > MAXPT:
            stp = len(ks) / MAXPT
            ks = [ks[int(x * stp)] for x in range(MAXPT)]
        steps = [s.step.text for s in proof.steps]
        chunks, prev = {}, 0
        for k in ks:
            chunks[prev] = "".join(steps[prev:k]); prev = k
        queries = {}
        for k in ks:
            st = proof.steps[k]
            g = st.goals[0]
            loc = local_names(g)
            tac = HEADT.match(st.step.text).group(1)
            qs = []
            # ★ 구체→추상 **사다리** — SearchPattern 은 매칭(인스턴스)이라
            #   goal 보다 일반적인 lemma(not_eq_sym·Rle_trans 류)는 구체 패턴으로 안 잡힌다.
            if tac.endswith("apply"):
                for pat in ladder(g.goal, loc, max_levels=LEVELS):
                    qs.append(f"SearchPattern ({pat}).")
                # ★ 전방추론(`apply L in H`) — 가설 타입으로도 쏜다
                if FWD:
                    for pat in hyp_queries(g, loc, maxn=FWDN):
                        qs.append(f"SearchPattern ({pat}).")
            else:
                # ★ rewrite — 부분항 추측 대신 **기호 결합**으로 좁힌다
                qs.extend(symbol_queries(g.goal, loc, maxn=6))
                # ★ elaborate 형에서도 기호를 뽑는다 — notation 이 가린 상수(`**`→sepconj)
                _eg = ELABG.get((i, k))
                if _eg:
                    _ec = elab_concl(_eg)
                    qs.extend(symbol_queries(_ec, loc, maxn=5))
                    # ★ 부분항도 elaborate 형에서 뽑는다 — 괄호·notation·if 안쪽이 다 보인다
                    for _t in elab_subterms(_ec, maxn=6):
                        qs.append(f"SearchRewrite {_t}.")
                # ★ 괄호 없는 적용 부분항이 들어오면서 대상이 늘었다 — 2→RWN
                for pat in rewrite_targets(g.goal, loc, maxn=RWN):
                    qs.append(f"SearchRewrite ({pat}).")
                # ★ `rewrite L in H` — 가설 **안**을 재작성하므로 가설 기호로도 쏜다
                if FWD and re.search(r"\bin\s+[A-Za-z_]", st.step.text or ""):
                    qs.extend(hyp_rewrite_queries(g, loc, maxn=3))
                if FWD:
                    for pat in hyp_queries(g, loc, maxn=FWDN):
                        qs.append(f"SearchPattern ({pat}).")
                if not qs:
                    for pat in ladder(g.goal, loc, max_levels=LEVELS):
                        qs.append(f"SearchPattern ({pat}).")
            # ★ 최대 재현율 모드 — 기호 하나씩 넓게. 목표가 "포함률 100%" 일 때 쓴다.
            if WIDE:
                qs.extend(wide_queries(g.goal, loc, g.hyps, maxsym=WIDEN))
                _eg2 = ELABG.get((i, k))
                if _eg2:
                    qs.extend(wide_queries(elab_concl(_eg2), loc, None, maxsym=WIDEN))
            # ★ **위험 질의는 맨 뒤로.** 오류 나면 Coq 이 파일 처리를 중단하므로
            #   앞에 두면 뒤 질의를 통째로 잃는다(실측: 사망 84건 중 29건이 notation).
            qs.extend(notation_queries(g.goal, loc, maxn=2))
            queries[k] = qs
            meta[(i, k)] = dict(gold=NAMED.search(st.step.text).group(1),
                                tac="rewrite" if tac.endswith("rewrite") else "apply",
                                nq=len(qs))
        jobs.append((i, path, proof.theorem.term.text, chunks, ks, queries))
    jobs.sort(key=lambda j: len(open(j[1], errors="ignore").read()))
    print(f"■ 정리 {len(jobs)} · 질의지점 {len(meta)} · 병렬 {JOBS}", flush=True)
    S = collections.Counter(); T = []
    with open(OUT, "w") as fo, cf.ThreadPoolExecutor(JOBS) as ex:
        for n, (i, recs, err) in enumerate(ex.map(run, jobs)):
            for r in recs:
                m = meta.get((r["idx"], r["k"]))
                if not m: continue
                gb = m["gold"].split(".")[-1]
                lv = {int(a): b for a, b in r["levels"].items()}
                allf, cum, firsthit = set(), [], None
                types = {}
                for a in sorted(lv):
                    _b = lv[a]
                    if isinstance(_b, dict):
                        allf |= set(_b); types.update(_b)
                    else:
                        allf |= set(_b)
                    h = any(x == m["gold"] or x.split(".")[-1] == gb for x in allf)
                    cum.append((a, len(allf), h))
                    if h and firsthit is None: firsthit = a
                hit = firsthit is not None
                S["지점"] += 1; S["후보"] += len(allf); S["적중"] += hit
                S[f"{m['tac']} 지점"] += 1; S[f"{m['tac']} 적중"] += hit
                S[f"{m['tac']} 후보"] += len(allf)
                for a, nc, h in cum:
                    S[f"누적L{a} 지점"] += 1; S[f"누적L{a} 적중"] += h; S[f"누적L{a} 후보"] += nc
                T.append(r["sec"])
                r.update(gold=m["gold"], tac=m["tac"], hit=hit, first=firsthit,
                         nfound=len(allf), found=sorted(allf),
                         types={k2: v2 for k2, v2 in types.items() if v2})
                r.pop("levels", None)
                fo.write(json.dumps(r, ensure_ascii=False) + "\n")
            if err: S["실패"] += 1
            if (n + 1) % 10 == 0:
                print(f"   … {n+1}/{len(jobs)} · 지점 {S['지점']} · 적중 {S['적중']}", flush=True)
            fo.flush()
    n = max(S["지점"], 1)
    import statistics as st
    print(f"\n■ Coq 내장 색인 · 질의지점 {S['지점']} (정리 실패 {S['실패']})")
    print(f"   ① gold 적중   {S['적중']}/{n} = {S['적중']/n*100:.1f}%")
    print(f"   ② 후보 수     {S['후보']/n:.1f}개/지점   (현행 풀 ~2,100 대비 "
          f"{2100/max(S['후보']/n,0.01):.0f}배 축소)")
    print(f"\n   ── 사다리 단별 **누적** ──")
    print(f"      {'단':6s}{'지점':>6s}{'누적 적중':>10s}{'누적 후보':>11s}")
    for a in range(8):
        m = S[f"누적L{a} 지점"]
        if not m: continue
        print(f"      L{a:<5d}{m:6d}{S[f'누적L{a} 적중']/m*100:9.1f}%{S[f'누적L{a} 후보']/m:10.0f}개")
    for tac in ("apply", "rewrite"):
        m = S[f"{tac} 지점"]
        if m:
            print(f"   · {tac:8s} {m:3d} 지점 · 적중 {S[f'{tac} 적중']/m*100:5.1f}%"
                  f" · 후보 {S[f'{tac} 후보']/m:5.1f}개")
