"""LeanProgress(arXiv:2502.17925)용 progress-critic 학습 데이터 채굴.

타깃: 각 증명 상태에서 **no_goals 까지 남은 tactic 수**(remaining steps). 논문은 P(success) 가 아니라
이 **거리(distance)** 를 회귀한다 — HunyuanProver·QEDCartographer·MPS-Prover 모두 같은 선택.

라벨 출처(논문과의 정직한 차이):
  · 논문: 자기 BFS 증명트리의 **min-depth 성공 경로**에서 라벨 수확(on-policy).
  · 우리: **인간 증명 코퍼스**(train split)에서 수확. steps[i] 의 goals 는 tactic 적용 **전** 상태이고,
    remaining = len(steps) - i - 1 이 정확히 성립한다(검증 완료). 우리 bfs_trees 덤프에는 depth/부모
    포인터가 없어 min-depth 경로 복원이 불가능하다.
    ⚠️ 분포 이동: 인간 증명 상태 ≠ 모델이 탐색 중 만나는 상태. 이 격차는 실측으로 확인해야 한다.

누출 방지: mine_tactic_patterns.py 와 동일 — train split 만, compcert 파일 제외.

논문의 short-proof skew 보정: 증명 길이 버킷(1-5/6-10/11-20/21+)별로 균형을 맞출 수 있게
proof_len 을 같이 기록한다(밸런싱은 학습 스크립트에서).
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from multiprocessing import Pool
from pathlib import Path

DATA_LOC = Path("raw-data/coq-dataset")
SPLIT_LOC = Path("splits/random-split.json")
OUT = Path("data/progress/train.jsonl")

_COMMENT_RE = re.compile(r"\(\*.*?\*\)", re.DOTALL)


def clean(text: str) -> str:
    return _COMMENT_RE.sub(" ", text).strip()


def mine_file(dp_name: str) -> list[dict]:
    """한 파일의 (state, remaining, proof_len) 샘플들."""
    out: list[dict] = []
    path = DATA_LOC / "data_points" / dp_name
    try:
        with path.open() as f:
            d = json.load(f)
    except Exception:
        return out

    for pr in d.get("proofs", []):
        steps = pr.get("steps", [])
        # 유효 tactic 만 센다(주석뿐인 step 제외). goals 가 비면 이미 닫힌 상태 → 라벨 대상 아님.
        usable = [
            s for s in steps if clean(s.get("step", {}).get("text", "")) and s.get("goals")
        ]
        L = len(usable)
        if L == 0:
            continue
        # 같은 state 가 증명 안에서 여러 번 나오면(= `Proof.` 처럼 goal 을 안 바꾸는 tactic 때문)
        # 거리 라벨은 **최솟값**이 옳다: 그 상태에서 끝까지의 최단 거리. min 을 안 취하면 동일 state 에
        # remaining=2 와 1 이라는 모순된 라벨이 동시에 들어간다(실측). 논문의 min-depth 경로와 같은 취지.
        best: dict[str, int] = {}
        for i, s in enumerate(usable):
            goals = s["goals"]
            # goals 는 list[str] ("hyps\n\ngoal"). 다중 goal 이면 전부 이어붙인다.
            state = "\n===\n".join(goals) if isinstance(goals, list) else str(goals)
            if not state.strip():
                continue
            rem = L - i - 1
            if state not in best or rem < best[state]:
                best[state] = rem
        for state, rem in best.items():
            out.append({"state": state, "remaining": rem, "proof_len": L})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default=str(SPLIT_LOC))
    ap.add_argument("--exclude", default="compcert")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--max-state-chars", type=int, default=4000)
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    split = json.load(open(args.split))
    train = split["train_files"]
    excl = args.exclude.lower()
    kept = (
        [e for e in train if excl not in (e.get("file", "") + e["dp_name"]).lower()]
        if excl
        else train
    )
    print(f"train files: {len(train)} → 제외 '{args.exclude}' 후 {len(kept)}")

    names = [e["dp_name"] for e in kept]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    n = 0
    buckets: Counter = Counter()
    rem_hist: Counter = Counter()
    with out.open("w") as f, Pool(args.workers) as p:
        for i, rows in enumerate(p.imap_unordered(mine_file, names, 32)):
            for r in rows:
                if len(r["state"]) > args.max_state_chars:
                    r["state"] = r["state"][: args.max_state_chars]
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
                n += 1
                L = r["proof_len"]
                buckets["1-5" if L <= 5 else "6-10" if L <= 10 else "11-20" if L <= 20 else "21+"] += 1
                rem_hist[min(r["remaining"], 20)] += 1
            if (i + 1) % 2000 == 0:
                print(f"  {i+1}/{len(names)} files · {n:,} samples")

    print(f"\n저장: {out}  ({n:,} samples)")
    print("  proof-len 버킷:", dict(buckets))
    print("  remaining 분포(0..20+):", [rem_hist[k] for k in range(21)])


if __name__ == "__main__":
    main()
