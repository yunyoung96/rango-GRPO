#!/usr/bin/env python3
"""LUFFY 결과 리포트 생성 → all_log/docs/LUFFY_RESULT.md.

집계:
  - gold 커버리지: gold.json 이 롤아웃 대상(cc[200:240], 40개) 중 몇 개를 덮나.
  - gold 주입 성공률: 롤아웃(luffy.jsonl)에서 gold 재생이 COMPLETE(reward=1) 로 실제 주입된 비율.
      · off_policy=True + reward>=1 인 attempt 를 가진 그룹 = 주입 성공.
      · 분모 2종: 전체 대상 40, gold 보유분(gold.json 교집합).
  - dead group 부활: on-policy(off_policy 아님) 전멸(dead)인데 gold 로 신호 생긴 그룹 수.
  - @20/@40 성능: luffy.log 의 smart_eval 결과(우리 rango 대비).
데이터 없으면 'pending' 으로 표기(파이프라인 대기 중)."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROLL = Path("data/grpo_rollouts/luffy.jsonl")
GOLD = Path("data/curriculum/gold.json")
LOG = Path("all_log/luffy.log")
OUT = Path("all_log/docs/LUFFY_RESULT.md")
N_TARGET = 40  # 롤아웃 대상 cc[200:240]


def gold_coverage() -> tuple[int, list[int]]:
    if not GOLD.exists():
        return 0, []
    d = json.load(open(GOLD))
    Ls = sorted(v["L"] for v in d.values())
    return len(d), Ls


def rollout_stats():
    """luffy.jsonl → (그룹수, 주입성공, on-policy dead, gold부활, gold길이리스트)."""
    if not ROLL.exists() or ROLL.stat().st_size == 0:
        return None
    g = [json.loads(l) for l in open(ROLL)]
    injected = dead = revived = 0
    glens = []
    for x in g:
        att = x["attempts"]
        gold = [a for a in att if a.get("off_policy")]
        on = [a for a in att if not a.get("off_policy")]
        has_gold = any(a["reward"] >= 1 for a in gold)
        if has_gold:
            injected += 1
            glens.append(sum(len(a["steps"]) for a in gold if a["reward"] >= 1))
        is_dead = bool(on) and all(a["reward"] < 1 for a in on)
        if is_dead:
            dead += 1
            if has_gold:
                revived += 1
    return {"groups": len(g), "injected": injected, "dead": dead,
            "revived": revived, "glens": glens}


def perf() -> list[str]:
    if not LOG.exists():
        return []
    rows = []
    for m in re.finditer(r"■ (rango-grpo-luffy) @(\d+): (\d+)/\d+ \| vs (우리rango \d+) \| (net [+\-]?\d+)",
                         LOG.read_text()):
        rows.append(f"@{m.group(2)}: {m.group(3)}/{m.group(2).replace('@','')} — {m.group(4)}, {m.group(5)}")
    # 구 포맷(published 포함) 대비용 fallback
    if not rows:
        for m in re.finditer(r"■ rango-grpo-luffy @(\d+): (\d+)/(\d+)", LOG.read_text()):
            rows.append(f"@{m.group(1)}: {m.group(2)}/{m.group(3)}")
    return rows


def main() -> None:
    cov, Ls = gold_coverage()
    rs = rollout_stats()
    pr = perf()
    L = []
    L.append("# LUFFY (2504.14945) 결과 — off-policy gold 주입\n")
    L.append("> 비교기준 = **우리 rango**(@20=11, @40=15). published 비교 안 함.\n")

    L.append("## 1. gold 커버리지 (빌드 단계)\n")
    if cov:
        med = Ls[len(Ls) // 2]
        L.append(f"- gold.json: **{cov}/{N_TARGET}** 정리 (나머지 {N_TARGET-cov}개는 gold 증명 L>30 하드코어라 제외)")
        L.append(f"- gold tactic 길이 L: 중앙값 {med}, 최소 {min(Ls)}, 최대 {max(Ls)}\n")
    else:
        L.append("- gold.json 없음 (빌드 전)\n")

    L.append("## 2. gold 주입 성공률 (롤아웃)\n")
    if rs is None:
        L.append("- ⏳ **pending** — 롤아웃(`luffy.jsonl`) 미생성. core 파이프라인(retry-prm→fix@180 선점) 이후 시작.\n")
    else:
        inj, grp = rs["injected"], rs["groups"]
        denom_gold = cov if cov else grp
        avg_len = (sum(rs["glens"]) / len(rs["glens"])) if rs["glens"] else 0
        # 롤아웃 완료 판정: 40개 다 찼거나, step-3 효과측정 라인이 로그에 있으면 완료
        #   (idx 440 등 gold 없는 하드코어는 그룹이 안 생겨 39에서 멈출 수 있음).
        step3_done = LOG.exists() and "gold 로 부활한 dead group" in LOG.read_text()
        done = grp >= N_TARGET or step3_done
        tag = "" if done else f" ⏳ **진행중** (현재 {grp}/{N_TARGET} 정리 롤아웃 완료 — 최종 아님)"
        L.append(f"- 롤아웃 완료: {grp}/{N_TARGET} 정리{tag}")
        L.append(f"- 주입 성공: **{inj}/{grp}** = {inj/max(grp,1):.0%} (완료분 대비)"
                 + ("" if done else "  ← 롤아웃 끝나면 40 기준으로 갱신"))
        L.append(f"- 재생된 gold 궤적 평균 길이: {avg_len:.1f} step")
        L.append(f"- **dead group 부활**: on-policy 전멸 그룹 {rs['dead']}개 중 gold 로 신호 생성 **{rs['revived']}/{rs['dead']}**")
        L.append(f"  · (기존 round-1: 혼합그룹 신호 11/41=27% → LUFFY 는 dead 에 정답 직접 주입)\n")

    L.append("## 3. 성능 (smart_eval @20→@40)\n")
    if pr:
        for r in pr:
            L.append(f"- {r}")
        L.append("")
    else:
        L.append("- ⏳ **pending** — 학습·평가 전.\n")

    from subprocess import run
    ts = run(["date", "+%Y-%m-%d %H:%M KST"], capture_output=True, text=True,
             env={"TZ": "Asia/Seoul", "PATH": "/usr/bin:/bin"}).stdout.strip()
    L.append(f"\n---\n_생성: {ts} · 소스: `luffy.jsonl`/`luffy.log` · 갱신기: `scripts/luffy_report.py`_")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(L))
    print(f"저장 → {OUT}")
    print("\n".join(L))


if __name__ == "__main__":
    main()
