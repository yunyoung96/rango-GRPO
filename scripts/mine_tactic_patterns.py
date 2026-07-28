"""PGTS(2604.24354)용 tactic 전이 패턴 채굴 — 인간이 쓴 Coq 증명에서 tactic head bigram 통계.

출력: data/tactic_patterns/patterns.json  {bigram, unigram, total, meta}

누출 방지(중요):
  · **random-split 의 TRAIN 파일만** 사용(평가는 CoqStoq test).
  · 추가로 **compcert 경로 파일을 통째로 제외**(--exclude). 우리 평가셋이 CompCert라,
    같은 프로젝트의 인간 증명에서 통계를 캐면 sibling 누출 논란이 생긴다. 제외하면
    "다른 프로젝트에서 배운 tactic 문법 사전"이 되어 방어 가능해진다.

속도: data_points 의 raw JSON 을 직접 읽는다(SentenceDB 우회 — sentence 당 sqlite 조회를 피함).
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from multiprocessing import Pool
from pathlib import Path

import sys

sys.path.insert(0, "src")
sys.path.insert(0, str(Path(__file__).parent))

from model_deployment.pgts_searcher import BOS, tactic_head  # noqa: E402

DATA_LOC = Path("raw-data/coq-dataset")
SPLIT_LOC = Path("splits/random-split.json")
OUT = Path("data/tactic_patterns/patterns.json")

# (* ... *) 및 (** ... *) 주석 제거. step.text 에 주석이 붙어 오는 경우가 흔하다.
_COMMENT_RE = re.compile(r"\(\*.*?\*\)", re.DOTALL)


def clean_tactic(text: str) -> str:
    return _COMMENT_RE.sub(" ", text).strip()


def mine_file(dp_name: str) -> tuple[Counter, Counter, int, int]:
    """한 파일의 (bigram, unigram, n_proofs, n_steps)."""
    bi: Counter = Counter()
    uni: Counter = Counter()
    n_proofs = n_steps = 0
    path = DATA_LOC / "data_points" / dp_name
    try:
        with path.open() as f:
            d = json.load(f)
    except Exception:
        return bi, uni, 0, 0

    for pr in d.get("proofs", []):
        heads = []
        for s in pr.get("steps", []):
            t = clean_tactic(s.get("step", {}).get("text", ""))
            if not t:
                continue
            heads.append(tactic_head(t))
        if not heads:
            continue
        n_proofs += 1
        n_steps += len(heads)
        prev = BOS
        for h in heads:
            bi[(prev, h)] += 1
            uni[h] += 1
            prev = h
    return bi, uni, n_proofs, n_steps


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default=str(SPLIT_LOC))
    ap.add_argument(
        "--exclude",
        default="compcert",
        help="이 문자열이 파일 경로에 있으면 제외(누출 방지). 빈 문자열이면 제외 없음.",
    )
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--min-count", type=int, default=2, help="이 미만 빈도의 bigram은 버림")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    split = json.load(open(args.split))
    train = split["train_files"]
    excl = args.exclude.lower()
    if excl:
        kept = [
            e for e in train if excl not in (e.get("file", "") + e["dp_name"]).lower()
        ]
    else:
        kept = train
    print(
        f"train files: {len(train)} → 제외 '{args.exclude}' 후 {len(kept)} "
        f"({len(train)-len(kept)}개 제외)"
    )

    names = [e["dp_name"] for e in kept]
    bi_all: Counter = Counter()
    uni_all: Counter = Counter()
    n_proofs = n_steps = 0
    with Pool(args.workers) as p:
        for i, (bi, uni, np_, ns_) in enumerate(p.imap_unordered(mine_file, names, 32)):
            bi_all.update(bi)
            uni_all.update(uni)
            n_proofs += np_
            n_steps += ns_
            if (i + 1) % 1000 == 0:
                print(f"  {i+1}/{len(names)} files · {n_proofs} proofs · {n_steps} steps")

    nested: dict[str, dict[str, int]] = defaultdict(dict)
    dropped = 0
    for (prev, h), c in bi_all.items():
        if c < args.min_count:
            dropped += 1
            continue
        nested[prev][h] = c

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        json.dump(
            {
                "bigram": nested,
                "unigram": dict(uni_all),
                "total": n_steps,
                "meta": {
                    "split": args.split,
                    "excluded": args.exclude,
                    "files": len(names),
                    "proofs": n_proofs,
                    "steps": n_steps,
                    "distinct_heads": len(uni_all),
                    "bigrams_kept": sum(len(v) for v in nested.values()),
                    "bigrams_dropped_min_count": dropped,
                },
            },
            f,
        )
    print(f"\n저장: {out}")
    print(f"  proofs {n_proofs:,} · steps {n_steps:,} · distinct heads {len(uni_all):,}")
    print(f"  bigram {sum(len(v) for v in nested.values()):,} (min-count<{args.min_count} 로 {dropped:,} 버림)")
    print("  최빈 head:", uni_all.most_common(12))


if __name__ == "__main__":
    main()
