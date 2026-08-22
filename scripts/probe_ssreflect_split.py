#!/usr/bin/env python3
"""★ SSReflect 사용률이 스플릿마다 얼마나 다른가 — TRAIN 에서 건너뛸 수 있나.

## 가설 (사용자 제안)

held-out(TEST/VAL)에 SSReflect 가 거의 없다면, TRAIN 의 SSReflect 스텝은
**배워도 쓸 데가 없다.** 그러면 그냥 제외해서
  · 환각(파일 밖 Ltac·`have` 이름 등)을 줄이고
  · 학습 예산을 실제로 쓰일 문법에 몰아줄 수 있다.

## 판정

SSReflect 표지: `move:`·`move=>`·`apply:`·`case:`·`elim:`·`rewrite -`·`have `·
`suff`·`wlog`·`by []`·`//`·`/=`·`=>` 패턴. (mathcomp/HoTT 계열이 주로 쓴다.)

스플릿마다 · gold lemma 를 쓰는 스텝 중 SSReflect 비율 · 프로젝트별 분포를 낸다.

사용: PYTHONPATH=src python3 scripts/probe_ssreflect_split.py [스플릿당 표본]
"""
import collections
import copy
import logging
import os
import random
import re
import sys

sys.path.insert(0, "src")
sys.path.insert(0, "scripts")
logging.disable(logging.CRITICAL)
from _env_from_v9 import apply_v9_env  # noqa: E402
apply_v9_env(verbose=True)
os.environ.setdefault("CACHE_MAX_PAGE", "0")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")

import yaml  # noqa: E402
from data_management.splits import Split  # noqa: E402
from tactic_gen.tactic_data import TacticDataConf, LmDataset  # noqa: E402
from tactic_gen.gold_lemma import gold_lemmas  # noqa: E402
from tactic_gen.search_query import local_names  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 1500
cc = yaml.safe_load(open("all_log/ft_qwen3b_v9_conf.yaml"))

# SSReflect 표지 — 하나라도 걸리면 SSReflect 로 본다
SSR = re.compile(
    r"(?:^|[;\s\[\]|(){}])(?:move|apply|case|elim|congr|rewrite|exact|set|pose)\s*:"
    r"|=>\s*[\[\/]"
    r"|(?:^|[;\s])(?:have|suff|suffices|wlog)\s"
    r"|\bby\s*\[\]"
    r"|//[=/]?"
    r"|rewrite\s+-"
    r"|/=")

for sp in ("TRAIN", "VAL", "TEST"):
    _td = copy.deepcopy(cc["tactic_data"])
    _td["cache_loc"] = f"/tmp/ssr-{sp.lower()}-cache"
    conf = TacticDataConf.from_yaml(_td)
    try:
        ds = LmDataset.from_conf(conf, getattr(Split, sp), None)
    except Exception as e:
        print(f"  {sp}: 로드 실패 {e}")
        continue
    TOT = ds.shuffled_idx.split_length(getattr(Split, sp))
    st = collections.Counter()
    proj_ssr = collections.Counter()
    proj_all = collections.Counter()
    random.seed(5)
    tried = 0
    while st["스텝"] < N and tried < N * 12:
        i = random.randrange(TOT)
        tried += 1
        try:
            e = ds.raw_example(i)
        except RuntimeError as _re:
            sys.stderr.write(f"\n★★ {sp} 중단: {str(_re)[:200]}\n"); sys.exit(3)
        except Exception:
            continue
        st["스텝"] += 1
        tac = (e.next_steps[0] if getattr(e, "next_steps", None) else "").strip()
        is_ssr = bool(SSR.search(tac))
        fn = (getattr(e, "file_name", "") or "").split("repos/")[-1].split("/")[0]
        proj_all[fn] += 1
        if is_ssr:
            st["SSReflect"] += 1
            proj_ssr[fn] += 1
        golds = gold_lemmas(tac, local_names(getattr(e, "proof_state", "") or ""))
        if golds:
            st["gold lemma 사용"] += 1
            if is_ssr:
                st["★ gold lemma + SSReflect"] += 1
    n = max(st["스텝"], 1)
    g = max(st["gold lemma 사용"], 1)
    print(f"\n■ {sp}  (표본 {st['스텝']:,})")
    print(f"   SSReflect               {st['SSReflect']:6,}  {st['SSReflect']/n*100:5.1f}%")
    print(f"   gold lemma 사용          {st['gold lemma 사용']:6,}  {st['gold lemma 사용']/n*100:5.1f}%")
    print(f"   ★ gold lemma + SSReflect {st['★ gold lemma + SSReflect']:6,}  "
          f"{st['★ gold lemma + SSReflect']/n*100:5.1f}% (전체) · "
          f"{st['★ gold lemma + SSReflect']/g*100:5.1f}% (lemma 스텝 중)")
    top = sorted(proj_all, key=lambda k: -proj_ssr[k])[:6]
    print("   SSReflect 많은 프로젝트:")
    for k in top:
        if proj_ssr[k]:
            print(f"     {k[:44]:44s} {proj_ssr[k]:5,}/{proj_all[k]:<5,} "
                  f"({proj_ssr[k]/max(proj_all[k],1)*100:.0f}%)")
