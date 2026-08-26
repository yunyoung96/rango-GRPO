#!/usr/bin/env python3
"""v10 사전점검 — 학습을 돌리기 전에 **분기가 제대로 갈리는지** 본다. GPU 불필요.

  (1) 외부 참조 없음 / (2-a) gold 이미 보임 / (2-b) gold 끼워 넣음

그리고 (2-b) 예제에서 **정말로 gold 가 프롬프트에 들어갔는지**, v9 였다면 무엇이
됐을지(assert 로 바뀌었을지)를 같이 낸다.

사용: V10_N=200 python3 scripts/v10_dryrun.py [conf.yaml]
"""
import os, re, sys, json, yaml, logging, collections
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")
os.environ["CUDA_VISIBLE_DEVICES"] = ""
sys.path.insert(0, "src")
logging.disable(logging.CRITICAL)
from pathlib import Path
import rango_defaults as _D
from tactic_gen.tactic_data import (LmDataset, TacticDataConf, get_tokenizer,
                                    example_collator_from_conf, example_collator_conf_from_yaml)
from tactic_gen import v10_inject as V10
NAMED = V10.NAMED
LOCAL = V10._LOCAL

CONF = yaml.safe_load(open(sys.argv[1] if len(sys.argv) > 1 else "all_log/ft_qwen3b_v10_conf.yaml"))
N = int(os.environ.get("V10_N", "200"))
td = TacticDataConf.from_yaml(CONF["tactic_data"])
tok = get_tokenizer(td.model_name)
from data_management.splits import Split
ds = LmDataset.from_conf(td, Split.TRAIN)
tok = ds.tokenizer
# 설정은 `tactic_gen.v10_inject` 상단의 **파이썬 변수**가 단일 출처다(env 아님).
print(f"■ v10 사전점검 · ENABLED={V10.ENABLED} MAX_INJECT={V10.MAX_INJECT or '무제한'} "
      f"REQUIRE_ALL={V10.REQUIRE_ALL} DB_FALLBACK={V10.DB_FALLBACK} · 예제 {N}개", flush=True)

seen = collections.Counter()
bad, good = [], []
step = max(1, len(ds) // N)
for i in range(0, min(len(ds), N * step), step):
    try:
        ex = ds.resolved_example(i)
        before = dict(V10.STATS)
        full = ds.example_collator.collate(tok, ex)
    except Exception as e:
        seen["오류"] += 1
        continue
    after = V10.STATS
    br = None
    for k in ("(1) 외부참조 없음", "(2-a) gold 이미 보임", "(2-b) gold 끼워 넣음",
              "(2-b) 실패(포기)", "계획 없음"):
        if after[k] > before.get(k, 0):
            br = k; break
    seen[br or "?"] += 1
    if br == "(2-b) gold 끼워 넣음":
        # ★ 검증은 **정규화 후** 이름으로 해야 한다. NORMALIZE_NAMES 가 프롬프트와 정답에
        #   같은 매핑을 걸어 `map_expand` → `_L3` 같은 익명이름이 된다. 원래 이름으로
        #   찾으면 항상 실패한다(실측: 그래서 5/11 가 "누락"으로 잘못 잡혔다).
        #   학습이 실제로 요구하는 것은 "정답이 쓰는 이름이 프롬프트에 있는가" 다.
        prompt, target = full.rsplit("[TACTIC]", 1)
        try:
            ids = tok(full, add_special_tokens=False)["input_ids"]
            vis = tok.decode(ids[max(0, len(ids) - td.hard_seq_len):], skip_special_tokens=True)
            vp = vis.rsplit("[TACTIC]", 1)[0] if "[TACTIC]" in vis else vis
        except Exception:
            vp = prompt
        tn = [n for n in dict.fromkeys(m.group(1) for m in NAMED.finditer(target))
              if len(n) > 2 and not LOCAL.match(n)]
        seen_ = lambda n: bool(re.search(r"(?<![\w'])" + re.escape(n) + r"(?![\w'])", vp))
        ok = [n for n in tn if seen_(n)]
        # ★ v10 이 **책임지는** 것은 자기가 공급한 lemma 뿐이다.
        #   정답은 정의·생성자·필드(`fn` 범주)도 부르는데 그것들은 선언문이 명제가
        #   아니라 주입 대상이 아니다(README §6.3) — `DROP_HALLUC` 이 그 몫을 거른다.
        #   두 지표를 갈라 낸다: 안 가르면 범위 밖 이름 때문에 v10 이 실패한 것처럼 보인다.
        lems = [nm for nm, _ in (V10.plan_lemmas(ex) or [])]
        supplied = [n for n in tn if n.split(".")[-1] in {l.split(".")[-1] for l in lems}]
        oos = [n for n in tn if n not in supplied]
        rec = dict(i=i, target_names=tn, visible=ok, lems=lems,
                   supplied=supplied, oos=oos,
                   sup_ok=[n for n in supplied if seen_(n)],
                   target=target.strip()[:200])
        (good if len(rec["sup_ok"]) == len(supplied) else bad).append(rec)
    if sum(seen.values()) % 50 == 0:
        print(f"   … {sum(seen.values())}", flush=True)

n = max(sum(seen.values()), 1)
print("\n■ 분기 분포")
for k, v in seen.most_common():
    print(f"   {k:20s} {v:5d}  {v/n*100:5.1f}%")
tot = len(good) + len(bad)
print(f"\n■ (2-b) 검증 (n={tot}) — 절단·정규화 후 프롬프트에 보이는가")
print(f"   ★ v10 이 공급한 lemma 전부 보임   {len(good)}/{tot} = {len(good)/max(tot,1)*100:.1f}%   ← 이게 v10 의 지표")
_all = [r for r in good + bad if len(r["visible"]) == len(r["target_names"])]
print(f"     참고: 정답의 **모든** 이름 보임   {len(_all)}/{tot} = {len(_all)/max(tot,1)*100:.1f}%"
      f"   (fn 범주 포함 — v10 대상 아님)")
_oos = sum(len(r["oos"]) for r in good + bad)
print(f"     범위 밖(fn) 이름 {_oos}개")
if bad:
    print("   공급했는데 안 보이는 것:")
    for r in bad[:5]:
        print(f"     idx {r['i']} · 공급 {r['supplied']} · 보임 {r['sup_ok']} · gold {r['lems']}")
print(f"\n{V10.format_stats()}")
print("\n■ (2-b) 예제 표본 3개 — 끼워 넣은 gold 와 정답")
for r in good[:3]:
    print(f"   idx {r['i']} · gold lemma {r['lems']} · 정답이름 {r['target_names']}")
    print(f"      정답: {r['target'][:150]}")
