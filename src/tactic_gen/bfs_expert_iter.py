#!/usr/bin/env python3
"""BFS-Prover full 학습 오케스트레이션 — expert-iteration(+DPO) 라운드 루프.

BFS-Prover(2502.03438) 학습 파이프라인:
  라운드 r:
    1) 현재 정책으로 train 정리들에 BFS 탐색(trace_out에 트리 덤프).
    2) trace → SFT 데이터(성공경로 (state,tactic)) + DPO 선호쌍(성공 vs 실패 tactic).
    3) SFT fine-tune(expert-iter) → 이어서 DPO(dpo_train) → 새 adapter.
    4) 새 adapter로 다음 라운드.

탐색·학습이 GPU/Coq/서버 필요 → 실제 구동은 평가/실행 단계. 이 스크립트는 라운드 오케스트레이션
(subprocess로 run_all 탐색 + 추출 + 학습 호출)을 담당. 데이터 추출은 bfs_dpo_data 사용.
★OCaml 무관.
"""
from __future__ import annotations

import argparse
import glob
import subprocess
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tactic_gen.bfs_dpo_data import (  # noqa: E402
    load_trees, extract_sft, extract_dpo_pairs, write_jsonl,
)


def run_search(round_dir: Path, num: int, start: int, timeout: int) -> Path:
    """bfs-prover(trace on)로 train 정리 탐색. trace_out jsonl 경로 반환."""
    trace = round_dir / "trees.jsonl"
    # run_thm의 trace_out을 켜려면 alias 'bfs-prover-trace'가 필요(run_thm에 등록).
    cmd = [
        "python3", "scripts/run_all.py", "--alias", "bfs-prover-trace",
        "--num", str(num), "--start", str(start),
        "--timeout", str(timeout), "--workers", "1",
        "--description", f"bfs expert-iter round trace → {trace}",
    ]
    print("[expert-iter] 탐색:", " ".join(cmd))
    subprocess.run(cmd, check=False)
    return trace


def extract_round(trace_path: Path, round_dir: Path) -> tuple[Path, Path]:
    nodes = load_trees(trace_path) if trace_path.exists() else []
    sft = extract_sft(nodes)
    pairs = extract_dpo_pairs(nodes)
    sft_path = round_dir / "sft.jsonl"
    pair_path = round_dir / "dpo_pairs.jsonl"
    write_jsonl(sft, sft_path)
    write_jsonl(pairs, pair_path)
    print(f"[expert-iter] 추출: SFT {len(sft)}개, DPO쌍 {len(pairs)}개")
    return sft_path, pair_path


def run_dpo(pair_path: Path, model_name: str, in_adapter: str, out_adapter: Path,
            collator_conf: str) -> None:
    cmd = [
        "python3", "src/tactic_gen/dpo_train.py",
        "--pairs", str(pair_path), "--model_name", model_name,
        "--save_dir", str(out_adapter), "--collator_conf", collator_conf,
        "--epochs", "1",
    ]
    if in_adapter:
        cmd += ["--init_adapter", in_adapter]
    print("[expert-iter] DPO 학습:", " ".join(cmd))
    subprocess.run(cmd, check=False)


def main():
    ap = argparse.ArgumentParser(description="BFS-Prover expert-iteration 라운드")
    ap.add_argument("--rounds", type=int, default=2)
    ap.add_argument("--num", type=int, default=40, help="train 정리 수")
    ap.add_argument("--start", type=int, default=200, help="eval 분리 오프셋")
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--model_name", required=True)
    ap.add_argument("--init_adapter", default="", help="rango 시작 adapter")
    ap.add_argument("--collator_conf", required=True)
    ap.add_argument("--work", default="data/bfs_expert_iter")
    args = ap.parse_args()

    work = Path(args.work)
    adapter = args.init_adapter
    for r in range(args.rounds):
        rd = work / f"round{r}"
        rd.mkdir(parents=True, exist_ok=True)
        print(f"\n===== expert-iter round {r} (adapter={adapter or 'rango-base'}) =====")
        trace = run_search(rd, args.num, args.start, args.timeout)
        sft_path, pair_path = extract_round(trace, rd)
        out_adapter = rd / "adapter"
        # (SFT 단계는 train_decoder 재사용 가능 — 여기선 DPO 위주로 데모. 확장 시 SFT 추가.)
        run_dpo(pair_path, args.model_name, adapter, out_adapter, args.collator_conf)
        adapter = str(out_adapter)
    print(f"\n[expert-iter] 완료. 최종 adapter: {adapter}")


if __name__ == "__main__":
    main()
