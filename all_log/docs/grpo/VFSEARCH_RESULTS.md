# value-free structural search — 실험 결과 (2026-07-29, 부정)

`VALUE_FREE_SEARCH.md` 알고리즘을 구현(`bfs_prover_searcher.py`, alias `rango-vfsearch`)해 rand200 w6에서 측정. **결론: 천장 돌파 실패 — 오히려 큰 후퇴(regression).**

## 결과 (rand200, w6, Blackwell, 정책=rango-grpo π₀)
동일 정리 공정비교(190 공통):

| 방법 | 검색 | 성공률 | vs BFS |
|---|---|---|---|
| #5 rango (classical) | classical | **36.8%** | — |
| #6 SFT→GRPO (classical) | classical | 34.7% | — |
| BFS baseline (SFT 정책) | BFS | 27.9% | 기준 |
| **vfsearch (구조열거+MC)** | BFS+VF | **17.4%** | **−10.5%p** |
| vfsearch-nomc (열거만) | BFS+enum | 16.8% | −11%p |

- vfsearch만 성공 5개 [9,222,852,1678,1977] vs **BFS만 성공 25개** → 강제분해가 BFS가 풀던 걸 대량으로 못 풀게 함.
- (대조군 `rango-grpo+순수BFS`는 사용자 요청으로 조기중단 1/200 — policy confound 완전제거는 미완. 단 vfsearch 17%는 어떤 baseline보다도 낮아 결론 불변.)

## 왜 실패했나 (진단)
1. **강제 분해 열거가 정책의 좋은 안내를 덮어씀** — rango-grpo(π₀)는 이미 적절한 tactic을 냄. `destruct/induction`을 모든 hyp/var에 강제 주입 + `+1000` 우선순위 bonus로 먼저 확장 → 대부분 쓸모없는 case-split로 탐색을 끌고 감.
2. **MC compute가 예산 잠식** — 분해노드마다 K·D 롤아웃 → 600s 예산에서 실제 탐색 노드 수↓ → BFS가 찾던 증명을 못 찾음(BFS-only 25개).
3. **nomc(열거만)가 더 나쁨(16.8%)** — 열거를 MC 없이 하면 프론티어를 클러터. MC가 그 손해를 겨우 되돌려 vfsearch가 nomc와 비슷(둘 다 후퇴).
4. **BFS 기반이 애초에 천장** — VALUE_FREE_SEARCH.md 전제는 우리가 **나중에** 밝힌 "검색축(classical 37% ≫ BFS 28%)이 지배적"을 몰랐음. 약한 BFS 위에 얹은 게 설계 오류 — classical 위에 얹었어야.

## 교훈
- **정책이 이미 reasonable하면 test-time에 분해를 "강제"하는 건 해롭다.** coverage 22%(정답분해 못 생성)를 열거로 메우려 했으나, 대부분 정리에선 강제분해가 노이즈. 도움은 소수(5개), 손해는 다수(25개).
- **진짜 레버는 여전히 (a) 검색축(classical) (b) 큰 base(capability).** 구조 열거는 "선택적 발동"(정책이 확신 있게 stuck일 때만) 아니면 순수 손해.
- value-free MC 아이디어 자체는 작동(정리 5개 신규 해결 = 메커니즘 유효)하나, 무차별 적용이 문제.

## 재현
- branch `algo-vfsearch`. `rango-vfsearch`(MC) / `rango-vfsearch-nomc`(ablation) / `rango-bfs-grpo`(대조) alias.
- `python3 scripts/run_all.py --alias rango-vfsearch --idx-file data/compcert_bs2_rand200_idx.txt --timeout 600 --gpus 0 --workers 6 --out ...`
- 구현: `bfs_prover_searcher.py`(use_vfsearch/mc_K/mc_D/mc_budget/struct_cap + _is_decomp_point/_enum_structural/_mc_value).
