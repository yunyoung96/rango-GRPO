#!/usr/bin/env python3
"""★ **적용가능성 필터를 tf-idf **앞에** 두면 gold 가 더 실리나** — 실측. GPU 불필요.

제안: tf-idf 로 점수를 매기기 전에 판별트리(discrimination tree) 류 색인으로
"실제로 적용 가능한" 것만 남기고, 그 안에서만 점수를 매긴다.

우리한테 이미 그 판정기가 있다 — `tactic_gen.applicable.usable_flags` 는
premise 를 `forall x…, H₁ → … → C` 로 파싱해 C 를 goal 결론과 **일차 단일화**한다.
판별트리가 색인으로 하는 일(유니피케이션 가능 후보만 꺼내기)을 선형탐색으로 하는 것이라,
**품질은 같고 속도만 다르다.** 지금 재는 것은 품질이므로 이걸로 충분하다.

★ §36 에서 기각된 것과 **다른 실험**이다:
    §36  `sig_applicable` 을 **점수 보너스**(커널)로 더했다 → 단조 악화
    여기 `usable_flags` 를 **하드 필터**로 앞에 둔다 → 후보 자체가 줄어든다
  커널은 순위를 흔들고, 필터는 경쟁자를 없앤다. 결과가 같을 이유가 없다.

재는 것 셋 (이 순서로 봐야 한다):
    ① 재현율   gold 가 필터를 살아남나 — **이게 100% 가 아니면 나머지는 볼 필요 없다**
    ② 축소율   후보가 몇 배로 줄어드나
    ③ 순위     gold 의 tf-idf 순위와 top-100 진입률이 실제로 오르나

사용: AF_N=60 AF_SHARD/AF_NSHARD python3 scripts/applic_filter_eval.py
"""
import collections, json, os, re, sys, yaml, logging
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")
os.environ["CUDA_VISIBLE_DEVICES"] = ""
sys.path.insert(0, "src"); sys.path.insert(0, "CoqStoq")
logging.disable(logging.CRITICAL)
from pathlib import Path
from coqstoq import Split as CSSplit, get_theorem
from data_management.sentence_db import SentenceDB
from evaluation.find_coqstoq_idx import get_thm_desc
from tactic_gen.lm_example import formatter_from_conf
from tactic_gen.tactic_data import TacticDataConf
from tactic_gen.applicable import usable_flags

NTHM = int(os.environ.get("AF_N", "60"))
SHARD = int(os.environ.get("AF_SHARD", "0"))
NSHARD = int(os.environ.get("AF_NSHARD", "1"))
MAXPT = int(os.environ.get("AF_MAX_PER_THM", "4"))
TOPK = int(os.environ.get("AF_TOPK", "100"))
OUT = Path(os.environ.get("AF_OUT", "all_log/applic_filter.jsonl"))
CONF = yaml.safe_load(open("all_log/ft_qwen3b_v10_conf.yaml"))
td = TacticDataConf.from_yaml(CONF["tactic_data"])
DATA_LOC = Path("raw-data/coqstoq-test")
sdb = SentenceDB.load(Path("raw-data/coqstoq-test/coqstoq-test-sentences.db"))
fm = formatter_from_conf(td.formatter_conf)
pc = fm.premise_client

NAMED = re.compile(r"\b(?:e?apply|e?rewrite)\s+(?:<-\s*)?\(?\s*"
                   r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
DECL = re.compile(r"^\s*(?:Local\s+|Global\s+|Program\s+)?"
                  r"(?:Lemma|Theorem|Definition|Corollary|Fixpoint|Inductive|Remark|"
                  r"Proposition|Instance|Record|Axiom)\s+([A-Za-z_][\w']*)")
HEAD = re.compile(r"^\s*(?:now\s+|try\s+|repeat\s+)?([A-Za-z_][\w']*)")

def decl_name(t):
    m = DECL.match(t or "")
    return m.group(1) if m else None

idx_all = [int(x) for x in Path("data/compcert_bs2_rand200_idx.txt").read_text().split()][:NTHM]
mine = [i for j, i in enumerate(idx_all) if j % NSHARD == SHARD]
print(f"■ 담당 {len(mine)} 정리 · top-{TOPK}", flush=True)

S = collections.Counter()
fout = OUT.open("w"); done = 0
for i in mine:
    try:
        thm = get_theorem(CSSplit.TEST, i, Path("CoqStoq"))
        d = get_thm_desc(thm, DATA_LOC, sdb)
        if d is None: continue
        dp, pidx = d.dp, d.idx
        proof = dp.proofs[pidx]
    except Exception:
        continue
    ks = []
    for k, st in enumerate(proof.steps):
        try: t = st.step.text
        except Exception: continue
        h = HEAD.match(t)
        if h and h.group(1) in ("apply", "eapply", "rewrite", "erewrite") and NAMED.search(t):
            ks.append(k)
    if not ks: continue
    if len(ks) > MAXPT:
        stp = len(ks) / MAXPT
        ks = [ks[int(j * stp)] for j in range(MAXPT)]
    for k in ks:
        try:
            step = proof.steps[k]
            gold = NAMED.search(step.step.text).group(1)
            gbare = gold.split(".")[-1]
            fr = pc.premise_filter.get_pos_and_avail_premises(step, proof, dp)
            avail = list(fr.avail_premises)
            if not avail: continue
            ranked = pc.get_ranked_premises(k, proof, dp, avail, False)
            texts = [getattr(p, "text", "") or "" for p in ranked]
            names = [decl_name(t) for t in texts]
            try: r_before = next(j for j, n in enumerate(names)
                                 if n and (n == gold or n == gbare))
            except StopIteration:
                S["gold 이 풀에 없음"] += 1
                continue
            gstate = "\n".join(step.goals[0].hyps) + "\n\n" + step.goals[0].goal if step.goals else ""
            flags = usable_flags(gstate, texts)
            keep = [j for j, f in enumerate(flags) if f]
            gold_kept = flags[r_before]
            r_after = keep.index(r_before) if gold_kept else None
            S["스텝"] += 1
            S["풀 총"] += len(texts); S["통과 총"] += len(keep)
            S["gold 살아남음"] += bool(gold_kept)
            S[f"before@{TOPK}"] += (r_before < TOPK)
            S[f"after@{TOPK}"] += (r_after is not None and r_after < TOPK)
            S["순위 오름"] += (r_after is not None and r_after < r_before)
            fout.write(json.dumps(dict(idx=i, k=k, gold=gold, pool=len(texts),
                                       kept=len(keep), r_before=r_before,
                                       r_after=r_after, gold_kept=bool(gold_kept)),
                                  ensure_ascii=False) + "\n")
        except Exception:
            S["오류"] += 1
    done += 1; fout.flush()
    if done % 5 == 0: print(f"   … {done}/{len(mine)} (스텝 {S['스텝']})", flush=True)

n = max(S["스텝"], 1)
print(f"\n■ 스텝 {S['스텝']} (gold 이 풀에 없음 {S['gold 이 풀에 없음']} · 오류 {S['오류']})")
print(f"\n  ① ★ 재현율 — gold 이 필터를 살아남나")
print(f"       {S['gold 살아남음']}/{n} = {S['gold 살아남음']/n*100:.1f}%"
      f"   {'✅ 안전' if S['gold 살아남음'] == n else '❌ gold 를 떨어뜨린다 — 여기서 끝'}")
print(f"\n  ② 축소율")
print(f"       풀 {S['풀 총']/n:,.0f}개 → 통과 {S['통과 총']/n:,.0f}개"
      f"  ({S['통과 총']/max(S['풀 총'],1)*100:.1f}%, {S['풀 총']/max(S['통과 총'],1):.1f}배 축소)")
print(f"\n  ③ gold 이 top-{TOPK} 에 드나")
print(f"       필터 전  {S[f'before@{TOPK}']}/{n} = {S[f'before@{TOPK}']/n*100:.1f}%")
print(f"       필터 후  {S[f'after@{TOPK}']}/{n} = {S[f'after@{TOPK}']/n*100:.1f}%"
      f"   ({(S[f'after@{TOPK}']-S[f'before@{TOPK}'])/n*100:+.1f}pp)")
print(f"       순위가 오른 스텝 {S['순위 오름']}/{n} = {S['순위 오름']/n*100:.1f}%")
