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
import re
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

    # 성공 여부 + rango.json 기준 원래 성공 여부를 로그에서 파싱
    success = False
    original_success = None  # rango.json(published Rango) 기준
    try:
        text = log_file.read_text()
        success = "CURRENT RESULT: SUCCESS" in text
        m = re.search(r"RANGO_JSON_SUCCESS: (True|False)", text)
        if m:
            original_success = m.group(1) == "True"
    except Exception:
        pass

    return {
        "idx": idx,
        "architecture": alias,
        "timeout_sec": timeout,
        "success": success,
        "original_success": original_success,
        "exit_code": result.returncode,
        "elapsed_sec": round(elapsed, 2),
        "log": str(log_file),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--num", type=int, default=None, metavar="N",
                        help="실행할 compcert 인덱스 수 (기본값: 전체)")
    parser.add_argument("--start", type=int, default=0, metavar="I",
                        help="시작 오프셋(compcert 인덱스 리스트 기준). eval셋과 분리용. (기본값: 0)")
    parser.add_argument("--workers", type=int, default=2, metavar="N",
                        help="병렬 실행 워커 수 (기본값: 2)")
    parser.add_argument("--alias", "--arch", dest="alias", default="rango", metavar="ALIAS",
                        help="실행 아키텍처(run_thm.py alias) (기본값: rango)")
    parser.add_argument("--timeout", type=int, default=600, metavar="SEC",
                        help="search 제한 시간(초) (기본값: 600)")
    parser.add_argument("--description", type=str, default="", metavar="TEXT",
                        help="이 아키텍처가 어떤 아이디어로 개선한 것인지 짧은 설명 (summary.json에 기록)")
    parser.add_argument("--out", type=str, default=None, metavar="DIR",
                        help="기존 결과 디렉토리 재사용(resume). 이미 완료된 idx는 건너뜀.")
    args = parser.parse_args()

    # compcert 인덱스 결정
    indices = get_compcert_indices()
    if args.start:
        indices = indices[args.start:]
    if args.num is not None:
        indices = indices[: args.num]

    # 출력 디렉토리 (--out 이면 resume)
    if args.out is not None:
        out_dir = Path(args.out)
        timestamp = out_dir.name
    else:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        out_dir = Path("all_results") / timestamp
    log_dir = out_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "summary.json"

    # resume: 기존 summary.json에서 완료분 로드 → 남은 idx만 실행
    results = []
    n_success = 0
    if summary_path.exists():
        prev = json.loads(summary_path.read_text())
        results = prev.get("results", [])
        n_success = sum(1 for r in results if r.get("success"))
        done_idx = {r["idx"] for r in results}
        remaining = [i for i in indices if i not in done_idx]
        print(f"[resume] {len(done_idx)}개 완료됨 → 남은 {len(remaining)}개 실행")
        indices_to_run = remaining
    else:
        indices_to_run = indices

    total = len(indices)
    done = len(results)
    print(f"총 {total}개  arch={args.alias}  timeout={args.timeout}s  workers={args.workers}  →  {out_dir}")

    lock = threading.Lock()

    def save_summary():
        summary = {
            "timestamp": timestamp,
            "architecture": args.alias,
            "description": args.description,
            "timeout_sec": args.timeout,
            "total": total,
            "done": done,
            "success": n_success,
            "fail": done - n_success,
            "results": sorted(results, key=lambda r: r["idx"]),
        }
        summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    save_summary()  # resume 시에도 총계 즉시 반영
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(run_one, idx, log_dir / f"{idx}.txt", args.alias, args.timeout): idx
            for idx in indices_to_run
        }
        for future in as_completed(futures):
            r = future.result()
            with lock:
                done += 1
                n_success += r["success"]
                results.append(r)
                status = "✓" if r["success"] else "✗"
                print(f"  [{done}/{total}] idx={r['idx']}  {status}  {r['elapsed_sec']:.1f}s")
                save_summary()

    print(f"\n완료: {n_success}/{total} 성공  →  {summary_path}")


if __name__ == "__main__":
    main()
