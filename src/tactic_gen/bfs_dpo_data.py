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
    """같은 state에서 성공 tactic(chosen) × 실패 tactic(rejected)의 곱 쌍.
    한 state에 성공·실패 둘 다 있어야 쌍 생성."""
    pairs = []
    for n in nodes:
        chosen, rejected = [], []
        for t in n.get("tactics", []):
            if t.get("leads_to_success"):
                chosen.append(t["tactic"])
            elif t.get("result") == "INVALID" or t.get("leads_to_success") is False:
                rejected.append(t["tactic"])
        st = _state(n)
        for c in chosen:
            for r in rejected:
                if c != r:
                    pairs.append({"state": st, "chosen": c, "rejected": r})
    return pairs


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
