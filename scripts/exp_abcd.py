#!/usr/bin/env python3
"""★ 통합 실험 — `all_log/docs/premise/experiment.txt` 의 A/B/C/D.

방법론이 바뀔 때마다 이 스크립트를 다시 돌린다. 세 스플릿 · 랭커 여러 종을 **한 번의
순회로** 잰다(데이터 로드와 tfidf·구조신호 계산을 공유한다 — 랭커마다 따로 돌리면
같은 일을 4번 한다).

## 무엇을 재나

  A. gold premise 가 검색 상위에 있는 비율            R@1/20/50 · ALL@1/20/50
  C. gold 가 top50 밖일 때 **L' 을 assert 하고** 그 goal 로 재검색한 L 의 순위
  D. 그 밖에 걸린 이상 징후
  (B 는 Coq 실행이 필요해 `hunt_assert_errors.py` 가 맡는다)

## 지표

분모는 **gold lemma 를 쓰고 그 lemma 가 후보 풀에 실제로 있는 스텝**.

  R@k    필요한 gold 중 **하나라도** 상위 k 안       (관행 지표)
  ALL@k  필요한 gold 를 **전부** 상위 k 안           ← 실제로 중요한 것

프롬프트에 상위 N 개만 들어가므로, tactic 이 lemma 를 2개 쓰는데 하나만 들어가면 모델은
나머지를 지어내야 한다 — 불가능하다.

## 동적 자기검사

실험 **전**에 합성 사례로 랭커·assert 를 점검하고(`--selftest`), 실험 **중**에는 매 스텝
불변식을 확인한다(점수 길이·NaN·gold 인덱스 범위). 깨지면 D 에 쌓이고 즉시 눈에 띈다.

사용:
  python3 scripts/exp_abcd.py --split test --nrank 3000
  python3 scripts/exp_abcd.py --selftest        # 자기검사만
"""
import argparse
import collections
import copy
import json
import math
import os
import re
import sys
import time
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.insert(0, "src")
import logging  # noqa: E402

logging.disable(logging.CRITICAL)
import yaml  # noqa: E402
from data_management.splits import Split  # noqa: E402
from data_management.dataset_file import (DatasetFile, get_ids_from_goal,  # noqa: E402
                                          get_ids_from_sentence)
from data_management.sentence_db import SentenceDB  # noqa: E402
from proof_retrieval.tfidf import tf_idf  # noqa: E402
from premise_selection.premise_filter import PremiseFilter, PremiseFilterConf  # noqa: E402
from tactic_gen.tactic_data import TacticDataConf, LmDataset  # noqa: E402
from tactic_gen.gold_lemma import gold_lemmas  # noqa: E402
from tactic_gen.search_query import local_names  # noqa: E402
from tactic_gen.applicable import (canon, decompose, match, parse,  # noqa: E402
                                   parse_toks, subterms)
from tactic_gen.assert_split import statement_of  # noqa: E402
from tactic_gen.tier_rank import (TierRanker, declname, prem_struct,  # noqa: E402
                                  goal_struct, sig_hyp_match, head_of, sig_au_dist,
                                  au_res_gen, sig_au_f, goal_alpha, prem_alpha,
                                  goal_stmt, prem_stmt,
                                  au_f_alpha, hinge)

# ★ C 국면 질의의 binder 를 개명할지. 기본 끔(옛 측정과 비교 가능하게).
#   켜면 "모델이 자기 말로 assert 를 쓴 경우" 를 재는 것이고, 그것이 실전 조건이다.
C_RENAME = os.environ.get("C_RENAME", "0") == "1"

ap = argparse.ArgumentParser()
ap.add_argument("--split", default="test",
                help="쉼표로 여러 개 가능 — 한 프로세스에서 돌면 토큰 캐시를 공유해 빠르다")
ap.add_argument("--nrank", type=int, default=3000)
ap.add_argument("--rankers", default="tfidf,rrf,struct,gbdt")
ap.add_argument("--stage1", type=int, default=2000)
ap.add_argument("--selftest", action="store_true")
ap.add_argument("--ctr_top", type=int, default=200,
                help="contrastive 로 재정렬할 RRF 상위 개수")
ap.add_argument("--budget", type=int, default=0,
                help="premise 토큰 예산. 0 이면 conf 값(896). "
                     "★ 이 값을 넘으면 프롬프트에서 잘린다")
ap.add_argument("--out", default="")
A = ap.parse_args()
SPLIT = A.split.upper()
BUDGET = A.budget or 896      # conf 의 premise_tokens
CTR_TOP = A.ctr_top
RANKERS = [x for x in A.rankers.split(",") if x]
# ★ 랭커 이름 오타/구버전 이름을 **시작 전에** 잡는다. 예전엔 잘못된 이름이 매 스텝
#   예외로 빠져 결과가 전부 0.0% 로 나왔고, 20분을 버린 뒤에야 알았다.
_KNOWN = {"tfidf", "rrf", "struct", "eq", "eqa", "eqx", "cov", "eqcov",
          "afh80", "afh90", "afh95", "afh100",
          "structural", "structural_mmr", "gbdt", "ctr",
          "hyp", "sub", "cooc", "nsub", "allsig",
          # ★ 반유니피케이션 비유사도 D_λ (future-idea.md ⑮-A)
          #   au      = structural 에서 EQ_W(이진 완전일치) 대신 연속 D_λ
          #   au_eq   = 둘 다 (완전일치 특례 + 거리)
          #   au0/au1 = λ 끝점 확인용 (au0 은 옛 붕괴 재현, au1 은 대칭)
          "au", "au_eq", "au0", "au1",
          # λ 스윕 (au10 = λ0.10 …) + λ 를 아예 없앤 두 신호 RRF 융합
          "au10", "au20", "au50", "au75", "au2sig",
          # ★ F-측도 형태 — λ 대신 β(재현율 가중). β=1 이 정준값.
          #   `res/|concl| = 1−P`, `gen/|goal| = 1−R` 이므로 D_λ 는 정밀도·재현율의
          #   가중합이었다. 조화평균으로 합치면 λ 가 사라진다.
          #   그리고 한쪽이 0 이면 0 이라 **공허한 lemma 가 구조적으로 배제**된다.
          "auf", "auf05", "auf2",
          # ★ logit 결합 — `EQ_W=3.0` 을 유도로 대체한다.
          #   F 를 적용가능성의 **확률**로 보면 증거를 더하는 정준 척도는 로그 오즈다.
          #   logit 은 F=1 에서 극점을 가지므로 **완전일치가 자동으로 압도**한다 —
          #   손으로 정한 3.0 이 하던 일이 정의에서 나온다.
          #   (로그 오즈의 가산 = 독립 증거의 결합, 나이브 베이즈)
          "aul", "aul05", "aul2",
          # ★ 절단형(hinge) — EQ_W 의 **희소성**을 유지한 채 연속화한다.
          #   aul 이 진 원인이 희소성 파괴였다: logit 은 모든 후보에 ±3.45 를 주어
          #   RRF 항(최대 0.017)을 통째로 지웠다(목표 76.6% — 최하위권).
          #   EQ_W 는 완전일치일 때만 발화해서 나머지는 RRF 가 정한다.
          #   hinge 는 F<τ 면 0, F≥τ 면 선형 — EQ_W 는 τ→1 극한이다.
          "aufh", "aufh80", "aufh95",
          # ★ 국면 게이트 모형 — 잠재 국면 z∈{A,C} 의 혼합.
          #   P(p|g) = Σ_z P(z|g)·P(p|g,z) 인데 P(z=C|g) 가 **관측 가능**하다:
          #       τ(g) = max_p F₁(p,g)   ← goal 이 누군가의 명제면 1 에 가깝다
          #   ω(g) = hinge_{τ₀}(τ(g)) 로 게이트를 만들면
          #       score = RRF(tfidf)+RRF(C')  +  ω·[RRF(cov) + W·F₁]
          #   ω≡0 → rrf(A 최고) · ω≡1 → structural 유사(C 최고) ·
          #   ω=[τ=1] 이고 F₁→지시자면 **EQ_W 그 자체**(특수해).
          "gate", "gate80", "gate95"}
# ★ afh 족은 τ 를 이름에 담는다(`afh80` = τ 0.80). 유효 범위만 확인하고 통과시킨다 —
#   목록에 일일이 적으면 τ 하나 바꿀 때마다 "알 수 없는 랭커" 로 죽는다(실제로 겪었다).
_AFH = re.compile(r"^afh([1-9]\d?|100)$")
_bad = [r for r in RANKERS if r not in _KNOWN and not _AFH.match(r)]
if _bad:
    sys.stderr.write(f"알 수 없는 랭커: {_bad}\n사용 가능: {sorted(_KNOWN)}\n")
    sys.exit(2)
KS = (1, 20, 50)
CTR_TOP = 200


class _G:
    def __init__(self, g, h):
        self.goal, self.hyps = g, h


def _query_tree(state: str):
    """state 의 goal 결론을 항 트리로. struct 랭커의 질의.

    ★ goal 이 `forall x y : nat, …` 로 시작할 수 있다(assert 직후의 subgoal 이 그렇다).
      premise 와 **같은 경로**(decompose)로 binder 를 벗겨야 트리가 맞물린다.
    """
    g = state.split("\n\n")[-1] if "\n\n" in state else state
    g = g.strip()
    d = decompose("Lemma _g : " + g.rstrip(". ") + ".")
    t = parse_toks(d[2]) if d is not None else parse(g)
    return canon(t) if t is not None else None


def _rrf_rank(vals, k=60.0):
    """값 → 순위 → 1/(k+순위). 서로 다른 척도의 신호를 합칠 때 쓴다."""
    n = len(vals)
    o = sorted(range(n), key=lambda j: -vals[j])
    r = [0] * n
    for p_, j in enumerate(o):
        r[j] = p_
    return [1.0 / (k + r[j]) for j in range(n)]


def _cov(q_ids, docs, n):
    """질의 토큰을 premise 가 **얼마나 담고 있나** (0~1).

    ★ TF-IDF 의 길이 정규화가 만드는 실패를 정면으로 겨눈다: 질의를 통째로 담고 있는
      긴 lemma 가, 토큰 하나뿐인 짧은 정의에 지는 문제(실측 58/161 건).
      포함률은 문서 길이로 나누지 않으므로 그 편향이 없다.
    """
    if not q_ids:
        return [0.0] * n
    qs = set(q_ids)
    return [len(qs & set(docs[j])) / len(qs) for j in range(n)]


# ★ eq 항의 **받침 측정** — verify_eq_props.py 의 성질 S 를 실측으로 뒷받침한다.
#   "A 국면에서는 거의 발화하지 않고 C 국면에서는 거의 항상 발화한다" 가 자기게이팅의
#   실증이고, 그게 사실이면 τ₀·ω 같은 게이트 매개변수가 필요 없다는 근거가 된다.
PHASE = "A"
EQFIRE = collections.Counter()


def rank_all(state, texts, pool, tf, tr, kinds, docs=None, names=None,
             q_ids=None, dp=None):
    """랭커별 점수를 **한 번의 신호 계산으로** 모두 만든다. 큰 값이 상위."""
    out = {}
    n = len(tf)
    if kinds == ["tfidf"]:
        return {"tfidf": list(tf)}
    base, c2r, apl, ms, au, cand = tr.signals(state, tf)
    rrf = [base[j] + c2r[j] for j in range(n)]

    # ★ 트리 완전일치 — assert 하위목표에서만 발화하고 일반 goal 에서는 거의 안 걸린다.
    #   그래서 **A 를 해치지 않으면서 C 를 살리는** 단일 랭커의 핵심이 된다.
    _eqb = None

    def eq_bonus():
        nonlocal _eqb
        if _eqb is None:
            _eqb = [0.0] * n
            qt = _query_tree(state)
            if qt is not None:
                for j in cand:
                    ps = prem_struct(texts[j])
                    if ps is not None and ps[1] is not None and ps[1] == qt:
                        _eqb[j] = 1.0
            nf = int(sum(_eqb))
            EQFIRE[f"{PHASE}:질의"] += 1
            EQFIRE[f"{PHASE}:후보"] += len(cand)
            EQFIRE[f"{PHASE}:발화"] += nf
            EQFIRE[f"{PHASE}:발화질의"] += (nf > 0)
        return _eqb

    _ab = None

    def alpha_bonus():
        nonlocal _ab
        if _ab is None:
            _ab = [0.0] * n
            ga = goal_alpha(state)
            if ga is not None:
                for j in cand:
                    if prem_alpha(prem_struct(texts[j])) == ga:
                        _ab[j] = 1.0
            nf = int(sum(_ab))
            EQFIRE[f"{PHASE}:α발화"] += nf
            EQFIRE[f"{PHASE}:α발화질의"] += (nf > 0)
        return _ab

    _xb = None

    def stmt_bonus():
        nonlocal _xb
        if _xb is None:
            _xb = [0.0] * n
            gq = goal_stmt(state)
            if gq is not None:
                for j in cand:
                    if prem_stmt(texts[j]) == gq:
                        _xb[j] = 1.0
            nf = int(sum(_xb))
            EQFIRE[f"{PHASE}:x발화"] += nf
            EQFIRE[f"{PHASE}:x발화질의"] += (nf > 0)
        return _xb

    _afv = None

    def af_vals():
        """F₁^α(p, g) — 몫 위의 AU-Dice. τ 여러 개가 이 값을 공유한다."""
        nonlocal _afv
        if _afv is None:
            _afv = [0.0] * n
            gq = goal_stmt(state)
            if gq is not None:
                for j in cand:
                    _afv[j] = au_f_alpha(prem_stmt(texts[j]), gq)
        return _afv

    _covv = None

    def cov_rrf():
        nonlocal _covv
        if _covv is None:
            c = _cov(q_ids or [], docs, n)
            o = sorted(range(n), key=lambda j: -c[j])
            r = [0] * n
            for pp, j in enumerate(o):
                r[j] = pp
            _covv = [1.0 / (60 + r[j]) for j in range(n)]
        return _covv
    for k in kinds:
        if k == "tfidf":
            out[k] = list(tf)
        elif k == "rrf":
            out[k] = rrf
        elif k == "struct":
            # ★ 질의가 lemma 문장일 때 옳은 질문: **항 트리가 같은가**
            qt = _query_tree(state)
            sc = list(rrf)
            if qt is not None:
                for j in cand:
                    ps = prem_struct(texts[j])
                    if ps is None or ps[1] is None:
                        continue
                    if ps[1] == qt:
                        sc[j] += 3.0
                    elif match(ps[1], qt, ps[0], {}):
                        sc[j] += 1.0
            out[k] = sc
        elif k == "eq":
            eb = eq_bonus()
            out[k] = [rrf[j] + 3.0 * eb[j] for j in range(n)]
        elif k.startswith("afh"):
            # ★ 한 족(族)으로 묶는다.
            #     score_τ(p) = RRF(tfidf) + RRF(C') + W·h_τ(F₁^α(p,g))
            #     h_τ(x) = max(0, x−τ)/(1−τ)      h₁ = 1[F₁^α=1] = eqx
            #
            #   옛 `auf`/`aufh` 는 여기에 `cov`(A 를 −6.9pp 해친다)와 **상시 켜진**
            #   RRF(F₁) 을 얹었고, F 도 비대칭(premise binder 만 메타변수)이라 몫 위의
            #   함수가 아니었다. 그 셋을 빼면 남는 것이 이 족이다.
            tau = int(k[3:]) / 100.0
            W = float(os.environ.get("AU_HINGE_W", "3.0"))
            fv = af_vals()
            out[k] = [rrf[j] + W * hinge(fv[j], tau) for j in range(n)]
        elif k == "eqx":
            # ★ 전체 명제(∀mv. h₁→…→c)의 α-정규형 비교.
            #   `eqa` 는 결론만 봐서 `∀x, P x → Q x` 와 `Q a` 가 맞아버린다 —
            #   exact 는 실패한다. 가설을 화살표로 되감으면 **발화 ⟺ exact 성공**.
            #   덤으로 goal 문맥을 추측할 필요가 없어져 정규식 휴리스틱이 사라진다.
            xb = stmt_bonus()
            out[k] = [rrf[j] + 3.0 * xb[j] for j in range(n)]
        elif k == "eqa":
            # ★ α-동치 = L ⊑ g ∧ g ⊑ L — 포섭 선순서를 부분순서로 만드는 표준 몫.
            #   `eq` 는 몫을 안 낸 대표원 비교(이름 의존)이고, `⊑` 단독은 이데알이라
            #   바닥(공허 premise)까지 발화해 A 를 무너뜨린다. 대칭화가 그 사이다.
            ab = alpha_bonus()
            out[k] = [rrf[j] + 3.0 * ab[j] for j in range(n)]
        elif k == "cov":
            cv = cov_rrf()
            out[k] = [rrf[j] + cv[j] for j in range(n)]
        elif k == "eqcov":
            eb, cv = eq_bonus(), cov_rrf()
            out[k] = [rrf[j] + cv[j] + 3.0 * eb[j] for j in range(n)]
        elif k in ("au", "au_eq", "au0", "au1"):
            # ★ D_λ = (size(concl)−size(⊓)) + λ·(size(goal)−size(⊓))
            #   λ=0 은 순수 적용가능성(= 예전에 A 를 45.4→18.2% 로 무너뜨린 설정),
            #   λ=1 은 대칭. 0<λ<1 이 "적용 가능하면서 구체적인 것"을 고른다.
            lam = {"au0": 0.0, "au10": 0.10, "au20": 0.20, "au50": 0.50,
                   "au75": 0.75, "au1": 1.0}.get(
                       k, float(os.environ.get("AU_LAM", "0.35")))
            gs2 = goal_struct("\n" + state if not state.startswith("\n") else state)
            av = [0.0] * n
            if gs2 is not None:
                for j in cand:
                    ps = prem_struct(texts[j])
                    if ps is not None:
                        av[j] = sig_au_dist(gs2, ps, lam)
            # RRF 항으로 결합 — 절대값 대신 순위를 쓴다(스케일 손튜닝 회피)
            o = sorted(range(n), key=lambda j: -av[j])
            rr = [0] * n
            for pp, j in enumerate(o):
                rr[j] = pp
            au_rrf = [1.0 / (60 + rr[j]) for j in range(n)]
            cv = cov_rrf()
            sc = [rrf[j] + cv[j] + au_rrf[j] for j in range(n)]
            if k == "au_eq":                      # 완전일치 특례도 함께
                eb = eq_bonus()
                sc = [sc[j] + 3.0 * eb[j] for j in range(n)]
            out[k] = sc
        elif k in ("gate", "gate80", "gate95"):
            # ★ 국면 게이트 — 이 파일의 핵심 제안.
            #
            #   관찰: 같은 신호가 A 와 C 에서 **정반대로** 작동한다.
            #     cov  : A −4.4pp        C 도움
            #     EQ   : A 0 (미발화)    C +23.6pp (@1)
            #   원인: 두 국면이 **다른 질문**을 던진다.
            #     A — goal 이 어떤 lemma 의 명제도 아니다 → "무엇이 관련 있나"(어휘)
            #     C — 질의가 곧 명제다                    → "무엇이 이 명제인가"(구조)
            #
            #   그래서 국면을 잠재변수로 두고 혼합한다. 그런데 국면이 **관측 가능**하다:
            #     τ(g) = max_p F₁(p,g)  가 1 에 가까우면 C 국면이다.
            #
            #   ω = hinge_{τ₀}(τ) 로 C 국면 특징만 켠다. A 국면에서는 정확히 rrf 가 된다.
            tau0 = {"gate80": 0.80, "gate95": 0.95}.get(k, 0.90)
            W = float(os.environ.get("AU_GATE_W", "3.0"))
            gs2 = goal_struct("\n" + state if not state.startswith("\n") else state)
            fv = [0.0] * n
            if gs2 is not None:
                for j in cand:
                    ps = prem_struct(texts[j])
                    if ps is not None:
                        fv[j] = sig_au_f(gs2, ps, 1.0)
            tau = max(fv) if fv else 0.0
            omega = max(0.0, tau - tau0) / (1.0 - tau0)       # 게이트 ∈ [0,1]
            if omega <= 0.0:
                out[k] = list(rrf)                            # A 국면 = rrf 그대로
            else:
                cv = cov_rrf()
                out[k] = [rrf[j] + omega * (cv[j] + W * fv[j]) for j in range(n)]
        elif k in ("aufh", "aufh80", "aufh95"):
            # ★ score = RRF(tfidf) + RRF(cov) + RRF(F₁) + W·hinge_τ(F₁)
            #     hinge_τ(F) = max(0, F−τ)/(1−τ)      F<τ 면 0 · F=1 이면 1
            #
            #   EQ_W(=3.0×[완전일치]) 는 이것의 **τ→1 극한**이다.
            #   τ<1 로 두면 "거의 완전일치"(F=0.95, 인자 하나 차이)까지 잡으므로
            #   EQ_W 보다 **엄밀히 더 일반적**이면서 희소성은 유지된다.
            tau = {"aufh80": 0.80, "aufh95": 0.95}.get(k, 0.90)
            W = float(os.environ.get("AU_HINGE_W", "3.0"))
            gs2 = goal_struct("\n" + state if not state.startswith("\n") else state)
            fv = [0.0] * n
            if gs2 is not None:
                for j in cand:
                    ps = prem_struct(texts[j])
                    if ps is not None:
                        fv[j] = sig_au_f(gs2, ps, 1.0)
            o = sorted(range(n), key=lambda j: -fv[j])
            rr = [0] * n
            for pp, j in enumerate(o):
                rr[j] = pp
            f_rrf = [1.0 / (60 + rr[j]) for j in range(n)]
            cv = cov_rrf()
            out[k] = [rrf[j] + cv[j] + f_rrf[j]
                      + W * max(0.0, (fv[j] - tau)) / (1.0 - tau) for j in range(n)]
        elif k in ("aul", "aul05", "aul2"):
            # ★ score = RRF(tfidf) + RRF(cov) + w·logit(F_β)
            #
            #   왜 logit 인가: F 를 확률로 보면 로그 오즈가 증거의 정준 척도이고,
            #   가산은 독립 증거의 결합(나이브 베이즈)이다. logit 은 F=1 에서 극점을
            #   가지므로 **완전일치가 자동으로 압도**한다 — `EQ_W=3.0` 의 역할이
            #   손으로 정한 상수가 아니라 **변환의 성질**에서 나온다.
            #
            #   ★ 앞선 실험에서 au 계열이 진 이유가 바로 여기다: F 를 RRF 로 넣으면
            #     F=1.0 이어도 1/60 ≈ 0.017 밖에 못 받는데, structural 의 완전일치
            #     가산은 3.0 이다(180배). 신호가 나빴던 게 아니라 **눌러서** 진 것이다.
            beta = {"aul05": 0.5, "aul2": 2.0}.get(k, 1.0)
            W = float(os.environ.get("AU_LOGIT_W", "0.5"))
            EPS_F = 1e-3                      # logit 발산 방지 → 최대 ±6.9
            gs2 = goal_struct("\n" + state if not state.startswith("\n") else state)
            lv = [0.0] * n
            if gs2 is not None:
                for j in cand:
                    ps = prem_struct(texts[j])
                    if ps is None:
                        continue
                    f = min(max(sig_au_f(gs2, ps, beta), EPS_F), 1 - EPS_F)
                    lv[j] = math.log(f / (1 - f))
            cv = cov_rrf()
            out[k] = [rrf[j] + cv[j] + W * lv[j] for j in range(n)]
        elif k in ("auf", "auf05", "auf2"):
            # ★ F_β(P, R) — λ 를 β 로 대체한다.
            #     P = size(⊓)/size_rigid(concl)   premise 주장 중 쓰인 비율
            #     R = size(⊓)/size(goal)          goal 중 설명된 비율
            #   조화평균이라 한쪽이 0 이면 0 → 공허한 lemma(R≈0)가 자동으로 배제된다.
            #   실측: 공허 케이스가 β=0.5/1/2 **전부에서 0.000** (λ 형태는 λ=0 에서 1.0).
            beta = {"auf05": 0.5, "auf2": 2.0}.get(k, 1.0)
            gs2 = goal_struct("\n" + state if not state.startswith("\n") else state)
            fv = [0.0] * n
            if gs2 is not None:
                for j in cand:
                    ps = prem_struct(texts[j])
                    if ps is not None:
                        fv[j] = sig_au_f(gs2, ps, beta)
            o = sorted(range(n), key=lambda j: -fv[j])
            rr = [0] * n
            for pp, j in enumerate(o):
                rr[j] = pp
            f_rrf = [1.0 / (60 + rr[j]) for j in range(n)]
            cv = cov_rrf()
            out[k] = [rrf[j] + cv[j] + f_rrf[j] for j in range(n)]
        elif k == "au2sig":
            # ★ λ 를 **없앤** 안 — res 와 gen 을 각각 신호로 넣고 RRF 로 융합한다.
            #   RRF 는 순위 기반이라 스케일이 없으므로 "노드 1개가 몇 배" 라는
            #   질문 자체가 사라진다. 손튜닝 상수가 0개다.
            #   대가: 두 신호에 같은 가중치가 걸리고 상호작용을 못 잡는다.
            gs2 = goal_struct("\n" + state if not state.startswith("\n") else state)
            rv = [0.0] * n
            gv = [0.0] * n
            if gs2 is not None:
                for j in cand:
                    ps = prem_struct(texts[j])
                    if ps is None:
                        continue
                    r_, g_ = au_res_gen(gs2, ps)
                    rv[j] = -r_          # 작을수록 좋으므로 부호 반전
                    gv[j] = -g_
            def _rr(vals):
                o = sorted(range(n), key=lambda j: -vals[j])
                rr = [0] * n
                for pp, j in enumerate(o):
                    rr[j] = pp
                return [1.0 / (60 + rr[j]) for j in range(n)]
            rres, rgen = _rr(rv), _rr(gv)
            cv = cov_rrf()
            out[k] = [rrf[j] + cv[j] + rres[j] + rgen[j] for j in range(n)]
        elif k in ("hyp", "sub", "cooc", "nsub", "allsig"):
            # ★ future-idea 의 미시도 신호들 — A(직접 검색)를 올리려는 시도.
            #   cut 은 생성 실패·문법 오류 위험이 있으므로 A 가 높을수록 안전하다.
            add = [0.0] * n
            if k in ("hyp", "allsig"):
                # ③ 가설부 매칭 E — lemma 의 **가설**이 goal 문맥에 이미 있는가.
                #   `apply X` 는 X 의 가설을 새 subgoal 로 남기는데, 이미 있으면
                #   바로 닫히므로 훨씬 유망하다. GBDT 특징엔 있으나 랭커엔 없었다.
                gs2 = goal_struct(state)
                if gs2 is not None:
                    v = [0.0] * n
                    for j in cand:
                        ps = prem_struct(texts[j])
                        if ps is not None:
                            v[j] = sig_hyp_match(gs2, ps)
                    rr = _rrf_rank(v)
                    for j in range(n):
                        add[j] += rr[j]
            if k in ("sub", "allsig"):
                # ⑤ 부분항별 다중 질의 — rewrite 는 lemma 가 goal 의 **부분항**에 맞는다.
                #   결론 전체로 한 번만 질의하면 그걸 놓친다. 부분항마다 질의해 RRF 합.
                gtxt = state.split("\n\n")[-1] if "\n\n" in state else state
                gt = parse(gtxt)
                subs = []
                if gt is not None:
                    for t in list(subterms(canon(gt)))[:6]:
                        h = head_of(t)
                        if h and len(h) > 1:
                            subs.append(h)
                for h in dict.fromkeys(subs):
                    v = [1.0 if h in (texts[j] or "") else 0.0 for j in range(n)]
                    rr = _rrf_rank(v)
                    for j in range(n):
                        add[j] += rr[j] * 0.5
            if k in ("cooc", "allsig"):
                # ⑦ 같은 파일 안에서의 **동시출현 사전확률** — 학습 없이 카운트만.
                #   "이 goal 의 상수를 쓰는 이전 증명들이 자주 쓴 lemma".
                #   여기서는 근사로 **같은 파일 출처** premise 를 우대한다.
                cur = getattr(dp.file_context, "file", "") or ""
                v = [1.0 if (getattr(pool[j], "file_path", "") or "")[-30:] == cur[-30:]
                     else 0.0 for j in range(n)]
                rr = _rrf_rank(v)
                for j in range(n):
                    add[j] += rr[j]
            if k in ("nsub", "allsig"):
                # 이름 서브워드 tfidf — GBDT 특징엔 있으나 랭커엔 없었다.
                from tactic_gen import gbdt_rank
                nsd = gbdt_rank.name_docs(docs, names)
                gl2 = state.split("\n\n")[-1] if "\n\n" in state else state
                h2, g2 = get_ids_from_goal(_G(gl2, []))
                ns = tf_idf(h2 + g2, nsd)
                rr = _rrf_rank(ns)
                for j in range(n):
                    add[j] += rr[j]
            out[k] = [rrf[j] + add[j] for j in range(n)]
        elif k in ("structural", "structural_mmr"):
            # ★ 파이프라인(SparseClient)이 쓰는 것과 **같은 함수**를 부른다 —
            #   하네스와 실제 경로가 갈라지면 측정이 의미를 잃는다.
            from tactic_gen.tier_rank import eqcov_scores
            gl = state.split("\n\n")[-1] if "\n\n" in state else state
            hy = state.split("\n\n")[0].split("\n") if "\n\n" in state else []
            out[k] = eqcov_scores(gl, hy, texts, tf, query_ids=q_ids, docs=docs,
                                  stage1=len(cand), use_mmr=(k == "structural_mmr"))
        elif k == "ctr":
            # ★ cross-encoder 는 후보마다 한 번씩 돌려야 해서 비싸다 → RRF 상위
            #   CTR_TOP 개만 재정렬하고 나머지는 RRF 순서를 유지한다(3단계 구조).
            from tactic_gen import contrastive_rank as CR
            top = sorted(range(n), key=lambda j: -rrf[j])[:CTR_TOP]
            gl = state.split("\n\n")[-1] if "\n\n" in state else state
            cs = CR.score(gl, texts, top)
            if cs:
                # ★ CE 순서로 **덮어쓰면** RRF 신호를 통째로 버린다(실측: 크게 손해).
                #   RRF 융합으로 합친다 — CE 가 약해도 RRF 밑으로 안 떨어진다.
                o = sorted(cs, key=lambda j: -cs[j])
                add = {j: 1.0 / (60 + r) for r, j in enumerate(o)}
                out[k] = [rrf[j] + add.get(j, 0.0) for j in range(n)]
            else:
                out[k] = rrf
        elif k == "gbdt":
            from tactic_gen import gbdt_rank
            gl = state.split("\n\n")[-1] if "\n\n" in state else state
            h_, g_ = get_ids_from_goal(_G(gl, []))
            ns = tf_idf(h_ + g_, gbdt_rank.name_docs(docs, names))
            out[k] = gbdt_rank.score(state, texts, tf, ns, cand=cand)
        else:
            raise ValueError(k)
    return out


# ★ 검색 순위가 아니라 **프롬프트에 실제로 들어가는가**로 판정한다.
#   `whole_number_allocate` 는 앞에서부터 담다가 예산이 넘으면 **break** 한다
#   → 순위 k 가 들어가려면 1..k 위 길이 합이 예산 이내여야 한다.
#   실측: 검색이 넘긴 62개(중앙) 중 프롬프트엔 16개(중앙)만 들어간다.
_TOKLEN: dict = {}


def _tlen(t: str) -> int:
    """premise 토큰 길이. **같은 premise 가 여러 스텝에 반복 등장**하므로 캐시가 크게 먹는다
    (실측: 캐시 없이 2.90초/건 → 있으면 그 절반 이하)."""
    v = _TOKLEN.get(t)
    if v is None:
        v = len(_TOK.tokenize(t))
        _TOKLEN[t] = v
    return v


def n_in_prompt(texts, order, budget: int) -> int:
    """랭킹 순서대로 담았을 때 **프롬프트에 들어가는 개수**."""
    left = budget
    k = 0
    for j in order:
        left -= _tlen(texts[j])
        if left < 0:
            break
        k += 1
    return k


def recall_prompt(sc, gset, names, texts, budget):
    """**두 기준을 분리해서** 돌려준다.

    ★ 표기 규칙 (혼동 방지):
        [순위]     검색 점수 상위 k 안에 있는가 — **프롬프트 예산과 무관**
        [프롬프트]  토큰 예산 안에 살아남아 **실제로 프롬프트에 들어가는가**

      예전에는 `top20` 열이 "순위 20 안 **이면서** 프롬프트에도 있음" 이라
      두 기준이 섞여 있었다. 프롬프트에 들어가는 것이 중앙 22개뿐이라
      top50 과 프롬프트 기준이 같은 값이 되어 오해를 낳았다.

    반환: (순위_best, 순위_worst, 프롬프트_best, 프롬프트_worst, nfit)
    """
    order = sorted(range(len(sc)), key=lambda j: -sc[j])
    nfit = n_in_prompt(texts, order, budget)
    pos = {j: r for r, j in enumerate(order)}
    BIG = 10 ** 9
    per_rank, per_pr = {}, {}
    for j in gset:
        nm = names[j]
        per_rank[nm] = min(per_rank.get(nm, BIG), pos[j])
        per_pr[nm] = min(per_pr.get(nm, BIG), pos[j] if pos[j] < nfit else BIG)
    return (min(per_rank.values()), max(per_rank.values()),
            min(per_pr.values()), max(per_pr.values()), nfit)


def recall(sc, gset, names):
    o = sorted(range(len(sc)), key=lambda j: -sc[j])
    pos = {j: r for r, j in enumerate(o)}
    best = min(pos[j] for j in gset)
    per = {}
    for j in gset:
        per[names[j]] = min(per.get(names[j], 10 ** 9), pos[j])
    return best, max(per.values())


# ══ 실험 전 동적 자기검사 ═════════════════════════════════════════════════
def selftest() -> int:
    """합성 사례로 랭커가 **상식적인 순서**를 내는지 확인한다.

    여기서 깨지면 큰 실험을 돌릴 이유가 없다 — 몇 시간을 버리기 전에 잡는다.
    """
    bad = 0
    POOL = ["Lemma add_comm : forall x y : nat, x + y = y + x.",
            "Lemma mul_comm : forall x y : nat, x * y = y * x.",
            "Lemma add_assoc : forall x y z : nat, x + (y + z) = x + y + z.",
            "Lemma le_refl : forall n : nat, n <= n.",
            "Lemma add_0 : forall n : nat, n + 0 = n."]
    st = "a, b : nat\n\na + b = b + a"
    docs = [d.split() for d in POOL]
    tf = tf_idf(["+", "+"], docs)
    tr = TierRanker(POOL, stage1=100)
    sc = rank_all(st, POOL, POOL, tf, tr, ["rrf", "struct"], docs, [None] * 5)
    for k, v in sc.items():
        top = max(range(len(POOL)), key=lambda j: v[j])
        ok = (top == 0)
        print(f"   [{'✓' if ok else '✗'}] {k:7s} `a+b=b+a` 로 add_comm 이 1위인가 "
              f"→ {POOL[top].split(':')[0].strip()}")
        bad += (not ok)
    # 점수 위생
    for k, v in sc.items():
        if len(v) != len(POOL) or any(not math.isfinite(x) for x in v):
            print(f"   [✗] {k}: 점수 길이/NaN 이상")
            bad += 1
    # ★ eqa — α-동치가 **이름에 의존하지 않는가**. 여기가 깨지면 eqa 는 eq 의
    #   비싼 복사본이 되고, 그러면 "구조만 본다" 는 주장 자체가 거짓이 된다.
    _prem = "Lemma add_comm x y : x + y = y + x."
    _sub = "\n\n" + (statement_of("Lemma add_comm (p q : nat) : p + q = q + p.") or "")
    _ok = prem_alpha(prem_struct(_prem)) == goal_alpha(_sub)
    print(f"   [{'✓' if _ok else '✗'}] eqa  이름이 달라도 α-동치로 잡는가 "
          f"(x,y ↔ p,q) → {_ok}")
    bad += (not _ok)
    #   그리고 **바닥(공허 premise)에는 발화하면 안 된다** — ⊑ 단독이 A 를 무너뜨린
    #   원인이 정확히 바닥이었다. 대칭화가 그것을 걸러내는지 여기서 못박는다.
    _bot = prem_alpha(prem_struct("Lemma triv (P : Prop) (h : P) : P."))
    _ok2 = _bot != goal_alpha(_sub)
    print(f"   [{'✓' if _ok2 else '✗'}] eqa  공허 premise(⊥)에는 발화하지 않는가 → {_ok2}")
    bad += (not _ok2)
    # ★ eqx — **발화 ⟺ exact 성공** 을 못박는다. 여기가 깨지면 랭커가 exact 로
    #   닫히지 않는 premise 를 1순위로 올린다(= cut 이 컴파일에 실패한다).
    _EX = [("C 국면 subgoal · 이름 다름", "\n\nforall p q : nat, p + q = q + p",
            "Lemma add_comm x y : x + y = y + x.", True),
           ("가설 lemma vs 결론만 같은 goal", "a : nat\n\nQ a",
            "Lemma foo : forall x, P x -> Q x.", False),
           ("가설 개수 다름", "\n\nforall x : nat, Q x",
            "Lemma foo : forall x, P x -> Q x.", False),
           ("공허 premise(⊥)", "\n\nforall a b : nat, a + b = b + a",
            "Lemma triv (P : Prop) (h : P) : P.", False)]
    _nb = 0
    for _tag, _st, _p, _want in _EX:
        _g = goal_stmt(_st)
        _got = _g is not None and prem_stmt(_p) == _g
        if _got != _want:
            print(f"   [✗] eqx  {_tag}: 발화={_got} 기대={_want}")
            _nb += 1
    print(f"   [{'✓' if not _nb else '✗'}] eqx  발화 ⟺ exact 성공 ({len(_EX)}건)")
    bad += _nb
    # ★ afh100 (τ=1) 이 eqx 와 **완전히 같은 점수**인가 — "eqx 는 족의 끝점" 이라는
    #   주장이 코드에서도 참인지 못박는다. 논문의 그림이 여기에 걸려 있다.
    # ★ C_RENAME 경로를 직접 태운다 — 이 코드는 C 국면에서만 실행되므로
    #   자기검사가 안 태우면 오타 하나도 실험 30분 뒤에야 드러난다(실제로 겪었다).
    _pq = statement_of("Lemma add_comm (a b : nat) : a + b = b + a.") or ""
    _dq = decompose("Lemma _g : " + _pq.rstrip(". ") + ".")
    _rq = _pq
    if _dq is not None and _dq[0]:
        for _i, _v in enumerate(sorted(_dq[0])):
            _rq = re.sub(r"(?<![\w'])" + re.escape(_v) + r"(?![\w'])", "zq%d" % _i, _rq)
    _rok = ("zq0" in _rq and "zq1" in _rq
            and prem_stmt("Lemma add_comm x y : x + y = y + x.") == goal_stmt("\n\n" + _rq))
    print(f"   [{'✓' if _rok else '✗'}] C_RENAME 개명 질의가 α-동치로 잡히는가 → {_rq[:46]}")
    bad += (not _rok)

    _st2 = "\n\nforall (x y : nat), x + y = y + x"
    _sc2 = rank_all(_st2, POOL, POOL, tf, tr, ["eqx", "afh100"], docs,
                    [None] * len(POOL), q_ids=[0, 1])
    _same = _sc2["eqx"] == _sc2["afh100"]
    print(f"   [{'✓' if _same else '✗'}] afh100(τ=1) 점수가 eqx 와 동일한가 (족의 끝점) → {_same}")
    bad += (not _same)
    # assert 변환 + 이름 충돌
    from tactic_gen import assert_split as AS
    AS.WHY.clear()
    tr2 = AS.transform_with_types(
        "apply L", [("L", "forall n : nat, n <= n")],
        state="H_asrt0 : True\n\nn <= n", proof_script="intros n H_asrt0.")
    ok = tr2 is not None and "H_asrt0" not in tr2.split("as ")[1][:12]
    print(f"   [{'✓' if ok else '✗'}] assert 이름이 기존 H_asrt0 을 피하는가 → "
          f"{tr2.splitlines()[0] if tr2 else 'None'}")
    bad += (not ok)
    # ★ 변환 반환형 — 필터 계측 모드(ASSERT_RISK=0)에서 False 가 새면
    #   호출부가 문자열로 쓰다 TypeError 로 죽는다(실측: B 실험이 190/200 에서 크래시).
    for tac, apps in [("apply L", [("L", "forall n:nat, n<=n")]),
                      ("apply Q", [("L", "forall n:nat, n<=n")]),
                      ("apply L", [("L", "forall (T:eqType)(x:T), x==x")]),
                      ("rewrite ?L", [("L", "forall n:nat, n+0=n")]),
                      ("apply L", [("L", "forall n, P ?x n")])]:
        AS.WHY.clear()
        r = AS.transform_with_types(tac, apps, state="", proof_script="")
        if not (r is None or isinstance(r, str)):
            print(f"   [✗] 변환 반환형 이상: {tac} → {type(r).__name__}")
            bad += 1

    # ★ evar 구제 — `?x` 가 있는 타입은 `_` + eassert 로 살려야 한다
    AS.WHY.clear()
    r = AS.transform_with_types(
        "apply L", [("L", "forall (l : list ?A) (d : ?A), nth 0 l d = d")],
        state="", proof_script="")
    ok = r is not None and r.startswith("eassert") and "?" not in r.split("as ")[0]
    print(f"   [{'✓' if ok else '✗'}] evar 타입이 eassert + _ 로 구제되는가 → "
          f"{(r or 'None').splitlines()[0][:70]}")
    bad += (not ok)

    # gold lemma 추출
    from tactic_gen.gold_lemma import gold_lemmas as GL
    cases = [("apply Nat.add_comm.", {"add_comm"}),
             ("rewrite <- app_assoc.", {"app_assoc"}),
             ("by rewrite -catA.", {"catA"}),
             ("exact: foo_bar.", {"foo_bar"}),
             ("intros n.", set())]
    for tac, exp in cases:
        got = set(GL(tac, set()))
        ok = got == exp
        if not ok:
            print(f"   [✗] gold_lemma `{tac}` → {got} (기대 {exp})")
            bad += 1
    print(f"   자기검사: {'통과' if bad == 0 else str(bad) + '건 실패'}")
    return bad


print(f"■ 실험 전 동적 자기검사", flush=True)
nbad = selftest()
if A.selftest:
    sys.exit(1 if nbad else 0)
if nbad:
    print(f"   ★ 자기검사 {nbad}건 실패 — 그래도 진행하되 결과를 의심할 것", flush=True)

# ══ 데이터 ════════════════════════════════════════════════════════════════
from transformers import AutoTokenizer  # noqa: E402

cc = yaml.safe_load(open("all_log/ft_qwen3b_v8_conf.yaml"))
_TOK = AutoTokenizer.from_pretrained(cc["model_name"])
tdc = copy.deepcopy(cc["tactic_data"])
tdc["formatter_conf"].pop("proof_ret", None)
tdc["formatter_conf"].pop("num_proofs", None)
conf = TacticDataConf.from_yaml(tdc)
ds = LmDataset.from_conf(conf, getattr(Split, SPLIT), 200000)
sdb = SentenceDB.load(conf.sentence_db_loc)
pf = PremiseFilterConf.from_yaml(tdc["formatter_conf"]["premise"]["premise_filter"])
pfilter = PremiseFilter(pf.coq_excludes, pf.non_coq_excludes, pf.general_excludes)

RA = {r: collections.Counter() for r in RANKERS}
ALLA = {r: collections.Counter() for r in RANKERS}
RC = {r: collections.Counter() for r in RANKERS}
ALLC = {r: collections.Counter() for r in RANKERS}
D = collections.Counter()
# ★ 예제별 **복합 성공** 불리언. 목표지표 A + (1−A)×C 는 이 불리언의 평균과 같다.
#   집계만 있으면 두 랭커를 **독립 표본**으로 비교하게 되어 CI 가 크게 나온다.
#   같은 예제를 같은 후보 풀로 재는 **쌍 비교**(McNemar)면 공통 분산이 상쇄되어
#   훨씬 작은 차이도 유의하게 가른다. 저장 비용은 랭커당 불리언 하나뿐이다.
PAIRED = collections.defaultdict(list)
TM = collections.Counter()
nA = nC = nmulti = nCname = nCmulti = 0
NFIT = []
t0 = time.time()

for i in range(200000):
    if nA >= A.nrank:
        break
    try:
        e = ds.raw_example(i)
    except Exception:
        continue
    st = getattr(e, "proof_state", "") or ""
    tac = (e.next_steps[0] if getattr(e, "next_steps", None) else "").strip()
    golds = gold_lemmas(tac, local_names(st))
    if not golds:
        continue
    sid = ds.shuffled_idx.get_idx(ds.split, i)
    try:
        dp = DatasetFile.load(conf.data_loc / "data_points" / sid.file, sdb)
        proof = dp.proofs[sid.proof_idx]
        step = proof.steps[sid.step_idx]
    except Exception:
        D["DatasetFile 로드 실패"] += 1
        continue
    if not step.goals:
        continue
    pool = [p for p in dp.get_premises_before(proof) if pfilter.filter_premise(p)]
    if not pool:
        D["후보 풀이 비어 있음"] += 1
        continue
    texts = [getattr(p, "text", "") or "" for p in pool]
    names = [declname(t) for t in texts]
    gset = {j for j, nm in enumerate(names) if nm and nm in golds}
    if not gset:
        D["gold 가 풀에 없음(랭킹으로 해결 불가)"] += 1
        continue
    nA += 1
    nmulti += (len({names[j] for j in gset}) >= 2)

    docs = [get_ids_from_sentence(p) for p in pool]
    h_ids, g_ids = get_ids_from_goal(step.goals[0])
    tf = tf_idf(h_ids + g_ids, docs)
    tr = TierRanker(texts, stage1=A.stage1)
    ta = time.time()
    PHASE = "A"
    try:
        sc = rank_all(st, texts, pool, tf, tr, RANKERS, docs, names,
                      q_ids=h_ids + g_ids, dp=dp)
    except Exception as ex:
        D[f"랭킹 예외: {type(ex).__name__} {str(ex)[:40]}"] += 1
        continue
    TM["rank"] += time.time() - ta

    # ── 실험 중 불변식 검사 ──────────────────────────────────────────────
    _aok = {}                      # 예제별: A 단계(ALL·P)에서 성공했나
    for r, v in sc.items():
        if len(v) != len(pool):
            D[f"불변식: {r} 점수 길이 불일치"] += 1
            continue
        if any(not math.isfinite(x) for x in v):
            D[f"불변식: {r} 에 NaN/Inf"] += 1
            continue
        rb, rw, pb, pw, nfit = recall_prompt(v, gset, names, texts, BUDGET)
        NFIT.append(nfit)
        for k in KS:
            RA[r][k] += (rb < k)          # [순위] 기준
            ALLA[r][k] += (rw < k)
        RA[r]["P"] += (pb < 10 ** 9)      # [프롬프트] 기준
        ALLA[r]["P"] += (pw < 10 ** 9)
        _aok[r] = (pw < 10 ** 9)          # ALL·P 기준으로 A 가 성공했나

    # ── C: 못 찾은 gold **하나하나** 에 대해 L' 을 세우고 그 L 이 잡히나 ───
    #   ★ 예전엔 gold 중 첫 번째 하나로만 질의를 만들고 순위는 전체 중 최선을 봤다.
    #     tactic 이 lemma 를 2개 쓰면 assert 도 2개 만들어야 하므로, **각 gold 마다**
    #     따로 L' 을 세워 그 gold 자신이 잡히는지를 재야 맞다. ALL 도 그래야 의미가 있다.
    # ★ cut 대상 판정은 **프롬프트에 들어가는가** 기준이다(검색 순위가 아니라).
    #   검색이 62개를 넘겨도 프롬프트엔 16개만 들어간다 — 나머지는 모델이 못 읽는다.
    ref = "rrf" if "rrf" in sc else RANKERS[0]
    o_ = sorted(range(len(pool)), key=lambda j: -sc[ref][j])
    nfit_ref = n_in_prompt(texts, o_, BUDGET)
    rpos = {j: r_ for r_, j in enumerate(o_)}
    per_name = {}
    for j in gset:
        per_name.setdefault(names[j], []).append(j)
    missing = {nm: js for nm, js in per_name.items()
               if min(rpos[j] for j in js) >= nfit_ref}
    if missing:
        found = {r: {k: True for k in list(KS) + ["P"]} for r in RANKERS}
        any_ok = {r: {k: False for k in list(KS) + ["P"]} for r in RANKERS}
        cnt = 0
        for nm, js in missing.items():
            g0 = js[0]
            d = decompose(texts[g0])
            if d is None:
                D["C: gold 문장 파싱 실패 → L' 을 못 만듦"] += 1
                for r in RANKERS:
                    for k in KS:
                        found[r][k] = False
                continue
            # ★ 실제 파이프라인은 `assert (statement_of(L)) as H. { exact L. }` 를 쓴다.
            #   그 subgoal 은 **∀ binder 를 포함한 전체 statement** 이지 결론부가 아니다.
            #   결론부만 질의로 쓰면 이름이 gold 것 그대로라 eq 가 공짜로 맞아
            #   C 수치가 낙관적으로 나온다(측정 편향).
            q = statement_of(texts[g0]) or " ".join(d[2])
            # ★ C_RENAME=1 — 명제의 **binder 를 개명**해서 질의한다.
            #   실제 추론에서는 모델이 assert 를 자기 말로 쓰므로 변수 이름이 gold 와
            #   다르다. gold 의 이름을 그대로 넘겨주면 `eq`(이름 비교)가 공짜로 맞아
            #   이름 강건성을 **원리적으로 측정할 수 없다.** 이것이 그 편향을 없앤다.
            if C_RENAME:
                _dq = decompose("Lemma _g : " + q.rstrip(". ") + ".")
                if _dq is not None and _dq[0]:
                    for _i, _v in enumerate(sorted(_dq[0])):
                        q = re.sub(r"(?<![\w'])" + re.escape(_v) + r"(?![\w'])",
                                   "zq%d" % _i, q)
            hyp = st.split("\n\n")[0] if "\n\n" in st else ""
            st2 = (hyp + "\n\n" + q) if hyp else ("\n\n" + q)
            _, qi = get_ids_from_goal(_G(q, []))
            tf2 = tf_idf(qi, docs)
            tr2 = TierRanker(texts, stage1=A.stage1)
            PHASE = "C"
            try:
                sc2 = rank_all(st2, texts, pool, tf2, tr2, RANKERS, docs, names,
                               q_ids=qi, dp=dp)
            except Exception as ex:
                D[f"C 랭킹 예외: {type(ex).__name__} {str(ex)[:40]}"] += 1
                for r in RANKERS:
                    for k in KS:
                        found[r][k] = False
                continue
            cnt += 1
            for r, v in sc2.items():
                o2 = sorted(range(len(pool)), key=lambda j: -v[j])
                nf2 = n_in_prompt(texts, o2, BUDGET)
                p2 = {j: rr for rr, j in enumerate(o2)}
                # ★ **그 gold 자신**이 프롬프트에 들어가는가
                b2 = min(p2[j] for j in js)           # [순위] 기준
                for k in KS:
                    if b2 < k:
                        any_ok[r][k] = True
                    else:
                        found[r][k] = False
                if b2 < nf2:                          # [프롬프트] 기준
                    any_ok[r]["P"] = True
                else:
                    found[r]["P"] = False
        if cnt:
            nC += 1
            nCname += len(missing)
            nCmulti += (len(missing) >= 2)
            for r in RANKERS:
                for k in list(KS) + ["P"]:
                    RC[r][k] += any_ok[r][k]      # R: 하나라도
                    ALLC[r][k] += found[r][k]     # ALL: 전부
                # 복합: A 로 잡았거나(위) C 로 전부 건졌으면 성공
                PAIRED[r].append(bool(_aok.get(r)) or bool(found[r]["P"]))
        else:
            for r in RANKERS:
                PAIRED[r].append(bool(_aok.get(r)))
    else:
        for r in RANKERS:
            PAIRED[r].append(bool(_aok.get(r)))
    if nA % 100 == 0:
        el = time.time() - t0
        print(f"   {nA}/{A.nrank}  ({el:.0f}s · {el/max(nA,1):.2f}s/건 · "
              f"C {nC}건 · D {sum(D.values())}건)", flush=True)

# ══ 출력 ══════════════════════════════════════════════════════════════════
def row(lbl, cnt, n):
    return f"      {lbl:16s}" + " ".join(f"{cnt[k]/max(n,1)*100:7.1f}%" for k in KS)


print(f"\n{'='*76}")
print(f"■ {SPLIT} · stage1 {A.stage1} · {time.time()-t0:.0f}s")
print(f"{'='*76}")
_nf = sorted(NFIT) if NFIT else [0]
print(f"\n※ 프롬프트 예산 {BUDGET} 토큰 → 실제로 들어가는 premise "
      f"중앙 {_nf[len(_nf)//2]}개 (p10 {_nf[len(_nf)//10]} · p90 {_nf[len(_nf)*9//10]})")
print(f"   ★ 열 표기:  @k[순위] = 검색 상위 k 안 (프롬프트 예산 무관)")
print(f"              [프롬프트] = 토큰 예산 안에 살아남아 실제로 들어감 ← **실제 기준**")
print(f"      행 표기:  · R = 필요한 gold 중 하나라도 / · ALL = 전부")

print(f"\n【A】 gold premise 가 프롬프트에 들어가는 비율")
print(f"      분모: gold lemma 를 쓰고 그 lemma 가 후보 풀에 있는 스텝 {nA}건")
print(f"           (그중 lemma 2개 이상 필요 {nmulti}건 = {nmulti/max(nA,1)*100:.1f}%)")
print(f"      {'':16s}" + " ".join(f"{'@'+str(k)+'[순위]':>10s}" for k in KS)
      + f" |{'[프롬프트]':>12s}")
for r in RANKERS:
    print(f"      {r+' · R':16s}"
          + " ".join(f"{RA[r][k]/max(nA,1)*100:9.1f}%" for k in KS)
          + f" |{RA[r]['P']/max(nA,1)*100:11.1f}%")
for r in RANKERS:
    print(f"      {r+' · ALL':16s}"
          + " ".join(f"{ALLA[r][k]/max(nA,1)*100:9.1f}%" for k in KS)
          + f" |{ALLA[r]['P']/max(nA,1)*100:11.1f}%")

print(f"\n【C】 못 찾은 gold **마다** L' 을 assert 하고 그 goal 로 재검색했을 때")
print(f"      분모: 위 {nA}건 중 top50 밖 gold 가 있던 {nC}건")
print(f"           (그 안에서 만든 L' 총 {nCname}개 · L' 을 2개 이상 만들어야 한 스텝 "
      f"{nCmulti}건 = {nCmulti/max(nC,1)*100:.1f}%)")
if nC:
    print(f"      {'':16s}" + " ".join(f"{'@'+str(k)+'[순위]':>10s}" for k in KS)
          + f" |{'[프롬프트]':>12s}")
    for r in RANKERS:
        print(f"      {r+' · R':16s}"
              + " ".join(f"{RC[r][k]/max(nC,1)*100:9.1f}%" for k in KS)
              + f" |{RC[r]['P']/max(nC,1)*100:11.1f}%")
    for r in RANKERS:
        print(f"      {r+' · ALL':16s}"
              + " ".join(f"{ALLC[r][k]/max(nC,1)*100:9.1f}%" for k in KS)
              + f" |{ALLC[r]['P']/max(nC,1)*100:11.1f}%")
else:
    print("      (해당 사례 없음)")

# ★ experiment.txt 의 목표 지표: A 로 잡은 것 + 못 잡은 것을 assert 로 건진 것
print(f"\n【목표】 A + (1-A)×C  — experiment.txt 기준 90~95% 필요")
print(f"      ※ C 는 'A 가 top50 밖'인 사례가 분모이므로 이렇게 합성한다.")
print(f"      {'':16s}" + f"{'R@50':>10s}{'ALL@50':>10s}   {'R@20':>10s}{'ALL@20':>10s}")
best = (None, -1)
for r in RANKERS:
    line = f"      {r:16s}"
    for k in (50, 20):
        for cnt_a, cnt_c in ((RA, RC), (ALLA, ALLC)):
            a_ = cnt_a[r][k] / max(nA, 1)
            c_ = cnt_c[r][k] / max(nC, 1)
            tot = a_ + (1 - a_) * c_
            line += f"{tot*100:9.1f}%"
            if k == 50 and cnt_a is ALLA and tot > best[1]:
                best = (r, tot)
        if k == 50:
            line += "   "
    print(line)
print(f"      → ALL@50 기준 최선: {best[0]} {best[1]*100:.1f}%")
print(f"\n      ★ 프롬프트 포함(P) 기준 — 실제 학습이 쓰는 값")
print(f"      {'':16s}{'R·P':>10s}{'ALL·P':>10s}")
for r in RANKERS:
    a_ = RA[r]["P"] / max(nA, 1)
    c_ = RC[r]["P"] / max(nC, 1)
    aa = ALLA[r]["P"] / max(nA, 1)
    cc_ = ALLC[r]["P"] / max(nC, 1)
    print(f"      {r:16s}{(a_+(1-a_)*c_)*100:12.1f}%{(aa+(1-aa)*cc_)*100:14.1f}%")

# ── 쌍 비교 (McNemar) ────────────────────────────────────────────────────
#   ★ 왜 필요한가: 랭커들은 **같은 예제·같은 후보 풀**을 본다. 그래서 두 랭커의
#     차이를 독립 표본 CI(±1.2pp @ n=1500)로 재면 공통 분산까지 오차로 세게 되어
#     실제로 유의한 차이를 "구분 불가" 로 잘못 판정한다.
#     불일치 쌍만 세는 McNemar 는 그 공통 분산이 상쇄되므로 훨씬 예민하다.
#     b = 이긴 쪽만 성공한 예제 수 · c = 진 쪽만 성공한 예제 수.
#     H0 아래 b ~ Binom(b+c, 1/2) 이므로 정확 이항검정을 쓴다(근사 없이).
if PAIRED and len(PAIRED) > 1:
    _n = min(len(v) for v in PAIRED.values())
    _rate = {r: sum(PAIRED[r][:_n]) / max(_n, 1) for r in PAIRED}
    _best = max(_rate, key=lambda r: _rate[r])

    def _binom_p(b, c):
        """정확 이항 양측검정 P(|X−(b+c)/2| ≥ |b−(b+c)/2|), X~Binom(b+c, 1/2)."""
        m = b + c
        if m == 0:
            return 1.0
        k = max(b, c)
        tail = sum(math.comb(m, j) for j in range(k, m + 1)) / (2 ** m)
        return min(1.0, 2 * tail)

    print(f"\n【P】 쌍 비교 (McNemar 정확검정) — 기준 `{_best}` {_rate[_best]*100:.1f}%")
    print(f"      같은 예제 {_n}건을 같은 후보 풀로 재므로 **쌍 비교**가 맞다.")
    print(f"      b = 기준만 성공 · c = 상대만 성공 · 차이는 (b−c)/n")
    print(f"      {'랭커':16s}{'ALL·P':>8}{'차이':>9}{'b':>6}{'c':>6}{'p':>10}  판정")
    for r in RANKERS:
        if r == _best or r not in PAIRED:
            continue
        b = sum(1 for i in range(_n) if PAIRED[_best][i] and not PAIRED[r][i])
        c = sum(1 for i in range(_n) if not PAIRED[_best][i] and PAIRED[r][i])
        pv = _binom_p(b, c)
        d = (b - c) / max(_n, 1) * 100
        mark = "유의" if pv < 0.05 else "구분 불가"
        print(f"      {r:16s}{_rate[r]*100:7.1f}%{d:+8.2f}{b:6d}{c:6d}{pv:10.4f}  {mark}")


if D:
    print(f"\n【D】 그 밖에 걸린 것")
    for k, v in D.most_common(15):
        print(f"      [{v:6d}] {k}")

    # ── eq 항의 받침 (자기게이팅 실측) ────────────────────────────────────
    #   verify_eq_props.py 성질 S: 1[d₀=0]≠0 ⟹ τ(g)=1 이므로 이 항은 C 국면에만
    #   받침을 갖는다. A 에서 거의 0 · C 에서 거의 1 이면 게이트 매개변수가 불필요하다.
    if EQFIRE:
        print(f"\n【E】 eq 항이 실제로 언제 발화하나 (성질 S 의 실측)")
        print(f"      {'국면':6s} {'질의수':>8} {'발화한 질의':>12} {'후보당 발화율':>14}")
        for ph in ("A", "C"):
            q = EQFIRE[f"{ph}:질의"]
            if not q:
                continue
            fq = EQFIRE[f"{ph}:발화질의"]
            nc = max(EQFIRE[f"{ph}:후보"], 1)
            print(f"      {ph:6s} {q:8d} {fq/q*100:11.1f}% "
                  f"{EQFIRE[f'{ph}:발화']/nc*100:13.4f}%")

res = {"split": SPLIT, "stage1": A.stage1, "nA": nA, "nC": nC, "nmulti": nmulti,
       "rankers": RANKERS,
       "A_R": {r: dict(RA[r]) for r in RANKERS},
       "A_ALL": {r: dict(ALLA[r]) for r in RANKERS},
       "C_R": {r: dict(RC[r]) for r in RANKERS},
       "C_ALL": {r: dict(ALLC[r]) for r in RANKERS},
       "paired": {r: [int(x) for x in PAIRED[r]] for r in PAIRED},
       "nCname": nCname, "nCmulti": nCmulti,
       "D": dict(D), "sec": round(time.time() - t0, 1)}
out = A.out or ("/tmp/claude-0/-app-coq-modeling/e02d0688-7cb1-43a8-aa0e-ee8afd60ce19/"
                f"scratchpad/abcd_{SPLIT.lower()}.json")
Path(out).write_text(json.dumps(res, ensure_ascii=False, indent=1))
print(f"\n   → {out}")
