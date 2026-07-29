# CompCert 증명 천장 분석 — 왜 ~28%에서 막히나 (retrieval vs rerank vs capability)

작성 2026-07-29. rand200(w6, 새 Blackwell HW) 평가에서 **baseline·B·D·U가 (같은 워커·검색이면) ~28%로 수렴**한 이유를 실제 proof·트레이스·**Coq 실행검증**으로 분해.

**핵심 결론 (3층)**:
1. **표면**: 실패=긴 증명(성공 ~9step vs 실패 ~28step). 방법(SFT/GRPO/DPO/SRFT)이 아니라 정리 난이도가 지배.
2. **lemma 이름 버킷(§2, 텍스트기준)**: gold가 쓴 이름 중 retrieval/rerank 표적이 46%(D+B)로 커 보임.
3. **Coq 실행검증(§2.5, goal기준)이 2를 뒤집음**: ⓐ step 단위로 gold lemma의 **96%가 auto/lia/ring 자동대체 가능**(그 특정 lemma 검색이 병목 아님). ⓑ train 실패 189개를 도달 최심점에서 강력탐색으로 닫아보면 **42%는 자동화로 회복 가능(도달은 했음), 57%는 그래도 안 닫힘(진짜 어려움=도달성)**. → 진짜 병목 = **도달성/조립(capability)** × **탐색예산(compute; 실패 100%가 timeout)**. **레버 2개: 42%는 싼 자동화, 57%는 큰 base(Qwen 7B).** retrieval/rerank의 *실효*는 작음.

관련: [[SUBGOAL_PAPER_ASSESSMENT]] §10 도달성, [[BFS_PROVER_METHOD]], [[research-direction-2026-07]].

---

## 0. 한 눈에 (성공률)
> ★ 성공률은 **반드시 (검색·워커·GPU/HW)를 함께** 기입 — 이 축들이 다르면 직접 비교 불가(§0 confound). HW: **Ada**=RTX 6000 Ada 48GB(~07-24), **BW**=RTX PRO 6000 Blackwell 96GB(07-29~).

| 방법 | search | 워커 | GPU/HW | 측정일 | rand200 성공률 |
|---|---|---|---|---|---|
| baseline (rango SFT) | classical | **w2** | **Ada 48GB** | 07-24 | **33.5%** (67/200) |
| baseline (rango SFT) | BFS | w6 | **BW 96GB** | 07-29 | 28.0% (56/200) |
| combo-D (SFT+GRPO+DPO, EI2) | BFS | w6 | BW 96GB | 07-29 | 28.5% (57/200) |
| B-EI (SFT+DPO) | BFS | w6 | BW 96GB | 07-29 | 27.0% (54/200) |
| combo-U (SRFT) | BFS | w6 | BW 96GB | 07-29 | 32.5% (65/200) |
| SFT→GRPO | classical | **w2** | **Ada 48GB** | 07-24 | **37.5%** (75/200) |
| **#5** 순수 rango(대조) | classical | w6 | BW 96GB | 07-29 | **37.2%** (54/145, 잠정·측정중) |
| **#6** SFT→GRPO(대조) | classical | w6 | BW 96GB | 07-29 | **33.3%** (24/72, 잠정·측정중) |

> ★ **#5가 confound를 확정(잠정)**: 같은 워커(w6)·HW(BW)에서 **classical 37.2% ≫ BFS 28%(+9%p)**. → **천장 28%의 주범은 검색 알고리즘(BFS<classical)**, 워커·GPU 아님. (현재 HW 58코어 여유라 w6가 안 굶김과 정합.) classical·w6·BW(37%)가 classical·w2·Ada(33.5%)보다도 높음 → Blackwell이 더 빨라 노드 더 탐색. **200개 완료 시 확정.**

→ **학습 조합을 뭘 해도 같은 워커·검색·HW면 ~28%.** 공통 52정리 겹침분석: **12개는 뭘 해도 성공 / 36개(69%)는 뭘 해도 실패 / 4개만 방법이 갈림.** = 성능은 방법이 아니라 **정리 난이도**가 지배.

> ⚠️ **천장 숫자는 워커 수에 confound(2026-07-29 발견).** **실패 정리의 100%가 timeout(600s)에서 죽음** = 탐색 포기가 아니라 시간부족. 워커↑ → 정리당 CPU↓ → 600s 내 탐색 노드↓ → 성공↓. 실제로 고득점(33.5·37.5%)은 전부 **w2**, 저득점(27~32.5%)은 전부 **w6**. **공정비교는 워커 고정**(w6 기준: combo-U 32.5% > baseline 28%, +4.5%p 유효). GPU 속도는 성공률을 직접 안 바꿈(노드/600s 통한 간접효과, Blackwell이 옛 HW보다 빠름). 검색축(classical>BFS, 같은셋 net +11)도 별개 변수. → **천장의 일부는 capability가 아니라 탐색예산(compute) 아티팩트.**
>
> ※ 단, **현재 HW는 58코어에 load~17(여유 큼)** — w6가 코어를 굶기지 않음. 즉 워커 confound의 메커니즘(CPU 경합)은 **옛 HW(코어 적음) 특유**일 수 있고, 현재 HW에선 28%↔33.5% 갭의 주범이 **검색(classical>BFS)**일 공산이 큼. 어느 쪽이든 실패는 600s wall-clock 자체에 막히므로 레버는 "워커↓"가 아니라 **timeout↑ 또는 검색·모델 개선**. **#5(classical·w6·현재HW)가 확정**: ~33%면 검색이 주범(워커 무관), ~28%면 다른 요인. [[worker-timeout-confound]]

---

## 1. 성공/실패를 가르는 것 = **증명 길이**
| 그룹 | gold proof 길이(평균 step) |
|---|---|
| TEST 성공 | **9.1** |
| TEST 실패(천장) | **28.2** (최대 120) |
| TRAIN beam-solved(쉬움) | 6.1 |
| TRAIN BFS-solved(중간) | 8.0 |
| TRAIN BFS-fail(어려움) | **35.0** (최대 631) |

**짧으면(~9step) 다 풀고, 길면(~28step) 다 못 푼다.** 길이 = 탐색공간 지수폭발 + 여러 lemma 조립. train/test **동일 패턴**.

---

## 2. ★핵심 마스터 테이블 — 실패 정리가 필요로 한 lemma의 정체
> ⚠️ **정정판(2026-07-29)**: 초판은 정규식이 tactic 끝 마침표(`sep_proj2.`)를 이름에 포함해 프로젝트 lemma를 built-in으로 오분류했음. 마침표 제거 + 프로젝트 정의(lemma+생성자 10,962개) 대조로 재분류. **결론이 바뀜: built-in은 61%가 아니라 24%, retrieval/rerank 표적은 18%가 아니라 46%.**

**분모 = TRAIN 실패 정리(BFS collect fail)가 apply/rewrite한 이름 총 1,493개** (트레이스로 검색순위까지 매칭).
**분자 = 각 버킷 개수.** 각 이름을 "검색됐나 / 몇 위였나 / 안 됐으면 정체가 뭔가"로 딱 한 버킷.

| 버킷 | 개수 | % | 뜻 (실제 예) | 진단 | 해결 레버 |
|---|---|---|---|---|---|
| **A. 검색 top1-5인데 실패** | 77 | **5%** | 정답이 검색 상위인데도 못 닫음 (stacksize_preserved…) | **조립(capability)** | 큰 모델 |
| **B. 검색 top6-50** | 316 | **21%** | 검색은 됐는데 하위권 → 모델이 사실상 안 씀 (plus_one, symbols_preserved, bpow_gt_0) | **RERANK** | 학습형 reranker |
| **C. stdlib/built-in** | 366 | **24%** | Coq Reals·Z 산술 (Rle_trans, Rmult_assoc, IZR_le, f_equal) | **자동화 영역** | lra/ring (과거 rango-search=無) |
| **D. 프로젝트 lemma 검색실패** | 383 | **25%** | CompCert 내부인데 검색 50개 밖 (sep_proj2, agree_regs_undef_regs, frame_undef_regs) | **RETRIEVAL(recall)** | 검색범위↑, embedding retriever |
| **E. 로컬가설** | 173 | **11%** | 증명 중 만든 가설 조합 (SEP, H, H0, UNDEF) | **조립(capability)** | 큰 모델 |
| **F. 기타** | 178 | **11%** | 모듈lemma(PTree.gss, Mem.perm_alloc_2)+로컬 소수 혼재 | 혼재 | — |
| **합계** | **1,493** | **100%** | | | |

### 각 %의 의미 (한 줄씩)
- **A 5%**: "찾아줘도 못 쓴다" = retrieval/rerank로 못 고침. 순수 capability.
- **B 21%**: **rerank의 표적** — 검색됐는데 top5 밖이라 안 쓰임. 정답을 top5로 올리면 도움.
- **C 24%**: Coq Reals/Z 산술 = **자동화(lra/ring) 영역**, retriever 무관. (초판이 61%로 뻥튀기했던 것 — 실제 24%.)
- **D 25%**: **retriever recall 실패** — 프로젝트 lemma인데 검색 50개 밖. 검색 개선으로 회복 가능.
- **E 11%**: 로컬가설 조합 = capability. **F 11%**: 혼재(모듈lemma+로컬).

### 버킷별 실제 코드 예시 (▶ 눌러 펼치기)
> 각 예시는 CompCert 소스에서 grep한 **gold 증명이 실제로 쓴 줄**과 그 lemma의 **정의 위치**다. (좌측 세로선 = 예시 영역)

<details>
<summary><b>A. 검색 top1-5인데 실패</b> — 정답이 상위에 검색됐는데도 못 닫음 (조립력)</summary>

> **정리**: `Tailcallproof.v` — free 권한(range_perm) goal
> ```coq
> (* gold(정답)이 이 지점에서 쓴 줄 *)
> apply Mem.range_perm_free. rewrite stacksize_preserved. rewrite H7.
> ```
> - `stacksize_preserved` : `Linearizeproof.v`에 정의된 **프로젝트 lemma** → 검색 top1-5 안에 실제로 들어왔음.
> - 그런데도 rango는 이 state에서 못 닫음. **검색이 맞아도(정답 상위) 조립을 못 한 케이스** → retrieval/rerank로는 못 고침. 순수 capability.

</details>

<details>
<summary><b>B. 검색 top6-50 (RERANK 표적)</b> — 검색은 됐는데 하위권이라 모델이 사실상 안 씀</summary>

> **정리1**: `RTLgenproof.v` — 실행 step(plus) 증명
> ```coq
> left; apply plus_one. eapply exec_Ireturn. eauto.
> ```
> `plus_one` : `Smallstep.v` 정의. 검색은 되나 6~50위 → top5 프롬프트에 안 실려 모델이 후보로 못 봄.
>
> **정리2**: `Renumberproof.v` — 심볼 보존
> ```coq
> rewrite symbols_preserved. destruct (Genv.find_symbol ge id); try congruence.
> ```
> `symbols_preserved` : 같은 파일 정의인데도 하위권.
>
> **정리3**: `IEEE754_extra.v` — 부동소수 bound
> ```coq
> apply bpow_gt_0. rewrite <- IZR_Zpower by (red in prec_gt_0_; lia).
> ```
> `bpow_gt_0` : `Raux.v`(Flocq) 정의. → **정답을 top5로 끌어올리는 reranker면 회복 가능**(§5).

</details>

<details>
<summary><b>C. stdlib/built-in</b> — Coq Reals·Z 산술, retriever 무관 = 자동화(lra/ring) 영역</summary>

> **정리**: `IEEE754_extra.v` — 실수 부등식/곱셈 결합
> ```coq
> apply Rle_trans with (IZR n); auto. apply IZR_le; auto.   (* Rle_trans: Coq.Reals *)
> unfold F2R; simpl. rewrite Rmult_assoc. f_equal.          (* Rmult_assoc, f_equal *)
> ```
> - `Rle_trans`·`Rmult_assoc`·`f_equal` 모두 **Coq 표준 라이브러리** — CompCert 밖. 검색해서 넣을 대상이 아님.
> - 이런 산술은 `lra`/`nra`/`ring`이 **한 줄로 자동으로** 닫는 게 정석. (rango-search가 stdlib `Search`로 시도했다 실패한 전례 있음 → lra/ring 정밀화는 미시도.)

</details>

<details>
<summary><b>D. 프로젝트 lemma 검색실패 (RETRIEVAL recall 표적)</b> — CompCert 내부인데 검색 50개 밖</summary>

> **정리**: `Stackingproof.v` — separation logic frame
> ```coq
> eapply sep_proj2; eassumption.                                   (* sep_proj2 *)
> apply agree_regs_undef_regs. apply agree_regs_call_regs. auto.   (* agree_regs_undef_regs *)
> eapply frame_undef_regs with (rl := destroyed_by_setstack ty) in SEP.  (* frame_undef_regs *)
> ```
> - `sep_proj2` : `Separation.v` 정의(**프로젝트 내부**), `agree_regs_undef_regs` : `Stackingproof.v` 자기 파일 정의.
> - 명백히 존재하는데 검색 상위 50 밖 → **retriever recall 실패**. 검색범위↑ / embedding retriever로 회복 가능한 표적.

</details>

<details>
<summary><b>E. 로컬가설</b> — 증명 도중 만들어진 가설. ★애초에 검색 대상이 아님(아래 참조)</summary>

> **정리**: `Stackingproof.v`
> ```coq
> split. rewrite (contains_callee_saves_exten j sp ls0 ls1). exact SEP.
> ```
> - `SEP` : 이 증명이 앞에서 `intros`/`destruct`로 **그 순간 만들어낸 로컬 가설**. 어떤 라이브러리에도 없음.
> - "정답 lemma가 검색 밖" 문제가 아니라, **모델이 자기 context의 가설을 추적·조합**하는 문제 = capability.

</details>

### 로컬가설(E, F 일부)은 애초에 "검색 대상"이 아니다
질문에 대한 답: **아니다 — 로컬가설은 retriever의 인덱싱 대상 자체가 아니다.**
- retriever(BM25 proof + TF-IDF premise)는 **파일에 정의된 전역 lemma/정의**만 인덱싱한다. `SEP`, `H`, `H0`, `UNDEF` 같은 로컬가설은 증명 도중 `intros`/`destruct`/`generalize`가 **그 state에 도달하는 순간** 만들어내는 것 — 어떤 라이브러리에도 없고, 그 지점 전엔 존재하지도 않는다.
- 따라서 **E(11%)는 retrieval로 고칠 수 없다(고칠 대상이 아님).** "정답이 검색 밖" 문제가 아니라 모델이 자기 문맥의 가설들을 추적·조합하는 문제 = 순수 capability/assembly.
- 이는 결론을 **강화**한다: retrieval/rerank 표적(D+B=46%)에서 E는 빠지는 게 맞고, **capability 하한(A+E=16%)은 "검색으로는 절대 못 여는" 몫**이다.

### 버킷 → 병목으로 묶기 (정정)
| 병목 | 버킷 | 합 |
|---|---|---|
| **RETRIEVAL(recall) — 검색 개선** | D | **25%** |
| **RERANK(순위) — 재정렬** | B | **21%** |
| **stdlib 산술 — 자동화(lra)** | C | 24% |
| **capability(조립) — 큰 모델** | A + E | 16% |
| 혼재 | F | 11% |

---

## 2.5 ★Coq 실행검증 — goal 기준으로 "정말 필요했나" (텍스트 아님)
§2는 텍스트(어떤 이름을 apply/rewrite 했나)라 "정말 그게 필요했나"는 못 말함. **두 개의 Coq 배터리**로 goal 기준 재검증. 결론이 §2를 뒤집음: **retrieval/rerank는 실병목 아니고, 병목은 "깊은 state에 도달 못 함"(도달성).**

### A. step 단위 — gold lemma가 그 자리에 정말 필수인가 (goal_verify, 실패지점 apply/rewrite 33개)
- **22/23 판정가능 = 96%가 `auto`/`lia`/`ring` 등으로 자동대체 가능** (10개는 replay 실패로 판정불가).
- → 개별 step에서 그 특정 gold lemma는 **대부분 필수가 아님**. "정확히 그 lemma를 검색해 넣기"(retrieval/rerank)는 실병목이 아님.

### B. 잔여 전체 — 도달한 최심 지점에서 나머지가 자동으로 닫히나 (all-solvers 배터리)
각 실패 정리에서 정책이 **실제로 도달한 가장 깊은 state**를 잡고, 거기서 강력탐색(`auto|eauto|lia|nia|congruence|intuition|firstorder|ring`)으로 나머지 전체가 닫히는지 Coq 실행. **train·rand200 둘 다** 측정 → **거의 동일**:

| 결과 | train(189) | rand200(113) | 뜻 | 레버 |
|---|---|---|---|---|
| **closer가 닫음** | 81 (**42%**) | 46 (**40%**) | 도달은 했는데 강력탐색을 안 써서 놓침 | **자동화 — 싸게 회복** |
| **closer도 못 닫음** | 108 (**57%**) | 67 (**59%**) | 도달지점 잔여가 진짜 어려움(다단계 도달) | **capability — 큰 모델** |
| 도달 깊이(중앙)/gold | 12 / 18 (67%) | 14 / 18 (78%) | gold의 그만큼까지만 뻗고 멈춤 | |

- **train↔rand200 일치(42%↔40%, 57%↔59%)** = 병목이 **셋·방법 무관하게 동일**함을 증명(§0 "36/52는 뭘 해도 실패"와 정합).
- (데이터: train=`bfs_expert_iter/round1/collect`, rand200=`data/test_trace` 트레이스.)

### A(96%) vs B(42%) — 모순 아니라 화해
- A=**개별 step**은 96% 자동화 가능. B=**잔여 전체**는 42%만. 차이 = 잔여가 여러 step이라 **자동화가 leaf는 닫아도 중간 state들을 "도달"시키진 못함**.
- → **57%는 도달성(reachability) 문제로 귀결.** §10("닫기는 배우나 도달을 못 배움")을 **goal 실행 기준으로 재확인.**

### 결론 (train 병목 최종)
1. **42% = 싼 자동화 win** — 도달은 했으니 `lra/nia/auto/ring`을 **탐색에 공격적으로** 넣으면 회복(§2.5-특화 automation 레버).
2. **57% = capability** — 큰 base로 **도달 자체를 늘려야** 함 ← **Qwen2.5-Coder-7B 재학습이 겨냥**.
3. **retrieval/rerank는 어느 쪽도 아님** — A(96%)가 §2 텍스트버킷 46%의 *실효*를 반증.

> ✅ **rand200도 완료(2026-07-29)**: 40%/59% — train(42%/57%)과 거의 동일. 병목 진단이 train·test 양쪽에서 재현됨.

---

## 3. 진단: retrieval 문제냐 rerank 문제냐 (정정)
**둘 다 생각보다 큼 — 합쳐서 46%.**
- **RERANK = 21%(B).** 정답이 검색은 됐는데 top5 밖이라 안 씀. 모델은 성공 시 apply한 lemma의 **90%가 top1-5**였음(순위 높으면 쓴다는 것 확인) → **정답을 top5로 올리면(rerank) 이 21%가 표적.**
- **RETRIEVAL = 25%(D).** 프로젝트 내부 lemma를 top50에 못 넣은 recall 실패 → 검색범위·retriever 개선으로 회복.
- **자동화(lra/ring) = 24%(C)** = Coq Reals/Z 산술. retriever 무관. (초판이 이걸 61% built-in으로 뻥튀기해 "retrieval 무의미"로 오도했었음 — 정정.)
- **capability(조립) = 16%(A+E).** 찾아줘도 못 조립.
- **과거 검증**: `rango-search`(Coq Search로 stdlib 힌트) 시도 → **35%/31.7% ≈ baseline 33.5%(효과 없음)** = C(stdlib 접근)는 안 통함 실증.
- **핵심 반전**: 초판은 "retrieval/rerank 18%뿐, 나머지 82% capability/자동화"였으나, 정정 후 **retrieval+rerank가 46%** = **검색·재정렬 레버의 여지가 실제로 큼**(단 §5 한계 참조).
- **왜 학습(RL/SFT)이 천장을 못 올렸나**: test 필요 lemma의 **78%가 train에 없음**(53% 정리는 완전 novel lemma). → "특정 lemma를 apply하는 법"을 외우는 학습은 **전이 안 됨**. 그래서 모든 RL 변형이 같은 천장.

---

## 4. 해결 방법 (레버별 상한·비용) — 정정
| 레버 | 공략 버킷 | 상한(lemma %) | 비용 | 판정 |
|---|---|---|---|---|
| **① retriever recall↑** (범위 50→100, embedding retriever) | D | **~25%** | 중 | **표적이 큼.** 프로젝트 lemma를 검색에 넣는 것 |
| **② 학습형 reranker** (검색된 걸 top5로) | B | **~21%** | 중 | 아래 §5. 표적 큼 |
| **③ 자동화 강화** (lra/ring/nra 더 공격적) | C | ~24% | 저 | rango-search(stdlib Search) 실패 전례. **SearchRewrite/lra 정밀화는 미시도** |
| **④ 더 큰 base 모델** (조립력·lemma 지식) | A+E+F+나머지 | 근본 | 고(재-SFT) | 조립(16%)+전반 향상. 근본 레버 |

**요약(정정)**: **retrieval+rerank(①②)가 46%로 표적이 큼** — 초판(18%)의 오분류를 걷어내니 검색·재정렬 레버의 여지가 컸음. 단 **§5 냉정한 한계**: 한 정리에 A~F 여러 버킷이 섞여 있어, D/B를 고쳐도 그 정리의 다른 버킷(조립·자동화)이 막으면 못 닫음 → 정리 성공률 기여는 lemma %보다 작음. **capability(④)는 여전히 전반을 올리는 근본 레버.**

---

## 5. rerank가 문제라면 — 강화학습으로 어떻게 푸나
버킷 B(7%): "정답 lemma가 검색 6~50위 → 모델이 안 씀". 목표 = **정답을 top5로 끌어올리는 reranker**.

### 왜 supervised만으론 부족한가
- gold proof가 "어떤 lemma를 썼는지"는 알지만(positive), **"안 쓴 49개 중 뭐가 진짜 무관인지"** 라벨이 없음(hard negative 모호). 순위만 맞추는 pointwise/pairwise supervised는 **"proof가 실제로 닫히는가"** 와 어긋날 수 있음.

### RL(RLVR) reranker 설계
- **정책**: cross-encoder 스코어러 `f(goal, premise)` → 50개 재정렬(top-k 선택).
- **행동**: 검색된 50개 중 **top-k(예: k=10) 부분집합 선택/재정렬**.
- **보상(verifier 기반, 공짜)**: 재정렬된 top-k를 prover(BFS)에 넣어 **정리가 닫히면 +1, 아니면 0** (BFS-Prover의 이진보상 그대로). = **"어떤 premise를 상위에 올려야 prover가 증명을 닫나"** 를 직접 최적화.
- **왜 RL이 맞나**: reranker의 성공 = "그 premise들을 줬더니 **downstream에서 증명이 닫힘**"이라는 **결과 신호**로만 정의됨. supervised label(어느 게 정답 순위)이 없으니 **verifier reward가 유일한 정답 신호** → RLVR 구조가 자연스러움.
- **credit assignment**: 여러 premise를 top-k에 올렸을 때, 그룹상대(GRPO) advantage로 "어떤 배치가 성공률 높았나"를 그룹 비교 → 개별 premise 기여 추정.

### 구체 파이프라인 (우리 인프라 재사용)
1. **rollout**: 각 정리에서 reranker가 top-k 후보 배치를 여러 개 샘플 → 각 배치로 BFS 짧게 → 닫힘/실패 = 보상.
2. **GRPO**: 배치(=premise 순열) 그룹의 상대 advantage로 reranker 업데이트. (dead group 문제 동일 — 애초에 못 닫는 정리는 신호 0.)
3. **cold-start SFT**: gold proof가 쓴 lemma를 positive로 pairwise SFT 워밍업 → RL 부트스트랩.

### 냉정한 한계
- **순수 표적 21%(B)** — 초판(7%)보다 크지만, reranker가 다 회복해도 정리 성공률 기여는 그보다 작음(한 정리에 A~F 여러 버킷 섞여 있어, B를 고쳐도 다른 버킷이 막으면 못 닫음).
- **dead group 재발**: RL reranker도 "애초에 닫히는 정리"에서만 신호 → 천장 정리(69%)엔 보상 0. subgoal/GRPO와 같은 도달성 벽.
- → **rerank-RL은 "값싼 +α"**, 우선순위는 ①retriever recall(25%, 더 값쌈)과 ④ 큰 모델.

---

## 6. 최종 결론 (정정)
1. 천장(~28%)의 lemma별 원인 분해(정정): **RETRIEVAL 25%(D) + RERANK 21%(B) + 자동화 24%(C) + 조립 16%(A+E) + 혼재 11%(F).**
2. **초판 정정**: built-in은 61%가 아니라 **24%**. 정규식 마침표 버그로 프로젝트 lemma를 built-in으로 오분류했었음. → **retrieval/rerank 표적이 18%가 아니라 46%로 훨씬 큼.**
3. **학습(RL/SFT)이 천장을 못 올린 이유** = test 필요 lemma **78%가 novel**(train에 없음) → "특정 lemma apply 외우기"는 전이 안 됨. **"검색된 걸 고르기"로 전환해야 전이.** (rerank가 원리에 맞는 이유.)
4. **레버 우선순위(정정)**: ① **retriever recall↑(D 25%, 값쌈)** → ② **학습형 reranker(B 21%)** → ④ **큰 모델(조립+전반)**. ③ 자동화는 rango-search 실패 전례(단 lra/SearchRewrite 정밀화 미시도).
5. **단 실제 성공률 기여는 lemma % 보다 작음** — 한 정리에 여러 병목이 겹쳐서. 그래도 초판 결론("retrieval 무의미, 오직 큰 모델")은 **틀렸고**, retrieval/rerank가 실질 레버로 재평가됨.
