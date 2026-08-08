#!/usr/bin/env python3
"""collate 속도 프로파일 — 기능별 오버헤드 실측(성능 회귀 상시 검사).

★ 왜 필요한가: distractor 가 예제마다 `list(idx.keys())`(8만 원소)를 만들어
  학습이 **6.02 s/it** 로 2배 느려진 적이 있다(v2 는 3.0). 정적 리뷰로는 안 보였고,
  이 프로파일로 잡았다. 기능을 추가할 때마다 돌려서 회귀를 막는다.

사용: python3 scripts/profile_collate.py [--n 150]
"""
import argparse
import json
import logging
import os
import statistics
import sys
import time

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.insert(0, "src")
logging.disable(logging.CRITICAL)

BASE = dict(AUGMENT_V2="1", RERANK_PREMISES="1", INJECT_TYPES="1", INJECT_DEFS="1",
            HARD_SEQ_LEN="4096", TYPES_TOKENS="300", DEFS_TOKENS="300")
KNOBS = ["FUNC_DEFS_PATH", "CITE_TARGET", "NORMALIZE_NAMES", "NORMALIZE_RATE",
         "TYPE_FACTS", "DISTRACTORS"]
CONFS = [
    ("v2 인덱스 기준", {"FUNC_DEFS_PATH": "data/func_defs.json"}),
    ("v3 인덱스", {"FUNC_DEFS_PATH": "data/func_defs_v3.json"}),
    ("+CITE", {"FUNC_DEFS_PATH": "data/func_defs_v3.json", "CITE_TARGET": "1"}),
    ("+NORM", {"FUNC_DEFS_PATH": "data/func_defs_v3.json", "CITE_TARGET": "1",
               "NORMALIZE_NAMES": "1", "NORMALIZE_RATE": "0.5"}),
    ("+FACTS", {"FUNC_DEFS_PATH": "data/func_defs_v3.json", "CITE_TARGET": "1",
                "NORMALIZE_NAMES": "1", "NORMALIZE_RATE": "0.5", "TYPE_FACTS": "1"}),
    ("v4 전체(+DISTRACT)", {"FUNC_DEFS_PATH": "data/func_defs_v3.json", "CITE_TARGET": "1",
                            "NORMALIZE_NAMES": "1", "NORMALIZE_RATE": "0.5",
                            "TYPE_FACTS": "1", "DISTRACTORS": "2"}),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=150)
    ap.add_argument("--max-slowdown", type=float, default=1.30,
                    help="기준 대비 허용 배수(넘으면 실패)")
    args = ap.parse_args()

    import yaml
    from transformers import AutoTokenizer
    from tactic_gen.lm_example import LmExample
    from tactic_gen.tactic_data import example_collator_conf_from_yaml, example_collator_from_conf

    cc = yaml.safe_load(open(
        "models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml"))
    col = example_collator_from_conf(example_collator_conf_from_yaml(cc["example_collator"]))
    tok = AutoTokenizer.from_pretrained("deepseek-ai/deepseek-coder-1.3b-instruct")

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
                    if len(steps) >= args.n:
                        break
            if len(steps) >= args.n:
                break
        if len(steps) >= args.n:
            break

    print(f"{'설정':22s} {'예제당 ms':>10} {'배수':>7} {'토큰중앙':>9}")
    print("-" * 52)
    base = None
    worst = 1.0
    for name, extra in CONFS:
        for k in list(BASE) + KNOBS:
            os.environ.pop(k, None)
        os.environ.update(BASE)
        os.environ.update(extra)
        import tactic_gen.tactic_data as _t
        _t._FD_INDEX = None
        _t._DISTRACTOR_KEYS = None
        import tactic_gen.normalize_names as _n
        _n._IDX = None
        for e in steps[:10]:
            col.collate(tok, e)                      # 워밍
        t0 = time.time()
        lens = [len(tok(col.collate(tok, e), add_special_tokens=False)["input_ids"])
                for e in steps]
        ms = (time.time() - t0) / len(steps) * 1000
        if base is None:
            base = ms
        worst = max(worst, ms / base)
        print(f"{name:22s} {ms:>10.1f} {ms/base:>6.2f}x {statistics.median(lens):>9.0f}")
    print()
    if worst > args.max_slowdown:
        print(f"❌ 회귀: 최대 {worst:.2f}x (허용 {args.max_slowdown}x)")
        return 1
    print(f"✅ 오버헤드 최대 {worst:.2f}x (허용 {args.max_slowdown}x)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
