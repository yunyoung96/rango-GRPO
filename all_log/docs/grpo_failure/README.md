# grpo_failure — GRPO 실패 원인 분석 (lr별로 분리)

> ★ **규칙: 실패 데이터 분석 md는 파일명에 그 실험의 lr을 반드시 넣는다.** lr별로 따로 만들어 비교.

## 파일 구성

### lr-specific (실험 데이터 기반, lr이 이름에)
- **`MIXED_FAILURE_ANALYSIS_lr3e-4.md`** — lr=3e-4 실험(`tst1000tr5091_bc_lr3e-4_...`, b000~b039 롤아웃 36 gz) 기반.
  probe 29→30 정체, tactic별 성공/실패 INVALID, apply·rewrite 원인분해(R1/H/E/X), hallucination vs 틀린인자.
- **`TACTIC_FAILURE_EXAMPLES_lr3e-4.md`** — 같은 lr3e-4 롤아웃에서 **apply/eapply/rewrite/destruct 실패 실사례**를 goal+lemma 문장까지 보여줌(예시 풍부). FLX↔FLT 혼동, combine↔combine_l 매칭실패, destruct 구조오류 등.
- **`MIXED_FAILURE_ANALYSIS_lr1e-3.md`** — *(예정)* lr=1e-3 실험 기반. 위와 **같은 항목을 뽑아 lr3e-4와 비교**.
- *(향후 lr 바뀌면 `MIXED_FAILURE_ANALYSIS_lr<값>.md` 로 추가)*

### lr-independent (설계/논문, lr 무관)
- **`TYPE_LEARNING_RESEARCH.md`** — 타입 학습 논문 조사 + 코드베이스 적응 설계(방향 A retriever / B process reward). lr에 안 묶임(단 근거 데이터는 lr=3e-4).

## lr별 비교 방법 (앞으로)
각 lr 실험이 끝나면 `MIXED_FAILURE_ANALYSIS_lr<값>.md`를 같은 틀로 만들고, 핵심 지표를 나란히 비교:
| 비교 지표 | lr3e-4 | lr1e-3 | … |
|---|---|---|---|
| probe 최종(baseline 대비) | 30 (+1) | ? | |
| apply 실패中 거부율 추세 | 62→65%(불변) | ? | |
| R1/E/X 비율 | 33/22/36% | ? | |
| KL·max_ρ 범위 | 0.011~0.033 / 4~56 | ? | |

> 데이터 출처: 각 실험의 롤아웃 gz `data/grpo_rollouts/${TAG}_bc_lr<값>_..._roll.jsonl.gz` + 로그 `all_log/${TAG}_bc_lr<값>_....log`. 롤아웃은 `RECORD_ERROR=1` 기본이라 INVALID의 `coq_error`가 저장됨 → `scripts/classify_rollout_errors.py`로 원인(없는참조 vs 타입불일치) 확정.
