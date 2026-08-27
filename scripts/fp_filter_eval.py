#!/usr/bin/env python3
"""★★ **진짜 지문색인**(Schulz FP6M, 깊이 2)으로 필터를 잰다 — 양쪽 elaborate.

앞선 다섯 판본은 전부 **깊이 0**(머리기호 하나)이었다. Coq 의 `auto` 힌트 DB 수준이지
판별트리도 지문색인도 아니었다. 여기서 처음으로 **위치 6곳**을 본다:

    ε, 1, 2, 3, 1.1, 1.2

  apply    : lemma 결론 지문 ↔ goal 결론 지문        (유니피케이션 호환표)
  rewrite  : lemma 좌·우변 지문 ↔ goal **모든 부분항** 지문  (매칭 호환표)
  … in H   : 전방추론이라 판정 안 함(통과)

전제: lemma(`data/elab_compcert.jsonl`) 와 goal(`all_log/elab_goals_batch.jsonl`) 이
**둘 다 elaborate** 되어 있어야 한다.

사용: python3 scripts/fp_filter_eval.py [goal_jsonl …]
"""
import collections, json, os, re, sys, yaml, logging
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")
os.environ["CUDA_VISIBLE_DEVICES"] = ""
sys.path.insert(0, "src"); sys.path.insert(0, "CoqStoq")
logging.disable(logging.CRITICAL)
from pathlib import Path
from data_management.sentence_db import SentenceDB
from tactic_gen.lm_example import formatter_from_conf
from tactic_gen.tactic_data import TacticDataConf
from coqstoq import Split as CSSplit, get_theorem
from evaluation.find_coqstoq_idx import get_thm_desc
from premise_selection.fingerprint import (parse, fingerprint, compatible, FP6M,
                                          peel, dt_key, dt_compatible, st_compatible)

GOALS = sys.argv[1:] or ["all_log/elab_goals_batch.jsonl"]
ELAB = os.environ.get("FP_ELAB", "data/elab_compcert.jsonl")
DEPTH = os.environ.get("FP_POS", "")     # 빈 값이면 FP6M
POS = DEPTH.split(",") if DEPTH else FP6M
MODE = os.environ.get("FP_MODE", "fp")   # fp=지문색인 · dt=판별트리 · st=치환트리
CONF = yaml.safe_load(open("all_log/ft_qwen3b_v10_conf.yaml"))
td = TacticDataConf.from_yaml(CONF["tactic_data"])
fm = formatter_from_conf(td.formatter_conf); pc = fm.premise_client
sdb = SentenceDB.load(Path("raw-data/coqstoq-test/coqstoq-test-sentences.db"))

ELABT = {}
for ln in open(ELAB):
    d = json.loads(ln); ELABT.setdefault(d["name"].split(".")[-1], d["type"])
G = {}
for f in GOALS:
    p = Path(f)
    if p.exists():
        for ln in p.open():
            d = json.loads(ln); G[(d["idx"], d["k"])] = d["goal_elab"]
print(f"■ lemma 색인 {len(ELABT):,} · elaborate goal {len(G):,} · 위치 {POS}", flush=True)

ID = re.compile(r"@?([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
BIND = re.compile(r"[\(\[\{]\s*([^:\)\]\}]+?)\s*:")
DECL = re.compile(r"^\s*(?:Local\s+|Global\s+|Program\s+)?"
                  r"(?:Lemma|Theorem|Definition|Corollary|Fixpoint|Inductive|Remark|"
                  r"Proposition|Instance|Record|Axiom|Fact|Property)\s+([A-Za-z_][\w']*)")
NAMED = re.compile(r"\b(?:e?apply|e?rewrite)\s+(?:<-\s*)?\(?\s*"
                   r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
HEADT = re.compile(r"^\s*(?:now\s+|try\s+|repeat\s+)?([A-Za-z_][\w']*)")

def sides(c):
    """결론이 `@eq T L R` / `iff A B` 면 [L, R] 문자열. 아니면 [c]."""
    n = parse(c)
    if n is None or n[0] != "app" or n[1][0] != "atom":
        return [c]
    h = n[1][1].split(".")[-1]
    if h == "eq" and len(n[2]) >= 3:
        return [unparse(n[2][1]), unparse(n[2][2])]
    if h == "iff" and len(n[2]) >= 2:
        return [unparse(n[2][0]), unparse(n[2][1])]
    return [c]

def unparse(n):
    if n is None: return ""
    if n[0] == "atom": return n[1]
    return "(" + unparse(n[1]) + " " + " ".join(unparse(a) for a in n[2]) + ")"

def subterms(n, out, d=0):
    if n is None or d > 6: return
    out.append(n)
    if n[0] == "app":
        subterms(n[1], out, d + 1)
        for a in n[2]: subterms(a, out, d + 1)

def goal_concl(g):
    """★ **첫 goal** 의 결론. tactic 은 첫 goal 에 적용된다 —
       `Show.` 는 goal 을 여러 개 찍으므로 마지막을 쓰면 엉뚱한 것을 본다."""
    b = g.split("============================")
    if len(b) < 2:
        return g.strip()
    c = b[1]
    # 다음 goal 블록이 시작되기 전까지 (빈 줄 뒤 `이름 : 타입` 이 나오면 새 goal)
    lines, out = c.split("\n"), []
    blank = False
    for ln in lines:
        if not ln.strip():
            if out: blank = True
            continue
        if blank:
            break
        out.append(ln)
    return " ".join(" ".join(out).split())

def decl(t):
    m = DECL.match(t or ""); return m.group(1) if m else None

S = collections.Counter(); drop = []
for i in sorted({k[0] for k in G}):
    try:
        d = get_thm_desc(get_theorem(CSSplit.TEST, i, Path("CoqStoq")),
                         Path("raw-data/coqstoq-test"), sdb)
        if d is None: continue
        proof = d.dp.proofs[d.idx]
    except Exception:
        continue
    for (ii, k), ge in [(kk, v) for kk, v in G.items() if kk[0] == i]:
        try:
            step = proof.steps[k]; raw = step.step.text
            gold = NAMED.search(raw).group(1); gb = gold.split(".")[-1]
            tac = HEADT.match(raw).group(1)
            tac = "rewrite" if tac.endswith("rewrite") else "apply"
            fwd = re.search(r"\bin\s+[A-Za-z_][\w']*", raw) is not None
            pool = list(pc.premise_filter.get_pos_and_avail_premises(step, proof, d.dp).avail_premises)
            texts = [getattr(p, "text", "") or "" for p in pool]
            gi = next((x for x, t in enumerate(texts) if (decl(t) or "") in (gold, gb)), None)
            if gi is None: continue
            gc = goal_concl(ge)
            gfp = fingerprint(gc, set(), POS)
            gsub = []
            subterms(parse(gc), gsub)
            gsubfp = [[fingerprint(unparse(x), set(), POS)] for x in gsub[:120]]
            gsubfp = [f[0] for f in gsubfp if f[0] is not None]
            gk = dt_key(gc, set())
            gsubk = [dt_key(unparse(x), set()) for x in gsub[:120]]
            gsubk = [x for x in gsubk if x is not None]
            keep, noidx = [], 0
            for x, t in enumerate(texts):
                nm = decl(t); ty = ELABT.get((nm or "").split(".")[-1]) if nm else None
                if ty is None or fwd:
                    keep.append(x); noidx += (ty is None); continue
                c, bs = peel(ty)
                if MODE == "st":
                    if tac == "apply":
                        if st_compatible(c, gc, bs):
                            keep.append(x)
                    else:
                        if any(st_compatible(s2, unparse(g2), bs)
                               for s2 in sides(c) for g2 in gsub[:120]):
                            keep.append(x)
                elif MODE == "dt":
                    if tac == "apply":
                        if dt_compatible(dt_key(c, bs), gk, "uni"):
                            keep.append(x)
                    else:
                        ks = [dt_key(s2, bs) for s2 in sides(c)]
                        if any(k2 is None for k2 in ks) or \
                           any(dt_compatible(k2, gs, "match") for k2 in ks for gs in gsubk):
                            keep.append(x)
                else:
                    if tac == "apply":
                        if compatible(fingerprint(c, bs, POS), gfp, "uni"):
                            keep.append(x)
                    else:
                        fps = [fingerprint(s2, bs, POS) for s2 in sides(c)]
                        if any(fp is None for fp in fps) or \
                           any(compatible(fp, gs, "match") for fp in fps for gs in gsubfp):
                            keep.append(x)
            S["스텝"] += 1; S["풀"] += len(texts); S["통과"] += len(keep)
            S["색인없음"] += noidx; S["gold생존"] += (gi in keep)
            S[f"{tac} n"] += 1; S[f"{tac} gold"] += (gi in keep)
            S[f"{tac} 풀"] += len(texts); S[f"{tac} 통과"] += len(keep)
            if gi not in keep: drop.append((gold, tac))
        except Exception:
            S["오류"] += 1
n = max(S["스텝"], 1)
MODENAME = {"dt": "판별트리", "st": "치환트리"}.get(MODE, "지문색인 FP" + str(len(POS)))
print("")
print(f"■ {MODENAME} · TEST {S['스텝']} 스텝 (오류 {S['오류']})")
print(f"   ① gold 생존   {S['gold생존']}/{n} = {S['gold생존']/n*100:.1f}%")
print(f"   ② 축소율      {S['풀']/n:,.0f} → {S['통과']/n:,.0f}"
      f"  ({S['통과']/max(S['풀'],1)*100:.1f}% 남음, {S['풀']/max(S['통과'],1):.1f}배)")
for t in ("apply", "rewrite"):
    m = S[f"{t} n"]
    if m:
        print(f"   · {t:8s} {m:3d} 스텝 · gold {S[f'{t} gold']/m*100:5.1f}%"
              f" · 축소 {S[f'{t} 풀']/max(S[f'{t} 통과'],1):.1f}배")
c = collections.Counter(x[1] for x in drop)
print(f"   떨굼 {len(drop)}건: {dict(c)}")
for g, t in drop[:10]: print(f"     {g:36s} {t}")
