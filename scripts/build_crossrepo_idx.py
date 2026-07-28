"""GRPO 학습셋 확대(§10 P6): CompCert 밖 test repo 에서 롤아웃 대상 정리를 고른다.

배경: 지금 rango-grpo 는 CompCert(cc[200:240]) 40개로만 학습한다. 그 40개 중 73%가 dead group
  (8시도 전멸 → advantage 0 → 학습에서 제외). 학습 신호가 극도로 희소하다.
  CoqStoq TEST 에 non-CompCert 정리가 4,305개 있다(fourcolor 1341, math-classes 763, ...).

왜 cross-repo 가 중요한가:
  (1) **신호량**: 40개 → 수백~수천 개. dead group 이 많아도 절대 개수가 늘어난다.
  (2) **sibling 누출 0**: 평가는 CompCert. 다른 repo 로 학습하면 파일 겹침이 구조적으로 0
      (기존 rango-grpo-self 는 CompCert 로 학습·평가해 39%가 같은 파일 → confound).

전역 test idx 를 그대로 출력한다. run_all.py --idx-file 이 이 파일을 받아 run_thm 이
get_theorem(split, idx) 로 정리를 가져온다 (repo 무관, 코드 수정 불필요).

사용:
  python3 scripts/build_crossrepo_idx.py --repos fourcolor,math-classes --num 300 \
      --out data/crossrepo/train_idx.txt
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, "src")

from coqstoq import Split, get_theorem_list  # noqa: E402

COQSTOQ = Path("CoqStoq")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--repos",
        default="fourcolor,math-classes,buchberger,reglang,poltac,huffman",
        help="쉼표구분 repo 목록. compcert 는 평가셋이라 제외 권장.",
    )
    ap.add_argument("--num", type=int, default=300, help="repo당 최대 정리 수(앞에서부터)")
    ap.add_argument("--exclude-compcert", action="store_true", default=True)
    ap.add_argument("--out", default="data/crossrepo/train_idx.txt")
    args = ap.parse_args()

    thms = get_theorem_list(Split.TEST, COQSTOQ)
    want = [r.strip() for r in args.repos.split(",") if r.strip()]
    by_repo: dict[str, list[int]] = {r: [] for r in want}
    for i, t in enumerate(thms):
        r = t.project.dir_name
        if r == "compcert" and args.exclude_compcert:
            continue
        if r in by_repo:
            by_repo[r].append(i)

    picked: list[int] = []
    print("=== repo별 선택 ===")
    for r in want:
        idxs = by_repo[r][: args.num]
        picked.extend(idxs)
        avail = len(by_repo[r])
        print(f"  {r:16} {len(idxs):4} / {avail:4}  (전역 idx {idxs[0] if idxs else '-'}..{idxs[-1] if idxs else '-'})")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(str(i) for i in picked) + "\n")
    print(f"\n저장: {out}  ({len(picked)}개 전역 test idx)")
    print("★ 평가셋(CompCert cc[0:180])과 겹치지 않음 — 다른 repo 라 파일 disjoint")


if __name__ == "__main__":
    main()
