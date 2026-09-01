#!/usr/bin/env python3
"""★ dn_why 결과를 **rewrite 지점만** 떼어 본다.

기록에는 tactic 종류가 없으므로 원본에서 다시 읽어 붙인다.
    dnR=1  판별트리(rw 색인)가 정답을 돌려줬다
    dnR=0  못 돌려줬다 → 이게 rewrite 재현율의 손실 지점이다
"""
import json, os, re, sys, collections, logging
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")
os.environ["CUDA_VISIBLE_DEVICES"] = ""
sys.path.insert(0, "src"); sys.path.insert(0, "CoqStoq")
logging.disable(logging.CRITICAL)
from pathlib import Path
from coqstoq import Split as CSSplit, get_theorem
from data_management.sentence_db import SentenceDB
from evaluation.find_coqstoq_idx import get_thm_desc

SRC = sys.argv[1] if len(sys.argv) > 1 else "all_log/dn_why.jsonl"
sdb = SentenceDB.load(Path("raw-data/coqstoq-test/coqstoq-test-sentences.db"))
HEADT = re.compile(r"^\s*(?:now\s+|try\s+|repeat\s+)?([A-Za-z_][\w']*)")

rows = [json.loads(l) for l in open(SRC)]
by = collections.defaultdict(list)
for r in rows: by[r["idx"]].append(r)

S = collections.Counter(); D = collections.Counter(); EX = collections.defaultdict(list)
C = collections.defaultdict(list)
for i, rs in sorted(by.items()):
    try:
        d = get_thm_desc(get_theorem(CSSplit.TEST, i, Path("CoqStoq")),
                         Path("raw-data/coqstoq-test"), sdb)
        if d is None: continue
        proof = d.dp.proofs[d.idx]
    except Exception: continue
    for r in rs:
        try: t = proof.steps[r["k"]].step.text or ""
        except Exception: continue
        h = HEADT.match(t)
        if not h: continue
        tac = "rewrite" if h.group(1).endswith("rewrite") else "apply"
        S[f"{tac}|지점"] += 1
        real = r.get("real")
        if real is not None:
            S[f"{tac}|실제로됨"] += real
            if real == 0: S[f"{tac}|상태어긋남"] += 1
        surv = r["ap"] or r["in"] or r["rw"]
        if real == 1:
            S[f"{tac}|실제됨n"] += 1
            S[f"{tac}|실제됨중생존"] += bool(surv)
        S[f"{tac}|★생존"] += bool(surv)
        for tag in ("ap", "in", "rw"): S[f"{tac}|{tag}"] += r[tag]
        S[f"{tac}|색인에있음"] += r["indexed"]
        S[f"{tac}|dnR"] += r["dnR"]; S[f"{tac}|dnA"] += r["dnA"]
        C[f"{tac}|후보"].append(r["nap"] + r["nin"] + r["nrw"])
        C[f"{tac}|redex"].append(r["redex"])
        if tac == "rewrite" and not surv:
            # ★ 사슬 어디서 끊겼나: 관계 인식 → 머리 일치 → 단일화 → 트리
            if r.get("sides", -1) < 0:
                key = "① 관계로 인식 안 됨 (rw_sides 실패)"
            elif not r.get("headm"):
                key = "② redex 와 머리가 안 맞음 (keyed 실패)"
            elif not r.get("unifm"):
                key = "③ 머리는 맞는데 단일화 실패"
            elif not r["indexed"]:
                key = "④ 색인에 없음 (지역가설)"
            elif not r["dnR"]:
                key = "⑤ 단일화는 되는데 트리가 못 돌려줌"
            else:
                key = "⑥ 트리는 돌려줬는데 최종 탈락"
            D[key] += 1
            if len(EX[key]) < 6:
                EX[key].append((i, r["k"], r["name"], t.strip()[:70]))

print(f"■ dn_why {len(rows)} 기록 · 정리 {len(by)}\n")
for tac in ("apply", "rewrite"):
    n = max(S[f"{tac}|지점"], 1)
    print(f"── gold tactic = {tac} ({S[f'{tac}|지점']} 지점) ──")
    import statistics as stt
    print(f"   ★ 필터에서 살아남음    {S[f'{tac}|★생존']/n*100:5.1f}%")
    if S[f"{tac}|실제됨n"]:
        n3 = S[f"{tac}|실제됨n"]
        print(f"   ── 분모를 가르면 ──")
        print(f"   그 자리에서 실제로 됨  {S[f'{tac}|실제로됨']/n*100:5.1f}%"
              f"   (안 되는 {S[f'{tac}|상태어긋남']}건 = 재구성 상태가 어긋남)")
        print(f"   ★★ 실제로 되는 것 중 생존 {S[f'{tac}|실제됨중생존']/n3*100:5.1f}%"
              f"  ({S[f'{tac}|실제됨중생존']}/{n3})")
    print(f"     · apply 경로         {S[f'{tac}|ap']/n*100:5.1f}%")
    print(f"     · apply…in 경로      {S[f'{tac}|in']/n*100:5.1f}%")
    print(f"     · rewrite 경로       {S[f'{tac}|rw']/n*100:5.1f}%")
    print(f"   (귀속) 색인에 있음     {S[f'{tac}|색인에있음']/n*100:5.1f}%"
          f" · rw트리 {S[f'{tac}|dnR']/n*100:5.1f}%"
          f" · apply트리 {S[f'{tac}|dnA']/n*100:5.1f}%")
    if C[f'{tac}|후보']:
        print(f"   후보 중앙 {stt.median(C[f'{tac}|후보']):,.0f}"
              f" · redex 중앙 {stt.median(C[f'{tac}|redex']):,.0f}\n")
print("── ★ rewrite gold 가 필터에서 사라진 경우 ──")
tot = max(1, sum(D.values()))
for k, v in D.most_common(20):
    print(f"   {v:4d} ({v/tot*100:5.1f}%)  {k[:100]}")
print("\n── 보기 ──")
for k, _ in D.most_common(6):
    print(f"  [{k[:70]}]")
    for i, kk, nm, t in EX[k]:
        print(f"     idx {i:5d} k {kk:3d}  {nm:28s} {t}")
