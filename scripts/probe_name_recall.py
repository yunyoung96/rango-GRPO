#!/usr/bin/env python3
"""★ **부류별 사전학습 회상률** — notation·Ltac 이름도 익명화할 값어치가 있나.

## 왜 이걸 재나

v8 의 이름 익명화(`Int.bits_not` → `L3`)는 근거가 있었다: SFT 안 한 Qwen3B 가
실재 CompCert 이름을 가짜보다 **65.2%** 로 선호했다 = 사전학습 오염이 실재한다.
익명화는 그 지름길을 막아 **프롬프트를 읽게** 만든다.

그럼 `[LTAC]`·`[NOTATION]` 은? 여기 이름은 **프로젝트 전용**이라 사전학습에
없을 가능성이 크다. 없다면 막을 지름길도 없고, 익명화는 "뜻 있는 이름" 이라는
정당한 신호만 잃는 순손실이다. **재서 정한다.**

## 방법 (생성 없이 NLL — 2지선다)

가짜는 `_` 조각을 섞어 만든다 — 토큰 구성이 같아 길이 편향이 없다.
    order_tac → tac_order      isequiv_adjointify → adjointify_isequiv

    (* File: <프로젝트 경로> *)
    <선언 키워드> ▁<이름>

실명 NLL < 가짜 NLL 이면 1승. 50% = 우연(=회상 없음). 65% 근처면 회상 있음.

사용: CUDA_VISIBLE_DEVICES=0 python3 scripts/probe_name_recall.py [부류당 표본]
"""
import json
import os
import random
import re
import sqlite3
import sys

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.insert(0, "src")

import torch  # noqa: E402
from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 250
MODEL = os.environ.get("PROBE_MODEL", "Qwen/Qwen2.5-Coder-3B-Instruct")
DB = "raw-data/coq-dataset/sentences.db"


def shuffle_name(nm: str, rng) -> str:
    parts = nm.split("_")
    if len(parts) < 2:
        return None
    for _ in range(8):
        p = parts[:]
        rng.shuffle(p)
        cand = "_".join(p)
        if cand != nm:
            return cand
    return None


def collect(rng):
    c = sqlite3.connect(DB)
    out = {}
    # ① 프로젝트 Lemma — 기준선(65.2% 가 나온 부류)
    rows = c.execute(
        "select text,file_path from sentence where sentence_type like '%LEMMA%' "
        "and file_path like '%/repos/%' limit 120000").fetchall()
    lem = []
    for t, f in rows:
        m = re.match(r"\s*(?:Lemma|Theorem)\s+([A-Za-z_][\w']*)", t or "")
        if m and "_" in m.group(1):
            lem.append((m.group(1), f, "Lemma"))
    out["프로젝트 Lemma"] = lem
    # ② 프로젝트 Ltac
    rows = c.execute(
        "select text,file_path from sentence where sentence_type like '%TACTIC%' "
        "and file_path like '%/repos/%'").fetchall()
    lt = []
    for t, f in rows:
        m = re.match(r"\s*(?:Ltac|Ltac2)\s+([A-Za-z_][\w']*)", t or "")
        if m and "_" in m.group(1):
            lt.append((m.group(1), f, "Ltac"))
    out["프로젝트 Ltac"] = lt
    # ③ notation 이 드러내는 이름
    try:
        NI = json.load(open("data/notation_index.json"))
    except Exception:
        NI = {}
    nt = []
    for proj, e in NI.items():
        for _an, names, _text in e.get("n", ()):
            for nm in names[:1]:
                if "_" in nm:
                    nt.append((nm, f"/repos/{proj}/", "Definition"))
    out["notation 이 가린 이름"] = nt
    # ④ stdlib Lemma — 대조군(가장 잘 알 것)
    rows = c.execute(
        "select text,file_path from sentence where sentence_type like '%LEMMA%' "
        "and file_path like '%lib/coq/theories%'").fetchall()
    sl = []
    for t, f in rows:
        m = re.match(r"\s*(?:Lemma|Theorem)\s+([A-Za-z_][\w']*)", t or "")
        if m and "_" in m.group(1):
            sl.append((m.group(1), f, "Lemma"))
    out["stdlib Lemma (대조)"] = sl
    return out


@torch.no_grad()
def nll(model, tok, prefix: str, name: str) -> float:
    pi = tok(prefix, add_special_tokens=False)["input_ids"]
    ni = tok(name, add_special_tokens=False)["input_ids"]
    ids = torch.tensor([pi + ni], device=model.device)
    logits = model(ids).logits[0].float().log_softmax(-1)
    tgt = ids[0, len(pi):]
    lp = logits[len(pi) - 1:-1].gather(1, tgt[:, None]).sum().item()
    return -lp / max(len(ni), 1)


def main():
    rng = random.Random(3)
    pools = collect(rng)
    print(f"■ 모델 {MODEL}", flush=True)
    tok = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL, torch_dtype=torch.bfloat16, device_map="cuda:0").eval()
    print(f"   후보 풀: " + " · ".join(f"{k}={len(v):,}" for k, v in pools.items()),
          flush=True)
    print()
    for cls, pool in pools.items():
        rng.shuffle(pool)
        win = tie = tot = 0
        seen = set()
        for nm, fp, kw in pool:
            if tot >= N:
                break
            if nm in seen:
                continue
            fake = shuffle_name(nm, rng)
            if not fake:
                continue
            seen.add(nm)
            # ★ **맥락을 부류마다 같게 한다.** 1차 측정에서 notation 부류만 파일명
            #   없이 프로젝트 경로만 줬는데, 그 자체로 회상이 낮아진다(교란).
            #   전부 **프로젝트 이름만** 주는 형태로 통일한다.
            m_ = re.search(r"/repos/([^/]+)/", fp or "")
            short = m_.group(1) if m_ else "coq"
            pre = f"(* Project: {short} *)\n{kw} "
            a, b = nll(model, tok, pre, nm), nll(model, tok, pre, fake)
            tot += 1
            if abs(a - b) < 1e-6:
                tie += 1
            elif a < b:
                win += 1
        r = win / max(tot, 1) * 100
        bar = "█" * int(r / 2)
        print(f"   {cls:22s} 실명 선호 **{r:5.1f}%**  ({win}/{tot}, 무승부 {tie})  {bar}",
              flush=True)
    print("\n   50% = 우연(회상 없음) · 65% 근처 = 사전학습 회상 있음")


if __name__ == "__main__":
    main()
