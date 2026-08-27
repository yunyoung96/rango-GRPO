#!/usr/bin/env python3
"""★ **gold 이 stdlib 이 아닌 스텝만** 놓고 필터를 걸면 어떻게 되나.

stdlib gold 는 지금 풀에 아예 없어서(§4.5) 필터로 손댈 수 없다. 그 몫을 빼고
**필터가 실제로 다룰 수 있는 스텝만** 남기면 판정이 달라지는지 본다.

두 풀에 각각 건다:
    지금 풀 (proj-thm · stdlib 없음)   ← 실전 설정
    stdlib 포함 풀                      ← 비교용

재는 것:
    ① 남는 비율   필터 후 후보가 전체의 몇 %인가
    ② gold 생존   gold 이 필터를 살아남나  ← 이게 100% 여야 쓸 수 있다
    ③ top-100     gold 이 상위 100 에 드는 비율 (필터 전/후)

★ stdlib 판정은 **선언의 file_path**(`lib/coq/theories`)로 한다 — PremiseFilter 가
  쓰는 것과 같은 기준이다. 이름 집합(`data/stdlib_names.json`)으로 하면 프로젝트가
  같은 이름을 재선언한 경우와 갈리지 않는다.

사용: FN_SPLIT=TEST|TRAIN FN_N=200 FN_SHARD/FN_NSHARD python3 scripts/filter_nonstdlib_eval.py
"""
import collections, json, os, re, sqlite3, sys, yaml, logging
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")
os.environ["CUDA_VISIBLE_DEVICES"] = ""
sys.path.insert(0, "src"); sys.path.insert(0, "CoqStoq")
logging.disable(logging.CRITICAL)
from pathlib import Path
from data_management.sentence_db import SentenceDB
from data_management.dataset_file import DatasetFile
from tactic_gen.lm_example import formatter_from_conf
from tactic_gen.tactic_data import TacticDataConf
from premise_selection.premise_filter import PremiseFilter

SPLIT = os.environ.get("FN_SPLIT", "TEST")
N = int(os.environ.get("FN_N", "200"))
SHARD = int(os.environ.get("FN_SHARD", "0"))
NSHARD = int(os.environ.get("FN_NSHARD", "1"))
MAXPT = int(os.environ.get("FN_MAX_PER_THM", "4"))
OUT = Path(os.environ.get("FN_OUT", f"all_log/fnonstd_{SPLIT.lower()}.jsonl"))
STDL = os.path.join("lib", "coq", "theories")

CONF = yaml.safe_load(open("all_log/ft_qwen3b_v10_conf.yaml"))
td = TacticDataConf.from_yaml(CONF["tactic_data"])
fm = formatter_from_conf(td.formatter_conf)
pc = fm.premise_client
NOFILT = PremiseFilter([], [], [])

DECL = re.compile(r"^\s*(?:Local\s+|Global\s+|Program\s+)?"
                  r"(?:Lemma|Theorem|Definition|Corollary|Fixpoint|Inductive|Remark|"
                  r"Proposition|Instance|Record|Axiom|Fact|Property)\s+([A-Za-z_][\w']*)")
NAMED = re.compile(r"\b(?:e?apply|e?rewrite)\s+(?:<-\s*)?\(?\s*"
                   r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
HEADT = re.compile(r"^\s*(?:now\s+|try\s+|repeat\s+)?([A-Za-z_][\w']*)")
ID = re.compile(r"@?([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
KW = {"forall", "exists", "fun", "let", "in", "match", "with", "end", "if", "then",
      "else", "Prop", "Type", "Set", "True", "False"}

def decl(t):
    m = DECL.match(t or "")
    return m.group(1) if m else None

def concl_head(stmt):
    s = re.sub(r"^\s*\w+\s+[\w']+\s*", "", (stmt or "").strip(), count=1)
    s = s.split(":", 1)[-1] if ":" in s else s
    c = re.split(r"->|→", s)[-1].strip().rstrip(".")
    c = re.sub(r"^\(|\)$", "", c).strip()
    m = ID.match(c)
    if not m:
        return None
    n = m.group(1)
    return None if n in KW else n.split(".")[-1]

def goal_heads(g):
    tail = re.split(r"->|→", g.goal)[-1].strip()
    m = ID.match(tail)
    top = m.group(1).split(".")[-1] if m and m.group(1) not in KW else None
    hs = set()
    for mm in re.finditer(r"(?:^|[(\[{,;]|\s)\s*@?([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)", g.goal):
        hs.add(mm.group(1)); hs.add(mm.group(1).split(".")[-1])
    return top, hs

def keep_idx(head, texts, gtop, ghs):
    out = []
    for j, t in enumerate(texts):
        ch = concl_head(t)
        ok = (ch is None or gtop is None or ch == gtop) if head in ("apply", "eapply") \
             else (ch is None or ch in ghs)
        if ok:
            out.append(j)
    return out

def iter_steps():
    if SPLIT == "TEST":
        from coqstoq import Split as CSSplit, get_theorem
        from evaluation.find_coqstoq_idx import get_thm_desc
        sdb = SentenceDB.load(Path("raw-data/coqstoq-test/coqstoq-test-sentences.db"))
        ids = [int(x) for x in Path("data/compcert_bs2_rand200_idx.txt").read_text().split()][:N]
        for j, i in enumerate(ids):
            if j % NSHARD != SHARD:
                continue
            try:
                d = get_thm_desc(get_theorem(CSSplit.TEST, i, Path("CoqStoq")),
                                 Path("raw-data/coqstoq-test"), sdb)
                if d is not None:
                    yield i, d.dp, d.dp.proofs[d.idx]
            except Exception:
                continue
    else:
        from tactic_gen.tactic_data import LmDataset
        from data_management.splits import Split
        ds = LmDataset.from_conf(td, Split.TRAIN)
        stp = max(1, len(ds) // N); seen = set()
        for j, idx in enumerate(range(0, min(len(ds), N * stp), stp)):
            if j % NSHARD != SHARD:
                continue
            try:
                sid = ds.shuffled_idx.get_idx(ds.split, idx)
                if (sid.file, sid.proof_idx) in seen:
                    continue
                seen.add((sid.file, sid.proof_idx))
                dp = DatasetFile.load(ds.data_loc / "data_points" / sid.file, ds.sentence_db)
                yield idx, dp, dp.proofs[sid.proof_idx]
            except Exception:
                continue

print(f"■ {SPLIT} · 정리 {N} · 샤드 {SHARD}/{NSHARD}", flush=True)
S = collections.Counter()
fout = OUT.open("w"); done = 0
for tid, dp, proof in iter_steps():
    ks = [k for k, st in enumerate(proof.steps)
          if HEADT.match(st.step.text or "")
          and HEADT.match(st.step.text).group(1) in ("apply", "eapply", "rewrite", "erewrite")
          and NAMED.search(st.step.text or "")]
    if not ks:
        continue
    if len(ks) > MAXPT:
        stp = len(ks) / MAXPT
        ks = [ks[int(j * stp)] for j in range(MAXPT)]
    for k in ks:
        try:
            step = proof.steps[k]
            if not step.goals:
                continue
            gold = NAMED.search(step.step.text).group(1)
            gb = gold.split(".")[-1]
            head = HEADT.match(step.step.text).group(1)
            allp = list(NOFILT.get_pos_and_avail_premises(step, proof, dp).avail_premises)
            now = list(pc.premise_filter.get_pos_and_avail_premises(step, proof, dp).avail_premises)
            if not allp:
                continue
            # ★ gold 이 stdlib 인가 — 선언의 file_path 로 판정(PremiseFilter 와 같은 기준)
            gsrc = next((p for p in allp
                         if (decl(getattr(p, "text", "")) or "") in (gold, gb)), None)
            if gsrc is None:
                S["gold 선언 못 찾음"] += 1
                continue
            g_std = STDL in (getattr(gsrc, "file_path", "") or "")
            tag = "stdlib gold" if g_std else "비-stdlib gold"
            S[tag] += 1
            gtop, ghs = goal_heads(step.goals[0])
            rec = dict(tid=tid, k=k, gold=gold, head=head, gold_stdlib=g_std)
            for lab, pool in (("지금", now), ("stdlib포함", allp)):
                texts = [getattr(p, "text", "") or "" for p in pool]
                gi = next((j for j, t in enumerate(texts) if (decl(t) or "") in (gold, gb)), None)
                if not texts:
                    continue
                keep = keep_idx(head, texts, gtop, ghs)
                S[f"{tag}|{lab}|풀"] += len(texts)
                S[f"{tag}|{lab}|통과"] += len(keep)
                S[f"{tag}|{lab}|스텝"] += 1
                rec[f"{lab}_pool"] = len(texts); rec[f"{lab}_keep"] = len(keep)
                if gi is None:
                    rec[f"{lab}_gold"] = None
                    continue
                S[f"{tag}|{lab}|gold대상"] += 1
                S[f"{tag}|{lab}|gold생존"] += (gi in keep)
                rec[f"{lab}_gold"] = (gi in keep)
                rk = lambda ps: [decl(getattr(x, "text", "")) or ""
                                 for x in pc.get_ranked_premises(k, proof, dp, ps, False)]
                rb = next((j for j, x in enumerate(rk(pool)) if x in (gold, gb)), None)
                if rb is not None:
                    S[f"{tag}|{lab}|b100"] += (rb < 100)
                if gi in keep:
                    sub = [pool[j] for j in keep]
                    ra = next((j for j, x in enumerate(rk(sub)) if x in (gold, gb)), None)
                    if ra is not None:
                        S[f"{tag}|{lab}|a100"] += (ra < 100)
                rec[f"{lab}_rb"] = rb
            fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception:
            S["오류"] += 1
    done += 1; fout.flush()
    if done % 5 == 0:
        print(f"   … {done}", flush=True)

print(f"\n■ {SPLIT}  비-stdlib gold {S['비-stdlib gold']} · stdlib gold {S['stdlib gold']}"
      f" · 선언 못 찾음 {S['gold 선언 못 찾음']} · 오류 {S['오류']}")
for tag in ("비-stdlib gold", "stdlib gold"):
    if not S[tag]:
        continue
    print(f"\n  【{tag}】")
    print(f"     {'풀':12s}{'스텝':>6s}{'후보':>10s}{'필터후':>10s}{'남음':>8s}"
          f"{'gold생존':>10s}{'top100 전':>11s}{'top100 후':>11s}")
    for lab in ("지금", "stdlib포함"):
        m = S[f"{tag}|{lab}|스텝"]
        if not m:
            continue
        gd = max(S[f"{tag}|{lab}|gold대상"], 1)
        print(f"     {lab:12s}{m:6d}{S[f'{tag}|{lab}|풀']/m:10,.0f}"
              f"{S[f'{tag}|{lab}|통과']/m:10,.0f}"
              f"{S[f'{tag}|{lab}|통과']/max(S[f'{tag}|{lab}|풀'],1)*100:7.1f}%"
              f"{S[f'{tag}|{lab}|gold생존']/gd*100:9.1f}%"
              f"{S[f'{tag}|{lab}|b100']/m*100:10.1f}%"
              f"{S[f'{tag}|{lab}|a100']/m*100:10.1f}%")
