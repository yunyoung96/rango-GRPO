#!/usr/bin/env python3
"""파서·구조신호 **대규모 동적 검증** — 실제 코퍼스 전체를 훑어 이상을 잡는다.

합성 예제 몇 개로는 안 잡힌다. `Definition f : bool := true.` 의 결론이 `bool : = true`
라는 쓰레기였는데 단위 테스트는 전부 통과했다 — 그런 것을 실제 데이터에서 잡는다.

검사 항목
  ① 파싱 성공률          — 선언 종류별
  ② **쓰레기 결론** 탐지  — 결론에 `:=` `:` `match` `with` `=>` `|` 같은 것이 남으면
                          명제가 아닌 것을 결론으로 잡은 것이다
  ③ head 위생            — 결론 head 가 키워드/구두점이면 이상
  ④ 왕복 검사            — 결론 토큰을 다시 파싱했을 때 같은 트리가 나오나
  ⑤ 이전 버전과의 회귀    — `--baseline` 파일과 비교해 **나빠진 것**만 뽑는다
  ⑥ 예외                — 어떤 입력에도 예외가 나면 안 된다

사용:
  python3 scripts/dyncheck_parser.py [n] [train|val|test] [--save base.json] [--baseline base.json]
"""
import collections
import copy
import json
import os
import re
import sys
import traceback

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.insert(0, "src")
import logging  # noqa: E402

logging.disable(logging.CRITICAL)
import yaml  # noqa: E402
from data_management.splits import Split  # noqa: E402
from data_management.dataset_file import DatasetFile  # noqa: E402
from data_management.sentence_db import SentenceDB  # noqa: E402
from premise_selection.premise_filter import PremiseFilter, PremiseFilterConf  # noqa: E402
from tactic_gen.tactic_data import TacticDataConf, LmDataset  # noqa: E402
from tactic_gen.applicable import canon, decompose, parse, parse_toks  # noqa: E402
from tactic_gen.tier_rank import declname, head_of, prem_struct  # noqa: E402

args = [a for a in sys.argv[1:] if not a.startswith("--")]
N = int(args[0]) if args else 300
SPLIT = (args[1] if len(args) > 1 else "test").upper()
SAVE = next((sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == "--save"), "")
BASE = next((sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == "--baseline"), "")

# ② 결론에 남으면 안 되는 것들 — 명제가 아닌 것을 결론으로 잡았다는 신호
_JUNK = {":=": "정의 대입", ":": "타입 표기", "match": "match 식", "with": "with 절",
         "=>": "화살표 분기", "|": "분기 막대", "end": "end", "let": "let 식",
         "fun": "람다", "Type": "Type", "Set": "Set", "Prop": "Prop"}
_BAD_HEAD = set(_JUNK) | {"forall", "exists", "fix", "cofix", "if", "then", "else"}

cc = yaml.safe_load(open("all_log/ft_qwen3b_v8_conf.yaml"))
tdc = copy.deepcopy(cc["tactic_data"])
tdc["formatter_conf"].pop("proof_ret", None)
tdc["formatter_conf"].pop("num_proofs", None)
conf = TacticDataConf.from_yaml(tdc)
ds = LmDataset.from_conf(conf, getattr(Split, SPLIT), 40000)
sdb = SentenceDB.load(conf.sentence_db_loc)
pf = PremiseFilterConf.from_yaml(tdc["formatter_conf"]["premise"]["premise_filter"])
pfilter = PremiseFilter(pf.coq_excludes, pf.non_coq_excludes, pf.general_excludes)

_KIND = re.compile(r"^\s*(\w+)")
stat = collections.Counter()
by_kind = collections.Counter()
junk = collections.Counter()
badhead = collections.Counter()
samples = collections.defaultdict(list)
exc = collections.Counter()
seen_txt = set()
n_prem = 0

for i in range(40000):
    if stat["스텝"] >= N:
        break
    try:
        e = ds.raw_example(i)
    except Exception:
        continue
    sid = ds.shuffled_idx.get_idx(ds.split, i)
    try:
        dp = DatasetFile.load(conf.data_loc / "data_points" / sid.file, sdb)
        proof = dp.proofs[sid.proof_idx]
    except Exception:
        continue
    pool = [p for p in dp.get_premises_before(proof) if pfilter.filter_premise(p)]
    if not pool:
        continue
    stat["스텝"] += 1
    # 풀이 크므로 균등 표본
    step = max(1, len(pool) // 60)
    for p in pool[::step]:
        txt = (getattr(p, "text", "") or "").strip()
        if not txt or txt in seen_txt:
            continue
        seen_txt.add(txt)
        n_prem += 1
        kind = (_KIND.match(txt) or ["?"])[0] if _KIND.match(txt) else "?"
        kind = _KIND.match(txt).group(1) if _KIND.match(txt) else "?"
        # ⑥ 예외
        try:
            d = decompose(txt)
            ps = prem_struct(txt)
        except Exception as ex:
            exc[f"{type(ex).__name__}: {str(ex)[:50]}"] += 1
            if len(samples["예외"]) < 5:
                samples["예외"].append(txt[:120])
            continue
        ok = ps is not None and ps[1] is not None
        by_kind[(kind, ok)] += 1
        stat["파싱 성공" if ok else "파싱 실패"] += 1
        if not ok:
            continue
        concl = " ".join(d[2])
        # ② 쓰레기 결론
        toks = set(d[2])
        for k, why in _JUNK.items():
            if k in toks:
                junk[why] += 1
                if len(samples[why]) < 3:
                    samples[why].append(f"{concl[:70]}   ←   {txt[:70]}")
                break
        # ③ head 위생
        h = ps[2]
        if h is None or h in _BAD_HEAD:
            badhead[str(h)] += 1
            if len(samples["head"]) < 3:
                samples["head"].append(f"head={h}  {concl[:60]}   ←   {txt[:60]}")
        # ④ 왕복
        try:
            again = parse_toks(d[2])
            if again is not None and canon(again) != ps[1]:
                stat["왕복 불일치"] += 1
        except Exception:
            stat["왕복 예외"] += 1

tot = max(n_prem, 1)
print(f"\n■ {SPLIT} — 파서 동적 검증 (스텝 {stat['스텝']} · 고유 premise {n_prem})")
print(f"\n① 파싱 성공률   {stat['파싱 성공']/tot*100:5.1f}%  "
      f"({stat['파싱 성공']}/{tot})")
print(f"\n   선언 종류별:")
kinds = sorted({k for k, _ in by_kind}, key=lambda k: -(by_kind[(k, True)] + by_kind[(k, False)]))
for k in kinds[:10]:
    o, x = by_kind[(k, True)], by_kind[(k, False)]
    print(f"     {k:14s} {o+x:6d}건  성공 {o/(max(o+x,1))*100:5.1f}%")

print(f"\n② 쓰레기 결론 (명제가 아닌 것을 결론으로 잡음)  총 {sum(junk.values())} "
      f"({sum(junk.values())/tot*100:.2f}%)")
for k, v in junk.most_common(8):
    print(f"     [{v:5d}] {k}")
    for s_ in samples[k][:2]:
        print(f"             {s_}")

print(f"\n③ 이상한 head  총 {sum(badhead.values())} ({sum(badhead.values())/tot*100:.2f}%)")
for k, v in badhead.most_common(6):
    print(f"     [{v:5d}] {k}")
for s_ in samples["head"][:2]:
    print(f"             {s_}")

print(f"\n④ 왕복 불일치 {stat['왕복 불일치']} · 왕복 예외 {stat['왕복 예외']}")
print(f"\n⑥ 예외  총 {sum(exc.values())}")
for k, v in exc.most_common(5):
    print(f"     [{v:5d}] {k}")
for s_ in samples["예외"][:3]:
    print(f"             {s_}")

res = {"n_prem": n_prem, "ok": stat["파싱 성공"], "junk": sum(junk.values()),
       "badhead": sum(badhead.values()), "exc": sum(exc.values()),
       "rt": stat["왕복 불일치"],
       "by_kind": {f"{k}": [by_kind[(k, True)], by_kind[(k, False)]] for k in kinds}}
if SAVE:
    open(SAVE, "w").write(json.dumps(res, ensure_ascii=False))
    print(f"\n   기준선 저장 → {SAVE}")
if BASE and os.path.exists(BASE):
    b = json.load(open(BASE))
    print(f"\n⑤ 이전 대비 (기준선 {BASE})")
    for k, lbl, good_up in (("ok", "파싱 성공", True), ("junk", "쓰레기 결론", False),
                            ("badhead", "이상 head", False), ("exc", "예외", False),
                            ("rt", "왕복 불일치", False)):
        a_, b_ = res[k], b.get(k, 0)
        d_ = a_ - b_
        mark = "✓" if (d_ >= 0) == good_up or d_ == 0 else "★ 나빠짐"
        print(f"     {lbl:12s} {b_:6d} → {a_:6d}  ({d_:+d})  {mark}")
