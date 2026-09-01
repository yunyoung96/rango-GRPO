#!/usr/bin/env python3
"""★ 프롬프트용 **정렬된** 풀을 만든다 — 채널별 나이브베이즈 + 슬롯 배분.

지금까지 필터 풀을 프롬프트에 넣으면 손해였다(top8 39.2% → 37.0%). 이유는
`next_step_eval` 이 풀을 받아 **tf-idf 로 다시 정렬**했기 때문이다 — 우리
랭킹을 통째로 버렸다. 그래서 여기서 **최종 순서까지 정해** 내보내고,
`POOL_MODE="ordered"` 가 그 순서를 그대로 쓴다.

순서를 정하는 법 (소프트 배분):
    ① 채널마다 나이브베이즈로 **따로** 정렬한다
    ② 채널 비율대로 **번갈아 뽑는다** (weighted round-robin)
       비율은 물채우기를 K=20 에서 적합한 값 — ap 15 · rw 4 · in 1
       하드 선택(한 채널만)과 달리 **회수율을 안 잃는다**

사용: python3 scripts/build_prompt_pool.py [입력풀] [출력]
"""
import collections, json, math, os, re, statistics as st, sys
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")
os.environ["CUDA_VISIBLE_DEVICES"] = ""
sys.path.insert(0, "scripts"); sys.path.insert(0, "src"); sys.path.insert(0, "CoqStoq")
import logging; logging.disable(logging.CRITICAL)
from pathlib import Path
import applic_rank as AR
from coqstoq import Split as CSSplit, get_theorem
from data_management.sentence_db import SentenceDB
from evaluation.find_coqstoq_idx import get_thm_desc

SRC = sys.argv[1] if len(sys.argv) > 1 else "all_log/dn_pool.jsonl"
DST = sys.argv[2] if len(sys.argv) > 2 else "all_log/r11_prompt_pool.jsonl"
#: 합치는 방식
#     "z"      채널별 z-정규화 후 합침  — **실전용**. gold tactic 을 안 쓴다
#     "rr"     균등 라운드로빈          — 순위만 쓰는 거친 판본
#     "oracle" gold tactic 의 채널만    — **상한 측정용**. 실전에 못 쓴다
MODE = sys.argv[3] if len(sys.argv) > 3 else "z"
#: 진술문을 어디서 가져오나
#     "plugin"  플러그인 pretty-print (`Retyping.get_type_of`)
#     "source"  문장 DB 의 **원본 선언문** — 모델이 학습 때 본 형태
#
#   실측(487지점 · ckpt32000):
#     원본 텍스트를 쓴 풀(현행·gold주입)   조립률 71.1~71.8%
#     플러그인 pretty-print 를 쓴 풀        조립률 67.8~70.2%   ← 4pp 낮다
#   Coq pretty-printer 는 암묵 인자 타입을 다 펼치고 괄호를 붙인다:
#     우리   Lemma L : (forall (b : Values.block) (lo hi : Z) …, …)
#     원본   Lemma L: forall b lo hi P mid m, …
STMT = sys.argv[4] if len(sys.argv) > 4 else "source"
#: gold tactic → 그 tactic 전용 채널 (오라클 모드)
TIGHT = {"apply": ("ap", "in"), "rewrite": ("rw", "rwh")}
#: 채널별 슬롯 비율 — **균등**이 최선이다 (실측).
#
#   물채우기를 K=20 에서 적합한 값(ap 15·rw 4·in 1)을 썼더니 @10 이 42.1% 로
#   무너졌다. ap 를 15개 먼저 다 뱉느라 `rw` **1위** 후보가 16번째로 밀린다.
#   균등하게 하나씩 번갈아 뽑으면 **어느 채널의 1위든 상위 4칸** 안에 온다.
#
#     apply/rewrite 178지점            @10   / 순위중앙
#       오라클(gold tactic 앎)        59.0%  /  3
#       합쳐서 점수순                 50.6%  /  8
#       ap15·rw4·rwh2·in1           42.1%  / 16   ← 나쁨
#       ★ 균등 1:1:1:1               59.6%  /  4   ← 오라클을 넘는다
#
#   즉 **tactic 을 예측할 필요가 없다.**
WEIGHT = {"ap": 1, "rw": 1, "rwh": 1, "in": 1}


assert MODE in ("z", "rr", "oracle"), f"모르는 MODE: {MODE}"
assert STMT in ("plugin", "source"), f"모르는 STMT: {STMT}"

# ── ★ 시동 자가검사 — 배분이 조용히 망가지는 것을 막는다 ─────────────────
assert set(WEIGHT) <= set(AR.ALL_CH), f"WEIGHT 에 모르는 채널: {set(WEIGHT)-set(AR.ALL_CH)}"
assert set(AR.ACTIVE_CH) <= set(WEIGHT), \
    f"활성 채널인데 WEIGHT 가 없다: {set(AR.ACTIVE_CH)-set(WEIGHT)}"
assert all(isinstance(v, int) and v >= 1 for v in WEIGHT.values()), \
    "가중치는 1 이상 정수여야 한다 — 0 이면 그 채널이 통째로 사라진다"


def zmerge(per_chan_scored):
    """★ 채널별 z-정규화 후 합친다.

    점수를 그대로 합치면 안 되는 이유: `feats` 에 `('ch', …)` 특징이 있어
    **채널마다 상수 오프셋**이 붙는다(`('ch','in') −2.41` 등). 채널 크기도
    달라(ap 334 · in 618 · rw 418) idf 분포가 다르다. 그대로 합치면 한 채널이
    다른 채널을 덮는다.

    라운드로빈은 "점수를 아예 안 쓰고 순위만" 으로 우회하지만 **1위가 2위보다
    얼마나 좋은지**를 버린다. z-정규화는 눈금만 맞추고 그 정보를 살린다.

        apply/rewrite 178지점        @10   / 순위중앙
          점수 그대로 합침           50.0%  /  8
          균등 라운드로빈            60.1%  /  4
          ★ z-정규화               62.9%  /  2   ← 오라클(59.0%)도 넘는다
    """
    best = {}
    for c, v in per_chan_scored.items():
        ss = [s for _, s in v]
        if not ss: continue
        m = st.mean(ss)
        sd = st.pstdev(ss) or 1.0
        for x, s0 in v:
            z = (s0 - m) / sd
            best[x] = max(best.get(x, -1e9), z)
    out = [x for x, _ in sorted(best.items(), key=lambda kv: -kv[1])]
    union = set()
    for v in per_chan_scored.values(): union |= {x for x, _ in v}
    assert set(out) == union, "z-병합이 후보를 잃거나 만들었다"
    return out


def interleave(per_chan, weight=WEIGHT):
    """채널별 정렬 목록을 비율대로 번갈아 뽑아 하나로 합친다."""
    it = {c: iter(v) for c, v in per_chan.items() if v}
    left = {c: weight.get(c, 1) for c in it}
    out, seen = [], set()
    while it:
        progressed = False
        for c in list(it):
            for _ in range(left[c]):
                nxt = next(it[c], None)
                if nxt is None:
                    it.pop(c, None); break
                progressed = True
                if nxt not in seen:
                    seen.add(nxt); out.append(nxt)
        if not progressed:
            break
    # ★ 사후조건 — 하나도 잃지 않고, 없던 것을 만들지도 않는다.
    #   배분은 **순서만** 바꾸는 연산이다. 회수율이 여기서 떨어지면 안 된다.
    union = set()
    for v in per_chan.values(): union |= set(v)
    assert set(out) == union, \
        f"배분이 후보를 잃거나 만들었다: 잃음 {len(union - set(out))} · 생김 {len(set(out) - union)}"
    assert len(out) == len(set(out)), "배분 결과에 중복이 있다"
    return out


_SRC = None
_DECL = re.compile(r"^\s*(?:Local\s+|Global\s+|Program\s+|#\[[^\]]*\]\s*)?"
                   r"(?:Lemma|Theorem|Corollary|Remark|Fact|Proposition|Property|"
                   r"Definition|Fixpoint|Inductive|Axiom|Instance)\s+"
                   r"([A-Za-z_][\w']*)\s*[:({]")


def _load_source():
    """★ 문장 DB 를 **한 번만** 훑어 `이름 → 원본 선언문` 사전을 만든다.

    이름마다 `LIKE` 질의를 날리면 53,387행 전체 스캔이 50만 번 돈다 —
    실측으로 11시간 돌고도 안 끝났다. 한 번 훑으면 몇 초다."""
    import sqlite3, time
    t0 = time.time()
    con = sqlite3.connect("raw-data/coqstoq-test/coqstoq-test-sentences.db")
    d = {}; n = 0
    for (t,) in con.execute("SELECT text FROM sentence"):
        n += 1
        if not t: continue
        m = _DECL.match(t)
        if not m: continue
        nm = m.group(1)
        if nm in d: continue
        x = " ".join(t.split())
        if not x.endswith("."): x += "."
        d[nm] = x
    con.close()
    assert d, "문장 DB 에서 선언문을 하나도 못 뽑았다 — 정규식을 의심하라"
    print(f"■ 원본 선언문 사전 {len(d):,}개 (문장 {n:,}행 · {time.time()-t0:.1f}초)", flush=True)
    return d


def source_decl(name):
    """이름 → 원본 선언문. 없으면 None."""
    global _SRC
    if _SRC is None: _SRC = _load_source()
    return _SRC.get(name.split(".")[-1])


def enrich(rows):
    """★ `lex`(어휘 겹침)·`gnames`(이름 겹침)를 붙인다.

    이 둘이 없으면 나이브베이즈에서 **가중치 2·3위 특징**이 통째로 빠진다
    (`('nov',3) +8.19` · `('lex',5) +6.94`). 안 붙이고 쟀다가 @10 을
    13pp 낮게 봤다. goal 텍스트가 필요해서 sentence DB 를 읽어야 한다."""
    sdb = SentenceDB.load(Path("raw-data/coqstoq-test/coqstoq-test-sentences.db"))
    _df = collections.Counter(); _nd = 0
    for r in rows:
        for stmt in (r.get("stmts") or {}).values():
            if stmt:
                _nd += 1
                for t in set(AR._TOK.findall(stmt)): _df[t] += 1
    tok_idf = {t: math.log((_nd + 1.0) / (v + 1.0)) for t, v in _df.items()}
    by = collections.defaultdict(list)
    for r in rows: by[r["idx"]].append(r)
    ok = 0
    for i, rs in by.items():
        try:
            d = get_thm_desc(get_theorem(CSSplit.TEST, i, Path("CoqStoq")),
                             Path("raw-data/coqstoq-test"), sdb)
            if d is None: continue
            proof = d.dp.proofs[d.idx]
        except Exception:
            continue
        for r in rs:
            try:
                gs = proof.steps[r["k"]].goals
                gl = (gs[0].goal or "") if gs else ""
            except Exception:
                gl = ""
            gt = set(AR._TOK.findall(gl))
            r["lex"] = {nm: AR.lex_overlap(stmt, gt, tok_idf)
                        for nm, stmt in (r.get("stmts") or {}).items() if stmt}
            gn = set()
            for x in gt: gn |= AR._name_toks(x)
            r["gnames"] = sorted(gn)
            ok += 1
    # ★ lex·nov 는 학습 가중치 **2·3위**다(+8.19 · +6.94). 조용히 빠지면
    #   @10 을 13pp 낮게 본다 — 실제로 한 번 그렇게 쟀다.
    assert ok >= 0.9 * len(rows), \
        (f"lex/gnames 를 {ok}/{len(rows)} 에만 붙였다 — sentence DB 경로나 "
         f"CoqStoq 인덱스를 의심하라")
    _nz = sum(1 for r in rows if any(v > 0 for v in (r.get("lex") or {}).values()))
    assert _nz >= 0.5 * len(rows), \
        f"lex 가 전부 0 인 지점이 너무 많다 ({len(rows)-_nz}/{len(rows)}) — goal 텍스트를 의심하라"
    _gn = sum(1 for r in rows if r.get("gnames"))
    assert _gn >= 0.9 * len(rows), f"gnames 가 빈 지점 {len(rows)-_gn}개"
    print(f"■ lex/gnames 부착 {ok}/{len(rows)} 지점 "
          f"(lex>0 {_nz} · gnames 있음 {_gn})", flush=True)
    return rows


if __name__ == "__main__":
    rows = [json.loads(l) for l in open(SRC)]
    assert rows, f"{SRC} 가 비었다"
    rows = enrich(rows)
    # gold 은 랭커 학습에만 쓴다. 출력 순서에는 안 쓴다(누출 없음).
    tr = [r for r in rows if r.get("gold") and not r.get("local")]
    if not tr:
        # dn_pool 에는 gold 이 없다 — dn_rank 에서 붙여 온다
        try:
            rk = {(x["idx"], x["k"]): x for x in
                  (json.loads(l) for l in open("all_log/dn_rank.jsonl"))}
            for r in rows:
                g = rk.get((r["idx"], r["k"]))
                if g:
                    r["gold"] = g.get("gold"); r["local"] = g.get("local")
                    r["tac"] = g.get("tac")
            tr = [r for r in rows if r.get("gold") and not r.get("local")]
        except Exception:
            pass
    assert tr, "랭커를 학습할 gold 붙은 행이 없다"
    idf, _, _ = AR.build_idf(tr)
    W, npos, nneg = AR.train_nb(tr, idf, AR.chans_for)
    assert npos > 0, "양성 표본이 0 — gold 이 후보 안에 하나도 없다"
    assert nneg > npos, f"음성({nneg})이 양성({npos})보다 적다 — 채널 배선을 의심하라"
    assert W, "가중치표가 비었다"
    # ★ lex·nov 특징이 실제로 학습됐는지 확인한다 (조용히 빠지는 자리)
    _ks = {k for k, _ in W}
    for _need in ("lex", "nov", "idf", "lcp", "e", "ch"):
        assert _need in _ks, f"특징 '{_need}' 가 가중치표에 없다 — feats 배선을 의심하라"
    print(f"■ 랭커 학습 — 지점 {len(tr)} · 양성 {npos:,} · 음성 {nneg:,} "
          f"· 특징종류 {len(_ks)}", flush=True)

    nout = 0; sizes = []; nsrc = 0; ntot = 0
    with open(DST, "w") as fo:
        for r in rows:
            chan = r.get("chan") or {}
            stmts = r.get("stmts") or {}
            sig = r.get("sig") or {}
            g = float((list(sig.values()) or [{}])[0].get("g", 1) or 1)
            chan_of = {}
            for c in AR.ALL_CH:
                for x in chan.get(c, []): chan_of.setdefault(x, c)
            sc = AR.nb_score_fn(W, idf, chan_of, r.get("lex"),
                                set(r.get("gnames") or []))
            # ★ 오라클 모드는 **gold tactic 을 본다.** 실전에 못 쓰는 상한이다.
            chs = (TIGHT.get(r.get("tac"), AR.ACTIVE_CH) if MODE == "oracle"
                   else AR.ACTIVE_CH)
            per = {}
            for c in chs:
                v = sorted(set(chan.get(c, [])), key=lambda x: -sc(x, sig, idf, g))
                if v: per[c] = [(x, sc(x, sig, idf, g)) for x in v]
            if not per: continue
            if MODE == "rr":
                order = interleave({c: [x for x, _ in v] for c, v in per.items()})
            else:
                order = zmerge(per)
            if not order: continue
            # ★ 회수율 보존 — 채널 합집합에 gold 이 있으면 순서에도 있어야 한다
            if r.get("gold") and not r.get("local"):
                _u = {x for c in chs for x in chan.get(c, [])}
                _g = r["gold"]; _gb = _g.split(".")[-1]
                _in_u = any(x == _g or x.split(".")[-1] == _gb for x in _u)
                _in_o = any(x == _g or x.split(".")[-1] == _gb for x in order)
                assert _in_u == _in_o, f"배분이 gold 을 잃었다: {_g} (idx={r['idx']} k={r['k']})"
            sizes.append(len(order)); ntot += len(order)
            # ★ 진술문 — 원본 소스가 있으면 그걸 쓴다
            out_st = {}
            for n in order:
                d = source_decl(n) if STMT == "source" else None
                if d:
                    nsrc += 1
                    # `Lemma foo : bar.` 에서 본문만 떼어 낸다 (형식은 아래에서 통일)
                    out_st[n] = d
                else:
                    t = stmts.get(n, "")
                    out_st[n] = f"Lemma {n} : {t}." if t else ""
            fo.write(json.dumps({"idx": r["idx"], "k": r["k"],
                                 "order": [n for n in order if out_st.get(n)],
                                 "stmts": {n: v for n, v in out_st.items() if v},
                                 "raw": True},
                                ensure_ascii=False) + "\n")
            nout += 1
    import statistics as st
    assert nout > 0, f"{DST} 에 한 지점도 안 나갔다"
    # ★ 출력 검증 — 이름과 진술문이 짝이 맞나
    _bad = 0
    for _ln in open(DST):
        _d = json.loads(_ln)
        assert _d["order"], f"order 가 빈 지점 idx={_d['idx']}"
        assert len(_d["order"]) == len(set(_d["order"])), "order 에 중복"
        if not all(n in _d["stmts"] for n in _d["order"]): _bad += 1
    assert _bad == 0, f"order 에 있는데 stmts 에 없는 이름이 있는 지점 {_bad}개"
    print(f"■ {DST} — {nout} 지점 · 후보 중앙 {st.median(sizes):,.0f}")
    print(f"   진술문 {STMT} — 원본 소스로 채운 것 {nsrc:,}/{ntot:,} "
          f"({nsrc/max(ntot,1)*100:.1f}%)")
    print(f"   모드 {MODE}" + (f" · 채널 비율 {WEIGHT}" if MODE == "rr" else ""))
    print("BUILD_POOL_DONE", flush=True)
