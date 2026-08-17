#!/usr/bin/env python3
"""적용가능성을 재랭킹에 **얼마나** 섞을지 정한다.

적용가능성을 최우선(계층)으로 두면 top1 은 크게 오르지만(24→42%) top5 는 정체한다.
판정 재현율이 90% 라 10% 는 gold 를 잘못 떨어뜨리므로, 계층 대신 **점수 가산**으로 섞고
가중치를 훑어 top1/5/10 이 함께 좋아지는 지점을 찾는다.

점수 = (원순위 prior) + α×타입지향점수 + β×적용가능성      ← 기존 α=5.0 은 고정

사용: python3 scripts/tune_applicable_rerank.py <train|compcert> [n]
"""
import json
import os
import re
import sys

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.insert(0, "src")
import logging  # noqa: E402

logging.disable(logging.CRITICAL)
import yaml  # noqa: E402
from tactic_gen.lm_example import LmExample  # noqa: E402
from tactic_gen.applicable import applicability  # noqa: E402
from tactic_gen.tactic_data import _rr_score, _rr_goal_concl, _RR_ALPHA  # noqa: E402

SRC = sys.argv[1] if len(sys.argv) > 1 else "compcert"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 400
CONF = os.environ.get("CONF", "all_log/ft_qwen3b_v8_conf.yaml")
cc = yaml.safe_load(open(CONF))

_ID = re.compile(r"\b([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)\b")
_KW = {"rewrite", "apply", "eapply", "erewrite", "in", "with", "by", "at", "using",
       "auto", "eauto", "lia", "omega", "now", "intros", "destruct", "simpl", "unfold"}
_NAME = re.compile(r"^\s*(?:Lemma|Theorem|Definition|Corollary|Remark|Fact|Fixpoint|"
                   r"Instance|Axiom|Proposition|Example|Let)\s+"
                   r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
_LOCAL = re.compile(r"^(?:H\d*|H'+|IH\w*|Heq\w*|E\d*|e\d*)$")


def load_compcert(n):
    out = []
    for line in open("data/grpo_rollouts/goldsft_bs2.jsonl"):
        g = json.loads(line)
        for a in g["attempts"]:
            if a["reward"] < 1.0:
                continue
            for s in a["steps"]:
                if s.get("example") and s.get("tactic"):
                    e = LmExample.from_json(s["example"])
                    e.next_steps = [s["tactic"]]
                    out.append(e)
                    if len(out) >= n:
                        return out
    return out


def load_train(n):
    from tactic_gen.tactic_data import TacticDataConf, LmDataset
    from data_management.splits import Split
    ds = LmDataset.from_conf(TacticDataConf.from_yaml(cc["tactic_data"]), Split.TRAIN, n)
    out = []
    for i in range(n):
        try:
            out.append(ds.raw_example(i))
        except Exception:
            pass
    return out


examples = load_train(N) if SRC == "train" else load_compcert(N)

# 예제별로 (원순위 prior, 타입점수, 적용가능성, gold 인덱스) 를 미리 계산해두고
# 가중치만 바꿔 재정렬한다 (판정을 매번 다시 하면 느리다).
cases = []
for e in examples:
    prems = [p if isinstance(p, str) else getattr(p, "text", str(p))
             for p in (getattr(e, "premises", None) or [])]
    if not prems:
        continue
    tac = (e.next_steps[0] if getattr(e, "next_steps", None) else "").strip()
    head = tac.split()[0].lower().strip(";.") if tac.split() else ""
    if head not in ("rewrite", "apply", "eapply", "erewrite"):
        continue
    cand = [x for x in _ID.findall(tac[len(head):])
            if x not in _KW and not x.isdigit() and not _LOCAL.match(x)]
    if not cand:
        continue
    base = cand[0].split(".")[-1]
    gi = -1
    for i, t in enumerate(prems):
        m = _NAME.match(t)
        if m and m.group(1).split(".")[-1] == base:
            gi = i
            break
    if gi < 0:
        continue
    st = getattr(e, "proof_state", "") or ""
    gc = _rr_goal_concl(st)
    n_ = len(prems)
    rows = []
    for i, t in enumerate(prems):
        a = applicability(st, t)
        ok = 1.0 if ((not a["parsed"]) or a["apply"] or a["rw"] or a["rw_rev"]) else 0.0
        rows.append(((n_ - i), _rr_score(gc, t), ok, i))
    cases.append((rows, gi))

print(f"■ {SRC.upper()} — gold 를 premise 에서 찾은 {len(cases)}건 (α={_RR_ALPHA} 고정)\n")
print(f"   {'β':>6}  {'top1':>7} {'top5':>7} {'top10':>7} {'top20':>7}")


def evaluate(beta):
    ranks = []
    for rows, gi in cases:
        sc = sorted(rows, key=lambda r: (-(r[0] + _RR_ALPHA * r[1] + beta * r[2]), r[3]))
        ranks.append([r[3] for r in sc].index(gi))
    return [sum(1 for r in ranks if r < k) / max(len(ranks), 1) * 100
            for k in (1, 5, 10, 20)]


for beta in (0, 18, 20, 22, 25, 28, 30, 35, 40):
    t1, t5, t10, t20 = evaluate(beta)
    mark = "   ← 현재(β=0)" if beta == 0 else ("   ← 계층식과 동등" if beta == 1000 else "")
    print(f"   {beta:>6}  {t1:6.1f}% {t5:6.1f}% {t10:6.1f}% {t20:6.1f}%{mark}")
