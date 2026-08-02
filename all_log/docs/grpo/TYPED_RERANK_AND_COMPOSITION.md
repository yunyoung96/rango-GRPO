# 타입-지향 premise 재랭킹 (selection 개선) + 조립 학습 논의

작성 2026-08-02. 연장: [[STRUCTURED_CONTEXT]] §4-1(타입-지향 재랭킹), oracle +2pp 재해석, 조립 학습법.

## 1. 타입-지향 premise 재랭킹 — 구현 & 측정 (CPU)

동기: 닫기 실패의 90%가 **잘못된 lemma 선택**([[opener/CLOSING_FAILURE_ANALYSIS]]). BM25는 **어휘유사**로 랭킹 → apply에 필요한 "**결론이 goal과 맞는** lemma"를 위로 못 올림.

**방법** (`scripts/rerank_premises_typed.py`): premise(lemma statement)의 **결론**(top-level `->` 뒤)을 goal 결론과 매칭 점수화:
- 결론 head 일치 +3.0 (강 신호: `apply L`이 되려면 L의 결론 head = goal head),
- 공유 식별자 ×0.3, 둘 다 등식 +0.5.
→ premise 재정렬.

**결과** (gold apply, retrieve된 214개 = 재랭킹 대상):
| | BM25(현재) | **타입지향 재랭킹** |
|---|---|---|
| top-1 | 22% | **36%** (+14pp) |
| top-5 | 58% | **68%** (+10pp) |
| 중앙 랭크 | 4 | **2** |

**→ selection 랭킹이 실측으로 개선.** gold lemma가 이미 retrieve된 경우, 결론매칭으로 위로 올림 = 모델이 top-k만 봐도 gold를 만날 확률↑.

**한계**: (a) 텍스트 결론매칭 = **실제 unification의 근사**(진짜 단일화는 evar·implicit 필요). (b) retrieve **안 된** lemma는 대상 아님(recall은 별도). (c) n=214, 후보생성 개선이지 end성능 보장 아님.
→ 그래도 recall 안엔 있는데 랭킹에 묻힌 gold를 끌어올림 = **90% 오선택의 일부(랭킹기인분)를 직접 겨냥.** 실제 unification(coq-lsp)로 하면 더 강해짐.

## 2. "gold lemma 줘도 +2pp" 재해석 — 천장이 아니라 하한

oracle 실험: gold lemma를 retrieval에 주입 → top-1 8%→10%(+2pp). "정답 알려줘도 소폭"으로 읽혔으나, **중요한 단서**:
- 그 +2pp는 **"gold 주입 신호를 쓰도록 학습 안 된"** 모델의 값 = **OOD**. 모델은 "여기 이게 정답 후보다"를 우선하도록 배운 적 없음 → 주입해도 무시.
- 즉 **+2pp는 하한**(훈련 안 된 모델). **주입/재랭킹/시그니처를 쓰도록 학습한 모델은 더 높을 수 있음.**
- 사용자 직관("1.3B를 잘 학습하면 더 되지 않을까")과 정합: 지금 못 쓰는 건 **능력 부재가 아니라 그 신호로 학습을 안 해서**일 수 있음. → **재랭킹/구조를 넣고 학습**하는 실험이 이걸 판별.

⚠️ 단 완전낙관 금지: 선택 위에 **다단계 도달성** 벽 있음(§10). 재랭킹이 선택을 고쳐도 경로 전체는 별개. → 그래서 "얼마나 오르나"는 실험으로.

## 3. "조립(composition)을 잘하게 학습하는 법"

목표 = 모델이 이름 표층연상이 아니라 **"이 시그니처 → 이렇게 적용"**을 배워 전이되게.

### 후보 (싼→비싼)
1. **재랭킹된 premise + 시그니처를 입력에 넣고 SFT/GRPO** ([[STRUCTURED_CONTEXT]] [SIGNATURES]/[TYPES] + §1 재랭킹). 모델이 결론매칭·시그니처를 **읽어 고르도록** 학습 → 전이가능한 선택.
2. **하드-네거티브 선택 학습**: goal에 대해 **타입 유사하지만 틀린** lemma(near-miss)를 오답으로 제시 → gold와 구별하게. contrastive/DPO. selection 예리화 직접겨냥.
3. **process reward on selection**: 전체 증명 성공 전에도 **gold lemma head를 고르면 부분보상**(PRM). 희소보상(dead 62%) 완화 + 선택을 직접 강화. (기존 코드 process reward 있음.)
4. **시그니처→적용 커리큘럼**: `forall a b, P a b -> Q a b` 시그니처를 주고 **올바른 `apply L` + 인자 형태**를 생성하는 보조 task. 조립을 명시적으로 교육.
5. **anti-unification 기반 일반화**(AU?): goal과 lemma 결론의 **최소일반화**를 계산해, "이 구조엔 이 lemma류"를 추상패턴으로 학습·매칭. (외부 AU 파일 확인 필요 — 아래.)
6. **self-play + 구조주석 expert-iteration**: 성공궤적을 [TYPES]/[SIGNATURES]/재랭킹 붙여 재학습 → 도달+선택+조립 함께.

### 왜 이게 지금 opener/compound와 다른가
- opener/compound = **여는 부품**(opening) 개선 → 병목 아니었음(parity).
- 여기 = **닫기의 선택(what)** 직접겨냥 + **전이가능 형태로 학습**. 지금까지 안 건드린 축.

## 4. AU/CLEAVE 확인 + AU 랭킹 비교 (2026-08-02)

`AU_CLEAVE_ALGORITHMS.md`(레포 루트로 옮겨짐, 128KB) 확인:
- **AU** = **anti-unification 기반 증명 검색** — goal 결론 AST의 lgg(최소일반화) 크기를 유사도로 **구조적 twin 골 상태**를 찾아 그 **증명 접미사를 few-shot 시연**으로 프롬프트에 넣음. au 0.78-0.96(MiniLM 0.29-0.50), CTXAU가 BM25 놓친 전이가능 증명 구제(z=+3.4).
- **CLEAVE** = **RESIDUAL=CONJECTURE**. 함수정의서 유도한 opener로 열고 기존 lemma로 포화 → **잔여 골 = 필요한 새 보조정리**. head심볼에 lemma 없는 가설을 subject로. zero-FP 게이트(fresh coqc + 공리⊆gold).
- 문서에 **applyshape**(head+arg 단일화 premise **선택** 점수)가 언급 — **내 §1 재랭킹과 같은 개념**. AU는 이것과 구별해 "증명템플릿 검색용 연속유사도"를 novel로 주장.
- ⚠️ **타인 미공개 논문**: AU의 novel 기여(lgg-유사도를 검색 랭킹 메트릭으로)는 **베끼지 않음**. 아래 측정도 그 기여가 이 문제(premise 선택)엔 무관함을 보임.

### AU(lgg) 독립구현 → premise 랭킹 측정 (`scripts/au_rank_probe.py`, 고전 Plotkin lgg)
| 랭커 | top-1 | top-5 | 중앙랭크 |
|---|---|---|---|
| BM25(현재) | 22% | 58% | 4 |
| **내 텍스트 재랭킹(결론 head+식별자)** | **36%** | **68%** | **2** |
| AU lgg 유사도(독립구현) | 25% | 44% | 8 |
| 텍스트+AU 블렌드 | 35% | 66% | — |

**→ AU lgg는 premise 선택에 오히려 나쁨**(top-5 44%<BM25 58%), 블렌드도 미개선. **내 재랭킹 유지(원래 걸로 밀기).**
**이유(정직)**: AU의 lgg-유사도는 **다른 문제**용 — 구조적 twin **골을 찾아 증명시연**을 고르는 것(전이 품질=tactic-flow Jaccard). premise **선택**(어느 lemma를 apply)엔 **결론 head+arg 매칭**(내 재랭킹 = applyshape류 일반개념)이 맞고 이김. → AU 논문 기여를 안 써도 이 랭킹 문제는 내 것이 최선.

### AU가 도울 수 있는 별개 채널 (안 건드림)
AU는 **proof-retrieval 채널**(어떤 증명을 few-shot 시연으로 보여줄까)엔 유효할 수 있음(구조적 twin). 단 (a) 이 A/B(premise 선택)와 다른 레버, (b) 타인 논문이라 구현 안 함. 필요 시 별도 검토.

## 5. 결론 & 다음
- **타입-지향 재랭킹 = 즉시 이득**(selection top-1 22→36%, CPU). AU lgg보다 우수 → **내 재랭킹 채택.**
- **구현·배선 완료**: `src/tactic_gen/tactic_data.py`에 `RERANK_PREMISES=1` env → ProofPremiseCollator가 premise를 결론매칭 재정렬(앞쪽 우선). `scripts/rerank_premises_typed.py` 단독측정.
- **A/B 큐 실행중**: `all_log/rerank_ab_queue.sh` — tst1000tr5091 학습 완료 후 subgoal executor로 rand200 @300s, RERANK off vs on. 결과 `all_results/rerank_{base,on}`.
- **+2pp는 하한**: 재랭킹/구조를 **쓰도록 학습**하면 더 오를 여지 — 조립학습 핵심 가설.
- **검증 우선순위**: (a) 재랭킹 A/B(진행중, inference) → 오르면 (b) SFT/GRPO에 재랭킹+시그니처 반영 → (c) 하드네거티브/PRM-selection.

관련: [[STRUCTURED_CONTEXT]] · [[REPRESENTATION_FOR_TRANSFER]] · [[opener/DDR_COMPOUND_RETRIEVAL]] · [[opener/CLOSING_FAILURE_ANALYSIS]] · [[opener/RANKING_GOLD_VS_APPLIED]]
