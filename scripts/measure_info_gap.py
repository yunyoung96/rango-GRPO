#!/usr/bin/env python3
"""프롬프트의 **정보 결손**을 TRAIN 과 CompCert 양쪽에서 잰다.

## 왜 두 곳을 다 보나

  · TRAIN(513 프로젝트)  — 모델이 **배우는** 분포. 여기서 정보가 없으면 "기억으로 메우기"를 배운다.
  · CompCert(gold 롤아웃) — 모델이 **평가받는** 분포. 여기서 정보가 없으면 못 푼다.

v8 은 이름을 익명화하므로 기억으로 메우는 경로가 막힌다. 정보가 없는 채 기억만 막으면
**불가능한 문제**가 되므로, 결손 비율을 먼저 알아야 한다.

## 재는 것

  G1 타입 결손   [DEFINITIONS] 에 실린 함수의 시그니처에 나오는 타입이 [TYPES] 에 없는 비율
  G2 lemma 결손  gold 가 쓴 rewrite/apply lemma 가 프롬프트 어디에도 없는 비율

사용: python3 scripts/measure_info_gap.py <train|compcert> [n]
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
from transformers import AutoTokenizer  # noqa: E402
from tactic_gen.lm_example import LmExample  # noqa: E402
import tactic_gen.tactic_data as td  # noqa: E402
from tactic_gen.augment import _is_type_def, pick_def  # noqa: E402

SRC = sys.argv[1] if len(sys.argv) > 1 else "compcert"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 150
CONF = os.environ.get("CONF", "all_log/ft_qwen3b_v8_conf.yaml")
cc = yaml.safe_load(open(CONF))
tok = AutoTokenizer.from_pretrained(cc["model_name"])
col = td.example_collator_from_conf(td.example_collator_conf_from_yaml(cc["example_collator"]))
IDX = json.load(open(os.environ.get("FUNC_DEFS_PATH", "data/func_defs_v3.json")))

_STD = {"nat", "list", "bool", "option", "Z", "N", "Prop", "Type", "Set", "unit", "prod",
        "sum", "positive", "string", "comparison", "int", "True", "False", "and", "or",
        "not", "eq", "forall", "fun", "match", "with", "end", "if", "then", "else"}
_ID = re.compile(r"\b([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)\b")
_KW = {"rewrite", "apply", "eapply", "erewrite", "in", "with", "by", "at", "using",
       "auto", "eauto", "lia", "now", "intros", "destruct", "simpl", "unfold"}


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
    import copy
    from tactic_gen.tactic_data import TacticDataConf, LmDataset
    from data_management.splits import Split
    tdc = copy.deepcopy(cc["tactic_data"])
    # ★ [PROOFS] 용 BM25 유사증명 검색이 **예제당 수십 초**를 먹는다(py-spy 로 확인).
    #   G1(타입 결손)은 [PROOFS] 와 무관하므로 뺀다. G2 는 [PROOFS] 가 필요하니 값이 낮게 나온다.
    if os.environ.get("SKIP_PROOF_RET", "1") == "1":
        tdc["formatter_conf"].pop("proof_ret", None)
        tdc["formatter_conf"].pop("num_proofs", None)
    ds = LmDataset.from_conf(TacticDataConf.from_yaml(tdc), Split.TRAIN, n)
    out = []
    for i in range(n):
        try:
            out.append(ds.raw_example(i))
        except Exception:
            pass
    return out


examples = load_train(N) if SRC == "train" else load_compcert(N)

n_inj = 0
miss_types = 0
n_with_miss = 0
missing = collections.Counter()
n_lem = lem_hit = 0

for e in examples:
    prompt = col.collate_input(tok, e)
    inj = dict(td._LAST_INJECTED)

    # ── G1 타입 결손 ──
    if inj:
        n_inj += 1
        miss = set()
        for k, d in inj.items():
            if _is_type_def(d):
                continue                       # 함수/정의만 본다
            sig = d.split(":=", 1)[0]
            for r in re.findall(r"[A-Za-z_][\w']*", sig):
                if r in _STD or r in inj or r == k:
                    continue
                c = IDX.get(r)
                if not isinstance(c, dict):
                    continue
                dd = pick_def(c, e.file_name)
                if dd and _is_type_def(dd):     # 실재 타입인데 프롬프트에 없음
                    miss.add(r)
        miss_types += len(miss)
        if miss:
            n_with_miss += 1
            missing.update(miss)

    # ── G2 gold lemma 결손 ──
    tac = (e.next_steps[0] if getattr(e, "next_steps", None) else "").strip()
    head = tac.split()[0].lower().strip(";.") if tac.split() else ""
    if head in ("rewrite", "apply", "eapply", "erewrite"):
        names = [x for x in _ID.findall(tac[len(head):]) if x not in _KW and not x.isdigit()]
        if names:
            n_lem += 1
            base = names[0].split(".")[-1]
            if re.search(r"(?<![\w'])" + re.escape(base) + r"(?![\w'])", prompt):
                lem_hit += 1

print(f"■ {SRC.upper()} — 예제 {len(examples)}개")
print(f"   G1 함수 시그니처 타입 결손 : {n_with_miss}/{n_inj} 예제 "
      f"({n_with_miss / max(n_inj, 1) * 100:.1f}%), 총 {miss_types}개")
if missing:
    print(f"      자주 빠지는 타입: {[k for k, _ in missing.most_common(6)]}")
print(f"   G2 gold lemma 가 프롬프트에 : {lem_hit}/{n_lem} "
      f"({lem_hit / max(n_lem, 1) * 100:.1f}%)  → 결손 {100 - lem_hit / max(n_lem, 1) * 100:.1f}%")
