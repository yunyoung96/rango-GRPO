"""스마트 에스컬레이션 평가 하니스.

요구사항:
  ① @20 먼저 → 가망 있으면 그 20개를 **재사용**하고 40개로 확장 (20 버리지 않음).
  ② all_results/{date}_{alias} 를 alias 로 매칭. 이미 있으면:
       - 코드/모델이 그대로면 → **완료된 idx 재사용**(resume).
       - 수정 이력이 있으면(fingerprint 불일치) → **덮어쓰기**(그 dir 비우고 재실행).
  ③ 비교 기준 = **우리 rango**(published 아님). @20 우리rango=11, @40=15.

fingerprint = (searcher conf repr) + (searcher 구현 파일 내용) + (adapter 파일 mtime+size).
  → alias 정의 변경/재학습/탐색기 코드 변경을 감지. 무관한 변경엔 안 걸림(좁게 잡음).

사용:
  python3 scripts/smart_eval.py --alias rango-grpo-fix --stages 20,40 --promise 10
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import inspect
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "src")
sys.path.insert(0, "scripts")

from coqstoq import Split, get_theorem_list  # noqa: E402

COQSTOQ = Path("CoqStoq")
RESULTS = Path("all_results")


def safe(alias: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "-", alias)


def fingerprint(alias: str) -> str:
    """alias 의 코드/모델 지문. 바뀌면 캐시 무효."""
    import run_thm

    h = hashlib.md5()
    # 1) searcher conf repr + 구현 파일
    try:
        sc = run_thm.get_searcher_conf(alias)
        h.update(repr(sc).encode())
        h.update(Path(inspect.getfile(type(sc))).read_bytes())
    except Exception as e:
        h.update(f"searcher-err:{e}".encode())
    # 2) tactic conf 의 adapter 파일 mtime+size (재학습 감지)
    try:
        confs = run_thm.get_tactic_confs(alias, Split.TEST)
        for c in confs:
            ck = getattr(c, "checkpoint_loc", None) or getattr(c, "checkpoint", None)
            if ck:
                h.update(str(ck).encode())  # adapter 경로 (alias 구분)
                p = Path(ck) / "adapter_model.safetensors"
                if p.exists():
                    st = p.stat()
                    h.update(f"{st.st_mtime_ns}:{st.st_size}".encode())  # 재학습 감지
                else:
                    h.update(b"no-adapter")  # 아직 학습 안 됨
    except Exception as e:
        h.update(f"tactic-err:{e}".encode())
    return h.hexdigest()[:16]


def find_dir(alias: str) -> Path | None:
    ds = sorted(glob.glob(str(RESULTS / f"*_{safe(alias)}")))
    return Path(ds[-1]) if ds else None


_CC_CACHE: list[int] = []


def first_cc(n: int) -> set[int]:
    global _CC_CACHE
    if not _CC_CACHE:
        thms = get_theorem_list(Split.TEST, COQSTOQ)
        _CC_CACHE = [i for i, t in enumerate(thms) if t.project.dir_name == "compcert"]
    return set(_CC_CACHE[:n])


def stat_at(d: Path, num: int) -> tuple[int, int, int, list, list]:
    """dir 결과를 **첫 num개 compcert 인덱스로 제한**해 집계. 캐시가 더 많아도 정확."""
    r = json.loads((d / "summary.json").read_text())["results"]
    keep = first_cc(num)
    rr = [x for x in r if x["idx"] in keep]
    s = sum(1 for x in rr if x.get("success"))
    o = sum(1 for x in rr if x.get("original_success"))
    g = [x["idx"] for x in rr if x.get("success") and not x.get("original_success")]
    c = [x["idx"] for x in rr if x.get("original_success") and not x.get("success")]
    return len(rr), s, o, g, c


def our_rango(n: int) -> int | None:
    """우리 rango @n 성공수 (있으면). 비교 기준."""
    ds = sorted(glob.glob(str(RESULTS / "2026071*_rango")))
    if not ds:
        return None
    thms = get_theorem_list(Split.TEST, COQSTOQ)
    cc = [i for i, t in enumerate(thms) if t.project.dir_name == "compcert"][:n]
    r = {x["idx"]: x for x in json.loads(Path(ds[-1], "summary.json").read_text())["results"]}
    return sum(1 for i in cc if r.get(i, {}).get("success"))


def run_stage(alias: str, num: int, out: Path, workers: int, timeout: int) -> None:
    cmd = ["python3", "scripts/run_all.py", "--alias", alias, "--num", str(num),
           "--timeout", str(timeout), "--workers", str(workers), "--out", str(out),
           "--description", f"smart_eval @{num} ({alias})"]
    subprocess.run(cmd, check=False)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--alias", required=True)
    ap.add_argument("--stages", default="20,40", help="에스컬레이션 단계, 쉼표구분")
    ap.add_argument("--promise", type=int, default=None,
                    help="@첫단계 성공수가 이 미만이면 확장 중단. 미지정=우리rango-1 자동")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--timeout", type=int, default=600)
    args = ap.parse_args()

    stages = [int(x) for x in args.stages.split(",")]
    fp = fingerprint(args.alias)
    d = find_dir(args.alias)

    # 캐시 판정
    if d is not None:
        fpf = d / "fingerprint.txt"
        cached_fp = fpf.read_text().strip() if fpf.exists() else "(없음)"
        if cached_fp == fp:
            print(f"[smart] 캐시 일치 → 재사용 {d} (fp={fp})")
        else:
            print(f"[smart] ★ 수정 감지 (fp {cached_fp} → {fp}) → 덮어쓰기 {d}")
            # summary + logs 비우고 같은 dir 재사용
            (d / "summary.json").unlink(missing_ok=True)
            for f in (d / "logs").glob("*.txt"):
                f.unlink()
    else:
        # 새 dir (날짜 없이 stable name — Date.now 불가 회피, run_all 이 dir 이름 유지)
        d = RESULTS / f"smart_{safe(args.alias)}"
        d.mkdir(parents=True, exist_ok=True)
        print(f"[smart] 신규 {d} (fp={fp})")
    (d / "fingerprint.txt").write_text(fp)

    # 에스컬레이션
    for k, n in enumerate(stages):
        run_stage(args.alias, n, d, args.workers, args.timeout)
        tot, s, o, g, c = stat_at(d, n)
        base = our_rango(n)
        base_s = f"우리rango {base}" if base is not None else "우리rango ?"
        # ★ 비교기준은 우리 rango 뿐(published 비교 안 함 — 하드웨어 confound).
        net_s = f"net {s-base:+d}" if base is not None else "net ?"
        print(f"\n[smart] ■ {args.alias} @{n}: {s}/{n} | vs {base_s} | {net_s}")

        if k < len(stages) - 1:  # 다음 단계로 갈지 판정
            thr = args.promise if args.promise is not None else (
                (base - 1) if base is not None else 0)
            if s < thr:
                print(f"[smart] ✗ @{n} 성공 {s} < 가망기준 {thr} → 확장 중단 (compute 절약)")
                break
            print(f"[smart] ✓ @{n} 성공 {s} ≥ 가망기준 {thr} → @{stages[k+1]} 확장 "
                  f"(기존 {tot}개 재사용, {stages[k+1]-tot}개만 추가)")


if __name__ == "__main__":
    main()
