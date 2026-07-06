# 알고리즘 개선 실험 저널 (Rango retrieval 성능 향상)

> 목표: 단순 retrieval 기반 Rango의 낮은 성능을 **search / backtracking / retrieval-aware(선택적 RAG) / hammer**로 끌어올린다. (강화학습 미사용)
> 개발 브랜치: `algo-dev` → 괜찮으면 `master`로 merge.
> 벤치마크: CompCert test **앞 20개** 고정 (idx 0,2,4,5,6,8,9,10,11,12,15,19,20,21,22,25,26,27,28,29).
> 각 실험은 새 alias + `run_all --description`으로 `all_results/<ts>/summary.json`에 아이디어를 기록.
> 이 저널은 반복 과정(가설 → 실험 → 결과 → 다음 아이디어)을 누적 기록한다.

## 환경 메모
- GPU: RTX 6000 Ada 48GB (유휴 확인).
- 모델: `models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500` (rango).
- **CoqHammer 미설치** (opam에 coq-hammer/ATP 없음) → hammer 계열은 설치 선행 필요. 우선 backtracking + 선택적 RAG부터.
- 이미 존재하는 alias: `rango`(StraightLine), `rango-best-beam`/`rango-best-rand`(ClassicalSearch = best-first + backtracking).

## 실행 규칙
- 실험은 **순차** 실행 (동시에 여러 개 GPU 점유 금지).
- 공정 비교: 같은 (데이터셋, timeout)에서 baseline `rango`를 한 번 고정 측정 후 재사용.
- "가망 있음" 판정 → timeout 10분 + 데이터 40개로 확대 재실험.

---

## 진행 상황 (최신이 위)

### baseline 확정 (사용자 지정)
- **baseline = `all_results/20260701-061839` (M0@600s, 대실행)**. 앞-20개 기준 **M0 성공 11/20**: [2,5,6,9,10,11,12,19,26,28,29].
- 모든 방법(M1~)은 **동일 조건 600s/20개**로 이 baseline과 직접 비교.
- 참고: idx 10은 600s 성공/300s 실패 → timeout이 결과에 영향(그래서 300s 스크리닝 폐기, 600s로 통일).
- (M0@300 재실행 20260705-062926은 중단·폐기; 부분결과만 참고용 잔존.)

### [완료] Iter 1 — M1 backtracking @600s/20 → ❌ 하락 (8/20, 순증감 -3)
- 결과: `rango-best-beam` **8/20** vs baseline **11/20**. 신규 해결 0, 회귀 3 [2,5,11]. (report: all_results/20260705-072250/analysis.md)
- 해석: best-first(max_branch=4, beam)이 **너무 좁게** 탐색 → straight-line의 "다양한 재시작이 우연히 찾던" 케이스(idx 2 = baseline '늦은 성공: 우연에 가까운 발견')를 놓침. 신규 해결이 0이라 backtracking의 prefix 보존 이점이 좁은 분기에 가려짐.
- 결정: **merge 안 함**. 교훈 → 분기 폭 확대 필요(lit A1 GPT-f는 e≈32). M2는 memory + **max_branch 4→8**로 넓혀 재도전.

### [완료] Iter 2 — M2 search-memory (memory+분기8) → ❌ 하락 (8/20, 순증감 -3)
- `rango-mem` **8/20** vs baseline 11/20. 신규 해결 **[27]**(baseline+rango.json 둘 다 실패한 것!), 회귀 [2,10,11,12]. (report: all_results/20260705-082853/analysis.md)
- 해석: classical 계열은 memory·분기확대로도 straight-line 미달. 단 **idx 27처럼 straight-line이 못 찾는 걸 찾음** → 두 방식이 상보적(portfolio 가능성). 하지만 전면 대체로는 하락.
- 결정: merge 안 함. **결론: 이후 retrieval 개선은 강한 baseline(straight-line) 위에 얹는다.** classical 단독 탐색 노선 중단.

### [진행중] Iter 3 — M3 rango-align (straight-line + aligned next-tactic 힌트) @600/20
- 가설: STRATEGY_DIVERGE(36%) = retrieval된 sibling을 모델이 안 따라감 → sibling의 **매칭 중간상태 다음 tactic**을 프롬프트 최상단에 주입해 salient하게.
- 구현: GeneralFormatterConf.align_hint; get_similar_proof_steps top-1의 ref_step_idx→tactic. 자명(Proof./불릿) 제외. **주석(* *) 대신 bare tactic**(모델이 따라 해도 유효 Coq). conf_utils formatter 재구성 시 align_hint 보존 버그 수정.
- 검증: 스모크 idx6 성공, idx22 실질 hint(`red; intro; subst a y.`) 주입, Unterminated comment 0(baseline과 동일).
- 상태: 10:45 UTC 실행 시작(detach). 완료 후 make_report→baseline(11/20) 대비 판정.
- 가설: SEARCH_THRASH(47%)는 straight-line 재시작 낭비 → best-first backtracking(`rango-best-beam`)이 유효 prefix 보존해 성공률↑.
- 실행: `setsid`로 detach, `all_log/run_method.sh rango-best-beam 600`. 로그 all_log/m1_run.log. 07:22 UTC 시작.
- 완료 후 M0@600(11/20)과 성공 개수 비교→기록. ≥이면 master merge 검토, 그리고 M2(rango-mem) 동일조건 실행.

### [완료] Iter 0 — 파이프라인 스모크 테스트
- rango(StraightLine): idx 6 SUCCESS 6.6s. rango-best-beam(ClassicalSearch/backtracking): idx 6 SUCCESS. `--timeout` 오버라이드 정상.
- 결론: 두 실행 경로 모두 정상 → Iter 1 진행.

### [완료] Iter 3 — M3 rango-align → ❌ 하락 (9/20, 순증감 -2)
- 회귀 [10,11], 신규 0 (단 rango.json 대비 idx2 신규). align 힌트가 baseline 못 넘음. merge 안 함.

### [진행중] Iter 4 — M4' rango-apply (사용자 요청: 좋은 premise면 apply 강제)
- 진단(idx 840 loadv_rule): `load_rule`이 premise/proof retrieval **Top1**로 완벽 검색됐으나, 모델은 수백 시도 중 `eapply load_rule`를 2~3회만 시도(정답=`exploit load_rule`). → 좋은 premise를 찾고도 apply/exploit를 거의 안 씀.
- 방법: formatter가 top premise 이름 추출→stash, get_recs가 `exploit/eapply/apply <premise>` 강제 후보를 next_tactic_list에 append. classical(use_memo)이 이를 시도. alias `rango-apply`.
- 검증(idx840 스모크): `load_rule` 강제 추출 → `exploit load_rule; eauto.`/`eapply load_rule; eauto.`/`apply load_rule.` 실제 시도 확인(이전엔 거의 안 씀). 메커니즘 완성.
- 실행: first-20 @600 detach. 완료 후 baseline(11/20) 대비 판정 + idx840 별도 600s 검증 예정.

### [오버나이트] 자동 연쇄 드라이버 가동 (14:30 UTC~)
- 사용자 취침 → 무개입 대량 실험. `all_log/overnight.sh`가 queue.txt를 순차 처리(스모크→run_all 300s/20→make_report), 깨진 alias 스킵, done.txt resume, queue 추가 시 픽업.
- 초기 큐 7개: rango(baseline@300), rango-apply, rango-alignapply, rango-mem, rango-mem-wide(branch16), rango-best-beam, rango-align.
- 300s 스크리닝으로 처리량↑. 유망하면 600s/확대 확인. 완료마다 analysis.md.
- 매 wakeup: 진행/결과 보고 + 큐에 새 방법 append(변형·조합·신규구현) + 드라이버 죽으면 재시작.

### [오버나이트 중간] 300s 스크리닝 결과 (baseline@600=11/20, baseline@300=10/20)
| 방법 | 성공@300 | vs baseline@600 |
|------|---------|----------------|
| rango(baseline@300) | 10/20 | -1 (idx10 timeout) |
| rango-apply | 8/20 | -3 (신규[27], 회귀[2,10,11,12]) |
- 패턴 확정: **classical 계열 ~8/20 < straight-line ~10-11/20.** memo/apply-forcing로도 못 넘음.
- rango-apply의 premise-apply는 idx840류(premise Top1 강함+model 미적용)를 겨냥하나 first-20엔 그런 케이스 부재 → 이점 안 드러남. (idx840 별도 검증 필요.)
- **돌파 방향**: (a) 좋은 아이디어(apply/align)를 straight-line에 얹기, (b) RL value-guided로 classical 순서 교정, (c) portfolio(straight∪classical union=12). 큐 소진 후 공유파일 자유로울 때 구현.

### [오버나이트] 300s 스크리닝 전체 결과 (baseline@300=10, @600=11)
| 방법 | 성공@300 | 신규 |
|------|---------|------|
| rango (baseline) | 10 | - |
| rango-apply (classical+force) | 8 | [27] |
| rango-alignapply | 9 | [27] |
| rango-mem | 8 | [27] |
| rango-mem-wide(br16) | 8 | - |
| rango-best-beam | 8 | - |
| rango-align | 8 | - |
| rango-apply-sl (straight+force) | 9 | [27] |
- **핵심 발견**: 어떤 inference tweak도 baseline(straight-line) 못 넘음. 공통적으로 **idx27만 신규**(classical/forcing이 찾는 것)이고 straight-line 성공 2-3개 회귀. straight-line의 다양한 재시작이 이 20-set에서 매우 강함.
- 남은 희망: **portfolio**(straight∪classical=union). 실패 시 RL value-guided이 마지막 카드.

---
## ★ 결론 (오버나이트 최종, 2026-07-06 아침)

### 🎉 baseline 돌파: rango-portfolio @600 = 12/20 (+1)
- **첫이자 유일한 baseline(11/20) 돌파.** 회귀 0, 신규 [27]. published rango.json(8/20) 대비 +4[2,10,11,27].
- **왜 됐나**: straight-line(420s)이 baseline을 회귀 없이 그대로 재현 + classical-mem(180s)이 straight-line이 못 찾는 idx27을 추가 → 두 방식의 union. **300s에선 각 phase가 굶어서 실패(6/20)했지만 600s에선 성공.**
- `git branch -f master algo-dev`로 master에 반영(FF).

### 전체 방법 결과 (앞-20, baseline@600=11, @300=10)
| 방법 | @300 | @600 | 비고 |
|------|------|------|------|
| rango (baseline) | 10 | **11** | 강한 기준 |
| rango-apply (premise 강제, classical) | 8 | - | 신규[27] |
| rango-alignapply (align+apply) | 9 | - | 신규[27] |
| rango-mem / mem-wide / best-beam (classical) | 8 | - | classical 한계 |
| rango-align (aligned tactic, straight) | 8 | 9 | - |
| rango-apply-sl (premise 강제, straight) | 9 | 진행중 | 신규[27] |
| **rango-portfolio (straight∪classical)** | 6 | **12 ✓** | **돌파** |

### 교훈
1. **straight-line baseline이 매우 강함** — 다양한 재시작이 full 예산에서 효과적. classical 단독은 너무 좁아 ~8 (idx27만 얻고 2-3 회귀).
2. **개별 inference tweak(apply/align/memo)은 baseline 못 넘음** — 전부 idx27만 신규 + 회귀. straight-line에 얹어도(apply-sl) 마찬가지.
3. **돌파는 "대체"가 아니라 "합집합"에서** — portfolio가 baseline을 훼손 없이 재현 + 보완. 단 **예산이 충분해야(600s)** 각 phase가 제 역할.
4. idx840류(premise Top1 강함+model 미적용)는 first-20에 부재 → apply-forcing 이점이 이 벤치에 안 드러남. 별도 검증 필요.

### 다음 (진행 예정)
- rango-portfolio **40개 확대**(--num 40 --timeout 600)로 +1 견고성 확인.
- straight_frac 스윕(0.8/0.6)으로 portfolio 최적화.
- idx840 검증(rango-apply-sl/rango-apply).
- RL value-guided(MR1) — classical 순서 교정으로 idx27 외 추가 획득 시도.

### [분석] 하드코어 8개 (어떤 방법도 못 푼 first-20 정리) — 2026-07-06
never-solved = [0,4,8,15,20,21,22,25]. 두 부류:
- **자동화 가능형(arith/bit/decidability)**: idx4 flocq Zrnd_ZR_or_AW(반올림 disjunction), idx8 aarch64 Int bit, idx15 Integers translate_ltu(정수 부등식), **idx22 Intv In_dec `{In x i}+{~In x i}`(결정가능성)**, idx25 x86 addrmode(어셈블리) → **sauto/lia/decide/hauto 직격 대상**. retrieval도 매칭~6-7로 나쁘지 않음.
- **구조적 시뮬레이션형(길고 커스텀 귀납)**: idx0 Deadcode step_simulation, idx20 Selection eval_load, idx21 Inlining match_stacks_invariant → 1.3B 사정권 밖, decomposition/큰모델 필요. 최난이도.
→ **rango-sauto는 자동화형(5개) 겨냥** → idx27 외 추가 획득 잠재력, baseline 초과 가능성. 스모크 타깃에 **idx22** 추가(결정가능성=sauto 교과서 케이스).
→ 구조형은 별도(subgoal 분해/앙상블/RL). 논문 조사(진행중)에서 decomposition·best-of-N 기법 반영 예정.

### [인프라] 공정 비교 + 재사용 baseline (2026-07-06)
- `all_results/baseline300`(rango@300/20=10) + `all_results/baseline600`(→대실행 @600, 앞-20=11) named 디렉토리 생성, 계속 재사용.
- make_report가 **실험 timeout에 맞는 baseline 자동 선택**(@300→baseline300, @600→baseline600). 드라이버도 자동 공정 비교.
- 기존 @300 리포트 재생성. **공정 비교 표(@300 vs 10, @600 vs 11)**:
  | 방법 | 성공 | 공정순증감 |
  |------|------|-----------|
  | rango-portfolio@600 | 12 | **+1** |
  | rango-mem-wide@300 | 10 | **+0**(동률) |
  | rango-alignapply/apply-sl/portfolio@300 | 9 | -1 |
  | 나머지 | 8~9 | -1~-3 |
- 결론 유지: portfolio(union)만 baseline 초과. mem-wide(classical branch16)가 @300 동률로 근접.

### [개입] apply-sl@600 중단 + 큐 재정렬 (2026-07-06 04:2x)
- rango-apply-sl@600이 **try_candidates=6으로 정리당 6배 느림 + 로그 150MB/정리**로 3.5h째 큐 정체(17/20). 기대값 낮아(@300=9) 중단.
- **교훈**: try_candidates 높이면(다중후보 straight-line) 검증콜·로그 폭증 → 비효율. 향후 지양. retrieval 디버그 프린트도 로그 비대 주범(추후 축소 필요).
- 큐 재정렬: **rango-ensemble(A1 retrieval다양성, 연구 1순위)·no-retrieval 우선** → portfolio 변형. 드라이버 재시작(fd 갱신).

### [분석] ensemble 중간(8/20, idx11 회귀) — 2026-07-06 05:2x
- ensemble(retrieval모델↔no-retrieval모델 로테이션)이 idx11 회귀. no-retrieval fine-tune이 그냥 더 약해서, 로테이션이 강한모델 attempt를 절반 낭비.
- **교훈**: 연구 A1(retrieval 다양성)은 **약한 별도 모델 혼합이 아니라, 같은 강한 rango 모델에서 retrieval 컨텍스트 on/off 토글**이어야 함(decorrelation은 얻되 모델강도 유지). → 신규 **rango-divsample**: straight-line 재시도마다 formatter의 retrieval 주입 on/off 토글(같은 모델). ensemble보다 유망.

### [완료] ensemble@600 = 10/20 (-1, 회귀 idx11, 신규 0)
- 약한 no-retrieval 모델 혼합 → 강한모델이 풀던 idx11 회귀. **A1을 약한 별도모델로 하면 실패 확정.**
- 다음: rango-divsample(같은 강한모델 retrieval토글) — 단 주의: rango는 retrieval과 함께 학습돼서 retrieval-off attempt가 OOD로 약할 수 있음. 데이터로 확인.

### [분석/수정] sauto-모든노드 = 5/17 회귀 → sparse sauto — 2026-07-06 09:4x
- rango-sauto(classical 모든 노드에 sauto/hauto/`sauto use:` 주입)가 5/17로 심각 회귀. **원인: sauto가 비싸서(호출당 수초) 모든 노드 호출→시간예산 폭식→정상 증명까지 실패.**
- **교훈(연구 PALM/DT-Solver와 일치)**: hammer/sauto는 **모든 노드가 아니라 드물게(초기 goal/fallback)** 써야. → **수정: step_idx<=1(초기 goal)에만 sauto 주입(sparse).** 재시도 중.
- 대안(안되면): sauto를 portfolio 3rd phase로(normal search 실패시 마지막에 sauto 1회) — PALM식.
