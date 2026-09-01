#!/usr/bin/env python3
"""★ 우리 필터 vs 현행 tf-idf — **같은 지점**에서 gold 포함률·순위를 나란히 잰다.

r11 풀(`all_log/r11_pool_<split>.jsonl`)이 기록한 (proj, thm, thmi, k) 로
정리를 되찾아, rango 의 현행 검색(`get_ranked_premises`)을 같은 스텝에 돌린다.

비교하는 것:
    ① gold 이 풀에 드나        현행 tf-idf  vs  우리 4채널 합집합
    ② gold 이 몇 위인가        현행 tf-idf  vs  우리 나이브베이즈
    ③ **채널별**로 gold 이 어디 있나 (ap / in / rw / rwh)

사용: python3 scripts/tfidf_compare.py VAL
"""
import collections, json, os, sys, logging, statistics as st
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")
os.environ["CUDA_VISIBLE_DEVICES"] = ""
sys.path.insert(0, "src"); sys.path.insert(0, "CoqStoq"); sys.path.insert(0, "scripts")
logging.disable(logging.CRITICAL)
from pathlib import Path
import yaml
from coqstoq import Split, get_theorem_list
from data_management.sentence_db import SentenceDB
from evaluation.find_coqstoq_idx import get_thm_desc
import applic_rank as AR

SPLIT = (sys.argv[1] if len(sys.argv) > 1 else "VAL").upper()
POOL = f"all_log/r11_pool_{SPLIT.lower()}.jsonl"
_S = {"VAL": Split.VAL, "TEST": Split.TEST, "CUTOFF": Split.CUTOFF}[SPLIT]
_DATA = {"VAL": "raw-data/coqstoq-val", "TEST": "raw-data/coqstoq-test",
         "CUTOFF": "raw-data/coqstoq-cutoff"}[SPLIT]
_SDB = f"{_DATA}/coqstoq-{SPLIT.lower()}-sentences.db"
FORMS = ("apply", "apply-in", "rewrite", "rewrite-in")
CH4 = ("ap", "in", "rw", "rwh")
FORM_CH = {"apply": ("ap",), "apply-in": ("in",),
           "rewrite": ("rw",), "rewrite-in": ("rwh",)}

# ── ★ 시동 자가검사 ──────────────────────────────────────────────────────
assert SPLIT in ("VAL", "TEST", "CUTOFF"), f"모르는 split: {SPLIT}"
assert os.path.exists(POOL), f"풀이 없다: {POOL}"
assert os.path.exists(_SDB), f"문장 DB 가 없다: {_SDB}"
assert set(FORM_CH) == set(FORMS), "FORM_CH 와 FORMS 가 어긋난다"
assert set(CH4) >= {c for cs in FORM_CH.values() for c in cs}


def build_formatter():
    """v10 학습 설정의 formatter 를 이 스플릿의 DB 로 만든다."""
    from tactic_gen.lm_example import formatter_conf_from_yaml, formatter_from_conf
    conf = yaml.safe_load(open("all_log/ft_qwen3b_v10_conf.yaml"))
    td = conf["tactic_data"]
    td["data_loc"] = _DATA
    td["sentence_db_loc"] = _SDB
    fc = td["formatter_conf"]
    fc["premise"]["sentence_db_loc"] = _SDB
    if "proof_ret" in fc:
        fc["proof_ret"]["data_loc"] = _DATA
        fc["proof_ret"]["sentence_db_loc"] = _SDB
    return formatter_from_conf(formatter_conf_from_yaml(fc))


def name_of(text):
    import re
    m = AR._TOK.match((text or "").strip().lstrip("("))
    return None


if __name__ == "__main__":
    rows = [json.loads(l) for l in open(POOL)]
    rows = [r for r in rows if r.get("gold") and not r.get("local")
            and r.get("tac") in FORMS]
    assert rows, f"{POOL} 에 4형태 지점이 없다"
    print(f"■ {SPLIT} · 4형태 지점 {len(rows)}", flush=True)
    _f = collections.Counter(r["tac"] for r in rows)
    assert set(_f) <= set(FORMS), f"모르는 형태: {set(_f)-set(FORMS)}"
    print("   형태 분포:", dict(_f), flush=True)

    sdb = SentenceDB.load(Path(_SDB))
    thms = collections.defaultdict(list)
    for t in get_theorem_list(_S, Path("CoqStoq")):
        thms[str(t.project.dir_name)].append(t)
    fmt = build_formatter()
    import re
    DECL = re.compile(r"^\s*(?:Local\s+|Global\s+|Program\s+)?"
                      r"(?:Lemma|Theorem|Corollary|Remark|Definition|Fixpoint|"
                      r"Inductive|Proposition|Instance|Record|Axiom|Fact|Property)"
                      r"\s+([A-Za-z_][\w'.]*)")

    # ── 랭커 학습 (프로젝트 leave-one-out 은 비싸서 전량 학습 · 순위 비교용) ──
    idf, _, _ = AR.build_idf(rows)
    W, _, _ = AR.train_nb(rows, idf, lambda t: CH4)

    S = collections.defaultdict(collections.Counter)
    TF = collections.defaultdict(list); OU = collections.defaultdict(list)
    nerr = 0
    for n, r in enumerate(rows):
        f = r["tac"]; g = r["gold"]; gb = g.split(".")[-1]
        # ── 우리 쪽 ──
        pool = {x for c in CH4 for x in (r.get("chan") or {}).get(c, [])}
        ours_in = any(x == g or x.split(".")[-1] == gb for x in pool)
        S[f]["n"] += 1
        S[f]["우리"] += ours_in
        for c in CH4:
            if any(x == g or x.split(".")[-1] == gb
                   for x in (r.get("chan") or {}).get(c, [])):
                S[f][c] += 1
        if ours_in:
            sig = r.get("sig") or {}
            gsz = float((list(sig.values()) or [{}])[0].get("g", 1) or 1)
            co = {}
            for c in AR.ALL_CH:
                for x in (r.get("chan") or {}).get(c, []): co.setdefault(x, c)
            sc = AR.nb_score_fn(W, idf, co, r.get("lex"),
                                set(r.get("gnames") or []))
            rk = sorted(pool, key=lambda x: -sc(x, sig, idf, gsz))
            OU[f].append(next(i + 1 for i, x in enumerate(rk)
                              if x == g or x.split(".")[-1] == gb))
        # ── 현행 tf-idf ──
        try:
            ts = thms.get(r["proj"]) or []
            thm = ts[r["thmi"]]
            d = get_thm_desc(thm, Path(_DATA), sdb)
            if d is None: raise ValueError("desc None")
            ex = fmt.example_from_step(r["k"], d.idx, d.dp, training=False)
            prem = list(ex.premises or [])
            pos = None
            for i, t in enumerate(prem):
                m = DECL.match(t or "")
                if m and (m.group(1) == g or m.group(1).split(".")[-1] == gb):
                    pos = i + 1; break
            S[f]["tfidf풀"] += len(prem) > 0
            if pos is not None:
                S[f]["tfidf"] += 1; TF[f].append(pos)
        except Exception:
            nerr += 1
        if (n + 1) % 25 == 0:
            print(f"   … {n+1}/{len(rows)} (오류 {nerr})", flush=True)

    def atk(v, n, K): return sum(1 for x in v if x <= K) / max(n, 1) * 100
    print(f"\n■ {SPLIT} · gold 포함률 — 현행 tf-idf vs 우리 (분모 = 전체 지점)")
    print(f"   {'gold 형태':12s}{'지점':>6s}{'현행':>8s}{'우리':>8s}"
          f"{'ap':>7s}{'in':>7s}{'rw':>7s}{'rwh':>7s}   자기채널")
    tot = collections.Counter()
    for f in FORMS:
        c = S[f]; n = c["n"]
        if not n: continue
        for k in ("n", "우리", "tfidf"): tot[k] += c[k]
        print(f"   {f:12s}{n:6d}{c['tfidf']/n*100:7.1f}%{c['우리']/n*100:7.1f}%"
              + "".join(f"{c[x]/n*100:6.1f}%" for x in CH4)
              + f"   {'/'.join(FORM_CH[f])}")
    assert nerr < 0.5 * len(rows), \
        f"tf-idf 쪽 오류 {nerr}/{len(rows)} — formatter/DB 배선을 확인하라"
    if tot["n"]:
        print(f"   {'—— 합계':12s}{tot['n']:6d}{tot['tfidf']/tot['n']*100:7.1f}%"
              f"{tot['우리']/tot['n']*100:7.1f}%")
    print(f"\n■ {SPLIT} · 순위 — 현행 tf-idf vs 우리 나이브베이즈 (분모 = 전체 지점)")
    print(f"   {'gold 형태':12s}{'랭커':10s}{'@5':>8s}{'@10':>8s}{'@20':>8s}"
          f"{'@50':>8s}{'순위중앙':>9s}")
    for f in FORMS:
        n = S[f]["n"]
        if not n: continue
        for lab, v in (("현행 tf-idf", TF[f]), ("★ 우리", OU[f])):
            print(f"   {f if lab.startswith('현행') else '':12s}{lab:10s}"
                  + "".join(f"{atk(v,n,K):7.1f}%" for K in (5, 10, 20, 50))
                  + f"{(st.median(v) if v else 0):9,.0f}")
    print(f"\nTFIDF_CMP_{SPLIT}_DONE", flush=True)
