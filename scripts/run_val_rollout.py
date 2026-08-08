#!/usr/bin/env python3
"""VAL split 병렬 롤아웃 드라이버 — on-policy 에러 수집용.

★ 왜 별도 드라이버인가:
  scripts/run_all.py 는 `get_theorem_list(Split.TEST, ...)` 로 **TEST 를 하드코딩**한다.
  에러 수집에 TEST gold 를 쓰면 그 gold 가 학습에 들어가 **평가(rand200=TEST/CompCert)가 무효**가 된다.
  실제로 그렇게 돌릴 뻔했다 — 반드시 split 을 확인할 것.

★ 왜 VAL 인가:
  CoqStoq 에는 TRAIN split 이 없다(VAL/TEST/CUTOFF 뿐). 학습 코퍼스(data/coq-dataset)는
  별개 체계라 이 인프라로 바로 못 돈다. VAL(4,971 정리)은 프로젝트가 TEST 와 완전히 분리돼
  (VAL=graph-theory·coqeal·qarith-stern-brocot / TEST=compcert·fourcolor·math-classes)
  **평가 오염이 없다.**

사용:
  python3 scripts/run_val_rollout.py --num 400 --workers 6 --gpus 0,1 --timeout 240
"""
import argparse
import os
import random
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, "src")
sys.path.insert(0, "CoqStoq")


def run_one(idx: int, alias: str, timeout: int, gpu: str, logdir: Path) -> tuple:
    env = dict(os.environ)
    if gpu is not None:
        env["CUDA_VISIBLE_DEVICES"] = str(gpu)
    log = logdir / f"{idx}.txt"
    cmd = [sys.executable, "scripts/run_thm.py", "run", alias, "val", str(idx),
           "--timeout", str(timeout)]
    t0 = time.time()
    try:
        with open(log, "w") as f:
            subprocess.run(cmd, env=env, stdout=f, stderr=subprocess.STDOUT,
                           timeout=timeout + 180)
        return idx, True, time.time() - t0
    except Exception:
        return idx, False, time.time() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alias", default="grpo-rollout-cur")
    ap.add_argument("--num", type=int, default=400)
    ap.add_argument("--workers", type=int, default=6, help="GPU 당 워커")
    ap.add_argument("--gpus", default="0,1")
    ap.add_argument("--timeout", type=int, default=240)
    ap.add_argument("--out", default="all_results/val_rollout")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    from coqstoq import Split, get_theorem_list
    thms = get_theorem_list(Split.VAL, Path("CoqStoq"))
    print(f"CoqStoq VAL: {len(thms):,} 정리")
    random.seed(args.seed)
    idxs = sorted(random.sample(range(len(thms)), min(args.num, len(thms))))

    logdir = Path(args.out) / "logs"
    logdir.mkdir(parents=True, exist_ok=True)
    gpus = [g.strip() for g in args.gpus.split(",") if g.strip()]
    total = args.workers * len(gpus)
    print(f"대상 {len(idxs)}개 · 워커 {total} (g{len(gpus)}×w{args.workers}) · {args.timeout}s")

    done = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=total) as pool:
        futs = [pool.submit(run_one, ix, args.alias, args.timeout,
                            gpus[i % len(gpus)], logdir)
                for i, ix in enumerate(idxs)]
        for f in futs:
            ix, ok, el = f.result()
            done += 1
            if done % 20 == 0:
                print(f"  {done}/{len(idxs)}  ({time.time()-t0:.0f}s 경과)", flush=True)
    print(f"완료 {done}개, {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
