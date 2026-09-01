#!/usr/bin/env python3
"""★ 채널별 랭커 — 채널마다 **따로** 학습해서 랭킹한다.

지금은 4채널을 한 모델로 랭킹한다. 그런데 채널마다 신호의 성격이 다르다:

    apply    결론 전체 ↔ goal 전체   →  lcp·lgg 가 5~15 로 크다
    rewrite  등식 한 변 ↔ 부분항 하나 →  lcp 1~2 · z 6. 구조 신호가 빈약하다

실측(CompCert 74 rewrite 지점): 우리 랭킹 @10 38.6% vs 현행 tf-idf 49.1%.
**찾기는 잘 찾는데(94.7% vs 77.2%) 위로 못 올린다.** rewrite 에서는 어휘
신호(lex·nov)가 상대적으로 더 중요한데, 공통 가중치라 그게 안 반영된다.

그래서 채널마다 자기 가중치를 배우게 한다. 부수 효과로 **눈금 문제도 사라진다**
— 채널 안에서만 비교하므로 `('ch',…)` 오프셋이 순위에 영향을 안 준다.

사용: python3 scripts/chan_ranker.py <풀.jsonl> [split]
"""
import collections, json, math, os, re, sys, statistics as st
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")
os.environ["CUDA_VISIBLE_DEVICES"] = ""
sys.path.insert(0, "src"); sys.path.insert(0, "CoqStoq"); sys.path.insert(0, "scripts")
import logging; logging.disable(logging.CRITICAL)
from pathlib import Path
import applic_rank as AR

SRC = sys.argv[1] if len(sys.argv) > 1 else "all_log/dn_pool.jsonl"
SPLIT = (sys.argv[2] if len(sys.argv) > 2 else "TEST").upper()
_DATA = {"VAL": "raw-data/coqstoq-val", "TEST": "raw-data/coqstoq-test",
         "CUTOFF": "raw-data/coqstoq-cutoff"}[SPLIT]
_SDB = f"{_DATA}/coqstoq-{SPLIT.lower()}-sentences.db"
CH4 = ("ap", "in", "rw", "rwh")
FORMS = ("apply", "apply-in", "rewrite", "rewrite-in")
OWN = {"apply": ("ap", "in"), "apply-in": ("in",),
       "rewrite": ("rw", "rwh"), "rewrite-in": ("rwh",)}

# ── ★ 시동 자가검사 ──────────────────────────────────────────────────────
assert set(CH4) <= set(AR.ALL_CH), f"모르는 채널: {set(CH4)-set(AR.ALL_CH)}"
assert set(OWN) == set(FORMS), "OWN 과 FORMS 가 어긋난다"
for _f, _cs in OWN.items():
    assert set(_cs) <= set(CH4), f"OWN[{_f}] 이 CH4 밖: {set(_cs)-set(CH4)}"
assert SPLIT in ("VAL", "TEST", "CUTOFF"), f"모르는 split: {SPLIT}"
assert os.path.exists(SRC), f"풀 파일이 없다: {SRC}"


def enrich(rows):
    """lex·gnames 를 붙인다 — 가중치 2·3위 특징이라 빠지면 @10 이 13pp 떨어진다."""
    from coqstoq import Split as CS, get_theorem, get_theorem_list
    from data_management.sentence_db import SentenceDB
    from evaluation.find_coqstoq_idx import get_thm_desc
    if all(r.get("_gt") is not None for r in rows): return rows
    sdb = SentenceDB.load(Path(_SDB))
    # ★ 토큰 idf 는 **여기서 안 굽는다** — 겹마다 학습 겹으로만 만든다.
    #   평가 지점의 진술문까지 세면 그것도 평가 데이터를 훑는 것이다.
    sp = {"VAL": CS.VAL, "TEST": CS.TEST, "CUTOFF": CS.CUTOFF}[SPLIT]
    # 풀 형식 두 가지: CompCert(dn_pool: idx) · 멀티(r11_pool: proj/thmi)
    byproj = collections.defaultdict(list)
    if any("thmi" in r for r in rows):
        for t in get_theorem_list(sp, Path("CoqStoq")):
            byproj[str(t.project.dir_name)].append(t)
    ok = 0
    cache = {}
    for r in rows:
        try:
            if "thmi" in r:
                key = (r["proj"], r["thmi"])
                if key not in cache:
                    thm = byproj[r["proj"]][r["thmi"]]
                    cache[key] = get_thm_desc(thm, Path(_DATA), sdb)
                d = cache[key]
            else:
                key = r["idx"]
                if key not in cache:
                    cache[key] = get_thm_desc(get_theorem(sp, r["idx"], Path("CoqStoq")),
                                              Path(_DATA), sdb)
                d = cache[key]
            if d is None: continue
            gs = d.dp.proofs[d.idx].steps[r["k"]].goals
            gl = gs[0] if gs else ""
            gl = gl if isinstance(gl, str) else (getattr(gl, "goal", "") or "")
        except Exception:
            gl = ""
        gt = set(AR._TOK.findall(gl))
        r["_gt"] = sorted(gt)          # goal 토큰만 저장. lex 는 겹마다 계산
        gn = set()
        for x in gt: gn |= AR._name_toks(x)
        r["gnames"] = sorted(gn)
        if gt: ok += 1
    # ★ `_gt` 가 비면 lex·nov 가 통째로 죽는다 — 가중치 2·3위 특징이다.
    assert ok >= 0.5 * len(rows), \
        (f"goal 텍스트를 {ok}/{len(rows)} 에만 붙였다 — sentence DB 경로나 "
         f"CoqStoq 인덱스를 의심하라")
    _gn = sum(1 for r in rows if r.get("gnames"))
    assert _gn >= 0.5 * len(rows), f"gnames 가 빈 지점 {len(rows)-_gn}/{len(rows)}"
    print(f"■ lex/gnames 부착 {ok}/{len(rows)} (gnames {_gn})", flush=True)
    return rows


def chan_of(r):
    d = {}
    for c in AR.ALL_CH:
        for x in (r.get("chan") or {}).get(c, []): d.setdefault(x, c)
    return d


def train_chan(rows, idf, ch, skip=None):
    """★ 채널 `ch` 의 후보만으로 학습한다. 양성 = 그 채널에 든 gold."""
    pos = collections.Counter(); neg = collections.Counter(); npos = nneg = 0
    for r in rows:
        if skip and r.get("_grp") == skip: continue
        g = r.get("gold")
        if not g or r.get("local"): continue
        gb = g.split(".")[-1]
        cand = set((r.get("chan") or {}).get(ch, []))
        if not cand: continue
        co = chan_of(r); sig = r.get("sig") or {}
        gsz = float((list(sig.values()) or [{}])[0].get("g", 1) or 1)
        for x in cand:
            fs = AR.feats(x, sig, idf, gsz, co, r.get("lex"),
                          set(r.get("gnames") or []))
            if x == g or x.split(".")[-1] == gb:
                npos += 1
                for kv in fs: pos[kv] += 1
            else:
                nneg += 1
                for kv in fs: neg[kv] += 1
    assert npos >= 0 and nneg >= 0
    W = {}
    for kv in set(pos) | set(neg):
        p = (pos[kv] + 1.0) / (npos + 2.0); q = (neg[kv] + 1.0) / (nneg + 2.0)
        W[kv] = math.log2(p / q)
    return W, npos, nneg


def rank_in(r, ch, W, idf):
    sig = r.get("sig") or {}
    gsz = float((list(sig.values()) or [{}])[0].get("g", 1) or 1)
    sc = AR.nb_score_fn(W, idf, chan_of(r), r.get("lex"),
                        set(r.get("gnames") or []))
    v = sorted(set((r.get("chan") or {}).get(ch, [])),
               key=lambda x: -sc(x, sig, idf, gsz))
    return v


if __name__ == "__main__":
    rows = [json.loads(l) for l in open(SRC)]
    # ★ `dn_pool.jsonl` 에는 gold 이 없다 — `dn_rank.jsonl` 이 들고 있다.
    #   (풀 수집과 gold 추출이 다른 단계라서다.) 있으면 붙인다.
    if not any(r.get("gold") for r in rows):
        rk = {}
        for cand in ("all_log/dn_rank.jsonl",):
            if os.path.exists(cand):
                for l in open(cand):
                    x = json.loads(l); rk[(x["idx"], x["k"])] = x
        n0 = 0
        for r in rows:
            x = rk.get((r.get("idx"), r.get("k")))
            if x:
                r["gold"] = x.get("gold"); r["local"] = x.get("local")
                r["tac"] = x.get("tac"); n0 += 1
        print(f"■ gold 붙임 {n0}/{len(rows)} (dn_rank.jsonl)", flush=True)
    rows = [r for r in rows if r.get("gold") and not r.get("local")]
    assert rows, f"{SRC} 에 gold 지점이 없다"
    # ★ gold **원문**이 있으면 4형태로 다시 나눈다.
    #   `dn_rank.jsonl` 의 `tac` 은 옛 2형태(apply/rewrite)라
    #   `apply-in`·`rewrite-in` 이 apply/rewrite 에 섞여 있다.
    gt = {}
    for cand in ("all_log/next_step_32k.jsonl",):
        if os.path.exists(cand):
            for l in open(cand):
                x = json.loads(l); gt[(x["idx"], x["k"])] = " ".join(x["gold"].split())
    _IN = re.compile(r"\bin\b\s+[A-Za-z_*]")
    _HD = re.compile(r"^\s*(?:now\s+|try\s+|repeat\s+)?([A-Za-z_][\w']*)")

    def _strip(t):
        o = []; d = 0
        for c in t:
            if c == "(": d += 1
            elif c == ")": d = max(0, d - 1)
            elif d == 0: o.append(c)
        return "".join(o)

    n4 = 0
    for r in rows:
        t = r.get("gold_text") or gt.get((r.get("idx"), r.get("k")))
        if not t: continue
        h = _HD.match(t); h = h.group(1) if h else ""
        seg = _strip(t).split(";")[0].split(" by ")[0]
        hi = bool(_IN.search(seg))
        if h.endswith("rewrite"): r["tac"] = "rewrite-in" if hi else "rewrite"; n4 += 1
        elif h in ("apply", "eapply"): r["tac"] = "apply-in" if hi else "apply"; n4 += 1
    if n4: print(f"■ 4형태 재분류 {n4}/{len(rows)}", flush=True)

    # 교차검증 그룹 — 멀티는 프로젝트, CompCert 는 정리
    for r in rows: r["_grp"] = r.get("proj") or r.get("idx")
    rows = enrich(rows)
    # ★ 그룹을 **5겹**으로 묶는다. leave-one-out 은 그룹 162개 × 모델 5개
    #   = 810회 학습이라 못 끝낸다(실측). 겹으로 묶으면 25회다.
    #   같은 그룹(정리/프로젝트)은 같은 겹에 넣어 누출을 막는다.
    _g = sorted({r["_grp"] for r in rows}, key=str)
    NFOLD = 5
    fold = {g: i % NFOLD for i, g in enumerate(_g)}
    for r in rows: r["_fold"] = fold[r["_grp"]]
    grps = list(range(NFOLD))
    print(f"■ {SRC} · {len(rows)}지점 · 그룹 {len(_g)} → {NFOLD}겹", flush=True)

    # ── 학습: 공통 1개 vs 채널별 4개 (그룹 leave-one-out) ────────────────
    RES = collections.defaultdict(lambda: collections.defaultdict(list))
    N = collections.Counter()
    for g in grps:
        tr = [r for r in rows if r["_fold"] != g]
        te = [r for r in rows if r["_fold"] == g]
        if not tr or not te: continue
        # ★★ **누출 제거** — `idf` 도 겹 안에서만 계산한다.
        #   `build_idf` 는 gold 을 안 보지만(필터 통과 여부만 셈), 평가 지점을
        #   포함한 말뭉치 통계라 엄밀히는 평가 데이터를 훑는 것이다.
        #   학습 겹만으로 계산하면 평가 지점을 전혀 안 본다.
        # ★ 누출 검사 — 학습 겹에 평가 겹 지점이 섞이면 안 된다
        assert not ({id(r) for r in tr} & {id(r) for r in te}), "겹이 겹쳤다"
        idf, _, _ = AR.build_idf(tr)
        assert idf, "학습 겹에서 idf 가 비었다"
        # ★ 토큰 idf 도 학습 겹의 진술문만으로 만든다
        _df = collections.Counter(); _nd = 0
        for r in tr:
            for _s in (r.get("stmts") or {}).values():
                if _s:
                    _nd += 1
                    for t in set(AR._TOK.findall(_s)): _df[t] += 1
        tok_idf = {t: math.log((_nd + 1.0) / (v + 1.0)) for t, v in _df.items()}
        for r in rows:                       # 평가 겹에도 이 idf 로 lex 를 계산
            gt = set(r.get("_gt") or [])
            r["lex"] = {_n: AR.lex_overlap(_s, gt, tok_idf)
                        for _n, _s in (r.get("stmts") or {}).items() if _s}
        Wall, _np, _nn = AR.train_nb(tr, idf, lambda t: CH4)
        assert _np > 0, f"겹 {g}: 양성 표본 0 — 학습 겹에 gold 이 없다"
        assert Wall, f"겹 {g}: 가중치표가 비었다"
        _ks = {k for k, _ in Wall}
        for _need in ("lex", "nov", "idf", "e"):
            assert _need in _ks, f"겹 {g}: 특징 '{_need}' 가 없다 — feats 배선 확인"
        Wc = {c: train_chan(tr, idf, c)[0] for c in CH4}
        print(f"   겹 {g+1}/{NFOLD} (평가 {len(te)}지점)", flush=True)
        for r in te:
            f = r.get("tac")
            if f not in FORMS: continue
            N[f] += 1; N["전체"] += 1
            g0 = r["gold"]; gb = g0.split(".")[-1]
            for lab, getW in (("공통", lambda c: Wall), ("★채널별", lambda c: Wc[c])):
                # 자기 형태의 채널 안에서의 순위 (블록 구조를 가정)
                best = None
                for c in OWN.get(f, CH4):
                    v = rank_in(r, c, getW(c), idf)
                    p = next((i + 1 for i, x in enumerate(v)
                              if x == g0 or x.split(".")[-1] == gb), None)
                    if p is not None and (best is None or p < best): best = p
                if best is not None:
                    RES[lab][f].append(best); RES[lab]["전체"].append(best)
    assert N["전체"] > 0, "평가된 지점이 0 — 4형태 gold 이 하나도 없다"
    for lab in ("공통", "★채널별"):
        assert len(RES[lab]["전체"]) <= N["전체"], f"{lab}: 순위가 지점보다 많다"
    print(f"\n■ 자기 채널 안에서의 gold 순위 (그룹 leave-one-out · 분모 = 전체 지점)")
    print(f"   {'형태':12s}{'랭커':10s}{'지점':>6s}{'@5':>8s}{'@10':>8s}{'@20':>8s}"
          f"{'@50':>8s}{'순위중앙':>9s}")
    for f in ("전체",) + FORMS:
        n = N[f]
        if not n: continue
        for lab in ("공통", "★채널별"):
            v = RES[lab][f]
            print(f"   {f if lab=='공통' else '':12s}{lab:10s}{n:6d}"
                  + "".join(f"{sum(1 for x in v if x<=K)/n*100:7.1f}%"
                            for K in (5, 10, 20, 50))
                  + f"{(st.median(v) if v else 0):9,.0f}")
    print("\nCHAN_RANKER_DONE", flush=True)
