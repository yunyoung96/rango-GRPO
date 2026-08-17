#!/usr/bin/env python3
"""모델이 타입/goal 정보를 **쓸 수 있는지** 다각도 프로브 — SFT 없이 베이스 모델로.

## 배경

앞선 프로브(NLL of gold tactic)에서 1.3B·7B 모두 clean ≈ wrong (차이 0.001~0.005)이 나왔다.
그런데 그 실험만으로는 두 가지가 구분되지 않는다:

  (A) 모델이 타입 정의를 **읽지 못한다**
  (B) 읽기는 하는데 **다음 tactic 예측에 연결하지 못한다**

(A)라면 프롬프트 주입 전체가 무의미하고, (B)라면 연결을 가르치는 게 과제다.
그래서 **읽기 능력 자체**를 tactic 예측과 분리해 직접 잰다.

## 프로브 구성

  T1 생성자 세기   : 정의를 주고 `has N constructors` 의 N 을 맞히나
                     (정답 N vs 오답 N' 의 NLL 비교. 순수 읽기 — tactic 무관)
  T2 생성자 회상   : 정의를 주고 그 안의 생성자 이름을 이어쓰나
                     (정의에 있는 이름 vs 없는 가짜 이름의 NLL)
  T3 destruct 패턴 : `destruct x as [` 다음 정답 분기수 vs 오답 분기수
                     (읽기 → tactic 연결. T1 이 되고 T3 가 안 되면 (B))
  T4 goal 활용     : goal 의 변수 타입을 맞히나 (`x : ?`)
  T5 지시문 효과   : "타입 정보를 이용해 다음 tactic 을 예측하라" 같은 **명시적 지시**를
                     붙이면 gold tactic NLL 이 나아지나 (instruct 모델의 지시 따르기)

각 프로브는 **정답/오답 쌍의 NLL 차이**로 판정한다. 차이가 크고 정답이 낮으면 능력 있음.

사용:
    CUDA_VISIBLE_DEVICES=0 python3 scripts/probe_type_ability.py \
        --model deepseek-ai/deepseek-coder-1.3b-instruct --n 100
"""
import argparse
import json
import logging
import os
import random
import re
import statistics
import sys

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.insert(0, "src")
logging.disable(logging.CRITICAL)

import torch  # noqa: E402
from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: E402
from tactic_gen.lm_example import LmExample  # noqa: E402
from tactic_gen.augment import types_v2, definitions_v2  # noqa: E402

_CTOR = re.compile(r"\|\s*([A-Za-z_][\w']*)")


class Scorer:
    def __init__(self, model_name):
        print(f"모델: {model_name}")
        self.tok = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name, torch_dtype=torch.bfloat16).cuda().eval()

    def nll(self, prompt, target):
        pi = self.tok(prompt, return_tensors="pt", truncation=True,
                      max_length=3500)["input_ids"]
        ti = self.tok(target, return_tensors="pt", add_special_tokens=False)["input_ids"]
        ids = torch.cat([pi, ti], dim=1).cuda()
        lab = ids.clone()
        lab[:, : pi.shape[1]] = -100
        with torch.no_grad():
            return float(self.model(ids, labels=lab).loss)


def ctor_names(defn):
    if ":=" not in defn:
        return []
    return _CTOR.findall(defn.split(":=", 1)[1])


def ctor_count(defn):
    if ":=" not in defn or "..." in defn:
        return None
    head, body = defn.split(":=", 1)
    if not re.search(r"\b(Inductive|CoInductive|Variant)\b", head):
        return None
    n = len([p for p in body.split("|") if p.strip()])
    return n if n > 0 else None


def report(name, wins, tot, d_mean, note=""):
    rate = wins / max(tot, 1) * 100
    mark = "✅" if rate >= 65 else ("△" if rate >= 55 else "❌")
    print(f"   {mark} {name:24s} 정답선호 {wins:>3}/{tot:<3} = {rate:>5.1f}%   "
          f"ΔNLL {d_mean:+.4f}  {note}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="deepseek-ai/deepseek-coder-1.3b-instruct")
    ap.add_argument("--n", type=int, default=100)
    args = ap.parse_args()
    rnd = random.Random(0)
    sc = Scorer(args.model)
    idx = json.load(open("data/func_defs_v3.json"))

    steps = []
    for line in open("data/grpo_rollouts/goldsft_bs2.jsonl"):
        g = json.loads(line)
        for a in g["attempts"]:
            if a["reward"] < 1.0:
                continue
            for st in a["steps"]:
                if st.get("example") and st.get("tactic"):
                    e = LmExample.from_json(st["example"])
                    e.next_steps = [st["tactic"]]
                    steps.append(e)
    key = [s for s in steps if re.search(r"\b(destruct|induction)\b", s.next_steps[0])]
    sel = (key[: args.n // 2] + [s for s in steps if s not in key][: args.n // 2])[: args.n]

    r = {k: {"w": 0, "n": 0, "d": []} for k in ("T1", "T2", "T3", "T4", "T5a", "T5b")}
    for e in sel:
        goal = e.proof_state or ""
        tgt = e.next_steps[0]
        tl = types_v2(goal, idx, project=e.file_name, budget_tok=300)
        dl = definitions_v2(goal, idx, project=e.file_name, budget_tok=300)
        if not tl:
            continue
        blk = "\n".join(l for _, l in (tl + dl))

        # ── T1 생성자 세기 (순수 읽기) ──
        for nm, dfn in tl[:1]:
            n_true = ctor_count(dfn)
            if not n_true:
                continue
            n_bad = n_true + (1 if n_true < 8 else -1)
            p = f"{dfn}\n(* Question: how many constructors does {nm} have? *)\nAnswer: {nm} has "
            a = sc.nll(p, f"{n_true} constructors.")
            b = sc.nll(p, f"{n_bad} constructors.")
            r["T1"]["n"] += 1
            r["T1"]["d"].append(a - b)
            r["T1"]["w"] += int(a < b)

            # ── T2 생성자 회상 ──
            cs = ctor_names(dfn)
            if cs:
                p2 = f"{dfn}\n(* The constructors of {nm} are: *)\n"
                a2 = sc.nll(p2, cs[0])
                b2 = sc.nll(p2, "Zqfake_ctor")
                r["T2"]["n"] += 1
                r["T2"]["d"].append(a2 - b2)
                r["T2"]["w"] += int(a2 < b2)

            # ── T3 destruct 분기수 (읽기 → tactic 연결) ──
            p3 = f"[TYPES]\n{dfn}\n[STATE]\n{goal}\n[TACTIC]\ndestruct x as "
            a3 = sc.nll(p3, "[" + "|" * (n_true - 1) + "].")
            b3 = sc.nll(p3, "[" + "|" * (n_bad - 1) + "].")
            r["T3"]["n"] += 1
            r["T3"]["d"].append(a3 - b3)
            r["T3"]["w"] += int(a3 < b3)

        # ── T4 goal 의 변수 타입 맞히기 ──
        hyp = goal.split("\n\n", 1)[0]
        m = re.match(r"^\s*(\w+)\s*:\s*([A-Za-z_][\w']*)", hyp.strip())
        if m:
            var, typ = m.group(1), m.group(2)
            body = "\n".join(hyp.split("\n")[1:])
            p4 = f"[STATE]\n{body}\n\n(* What is the type of {var}? *)\n{var} : "
            a4 = sc.nll(p4, typ)
            b4 = sc.nll(p4, "Zqfake")
            r["T4"]["n"] += 1
            r["T4"]["d"].append(a4 - b4)
            r["T4"]["w"] += int(a4 < b4)

        # ── T5 명시적 지시문의 효과 ──
        INSTR = ("(* Use the type definitions below to determine the exact number of\n"
                 "   constructors and their arities, then predict the next tactic. *)\n")
        p_plain = f"[TYPES]\n{blk}\n[STATE]\n{goal}\n[TACTIC]\n"
        p_instr = INSTR + p_plain
        a5 = sc.nll(p_plain, tgt)
        b5 = sc.nll(p_instr, tgt)
        r["T5a"]["n"] += 1
        r["T5a"]["d"].append(b5 - a5)          # 음수면 지시문이 도움
        r["T5a"]["w"] += int(b5 < a5)
        # 지시문 + 타입 없음 (지시문만의 효과 분리)
        p_noty = f"[STATE]\n{goal}\n[TACTIC]\n"
        c5 = sc.nll(INSTR + p_noty, tgt)
        d5 = sc.nll(p_noty, tgt)
        r["T5b"]["n"] += 1
        r["T5b"]["d"].append(c5 - d5)
        r["T5b"]["w"] += int(c5 < d5)

    print(f"\n■ 타입/goal 활용 능력 프로브  ({args.model.split('/')[-1]})")
    print("   정답선호 = 정답 쪽 NLL 이 더 낮은 비율(50%=무작위). ΔNLL = 정답−오답(음수가 좋음)\n")
    names = {"T1": "생성자 세기(읽기)", "T2": "생성자 회상(읽기)",
             "T3": "destruct 분기수(연결)", "T4": "goal 변수 타입",
             "T5a": "지시문 효과(타입 있음)", "T5b": "지시문 효과(타입 없음)"}
    for k in ("T1", "T2", "T3", "T4", "T5a", "T5b"):
        if r[k]["n"]:
            report(names[k], r[k]["w"], r[k]["n"], statistics.mean(r[k]["d"]))
    print("\n   해석: T1/T2 가 높고 T3 가 낮으면 → 읽기는 되나 tactic 에 연결 못 함")
    print("        T1/T2 도 낮으면 → 애초에 못 읽음(프롬프트 주입 방향 자체가 무의미)")


if __name__ == "__main__":
    main()
