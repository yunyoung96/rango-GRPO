#!/usr/bin/env python3
"""★ 암기인가 이해인가 — **코퍼스에 없는 새 타입**으로 타입 추론 능력을 가린다.

## 왜 새 타입인가

앞선 프로브는 CompCert 등 **실재 타입**을 썼다. 그러면 "정의를 읽고 세었다"와
"학습 때 본 걸 외웠다"가 구분되지 않는다. 3B 가 생성자 세기 42.9%인데 destruct 분기수는
92.9%인 것도 암기로 설명 가능하다(흔한 타입의 destruct 패턴을 통째로 외움).

→ **그 자리에서 만든 타입**(코퍼스에 존재하지 않는 이름·구조)으로 물으면 암기가 불가능하다.
   맞히면 진짜로 정의를 읽고 추론한 것이다.

## 실험 (전부 NLL 대조 — 정답/오답 쌍의 선호도)

  U1 새 타입 arity      : 그 자리에서 정의한 Inductive 의 생성자 수 → destruct 분기수
  U2 생성자 인자수      : `| C1 : nat -> nat -> T` 를 destruct 하면 바인더 2개
  U3 재귀 구조          : 재귀 타입의 induction 가설 유무 판단
  U4 도메인 지식(CompCert): 실재 CompCert 타입 — 새 타입 대비 얼마나 잘하나(=암기 이득)
  U5 이름 무작위화      : 실재 타입의 **이름만** 바꿔 암기 경로 차단(구조는 동일)
  U6 반사실 정의        : 실재 타입의 **생성자 수를 바꿔** 정의. 정의를 따르나 암기를 따르나
                         ★ 가장 결정적 — 암기와 정의가 **충돌**하는 유일한 조건

사용:
    CUDA_VISIBLE_DEVICES=0 python3 scripts/probe_type_understanding.py --model <hf-name>
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


class Scorer:
    def __init__(self, name):
        print(f"모델: {name}")
        self.tok = AutoTokenizer.from_pretrained(name)
        self.model = AutoModelForCausalLM.from_pretrained(
            name, torch_dtype=torch.bfloat16).cuda().eval()

    def nll(self, prompt, target):
        """★ **총 NLL**(평균×토큰수)을 쓴다. 평균은 길이에 편향된다 — 실측:
             `[|||].` 평균 6.20 → `[|||||].` 평균 5.84 (긴 쪽이 낮음)
           뒤따르는 '|' 는 예측이 쉬워 평균을 끌어내리므로, 평균으로 비교하면
           **항상 긴 패턴을 선호**해 '정의를 무시한다'는 가짜 결론이 나온다.
           서로 다른 후보의 우도 비교는 총 로그확률이 올바르다."""
        pi = self.tok(prompt, return_tensors="pt", truncation=True, max_length=3000)["input_ids"]
        ti = self.tok(target, return_tensors="pt", add_special_tokens=False)["input_ids"]
        ids = torch.cat([pi, ti], dim=1).cuda()
        lab = ids.clone()
        lab[:, : pi.shape[1]] = -100
        with torch.no_grad():
            mean = float(self.model(ids, labels=lab).loss)
        return mean * ti.shape[1]

    def prefer(self, prompt, good, bad):
        """정답 쪽 총 NLL 이 더 낮으면 True (+ 차이). ※ 길이가 같은 후보에만 쓸 것."""
        a, b = self.nll(prompt, good), self.nll(prompt, bad)
        return a < b, a - b

    def next_prefer(self, prompt, good_tok, bad_tok):
        """★ 길이 편향 없는 비교 — **같은 프리픽스에서 다음 한 토큰**의 확률만 견준다.

        길이가 다른 후보를 통째로 비교하면 어느 쪽으로도 공정하지 않다(실측):
          · 평균 NLL → 항상 **긴** 쪽 선호 (뒤 토큰이 예측 쉬워 평균이 내려감)
          · 총 NLL   → 항상 **짧은** 쪽 선호 (토큰이 적어 합이 작음)
        단일 토큰 결정은 길이가 동일해 이 편향이 원천 차단된다.
        """
        # ★ 공백 경계 처리: 프롬프트가 공백으로 끝나면 후보의 첫 토큰이 실제 문맥과 어긋난다
        #   (BPE 는 " IH" 와 "IH" 를 다른 토큰으로 본다). 공백을 후보 쪽으로 옮긴다.
        if prompt.endswith(" "):
            prompt = prompt[:-1]
            good_tok, bad_tok = " " + good_tok.lstrip(), " " + bad_tok.lstrip()
        ids = self.tok(prompt, return_tensors="pt", truncation=True,
                       max_length=3000)["input_ids"].cuda()
        with torch.no_grad():
            logits = self.model(ids).logits[0, -1]
        lp = torch.log_softmax(logits.float(), dim=-1)
        ga = self.tok(good_tok, add_special_tokens=False)["input_ids"]
        ba = self.tok(bad_tok, add_special_tokens=False)["input_ids"]
        if not ga or not ba or ga[0] == ba[0]:
            return None, 0.0          # 첫 토큰이 같으면 이 지점에서 구분 불가 — 표본에서 제외
        g, b = float(lp[ga[0]]), float(lp[ba[0]])
        return g > b, b - g          # 양수면 정답이 더 그럴듯


# ── 합성 타입 생성기 (코퍼스에 없는 이름) ──
_SYL = ["Zor", "Quv", "Mek", "Pil", "Nax", "Tib", "Wug", "Vex", "Jom", "Kiv"]


def make_type(rnd, n_ctor, arities=None, recursive=False):
    """그 자리에서 만든 Inductive. 이름은 코퍼스에 없을 조합."""
    tname = rnd.choice(_SYL) + rnd.choice(_SYL).lower() + str(rnd.randrange(100))
    ctors = []
    ars = arities or [rnd.randrange(0, 3) for _ in range(n_ctor)]
    for i, a in enumerate(ars):
        cn = rnd.choice(_SYL) + str(i) + str(rnd.randrange(10))
        if a == 0:
            ctors.append(f"| {cn} : {tname}")
        else:
            args = " -> ".join(["nat"] * (a - 1) + [tname if recursive and i == len(ars) - 1
                                                    else "nat"])
            ctors.append(f"| {cn} : {args} -> {tname}")
    return tname, ars, f"Inductive {tname} : Type :=\n" + "\n".join(ctors) + "."


def pat(n):
    return "[" + "|" * (n - 1) + "]"


def binders(ars):
    """생성자별 인자수에 맞는 destruct 패턴 (바인더 이름 포함)."""
    g, k = [], 0
    for a in ars:
        names = []
        for _ in range(a):
            names.append(f"y{k}")
            k += 1
        g.append(" ".join(names))
    return "[" + "|".join(g) + "]"


def binom_p(k, n, p0=0.5):
    """이항검정 양측 p — '무작위(50%)와 다른가'. 표본이 작으면 큰 비율차도 우연이다."""
    from math import comb
    if n == 0:
        return 1.0
    tail = sum(comb(n, i) * p0 ** i * (1 - p0) ** (n - i)
               for i in range(n + 1)
               if abs(i - n * p0) >= abs(k - n * p0))
    return min(1.0, tail)


def report(tag, wins, tot, d):
    """★ 엄격 판정: 비율만 보지 않고 **유의성**까지 본다.
       표본 6개에서 100%가 나와도 p=0.03 이고, 12개에서 58%면 p=0.77 로 무의미하다."""
    r = wins / max(tot, 1) * 100
    p = binom_p(wins, tot)
    if p >= 0.05:
        mark, verdict = "·", "무의미(우연과 구분 안 됨)"
    elif r > 50:
        mark, verdict = "✅", "유의하게 정답 선호"
    else:
        mark, verdict = "❌", "유의하게 **오답** 선호"
    print(f"   {mark} {tag:26s} {wins:>3}/{tot:<3} = {r:>5.1f}%  p={p:.3f}  "
          f"ΔNLL {d:+.3f}  {verdict}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--n", type=int, default=40)
    args = ap.parse_args()
    rnd = random.Random(11)
    sc = Scorer(args.model)
    idx = json.load(open("data/func_defs_v3.json"))

    R = {k: [0, 0, []] for k in ("U1", "U2", "U3", "U4", "U5", "U6")}

    def rec(k, ok, d):
        R[k][0] += int(ok)
        R[k][1] += 1
        R[k][2].append(d)

    # ── U1/U2/U3: 새 타입 ──
    for _ in range(args.n):
        nc = rnd.randrange(2, 7)
        tname, ars, defn = make_type(rnd, nc)
        # ★ 두 결정 지점에서 '다음 한 토큰'만 비교(길이 편향 없음):
        #   nc-2 개 열었을 때 → 아직 '|' 가 더 필요   /   nc-1 개 열었을 때 → 이제 ']' 로 닫아야
        base = f"{defn}\n\nGoal forall (x : {tname}), True.\nProof.\nintros x.\ndestruct x as ["
        okA, dA = sc.next_prefer(base + "|" * (nc - 2), "|", "]")
        okB, dB = sc.next_prefer(base + "|" * (nc - 1), "]", "|")
        for o, dd in ((okA, dA), (okB, dB)):
            if o is not None:
                rec("U1", o, dd)
        # U2: 첫 생성자의 인자수. `[` 다음에 바인더가 와야 하나(arity>0) '|' 가 와야 하나(arity=0)
        okC, dC = sc.next_prefer(base, "y", "|") if ars[0] > 0 else sc.next_prefer(base, "|", "y")
        if okC is not None:
            rec("U2", okC, dC)
        # U3: 재귀 타입이면 induction 가설이 생긴다
        tname2, ars2, defn2 = make_type(rnd, 2, arities=[0, 1], recursive=True)
        # 재귀 생성자면 귀납가설이 붙는다 → `[| y0 ` 다음에 'IH' 가 와야(아니면 ']')
        p3 = (f"{defn2}\n\nGoal forall (x : {tname2}), True.\nProof.\ninduction x as [| y0 ")
        ok3, d3 = sc.next_prefer(p3, "IH", "]")
        if ok3 is not None:
            rec("U3", ok3, d3)

    # ── U4/U5/U6: 실재 CompCert 타입 ──
    # ★ 표본 확대: 6개로는 유의성이 안 나온다. CompCert 파일에서 생성자 2~8개인 Inductive 를 모은다.
    real = []
    for nm, slot in idx.items():
        if not isinstance(slot, dict) or len(real) >= 60:
            continue
        d = next((v for k, v in slot.items() if "ompCert" in k), None)
        if not d or ":=" not in d or "..." in d:
            continue
        if not re.search(r"\b(Inductive|Variant)\b", d.split(":=", 1)[0]):
            continue
        nc = len([x for x in d.split(":=", 1)[1].split("|") if x.strip()])
        if 3 <= nc <= 8:
            real.append((nm, slot))
    for nm, slot in real:
        defn = next((v for k, v in slot.items() if "ompCert" in k or "compcert" in k),
                    next(iter(slot.values())))
        if ":=" not in defn or "..." in defn:
            continue
        n_true = len([x for x in defn.split(":=", 1)[1].split("|") if x.strip()])
        if n_true < 2:
            continue
        n_bad = n_true + 1
        # U4 실재 타입(암기 가능)
        b4 = f"{defn}\n\nGoal forall (x : {nm}), True.\nProof.\nintros x.\ndestruct x as ["
        for o, dd in (sc.next_prefer(b4 + "|" * (n_true - 2), "|", "]"),
                      sc.next_prefer(b4 + "|" * (n_true - 1), "]", "|")):
            if o is not None:
                rec("U4", o, dd)
        # U5 이름만 무작위화(구조 동일) — 암기 경로 차단
        alias = rnd.choice(_SYL) + str(rnd.randrange(100))
        rd = re.sub(r"\b" + re.escape(nm) + r"\b", alias, defn)
        b5 = f"{rd}\n\nGoal forall (x : {alias}), True.\nProof.\nintros x.\ndestruct x as ["
        for o, dd in (sc.next_prefer(b5 + "|" * (n_true - 2), "|", "]"),
                      sc.next_prefer(b5 + "|" * (n_true - 1), "]", "|")):
            if o is not None:
                rec("U5", o, dd)
        # ── U6 반사실: 정의에서 생성자를 하나 지운다 → 정의대로면 n_true-1 이 정답 ──
        # ★ 포맷 보존: 원본이 `:= | A | B` 형태면 그대로 유지해야 한다.
        #   (전에는 join 으로 앞 '|' 가 사라지고 공백이 겹쳐 정의가 깨졌다)
        body = defn.split(":=", 1)[1].rstrip().rstrip(".")
        parts = [x.strip() for x in body.split("|") if x.strip()]
        lead = "| " if body.lstrip().startswith("|") else ""
        cut = defn.split(":=", 1)[0] + ":= " + lead + " | ".join(parts[:-1]) + "."
        # 정의대로면 n_true-1 분기 → n_true-2 개 열린 상태에서 ']' 로 닫아야 한다.
        # 암기하면 여기서 '|' 를 하나 더 연다.
        b6 = f"{cut}\n\nGoal forall (x : {nm}), True.\nProof.\nintros x.\ndestruct x as ["
        o6, d6 = sc.next_prefer(b6 + "|" * (n_true - 2), "]", "|")
        if o6 is not None:
            rec("U6", o6, d6)

    print(f"\n■ 타입 이해 vs 암기  ({args.model.split('/')[-1]})")
    print("   정답선호 비율(50%=무작위). ΔNLL 음수 = 정답을 더 그럴듯하게 봄\n")
    names = {"U1": "새 타입 분기수(추론)", "U2": "생성자 인자수(바인더)",
             "U3": "재귀→귀납가설", "U4": "실재 CompCert(암기가능)",
             "U5": "이름만 바꾼 실재타입", "U6": "★반사실(정의≠암기)"}
    for k in ("U1", "U2", "U3", "U4", "U5", "U6"):
        if R[k][1]:
            report(names[k], R[k][0], R[k][1], statistics.mean(R[k][2]))
    print("\n   해석:")
    print("     U1 높음        → 새 정의를 읽고 추론한다(암기 아님)")
    print("     U4 ≫ U1/U5     → 암기 의존. 처음 보는 타입엔 무력")
    print("     U6 높음        → 정의가 암기와 충돌할 때 **정의를 따른다**(진짜 이해)")
    print("     U6 낮음        → 정의를 무시하고 외운 답을 낸다")


if __name__ == "__main__":
    main()
