#!/usr/bin/env python3
"""★★ **lemma 와 goal 을 둘 다 elaborate 해서** 필터를 다시 잰다.

앞선 다섯 판본이 못 넘은 벽 하나가 "goal 이 여전히 출력 형태" 였다
(applicability-filter.md §4.8). 이제 양쪽을 같은 형태로 맞춘다:

    lemma : data/elab_compcert.jsonl        (Set Printing All · Search inside)
    goal  : all_log/elab_goals*.jsonl       (Set Printing All · Show.)

판정은 앞과 같되 **양쪽이 같은 어휘**를 쓴다 —
`dm!id = Some gd` 가 양쪽 다 `@eq (option _) (@Maps.PTree.get …) (@Some …)` 가 된다.

  apply    : 결론 머리(전칭 변수면 통과)가 goal 결론 어딘가에 있나
  rewrite  : 좌·우변 머리가 goal 의 **부분항 머리** 집합에 있나
  … in H   : 전방추론이라 판정 안 함(통과)

사용: python3 scripts/elab_both_eval.py [goal_jsonl …]
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

GOALS = sys.argv[1:] or ["all_log/elab_goals60.jsonl", "all_log/elab_goals.jsonl"]
ELAB = os.environ.get("EB_ELAB", "data/elab_compcert.jsonl")
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
    if not p.exists(): continue
    for ln in p.open():
        d = json.loads(ln); G[(d["idx"], d["k"])] = d["goal_elab"]
print(f"■ lemma 색인 {len(ELABT):,} · elaborate goal {len(G):,}", flush=True)

ID = re.compile(r"@?([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
BIND = re.compile(r"[\(\[\{]\s*([^:\)\]\}]+?)\s*:")
DECL = re.compile(r"^\s*(?:Local\s+|Global\s+|Program\s+)?"
                  r"(?:Lemma|Theorem|Definition|Corollary|Fixpoint|Inductive|Remark|"
                  r"Proposition|Instance|Record|Axiom|Fact|Property)\s+([A-Za-z_][\w']*)")
NAMED = re.compile(r"\b(?:e?apply|e?rewrite)\s+(?:<-\s*)?\(?\s*"
                   r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
HEADT = re.compile(r"^\s*(?:now\s+|try\s+|repeat\s+)?([A-Za-z_][\w']*)")

def split_top(c):
    out, buf, d = [], "", 0
    for ch in c:
        if ch in "([{": d += 1
        elif ch in ")]}": d -= 1
        if ch.isspace() and d == 0:
            if buf: out.append(buf); buf = ""
        else: buf += ch
    if buf: out.append(buf)
    return out

def head_of(t, binders):
    t = t.strip()
    while t.startswith("(") and t.endswith(")"): t = t[1:-1].strip()
    m = ID.match(t)
    if not m: return None
    h = m.group(1)
    return None if (h in binders or h.split(".")[-1] in binders) else h.split(".")[-1]

def peel(ty):
    binders, c = set(), ty
    for _ in range(60):
        s = c.strip()
        if not s.startswith("forall"): break
        i = s.find(",")
        if i < 0: break
        for m in BIND.finditer(s[:i]):
            binders |= set(re.findall(r"[A-Za-z_][\w']*", m.group(1)))
        binders |= set(re.findall(r"[A-Za-z_][\w']*",
                                  re.sub(r"[\(\[\{][^)\]\}]*[\)\]\}]", " ", s[6:i])))
        c = s[i + 1:]
    return c.strip(), binders

def match_keys(ty, tac):
    c, binders = peel(ty)
    h = head_of(c, binders)
    if h is None: return set()
    if tac == "apply": return {h}
    if h in ("eq", "iff"):
        cc = c
        while cc.startswith("(") and cc.endswith(")"): cc = cc[1:-1].strip()
        parts = split_top(cc.lstrip("@"))
        sides = parts[2:] if h == "eq" and len(parts) >= 4 else parts[1:]
        ks = {head_of(x, binders) for x in sides}; ks.discard(None)
        return ks or set()
    return {h}

def goal_parts(g):
    """elaborate goal → (결론 이름집합, 전체(가설 포함) 이름집합)."""
    body = g.split("============================")
    concl = body[-1] if len(body) > 1 else g
    f = lambda s: {m.group(1).split(".")[-1] for m in ID.finditer(s)} | \
                  {m.group(1) for m in ID.finditer(s)}
    return f(concl), f(g)

def decl(t):
    m = DECL.match(t or ""); return m.group(1) if m else None

S = collections.Counter(); drop = []
ids = sorted({k[0] for k in G})
for i in ids:
    try:
        d = get_thm_desc(get_theorem(CSSplit.TEST, i, Path("CoqStoq")),
                         Path("raw-data/coqstoq-test"), sdb)
        if d is None: continue
        proof = d.dp.proofs[d.idx]
    except Exception:
        continue
    for (ii, k), ge in [(kk, v) for kk, v in G.items() if kk[0] == i]:
        try:
            step = proof.steps[k]
            raw = step.step.text
            gold = NAMED.search(raw).group(1); gb = gold.split(".")[-1]
            tac = HEADT.match(raw).group(1)
            tac = "rewrite" if tac.endswith("rewrite") else "apply"
            fwd = re.search(r"\bin\s+[A-Za-z_][\w']*", raw) is not None
            pool = list(pc.premise_filter.get_pos_and_avail_premises(step, proof, d.dp).avail_premises)
            texts = [getattr(p, "text", "") or "" for p in pool]
            gi = next((x for x, t in enumerate(texts) if (decl(t) or "") in (gold, gb)), None)
            if gi is None: continue
            gc, ga = goal_parts(ge)
            tgt = ga if tac == "rewrite" else gc      # rewrite 는 부분항 전체
            keep, noidx = [], 0
            for x, t in enumerate(texts):
                nm = decl(t); ty = ELABT.get((nm or "").split(".")[-1]) if nm else None
                if ty is None: keep.append(x); noidx += 1; continue
                ks = set() if fwd else match_keys(ty, tac)
                if (not ks) or (ks & tgt): keep.append(x)
            S["스텝"] += 1; S["풀"] += len(texts); S["통과"] += len(keep)
            S["색인없음"] += noidx; S["gold생존"] += (gi in keep)
            S[f"{tac} 스텝"] += 1; S[f"{tac} gold생존"] += (gi in keep)
            if gi not in keep:
                drop.append((gold, tac, match_keys(ELABT.get(gb, ""), tac)))
        except Exception:
            S["오류"] += 1
n = max(S["스텝"], 1)
print(f"\n■ lemma+goal 둘 다 elaborate · TEST {S['스텝']} 스텝 (오류 {S['오류']})")
print(f"   ① gold 생존   {S['gold생존']}/{n} = {S['gold생존']/n*100:.1f}%")
print(f"   ② 축소율      {S['풀']/n:,.0f} → {S['통과']/n:,.0f}"
      f"  ({S['통과']/max(S['풀'],1)*100:.1f}% 남음, {S['풀']/max(S['통과'],1):.1f}배)")
for t in ("apply", "rewrite"):
    m = S[f"{t} 스텝"]
    if m: print(f"   · {t:8s} {m:3d} 스텝 · gold 생존 {S[f'{t} gold생존']/m*100:.1f}%")
print(f"   · 후보 중 색인에 있던 것 {(S['풀']-S['색인없음'])/max(S['풀'],1)*100:.1f}%")
for g, t, k in drop[:12]:
    print(f"     떨굼 {g:34s} {t:8s} 요구키={k}")
