#!/usr/bin/env python3
"""★ 익명화된 문맥에서 **lemma 사용에 배울 만한 패턴이 있나** — 정성 평가용 덤프.

정답이 `apply L7` 처럼 **익명 premise** 를 부르는 예제를 모아,
    goal 결론  ·  그 L# 의 진술  ·  gold tactic  ·  L# 의 순위
를 나란히 찍는다. TRAIN 과 TEST 를 같은 형식으로 뽑아 **패턴이 같은지** 눈으로 본다.

정량 보조: premise 진술의 **형태**와 tactic 의 짝이 규칙적인가
    결론이 등식(`a = b`)      → rewrite 를 쓰나
    결론이 goal 의 head 와 일치 → apply/exact 를 쓰나

사용: PYTHONPATH=src python3 scripts/dump_anon_pattern.py [SPLIT] [표본] [덤프개수]
"""
import collections
import copy
import json
import logging
import os
import random
import re
import sys
import time

sys.path.insert(0, "src")
sys.path.insert(0, "scripts")
logging.disable(logging.CRITICAL)
from _env_from_v9 import apply_v9_env  # noqa: E402
apply_v9_env(verbose=False)
os.environ.setdefault("CACHE_MAX_PAGE", "0")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")

SPLIT = (sys.argv[1] if len(sys.argv) > 1 else "TRAIN").upper()
N = int(sys.argv[2]) if len(sys.argv) > 2 else 1500
DUMP = int(sys.argv[3]) if len(sys.argv) > 3 else 10
if SPLIT == "TEST":                    # 평가에는 cut 계획이 없다 — 드롭도 없다
    os.environ["CUT_DROP_HOPELESS"] = "0"
    os.environ["DROP_HALLUC"] = "0"

import yaml  # noqa: E402
from data_management.splits import Split  # noqa: E402
from tactic_gen.tactic_data import (TacticDataConf, LmDataset,  # noqa: E402
                                    example_collator_from_conf, get_tokenizer,
                                    _strip_coq_comments, last_train_mapping)

cc = yaml.safe_load(open("all_log/ft_qwen3b_v9_conf.yaml"))
_td = copy.deepcopy(cc["tactic_data"])
_td["cache_loc"] = os.environ.get("VERIFY_CACHE", f"/tmp/anonpat-{SPLIT}")
conf = TacticDataConf.from_yaml(_td)
tok = get_tokenizer(cc["model_name"])
sp = getattr(Split, SPLIT)
ds = LmDataset.from_conf(conf, sp, None)
coll = example_collator_from_conf(conf.collator_conf)
TOTAL = ds.shuffled_idx.split_length(sp)
_DECL = re.compile(r"(?:Lemma|Theorem|Definition|Fixpoint|Corollary|Fact|Axiom|"
                   r"Proposition|Instance|Notation|Remark|Property)\s+([TfCLGK]\d+)\b")

PROJ = os.environ.get("PROJ_FILTER", "")     # 예: AbsInt-CompCert
st = collections.Counter()
out = []
random.seed(23)
tried = 0
t0 = time.time()
while st["예제"] < N and tried < N * 40 and len(out) < DUMP * 3:
    i = random.randrange(TOTAL)
    tried += 1
    try:
        ex = ds.resolved_example(i)
        full = coll.collate(tok, ex)
        m = last_train_mapping()
    except Exception:
        continue
    if "[TACTIC]" not in full:
        continue
    if PROJ and PROJ not in (getattr(ex, "file_name", "") or ""):
        continue
    st["예제"] += 1
    anon = set(m.values())
    prompt, target = full.rsplit("[TACTIC]", 1)
    tgt = _strip_coq_comments(target).strip()
    hits = [w for w in re.findall(r"(?<![\w'])([TfCLGK]\d+)(?![\w'])", tgt) if w in anon]
    if not hits:
        continue
    st["익명 참조를 쓰는 예제"] += 1
    # 프롬프트에서 그 L# 의 선언 줄을 찾는다
    pm = re.search(r"\[PREMISES\]\n(.*?)(?=\n\[[A-Z]+\]|\Z)", prompt, re.S)
    plines = [l for l in (pm.group(1).split("\n") if pm else []) if l.strip()]
    decl, rank = None, None
    for j, l in enumerate(plines):
        d = _DECL.search(l)
        if d and d.group(1) == hits[0]:
            decl, rank = l.strip(), j + 1
            break
    sm = re.search(r"\[STATE\]\n(.*?)(?=\n\[[A-Z]+\]|\Z)", prompt, re.S)
    state = (sm.group(1).strip() if sm else "")
    concl = state.split("\n\n")[-1].strip() if "\n\n" in state else state
    head = re.match(r"^\s*([A-Za-z_][\w']*)", concl)
    # 정량: premise 결론이 등식인가 · tactic 은 무엇인가
    tac0 = (re.match(r"^\s*([A-Za-z_][\w']*)", tgt) or [None]).group(1) if tgt else None
    if decl:
        body = decl.split(":", 1)[1] if ":" in decl else decl
        is_eq = bool(re.search(r"(?<![<>=!])=(?![=>])", body.split("->")[-1]))
        st[f"  {'등식' if is_eq else '비등식'}·{tac0}"] += 1
    out.append({"idx": i, "tok": hits[0], "rank": rank, "decl": decl,
                "concl": concl[:300], "tac": tgt[:160],
                "file": getattr(ex, "file_name", "")})
    if st["예제"] % 300 == 0:
        print(f"   … {st['예제']}/{N} · 수집 {len(out)} ({time.time()-t0:.0f}s)", flush=True)

print(f"\n■ {SPLIT}{('/' + PROJ) if PROJ else ''} · 예제 {st['예제']} · 익명 참조 예제 {st['익명 참조를 쓰는 예제']} "
      f"({st['익명 참조를 쓰는 예제']/max(st['예제'],1)*100:.1f}%)\n")
for k in sorted(st):
    if k.startswith("  "):
        print(f"   {k:26s} {st[k]}")
print()
for c in out[:DUMP]:
    print("─" * 92)
    print(f"[{SPLIT} idx={c['idx']}]  {c['file'][:70]}")
    print(f"  goal 결론 : {c['concl'][:180]}")
    print(f"  참조      : {c['tok']}  (premise 순위 {c['rank']})")
    print(f"  그 선언   : {(c['decl'] or '(프롬프트에서 못 찾음)')[:180]}")
    print(f"  gold      : {c['tac']}")
json.dump(out, open(f"/tmp/anonpat_{SPLIT}{('_'+PROJ) if PROJ else ''}.json", "w"), ensure_ascii=False)
print(f"\n→ 저장 {len(out)}건")
