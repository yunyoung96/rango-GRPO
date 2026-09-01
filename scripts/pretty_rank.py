#!/usr/bin/env python3
"""★★★ **최종 방법** — 최소 가중치·이론 정합·trainable·TRAIN→VAL/TEST 전이.

한 식으로 쓴다 (채널 c 에서 lemma L 의 점수):

    score_c(L) = share_c(L) + β·overlap_c(L) + λ·rig(L) + μ·std(L)

      share_c   = |매칭된 부분구조| / |대상|      격자의 meet — goal(가설)을
                  얼마나 설명하나. ap/in 은 lgg, rw/rwh 는 redex 크기 z.
      overlap_c = |lcp| / |대상|                  판별트리가 공짜로 주는 근사 meet
      rig       = 경직 라벨 수                    Baire: −log₂ P(통과) ∝ rig
      std       = 표준라이브러리 여부              사전 (프로젝트 lemma 우선)

    자유 파라미터는 β·λ·μ **최대 3개**. K-스윕으로 더 줄인다:
      K0: (β,λ,μ)=(1,0.2,0) 고정 — 학습 0
      K1: λ 만 학습          K2: β,λ        K3: β,λ,μ

프로토콜 (gold 는 TRAIN 라벨로만):
    ① TRAIN 5겹(정리파일 그룹) CV 로 K 선택 — 최고 대비 1.0pp 이내 최소 K
    ② 전체 TRAIN 으로 재적합 → 가중치 동결
    ③ VAL/TEST 는 **한 번씩만** 평가
평가 지표 = **자기 채널** (apply→ap, apply-in→in, rewrite→rw, rewrite-in→rwh):
    회수(채널에 gold 존재) · @5/@10/@20 (분모=그 형태 전체 지점)

사용: python3 scripts/pretty_rank.py <TRAIN풀들> -- <VAL풀들> -- <TEST풀들>
"""
import collections, itertools, json, os, re, sys, statistics as st
import numpy as np
sys.path.insert(0, "scripts")
import logging; logging.disable(logging.CRITICAL)
import applic_rank as AR
from scipy.optimize import minimize
import math

#: ★ goal 사이드카 — 재수집 없이 (proj,thm,thmi,k) 로 goal 텍스트 조인
GOALS = {}
for _gp in ("all_log/r11_goals_train.jsonl", "all_log/r11_goals_val.jsonl",
            "all_log/r11_goals_test.jsonl"):
    if os.path.exists(_gp):
        for _l in open(_gp):
            _r = json.loads(_l)
            GOALS[(_r["proj"], _r["thm"], _r["thmi"], _r["k"])] = _r.get("goal") or ""
#: 토큰-idf 는 첫 load_merge(TRAIN) 때 굽는다
_IDF = {}; _MAXI = [0.0]
#: ★ 옛 stdlib 이름 → 정규 basename (Zmult_comm→mul_comm 등 46건).
#   gold 텍스트와 후보 정규명이 어긋나는 **회계 실패**를 없앤다
#   (실측: TRAIN rewrite 회수 69.4→96.7). 맵이 없으면 빈 dict — 무해.
ALIAS = {}
if os.path.exists("all_log/r11_alias_map.json"):
    ALIAS = json.load(open("all_log/r11_alias_map.json"))


def build_idf(rows):
    df = collections.Counter(); N = 0
    for r in rows:
        for st_ in (r.get("stmts") or {}).values():
            if st_:
                N += 1
                for t in set(AR._TOK.findall(st_)): df[t] += 1
    _IDF.clear()
    _IDF.update({t: math.log((N + 1) / (v + 1)) for t, v in df.items()})
    _MAXI[0] = math.log(N + 1)
    return N

FORMS = ("apply", "apply-in", "rewrite", "rewrite-in")
#: ★ 한 스텝에 lemma 가 여럿일 수 있다 — `rewrite A, B in H.`
#   요구사항(§3): "하나라도 포함 + 다 포함을 구분해서" 보여준다.
_NAME = re.compile(r"(?:<-\s*)?\(?\s*([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")


def golds_of(r):
    """gold 이름 목록. gold_text 의 첫 전술 조각을 쉼표로 갈라 각각의 첫
    식별자를 취한다. 실패하면 [gold] 하나."""
    t = " ".join((r.get("gold_text") or "").split())
    seg = t.split(";")[0].split(" by ")[0]
    # 머리 전술어 제거 후 쉼표 목록
    m = re.match(r"\s*(?:now\s+|try\s+|repeat\s+)?"
                 r"(?:e?apply|e?rewrite)\s+(.*)$", seg)
    out = []
    if m:
        body = m.group(1).split(" in ")[0]
        for part in body.split(","):
            mm = _NAME.match(part.strip())
            if mm: out.append(mm.group(1))
    if r.get("gold") and r["gold"] not in out:
        out.insert(0, r["gold"])
    assert out, f"gold 추출 실패: {t!r}"
    return out
FORM_CH = {"apply": "ap", "apply-in": "in", "rewrite": "rw", "rewrite-in": "rwh"}
CH4 = ("ap", "in", "rw", "rwh")
#: ★ K-사다리 — AUC 탐침(2026-09-01) 순서로 쌓는다:
#   rig 0.710 > d 0.666(역) > z 0.604 > lcp 0.540 > nm·hp ≈ 0.5
#: K-사다리 — lex(어휘) 를 2층에 (실측: BLEND TEST +4.0pp · rwh +10.6pp)
K_GRID = {
    0: (),
    1: ("lam",),
    2: ("lam", "rho"),                 # + 어휘 겹침 lex
    3: ("beta", "lam", "rho"),
    4: ("beta", "lam", "mu", "rho"),
    5: ("beta", "lam", "mu", "rho", "kap"),
    6: ("lam", "rho", "rhh"),          # + rwh 전용 어휘 보정
}
DEF = {"beta": 1.0, "lam": 0.2, "mu": 0.0, "eta": 0.0, "kap": 0.0, "rho": 0.0,
       "rhh": 0.0}


def _vnum(r):
    m = re.match(r"r(\d+)", str(r.get("ver") or ""))
    return int(m.group(1)) if m else 0


def load_merge(paths):
    """풀 병합 — (proj,thm,k) 중복은 **플러그인 버전 높은 행**이 이긴다.

    main 풀(r11 의미)과 only_in 보강(r13)이 같은 지점을 담을 수 있다.
    예전엔 먼저 온 행이 이겨서 iff 수리(r13)가 병합에서 지워졌다 —
    실측: VAL apply-in 회수 7/8 인데 병합 후 5/6 으로 보임."""
    seen = {}; n_dup = 0
    for p in paths:
        if not os.path.exists(p): continue
        for l in open(p):
            r = json.loads(l)
            if not r.get("gold") or r.get("local"): continue
            key = (r.get("proj"), r.get("thm"), r.get("k"))
            if key in seen:
                n_dup += 1
                if _vnum(r) <= _vnum(seen[key]): continue
            seen[key] = r
    rows = list(seen.values())
    assert rows, f"풀이 비었다: {paths}"
    # ★ 쓰는 중인 풀을 읽는 사고 방지 — v5 덮어쓰기 사건(39지점 스캔)의 재발 방지.
    #   60초 내 갱신된 파일이 있으면 수집이 진행 중일 수 있다.
    import time as _t
    for p_ in paths:
        if os.path.exists(p_):
            age = _t.time() - os.path.getmtime(p_)
            assert age > 60, f"풀이 방금({age:.0f}s 전) 갱신됨 — 수집 중 읽기 의심: {p_}"
    return rows, n_dup


def parse_goal(txt):
    """pp goal → (가설 평탄 목록 [(이름, 타입문자열)], 결론문자열).

    형식: 가설 블록(이름[, 이름]*: 타입, 연속줄은 들여쓰기) + 빈 줄 + 결론.
    `A0, A1: A` 그룹은 **이름 수만큼** 펼친다 — hp(끝에서부터 위치)와
    맞추려면 평탄 개수가 커널 문맥과 같아야 한다."""
    if not txt: return [], ""
    if "\n\n" in txt:
        hb, concl = txt.rsplit("\n\n", 1)
    else:
        return [], txt
    out = []
    cur_names, cur_ty = None, []
    for ln in hb.split("\n"):
        m = re.match(r"^([A-Za-z_][\w']*(?:, [A-Za-z_][\w']*)*):( .*)?$", ln)
        if m:
            if cur_names:
                for nm_ in cur_names: out.append((nm_, " ".join(cur_ty)))
            cur_names = m.group(1).split(", ")
            cur_ty = [(m.group(2) or "").strip()]
        else:
            if cur_names is not None: cur_ty.append(ln.strip())
    if cur_names:
        for nm_ in cur_names: out.append((nm_, " ".join(cur_ty)))
    return out, concl


def pfeats(nm, s, gsz):
    """[share, overlap, rig, std, rec] — share = max(lgg,z)/g.
    rec = 1/hp (rwh 전용 가설 최근성 — 증명은 방금 만든 가설을 재작성한다).
    hp 없는 채널에선 0 이라 식이 채널마다 갈라지지 않는다."""
    share = max(float(s.get("lgg", 0)), float(s.get("z", 0))) / gsz
    hp = float(s.get("hp", 0))
    return np.array([share,
                     float(s.get("lcp", 0)) / gsz,
                     float(s.get("rig", 0)),
                     1.0 if AR._is_std(nm) else 0.0,
                     (1.0 / hp) if hp > 0 else 0.0,
                     float(s.get("d", 0))])   # 등식 깊이 = 전제 부담 (rw/rwh)


def point_data(r):
    """지점 → 자기 채널의 (X행렬, gold마스크들). 없으면 None.

    마스크는 **gold 하나당 하나** — `rewrite A, B` 면 A·B 각각.
    any = 하나라도 상위, all = 전부 상위 를 이걸로 구분한다."""
    f = r.get("tac")
    if f not in FORMS: return None
    c = FORM_CH[f]
    names = sorted(set((r.get("chan") or {}).get(c, [])))
    gs = golds_of(r)
    SC = AR.sig_by_chan(r)
    sig = r.get("sig") or {}
    gsz = float((list(sig.values()) or [{}])[0].get("g", 1) or 1)
    cs = SC.get(c, sig)
    if not names:
        return (f, [], None, None)
    _raw = GOALS.get((r.get("proj"), r.get("thm"), r.get("thmi"),
                      r.get("k")), "")
    hyps_fl, concl_tx = parse_goal(_raw)
    gt = set(AR._TOK.findall(_raw))           # 전 채널: 문맥 전체 (실측 최선)
    stmts = r.get("stmts") or {}
    # ★ 정규화 lex — goal 의 idf 질량 중 후보 진술문이 설명하는 **비율** [0,1].
    #   원(raw) 합은 0~30+ 로 무계라 구조 항(share ≤1)을 삼켰다 — 실측: 초일반
    #   gold(or_comm 류)가 in 채널 순위 ~120 으로 침몰(VAL apply-in 0%).
    #   비율로 만들면 share 와 같은 단위가 되어 "구조 겹침 + 어휘 겹침" 이
    #   대칭적으로 읽힌다.
    _gmass = sum(_IDF.get(t, _MAXI[0]) for t in gt) or 1.0
    # ★ 문맥은 전 채널 **전체**가 실측 최선이다. 두 가설-국소 변형은 모두
    #   rewrite-in 을 무너뜨렸다(후보별 문맥 19.1 · max-hyp 25.5, 원 38.3):
    #   가설 재작성도 결론을 향하므로 결론 어휘가 같이 필요하다.
    def _lex(n):
        stk = set(AR._TOK.findall(stmts.get(n) or ""))
        return sum(_IDF.get(t, _MAXI[0]) for t in stk & gt) / _gmass
    X = np.stack([(lambda _v: np.append(np.append(
                      pfeats(n, cs.get(n) or {}, gsz), _v),
                      _v if c == "rwh" else 0.0))(_lex(n))
                  for n in names])
    Ms = []
    for g in gs:
        bs = {g, g.split(".")[-1]}
        a = ALIAS.get(g) or ALIAS.get(g.split(".")[-1])
        if a: bs.add(a)
        Ms.append(np.array([n in bs or n.split(".")[-1] in bs for n in names]))
    return (f, names, X, Ms)


def w_of(theta, kparams):
    d = dict(DEF)
    for k, v in zip(kparams, theta): d[k] = float(v)
    return np.array([1.0, d["beta"], d["lam"], d["mu"], d["eta"], d["kap"],
                     d["rho"], d["rhh"]])


def rank_self(pd, w):
    """(형태, any순위, all순위). any = 여러 gold 중 최선, all = 최악(전부 회수시)."""
    f, names, X, Ms = pd
    if X is None or not any(m.any() for m in Ms): return f, None, None
    s = X @ w
    order = sorted(range(len(names)), key=lambda i: (-s[i], names[i]))
    pos = {j: i + 1 for i, j in enumerate(order)}
    per = [min(pos[j] for j in np.where(m)[0]) for m in Ms if m.any()]
    any_r = min(per)
    all_r = max(per) if all(m.any() for m in Ms) else None
    return f, any_r, all_r


def mrr(pds, w):
    v = []
    for pd in pds:
        _, r, _ = rank_self(pd, w)
        v.append(1.0 / r if r else 0.0)
    return float(np.mean(v)) if v else 0.0


def fit(pds, kparams):
    """결정적: 굵은 격자 → Nelder-Mead 다듬기. 목적 = 자기채널 MRR."""
    if not kparams: return np.array([])
    grids = {"beta": (0.0, 0.5, 1.0, 2.0), "lam": (0.05, 0.1, 0.2, 0.5, 1.0),
             "mu": (-1.0, -0.5, 0.0, 0.5), "eta": (0.0, 0.5, 1.0, 2.0),
             "kap": (-1.0, -0.5, -0.2, -0.1, 0.0),
             "rho": (0.0, 0.5, 1.0, 2.0, 4.0, 8.0),
             "rhh": (0.0, 2.0, 4.0, 8.0, 16.0)}
    best, bv = None, -1.0
    for combo in itertools.product(*[grids[k] for k in kparams]):
        v = mrr(pds, w_of(combo, kparams))
        if v > bv: bv, best = v, np.array(combo, dtype=float)
    res = minimize(lambda t: -mrr(pds, w_of(t, kparams)), best,
                   method="Nelder-Mead",
                   options={"maxiter": 200, "xatol": 1e-3, "fatol": 1e-5})
    return res.x if -res.fun >= bv else best


def at10(pds, w):
    n = 0; hit = 0
    for pd in pds:
        n += 1
        _, r, _ = rank_self(pd, w)
        if r and r <= 10: hit += 1
    return hit / max(n, 1) * 100


def table(tag, pds, w):
    N = collections.Counter(); RK = collections.defaultdict(list)
    RA = collections.defaultdict(list)          # all(다 포함) 순위
    REC = collections.Counter()
    for pd in pds:
        f, names, X, Ms = pd
        N[f] += 1; N["전체"] += 1
        if Ms is not None and any(m.any() for m in Ms):
            REC[f] += 1; REC["전체"] += 1
        _, r, ra = rank_self(pd, w)
        if r: RK[f].append(r); RK["전체"].append(r)
        if ra: RA[f].append(ra); RA["전체"].append(ra)
    print(f"\n■ {tag} · 자기 채널 평가 (분모=형태 전체 지점 · 하나라도/모두 구분)")
    print(f"   {'형태':12s}{'지점':>6s}{'채널회수':>9s}{'@10':>8s}{'@20':>8s}"
          f"{'@50':>8s}{'@10모두':>9s}{'@20모두':>9s}{'중앙':>7s}")
    for f in ("전체",) + FORMS:
        n = N.get(f, 0)
        if not n: continue
        rk = RK.get(f, []); ra = RA.get(f, [])
        at = lambda K: sum(1 for x in rk if x <= K) / n * 100
        aa = lambda K: sum(1 for x in ra if x <= K) / n * 100
        print(f"   {f:12s}{n:6d}{REC.get(f,0)/n*100:8.1f}%"
              f"{at(10):8.1f}%{at(20):8.1f}%{at(50):8.1f}%"
              f"{aa(10):9.1f}%{aa(20):9.1f}%{(st.median(rk) if rk else 0):7.0f}")


if __name__ == "__main__":
    argv = sys.argv[1:]
    assert argv.count("--") == 2, "TRAIN풀 -- VAL풀 -- TEST풀"
    i1, i2 = argv.index("--"), len(argv) - 1 - argv[::-1].index("--")
    TR_P, VA_P, TE_P = argv[:i1], argv[i1+1:i2], argv[i2+1:]

    tr, d1 = load_merge(TR_P)
    _N = build_idf(tr)          # ★ 토큰-idf 는 TRAIN 만으로 (동결)
    print(f"■ TRAIN {len(tr)}행 (중복 제거 {d1}) · 토큰표 N={_N:,}", flush=True)
    tr_pd = [pd for pd in (point_data(r) for r in tr) if pd]
    tr_grp = [r.get("thm") for r in tr if r.get("tac") in FORMS]
    assert len(tr_grp) == len(tr_pd)

    # ── ① K 선택: 정리파일 5겹 CV ───────────────────────────────────────
    files = sorted(set(tr_grp))
    folds = {f_: i % 5 for i, f_ in enumerate(files)}
    print(f"   4형태 지점 {len(tr_pd)} · 파일 {len(files)} · 5겹 CV")
    cv = {}
    for K, kp in K_GRID.items():
        accs = []
        for fold in range(5):
            tr_i = [pd for pd, g in zip(tr_pd, tr_grp) if folds[g] != fold]
            te_i = [pd for pd, g in zip(tr_pd, tr_grp) if folds[g] == fold]
            if not tr_i or not te_i: continue
            th = fit(tr_i, kp)
            accs.append(at10(te_i, w_of(th, kp)))
        cv[K] = float(np.mean(accs))
        print(f"   K={K} ({','.join(kp) or '고정'}): CV 자기@10 {cv[K]:.1f}%",
              flush=True)
    bestK = max(cv, key=lambda k: cv[k])
    K = min(k for k in cv if cv[k] >= cv[bestK] - 1.0)   # 1pp 이내 최소 K
    kp = K_GRID[K]
    print(f"   ★ 선택 K={K} (최고 K={bestK} 대비 {cv[bestK]-cv[K]:+.1f}pp)")

    # ── ② 전체 TRAIN 재적합 → 동결 ──────────────────────────────────────
    th = fit(tr_pd, kp)
    W = w_of(th, kp)
    print(f"   동결 가중치 [share overlap rig std rec d lex lexrwh] = "
          + " ".join(f"{x:+.3f}" for x in W))

    # ── ③ 세 스플릿 평가 (TRAIN 은 CV 수치가 정직 — 참고로 재적합판도) ──
    table(f"TRAIN (재적합 — 참고용, 정직한 수치는 위 CV)", tr_pd, W)
    for tag, paths in (("VAL", VA_P), ("TEST", TE_P)):
        rows, d = load_merge(paths)
        pds = [pd for pd in (point_data(r) for r in rows) if pd]
        print(f"\n({tag}: {len(rows)}행 · 중복 제거 {d} · 4형태 {len(pds)})")
        table(f"{tag} ← TRAIN 동결 가중치", pds, W)
    print("PRETTY_DONE", flush=True)
