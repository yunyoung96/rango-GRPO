#!/usr/bin/env python3
"""적용가능성 판정이 **쓸 만한가**를 실제 데이터로 잰다.

## 판정이 좋으려면 두 가지가 동시에 성립해야 한다

  R 재현율  gold 가 실제로 쓴 lemma 를 "적용 가능"으로 남기는가   ← 낮으면 못 씀(정답을 버림)
  S 선택성  전체 premise 중 몇 %만 남기는가                        ← 100% 면 무의미(안 거름)

R 이 높고 S 가 낮을수록 좋다. R 이 95% 미만이면 **필터로 쓰면 안 되고** 재랭킹 신호로만 쓴다.

## 추가로 재는 것

  · 파싱 성공률 (보수적 통과가 얼마나 자주 일어나나 = 판정 능력의 상한)
  · gold lemma 의 순위가 재랭킹으로 얼마나 올라가나 (top-1 / top-5 / top-10)

사용: python3 scripts/measure_applicable.py <train|compcert> [n]
"""
import collections
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
from tactic_gen.tactic_data import _rr_score, _rr_goal_concl  # noqa: E402

SRC = sys.argv[1] if len(sys.argv) > 1 else "compcert"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 200
CONF = os.environ.get("CONF", "all_log/ft_qwen3b_v8_conf.yaml")
cc = yaml.safe_load(open(CONF))

_ID = re.compile(r"\b([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)\b")
_KW = {"rewrite", "apply", "eapply", "erewrite", "in", "with", "by", "at", "using",
       "auto", "eauto", "lia", "now", "intros", "destruct", "simpl", "unfold", "H"}
_NAME = re.compile(r"^\s*(?:Lemma|Theorem|Definition|Corollary|Remark|Fact|Fixpoint|"
                   r"Instance|Axiom|Proposition|Example|Let)\s+([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")


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

n_prem = n_parsed = 0
keep = collections.Counter()          # 몇 %가 살아남나
n_gold = 0
gold_kept = gold_kept_mode = 0
gold_unparsed = 0
rank_before = []
rank_after = []
head_cnt = collections.Counter()

for e in examples:
    prems = list(getattr(e, "premises", None) or [])
    if not prems:
        continue
    state = getattr(e, "proof_state", "") or ""
    ptexts = [p if isinstance(p, str) else getattr(p, "text", str(p)) for p in prems]
    apps = [applicability(state, t) for t in ptexts]
    for a in apps:
        n_prem += 1
        n_parsed += a["parsed"]
        keep["apply"] += (not a["parsed"]) or a["apply"]
        keep["rw"] += (not a["parsed"]) or a["rw"] or a["rw_rev"]
        keep["any"] += (not a["parsed"]) or a["apply"] or a["rw"] or a["rw_rev"]

    # ── gold lemma 를 premise 목록에서 찾는다 ──
    tac = (e.next_steps[0] if getattr(e, "next_steps", None) else "").strip()
    head = tac.split()[0].lower().strip(";.") if tac.split() else ""
    if head not in ("rewrite", "apply", "eapply", "erewrite"):
        continue
    names = [x for x in _ID.findall(tac[len(head):]) if x not in _KW and not x.isdigit()]
    if not names:
        continue
    base = names[0].split(".")[-1]
    gi = -1
    for i, t in enumerate(ptexts):
        m = _NAME.match(t)
        if m and m.group(1).split(".")[-1] == base:
            gi = i
            break
    if gi < 0:
        continue                       # gold 가 프롬프트에 없음 — 검색 결손(별도 지표)
    n_gold += 1
    head_cnt[head] += 1
    a = apps[gi]
    if not a["parsed"]:
        gold_unparsed += 1
    gold_kept += (not a["parsed"]) or a["apply"] or a["rw"] or a["rw_rev"]
    if head in ("rewrite", "erewrite"):
        gold_kept_mode += (not a["parsed"]) or a["rw"] or a["rw_rev"]
    else:
        gold_kept_mode += (not a["parsed"]) or a["apply"]

    # ── 순위: 현재(재랭킹 후 순서 그대로) vs 적용가능성 우선 ──
    rank_before.append(gi)
    gc = _rr_goal_concl(state)
    scored = []
    for i, t in enumerate(ptexts):
        aa = apps[i]
        ok = (not aa["parsed"]) or aa["apply"] or aa["rw"] or aa["rw_rev"]
        strong = aa["parsed"] and (aa["apply"] or aa["rw"] or aa["rw_rev"])
        # 적용가능(확정) > 판정불가 > 불가.  동급 안에서는 기존 타입점수로.
        scored.append(((2 if strong else (1 if ok else 0)), _rr_score(gc, t), -i, i))
    scored.sort(key=lambda x: (-x[0], -x[1], -x[2]))
    rank_after.append([s[3] for s in scored].index(gi))


def topk(rs, k):
    return sum(1 for r in rs if r < k) / max(len(rs), 1) * 100


print(f"\n■ {SRC.upper()} — 예제 {len(examples)}개 · premise {n_prem}개")
print(f"   파싱 성공률          {n_parsed}/{n_prem} = {n_parsed/max(n_prem,1)*100:5.1f}%"
      f"   (실패분은 보수적으로 전부 통과)")
print(f"   S 선택성 — 남는 비율  apply {keep['apply']/max(n_prem,1)*100:5.1f}%"
      f" · rewrite {keep['rw']/max(n_prem,1)*100:5.1f}%"
      f" · 둘중하나 {keep['any']/max(n_prem,1)*100:5.1f}%")
print(f"\n   gold 가 premise 안에 있는 경우 {n_gold}건  {dict(head_cnt)}")
print(f"   R 재현율(둘중하나)    {gold_kept}/{n_gold} = {gold_kept/max(n_gold,1)*100:5.1f}%"
      f"   ← 95%% 미만이면 필터 금지")
print(f"   R 재현율(tactic 별)   {gold_kept_mode}/{n_gold} = {gold_kept_mode/max(n_gold,1)*100:5.1f}%")
print(f"   그중 판정불가로 통과   {gold_unparsed}/{n_gold} = {gold_unparsed/max(n_gold,1)*100:5.1f}%")
print(f"\n   gold 순위   현재:  top1 {topk(rank_before,1):5.1f}%  top5 {topk(rank_before,5):5.1f}%"
      f"  top10 {topk(rank_before,10):5.1f}%")
print(f"               적용성: top1 {topk(rank_after,1):5.1f}%  top5 {topk(rank_after,5):5.1f}%"
      f"  top10 {topk(rank_after,10):5.1f}%")
