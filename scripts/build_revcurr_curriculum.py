"""Reverse curriculum(전체 역행) 빌더 — gold 증명의 **모든 중간 goal state**를 시작점으로.

기존 backward 는 remaining=4 **한 점**만 썼다. 여기서는 gold 궤적의 각 접두(prefix)마다
시작 상태를 만들어 **정리당 여러 그룹**을 생성한다(Florensa 2017 reverse curriculum 의 완전형).

    gold:  a_0 a_1 ... a_{L-1}
    state s_i (i tactic 적용 후) → remaining = L-i.
    initial_proof(s_i) = "".join(a_0..a_{i-1})   (build_backward 와 동일 포맷)

★ 중간밴드 필터(합의): 양 끝은 GRPO 신호가 없다.
    remaining=1 → 거의 항상 성공 = all-success dead group
    remaining 큼 → 거의 항상 실패 = all-fail dead group
  → 유용한 구간(remaining ∈ [min,max])만 emit 해서 롤아웃 비용을 신호 있는 state 에 집중.
    (train 단계는 그래도 dead group 을 한 번 더 스킵하므로 이중 안전.)

gold.json(build_gold_trajectories.py) 을 재사용한다 — 이미 step.text 리스트가 있어 재파싱 불필요.

출력: data/curriculum/revcurr.json
  { <정규화된 statement>: {"starts": [{"initial_proof":str,"remaining":int}, ...], "total":L, "idx":int} }
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

GOLD = Path("data/curriculum/gold.json")
OUT = Path("data/curriculum/revcurr.json")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", default=str(GOLD))
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--min_remaining", type=int, default=2,
                    help="remaining<이값 은 제외(remaining=1 은 all-success dead).")
    ap.add_argument("--max_remaining", type=int, default=8,
                    help="remaining>이값 은 제외(먼 state 는 all-fail dead, 롤아웃 낭비).")
    args = ap.parse_args()

    gold = json.load(open(args.gold))
    out: dict[str, dict] = {}
    n_starts = 0
    for stmt, g in gold.items():
        tacs = g["tactics"]
        L = g["L"]
        starts = []
        # i = 적용한 tactic 수(1..L-1). remaining = L-i. s_0(전체)는 롤아웃 searcher 가 따로 s0 그룹으로.
        for i in range(1, L):
            remaining = L - i
            if remaining < args.min_remaining or remaining > args.max_remaining:
                continue
            initial_proof = "".join(tacs[:i])
            starts.append({"initial_proof": initial_proof, "remaining": remaining})
        if not starts:
            continue
        out[stmt] = {"starts": starts, "total": L, "idx": g["idx"]}
        n_starts += len(starts)

    o = Path(args.out)
    o.parent.mkdir(parents=True, exist_ok=True)
    o.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    rems = [s["remaining"] for v in out.values() for s in v["starts"]]
    print(f"저장: {o}  ({len(out)}개 정리, 시작점 총 {n_starts}개)")
    if rems:
        avg = sum(len(v['starts']) for v in out.values()) / max(len(out), 1)
        print(f"  정리당 시작점 평균 {avg:.1f}개 | remaining 범위 [{min(rems)},{max(rems)}]")
        print(f"  (기존 backward: 정리당 1점(remaining=4). 이건 중간밴드 전체.)")


if __name__ == "__main__":
    main()
