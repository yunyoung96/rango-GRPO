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

### [진행중] Iter 1 — backtracking(M1) vs baseline(M0), 20개 @ 300s
- 가설: SEARCH_THRASH(47%)는 straight-line 재시작 낭비 때문 → best-first backtracking(`rango-best-beam`)이 유효 prefix를 보존해 성공률↑.
- 실험: `rango`@300/20 (baseline, dir=20260705-062926) → `rango-best-beam`@300/20 (M1), 순차.
- **중단·재개 이력**: baseline 7/20(성공4)에서 세션 종료로 백그라운드 job 사망 → run_all에 `--out` resume 추가 후 `setsid`로 **detach 재실행**(남은 13개부터). 이후 중단돼도 resume로 저렴하게 이어감.
- 상태: **실행 중(detach)**. 완료 후 성공 개수 비교·기록.
- baseline 부분결과(7/20): 성공 idx 2,5,6,9 / 실패 0,4,8.

### [완료] Iter 0 — 파이프라인 스모크 테스트
- rango(StraightLine): idx 6 SUCCESS 6.6s. rango-best-beam(ClassicalSearch/backtracking): idx 6 SUCCESS. `--timeout` 오버라이드 정상.
- 결론: 두 실행 경로 모두 정상 → Iter 1 진행.
