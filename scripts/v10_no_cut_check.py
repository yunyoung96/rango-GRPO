#!/usr/bin/env python3
"""v10 이 정말 cut(assert)을 **안 쓰는가** — 학습 타깃을 직접 본다. GPU 불필요.

코드를 읽어 "게이트가 막혔다" 로 끝내면 안 된다. cut 경로가 넷이고(collate ①-b,
_substep_plan, _hopeless, _skip_norm) 하나라도 새면 학습 데이터에 조용히 섞인다.
그래서 **학습이 실제로 쓰는 타깃 문자열**에 `assert (…) as H_asrt` 가 나오는지 센다.

v10 ON / OFF 를 같은 인덱스로 돌려 **대조**한다 — OFF 에서 나와야 검사가 유효하다
(둘 다 0이면 "cut 이 원래 안 나오는 표본" 이라 아무것도 증명 못 한다).

사용: NC_N=400 python3 scripts/v10_no_cut_check.py
"""
import collections, os, re, sys, yaml, logging
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")
os.environ["CUDA_VISIBLE_DEVICES"] = ""
sys.path.insert(0, "src")
logging.disable(logging.CRITICAL)
from tactic_gen.tactic_data import LmDataset, TacticDataConf
from tactic_gen import v10_inject as V10
from data_management.splits import Split

N = int(os.environ.get("NC_N", "400"))
CONF = yaml.safe_load(open("all_log/ft_qwen3b_v10_conf.yaml"))
td = TacticDataConf.from_yaml(CONF["tactic_data"])
ds = LmDataset.from_conf(td, Split.TRAIN)
tok, col = ds.tokenizer, ds.example_collator
# ★ 두 가지를 **갈라야** 한다:
#     생성 cut  `assert (P) as H_asrt0. { exact L }`  ← v10 이 없앤 것
#     gold 자체 `assert (IN : In y …) by (…).`        ← 원래 증명에 있던 것. 정상이다
#   `assert` 로만 세면 gold 것까지 잡혀 "샌다" 는 오판이 난다(실제로 당했다).
CUT  = re.compile(r"H_asrt")
ASRT = re.compile(r"\bassert\s*\(")
step = max(1, len(ds) // N)
idxs = list(range(0, min(len(ds), N * step), step))
print(f"■ 학습 타깃에 assert 가 나오나 · TRAIN {len(idxs)} 예제", flush=True)

res = {}
for label, on in (("v10 ON (현행)", True), ("v10 OFF (v9 재현)", False)):
    V10.ENABLED = on
    S = collections.Counter()
    ex_hit = []
    for c, i in enumerate(idxs):
        try:
            ex = ds.resolved_example(i)
            full = col.collate(tok, ex)
        except Exception:
            S["오류"] += 1
            continue
        tgt = full.rsplit("[TACTIC]", 1)[-1] if "[TACTIC]" in full else ""
        S["예제"] += 1
        if CUT.search(tgt):
            S["생성 cut"] += 1
            if len(ex_hit) < 3:
                ex_hit.append((i, " ".join(tgt.split())[:130]))
        elif ASRT.search(tgt):
            S["gold 자체 assert"] += 1
        if (c + 1) % 100 == 0:
            print(f"   {label} … {c+1}/{len(idxs)}", flush=True)
    res[label] = (S, ex_hit)
V10.ENABLED = True                       # 원상복구

print()
for label, (S, ex_hit) in res.items():
    n = max(S["예제"], 1)
    print(f"  {label:20s} 예제 {n}"
          f" · ★생성 cut {S['생성 cut']:3d} ({S['생성 cut']/n*100:5.2f}%)"
          f" · gold 자체 assert {S['gold 자체 assert']:3d} ({S['gold 자체 assert']/n*100:5.2f}%)")
    for i, t in ex_hit:
        print(f"       [생성 cut] idx {i}: {t}")

on = res["v10 ON (현행)"][0]["생성 cut"]
off = res["v10 OFF (v9 재현)"][0]["생성 cut"]
print()
if on == 0 and off > 0:
    print(f"  ✅ v10 은 cut 을 안 쓴다 — 생성 cut ON 0건 vs OFF {off}건 (대조가 성립한다)")
    print("     (gold 증명이 원래 쓰던 assert 는 양쪽에 그대로 남는다 — 정상이다)")
elif on == 0 and off == 0:
    print("  ⚠ 둘 다 0 — 표본에 cut 대상이 없다. 검사가 아무것도 증명하지 못한다. N 을 키워라")
else:
    print(f"  ❌ v10 ON 에서 assert 가 {on}건 나왔다 — cut 경로가 샌다")
