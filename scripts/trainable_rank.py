#!/usr/bin/env python3
"""★★ **완전 학습형 가중치** — 나이브 베이즈(세기)를 넘어서 세 방식.

나이브 베이즈는 닫힌형이지만 목적함수가 **분류 우도**지 순위가 아니다.
가중치를 진짜 학습하려면:

  A. 쌍별 로지스틱 (구간 one-hot, 14파라)
     RankNet 의 선형판:  L = Σ_{(g,n)} log(1+e^{−(s_g − s_n)}) + λ‖w‖²
     볼록 → L-BFGS 전역해. NB 와 같은 특징, 목적만 순위로 교체.
  B. 쌍별 로지스틱 (연속 특징, 4파라)
     x = [lgg/g, lcp/g, rig, std] 원값 그대로 — **구간(손으로 고른
     경계)이라는 약점 자체를 제거**한다. 파라미터 4개.
  C. 베이지안 최적화 (GP-EI, 4차원)
     A/B 는 로지스틱 근사 목적. C 는 **순위 지표(MRR)를 직접** 최대화:
     sklearn GP(RBF) + Expected Improvement, 학습 겹 MRR 만 본다.

평가는 전부 프로젝트 leave-one-out — 최적화가 평가 겹을 절대 못 본다.

사용: python3 scripts/trainable_rank.py <풀.jsonl> [태그]
"""
import collections, json, os, sys, statistics as st
import numpy as np
sys.path.insert(0, "scripts")
import logging; logging.disable(logging.CRITICAL)
import applic_rank as AR

POOL = sys.argv[1]
TAG = sys.argv[2] if len(sys.argv) > 2 else os.path.basename(POOL)
CH4 = ("ap", "in", "rw", "rwh")
FORMS = ("apply", "apply-in", "rewrite", "rewrite-in")
SEED = 7
MAXNEG = 200          # 지점당 음성 쌍 상한 (결정적 표집)


def load(p):
    rows = [json.loads(l) for l in open(p)]
    rows = [r for r in rows if r.get("gold") and not r.get("local")]
    for r in rows: r["_g"] = r.get("proj") or r.get("idx")
    assert rows, f"풀이 비었다: {p}"
    return rows


# ── 특징 추출 (연속 4 + 구간 one-hot 14) ─────────────────────────────────
CONT_NAMES = ("lgg/g", "lcp/g", "rig", "std")


def cont_feats(nm, s, gsz):
    """연속 원값 — 구간 없음."""
    return np.array([
        float(s.get("lgg", 0)) / gsz,
        float(s.get("lcp", 0)) / gsz,
        float(s.get("rig", 0)),
        1.0 if AR._is_std(nm) else 0.0,
    ])


def onehot_index():
    """(특징,구간) → 열 번호. 14열 고정."""
    cols = {}
    for b in range(len(AR.BUCKETS["lgg"]) + 1): cols[("lgg", b)] = len(cols)
    for b in range(len(AR.BUCKETS["lcp"]) + 1): cols[("lcp", b)] = len(cols)
    for b in range(len(AR.BUCKETS["rig"]) + 1): cols[("rig", b)] = len(cols)
    for v in (0, 1): cols[("std", v)] = len(cols)
    return cols


COLS = onehot_index()
assert len(COLS) == 14, f"one-hot 열이 {len(COLS)}개 — 14가 아니다"


def oh_feats(nm, s, gsz):
    v = np.zeros(len(COLS))
    kv = AR.feats(nm, {nm: s}, {}, gsz, {}, keep={"lgg", "lcp", "rig", "std"})
    for k, b in kv:
        if (k, b) in COLS: v[COLS[(k, b)]] = 1.0
    return v


def point_data(r):
    """지점 → 채널별 (이름들, 연속행렬, one-hot행렬, gold마스크)."""
    g = r["gold"]; gb = g.split(".")[-1]
    SC = AR.sig_by_chan(r)
    sig = r.get("sig") or {}
    gsz = float((list(sig.values()) or [{}])[0].get("g", 1) or 1)
    out = {}
    for c in CH4:
        names = sorted(set((r.get("chan") or {}).get(c, [])))
        if not names: continue
        cs = SC.get(c, sig)
        X = np.stack([cont_feats(n, cs.get(n) or {}, gsz) for n in names])
        H = np.stack([oh_feats(n, cs.get(n) or {}, gsz) for n in names])
        m = np.array([n == g or n.split(".")[-1] == gb for n in names])
        out[c] = (names, X, H, m)
    return out


def rank_of(pd, w, use_oh):
    """네 채널 최선 순위 (결정적 동률: 이름)."""
    best = None
    for c, (names, X, H, m) in pd.items():
        if not m.any(): continue
        s = (H if use_oh else X) @ w
        order = sorted(range(len(names)), key=lambda i: (-s[i], names[i]))
        pos = next(idx + 1 for idx, i in enumerate(order) if m[i])
        if best is None or pos < best: best = pos
    return best


def metrics(rows_pd, w, use_oh):
    N = 0; RK = []
    for r, pd in rows_pd:
        if r.get("tac") not in FORMS: continue
        N += 1
        b = rank_of(pd, w, use_oh)
        if b is not None: RK.append(b)
    return N, RK


def pairs_of(rows_pd, use_oh, rng):
    """학습 쌍 (gold − 음성) 특징차 행렬."""
    D = []
    for r, pd in rows_pd:
        for c, (names, X, H, m) in pd.items():
            if not m.any() or m.all(): continue
            F = H if use_oh else X
            gi = np.where(m)[0]
            ni = np.where(~m)[0]
            if len(ni) > MAXNEG:
                ni = rng.choice(ni, MAXNEG, replace=False)
            for g_ in gi:
                D.append(F[ni] - F[g_])          # 음성 − gold (부호 주의)
    assert D, "학습 쌍이 없다"
    return np.vstack(D)


def fit_logistic(D, lam=1e-2):
    """min Σ log(1+e^{wᵀd}) + λ‖w‖²  (d = 음성−gold 이므로 wᵀd 가 음수여야)"""
    from scipy.optimize import minimize
    def f(w):
        z = D @ w
        # log(1+e^z) 안정판
        l = np.logaddexp(0.0, z).sum() + lam * (w @ w)
        p = 1.0 / (1.0 + np.exp(-z))
        gr = D.T @ p + 2 * lam * w
        return l, gr
    w0 = np.zeros(D.shape[1])
    res = minimize(f, w0, jac=True, method="L-BFGS-B", options={"maxiter": 500})
    assert res.success or res.status in (1, 2), f"L-BFGS 실패: {res.message}"
    return res.x


def mrr_obj(rows_pd, w):
    rr = []
    for r, pd in rows_pd:
        if r.get("tac") not in FORMS: continue
        b = rank_of(pd, w, use_oh=False)
        rr.append(1.0 / b if b else 0.0)
    return float(np.mean(rr)) if rr else 0.0


def fit_bo(tr_pd, iters=40, init=20):
    """GP-EI 베이지안 최적화 — 학습 겹 MRR 직접 최대화 (4차원)."""
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import Matern
    from scipy.stats import norm
    rng = np.random.default_rng(SEED)
    LO = np.array([0.0, 0.0, 0.0, -2.0])
    HI = np.array([20.0, 20.0, 2.0, 2.0])
    Xs = []; ys = []
    for _ in range(init):
        w = LO + rng.random(4) * (HI - LO)
        Xs.append(w); ys.append(mrr_obj(tr_pd, w))
    gp = GaussianProcessRegressor(kernel=Matern(nu=2.5), normalize_y=True,
                                  alpha=1e-6, random_state=SEED)
    for _ in range(iters):
        gp.fit(np.array(Xs), np.array(ys))
        C = LO + rng.random((512, 4)) * (HI - LO)
        mu, sd = gp.predict(C, return_std=True)
        best = max(ys)
        with np.errstate(divide="ignore", invalid="ignore"):
            z = (mu - best) / np.maximum(sd, 1e-9)
            ei = (mu - best) * norm.cdf(z) + sd * norm.pdf(z)
        w = C[int(np.argmax(ei))]
        Xs.append(w); ys.append(mrr_obj(tr_pd, w))
    return np.array(Xs[int(np.argmax(ys))]), max(ys)


def show(tag, N, RK):
    at = lambda K: sum(1 for x in RK if x <= K) / max(N, 1) * 100
    print(f"   {tag:34s}{N:5d}{at(5):8.1f}%{at(10):8.1f}%{at(20):8.1f}%"
          f"{(st.median(RK) if RK else 0):7.0f}", flush=True)


if __name__ == "__main__":
    rows = load(POOL)
    print(f"■ 완전 학습형 가중치 · {TAG} · {len(rows)}행 · 프로젝트 LOO", flush=True)
    PD = [(r, point_data(r)) for r in rows]
    grps = sorted({r["_g"] for r in rows}, key=str)
    assert len(grps) >= 2, "LOO 하려면 그룹 2+ 필요"

    RES = {k: (0, []) for k in ("A", "B", "C")}
    W_LOG = collections.defaultdict(list)
    for gp_ in grps:
        tr_pd = [(r, pd) for r, pd in PD if r["_g"] != gp_]
        te_pd = [(r, pd) for r, pd in PD if r["_g"] == gp_]
        if not tr_pd or not te_pd: continue
        rng = np.random.default_rng(SEED)
        # A: one-hot 로지스틱
        wA = fit_logistic(pairs_of(tr_pd, True, rng))
        # B: 연속 로지스틱
        wB = fit_logistic(pairs_of(tr_pd, False, rng))
        W_LOG["B"].append(wB)
        # C: GP-EI
        wC, dev = fit_bo(tr_pd)
        W_LOG["C"].append(wC)
        for k, w, oh in (("A", wA, True), ("B", wB, False), ("C", wC, False)):
            n, rk = metrics(te_pd, w, oh)
            N0, R0 = RES[k]; RES[k] = (N0 + n, R0 + rk)

    print(f"\n   {'방식':34s}{'지점':>5s}{'@5':>8s}{'@10':>8s}{'@20':>8s}{'중앙':>7s}")
    show("A 쌍별로지스틱 one-hot (14파라)", *RES["A"])
    show("B 쌍별로지스틱 연속 (4파라)", *RES["B"])
    show("C GP-EI 베이지안최적화 (4파라)", *RES["C"])
    for k in ("B", "C"):
        M = np.stack(W_LOG[k])
        print(f"   {k} 겹별 가중치 [lgg/g lcp/g rig std]:")
        for i, w in enumerate(M):
            print(f"     겹{i}: " + " ".join(f"{x:+7.3f}" for x in w))
    print("TRAINABLE_DONE", flush=True)
