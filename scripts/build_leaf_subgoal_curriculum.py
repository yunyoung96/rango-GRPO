#!/usr/bin/env python3
"""Leaf-first subgoal-단위 커리큘럼 (트리 깊은 leaf subgoal부터 → 위로).

사용자 의도: remaining=4,6,8 같은 평평한 tactic-거리가 아니라, **subgoal 트리 단위**로.
  gold 증명을 goal-수 궤적으로 트리화 → 각 subgoal 경계에서 seed → 그 focused subgoal 만 닫으면
  보상(grpo_rollout.py subgoal_reward, goal 수가 seed 레벨 아래로 떨어지면 reward=1, Qed 불필요).
  leaf(작은/깊은 subgoal)부터 스테이지 1 → 큰(위쪽) subgoal 로 올라감. remaining 숫자 불필요 —
  focused-subgoal 크기가 스테이지를 정의.

★ 트리 추출: c[i]=step i 직전 열린 goal 수.
  - c[s] > c[s-1]  = 분해(decompose): 새 subgoal 생성, 그 첫 자식이 focused → subgoal-start.
  - c[s] < c[s-1]  = subgoal 닫힘: 다음 형제가 focused → 또 다른 subgoal-start.
  각 subgoal-start s 의 **size** = c 가 c[s] 아래로 처음 떨어지기까지의 step 수(= 그 subgoal 증명 길이).
  size 작음 = leaf(더 이상 분해 안 되는 말단) = 쉬움 = 스테이지 1.

★ decompose-node(전부 dead)와의 차이: 거기선 Qed 보상이라 subtree 전체를 풀어야 했음.
  여기선 **focused subgoal 하나만** 닫으면 보상 → 첫 자식(보통 쉬운 base case)만 풀어도 신호.

출력(스테이지별, 엔진 adaptprefix/revcurr 와 같은 multi-start 포맷 — 정리당 여러 subgoal-start):
  { <정규화 정리>: {"starts": [{"initial_proof": str, "remaining": size}, ...], "idx", "path"} }
  s1=leaf(size≤2), s2=중간(size≤5), s3=나머지(size>5, 위쪽 subgoal/root 포함).
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

sys.path.insert(0, "src")
from coqstoq import Split, get_theorem_list  # noqa: E402
from data_management.dataset_file import DatasetFile  # noqa: E402
from data_management.sentence_db import SentenceDB  # noqa: E402

COQSTOQ = Path("CoqStoq")
DP = Path("raw-data/coqstoq-test/data_points")
SDB = Path("raw-data/coqstoq-test/coqstoq-test-sentences.db")
_WS = re.compile(r"\s+")
norm = lambda s: _WS.sub(" ", s).strip()


def dp_name(t):
    return f"{t.project.dir_name}-{str(t.path).replace('/', '-')}"


def gold_stmt(t):
    f = COQSTOQ / "test-repos" / t.project.dir_name / t.path
    lines = f.read_text(errors="ignore").split("\n")
    return "\n".join(lines[t.theorem_start_pos.line : t.theorem_end_pos.line + 1]).strip()


def n_goals(step):
    g = getattr(step, "goals", None)
    return len(g) if g is not None else 1


def subgoal_starts(steps, max_per_thm=8):
    """subgoal-start 목록: [{initial_proof, size, level, at}] (size=focused subgoal 증명 길이)."""
    L = len(steps)
    c = [n_goals(s) for s in steps]  # c[i] = step i 직전 goal 수
    out = []
    for s in range(1, L):
        # 전이(새 focused subgoal)만: 분해(↑) 또는 형제노출(↓)
        if c[s] == c[s - 1]:
            continue
        level = c[s]
        if level < 1:
            continue
        # size = c 가 level 아래로 처음 떨어지기까지
        size = None
        for k in range(s, L):
            if c[k] < level:
                size = k - s
                break
        if size is None:
            size = L - s
        if size <= 0:
            continue
        initial_proof = "".join(x.step.text for x in steps[:s])
        out.append({"initial_proof": initial_proof, "size": size, "level": level, "at": s})
    # size 오름차순(leaf 먼저), 정리당 상한
    out.sort(key=lambda x: (x["size"], x["at"]))
    return out[:max_per_thm]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default="compcert")
    ap.add_argument("--start", type=int, default=200)
    ap.add_argument("--num", type=int, default=40)
    ap.add_argument("--idx-file", dest="idx_file", default=None)
    ap.add_argument("--max-per-thm", type=int, default=8)
    ap.add_argument("--out", required=True, help="스테이지 파일 접두(예: data/curriculum/leaf.json → leaf_s1/s2/s3.json)")
    args = ap.parse_args()

    thms = get_theorem_list(Split.TEST, COQSTOQ)
    if args.idx_file:
        targets = [int(x) for x in Path(args.idx_file).read_text().split()]
        print(f"idx-file: {len(targets)}개")
    else:
        proj = [i for i, t in enumerate(thms) if t.project.dir_name == args.project]
        targets = proj[args.start : args.start + args.num]
        print(f"{args.project}: {len(targets)}개 (전역 {targets[0]}..{targets[-1]})")

    sdb = SentenceDB.load(SDB)
    cache, skipped, n_sub = {}, 0, 0
    # 스테이지 경계: leaf(≤2) / 중간(≤5) / 나머지
    stages = {"s1": (1, 2), "s2": (3, 5), "s3": (6, 10**9)}
    out = {k: {} for k in stages}

    for idx in targets:
        t = thms[idx]
        p = DP / dp_name(t)
        if not p.exists():
            skipped += 1; continue
        key = dp_name(t)
        if key not in cache:
            cache[key] = DatasetFile.load(p, sdb)
        want = norm(gold_stmt(t))
        m = [pr for pr in cache[key].proofs if norm(pr.theorem.term.text) == want]
        if not m or len(m[0].steps) < 3:
            skipped += 1; continue
        subs = subgoal_starts(m[0].steps, args.max_per_thm)
        if not subs:
            skipped += 1; continue
        n_sub += len(subs)
        for st, (lo, hi) in stages.items():
            sel = [s for s in subs if lo <= s["size"] <= hi]
            if sel:
                out[st][want] = {
                    "starts": [{"initial_proof": s["initial_proof"], "remaining": s["size"]} for s in sel],
                    "idx": idx, "path": str(t.path),
                }

    op = Path(args.out)
    op.parent.mkdir(parents=True, exist_ok=True)
    for st in stages:
        f = op.with_name(op.stem + "_" + st + op.suffix)
        f.write_text(json.dumps(out[st], ensure_ascii=False, indent=1))
        ns = sum(len(v["starts"]) for v in out[st].values())
        print(f"  {st} ({stages[st][0]}~{stages[st][1] if stages[st][1]<10**9 else '∞'} size): "
              f"{len(out[st])}개 정리 / subgoal-start {ns}개 → {f}")
    print(f"✓ subgoal-start 총 {n_sub}개, 스킵 {skipped}개")


if __name__ == "__main__":
    main()
