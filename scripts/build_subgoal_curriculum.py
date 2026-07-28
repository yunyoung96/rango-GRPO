#!/usr/bin/env python3
"""Subgoal-first 재귀 커리큘럼 빌더 (DeepSeek-Prover-V2 subgoal decomposition 계열, 2504.21801).

아이디어: gold 증명 트리에서 **decompose 노드**(induction/destruct/case/assert 등이 subgoal 을
만든 지점)마다 그 직전까지의 prefix 를 start 로 수집한다. 정리를 처음부터가 아니라 **각 subgoal
직후 상태**에서 롤아웃하게 해, dead group(전체는 못 풀지만 subgoal 은 풀 만함)을 되살린다.

★ backward(remaining=4, 깊은 idiosyncratic 상태)와의 차이:
  - decompose 직후 subgoal 상태는 **canonical** — decompose tactic + s0 에만 의존(누가 쳤든 동일).
    `induction n` 뒤 base/step subgoal 은 gold 든 모델이든 같은 state → 모델이 배포 때 실제로
    도달하는 state 라 transfer 가능성이 backward 보다 높다(covariate shift 완화).
  - 모든 깊이의 decompose 노드를 후보로 → "재귀적으로 파고들며" subgoal 부터 롤아웃.

★ 검출: step.goals = 그 step **직전** 열린 goal 수. n_goals(i+1) > n_goals(i) 이면 step i 의
  tactic 이 subgoal 을 만든 것 → seed = steps[:i+1](decompose 포함), 모델은 fresh subgoal 마주.

출력 포맷(adaptprefix/revcurr 와 동일 — 엔진이 adapt_prefix 로 pass-rate~0.5 노드 자동선택):
  { <정규화 정리 statement>: {"starts": [{"initial_proof": str, "remaining": int}, ...],
                              "idx": int, "total": int, "path": str} }
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

_WS = re.compile(r"\s+")


def norm(s: str) -> str:
    return _WS.sub(" ", s).strip()


def dp_name(t) -> str:
    return f"{t.project.dir_name}-{str(t.path).replace('/', '-')}"


def gold_statement(t) -> str:
    f = COQSTOQ / "test-repos" / t.project.dir_name / t.path
    lines = f.read_text(errors="ignore").split("\n")
    return "\n".join(
        lines[t.theorem_start_pos.line : t.theorem_end_pos.line + 1]
    ).strip()


def n_goals(step) -> int:
    g = getattr(step, "goals", None)
    return len(g) if g is not None else 1


def decompose_starts(steps, max_starts: int):
    """gold steps 에서 decompose 노드(goal 수 증가) 직후 prefix 목록.

    반환: [{"initial_proof": str, "remaining": int, "at": int, "n_sub": int}, ...]
    """
    L = len(steps)
    counts = [n_goals(s) for s in steps]
    starts = []
    for i in range(L - 1):
        if counts[i + 1] > counts[i]:  # step i 의 tactic 이 subgoal 을 만듦
            prefix = "".join(s.step.text for s in steps[: i + 1])  # decompose 포함
            starts.append({
                "initial_proof": prefix,
                "remaining": max(1, L - (i + 1)),
                "at": i + 1,
                "n_sub": counts[i + 1] - counts[i] + 1,
            })
    # 너무 많으면 얕은(작은 at) 것 우선 — canonical 성 높음
    starts.sort(key=lambda s: s["at"])
    return starts[:max_starts]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default="compcert")
    ap.add_argument("--start", type=int, default=200, help="프로젝트 내 슬라이스 시작(gate: 200)")
    ap.add_argument("--num", type=int, default=40)
    ap.add_argument("--idx-file", dest="idx_file", default=None,
                    help="전역 idx 목록(bigscale 300). 지정 시 --start/--num 무시.")
    ap.add_argument("--max-starts", type=int, default=6, help="정리당 최대 decompose 노드 수")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    thms = get_theorem_list(Split.TEST, COQSTOQ)
    if args.idx_file:
        targets = [int(x) for x in Path(args.idx_file).read_text().split()]
        print(f"idx-file {args.idx_file}: {len(targets)}개 정리")
    else:
        proj = [i for i, t in enumerate(thms) if t.project.dir_name == args.project]
        targets = proj[args.start : args.start + args.num]
        print(f"{args.project}: 전체 {len(proj)} → 대상 {len(targets)}개 (전역 {targets[0]}..{targets[-1]})")

    sdb = SentenceDB.load(SDB)
    cache: dict[str, DatasetFile] = {}
    out: dict[str, dict] = {}
    skipped, n_nodes = [], 0

    for idx in targets:
        t = thms[idx]
        p = DP / dp_name(t)
        if not p.exists():
            skipped.append((idx, "data_point 없음")); continue
        key = dp_name(t)
        if key not in cache:
            cache[key] = DatasetFile.load(p, sdb)
        dset = cache[key]
        want = norm(gold_statement(t))
        match = [pr for pr in dset.proofs if norm(pr.theorem.term.text) == want]
        if not match:
            skipped.append((idx, "정리 매칭 실패")); continue
        steps = match[0].steps
        if len(steps) < 3:
            skipped.append((idx, f"증명 짧음(L={len(steps)})")); continue
        starts = decompose_starts(steps, args.max_starts)
        if not starts:
            skipped.append((idx, "decompose 노드 없음(선형 증명)")); continue
        out[want] = {
            "starts": [{"initial_proof": s["initial_proof"], "remaining": s["remaining"]}
                       for s in starts],
            "idx": idx, "total": len(steps), "path": str(t.path),
        }
        n_nodes += len(starts)

    o = Path(args.out)
    o.parent.mkdir(parents=True, exist_ok=True)
    o.write_text(json.dumps(out, ensure_ascii=False, indent=1))

    # ★ 스테이지 파일(B: deep→shallow 부트스트랩용, backward 단일노드 포맷).
    #   s1 = 각 정리의 **가장 쉬운(min remaining=가장 안쪽) decompose 노드** → 먼저 학습(inner).
    #   s2 = 각 정리의 **가장 어려운(max remaining=가장 바깥) decompose 노드** → 나중에(outer).
    #   (노드 1개면 s1=s2 동일 — 무해, 그 노드 추가 학습.)
    def _emit_stage(pick, suffix):
        st = {}
        for stmt, v in out.items():
            starts = v["starts"]
            node = min(starts, key=lambda s: s["remaining"]) if pick == "inner" \
                else max(starts, key=lambda s: s["remaining"])
            st[stmt] = {"idx": v["idx"], "initial_proof": node["initial_proof"],
                        "remaining": node["remaining"], "total": v["total"], "path": v["path"]}
        sp = o.with_name(o.stem + suffix + o.suffix)
        sp.write_text(json.dumps(st, ensure_ascii=False, indent=1))
        return sp
    s1 = _emit_stage("inner", "_s1")
    s2 = _emit_stage("outer", "_s2")
    print(f"  스테이지: {s1} (inner/min-remaining), {s2} (outer/max-remaining)")

    print(f"✓ {len(out)}개 정리 / decompose 노드 총 {n_nodes}개 → {o}")
    print(f"  스킵 {len(skipped)}개 (선형증명/매칭실패 등)")
    if out:
        ns = [len(v["starts"]) for v in out.values()]
        print(f"  정리당 노드: 중앙값 {sorted(ns)[len(ns)//2]}  최소 {min(ns)}  최대 {max(ns)}")


if __name__ == "__main__":
    main()
