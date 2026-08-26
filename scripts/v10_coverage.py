#!/usr/bin/env python3
"""★ v10 커버리지 — **정답이 프롬프트에 보이는 비율이 100% 에 가까운가.**

두 숫자를 한 번에 낸다. 섞으면 안 된다:

  ① 검색 성공률 (주입 **전**)   랭커의 성질. v10 이 바꾸는 것이 아니다.
  ② 가시성      (주입 **후**)   ★ 이게 100% 에 가까워야 한다. v10 의 목표.

판정 규칙은 학습 경로와 **같게** 맞춘다:
  · 가시성은 `v10_inject.visible()` — collate_input(정규화 전) + 하드 절단 재현.
    `collate()` 로 재면 안 된다(NORMALIZE_NAMES 가 이름을 `_L0` 로 바꾼다).
  · **stdlib 은 제외**한다. `NORMALIZE_SKIP_STDLIB=1` 이라 익명화도 안 하고
    `_hallucinates` 도 면제한다 — 모델의 상식으로 본다.
  · 못 넣은 것이 남으면 `V10_REQUIRE_ALL` 이 예제를 **버린다**. 그것까지 세서
    "학습에 들어가는 예제 기준" 가시성을 따로 낸다.

사용: VC_N=900 VC_SHARD/VC_NSHARD VC_SPLIT=TRAIN|VAL python3 scripts/v10_coverage.py
"""
import collections, os, sys, yaml, logging
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")
os.environ["CUDA_VISIBLE_DEVICES"] = ""
sys.path.insert(0, "src")
logging.disable(logging.CRITICAL)
import rango_defaults as _D
from tactic_gen.tactic_data import LmDataset, TacticDataConf
from tactic_gen import v10_inject as V10
from data_management.splits import Split

CONF = yaml.safe_load(open(sys.argv[1] if len(sys.argv) > 1 else "all_log/ft_qwen3b_v10_conf.yaml"))
N = int(os.environ.get("VC_N", "900"))
SHARD = int(os.environ.get("VC_SHARD", "0"))
NSHARD = int(os.environ.get("VC_NSHARD", "1"))
SPLIT = getattr(Split, os.environ.get("VC_SPLIT", "TRAIN"))
td = TacticDataConf.from_yaml(CONF["tactic_data"])
ds = LmDataset.from_conf(td, SPLIT)
tok, col = ds.tokenizer, ds.example_collator
print(f"■ {SPLIT.name} · 표본 {N} · 샤드 {SHARD}/{NSHARD} · "
      f"V10={_D.get('V10_PREMISE_INJECT')} REQUIRE_ALL={_D.get('V10_REQUIRE_ALL')}", flush=True)

S = collections.Counter()
worst = []
step = max(1, len(ds) // N)
idxs = [i for j, i in enumerate(range(0, min(len(ds), N * step), step)) if j % NSHARD == SHARD]
for c, i in enumerate(idxs):
    try:
        ex = ds.raw_example(i)
        lems = V10.plan_lemmas(ex) or []
        # ★ stdlib 은 세지 않는다 — 익명화·환각판정 모두 면제하는 것과 같은 기준
        lems = [(nm, ty) for nm, ty in lems if not V10._is_stdlib(nm)]
        if not lems:
            S["외부참조 없음(또는 stdlib뿐)"] += 1
            continue
        S["외부참조 있음"] += 1
        S["lemma 총"] += len(lems)
        pre = [nm for nm, _ in lems if V10.visible(col, tok, ex, nm)]
        S["① 검색됨(주입전)"] += len(pre)
        if len(pre) == len(lems):
            S["① 스텝 전부 검색됨"] += 1
        ex2, br = V10.inject(col, tok, ex, col.collate_input(tok, ex, normalize=False))
        unpl = list(V10.LAST_UNPLACED)
        post = [nm for nm, _ in lems if V10.visible(col, tok, ex2, nm)]
        S["② 보임(주입후)"] += len(post)
        if len(post) == len(lems):
            S["② 스텝 전부 보임"] += 1
        else:
            S["② 스텝 일부 안 보임"] += 1
            if unpl:
                S["  └ v10 이 못 넣음 → 예제 폐기"] += 1
            else:
                S["  └ v10 이 넣었다 했는데 안 보임 ★버그"] += 1
                if len(worst) < 8:
                    worst.append((i, [n for n, _ in lems], post, unpl))
    except Exception:
        S["오류"] += 1
        continue
    if (c + 1) % 100 == 0:
        print(f"   … {c+1}/{len(idxs)}", flush=True)

e = max(S["외부참조 있음"], 1)
L = max(S["lemma 총"], 1)
tot = e + S["외부참조 없음(또는 stdlib뿐)"]
print(f"\n■ 스텝 {tot} · 외부참조(비-stdlib) 있음 {e} = {e/tot*100:.1f}%")
print(f"\n  {'':34s}{'스텝 기준':>12s}{'lemma 기준':>13s}")
print(f"  {'① 검색 성공률 (주입 전 · 랭커)':34s}"
      f"{S['① 스텝 전부 검색됨']/e*100:11.1f}%{S['① 검색됨(주입전)']/L*100:12.1f}%")
print(f"  {'② ★ 가시성 (주입 후 · v10)':34s}"
      f"{S['② 스텝 전부 보임']/e*100:11.1f}%{S['② 보임(주입후)']/L*100:12.1f}%")
kept = e - S["  └ v10 이 못 넣음 → 예제 폐기"]
print(f"\n  ② 를 **학습에 들어가는 예제**로만 보면 (폐기 {S['  └ v10 이 못 넣음 → 예제 폐기']} 제외)")
print(f"     {S['② 스텝 전부 보임']}/{kept} = {S['② 스텝 전부 보임']/max(kept,1)*100:.1f}%")
print(f"\n■ 안 보이는 것의 내역")
for k in ("② 스텝 일부 안 보임", "  └ v10 이 못 넣음 → 예제 폐기",
          "  └ v10 이 넣었다 했는데 안 보임 ★버그"):
    print(f"   {k:44s} {S[k]:5d}")
print(f"\n{V10.format_stats()}")
print(f"   못 넣음: 치명 {V10.STATS['못 넣음(치명)']} · stdlib면제 {V10.STATS['못 넣음(stdlib·면제)']}")
if worst:
    print("\n★버그 사례:")
    for i, nm, po, up in worst:
        print(f"   idx {i} · gold {nm} · 보임 {po} · 미배치 {up}")
if S["오류"]:
    print(f"\n(오류 {S['오류']})")
