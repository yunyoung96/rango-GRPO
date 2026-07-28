"""Backward curriculum(역방향 커리큘럼) 빌더 — sparse reward의 구조적 해법.

아이디어: 정리를 **처음부터** 풀게 하지 말고, 인간 gold 증명의 **중간 상태**에서 시작시킨다.
  인간 증명:  a_0 → a_1 → ... → a_11 → QED  (12 tactic)
  기존:      s_0 부터 → 12개 다 맞춰야 성공 → p^12 = 8.7%
  이것:      a_0..a_7 을 initial_proof 로 주고 → 남은 4개만 → p^4 = 44%

왜 sparse reward 가 구조적으로 풀리나:
  GRPO는 그룹 8개의 보상이 **균일하면 advantage=0** 이라 그 그룹을 통째로 버린다(현재 73%).
  남은 tactic 수(remaining)로 성공확률을 직접 조준할 수 있으므로, "8번 중 일부만 성공"하는
  구간을 **보장**할 수 있다 (p=0.816 실측 기준):

      remaining=3 → 1회 성공률 54% → 8회 혼합(신호 있음) 확률 99.1%
      remaining=4 → 44%           → 98.9%
      remaining=6 → 30%           → 93.9%
      remaining=14(현재) → 5.8%   → 38.0%   ← 실측 27%

RL 문헌의 표준 처방(reverse curriculum generation, Florensa 2017).

⚠️ 분포 이동: 평가는 s_0(처음)에서 시작한다. 중간 상태로만 학습하면 **끝내기만 잘하는 모델**이
   될 수 있다 — 우리 데이터에서 죽음은 오히려 **초반(깊이≤4에서 65.7%)**에 몰려 있다.
   → 롤아웃을 **섞는다**: 절반은 s_0 에서, 절반은 s_k 에서 (curriculum_frac).

출력: data/curriculum/backward.json
  { <정규화된 정리 statement>: {"initial_proof": str, "remaining": int, "total": int, "idx": int} }
  키가 텍스트인 이유: 롤아웃 searcher 의 theorem_id 는 hash() 기반이라 프로세스마다 달라진다.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, "src")

from coqstoq import Split, get_theorem_list  # noqa: E402

from data_management.dataset_file import DatasetFile  # noqa: E402
from data_management.sentence_db import SentenceDB  # noqa: E402

COQSTOQ = Path("CoqStoq")
DATA = Path("raw-data/coqstoq-test")
DP = DATA / "data_points"
SDB = DATA / "coqstoq-test-sentences.db"
OUT = Path("data/curriculum/backward.json")

_WS = re.compile(r"\s+")


def norm(s: str) -> str:
    """정리 statement 정규화 — DatasetFile 은 개행을 공백으로 접어 저장한다."""
    return _WS.sub(" ", s).strip()


def dp_name(t) -> str:
    return f"{t.project.dir_name}-{str(t.path).replace('/', '-')}"


def gold_statement(t) -> str:
    f = COQSTOQ / "test-repos" / t.project.dir_name / t.path
    lines = f.read_text(errors="ignore").split("\n")
    return "\n".join(
        lines[t.theorem_start_pos.line : t.theorem_end_pos.line + 1]
    ).strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default="compcert")
    ap.add_argument("--start", type=int, default=200, help="프로젝트 내 슬라이스 시작(학습셋)")
    ap.add_argument("--num", type=int, default=40)
    ap.add_argument(
        "--remaining", type=int, default=4,
        help="목표 남은 tactic 수. 4면 8회 중 혼합그룹 확률 98.9%(p=0.816 기준).",
    )
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--idx-file", dest="idx_file", default=None,
                    help="전역 idx 목록 파일(bigscale). 지정 시 --start/--num 무시.")
    args = ap.parse_args()

    thms = get_theorem_list(Split.TEST, COQSTOQ)
    if args.idx_file:
        targets = [int(x) for x in Path(args.idx_file).read_text().split()]
        print(f"idx-file {args.idx_file}: {len(targets)}개 정리 (remaining={args.remaining})")
    else:
        proj = [i for i, t in enumerate(thms) if t.project.dir_name == args.project]
        targets = proj[args.start : args.start + args.num]
        print(f"{args.project}: 전체 {len(proj)} → 대상 {len(targets)}개 (전역 idx {targets[0]}..{targets[-1]})")

    sdb = SentenceDB.load(SDB)
    cache: dict[str, DatasetFile] = {}
    out: dict[str, dict] = {}
    skipped: list[tuple[int, str]] = []

    for idx in targets:
        t = thms[idx]
        p = DP / dp_name(t)
        if not p.exists():
            skipped.append((idx, "data_point 없음"))
            continue
        key = dp_name(t)
        if key not in cache:
            cache[key] = DatasetFile.load(p, sdb)
        dset = cache[key]

        want = norm(gold_statement(t))
        match = [pr for pr in dset.proofs if norm(pr.theorem.term.text) == want]
        if not match:
            skipped.append((idx, "정리 매칭 실패"))
            continue
        pr = match[0]
        steps = pr.steps
        L = len(steps)
        if L < 2:
            skipped.append((idx, f"gold 증명이 너무 짧음(L={L})"))
            continue

        # 남길 tactic 수 = min(목표, L-1). 최소 1개는 모델이 만들어야 한다.
        remaining = min(args.remaining, L - 1)
        n_prefix = L - remaining
        # 원문 그대로 이어붙인다(step.text 가 선행 개행/들여쓰기를 포함) — check_proof 가 이 형식을 받는다.
        initial_proof = "".join(s.step.text for s in steps[:n_prefix])

        out[want] = {
            "idx": idx,
            "initial_proof": initial_proof,
            "remaining": remaining,
            "total": L,
            "path": str(t.path),
        }

    o = Path(args.out)
    o.parent.mkdir(parents=True, exist_ok=True)
    o.write_text(json.dumps(out, ensure_ascii=False, indent=1))

    rem = [v["remaining"] for v in out.values()]
    tot = [v["total"] for v in out.values()]
    print(f"\n저장: {o}  ({len(out)}개)")
    if rem:
        print(f"  gold 증명 길이: 중앙값 {sorted(tot)[len(tot)//2]}  최소 {min(tot)}  최대 {max(tot)}")
        print(f"  남긴 tactic 수: {sorted(set(rem))}  (목표 {args.remaining})")
    if skipped:
        print(f"  건너뜀 {len(skipped)}개: {skipped[:5]}")


if __name__ == "__main__":
    main()
