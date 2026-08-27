#!/usr/bin/env python3
"""★ **stdlib 을 검색 대상에 넣으면 풀이 얼마나 커지고, 필터가 되돌릴 수 있나.**

지금 `PROJ_THM_FILTER_CONF` 는 `lib/coq/theories` 경로의 선언을 **종류 불문 전부**
풀에서 뺀다(coq_excludes 에 THEOREM·LEMMA 포함). 그래서 gold 가 stdlib 이면
검색으로 절대 안 온다.

재는 것:
    ① 풀 크기        지금(proj-thm) vs stdlib 포함
    ② gold 커버리지  각각에서 gold 이 풀에 있나
    ③ 필터 통과율    건전 지문 필터가 몇 %를 남기나 (stdlib 포함 풀 기준)
    ④ gold 생존      필터가 gold 을 지키나
    ⑤ tf-idf 순위    지금 / stdlib 포함 / stdlib 포함+필터

사용: SP_SPLIT=TEST|TRAIN SP_N=60 SP_SHARD/SP_NSHARD python3 scripts/stdlib_pool_eval.py
"""
import collections, json, os, re, sys, yaml, logging
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

SPLIT = os.environ.get("SP_SPLIT", "TEST")
N = int(os.environ.get("SP_N", "60"))
SHARD = int(os.environ.get("SP_SHARD", "0"))
NSHARD = int(os.environ.get("SP_NSHARD", "1"))
MAXPT = int(os.environ.get("SP_MAX_PER_THM", "4"))
OUT = Path(os.environ.get("SP_OUT", f"all_log/stdlib_pool_{SPLIT.lower()}.jsonl"))

CONF = yaml.safe_load(open("all_log/ft_qwen3b_v10_conf.yaml"))
td = TacticDataConf.from_yaml(CONF["tactic_data"])
fm = formatter_from_conf(td.formatter_conf)
pc = fm.premise_client
NOFILT = PremiseFilter([], [], [])          # ★ stdlib 포함 — coq_excludes 를 비운다

DECL = re.compile(r"^\s*(?:Local\s+|Global\s+|Program\s+)?"
                  r"(?:Lemma|Theorem|Definition|Corollary|Fixpoint|Inductive|Remark|"
                  r"Proposition|Instance|Record|Axiom|Fact|Property)\s+([A-Za-z_][\w']*)")
NAMED = re.compile(r"\b(?:e?apply|e?rewrite)\s+(?:<-\s*)?\(?\s*"
                   r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
HEADT = re.compile(r"^\s*(?:now\s+|try\s+|repeat\s+)?([A-Za-z_][\w']*)")
ID = re.compile(r"@?([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
KW = {"forall", "exists", "fun", "let", "in", "match", "with", "end", "if", "then",
      "else", "Prop", "Type", "Set", "True", "False"}
STDL = "lib/coq/theories"

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
    """건전 지문 필터 — 확실히 불가능할 때만 쳐낸다."""
    out = []
    for j, t in enumerate(texts):
        ch = concl_head(t)
        if head in ("apply", "eapply"):
            ok = ch is None or gtop is None or ch == gtop
        else:
            ok = ch is None or ch in ghs
        if ok:
            out.append(j)
    return out

# ── 스텝 열거 ────────────────────────────────────────────────────────────────
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
                if d is None:
                    continue
                yield i, d.dp, d.dp.proofs[d.idx]
            except Exception:
                continue
    else:
        from tactic_gen.tactic_data import LmDataset
        from data_management.splits import Split
        ds = LmDataset.from_conf(td, Split.TRAIN)
        stp = max(1, len(ds) // N)
        seen = set()
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
            now = list(pc.premise_filter.get_pos_and_avail_premises(step, proof, dp).avail_premises)
            allp = list(NOFILT.get_pos_and_avail_premises(step, proof, dp).avail_premises)
            if not allp:
                continue
            n_now, n_all = len(now), len(allp)
            n_std = sum(1 for p in allp if STDL in (getattr(p, "file_path", "") or ""))
            f = lambda ps: next((j for j, p in enumerate(ps)
                                 if (decl(getattr(p, "text", "")) or "") in (gold, gb)), None)
            in_now, in_all = f(now) is not None, f(allp) is not None
            S["스텝"] += 1
            S["풀 지금"] += n_now; S["풀 stdlib포함"] += n_all; S["stdlib 개수"] += n_std
            S["gold 지금 있음"] += in_now; S["gold stdlib포함 있음"] += in_all
            if in_all and not in_now:
                S["★ stdlib 넣어야 생기는 gold"] += 1
            # 필터 통과율 (stdlib 포함 풀)
            gtop, ghs = goal_heads(step.goals[0])
            texts = [getattr(p, "text", "") or "" for p in allp]
            keep = keep_idx(head, texts, gtop, ghs)
            S["필터통과 stdlib포함"] += len(keep)
            gi = f(allp)
            if gi is not None:
                S["필터대상 gold"] += 1
                S["필터 gold 생존"] += (gi in keep)
            # 지금 풀에도 필터를 걸어 본다 (비교용)
            tn = [getattr(p, "text", "") or "" for p in now]
            S["필터통과 지금"] += len(keep_idx(head, tn, gtop, ghs))

            # ★★ 진짜 질문 — 풀이 커져도 gold 의 **순위**가 살아남나.
            #   풀 크기 자체는 문제가 아니다(tf-idf 는 O(n)). 문제는 방해꾼 12,000개가
            #   gold 를 top-100 밖으로 밀어내느냐다. 이게 아니면 필터가 필요 없다.
            r_now = r_all = r_flt = None
            if os.environ.get("SP_RANK", "1") == "1":
                rk = lambda ps: [ (decl(getattr(x, "text", "")) or "") for x in
                                  pc.get_ranked_premises(k, proof, dp, ps, False) ]
                if in_now:
                    nm = rk(now)
                    r_now = next((j for j, x in enumerate(nm) if x in (gold, gb)), None)
                if in_all:
                    nm = rk(allp)
                    r_all = next((j for j, x in enumerate(nm) if x in (gold, gb)), None)
                    sub = [allp[j] for j in keep]
                    if gi in keep:
                        nm = rk(sub)
                        r_flt = next((j for j, x in enumerate(nm) if x in (gold, gb)), None)
                for lab, r in (("지금", r_now), ("stdlib포함", r_all), ("+필터", r_flt)):
                    if r is not None:
                        S[f"순위 {lab} 대상"] += 1
                        for kk in (10, 50, 100):
                            S[f"{lab}@{kk}"] += (r < kk)
            fout.write(json.dumps(dict(tid=tid, k=k, gold=gold, head=head,
                                       n_now=n_now, n_all=n_all, n_std=n_std,
                                       in_now=in_now, in_all=in_all,
                                       keep_all=len(keep),
                                       gold_kept=(gi in keep) if gi is not None else None),
                                  ensure_ascii=False) + "\n")
        except Exception:
            S["오류"] += 1
    done += 1; fout.flush()
    if done % 5 == 0:
        print(f"   … {done} (스텝 {S['스텝']})", flush=True)

n = max(S["스텝"], 1)
print(f"\n■ {SPLIT} · 스텝 {S['스텝']} (오류 {S['오류']})")
print(f"\n  ① 풀 크기 (스텝당 평균)")
print(f"     지금 (proj-thm)   {S['풀 지금']/n:9,.0f}")
print(f"     stdlib 포함       {S['풀 stdlib포함']/n:9,.0f}"
      f"   ({S['풀 stdlib포함']/max(S['풀 지금'],1):.1f}배 · stdlib {S['stdlib 개수']/n:,.0f}개)")
print(f"\n  ② gold 이 풀에 있나")
print(f"     지금              {S['gold 지금 있음']/n*100:5.1f}%")
print(f"     stdlib 포함       {S['gold stdlib포함 있음']/n*100:5.1f}%"
      f"   (+{(S['gold stdlib포함 있음']-S['gold 지금 있음'])/n*100:.1f}pp)")
print(f"     ★ stdlib 넣어야 생기는 gold  {S['★ stdlib 넣어야 생기는 gold']}/{n}"
      f" = {S['★ stdlib 넣어야 생기는 gold']/n*100:.1f}%")
print(f"\n  ③ 건전 지문 필터가 몇 %를 남기나")
print(f"     지금 풀        {S['풀 지금']/n:9,.0f} → {S['필터통과 지금']/n:9,.0f}"
      f"  ({S['필터통과 지금']/max(S['풀 지금'],1)*100:5.1f}% 남음)")
print(f"     stdlib 포함    {S['풀 stdlib포함']/n:9,.0f} → {S['필터통과 stdlib포함']/n:9,.0f}"
      f"  ({S['필터통과 stdlib포함']/max(S['풀 stdlib포함'],1)*100:5.1f}% 남음)")
print(f"     → 필터 후 stdlib 포함 풀이 **지금 풀보다** "
      f"{S['필터통과 stdlib포함']/max(S['풀 지금'],1):.2f}배")
fn = max(S["필터대상 gold"], 1)
print(f"\n  ④ 필터가 gold 을 지키나  {S['필터 gold 생존']}/{S['필터대상 gold']}"
      f" = {S['필터 gold 생존']/fn*100:.1f}%")
if S["순위 지금 대상"] or S["순위 stdlib포함 대상"]:
    print(f"\n  ⑤ ★ gold 이 top-k 에 드나 (전체 {n} 스텝 기준)")
    print(f"     {'':12s}{'@10':>8s}{'@50':>8s}{'@100':>8s}")
    for lab in ("지금", "stdlib포함", "+필터"):
        if S[f"순위 {lab} 대상"]:
            print(f"     {lab:12s}" + "".join(f"{S[f'{lab}@{kk}']/n*100:7.1f}%" for kk in (10, 50, 100)))
