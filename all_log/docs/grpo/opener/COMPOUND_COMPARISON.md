# opener: compound retrieval 유무 비교 (7B)

작성 2026-08-01. 같은 7B opener를 **compound 인자 후보 + retrieval 입력** 유무로 비교.

## 두 버전
| | `7B_wo_compound/` | `7B_w_compound/` |
|---|---|---|
| opener | opener-7b-sub (goal만) | **opener-7b-tac** (goal + compound후보 + lemma/proof retrieval) |
| 생성 | whole-opening | **tactic 단위 + NMD** |
| 롤아웃 | combo_subgoal_opener.jsonl | opener_tac_pipe.jsonl |
| executor | subgoal 모델 | subgoal 모델 |

## opener 자체 품질 (gold 인자 일치)
| | wo_compound (opener-sub) | **w_compound (opener-tac)** |
|---|---|---|
| **인자까지 정확** | 52% | **92%** |
| 종류 일치 | 73% | 95% |
| NMD 인식 | — | 92% |
→ **compound 후보+retrieval 입력이 인자 정확도를 52%→92%로 대폭 개선.** (님 지적 "인자 틀림" 해결)

## 그런데 롤아웃 성공률은 동일 (parity)
| | wo_compound | w_compound |
|---|---|---|
| 성공(≥1) | 32% | 32% |
| mixed | 27% | 28% |
| 실패(dead) | 68% | 68% |
| attempt | 17.0% | 16.8% |
→ **opener 품질을 52→92%로 올려도 성공률·mixed 안 변함.**

## 왜? (SOLVED/FAILED 예시에서 확인)
- **SOLVED.md**: 두 버전 다 gold 경로 짧거나 automation으로 닫힘. opener가 열고 rango가 마무리.
- **FAILED.md**: opener가 (특히 w_compound는 인자까지) **잘 열어도**, rango가 **닫기(closing)에서 실패** — gold의 핵심 lemma/전략을 못 따라감.
- 실패 위치: **closing 75% vs opening 25%**.

## 결론
**"opener는 잘했는데 닫기가 안 됨"** — mixed 낮음의 정확한 원인.
- 열기(opener): wo 52% → w **92%** (크게 개선)
- 닫기(executor): 여전히 벽 → 성공률 parity (32%)
- = 열기는 병목이 아니고 **닫기(1.3B capacity)가 벽**. compound retrieval로 열기를 완벽히 해도 무효.

각 폴더의 `SOLVED.md`/`FAILED.md`에서 GOLD 전문 vs opener+rango 궤적(step별 validity)을 직접 대조 가능.

관련: [[OPENER_TAC]] · [[README]] · `7B_wo_compound/ANALYSIS.md`
