#!/usr/bin/env python3
"""**끝단 검증** — 적용가능성 재랭킹이 실제 프롬프트의 gold 포함률을 올리는가.

앞선 측정들은 premise 리스트 순위만 봤다. 하지만 실제로 중요한 건 **토큰예산에 잘려
프롬프트에 실제로 실린 뒤에도** gold 가 남아 있는가다. 여기서는 학습이 쓰는 것과 같은
collate 경로를 그대로 타고, 완성된 프롬프트 문자열에서 gold 이름을 찾는다.

gold 가 프롬프트에 없는 예제는 **암기를 훈련**하므로(읽을 수 없는 이름을 뱉으라고 가르친다),
이 수치가 곧 "암기 강요 비율"의 역이다.

사용: python3 scripts/verify_applicable_e2e.py <train|compcert> [n]
"""
import importlib
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
from transformers import AutoTokenizer  # noqa: E402
from tactic_gen.lm_example import LmExample  # noqa: E402

SRC = sys.argv[1] if len(sys.argv) > 1 else "compcert"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 400
CONF = os.environ.get("CONF", "all_log/ft_qwen3b_v8_conf.yaml")
cc = yaml.safe_load(open(CONF))
tok = AutoTokenizer.from_pretrained(cc["model_name"])

_ID = re.compile(r"\b([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)\b")
_KW = {"rewrite", "apply", "eapply", "erewrite", "in", "with", "by", "at", "using",
       "auto", "eauto", "lia", "omega", "now", "intros", "destruct", "simpl", "unfold"}
_LOCAL = re.compile(r"^(?:H\d*|H'+|IH\w*|Heq\w*|E\d*|e\d*)$")


def load(src, n):
    if src == "train":
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


examples = load(SRC, N)


def measure(flag: bool):
    """flag=True 면 적용가능성 재랭킹을 켠 채로 프롬프트를 만든다."""
    os.environ["APPLICABLE_RERANK"] = "1" if flag else "0"
    import tactic_gen.tactic_data as td
    importlib.reload(td)                       # 모듈 상수(_RR_APPLICABLE)를 다시 읽게 한다
    col = td.example_collator_from_conf(
        td.example_collator_conf_from_yaml(cc["example_collator"]))
    hit_any = hit_prem = tot = 0
    n_prem = 0
    in_list = hit_prem_of_list = 0
    for e in examples:
        tac = (e.next_steps[0] if getattr(e, "next_steps", None) else "").strip()
        head = tac.split()[0].lower().strip(";.") if tac.split() else ""
        if head not in ("rewrite", "apply", "eapply", "erewrite"):
            continue
        cand = [x for x in _ID.findall(tac[len(head):])
                if x not in _KW and not x.isdigit() and not _LOCAL.match(x)]
        if not cand:
            continue
        p = col.collate_input(tok, e)
        seg = p.split("[PREMISES]")[-1].split("[PROOFS]")[0]
        n_prem += sum(seg.count(k + " ") for k in
                      ("Lemma", "Theorem", "Definition", "Fixpoint", "Corollary"))
        tot += 1
        base = cand[0].split(".")[-1]
        rx = re.compile(r"(?<![\w'])" + re.escape(base) + r"(?![\w'])")
        hit_any += bool(rx.search(p))                      # 프롬프트 어디든
        inp = bool(rx.search(seg))
        hit_prem += inp                                    # [PREMISES] 안에
        # ★ 재랭킹이 손댈 수 있는 건 **검색 후보에 gold 가 있는 경우**뿐이다.
        #   후보에 아예 없으면 순서를 어떻게 바꿔도 못 넣는다 → 분모를 나눠 본다.
        cands = [(x if isinstance(x, str) else str(x)) for x in (e.premises or [])]
        if any(_DECL_NAME(c) == base for c in cands):
            in_list += 1
            hit_prem_of_list += inp
    return dict(hit_any=hit_any, hit_prem=hit_prem, tot=tot, n_prem=n_prem / max(tot, 1),
                in_list=in_list, hit_of_list=hit_prem_of_list)


_NAME_RE = re.compile(r"^\s*(?:Lemma|Theorem|Definition|Corollary|Remark|Fact|Fixpoint|"
                      r"Instance|Axiom|Proposition|Example|Let)\s+"
                      r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")


def _DECL_NAME(t):
    m = _NAME_RE.match(t)
    return m.group(1).split(".")[-1] if m else None


off = measure(False)
on = measure(True)


def pct(a, b):
    return a / max(b, 1) * 100


print(f"\n■ {SRC.upper()} — gold 가 lemma 를 쓰는 {off['tot']}건")
print(f"   그중 검색 후보에 gold 가 있는 경우 {off['in_list']}건 "
      f"({pct(off['in_list'], off['tot']):.1f}%)  ← 재랭킹이 손댈 수 있는 범위\n")
print(f"   {'':22s} {'끔':>16s} {'켬':>16s}   변화")
print(f"   {'[PREMISES] 안에':22s} {off['hit_prem']:5d}={pct(off['hit_prem'],off['tot']):5.1f}%"
      f"    {on['hit_prem']:5d}={pct(on['hit_prem'],on['tot']):5.1f}%"
      f"   {pct(on['hit_prem'],on['tot'])-pct(off['hit_prem'],off['tot']):+5.1f}pp")
print(f"   {'  ↳ 후보에 있던 것만':22s} {off['hit_of_list']:5d}="
      f"{pct(off['hit_of_list'],off['in_list']):5.1f}%"
      f"    {on['hit_of_list']:5d}={pct(on['hit_of_list'],on['in_list']):5.1f}%"
      f"   {pct(on['hit_of_list'],on['in_list'])-pct(off['hit_of_list'],off['in_list']):+5.1f}pp")
print(f"   {'프롬프트 어디든':22s} {off['hit_any']:5d}={pct(off['hit_any'],off['tot']):5.1f}%"
      f"    {on['hit_any']:5d}={pct(on['hit_any'],on['tot']):5.1f}%"
      f"   {pct(on['hit_any'],on['tot'])-pct(off['hit_any'],off['tot']):+5.1f}pp")
print(f"   {'실린 premise 평균':22s} {off['n_prem']:11.1f}개    {on['n_prem']:11.1f}개")
print(f"\n   ⇒ 암기 강요(gold 를 프롬프트 어디서도 못 읽는데 타깃은 요구): "
      f"{100-pct(off['hit_any'],off['tot']):.1f}% → {100-pct(on['hit_any'],on['tot']):.1f}%")
