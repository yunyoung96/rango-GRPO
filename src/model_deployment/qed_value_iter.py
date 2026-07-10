"""QEDCartographer full — 진짜 반복 Bellman value-iteration(부트스트랩) + closed-form.

논문 reward-free value iteration:
  V(s) = γ · (backup over children)   ;  QED(닫힘) 노드 = 1, 막다른 노드 = 0.
  OR(tactic 선택) 노드: max_a.  AND(subgoal 집합) 노드: product/sum/min(=ablation).

두 학습 모드:
  · closed-form: 성공경로 수렴값 V*=γ^dist에 직접 회귀(train_qed_value.py 방식).
  · bootstrap: 덤프의 AND-OR 엣지(node_id/children)로 V를 반복 갱신 → 회귀 타깃.
    (엣지 있는 새 덤프 필요; 없으면 closed-form로 폴백.)

ablation 축: mode(closed-form/bootstrap), gamma, backup(product/sum/min).
학습 산출 blob은 QEDValuePredictor 호환({enc_args, state_dict}).
★순수 PyTorch. OCaml 무관.
"""
from __future__ import annotations

import glob
import json
from pathlib import Path
from typing import Optional


def value_iteration(
    nodes_by_file: list[list[dict]],
    gamma: float,
    backup: str = "product",
    iters: int = 50,
) -> dict[str, float]:
    """엣지 구조(node_id/children/solved) 덤프에 반복 Bellman VI → goal→V* 타깃.
    각 파일(=한 정리 탐색트리) 내에서 node_id로 그래프 구성.
    OR 노드(자식=tactic 확장)는 max, 리프 solved=1, dead=0."""
    goal_val: dict[str, float] = {}
    for nodes in nodes_by_file:
        if not nodes or "node_id" not in nodes[0]:
            continue  # 엣지 없는 구 덤프 → 스킵(closed-form이 처리)
        by_id = {n["node_id"]: n for n in nodes}
        V = {nid: (1.0 if n.get("solved") else 0.0) for nid, n in by_id.items()}
        for _ in range(iters):
            newV = {}
            for nid, n in by_id.items():
                if n.get("solved"):
                    newV[nid] = 1.0
                    continue
                kids = [c for c in n.get("children", []) if c in by_id]
                if not kids:
                    newV[nid] = 0.0
                    continue
                # 자식들은 이 tactic 적용 후의 state(들). OR: 최선의 tactic-child 선택.
                cand = [gamma * V[c] for c in kids]
                newV[nid] = max(cand) if cand else 0.0
            if all(abs(newV[k] - V[k]) < 1e-6 for k in V):
                V = newV
                break
            V = newV
        for nid, n in by_id.items():
            g = n.get("goal")
            if g:
                for sub in g.split("\n===\n"):
                    sub = sub.strip()
                    if sub:
                        goal_val[sub] = max(goal_val.get(sub, 0.0), V[nid])
    return goal_val


def closed_form_targets(
    nodes_by_file: list[list[dict]], gamma: float
) -> dict[str, float]:
    """V* = γ^dist (label=1, dist>=0), 아니면 0. per-subgoal 분해."""
    goal_val: dict[str, float] = {}
    for nodes in nodes_by_file:
        for r in nodes:
            g = r.get("goal")
            if not g:
                continue
            dist = r.get("dist", -1)
            tgt = (gamma ** dist) if (r.get("label") == 1 and dist >= 0) else 0.0
            for sub in g.split("\n===\n"):
                sub = sub.strip()
                if sub:
                    goal_val[sub] = max(goal_val.get(sub, 0.0), tgt)
    return goal_val


def load_nodes_by_file(tree_glob: str) -> list[list[dict]]:
    out = []
    for path in glob.glob(tree_glob):
        nodes = []
        for line in Path(path).read_text(errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                nodes.append(json.loads(line))
            except Exception:
                continue
        if nodes:
            out.append(nodes)
    return out


def build_targets(tree_glob: str, gamma: float, mode: str, backup: str) -> dict[str, float]:
    """mode=bootstrap면 엣지 있는 파일은 VI, 없는 파일은 closed-form 폴백 병합."""
    nbf = load_nodes_by_file(tree_glob)
    if mode == "closed-form":
        return closed_form_targets(nbf, gamma)
    vi = value_iteration(nbf, gamma, backup)
    cf = closed_form_targets(nbf, gamma)
    # bootstrap 우선, 엣지 없어 VI가 못 만든 goal은 closed-form로 채움.
    merged = dict(cf)
    merged.update(vi)
    return merged
