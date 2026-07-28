# 논문 조사 2 — proof auto-gen, strong sampling baseline 넘기 (2026-07-06)

> **결론: 내 실험 발견 = 문헌 합의.** verifier(Coq) 있으면 **diverse sampling coverage(pass@k)가 지배적**. reranking/majority-voting은 **무용**(정답을 이미 검증하므로). search-order tweak은 진다. 넘는 길은 3가지뿐.

## 넘을 수 있는 3가지 (우선순위순)

### A. 같은 예산의 다양성/coverage↑ (최고 EV — 강점 강화)
- **A1 decoding-config 포트폴리오** (DeepSeek-Prover-V1.5, 2408.08152): 예산을 **temperature × {CoT,plain} × {retrieval-on,off}** 그리드에 분배. CoT/plain 반반이 coverage↑(서로 다른 정리 품). **retrieval-on/off는 강하게 decorrelated** → union. 거의 무비용. → *내 rango-ensemble(retrieval on/off 모델)·no-retrieval가 이미 부분 구현*.
- **A2 diverse decoding**: beam 대신 nucleus/diverse-beam으로 후보를 의미적으로 퍼뜨림(중복 tactic 방지). executor가 검증하니 순수 이득.
- **A3 DPP 다양성 필터** (3D-Prover, 2410.11133): 후보 N개 과생성→임베딩→k-DPP로 **고품질+상호비유사** 부분집합 선택(greedy MAP-DPP ~10줄). 학습 불필요, generator-agnostic. 중복/오류 tactic을 executor 치기 전에 제거.
- **A4 novelty 중복제거** (RMaxTS): 재시도가 이미 본 상태로 재진입하면 조기중단→예산을 새 샘플로. 탐색 아님, baseline 위 경량 dedup 레이어.

### B. sampling이 못 푸는 것 (다른 정보=에러메시지 사용) — union 패턴
- **B1 whole-proof + error-feedback repair** (Baldur FSE2023 2303.04910; **PALM 2409.14274=Coq네이티브**; CoqPilot 2410.19605; DeepSeek truncate-and-resume):
  - **PALM(Coq, 거의 drop-in)**: 생성→실패시 Coq 에러별 **기호적 repair** — ①unknown ref→로컬/글로벌에서 유사이름 lemma **BM25 랭킹**(내가 이미 보유!)로 치환, ②intros 이름충돌 rename, ③bullet 교정, ④apply/rewrite 오용→**CoqHammer sauto/qsimpl에 그 lemma 넣기**. + CoqHammer 백트래킹 fallback. **40.4%** (Proverbot 17%, DSP 23%), 1270개는 유일 증명. ~33s/proof.
  - **Baldur repair**: (정리,실패proof,**에러메시지**) 재입력→수정. +8.7%. 에러메시지가 load-bearing.
  - **truncate-and-resume**: 실패 whole-proof의 **최대 정답 prefix 유지 + 에러지점 상태부터 재개**(상태를 주석 주입). 실패를 부분크레딧으로.
  - **→ 내 적용**: 재시도가 이전보다 더 나아간(최대정답prefix↑) proof를 버리지 말고 에러 잡아 PALM 기호repair(BM25 ref치환 무료)+Baldur 재생성. 예산캡. **portfolio에 repair phase 추가.**
- **B2 decomposition** (DSP ICLR2023; POETRY NeurIPS2024 2405.14414: `sorry`로 레벨별 재귀, 최대증명길이 10→26; DeepSeek-Prover-V2): 긴 증명을 subgoal로. **긴 구조증명(하드코어 idx0,20,21)의 유일한 길.** 고위험(나쁜 sketch가 쉬운것 회귀)→sampling+repair 실패한 것에만 gate. Coq구현: `assert(H:..).{admit.}` skeleton→각 hole에 straight-line 독립 실행(CoqPilot proof-hole).

### C. 예산 배분 (내 유일한 승리=portfolio, 일반화)
- **C1 문제별 compute-optimal** (Large Language Monkeys 2407.21787: coverage가 samples에 log-linear; Snell 2024): 고정 600s×20에서 균등배분은 suboptimal. **적응적 중단+재배분**: 푼 것/가망없는 것(최근 M시도 novel상태 0) 중단→진전(최대정답prefix↑) 보이는 것에 예산 투입.
- **C2 DT-Solver** (ACL2023): 어려운(저confidence) 상태에 더 많은 compute. 저compute에서 +11%.
- **C3 N-armed portfolio**: A/B 전략들(temp그리드/retrieval on-off/repair/decomp)에 최소보장 slice + UCB 밴딧으로 marginal 정리 푸는 arm에 예산 이동. "각 phase 충분예산" 필수(내 관찰).

## 하지 말 것 (E)
- **complete proof reranking/majority-voting/self-consistency**: Coq검증 있으니 무용.
- **더 이상의 classical/best-first search-order tweak**: 실증적으로 진다(내 M1~M4').
- **독립 diverse sample 수를 줄이는 모든 것.**

## 내 다음 방법 매핑 (구현 우선순위)
1. **rango-ensemble/no-retrieval**(큐 대기) = A1 retrieval-diversity. 결과 주목.
2. **rango-sauto**(idle시) = B1의 premise-augmentation(sauto use: retrieved) + 하드코어 자동화형 5개 겨냥.
3. **rango-repair**(신규 설계): PALM-lite — 최대정답prefix proof의 Coq에러로 ①BM25 ref치환 ②sauto use premise 재시도. B1.
4. **rango-divsample**: straight-line 재시도마다 temperature/retrieval-on-off 순환(A1). temp plumbing 필요.
5. **rango-decomp**(고위험, 나중): assert-admit skeleton→hole별 증명(B2), 구조형 하드코어.
6. **adaptive budget**(C1): run_all/searcher에 진전없는 정리 조기중단.

출처: 2407.21787·2408.08152·2410.11133·2303.04910·2409.14274·2410.19605·2405.14414·2412.14063·2410.15700·2401.02949 등.
