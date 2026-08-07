#!/usr/bin/env python3
"""ExampleCache 병렬 워밍 — 학습 전에 예제(검색 포함)를 미리 만들어 둔다.

왜 필요한가:
  LmDataset.__getitem__ 은 ExampleCache 미스 시 **그 data_point 파일의 모든 proof × 모든 step**
  을 한 번에 빌드한다(파일당 수천 예제). 학습 중에 이게 걸리면 dataloader 워커가 수 분~수십 분
  멈추고 GPU 가 논다. 파일 단위로 병렬 선빌드하면 학습이 GPU-bound 가 된다.

특징:
  · 파일 단위 병렬(워커끼리 같은 파일을 건드리지 않음) → 경쟁 없음
  · 원자적 쓰기(tmp → rename): 중간에 죽어도 깨진 페이지가 안 남는다
  · 이미 캐시된 파일은 건너뜀(재실행 안전) — 죽으면 그대로 다시 돌리면 이어짐

사용: PYTHONPATH=src python3 scripts/warm_example_cache.py all_log/ft_rango_augmented_conf.yaml [워커수]
"""
import logging
import os
import pickle
import sys
import time
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.insert(0, "src")
import yaml  # noqa: E402

logging.disable(logging.CRITICAL)   # 검색 진단 로그 억제(워밍은 조용히)

_G: dict = {}


def _init(conf_path: str):
    from tactic_gen.tactic_data import TacticDataConf, LmDataset
    from data_management.splits import Split

    conf = yaml.safe_load(open(conf_path))
    ds = LmDataset.from_conf(TacticDataConf.from_yaml(conf["tactic_data"]), Split.TRAIN)
    _G["ds"] = ds


def _warm(fname: str):
    """파일 하나의 모든 (proof, step) 예제를 만들어 캐시 페이지로 저장. (예제수, 초, 스킵여부)"""
    from tactic_gen.tactic_data import ExamplePage
    from data_management.dataset_file import DatasetFile

    ds = _G["ds"]
    out = Path(ds.example_cache.cache_loc) / fname
    if out.exists():
        return (0, 0.0, True)
    t0 = time.time()
    try:
        dp = DatasetFile.load(ds.data_loc / "data_points" / fname, ds.sentence_db)
        # 거대 파일은 페이지 빌드에 수 시간 → 건너뛴다(학습 중 요청된 예제만 개별 생성됨. tactic_data 참조)
        pairs = sum(len(p.steps) for p in dp.proofs)
        if pairs > int(os.environ.get("CACHE_MAX_PAGE", "600")):
            print(f"  ~ {fname[:60]}: 예제 {pairs}개(거대) — 페이지 빌드 건너뜀", flush=True)
            return (0, time.time() - t0, True)
        page: dict[int, dict[int, object]] = {}
        n = 0
        for pi, proof in enumerate(dp.proofs):
            page[pi] = {}
            for si, _ in enumerate(proof.steps):
                page[pi][si] = ds.formatter.example_from_step(si, pi, dp, training=True)
                n += 1
        # tmp 이름은 짧게 — 255자 파일명(195개)에 접미사를 붙이면 ENAMETOOLONG
        tmp = out.parent / f".tmp-{os.getpid()}-{abs(hash(fname)) % 10**8}"
        with tmp.open("wb") as f:
            pickle.dump(ExamplePage(fname, page), f)
        os.replace(tmp, out)          # 원자적 — 부분 파일이 캐시에 남지 않음
        return (n, time.time() - t0, False)
    except Exception as e:            # 한 파일 실패가 전체를 죽이지 않게
        print(f"  ! {fname}: {type(e).__name__}: {str(e)[:120]}", flush=True)
        return (-1, time.time() - t0, False)


def main():
    conf_path = sys.argv[1] if len(sys.argv) > 1 else "all_log/ft_rango_augmented_conf.yaml"
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else max(1, (os.cpu_count() or 8) - 2)
    conf = yaml.safe_load(open(conf_path))
    td = conf["tactic_data"]
    data_loc = Path(td["data_loc"])
    cache_loc = Path(td["cache_loc"])
    cache_loc.mkdir(parents=True, exist_ok=True)
    files = sorted(os.listdir(data_loc / "data_points"))
    done0 = sum(1 for f in files if (cache_loc / f).exists())
    print(f"■ ExampleCache 워밍: 파일 {len(files)}개 (이미 캐시 {done0}) / 워커 {workers}")
    print(f"  data_loc={data_loc}  cache_loc={cache_loc}", flush=True)

    import multiprocessing as mp

    t0 = time.time()
    n_ex = n_file = n_skip = n_err = 0
    with mp.get_context("spawn").Pool(workers, initializer=_init, initargs=(conf_path,)) as pool:
        for i, (n, el, skipped) in enumerate(pool.imap_unordered(_warm, files, chunksize=4), 1):
            if skipped:
                n_skip += 1
            elif n < 0:
                n_err += 1
            else:
                n_ex += n
                n_file += 1
            if i % 200 == 0 or i == len(files):
                el_all = time.time() - t0
                rate = i / max(el_all, 1e-9)
                eta = (len(files) - i) / max(rate, 1e-9)
                print(f"  {i}/{len(files)} 파일  예제 {n_ex:,}  스킵 {n_skip}  에러 {n_err}  "
                      f"경과 {el_all/60:.1f}분  ETA {eta/60:.1f}분", flush=True)
    print(f"\n완료: 파일 {n_file} 빌드(+스킵 {n_skip}, 에러 {n_err}), 예제 {n_ex:,}, "
          f"{(time.time()-t0)/60:.1f}분")
    print(f"  캐시 용량: {sum(f.stat().st_size for f in cache_loc.iterdir())/1e9:.1f} GB")


if __name__ == "__main__":
    main()
