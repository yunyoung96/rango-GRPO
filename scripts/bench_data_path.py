#!/usr/bin/env python3
"""학습 데이터 경로의 **캐시 히트 / 미스 비용을 따로** 재고, 1에폭을 추정한다.

## 왜 따로 재나

스모크에서 본 `20.55 s/it` 은 **콜드스타트 평균**이라 정상속도가 아니다. 그렇다고
"캐시가 차면 빨라진다"고 넘기면 안 된다 — 실측하면 마지막 40스텝도 22.25 s/it 로
안 떨어졌다. 원인은 캐시가 **파일(=페이지) 단위**이기 때문이다:

  · 셔플된 2M 인덱스를 뽑으면 한 스텝(32샘플)이 서로 다른 파일 32개를 건드린다
  · 미스 한 번은 그 파일의 **모든 proof × step** 을 만든다(페이지 빌드)
  · 그래서 초반엔 거의 전부 미스고, 에폭이 진행돼야 히트로 바뀐다

즉 1에폭 비용 ≈ (전 파일 페이지 빌드) + (전 샘플 캐시 읽기) 이고, 두 항을 따로
재야 예측이 선다. 스텝당 평균만 봐서는 "느리다"는 말밖에 못 한다.

## 재는 것

  HIT   이미 캐시된 파일의 인덱스 → resolved_example + collate
  MISS  캐시 안 된 파일의 인덱스 → 같은 것 (페이지 빌드가 포함된다)

사용: PYTHONPATH=src python3 scripts/bench_data_path.py [히트표본] [미스표본]
"""
import copy
import logging
import os
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, "src")
logging.disable(logging.CRITICAL)
# ★ 설정의 출처는 `all_log/v9_env.sh` **하나**다. 여기에 값을 다시 적으면 반드시
#   어긋나고, 어긋나도 오류가 안 난다 — 조용히 다른 실험을 재게 된다(실제로 겪었다:
#   옛 CUTS_PATH 로 U1 을 재고, structural 로 "학습과 같은 설정" 감사를 돌렸다).
sys.path.insert(0, "scripts")
from _env_from_v9 import apply_v9_env  # noqa: E402
apply_v9_env(verbose=True)
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")

import yaml  # noqa: E402
from data_management.splits import Split  # noqa: E402
from tactic_gen.tactic_data import (TacticDataConf, LmDataset,  # noqa: E402
                                    example_collator_from_conf, get_tokenizer)

N_HIT = int(sys.argv[1]) if len(sys.argv) > 1 else 120
N_MISS = int(sys.argv[2]) if len(sys.argv) > 2 else 40

CONF = os.environ.get("CONF", "all_log/ft_qwen3b_v9_conf.yaml")
cc = yaml.safe_load(open(CONF))
conf = TacticDataConf.from_yaml(copy.deepcopy(cc["tactic_data"]))
tok = get_tokenizer(cc["model_name"])
ds = LmDataset.from_conf(conf, Split.TRAIN, None)
coll = example_collator_from_conf(conf.collator_conf)

CACHE = Path(cc["tactic_data"].get("cache_loc", "/tmp/ft-qwen3b-v9-cache"))
cached = {p.name for p in CACHE.iterdir() if p.is_file() and p.suffix == ".v"} \
    if CACHE.exists() else set()
TOTAL = ds.shuffled_idx.split_length(Split.TRAIN)
print(f"■ 데이터 경로 비용   TRAIN {TOTAL:,} · 캐시된 파일 {len(cached):,}개")
print(f"   캐시 위치 {CACHE}\n", flush=True)


def file_of(i):
    """인덱스 → 캐시 페이지 파일명. 검색을 돌리지 않고 StepID 만 본다."""
    try:
        return ds.shuffled_idx.get_idx(Split.TRAIN, i).file
    except Exception:
        return None


# ── 인덱스를 히트/미스로 나눈다 (검색을 안 돌리므로 싸다) ────────────────
random.seed(7)
hit_idx, miss_idx = [], []
probed = 0
while (len(hit_idx) < N_HIT or len(miss_idx) < N_MISS) and probed < 400_000:
    i = random.randrange(TOTAL)
    probed += 1
    f = file_of(i)
    if f is None:
        continue
    if f in cached:
        if len(hit_idx) < N_HIT:
            hit_idx.append(i)
    elif len(miss_idx) < N_MISS:
        miss_idx.append(i)
print(f"   인덱스 {probed:,}개 훑어 히트 {len(hit_idx)} · 미스 {len(miss_idx)} 확보")
print(f"   → 표본 히트율 {len(hit_idx)/max(probed,1)*100:.1f}% "
      f"(캐시 {len(cached):,}파일 기준)\n", flush=True)


def run(name, idxs):
    ts = []
    for k, i in enumerate(idxs):
        t0 = time.perf_counter()
        try:
            coll.collate(tok, ds.resolved_example(i))
        except Exception as ex:
            print(f"      idx={i} 예외 {type(ex).__name__}: {str(ex)[:60]}")
            continue
        ts.append(time.perf_counter() - t0)
        if (k + 1) % 20 == 0:
            print(f"      {name} {k+1}/{len(idxs)} · 중앙값 "
                  f"{sorted(ts)[len(ts)//2]*1000:.0f}ms", flush=True)
    if not ts:
        return None
    ts.sort()
    return dict(n=len(ts), mean=sum(ts) / len(ts), med=ts[len(ts) // 2],
                p90=ts[int(len(ts) * 0.9)], mx=ts[-1], total=sum(ts), _raw=ts)


print("■ 측정\n", flush=True)
r_hit = run("HIT ", hit_idx)
r_miss = run("MISS", miss_idx)

print("\n■ 결과\n")
print(f"   {'':6} {'n':>4} {'평균':>9} {'중앙값':>9} {'p90':>9} {'최대':>9}")
for nm, r in (("HIT", r_hit), ("MISS", r_miss)):
    if r:
        print(f"   {nm:6} {r['n']:4d} {r['mean']*1000:8.0f}ms "
              f"{r['med']*1000:8.0f}ms {r['p90']*1000:8.0f}ms {r['mx']*1000:8.0f}ms")

# ── 1에폭 추정 ────────────────────────────────────────────────────────
#
# ★ **평균으로 계산하면 안 된다.** HF DataLoader 는 워커를 **순서대로** 기다리므로
#   (round-robin), 한 스텝에 뽑히는 k 개 중 **가장 느린 것**이 스텝을 지배한다.
#   실측 분포가 그 차이를 만든다: MISS 중앙값 198ms 인데 최대 16.5초다.
#   평균 모형은 0.09 s/it 을 내놓지만 실제 스모크는 22.25 s/it 였다 — 250배 틀린다.
#   그래서 측정한 표본에서 **E[max of k]** 를 직접 뽑아 쓴다.
if r_hit and r_miss:
    import statistics
    print()
    NF = 13896                       # TRAIN .v 파일 수
    left = max(NF - len(cached), 0)
    W = int(cc.get("dataloader_num_workers", 6) or 1)
    NG = 2                                          # 스모크 GPU 수
    bs = int(cc.get("per_device_train_batch_size", 4))
    ga = int(cc.get("gradient_accumulation_steps", 4))
    steps = int(cc.get("max_steps", 20000))
    k = bs * ga                                     # GPU 하나가 한 스텝에 쓰는 샘플 수
    print(f"   한 스텝 = GPU당 {k}샘플 × {NG}GPU · 워커 {W}/GPU")
    print(f"   페이지 빌드 순비용 = MISS − HIT = {(r_miss['mean']-r_hit['mean'])*1000:.0f}ms/건")
    print(f"   남은 미빌드 파일 {left:,}개 (전체 {NF:,} · 캐시 {len(cached):,})\n")

    def emax(pool, k, trials=4000):
        """표본에서 k 개를 뽑을 때 **최댓값의 기대치** — 부트스트랩."""
        if not pool:
            return 0.0
        rnd = random.Random(11)
        return sum(max(rnd.choice(pool) for _ in range(k))
                   for _ in range(trials)) / trials

    hp, mp = r_hit["_raw"], r_miss["_raw"]
    print(f"   {'파일 히트율':>12} {'평균모형':>10} {'차수통계 E[max]':>16}")
    for hr in (0.0, 0.32, 0.6, 0.9, 1.0):
        pool = [x for x in hp for _ in range(int(hr * 100))] + \
               [x for x in mp for _ in range(int((1 - hr) * 100))]
        if not pool:
            continue
        mean_model = k * statistics.fmean(pool) / W
        ord_model = emax(pool, max(k // W, 1)) * W   # 워커 W개가 k개를 나눠 갖는다
        print(f"   {hr*100:11.0f}% {mean_model:9.2f}s {ord_model:15.2f}s")
    print()
    print("   ▸ 관측(스모크 마지막 40스텝) 22.25 s/it — 위 표에서 히트율 0~32% 구간과 대조")
    full = emax(hp, max(k // W, 1)) * W
    print(f"   ▸ **완전 워밍** 예측 {full:.2f} s/it  →  {steps:,}스텝 {full*steps/3600:.1f} 시간")
    print(f"   ▸ 워밍 비용(1회)  미빌드 {left:,}파일 × {r_miss['mean']:.2f}s "
          f"÷ (워커 {W}×GPU {NG}) = {left*r_miss['mean']/(W*NG)/3600:.1f} 시간")
