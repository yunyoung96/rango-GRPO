#!/usr/bin/env python3
"""★ 검색 3단이 서로 도움인지 방해인지 — 실제 프롬프트 포함률로 판정한다.

## 배경

검색이 3단으로 겹쳐 있다.

  ① SparseClient.get_premise_scores   tfidf → structural 재랭킹 → 상위 100개
  ② rerank_premises (RERANK_PREMISES=1)  점수 = (원순위 prior) + 30×타입매칭
  ③ allocate_and_fmt                  예산까지 담기

②는 ①이 약한 BM25 이던 시절에 만든 보정이다. **①이 이미 구조 신호를 쓰므로 정보가
겹칠 수 있다** — 계층 랭커에서 "신호를 겹쳐 쓰면 오히려 나빠진다"를 이미 겪었다.

## 2×2 비교

  ①  structural  vs  tfidf(원래 rango)
  ②  RERANK on   vs  off

판정 기준은 **gold 가 프롬프트에 실제로 들어가는 비율** (2048 왼쪽절단까지 반영).

## 동적 디버깅

  · 실험 전: 설정이 실제로 먹었는지 확인(환경변수만 바꾸고 코드가 안 읽으면 조용히 무시된다)
  · 실험 중: 프롬프트에 [PREMISES] 가 있는지, premise 개수가 0 이 아닌지

사용: python3 scripts/rerank_ablation.py [n] [train|val|test]
"""
import collections
import copy
import os
import sys
import time

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("AUGMENT_V2", "1")
os.environ.setdefault("INJECT_TYPES", "1")
os.environ.setdefault("INJECT_DEFS", "1")
# ★ HARD_SEQ_LEN 은 rango_defaults 기본값(3072)을 따른다 — 여기서 못 박지 않는다
os.environ.setdefault("TYPES_TOKENS", "300")
os.environ.setdefault("DEFS_TOKENS", "300")
os.environ.setdefault("FUNC_DEFS_PATH", "data/func_defs_v3.json")
os.environ.setdefault("STRIP_TARGET_NL", "1")
sys.path.insert(0, "src")
import rango_defaults as _D
import logging  # noqa: E402

logging.disable(logging.CRITICAL)
import yaml  # noqa: E402
from transformers import AutoTokenizer  # noqa: E402
from data_management.splits import Split  # noqa: E402
from tactic_gen.tactic_data import (TacticDataConf, LmDataset,  # noqa: E402
                                    example_collator_from_conf)
from tactic_gen.gold_lemma import gold_lemmas  # noqa: E402
from tactic_gen.search_query import local_names  # noqa: E402
from tactic_gen.tier_rank import declname  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 600
SPLIT = (sys.argv[2] if len(sys.argv) > 2 else "train").upper()
HARD = _D.num("HARD_SEQ_LEN")

cc = yaml.safe_load(open("all_log/ft_qwen3b_v8_conf.yaml"))
tok = AutoTokenizer.from_pretrained(cc["model_name"])
tok.truncation_side = "left"

# ── 실험 전 동적 확인: 환경변수가 실제로 코드에 먹는가 ─────────────────
print("■ 실험 전 확인")
import tactic_gen.tactic_data as TD  # noqa: E402
os.environ["RERANK_PREMISES"] = "1"
_probe_on = TD.rerank_premises.__doc__ is not None
from premise_selection import premise_client as PC  # noqa: E402
import inspect  # noqa: E402
_src = inspect.getsource(PC.SparseClient.get_premise_scores)
print(f"   [{'✓' if 'retrieval_mode()' in _src else '✗'}] SparseClient 가 retrieval_mode() 를 쓴다")
print(f"   [{'✓' if 'PREMISE_PACK_SKIP' in inspect.getsource(TD.whole_number_allocate) else '✗'}]"
      f" 담기가 skip 방식이다")
print(f"   [{'✓' if _probe_on else '✗'}] rerank_premises 존재")

CASES = [
    ("① structural + ② on  (현재)", "structural", "1"),
    ("① structural + ② off", "structural", "0"),
    ("① tfidf + ② on  (기존 rango)", "tfidf", "1"),
    ("① tfidf + ② off", "tfidf", "0"),
]
res = {}
for label, mode, rr in CASES:
    os.environ["RETRIEVAL_MODE"] = mode
    os.environ["RERANK_PREMISES"] = rr
    conf = TacticDataConf.from_yaml(copy.deepcopy(cc["tactic_data"]))
    ds = LmDataset.from_conf(conf, getattr(Split, SPLIT), 10 ** 9)
    coll = example_collator_from_conf(conf.collator_conf)
    gold_ok = ngold = n = 0
    nprem = []
    bad = collections.Counter()
    t0 = time.time()
    for i in range(N * 4):
        if n >= N:
            break
        try:
            e = ds.raw_example(i)
        except Exception:
            continue
        try:
            s = coll.collate(tok, e)
        except Exception as ex:
            bad[f"collate 예외 {type(ex).__name__}"] += 1
            continue
        ids = tok(s, add_special_tokens=False)["input_ids"]
        final = tok.decode(ids[-HARD:], skip_special_tokens=True) if len(ids) > HARD else s
        n += 1
        # 실험 중 불변식
        if "[PREMISES]" not in final:
            bad["프롬프트에 [PREMISES] 없음"] += 1
        seg = final.split("[PREMISES]", 1)[1] if "[PREMISES]" in final else ""
        for sep in ("[PROOFS]", "[STATE]", "[SCRIPT]"):
            if sep in seg:
                seg = seg.split(sep, 1)[0]
        lines = [x for x in seg.split("\n") if x.strip()]
        nprem.append(len(lines))
        if not lines:
            bad["premise 0개"] += 1
        st = getattr(e, "proof_state", "") or ""
        tac = (e.next_steps[0] if getattr(e, "next_steps", None) else "").strip()
        golds = gold_lemmas(tac, local_names(st))
        if not golds:
            continue
        prem_all = [p if isinstance(p, str) else str(p)
                    for p in (getattr(e, "premises", None) or [])]
        if not any((declname(t) or "") in golds for t in prem_all):
            continue
        ngold += 1
        gset = {declname(x) for x in lines if declname(x)}
        if all(g in gset for g in golds):
            gold_ok += 1
    nprem.sort()
    res[label] = dict(n=n, ngold=ngold, gold=gold_ok / max(ngold, 1) * 100,
                      med=nprem[len(nprem) // 2] if nprem else 0,
                      avg=sum(nprem) / max(len(nprem), 1), bad=dict(bad),
                      sec=time.time() - t0)
    r = res[label]
    print(f"   {label:32s} gold {r['gold']:5.1f}%  premise 중앙 {r['med']:3d}  "
          f"({r['sec']:.0f}s)", flush=True)

print(f"\n■ {SPLIT} — 검색 3단 조합 비교 (각 {N}건 · 2048 왼쪽절단 반영)")
print(f"\n   {'조합':34s} {'★gold 프롬프트 포함':>18s} {'premise 중앙':>13s} {'평균':>7s}")
for label, _, _ in CASES:
    r = res[label]
    print(f"   {label:34s} {r['gold']:17.1f}% {r['med']:13d} {r['avg']:7.1f}")
print(f"\n   gold 판정 대상 {res[CASES[0][0]]['ngold']}건")
anyb = {k: v for label, _, _ in CASES for k, v in res[label]["bad"].items()}
if anyb:
    print(f"\n   ■ 이상 징후")
    for k, v in anyb.items():
        print(f"     {k}: {v}")
else:
    print(f"\n   ✓ 이상 징후 없음")
