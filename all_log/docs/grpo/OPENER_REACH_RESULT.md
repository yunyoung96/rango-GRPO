# opener 도달성(§10 opener판)
target = gold s1 진입상태 287개 (그룹 307)  ← cascade s1 closer가 배운 상태

롤아웃                                   그룹  reach(exact)    reach(ws완화)
------------------------------------------------------------------------
rango-grpo-cascade-s0                285   48/287  16.7%   48/287  16.7%
reach_opener_every                   277   48/287  16.7%   48/287  16.7%
opener_once_pipe2                    288   43/287  15.0%   43/287  15.0%

해석: opener-EVERY(재귀) reach가 executor(cascade-s0 ≈16.7%)보다 확실히 높으면
  → opener가 gold leaf에 더 잘 도달 → per-state opener 재학습 가치 큼.
  ※ 롤아웃마다 정리집합·그룹수 다르면 절대치는 대략치(그룹수 적으면 reach 하향편향).

## 판정 (값싼 도달성 측정, 2026-08-02)

**재귀 opener-EVERY(once-v2) reach = 16.7% = executor(cascade-s0) 16.7%. 동률.**

→ **현재 opener는 재귀로 돌려도 gold s1 leaf 상태에 더 잘 도달 못 함.** root-anchored 학습이라 깊이서 gold 분해를 재현 못 하고, 자기 방식으로 열어 executor와 같은 상태집합(48개)만 방문.

### opener+cascade 아이디어에의 함의
- 대전제("재귀 opener가 gold s1로 데려가 cascade의 orphan 닫기스킬 살림")가 **현재 opener로는 거짓** — s1 도달 16.7%라 cascade 닫기스킬 83% 여전히 고아.
- 즉 **opener+cascade 조합은 현재 opener로 이득 없음.** 유일한 희망 = per-state opener 재학습이 도달률을 올리는 것 → 큰 베팅, 값싼 검증 불가.

### 세 실험 수렴 (2026-08-02)
1. once-v2 @600s 37.0%(top-tier, SFT→GRPO 못 넘음) — 상승은 도달개선 아님(reach 16.7% 동일) → GRPO+compute 덕.
2. multi-turn: 국소 유효성 94% 재샘플복구 = 병목 아님.
3. 도달성: 재귀 opener도 16.7% = executor → 도달을 못 고침.

→ **벽 = gold 분해의 선택/도달**(어떤 destruct/induction). 1.3B도 7B-root-opener도 못 함. memory "32B planner 가치=선택"과 일치.
→ 유망 방향 = **검색으로 완전체 증명을 찾아 통째 학습(expert-iteration, p_reach=1)** = 도달+닫기 end-to-end.

관련: [[OPENER_ONCE_COMP]] · SUBGOAL_PAPER_ASSESSMENT §10 · [[MULTITURN_PROBE_RESULT]]
