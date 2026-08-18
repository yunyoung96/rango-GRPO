#!/usr/bin/env python3
"""assert 로 쪼갠 뒤 **실제로 생기는 질의**로 gold lemma 가 건져지는가 — 정직한 값.

## 왜 다시 재나

앞선 측정(`research_assert_split.py`)은 질의를 **gold lemma L 자신의 결론**으로 만들었다.
L 을 L 의 문장으로 검색한 셈이라 순위가 높게 나오는 것이 당연하다 — **상한선**이다.

실제로 만들어지는 assert 명제는 그 증명 지점에서 **인스턴스화된** 형태다.

    gold L      forall n m, n + m = m + n
    상한 질의   n + m = m + n          ← L 의 결론 그대로 (앞선 측정)
    실제 질의   a + b = b + a          ← Check (L a b) 가 준 타입 (이 측정)

## 방법

gold 가 원래 goal 로는 top50 밖인 사례만 모아, **Coq 에 `Check (적용항).` 을 물어**
인스턴스화된 타입을 얻고 그것을 goal 로 같은 풀에서 재검색한다. 상한 질의도 같이 재서
둘을 나란히 놓는다.

사용: python3 scripts/measure_assert_query.py [스텝수] [train|val|test]
"""
import collections
import copy
import math
import os
import re
import sys
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.insert(0, "src")
import logging  # noqa: E402

logging.disable(logging.CRITICAL)
import yaml  # noqa: E402
from coqpyt.coq.base_file import CoqFile  # noqa: E402
from data_management.splits import Split  # noqa: E402
from data_management.dataset_file import (DatasetFile, get_ids_from_goal,  # noqa: E402
                                          get_ids_from_sentence)
from data_management.sentence_db import SentenceDB  # noqa: E402
from proof_retrieval.tfidf import tf_idf  # noqa: E402
from premise_selection.premise_filter import PremiseFilter, PremiseFilterConf  # noqa: E402
from tactic_gen.tactic_data import TacticDataConf, LmDataset  # noqa: E402
from tactic_gen.gold_lemma import gold_lemmas  # noqa: E402
from tactic_gen.search_query import local_names  # noqa: E402
from tactic_gen.applicable import decompose  # noqa: E402
from tactic_gen.assert_split import extract_application  # noqa: E402

_argv = sys.argv
sys.argv = [_argv[0], "1", "train"]
os.environ.setdefault("POOL_CAP", "100000")
sys.path.insert(0, "scripts")
import research_structural as RS  # noqa: E402
sys.argv = _argv

N = int(_argv[1]) if len(_argv) > 1 else 120
SPLIT = (_argv[2] if len(_argv) > 2 else "test").upper()
TOPK = 50
REPOS = (Path("/tmp/coq-dataset/repos") if SPLIT == "TRAIN"
         else Path(f"CoqStoq/{SPLIT.lower()}-repos"))

_NAME = re.compile(r"^\s*(?:Lemma|Theorem|Definition|Corollary|Remark|Fact|Fixpoint|"
                   r"Instance|Axiom|Proposition|Example|Let|Program\s+\w+)\s+"
                   r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")


def find_decl(src, decl):
    key = re.sub(r"\\ ", r"\\s+", re.escape(decl.strip()))
    m = re.search(key, src)
    if m:
        return m.start()
    mm = re.match(r"\s*\w+\s+([A-Za-z_][\w']*)", decl)
    if mm:
        m2 = re.search(r"^[ \t]*\w+\s+" + re.escape(mm.group(1)) + r"\b", src, re.M)
        if m2:
            return m2.start()
    return -1


cc = yaml.safe_load(open("all_log/ft_qwen3b_v8_conf.yaml"))
tdc = copy.deepcopy(cc["tactic_data"])
tdc["formatter_conf"].pop("proof_ret", None)
tdc["formatter_conf"].pop("num_proofs", None)
conf = TacticDataConf.from_yaml(tdc)
ds = LmDataset.from_conf(conf, getattr(Split, SPLIT), 20000)
sdb = SentenceDB.load(conf.sentence_db_loc)
pf = PremiseFilterConf.from_yaml(tdc["formatter_conf"]["premise"]["premise_filter"])
pfilter = PremiseFilter(pf.coq_excludes, pf.non_coq_excludes, pf.general_excludes)


class PoolRank:
    """한 증명 지점의 premise 풀. 구조 파싱은 **한 번만** 하고 질의만 바꿔가며 랭킹한다."""

    def __init__(self, pool):
        self.pool = pool
        self.docs = [get_ids_from_sentence(p) for p in pool]
        self.pss = [RS.prem_struct(getattr(p, "text", "") or "") for p in pool]
        df = collections.Counter()
        for ps in self.pss:
            if ps is not None:
                for k in ps[5]:
                    df[k] += 1
        nd = max(len(pool), 1)
        self.idf = {k: math.log(nd / v) for k, v in df.items()}

    @staticmethod
    def _ranks(v):
        o = sorted(range(len(v)), key=lambda j: -v[j])
        r = [0] * len(v)
        for p_, j in enumerate(o):
            r[j] = p_
        return r

    def scores(self, goal_text, hyp_block):
        class _G:
            def __init__(self, g, h):
                self.goal, self.hyps = g, h
        hyps = [ln for ln in hyp_block.split("\n") if ln.strip()] if hyp_block else []
        h_ids, g_ids = get_ids_from_goal(_G(goal_text, hyps))
        tf = tf_idf(h_ids + g_ids, self.docs)
        state = (hyp_block + "\n\n" + goal_text) if hyp_block else ("\n\n" + goal_text)
        gs = RS.goal_struct(state)
        n = len(self.pool)
        if gs is None:
            return tf, [0.0] * n, [0.0] * n, [0.0] * n
        c2 = [RS.sig_concl_heads(gs, ps, self.idf) if ps is not None else 0.0
              for ps in self.pss]
        ap = [RS.sig_applicable(gs, ps) if ps is not None else 0.0 for ps in self.pss]
        au = [RS.sig_anti_unify(gs, ps) if ps is not None else 0.0 for ps in self.pss]
        return tf, c2, ap, au

    def rank(self, goal_text, hyp_block, gset):
        """세 랭킹에서의 gold 순위.

          tfidf  현재 rango 가 쓰는 것 — **토큰 단위**
          rrf    tfidf + 결론구조 C' 의 순위역수합
          tier   ★ 적용가능성(단방향 유니피케이션)을 **계층**으로 올린 것
        """
        tf, c2, ap, au = self.scores(goal_text, hyp_block)
        rt, rc = self._ranks(tf), self._ranks(c2)
        n = len(self.pool)
        rrf = [1 / (60 + rt[j]) + 1 / (60 + rc[j]) for j in range(n)]
        tier = [rrf[j] + (1.0 if ap[j] > 0 else 0.0) + 0.01 * au[j] for j in range(n)]
        out = []
        for v in (tf, rrf, tier):
            o = sorted(range(n), key=lambda j: -v[j])
            pos = {j: r for r, j in enumerate(o)}
            out.append(min(pos[j] for j in gset))
        return out


KS = (1, 5, 10, 20, 50)
CNT = collections.defaultdict(collections.Counter)   # (질의종류, 랭커) → R@k
stat = collections.Counter()
n = 0

for i in range(20000):
    if n >= N:
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
    except Exception:
        continue
    pool = [p for p in dp.get_premises_before(proof) if pfilter.filter_premise(p)]
    if not pool:
        continue
    names = [(_NAME.match(getattr(p, "text", "") or "") or [None]) for p in pool]
    names = [m.group(1) if hasattr(m, "group") else None for m in names]
    gset = {j for j, nm in enumerate(names)
            if nm and nm.split(".")[-1] in golds}
    if not gset:
        continue
    hyp = st.split("\n\n")[0] if "\n\n" in st else ""
    try:
        pr = PoolRank(pool)
        r0v = pr.rank(RS.goal_conclusion(st), hyp, gset)
    except Exception:
        continue
    r0 = r0v[1]
    stat["gold 사용 스텝"] += 1
    if r0 < TOPK:
        continue                                    # 이미 잡히는 건 볼 필요 없다
    stat["top50 밖"] += 1

    # ── 실제 질의: Coq 에 인스턴스화된 타입을 묻는다 ──────────────────────
    script = getattr(e, "proof_script", "") or ""
    fc = getattr(dp.file_context, "file", "") or ""
    mm = re.search(r"repos/([^/]+)/(.+)$", fc)
    if not mm:
        continue
    proj_dir, rel = mm.group(1), mm.group(2)
    if SPLIT == "TRAIN":
        p0 = REPOS / proj_dir / rel
        cands = [p0] if p0.exists() else list(REPOS.glob(f"{proj_dir}/{rel}"))
    else:
        cands = list(REPOS.glob(f"*/{rel}")) or list(REPOS.glob(f"**/{rel}"))
    if not cands:
        stat["소스 없음"] += 1
        continue
    vf = cands[0].resolve()
    try:
        src = vf.read_text(errors="ignore")
    except Exception:
        continue
    at = find_decl(src, script.strip().split("\n")[0].strip())
    if at < 0:
        stat["선언 위치 못 찾음"] += 1
        continue
    ws = str((REPOS / cands[0].relative_to(REPOS).parts[0]).resolve())
    gname = sorted(golds)[0]
    r = extract_application(tac, gname)
    term = r[0] if r else gname
    ty = None
    bak = vf.parent / (vf.name + ".qbak")
    try:
        vf.rename(bak)
        vf.write_text(src[:at] + script + f"\nCheck ({term}).\n")
        cf = CoqFile(str(vf), timeout=180, workspace=ws)
        cf.run()
        for m in [getattr(d, "message", "") for d in cf.diagnostics
                  if getattr(d, "severity", 0) == 3]:
            mm2 = re.match(r"\s*(.+?)\s*:\s*(.+)$", m, re.S)
            if mm2:
                ty = " ".join(mm2.group(2).split())
                break
        cf.close()
    except Exception:
        pass
    finally:
        vf.unlink(missing_ok=True)
        if bak.exists():
            bak.rename(vf)
    if not ty:
        stat["Check 실패"] += 1
        continue

    d = decompose(ty)
    real_goal = " ".join(d[2]) if d else ty
    gtext = getattr(pool[min(gset)], "text", "") or ""
    d2 = decompose(gtext)
    orc_goal = " ".join(d2[2]) if d2 else gtext
    # ★ `assert (P) as H. { … }` 안에서는 **원래 가설 문맥이 그대로 남는다** —
    #   그러니 질의에 가설블록을 포함하는 쪽이 실제 상황이다. 둘 다 잰다.
    try:
        rv_real = pr.rank(real_goal, hyp, gset)
        rv_orc = pr.rank(orc_goal, "", gset)
    except Exception:
        continue
    n += 1
    for ri, rn in enumerate(("tfidf", "RRF", "계층")):
        for k in KS:
            CNT[("원래 goal", rn)][k] += (r0v[ri] < k)
            CNT[("assert 실제", rn)][k] += (rv_real[ri] < k)
            CNT[("assert 상한", rn)][k] += (rv_orc[ri] < k)
    if n <= 8:
        print(f"  [{n}] {gname:22s} 원래 {r0:5d}위 → assert 실제 "
              f"tfidf {rv_real[0]:4d} / RRF {rv_real[1]:4d} / 계층 {rv_real[2]:4d}",
              flush=True)

print(f"\n■ {SPLIT} — gold 가 (RRF 기준) top{TOPK} 밖인 {n}건")
print(f"   {'질의':12s} {'랭커':7s} " + " ".join(f"{'R@'+str(k):>7s}" for k in KS))
for q in ("원래 goal", "assert 실제", "assert 상한"):
    for rn in ("tfidf", "RRF", "계층"):
        c = CNT[(q, rn)]
        print(f"   {q:12s} {rn:7s} "
              + " ".join(f"{c[k]/max(n,1)*100:6.1f}%" for k in KS))
print()
for k in sorted(stat, key=lambda x: -stat[x]):
    print(f"   {k:20s} {stat[k]}")
