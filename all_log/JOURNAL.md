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

### [진행중] Iter 3 — M3 rango-align (straight-line + aligned next-tactic 힌트)
- 가설: SEARCH_THRASH(47%)는 straight-line 재시작 낭비 → best-first backtracking(`rango-best-beam`)이 유효 prefix 보존해 성공률↑.
- 실행: `setsid`로 detach, `all_log/run_method.sh rango-best-beam 600`. 로그 all_log/m1_run.log. 07:22 UTC 시작.
- 완료 후 M0@600(11/20)과 성공 개수 비교→기록. ≥이면 master merge 검토, 그리고 M2(rango-mem) 동일조건 실행.

### [완료] Iter 0 — 파이프라인 스모크 테스트
- rango(StraightLine): idx 6 SUCCESS 6.6s. rango-best-beam(ClassicalSearch/backtracking): idx 6 SUCCESS. `--timeout` 오버라이드 정상.
- 결론: 두 실행 경로 모두 정상 → Iter 1 진행.
