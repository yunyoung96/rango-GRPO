#!/usr/bin/env python3
"""★ v4 학습 데이터 동적 검증 — 학습 걸기 전 반드시 통과해야 하는 불변식들.

정적으로 '맞아 보인다'로 40시간을 걸 수 없다. 실제 예제 수백 개를 **실제 collate 경로**로
돌려 검사한다. 이 검사가 실제로 잡아낸 버그(전부 정적으로는 안 보였다):

  1. _LAST_INJECTED 가 조기반환 경로에서 초기화 안 돼 **이전 예제 이름이 잔류**  (400중 20건)
  2. 생성한 새 이름이 goal 의 기존 변수와 **충돌** (goal 에 이미 `f, f0: float` 이 있는데 f0 생성)
  3. 순서 오류 — 정규화된 goal 로 정의를 조회해 **섹션이 통째로 사라짐**
  4. 섹션 헤더/에러문장 오염 (`[ERROR]`→`[T7]`, `pattern`→`f11`)
  5. 인용이 **잘못된 collator** 에 배선돼 400/400 예제에서 미발동
  6. distractor 가 예제마다 8만 키 리스트를 생성해 학습이 2배 느려짐

사용:
    python3 scripts/verify_v4_data.py [--n 400]
"""
import argparse
import collections
import json
import logging
import os
import re
import statistics
import sys

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
# v4 최종 구성 (ERROR_COND 는 제외 — 학습 코퍼스에 .v 가 없어 진짜 에러를 못 만든다)
os.environ.update(dict(
    AUGMENT_V2="1", RERANK_PREMISES="1", INJECT_TYPES="1", INJECT_DEFS="1",
    HARD_SEQ_LEN="4096", TYPES_TOKENS="300", DEFS_TOKENS="300",
    FUNC_DEFS_PATH="data/func_defs_v3.json",
    NORMALIZE_NAMES="1", NORMALIZE_RATE="0.5",
    TYPE_FACTS="1", DISTRACTORS="2",
))
sys.path.insert(0, "src")
logging.disable(logging.CRITICAL)

import yaml  # noqa: E402
from transformers import AutoTokenizer  # noqa: E402
from tactic_gen.lm_example import LmExample  # noqa: E402
import tactic_gen.tactic_data as td  # noqa: E402
from tactic_gen.tactic_data import (  # noqa: E402
    example_collator_conf_from_yaml, example_collator_from_conf, NEWLINE_RESPONSE_TEMPLATE)
from tactic_gen.data_collator_compat import DataCollatorForCompletionOnlyLM  # noqa: E402
from tactic_gen.cite_target import strip_cite  # noqa: E402
from tactic_gen.normalize_names import build_mapping, should_normalize, apply_mapping  # noqa: E402

HEADERS = ["[PREMISES]", "[PROOFS]", "[STATE]", "[SCRIPT]", "[TACTIC]"]


def load_examples(n):
    steps = []
    src = "data/grpo_rollouts/goldsft_bs2.jsonl"
    for line in open(src):
        g = json.loads(line)
        for a in g["attempts"]:
            if a["reward"] < 1.0:
                continue
            for st in a["steps"]:
                if st.get("example") and st.get("tactic"):
                    e = LmExample.from_json(st["example"])
                    e.next_steps = [st["tactic"]]
                    steps.append(e)
                    if len(steps) >= n:
                        return steps
    return steps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=400)
    args = ap.parse_args()

    cc = yaml.safe_load(open(
        "models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml"))
    col = example_collator_from_conf(example_collator_conf_from_yaml(cc["example_collator"]))
    tok = AutoTokenizer.from_pretrained("deepseek-ai/deepseek-coder-1.3b-instruct")
    tok.pad_token = tok.eos_token
    steps = load_examples(args.n)

    fail = collections.Counter()
    ex = collections.defaultdict(list)
    lens = []
    n_norm = n_facts = n_cite = 0

    # ── 검사 0: 라벨 마스킹 (loss 가 정답에만 걸리나) ──
    dc = DataCollatorForCompletionOnlyLM(NEWLINE_RESPONSE_TEMPLATE, tokenizer=tok)
    p0 = col.collate(tok, steps[0])
    enc = tok(p0, truncation=True, max_length=4096)
    batch = dc([{k: enc[k] for k in ("input_ids", "attention_mask")}])
    lab = batch["labels"][0]
    n_lab, n_tot = int((lab != -100).sum()), int(lab.numel())
    tgt_txt = tok.decode([t for t in lab.tolist() if t != -100])
    if n_lab == 0:
        fail["라벨 전부 마스킹"] += 1
    if n_lab > n_tot * 0.3:
        fail["라벨 과다(프롬프트까지 학습)"] += 1
    if "[USES]" in tgt_txt:
        fail["라벨에 인용 잔존"] += 1
    label_info = f"{n_lab}/{n_tot} 토큰, {tgt_txt[:56]!r}"

    for i, e in enumerate(steps):
        p = col.collate(tok, e)
        lens.append(len(tok(p, add_special_tokens=False)["input_ids"]))
        inj = dict(td._LAST_INJECTED)
        key = (f"{getattr(e, 'file_name', '')}:"
               f"{getattr(e, 'proof_idx', '')}:{getattr(e, 'step_idx', '')}")
        tail = p.split("[TACTIC]")[-1]

        # ① 섹션 헤더 보존
        for h in HEADERS:
            if h not in p:
                fail[f"헤더 없음 {h}"] += 1

        # ② CITE_TARGET 을 뺐으므로 인용이 **없어야** 정상
        #    (타깃의 57%를 차지해 gradient 를 뺏고 v2 와 loss 비교를 막았다)
        if "[USES]" in p:
            fail["인용이 남아있음(CITE 제거했는데)"] += 1

        # ③ TYPE-FACTS 형식
        if "[TYPE-FACTS]" in p:
            n_facts += 1
            m = re.search(r"\[TYPE-FACTS\]\n([^\n]*)", p)
            if m and not re.search(r"\d+ ctors, arities \[", m.group(1)):
                fail["FACTS 형식 이상"] += 1
                ex["FACTS 형식 이상"].append(m.group(1)[:44])

        # ④ 정규화: 새 이름이 goal 에 있으면 섹션에도 있어야(조회 가능해야)
        mp = build_mapping(inj, key, avoid_text=p) if should_normalize(key) else {}
        if mp:
            n_norm += 1
            if len(set(mp.values())) != len(mp):
                fail["정규화 비단사(충돌)"] += 1
            inv = {v: k for k, v in mp.items()}
            probe = "X " + " ".join(mp)
            if apply_mapping(apply_mapping(probe, mp), inv) != probe:
                fail["역치환 불일치"] += 1
            new = set(mp.values())
            a = [p.find(x) for x in ("[TYPES]", "[DEFINITIONS]") if p.find(x) >= 0]
            if a:
                sec = p[min(a):p.find("[TACTIC]")]
                state = p[p.find("[STATE]"):p.find("[SCRIPT]")]
                gn = set(re.findall(r"[A-Za-z_][\w']*", state)) & new
                sn = set(re.findall(r"[A-Za-z_][\w']*", sec)) & new
                if gn and not (gn & sn):
                    fail["정규화 이름이 섹션에 없음"] += 1
                    ex["정규화 이름이 섹션에 없음"].append(sorted(gn)[:3])

        # ⑥ 타깃이 비면 안 됨
        if not tail.strip():
            fail["타깃 비어있음"] += 1

    print(f"■ v4 데이터 검증 (예제 {len(steps)}개)")
    print(f"   라벨 범위 : {label_info}")
    print(f"   정규화 {n_norm} · TYPE-FACTS {n_facts}")
    print(f"   토큰: 중앙 {statistics.median(lens):.0f}  최대 {max(lens)}  "
          f"4096초과 {sum(1 for x in lens if x > 4096)}건")
    if not fail:
        print("\n   ✅ 모든 불변식 통과")
        return 0
    print("\n   ❌ 위반")
    for k, v in fail.most_common():
        print(f"      {k:28s} {v:>4}건  {ex[k][:2]}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
