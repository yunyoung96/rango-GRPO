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
