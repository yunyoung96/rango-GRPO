"""LUFFY(2504.14945)용 gold 궤적 빌더 — 학습 정리의 인간 gold 증명을 tactic 리스트로 추출.

build_backward_curriculum.py 와 같은 파싱(DatasetFile.proofs[].steps[].step.text) 을 쓰되,
prefix 가 아니라 **전체 gold tactic 순서**를 저장한다. 롤아웃(gold 모드)이 이걸 하나씩 재생해
검증된 궤적(reward=1, off_policy)을 만든다.

출력: data/curriculum/gold.json
  { <정규화된 정리 statement>: {"tactics": [t0, t1, ..., "Qed."], "idx": <전역idx>, "L": <길이>} }
  키가 텍스트인 이유: 롤아웃 theorem_id 는 hash() 기반이라 프로세스마다 달라진다(backward 와 동일).
"""
from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, "src")

from coqstoq import Split, get_theorem_list  # noqa: E402

from data_management.dataset_file import DatasetFile  # noqa: E402
from data_management.sentence_db import SentenceDB  # noqa: E402

COQSTOQ = Path("CoqStoq")
DP = Path("raw-data/coq-dataset/data_points")
SDB = Path("raw-data/coq-dataset/sentences.db")
OUT = Path("data/curriculum/gold.json")
_WS = re.compile(r"\s+")


def norm(s: str) -> str:
    return _WS.sub(" ", s).strip()


def dp_path(t) -> Path | None:
    """data_point 파일 경로. 파일명은 repo prefix 를 쓴다(예: 'AbsInt-CompCert-common-Globalenvs.v')
    지만 t.project.dir_name 은 'compcert' 라 안 맞는다 → 경로 접미(common-Globalenvs.v)로 glob."""
    suffix = str(t.path).replace("/", "-")
    hits = glob.glob(str(DP / f"*{suffix}"))
    if not hits:
        return None
    # 접미가 여러 repo 에 있으면 project.dir_name 토큰이 파일명에 포함된 것 우선
    tok = t.project.dir_name.lower()
    exact = [h for h in hits if tok in Path(h).name.lower()]
    return Path((exact or hits)[0])


def gold_statement(t) -> str:
    f = COQSTOQ / "test-repos" / t.project.dir_name / t.path
    lines = f.read_text(errors="ignore").split("\n")
    return "\n".join(lines[t.theorem_start_pos.line : t.theorem_end_pos.line + 1]).strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default="compcert")
    ap.add_argument("--start", type=int, default=200)
    ap.add_argument("--num", type=int, default=40)
    ap.add_argument("--max_len", type=int, default=30, help="이보다 긴 gold 증명은 제외(하드코어).")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    thms = get_theorem_list(Split.TEST, COQSTOQ)
    proj = [i for i, t in enumerate(thms) if t.project.dir_name == args.project]
    targets = proj[args.start : args.start + args.num]
    print(f"{args.project}: 대상 {len(targets)}개 (전역 idx {targets[0]}..{targets[-1]})")

    sdb = SentenceDB.load(SDB)
    cache: dict[str, DatasetFile] = {}
    out: dict[str, dict] = {}
    skipped = []

    for idx in targets:
        t = thms[idx]
        p = dp_path(t)
        if p is None or not p.exists():
            skipped.append((idx, "data_point 없음"))
            continue
        key = p.name
        if key not in cache:
            cache[key] = DatasetFile.load(p, sdb)
        dset = cache[key]
        want = norm(gold_statement(t))
        match = [pr for pr in dset.proofs if norm(pr.theorem.term.text) == want]
        if not match:
            skipped.append((idx, "정리 매칭 실패"))
            continue
        steps = match[0].steps
        L = len(steps)
        if L < 2:
            skipped.append((idx, f"L={L} 너무 짧음"))
            continue
        if L > args.max_len:
            skipped.append((idx, f"L={L} 너무 김(하드코어)"))
            continue
        # 원문 그대로 (step.text 는 선행 개행/들여쓰기 포함) — 롤아웃 재생이 이 형식을 받는다.
        tactics = [s.step.text for s in steps]
        out[want] = {"tactics": tactics, "idx": idx, "L": L}

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1))
    Ls = [v["L"] for v in out.values()]
    print(f"저장: {args.out}  ({len(out)}개 정리)")
    if Ls:
        print(f"  gold 길이: 중앙값 {sorted(Ls)[len(Ls)//2]} 최소 {min(Ls)} 최대 {max(Ls)}")
    print(f"  제외 {len(skipped)}개: {skipped[:5]}")


if __name__ == "__main__":
    main()
