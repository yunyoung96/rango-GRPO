#!/usr/bin/env python3
"""
CompCert test 인덱스에 대해 run_thm.py를 실행하고 로그/요약을 저장합니다.

사용법:
  python3 scripts/run_all.py                  # rango 아키텍처로 compcert 전체 실행
  python3 scripts/run_all.py --num 100        # compcert 앞 100개만 실행
  python3 scripts/run_all.py --alias rango    # 아키텍처(alias) 지정 (기본값: rango)
"""

import argparse
import os
import signal
import json
import queue
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


def run_one(idx: int, log_file: Path, alias: str, timeout: int, gpu=None) -> dict:
    cmd = ["python3", SCRIPT, "run", alias, "test", str(idx), "--timeout", str(timeout)]
    # 하드 timeout: 검색이 hang(무한루프/거대 goal)해도 강제 종료. 모델로드+정리 버퍼 +300s.
    hard_timeout = timeout + 300
    # ★ 멀티-GPU: gpu 지정시 이 워커(+자식 서버/coq)를 해당 물리 GPU 에 핀.
    #   서버는 device 인자 없이 torch 기본(cuda:0)만 쓰므로 CUDA_VISIBLE_DEVICES remap 으로 정확히 핀된다.
    env = os.environ.copy()
    if gpu is not None:
        env["CUDA_VISIBLE_DEVICES"] = str(gpu)
    t0 = time.time()
    returncode = 0
    with log_file.open("w") as f:
        f.write(f"# cmd: {' '.join(cmd)}  [CUDA_VISIBLE_DEVICES={gpu}]\n\n")
        proc = subprocess.Popen(cmd, stdout=f, stderr=f, start_new_session=True, env=env)
        try:
            returncode = proc.wait(timeout=hard_timeout)
        except subprocess.TimeoutExpired:
            # 프로세스 그룹 통째로 SIGKILL (자식 서버/coqpyt까지)
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except Exception:
                proc.kill()
            proc.wait()
            returncode = -9
            f.write(f"\n[run_all] HARD TIMEOUT ({hard_timeout}s) — killed hung process group\n")
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
        "exit_code": returncode,
        "elapsed_sec": round(elapsed, 2),
        "gpu": gpu,
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
    parser.add_argument("--idx-file", dest="idx_file", type=str, default=None, metavar="FILE",
                        help="명시적 인덱스 리스트 파일(커리큘럼용). 지정시 --start 무시.")
    parser.add_argument("--gpus", type=str, default=None, metavar="LIST",
                        help="쉼표구분 물리 GPU 목록(예: 0,1). 지정시 --workers=GPU당 워커수 → "
                             "총 len(gpus)×workers 병렬, 각 워커를 CUDA_VISIBLE_DEVICES 로 핀(GPU당 정확히 workers개). "
                             "미지정시 기존 단일풀 동작.")
    args = parser.parse_args()

    # compcert 인덱스 결정
    if args.idx_file:
        # (E3 커리큘럼) 명시적 인덱스 리스트 파일(한 줄에 하나) — sibling-rich 정리 등.
        text = Path(args.idx_file).read_text().split()
        indices = [int(x) for x in text]
        if args.num is not None:
            indices = indices[: args.num]
    else:
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
        # 디렉토리 이름에 옵션(alias) 부착: 20260712-055144_rango-grpo-rmaxts
        safe_alias = re.sub(r"[^A-Za-z0-9._-]", "-", str(args.alias))
        out_dir = Path("all_results") / f"{timestamp}_{safe_alias}"
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

    # ★ HW 환경 stamp(성공률 해석은 검색·워커·GPU 함께 봐야 함 — CEILING_ANALYSIS §0 confound)
    try:
        import subprocess as _sp
        _gpu_name = _sp.check_output(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            text=True, timeout=10).strip().splitlines()[0].strip()
    except Exception:
        _gpu_name = "unknown"

    lock = threading.Lock()

    def save_summary():
        summary = {
            "timestamp": timestamp,
            "architecture": args.alias,
            "description": args.description,
            "timeout_sec": args.timeout,
            "workers": args.workers,          # ★ 워커 수(성공률 confound 축)
            "gpus": args.gpus,                 # ★ 사용 GPU id 리스트("0" / "0,1")
            "gpu_name": _gpu_name,             # ★ 실측 GPU 모델명
            "total": total,
            "done": done,
            "success": n_success,
            "fail": done - n_success,
            "results": sorted(results, key=lambda r: r["idx"]),
        }
        summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    save_summary()  # resume 시에도 총계 즉시 반영

    def record(r):
        nonlocal done, n_success
        with lock:
            done += 1
            n_success += r["success"]
            results.append(r)
            status = "✓" if r["success"] else "✗"
            g = r.get("gpu")
            gtag = f" gpu{g}" if g is not None else ""
            print(f"  [{done}/{total}] idx={r['idx']}  {status}  {r['elapsed_sec']:.1f}s{gtag}")
            save_summary()
            # (오염 가드는 in-code 로직 대신 별도 nvidia-smi 감시자(all_log/gpu_watch.sh)가
            #  GPU util·메모리를 md 에 연속 기록 → 사용자에 보고. 보고 전용, 자동정지 없음.)

    gpu_list = [g.strip() for g in args.gpus.split(",") if g.strip()] if args.gpus else None

    if gpu_list:
        # ★ 멀티-GPU: GPU당 정확히 args.workers 개 스레드(고정 GPU) + 공유큐(동적 분배) → 총 g×w 병렬.
        #   스레드는 subprocess.wait 에서 블록만 하므로 오케스트레이션 CPU 는 무시할 수준.
        total_par = len(gpu_list) * args.workers
        print(f"멀티-GPU 병렬: gpus={gpu_list} × workers/gpu={args.workers} = {total_par} 병렬 "
              f"(GPU당 {args.workers}개 캡, 공유큐 동적분배)")
        work_q: queue.Queue = queue.Queue()
        for idx in indices_to_run:
            work_q.put(idx)

        def worker(gpu):
            while True:
                try:
                    idx = work_q.get_nowait()
                except queue.Empty:
                    return
                try:
                    record(run_one(idx, log_dir / f"{idx}.txt", args.alias, args.timeout, gpu))
                finally:
                    work_q.task_done()

        threads = []
        for gpu in gpu_list:
            for _ in range(args.workers):
                t = threading.Thread(target=worker, args=(gpu,), daemon=True)
                t.start()
                threads.append(t)
        for t in threads:
            t.join()
    else:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(run_one, idx, log_dir / f"{idx}.txt", args.alias, args.timeout): idx
                for idx in indices_to_run
            }
            for future in as_completed(futures):
                record(future.result())

    print(f"\n완료: {n_success}/{total} 성공  →  {summary_path}")


if __name__ == "__main__":
    main()
