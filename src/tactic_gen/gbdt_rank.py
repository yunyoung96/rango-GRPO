"""★ 학습된 GBDT 로 premise 를 재랭킹한다 — 런타임에서 쓰는 쪽.

`scripts/train_ranker_gbdt.py` 가 저장한 모델(`data/gbdt_ranker.joblib`)을 읽어,
goal 상태와 후보 premise 목록을 주면 점수를 돌려준다.

## 왜 별도 모듈인가

지금까지 GBDT 는 **학습 스크립트 안에서만** 존재했다(학습 → 평가 → 종료). 그래서
다른 실험(assert 질의 검색 등)에서 쓸 수가 없어 어쩔 수 없이 RRF 를 썼다.
특징 추출과 벡터 구성이 **학습 때와 한 글자도 다르면 안 되므로** 여기 한 곳에 모은다.

## 특징 12개 → 36차원

    ① 원시값 (열별 최대로 정규화)
    ② 사례 내 순위 백분위 (0=1등)
    ③ RRF 변환 1/(0.15 + 백분위)

`scripts/dump_retrieval_features.py` 와 **같은 순서**여야 한다:
    0 A'매칭크기 1 B head 2 C 연산자 3 D 모양 4 C'결론head 5 E 가설매칭
    6 tfidf     7 이름subword 8 H 지역성 9 G anti-unify 10 가설수 11 메타변수비
"""
from __future__ import annotations

import collections
import math
import os
import re

import numpy as np

from tactic_gen.tier_rank import (declname, goal_struct, n_hyps,  # noqa: F401
                                  prem_struct, sig_anti_unify, sig_concl_heads,
                                  sig_head, sig_hyp_match, sig_locality,
                                  sig_match_size, sig_ops, sig_shape)

_SUBW = re.compile(r"[._]")
NF = 12
_model = None


def load(path: str | None = None):
    """모델을 한 번만 읽어 캐시한다."""
    global _model
    if _model is None:
        import joblib
        p = path or os.environ.get("GBDT_MODEL", "data/gbdt_ranker.joblib")
        _model = joblib.load(p)
    return _model


def features(state: str, texts: list[str], tfidf: list[float],
             name_tfidf: list[float], cur_file: str = "",
             prem_files: list[str] | None = None,
             cand: list[int] | None = None) -> list[list[float]]:
    """후보마다 12개 특징. `cand` 를 주면 그 인덱스만 계산한다(비용 절감)."""
    n = len(texts)
    idx = list(range(n)) if cand is None else list(cand)
    gs = goal_struct(state)
    pss = {j: prem_struct(texts[j]) for j in idx}
    # ★ IDF 는 **그 사례의 후보 집합 안에서** 계산한다 (학습 때와 동일)
    df: collections.Counter = collections.Counter()
    for j in idx:
        ps = pss[j]
        if ps is not None:
            for k in ps[5]:
                df[k] += 1
    nd = max(len(idx), 1)
    idf = {k: math.log(nd / v) for k, v in df.items()}

    out = [[0.0] * NF for _ in range(n)]
    for j in idx:
        ps = pss[j]
        if gs is None or ps is None:
            f = [0.0] * 6
        else:
            f = [sig_match_size(gs, ps), sig_head(gs, ps), sig_ops(gs, ps),
                 sig_shape(gs, ps), sig_concl_heads(gs, ps, idf),
                 sig_hyp_match(gs, ps)]
        h = sig_locality(cur_file, (prem_files[j] if prem_files else ""))
        gg = sig_anti_unify(gs, ps) if (gs is not None and ps is not None) else 0.0
        nh = n_hyps(texts[j]) if ps is not None else 0.0
        mv = min(float(len(ps[0])), 10.0) / 10.0 if ps is not None else 0.0
        out[j] = f + [tfidf[j], name_tfidf[j], h, gg, nh, mv]
    return out


def _ranks_pct(v):
    n = len(v)
    o = sorted(range(n), key=lambda j: -v[j])
    r = [0.0] * n
    for p, j in enumerate(o):
        r[j] = p / max(n - 1, 1)
    return r


def to_matrix(F: list[list[float]], rrf_k: float = 0.15) -> np.ndarray:
    """12특징 → 36차원. **학습 때와 같은 순서·같은 정규화**여야 한다."""
    n = len(F)
    cols = [[r[c] for r in F] for c in range(NF)]
    pcts = [_ranks_pct(c) for c in cols]
    mx = [max((abs(x) for x in cols[c]), default=1.0) or 1.0 for c in range(NF)]
    return np.array([[F[j][c] / mx[c] for c in range(NF)]
                     + [pcts[c][j] for c in range(NF)]
                     + [1.0 / (rrf_k + pcts[c][j]) for c in range(NF)]
                     for j in range(n)], dtype=np.float32)


def score(state: str, texts: list[str], tfidf: list[float],
          name_tfidf: list[float], cur_file: str = "",
          prem_files: list[str] | None = None,
          cand: list[int] | None = None, path: str | None = None) -> list[float]:
    """gold 일 확률. 큰 값이 상위.

    `cand` 밖의 후보는 **점수를 주지 않고** tfidf 순서를 유지하도록 아주 작은 값을 준다
    — 2단계 검색과 같은 구조다(학습도 tfidf 상위 CAP 개로 했다).
    """
    m = load(path)
    n = len(texts)
    idx = list(range(n)) if cand is None else list(cand)
    F = features(state, texts, tfidf, name_tfidf, cur_file, prem_files, idx)
    X = to_matrix([F[j] for j in idx], m.get("RRF_K", 0.15))
    p = m["clf"].predict_proba(X)[:, 1]
    # 후보 밖은 tfidf 순위로 뒤에 붙인다 (확률 최소값보다 작게)
    rt = _ranks_pct(tfidf)
    out = [-1.0 - rt[j] for j in range(n)]
    for k, j in enumerate(idx):
        out[j] = float(p[k])
    return out


def name_docs(docs, names):
    """이름 subword 를 문서에 두 번 넣은 버전 (특징 7 용). 학습 때와 동일."""
    return [list(d) + [w for w in _SUBW.split(nm or "") if len(w) >= 2] * 2
            for d, nm in zip(docs, names)]
