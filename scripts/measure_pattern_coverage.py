#!/usr/bin/env python3
"""**패턴 검색이 원리적으로 안 통하는 경우**가 얼마나 되나.

SearchPattern 은 lemma 의 **결론 모양**으로 찾는다. 그러므로 다음은 못 잡거나 약하다.

  A. goal 결론이 지역변수뿐이라 패턴이 `_` 로 무너짐   (`P x` 에서 P 가 가설의 술어변수)
  B. gold lemma 의 **결론이 메타변수 head** 인 경우      (`forall P, … -> P x` 꼴)
     — 어떤 goal 과도 매칭되므로 패턴으로 좁힐 수 없다
  C. 결론이 goal 과 구문적으로 다르고 unfold/delta 축약 후에야 맞는 경우
  D. `apply H in H0` 처럼 **가설**에 적용하는 경우 (goal 결론과 무관)
  E. eapply — 결론에 안 나오는 변수가 있어 통합이 지연되는 경우

여기서는 정적으로 셀 수 있는 A·B·D·E 를 재고, 나머지는 한계로 남긴다.
C 는 Coq 없이는 판정 불가.

사용: python3 scripts/measure_pattern_coverage.py [n] [train|test]
"""
import collections
import copy
import math
import os
import re
import sys

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.insert(0, "src")
import logging  # noqa: E402

logging.disable(logging.CRITICAL)
import yaml  # noqa: E402
from data_management.splits import Split  # noqa: E402
from tactic_gen.tactic_data import TacticDataConf, LmDataset  # noqa: E402
from tactic_gen.applicable import decompose, parse_toks, canon, as_eq  # noqa: E402
from tactic_gen.search_query import queries, goal_patterns, local_names  # noqa: E402
from tactic_gen.gold_lemma import _TACKW, _LOCALPAT, _IDRE  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
SPLIT = (sys.argv[2] if len(sys.argv) > 2 else "train").upper()
CONF = os.environ.get("CONF", "all_log/ft_qwen3b_v8_conf.yaml")

cc = yaml.safe_load(open(CONF))
tdc = copy.deepcopy(cc["tactic_data"])
tdc["formatter_conf"].pop("proof_ret", None)
tdc["formatter_conf"].pop("num_proofs", None)
conf = TacticDataConf.from_yaml(tdc)
ds = LmDataset.from_conf(conf, getattr(Split, SPLIT), N)

_NAME = re.compile(r"^\s*(?:Lemma|Theorem|Definition|Corollary|Remark|Fact|Fixpoint|"
                   r"Instance|Axiom|Proposition|Example|Let|Program\s+\w+)\s+"
                   r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")


def declname(t):
    m = _NAME.match(t or "")
    return m.group(1).split(".")[-1] if m else None


def head_of(t):
    """항 트리의 최상위 head 식별자 (application 을 왼쪽으로 따라간다)."""
    while t is not None and t[0] == "app":
        t = t[1]
    if t is None:
        return None
    if t[0] == "id":
        return t[1]
    if t[0] == "op":
        return t[1]
    return None


cnt = collections.Counter()
n_tac = 0
ex = collections.defaultdict(list)

for i in range(N):
    try:
        e = ds.raw_example(i)
    except Exception:
        continue
    tac = (e.next_steps[0] if getattr(e, "next_steps", None) else "").strip()
    piece = re.split(r"\s*;\s*", tac)[0]
    toks = piece.split()
    if not toks:
        continue
    head = toks[0].lower().strip(";.")
    if head not in ("apply", "eapply", "rewrite", "erewrite"):
        continue
    state = getattr(e, "proof_state", "") or ""
    loc = local_names(state)
    rest_all = piece[len(head):]
    names = [x.split(".")[-1] for x in _IDRE.findall(re.split(r"\bin\b", rest_all)[0])]
    names = [b for b in names
             if b not in _TACKW and not b.isdigit() and not _LOCALPAT.match(b)
             and not (len(b) < 3 and b.islower()) and b not in loc]
    if not names:
        continue
    n_tac += 1
    base = names[0]

    # ── D: 가설에 적용하는가 (`apply H in H0`) ──
    if re.search(r"\bin\b", rest_all):
        cnt["D goal 이 아니라 **가설**에 적용"] += 1
        if len(ex["D"]) < 4:
            ex["D"].append(tac[:60])
        continue

    # ── A: goal 결론에서 쓸 만한 패턴이 안 나오는가 ──
    qs = goal_patterns(state)
    if not qs:
        cnt["A goal 결론이 지역변수뿐 → 패턴 무의미"] += 1
        if len(ex["A"]) < 4:
            ex["A"].append(f"{tac[:40]}  goal={state.split(chr(10))[-1][:40]}")
        continue

    # ── B: gold lemma 의 결론 head 가 메타변수인가 ──
    prem = next((p if isinstance(p, str) else getattr(p, "text", str(p))
                 for p in (getattr(e, "premises", None) or [])
                 if declname(p if isinstance(p, str) else getattr(p, "text", "")) == base), None)
    if prem is not None:
        d = decompose(prem)
        if d is not None:
            mv, _h, ct = d
            c = parse_toks(ct)
            if c is not None:
                c = canon(c)
                eq = as_eq(c)
                hd = head_of(eq[0] if (eq and head in ("rewrite", "erewrite")) else c)
                if hd is not None and hd in mv:
                    cnt["B lemma 결론 head 가 **메타변수** → 패턴으로 못 좁힘"] += 1
                    if len(ex["B"]) < 4:
                        ex["B"].append(f"{base}: {' '.join(ct)[:58]}")
                    continue

    # ── E: eapply (결론에 안 나오는 변수가 남음) ──
    if head == "eapply":
        cnt["E eapply (통합 지연)"] += 1
        if len(ex["E"]) < 3:
            ex["E"].append(tac[:60])
        continue

    cnt["OK 패턴 검색이 원리적으로 통함"] += 1


def ci(p, n):
    return 1.96 * math.sqrt(max(p * (1 - p), 1e-12) / max(n, 1)) * 100


print(f"\n■ {SPLIT} — apply/rewrite 계열 {n_tac}건 중 **패턴 검색이 통하는가**\n")
for k in sorted(cnt, key=lambda x: -cnt[x]):
    p = cnt[k] / max(n_tac, 1)
    print(f"   {k:46s} {cnt[k]:5d} = {p*100:5.1f}%  ±{ci(p, n_tac):4.1f}pp")
for t, title in (("A", "A goal 결론이 지역변수뿐"),
                 ("B", "B lemma 결론 head 가 메타변수"),
                 ("D", "D 가설에 적용"),
                 ("E", "E eapply")):
    if ex[t]:
        print(f"\n   {title}:")
        for s in ex[t]:
            print(f"     · {s}")
