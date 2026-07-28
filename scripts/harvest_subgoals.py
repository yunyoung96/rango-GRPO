#!/usr/bin/env python3
"""닫힌 subgoal 재활용 (subgoal RFT / HER-for-provers 계열, arXiv:2112.10664).

GRPO 롤아웃에서 **정리 전체는 못 풀었지만(dead group, advantage=0)** 중간에 destruct/case/
induction 등으로 생긴 subgoal 이 완전히 닫힌 경우, 그 (subgoal-state, 닫은 tactic들)을 추출한다.

★ 왜 covariate shift 가 없나:
  - 이 subgoal 은 **모델 자신이 도달한 state**(gold 처럼 외부 분포 아님)
  - **모델 자신이 생성**한 tactic 으로
  - **Coq 가 롤아웃 중 실제로 닫아준**(재검증 불필요 — 로그가 곧 Coq 세션 기록)
  → 순수 on-policy RFT. gold 계열(LUFFY/backward)의 실패원인을 구조적으로 회피.

★ PRM(union +0)과의 차이: PRM 은 '에러 안 낸 tactic' 을 다 보상(실패 subtree 포함).
  여기는 **완전히 닫힌 subtree 의 tactic 만** — 훨씬 선별적.

추출 원리(선형 Coq 스크립트): Coq 는 goal 1(focused)에 tactic 적용. proof_state 는 열린 goal 을
'[GOAL]' 로 구분 → goal 수 g_i = [GOAL] 개수 + 1. step i 의 focused goal F_i(g_i≥2 인 진짜 subgoal)
는, 첫 j>i 에서 g_j = g_i-1 이 되면 서브트리 완전 종결 → [i..j-1] 이 F_i 의 증명.

출력: rollout jsonl 포맷(각 group=theorem, attempts=[{steps:[원본 step], reward:1}]).
  reward=1 이므로 grpo_train.py --sft 경로가 그대로 학습(추가 배선 불필요).
"""
from __future__ import annotations
import argparse, json
from pathlib import Path


def ngoals(ps: str) -> int:
    if not ps or not ps.strip():
        return 0
    return ps.count("[GOAL]") + 1


def focused(ps: str) -> str:
    return ps.split("[GOAL]")[0].strip() if ps else ""


def clean_counts(steps):
    """파싱 잡음(빈 proof_state=0)은 직전값 유지."""
    out, prev = [], 1
    for s in steps:
        c = ngoals(s.get("example", {}).get("proof_state", ""))
        out.append(c if c > 0 else prev)
        prev = out[-1]
    return out


def harvest_attempt(steps, max_goals=50):
    """한 시도에서 (start_index, end_index) 닫힌-subgoal subtree 목록."""
    counts = clean_counts(steps)
    spans = []
    for i in range(len(steps)):
        gi = counts[i]
        if gi < 2 or gi > max_goals:       # 진짜 subgoal, 병적 폭발 제외
            continue
        j = None
        for k in range(i + 1, len(steps)):
            if counts[k] == gi - 1:
                j = k
                break
            if counts[k] < gi - 1:         # 다른 subtree 로 뚫림 → 이 subgoal 서브트리 아님
                break
        if j is not None:
            spans.append((i, j))
    return spans


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rollouts", required=True, help="입력 GRPO 롤아웃 jsonl")
    ap.add_argument("--out", required=True, help="출력 subgoal-RFT jsonl")
    ap.add_argument("--min_tactics", type=int, default=1, help="이 수 미만 tactic 증명은 제외(1=전부)")
    ap.add_argument("--dead_only", action="store_true",
                    help="정리 전체 실패(dead group) 시도에서만 추출(GRPO 가 버리는 신호에 집중)")
    ap.add_argument("--max_goals", type=int, default=50)
    args = ap.parse_args()

    groups = [json.loads(l) for l in Path(args.rollouts).read_text().splitlines() if l.strip()]
    out_groups = []
    seen = set()          # (focused_state, tactic_tuple) dedup
    n_pairs = n_dead = n_steps = 0

    for x in groups:
        onp = [a for a in x["attempts"] if a.get("steps") and not a.get("off_policy")]
        if not onp:
            continue
        is_dead = all(a["reward"] < 1 for a in onp)
        if args.dead_only and not is_dead:
            continue
        subproofs = []
        for a in onp:
            steps = a["steps"]
            for (i, j) in harvest_attempt(steps, args.max_goals):
                sub = steps[i:j]
                tacs = tuple(s.get("tactic", "") for s in sub)
                fs = focused(sub[0].get("example", {}).get("proof_state", ""))
                if not fs or not all(tacs) or len(tacs) < args.min_tactics:
                    continue
                key = (fs, tacs)
                if key in seen:
                    continue
                seen.add(key)
                # 원본 step 을 그대로(example+tactic 보존), reward=1 로 표시
                subproofs.append({"steps": [dict(s) for s in sub], "reward": 1,
                                  "subgoal": True, "from_dead": is_dead})
                n_pairs += 1
                n_steps += len(sub)
                if is_dead:
                    n_dead += 1
        if subproofs:
            out_groups.append({"theorem": x["theorem"], "start": "subgoal",
                               "attempts": subproofs})

    with open(args.out, "w") as f:
        for gobj in out_groups:
            f.write(json.dumps(gobj, ensure_ascii=False) + "\n")

    print(f"[harvest] 입력 {len(groups)}그룹 → subgoal-증명 {n_pairs}개 "
          f"(dead group 출신 {n_dead}, 총 {n_steps} step) → {len(out_groups)}그룹 저장")
    print(f"          {args.out}")


if __name__ == "__main__":
    main()
