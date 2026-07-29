"""BFS-Prover expert-iteration + DPO용 데이터 추출.

BFS 탐색 트리 덤프(노드=state, 시도 tactic들 + 각 결과)에서:
  · SFT 데이터(expert-iteration): 성공 증명 경로의 (state, tactic) 쌍.
  · DPO 선호쌍: 같은 state에서 성공경로 tactic(chosen) vs 실패/막다른 tactic(rejected).

트리 덤프 레코드 포맷(줄=노드):
  {"state_example": <LmExample json 또는 prompt str>, "on_success_path": bool,
   "tactics": [{"tactic": str, "result": "COMPLETE"|"VALID"|"INVALID", "leads_to_success": bool}]}
★OCaml 무관.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _state(node: dict):
    return node.get("state_example", node.get("prompt"))


def extract_sft(nodes: list[dict]) -> list[dict]:
    """성공 경로의 (state, tactic) → SFT 예제. leads_to_success인 tactic만."""
    out = []
    for n in nodes:
        for t in n.get("tactics", []):
            if t.get("leads_to_success"):
                out.append({"state": _state(n), "tactic": t["tactic"]})
    return out


def extract_dpo_pairs(nodes: list[dict]) -> list[dict]:
    """논문(2502.03438) 그대로: proof path 위 state s에서 (a_w=경로 tactic, a_l=컴파일에러 tactic).
    chosen = leads_to_success tactic, rejected = **컴파일러 에러(INVALID)만**.
    (valid-but-off-path tactic은 negative로 쓰지 않음 — 논문은 'Lean compiler error' 에러만 negative.)"""
    pairs = []
    for n in nodes:
        chosen, rejected = [], []
        for t in n.get("tactics", []):
            if t.get("leads_to_success"):
                chosen.append(t["tactic"])
            elif t.get("result") == "INVALID":          # 컴파일러 에러만 negative
                rejected.append(t["tactic"])
        st = _state(n)
        for c in chosen:
            for r in rejected:
                if c != r:
                    pairs.append({"state": st, "chosen": c, "rejected": r})
    return pairs


def extract_sft_rollout(nodes: list[dict]) -> list[dict]:
    """성공경로 (state, tactic) → grpo_train --sft 소비용 rollout-group 포맷.
    각 성공 (state,tactic)=1 그룹 {theorem, attempts:[{reward:1.0, steps:[{example|prompt, tactic}]}]}.
    (grpo_train._flatten_prompt: dict state→example(collate), str→prompt.)"""
    groups = []
    for i, n in enumerate(nodes):
        st = _state(n)
        if st is None:
            continue
        key = "example" if isinstance(st, dict) else "prompt"
        for t in n.get("tactics", []):
            if t.get("leads_to_success"):
                groups.append({
                    "theorem": f"bfs-sft-{i}",
                    "attempts": [{"reward": 1.0, "steps": [{key: st, "tactic": t["tactic"]}]}],
                })
    return groups


def load_trees(path: Path) -> list[dict]:
    nodes = []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if line:
            nodes.append(json.loads(line))
    return nodes


def write_jsonl(items: list[Any], path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")


def _append_jsonl(items: list[Any], path: Path) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    return len(items)


def main():
    """bash 오케스트레이터용 CLI.
    extract <trace> <cum_sft_jsonl(append)> <pairs_out>: trace→SFT(rollout포맷,누적append)+DPO쌍.
    hard <summary.json> <all_idx.txt> <hard_out.txt>: all에서 beam-solved(success) 제거→hard idx.
    """
    import sys
    cmd = sys.argv[1]
    if cmd == "extract":
        trace, cum_sft, pairs_out = sys.argv[2], sys.argv[3], sys.argv[4]
        nodes = load_trees(Path(trace)) if Path(trace).exists() else []
        sft = extract_sft_rollout(nodes)
        pairs = extract_dpo_pairs(nodes)
        na = _append_jsonl(sft, Path(cum_sft))
        write_jsonl(pairs, Path(pairs_out))
        print(f"[bfs-data] SFT그룹 +{na}(누적→{cum_sft}) · DPO쌍 {len(pairs)}(→{pairs_out}) · 노드 {len(nodes)}")
    elif cmd == "hard":
        summary, all_idx, hard_out = sys.argv[2], sys.argv[3], sys.argv[4]
        alls = [int(x) for x in Path(all_idx).read_text().split()]
        solved = set()
        if Path(summary).exists():
            res = json.loads(Path(summary).read_text()).get("results", [])
            solved = {r["idx"] for r in res if r.get("success")}
        hard = [i for i in alls if i not in solved]
        Path(hard_out).write_text("\n".join(map(str, hard)) + "\n")
        print(f"[bfs-data] beam-solved {len(solved)}/{len(alls)} 제외 → hard {len(hard)}정리 (→{hard_out})")
    else:
        raise SystemExit(f"unknown cmd {cmd}")


if __name__ == "__main__":
    main()
