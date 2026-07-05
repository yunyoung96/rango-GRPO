#!/usr/bin/env python3
"""
CompCert test 인덱스에 대해 run_thm.py를 실행하고 로그/요약을 저장합니다.

사용법:
  python3 scripts/run_all.py                  # rango 아키텍처로 compcert 전체 실행
  python3 scripts/run_all.py --num 100        # compcert 앞 100개만 실행
  python3 scripts/run_all.py --alias rango    # 아키텍처(alias) 지정 (기본값: rango)
"""

import argparse
import json
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

COQSTOQ_LOC = Path("CoqStoq")
SCRIPT = "scripts/run_thm.py"


def get_compcert_indices() -> list[int]:
    from coqstoq import Split, get_theorem_list
    thms = get_theorem_list(Split.TEST, COQSTOQ_LOC)
    return [i for i, t in enumerate(thms) if t.project.dir_name == "compcert"]


def run_one(idx: int, log_file: Path, alias: str, timeout: int) -> dict:
    cmd = ["python3", SCRIPT, "run", alias, "test", str(idx), "--timeout", str(timeout)]
    t0 = time.time()
    with log_file.open("w") as f:
        f.write(f"# cmd: {' '.join(cmd)}\n\n")
        result = subprocess.run(cmd, stdout=f, stderr=f)
    elapsed = time.time() - t0

    # 성공 여부는 로그 마지막에서 파싱
    success = False
    try:
        text = log_file.read_text()
        success = "CURRENT RESULT: SUCCESS" in text
    except Exception:
        pass

    return {
        "idx": idx,
        "architecture": alias,
        "timeout_sec": timeout,
        "success": success,
        "exit_code": result.returncode,
        "elapsed_sec": round(elapsed, 2),
        "log": str(log_file),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--num", type=int, default=None, metavar="N",
                        help="실행할 compcert 인덱스 수 (기본값: 전체)")
    parser.add_argument("--workers", type=int, default=2, metavar="N",
                        help="병렬 실행 워커 수 (기본값: 2)")
    parser.add_argument("--alias", "--arch", dest="alias", default="rango", metavar="ALIAS",
                        help="실행 아키텍처(run_thm.py alias) (기본값: rango)")
    parser.add_argument("--timeout", type=int, default=600, metavar="SEC",
                        help="search 제한 시간(초) (기본값: 600)")
    args = parser.parse_args()

    # compcert 인덱스 결정
    indices = get_compcert_indices()
    if args.num is not None:
        indices = indices[: args.num]

    # 출력 디렉토리
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = Path("all_results") / timestamp
    log_dir = out_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    summary_path = out_dir / "summary.json"
    print(f"총 {len(indices)}개  arch={args.alias}  timeout={args.timeout}s  workers={args.workers}  →  {out_dir}")

    results = []
    n_success = 0
    done = 0
    lock = threading.Lock()

    def save_summary():
        summary = {
            "timestamp": timestamp,
            "architecture": args.alias,
            "timeout_sec": args.timeout,
            "total": len(indices),
            "done": done,
            "success": n_success,
            "fail": done - n_success,
            "results": sorted(results, key=lambda r: r["idx"]),
        }
        summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(run_one, idx, log_dir / f"{idx}.txt", args.alias, args.timeout): idx
            for idx in indices
        }
        for future in as_completed(futures):
            r = future.result()
            with lock:
                done += 1
                n_success += r["success"]
                results.append(r)
                status = "✓" if r["success"] else "✗"
                print(f"  [{done}/{len(indices)}] idx={r['idx']}  {status}  {r['elapsed_sec']:.1f}s")
                save_summary()

    print(f"\n완료: {n_success}/{len(indices)} 성공  →  {summary_path}")


if __name__ == "__main__":
    main()
