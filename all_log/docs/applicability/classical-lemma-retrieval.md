# 고전(비-LLM) lemma 검색 연구 — 외부 조사 (2026-08-26)

> 질문: `rewrite` 에 쓸 수 있는 lemma, `apply` 할 수 있는 lemma 를 찾는 고전 연구가
> 있는가 — LLM 말고, TF-IDF 같은 것으로.
>
> 방법: 5각도 병렬 검색 → 1차 출처 23개 fetch(전부 PDF 원문 추출) → 반증 가능한
> 주장 115건 추출 → 3표 적대적 검증.
> **검증은 도중에 중단했다**(토큰 절약). 그래서 아래 표시가 셋이다 —
> **✔ 확인**(3표 만장일치 무반증, 19건) · **✘ 기각**(2/3 이상 반증, 4건) ·
> **○ 미검증**(표결 전에 끊김, 90건). ○ 는 1차 출처에서 직접 인용한 것이지만
> **교차검증을 안 거쳤다.** 숫자를 인용할 때 이 표시를 같이 옮길 것.
>
> 원자료: `/tmp/claude-0/…/scratchpad/dr_claims.json`(주장 115건+표결), `dr_summary.txt`

---

## 0. 질문과 답

**답 — 있다. 그런데 하나가 아니라 서로 다른 두 개의 문헌이고, 섞으면 안 된다.**

| | (A) 관련성 랭킹 | (B) 적용가능성 색인 |
|---|---|---|
| 부르는 이름 | premise selection / relevance filtering | term indexing |
| 묻는 것 | "이 goal 에 **쓸모 있을 법한** 사실 200개는?" | "이 lemma 가 이 goal 에 **실제로 매칭/유니피케이션 되나**?" |
| 답의 성격 | 확률적 순위 (틀려도 됨) | 결정적 필터 (sound-but-incomplete) |
| 대표 도구 | TF-IDF·IDF, naive Bayes, k-NN, MePo, SInE | discrimination tree, substitution tree, fingerprint index |
| 시대 | 2003~2018 (ATP hammer) | 1990~2012 (ATP 내부 루프) |
| 규모 | 후보 수만 개 → 수백 개 | 후보 수십만 개 → 수십 개, **밀리초** |
| 우리 코드의 대응물 | `proof_retriever.py`, `structural` 랭커 | **없다** |

**우리 문제는 (B) 인데 (A) 도구로 풀고 있다.** `rewrite L` INVALID 889건 중
**약 87%가 "좌변이 goal 부분항과 매칭 안 됨"**([../v9/rewrite/why-rewrite-fails.md](../v9/rewrite/why-rewrite-fails.md))
이고, 환각은 8.8% 뿐이다. 이건 랭킹 문제가 아니라 **매칭 판정** 문제다.
`retrieval-theory.md` 가 포섭 격자로 손수 유도하고 있는 것이 (B) 문헌에
**1996년에 이미 책 한 권**으로 있다.

---

## 1. 기호 빈도 필터 — 학습 없는 쪽

### 1-1. MePo (Meng & Paulson 2009) — 널리 잘못 인용되는 식

Sledgehammer 의 원조 필터. **goal 의 기호를 씨앗으로 관련 기호 집합을 반복 확장**한다.

거의 모든 2차 문헌이 점수를 `r/(r+i)` (관련 기호 수 / (관련+비관련))로 소개하는데,
**원논문은 그 식을 §4.2 에서 도입했다가 §4.4 에서 명시적으로 버린다.** ✘(3-0 기각)

> "The relevance mark of a clause C calculated by `clause_mark` is **not** the
> percentage of relevant functions in C any more. Instead, we use `func_weight`
> to compute the sum of relevant functions' marks **weighted by their frequencies**."

실제로 채택된 식은 **희소도 가중(IDF 사촌)** 이다. ✔(3-0 확인)

```
점수(C) = M / (M + |IR|)              M   = Σ_{F ∈ 관련기호(C)} w(freq(F))
                                      w(n) = 1 + 2/log(n+1)      (n = 코퍼스 내 출현 횟수)
                                      |IR| = 비관련 기호의 raw 개수 (가중 안 함)
```

* 분자만 가중한다 — **드문 기호가 맞으면 크게 벌고, 흔한 기호는 거의 못 번다.**
* 더 완만한 `1 + 1.4/log(log(n+2))` 도 되지만 `1 + 1/√n` 은 **빈출 기호를 과벌**해서 나쁘다. ✔
* 통과선은 라운드마다 **올라간다**: `p' = p + (1−p)/c`, 최적 `p = 0.6, c = 2.4`
  (`c` 를 크게 하면 나빠지고, 실측한 건 1.6·2.4·3.2 뿐). ✔(3-0)
* 효과: Isabelle 파생 문제에서 평균 **909 → 142 절**(6.4배 축소), Vampire 성공률이
  `p = 0.6` 에서 **뾰족하게 정점**. 그 위로는 **필수 공리가 잘려서** 떨어진다. ✔(3-0)
* 알려진 실패 형태 두 가지 ○ — ① goal 기호가 전부 흔하면 **변별 못 함**,
  ② 최선우선 확장이라 뿌리 근처 사실이 **starvation**.
  MaSh 논문 Example 2: 필요한 lemma 4개가 MePo 에서 **6807/6808위**, MaSh 는 45위 안, MeSh 는 77위 안.

  ★ 우리 `EQ_W = 3.0` 과 같은 성격의 상수를 저쪽은 **격자탐색으로 정하고 그 격자를 논문에 적었다.**
    우리도 `p`·`c` 자리에 해당하는 상수를 적어 두는 편이 낫다.

### 1-2. SInE (Hoder & Voronkov, CADE-23 2011) — "가장 드문 기호만 방아쇠를 당긴다"

학습 전혀 없음. `occ(s)` = 기호 `s` 를 포함하는 공리 수라 할 때 ✔(3-0)

```
trigger(s, A)  ⟺  A 에 나오는 모든 기호 s' 에 대해 occ(s) ≤ occ(s')
```

즉 **공리 A 는 자기 안에서 가장 희귀한 기호로만 끌려나온다.** goal 기호에서 시작해
반복 전파(k-step). `subclass`·`instance-of` 같은 편재 기호가 라이브러리 전체를
끌고 오는 것을 막는 게 설계 목적이다.

불완전하다는 걸 인정하고 손잡이 셋을 단조롭게 달아 놨다 ✔(3-0):
`tolerance t ≥ 1` (`occ(s) ≤ t·occ(s')` 로 완화, 기본 1) ·
`depth d` (전파 횟수 상한, 기본 ∞) · `generality g` (`occ(s) ≤ g` 면 무조건 방아쇠, 기본 0).

**효과가 부수적이 아니라 결정적이다** ○ — TPTP 4.0.1 에서 원자 8만 개 이상 문제
373개 중 SInE 켜야만 풀린 게 187개, 꺼야만 풀린 건 **3개**. 64만 개 이상에서는 50 대 **0**.
CASC LTB 부문을 2008~2010 내내 SInE 계열이 쓸어갔다. ✔(3-0)

  ★ 다만 **수학 라이브러리엔 잘 안 듣는다** ○ — Mizar 는 평균 44,925 공리 / 332,143 원자라
    depth 1 에서도 이미 4,000개 넘게 고른다. 저자들이 "Mizar 가 모든 SInE 프로버에게
    훨씬 어려운 이유"로 이걸 지목한다. ITP goal 은 가설과 기호가 많아서 그렇다.
    **Coq 도 같은 쪽**이다.

  ★ 그리고 SInE 는 **검색 지표로는 최악인데 실전 성능은 좋다**(§3-3 참조).

---

## 2. 고전 ML premise selection — 학습하되 신경망 아닌 쪽

### 2-1. 자질 표현 — 여기가 제일 실용적인 부분

전부 **손으로 만든 희소 기호 자질**이다. 학습되는 임베딩이 아니다.

| 시스템 | 자질 | 가중 |
|---|---|---|
| **MaSh** (Isabelle) ✔ | 깊이 **2** 까지의 1차 **부분항 패턴**, 변수는 **자기 타입으로 치환**. `g (h x a)` → `g, g(h), h, h(τ), h(a), h(τ,a), a, τ` ○. + 타입·타입클래스(상위클래스 포함) · **소속 theory 이름** · local/global 플래그 | **IDF 그대로**: `w(f,Φ) = ln(|Φ| / |{φ : f ∈ F(φ)}|)` ✔(3-0) |
| **MizAR 40/60** (Mizar) ○ | MaLARea 식 — 기호·항·부분항 전부. 자질 안의 **변수를 전부 `A0` 하나로 리네임**해서 유사관계를 넓힘. cp(항그래프 상수·경로) · sub(부분항) · au(**반유니피케이션 자질**) · eni(ENIGMA 자질) · uni(합집합) | **TF-IDF** + 의존성 많은 사실 할인 |
| **CoqHammer** (Coq) ○ | 문장에 나오는 **상수**(기본 논리 상수 제외, 변수는 `X` 하나로 정규화) + **파스트리에서 변을 공유하는 상수·상수변수 쌍**. 예: `F(between_le) = {Between.between, Between.between-X, nat, le, le-X}` | **TF-IDF** |
| **Flyspeck/HOLyHammer** ✔(3-0) | 정규화된 부분항·타입·원자식 문자열 집합. 타입변수는 전부 `A` 하나로. 변수 정규화 4종 비교 — `syms0`(전부 A0) · `syms`(연번) · **`symst`(변수를 그 타입 텍스트로: Anum/Areal — 대부분의 학습에 쓴 것)** · `symsd` | — |
| **MPTP2078 3종**(SNoW·MOR-CG·BiLi) ○ | 기호·항의 **유무 이진 지시자** (TF-IDF **아님**). BiLi 는 랜덤 프로젝션으로 100차원, 20회 반복 평균 | 없음 |
| **ATPboost** ○ | (conjecture 자질벡터 ‖ premise 자질벡터) **연접** → XGBoost 이진분류 | Mizar-40 자질 재사용 |

  ★ **`rewrite`·`apply` 관점에서 중요한 것**: MaSh 의 "깊이 2 부분항 패턴 + 변수→타입" 은
    사실상 **얕은 discrimination tree 키를 자질로 뿌린 것**이다. 즉 (A) 진영도
    결국 (B) 의 항 구조를 흉내내는 쪽으로 수렴했다. 우리 `structural` 랭커의
    결론머리·트리일치 항이 정확히 같은 자리에 있다.

### 2-2. 학습기 — 놀랄 만큼 단순하다

* **sparse naive Bayes** 와 **k-NN**, 이 둘이 전부다. MaSh 는 이 둘을 Standard ML 로
  Isabelle 안에 재구현했고 ✔, CoqHammer 는 **그대로 이식**했다 ○.
* CoqHammer 의 k-NN 유사도 ○: `s(a,b) = Σ_{f ∈ 공유자질} w(f)^τ1`, 의존성 기반 관련도에 `τ2`,
  실측 상수 **τ1 = 6, τ2 = 2.7**, 그리고 **k 고정 안 함** — k=1 에서 시작해 충분한
  사실이 모일 때까지 늘린다.
* MaSh 도 같은 상수(τ1=6, τ2=2.7)와 NB fudge(σ1=30, σ2=5, σ3=0.2, σ4=−18)를 쓴다 ○.
* **MeSh** = MePo(기호) 와 MaSh(학습)를 **각각 0.5 가중으로 순위-확률 결합**. ✔(3-0)
  이게 Isabelle 의 기본값이 됐다.
* 부스팅 계열도 있다 ○ — ATPboost(XGBoost 이진), MizAR 60 의 LightGBM,
  Lean 용 random forest(Piotrowski 2023).
  ATPboost 는 음성 샘플 비율이 중요하다고 보고한다: ratio 1(균형) 74.0% →
  ratio 16 **80.1%** 에서 포화. **불균형이 낫다.**

  ★ 우리 [gbdt.md](../premise/gbdt.md)·[problem_of_gbdt.md](../premise/problem_of_gbdt.md) 가
    GBDT 를 접은 것과 방향이 반대다. 저쪽이 이긴 조건(음성 비율 16:1, 짧은 증명만
    양성으로)을 우리가 맞춰 봤는지 확인해 볼 값어치는 있다.

### 2-3. 검색 지표는 최종 성능을 예측 못 한다 — 이게 제일 중요한 교훈

MPTP2078 (2078 문제, 문제당 평균 **1976.5** 후보) 에서 ✔(3-0):

| 랭커 | AUC | Vampire 5s 로 푼 문제 |
|---|---|---|
| SNoW (naive Bayes) | 0.9713 | — |
| BiLi | 0.9615 | — |
| MOR-CG | 0.8806 | top-70 에서 **726** |
| Aprils (LSA) | 0.6443 | — |
| **SInE** | **0.4212** ← 무작위보다 나쁨 | 60~100 구간에서 **SNoW 와 대등** |

> "The surprising fact (given the machine learning performance) is that SInE performs
> very well, on par with SNoW in the range of 60-100 premises. **This indicates that
> SInE finds proofs that are very different from the human proofs.**"

**사람 증명을 정답으로 놓고 재는 Recall@k·AUC 는 ATP 성공률과 어긋난다.** 실제로
모든 방법의 합집합이 Vampire 5s 로 **1197**문제를 푸는데, 사람 증명의 전제를
정확히 준 Vampire 10s 는 **1105**문제밖에 못 푼다. ✔(3-0)

  ★ 우리 지표 체계([../premise/README.md](../premise/README.md) 의 `A`/`C`/`R`/`ALL`)도
    **gold lemma 를 정답으로 놓는다.** 위 결과는 그 분모가 상한이 아님을 뜻한다 —
    gold 를 못 찾아도 다른 lemma 로 풀리는 경로가 있다. 우리 `C`(assert 후 재검색)가
    그 방향의 일부를 이미 재고 있다.

### 2-4. 몇 개를 넘길 것인가 — 비단조 최적점

거의 모든 랭커에서 **70~80개 근처에서 정점**을 찍고 그 뒤로는 떨어진다 ✔ —
recall 이 올라가도 ATP 탐색공간이 더 빨리 커진다. 2단계 구조를 쓰면 한계가 늘어난다 ○:
1단 랭커가 512개를 넘기고 ATP 자신의 SInE 가 2단 필터를 하면 버티는데,
2단 선택이 없는 Z3 는 256개 12.4% → 740개 **6.2%** 로 무너진다.

  ★ 우리 토큰 예산(896)이 프롬프트에 10~22개만 남기는 것은 이 관점에서
    **꼭 나쁜 게 아니다.** 저쪽 최적점도 수백이 아니라 수십이다.
    다만 Judgement Day 는 **실제 성공한 증명이 평균 2~3개 사실만 쓴다**고 보고한다 ○ —
    즉 진짜 필요한 건 몇 개, 문제는 그 몇 개가 상위에 오느냐다.

### 2-5. 순위 합치기 — 우리가 쓰는 RRF 와 같은 계열

MizAR 60 ○: 알고리즘마다 점수 스케일이 달라 **비교 불가**하므로 점수 평균이 아니라
**순위 융합**을 쓴다 — 가중 역순위 `1 / Σ_i (w_i / r_i)`. 산술·최소·기하·조화 중
**조화평균이 제일 좋았다.**
MPTP2078 ○: MOR-CG 와 SInE 를 **동일 가중 선형 결합**하면 top-70 에서 726 → **797**(+10%),
top-20 에서는 476/341 → **604**(+27%).

  ★ 우리 랭커도 RRF 로 세 신호를 섞는다([retrieval-theory.md](../premise/retrieval-theory.md)).
    **학습 신호와 기호 신호를 섞는 게 항상 이긴다**는 게 이쪽의 반복된 결론이다.

---

## 3. 적용가능성 색인 — `rewrite`/`apply` 에 직접 대응하는 문헌

여기가 사용자가 물은 "**rewrite 에 적용 가능한** lemma 찾기"의 정확한 답이다.

### 3-1. Term indexing (Graf, LNCS 1053, 1996) ○

> "the technique that makes automated reasoning systems efficient by providing
> **rapid access to first-order terms having specific properties**"

294쪽짜리 단행본이 통째로 이 주제다. 분류는 셋 — attribute-based(43–50p) ·
set-based(51–126p) · **tree-based(127–199p)**. 후자 둘에 discrimination tree ·
substitution tree · path indexing 이 들어간다. 201–231p 는 **기법 간 정량 비교**,
233–263p 는 실제 프로버 안에서의 배치. **검색 속도뿐 아니라 삽입·삭제(유지보수)를
1급 문제로 다룬다** — 규칙 집합이 커질 때 성능이 무너지지 않게.

Handbook of Automated Reasoning Vol. II 26장 (Sekar·Ramakrishnan·Voronkov) 이 표준 서베이.
Vampire 쪽은 code tree(Riazanov & Voronkov, JELIA 2002).

### 3-2. Fingerprint indexing (Schulz, IJCAR 2012) — 우리한테 제일 쓸모 있는 것 ○

항을 **고정된 위치 몇 개에서만 뽑은 짧은 고정길이 벡터**로 요약해 얕은 trie 에 넣는다.

```
자질 알파벳:  F ⊎ {A, B, N}
  f  = 그 위치의 실제 최상위 함수기호
  A  = 그 위치가 변수
  B  = 그 위치가 변수 아래  (인스턴스화로 생길 수 있음)
  N  = 그 위치는 어떤 인스턴스에서도 존재 불가
```

* **matching 과 unification 을 둘 다** 지원한다 — 즉 `rewrite`(좌변이 goal 부분항과
  **매칭**)와 `apply`(결론이 goal 과 **유니피케이션**) **양쪽에 그대로 대응**한다.
* 판정은 5×5 표 두 개를 성분별로 보는 것뿐이다. **matching 표가 unification 표보다 엄격**
  (예: `f1` 대 `A` 는 unification 은 Y, matching(s→t)은 N).
* **sound-but-incomplete**: 지문 불일치는 비유니피케이션의 **필요조건**이다. 통과한
  후보는 진짜 매칭으로 다시 검사해야 한다. 즉 **싸고 안전한 사전 필터**.
* 성능 ○: TPTP 5.2.0 5,824문제에서 `FP6M`(위치 여섯 개: ε, 1, 2, 3, 1.1, 1.2)만으로
  E 총 실행시간 16,062s → **6,000s**(60% 이상 감소), 유니피케이션 시간 2,545s → 99s(**25배**).
* **가장 크게 이긴 곳이 backward rewriting** ○ — 새 규칙 `l ≃ r` 이 이미 처리된 항 중
  어디에 적용되나: 2,280s → **39s (58배)**, 색인 유지비 포함해도 25배.
* discrimination tree(NPDT)와 거의 대등(6000.2s vs 6082.2s)하지만 **유지비가 싸다**.

  ★ **우리 상황에 그대로 옮겨진다.** `rewrite L` 이 실패하는 87% 는
    "`L` 의 좌변이 goal 어디에도 없다" 이고, 지문 색인은 goal 의 부분항 집합에 대해
    **후보 lemma 를 O(1) 에 쳐낸다**. 6개 위치짜리 벡터면 충분하다는 게 실측이다.
    이건 학습도 LLM 도 필요 없고, `EQ_W` 같은 상수도 필요 없다 —
    **전부 아니면 전무가 아니라, 위치별로 부분점수가 나온다**는 점에서
    [retrieval-theory.md](../premise/retrieval-theory.md) 가 찾던 "구조 신호의
    연속적 형태"에 정확히 해당한다.

### 3-3. Coq 이 실제로 하는 것 ○ (Rocq 레퍼런스 매뉴얼)

| 기제 | 실제 구현 |
|---|---|
| `auto` 힌트 DB | **머리기호 → 힌트 리스트 맵**. goal 머리 상수와 같은 힌트만 꺼낸다. 즉 **최상위 기호 색인 1단계**뿐, discrimination tree 아님 |
| `discriminated` 모드 | 머리기호 조회 **뒤에** 구조 필터를 하나 더. **기본은 꺼져 있고**, 매뉴얼은 성능상 켜기를 권함 |
| `Hint Resolve` | lemma 타입의 **결론**에서 자동으로 검색 키를 뽑음. 비용 = `simple apply` 가 만들 subgoal 수, 낮은 비용 먼저 (순서만 정하고 가지치기는 안 함) |
| **결론 색인의 구조적 한계** | **전제의 변수가 결론에 안 나오는 lemma(예: 추이성)는 `auto` 가 아예 못 쓴다.** evar 를 남길 수 있는 `eauto`/`typeclasses eauto` 만 가능 |
| `Hint Rewrite`/`autorewrite` | **auto 힌트 DB 와 완전히 별개**(auto 는 무시). 그리고 **색인 검색이 아니라 베이스의 모든 규칙을 소진적 fixpoint 반복** — 종료 보장 없음 |

  ★ 두 줄이 우리 문서와 정면으로 맞물린다.
    ① `autorewrite` 에 **색인이 없다** → "goal 에 적용 가능한 rewrite 규칙 찾기"는
       Coq 안에 기성품이 없다. 우리가 만들면 그게 §3-2 다.
    ② **결론에 안 나오는 전제 변수** → [../v9/apply/apply-automation-gap.md](../v9/apply/apply-automation-gap.md)
       의 `apply L a b` 위치인자 문제(44.1% 실패)와 같은 뿌리다. 결론만 보고 색인하면
       `a b` 를 어디서 가져올지 알 수 없다.

---

## 4. 숫자 — 고전 파이프라인은 실제로 얼마나 푸나

| 시스템 / 코퍼스 | 설정 | 완전자동 성공률 | 표시 |
|---|---|---|---|
| **Judgement Day** (Isabelle 1240 goal) | E+SPASS+Vampire 병렬 120s | 54% ATP / **48%** Metis 재구성 | ✘ 부분기각(§6) |
| 〃 (사소한 goal 보정 후) | `simp`/`auto` 로 이미 닫히는 53% 를 걷어내면 | **~34%** | ✔(3-0) |
| **MizAR 40** (Mizar MML 57,897) | 14방법 병렬 30s / 14 CPU | **40.6%** | ○ |
| 〃 사람이 고른 전제를 주면 | | 56.2% | ○ |
| **MizAR 60** (같은 MML) | 420s, 95슬라이스 포트폴리오 | **58.36%** | ○ |
| 〃 bushy(사람 전제) | | ~75% | ○ |
| **Flyspeck/HOL Light** (14,185정리) | 14방법 병렬 30s | **39%** | ✔(3-0) |
| 〃 최고 단일 방법 | 30s / 300s | 24.1% / 26.8% | ✔ |
| 〃 사람 의존성을 그대로 준 재증명(상한) | 900s, 합집합 | 43.2% | ○ |
| **CoqHammer** (Coq 8.5 stdlib 9,276문제) | 8전략, ATP 30s, ~40s/8CPU | **40.8%** | ○ |
| 〃 최고 단일 전략 (Vampire + k-NN 1024) | | 28.8% | ○ |

읽는 법 두 가지:

1. **단일 방법과 포트폴리오의 차이가 크다.** Flyspeck 24.1% → 39%, MPTP2078 726 → 797.
   시간을 10배 주는 것(30s→300s)은 조합에 **+0.3%** 밖에 못 준다 ✔ — 다양성이 시간을 대체한다.
2. **Coq 이 제일 어렵다.** 같은 알고리즘이 HOL/Isabelle 에서 200~300개면 덮는 의존성을
   Coq stdlib 에서는 **499~530개**를 봐야 덮는다 ○. 저자들은 Coq 증명항 의존성이
   커널이 암묵적으로 쓰는 정보를 빠뜨리기 때문으로 본다.

  ★ 우리가 [../premise/README.md](../premise/README.md) 에서 프롬프트 기준 95% 를 재는 것과
    분모가 다르다(우리는 "gold 가 후보 풀에 있는 스텝"). 위 숫자는 **end-to-end**다.
    직접 비교하면 안 된다.

---

## 5. 고전 vs 신경망 — 고전이 아직 안 죽었다

| 비교 | 결과 | 표시 |
|---|---|---|
| **DeepMath** (2016, Mizar) | 신경망 def-CNN 66.4% vs **손자질 k-NN 65.1%** — 1.3%p 차 | ○ |
| 〃 합집합 | **74.25%** — 신경망 둘을 합치는 것보다 이득이 큼 | ○ |
| **Magnushammer** (2023, Isabelle PISA) | TF-IDF **31.8%** · BM25 30.6% · Sledgehammer 38.3% · ada-002 36.1% · 학습 retriever **59.5%** | ○ |
| **LeanHammer** (2025, Mathlib) | **MePo 가 ReProver(218M) 를 이긴다** — recall@32 42.1% vs 38.7%, 증명률 27.5% vs 22.3% | ○ |
| 〃 합집합 | LeanPremise ∪ MePo = **38.2/39.6%** (신경망 단독 30.1/33.3%, 정답전제 상한 41.0/43.0%) | ○ |
| 〃 recall 과 증명률의 괴리 | recall@32 은 **+73%** 인데 증명률은 **+21%** 뿐 | ○ |

세 줄 요약:

* **TF-IDF 단독은 약하다** (31.8%) — 그러나 0 은 아니고, 아무 도메인 지식 없이 그 정도다.
* **기호 필터는 아직 경쟁력 있다** — 2025년 Lean 에서 MePo 가 신경 retriever 를 이겼다.
* **거의 항상 합집합이 최고다.** 2012년(MOR-CG+SInE), 2016년(CNN+kNN), 2016년(MeSh),
  2025년(LeanPremise+MePo) — 네 번 다 같은 결론이다.

  ★ 이건 우리 방향과 어긋나지 않는다. 우리는 이미 RRF 로 여러 신호를 섞는다.
    빠진 건 **(B) 계열 신호가 하나도 없다는 것**이다.

---

## 6. 기각된 주장 (4건) — 되풀이하지 않으려고 남긴다

| 주장 | 표결 | 왜 틀렸나 |
|---|---|---|
| "MePo 의 핵심 점수는 `m/n` 기호중첩비 + 고정 통과선" | 3-0 | **인용 채굴.** 그 문단은 원논문 §4.2 가 도입했다 §4.4 에서 **버리는** 초안이다. 실제는 빈도가중 `M/(M+|IR|)`, 통과선은 매 라운드 상승. → §1-1 |
| "Judgement Day 는 pre-neural 최대 규모 평가" | 3-0 | 논문 자신은 "**to date**"(2010) 라고 시간한정했고 대상도 premise selection 이 아니라 ITP↔ATP 연결 전반. 이후 MaSh 평가들이 더 크다 |
| "Sledgehammer 의 premise selection **은**(현재형) MePo 다" | 2-3 | 인용은 정확하나 **시제가 틀렸다.** Isabelle2013/2014 이후 기본은 **MeSh**(MePo+MaSh). 2010년 논문을 현재형으로 옮기면 안 됨 |
| "Judgement Day theory 별 12%(FFT)~67%(FTA)" | 3-0 | 표 오독. ESV 120s 행에서 FFT 는 **22/18**, 12 는 E-5s 행 값이거나 FFT 의 **문제 비중** 12%. 논문 자신의 표현은 "below 20% up to 60%" |

**부분(1/3 반증) 2건** — SInE Table 5 의 ≥80,000 원자 행이 논문 본문은 138, 표는 **187**
(논문 내부 불일치. 누적 열이라 단조여야 하므로 187 이 맞다). MePo 실패 예시의 순위가
판본에 따라 3742위 / 6807위로 다르게 적혀 있다(ITP 2013 판 vs JAR 2016 판).

---

## 7. 우리한테 무엇을 쓸 수 있나 — 우선순위

> **★ 실측 후기 (2026-08-27)** — 아래 1순위(지문색인을 `rewrite`/`apply` 후보 필터로)를
> 실제로 걸어 봤다. **음성이다** — top-100 진입률이 −10.8pp / −1.4pp.
> 원인은 자료구조가 아니라 **elaboration**(암묵인자·섹션변수·notation·evar)이다.
> 전문: [applicability-filter.md](applicability-filter.md)

1. **지문 색인(fingerprint index)을 `rewrite` 후보 필터로** (§3-2).
   6개 위치 벡터 + matching 표. goal 부분항 집합에 대해 좌변이 매칭 **불가능한** lemma 를
   먼저 쳐낸다. `rewrite` INVALID 의 87% 가 이 한 판정에 걸린다.
   **학습 불요·상수 불요·Coq 호출 불요.** 가장 확실한 레버.
2. **MePo 식 희소도 가중을 우리 랭커에 명시적으로** (§1-1).
   `w(n) = 1 + 2/log(n+1)` — 분자만 가중, 분모는 raw. 우리 IDF 항과 형태가 다르다.
   특히 **`1/√n` 형태는 저쪽이 실측으로 버린 것**이니 우리도 그 함수형은 피한다.
3. **결론에 없는 전제 변수 문제를 색인 설계에 반영** (§3-3).
   `apply L a b` 실패는 결론 기반 색인의 알려진 사각이다. eauto 처럼 evar 를 남기는
   검색 아니면 못 푼다는 게 이미 문서화돼 있다.
4. **평가 분모 재검토** (§2-3). gold lemma 기준 recall 은 ATP/증명 성공률과 어긋난다는
   실측이 반복해서 나온다. 우리 `C` 지표가 그 방향이니 더 밀어 볼 값어치가 있다.
5. **GBDT 재고는 조건부** (§2-2). ATPboost 가 이긴 조건(음성:양성 = 16:1, 짧은 증명만 양성)이
   우리 실험 설정과 다르면 다시 볼 만하다. 아니면 [problem_of_gbdt.md](../premise/problem_of_gbdt.md) 결론 유지.

---

## 8. 미검증 (조사 중단으로 fetch 못 한 것)

검색에서 나왔지만 **원문을 안 읽었다** — 필요하면 여기서 이어서 하면 된다.

* **FindFacts: A Scalable Theorem Search** (Huch & Krauss, arXiv 2204.14191, 2022) —
  Isabelle 정리 **검색 엔진**. `find_theorems` 의 확장판. (A)/(B) 중간 지대라 우리와 제일 가깝다.
* **Partially Adaptive Code Trees** (Riazanov & Voronkov, JELIA 2002) — Vampire 색인.
* **Term Indexing** (Sekar·Ramakrishnan·Voronkov, Handbook of AR Vol. II 26장) — fetch 실패.
* Isabelle **`find_theorems`**, Coq **`Search`/`SearchPattern`/`SearchRewrite`** 의 구현 —
  매뉴얼만 읽었고 소스는 안 봄.
* **ENIGMA**, **MaLARea** 원논문 — 다른 논문의 인용으로만 확인.
* Nagashima **PaMpeR**, Gauthier & Kaliszyk **개념 매칭/유추** 계열 — 검색에도 안 걸림.

---

## 9. 출처 (전부 1차, PDF 원문 추출 확인)

| 논문 | 링크 |
|---|---|
| Meng & Paulson, *Lightweight Relevance Filtering…*, J. Applied Logic 7, 2009 | https://www.cl.cam.ac.uk/~lp15/papers/Automation/filtering.pdf |
| Hoder & Voronkov, *Sine Qua Non for Large Theory Reasoning*, CADE-23, 2011 | https://doi.org/10.1007/978-3-642-22438-6_23 |
| Böhme & Nipkow, *Sledgehammer: Judgement Day*, IJCAR 2010 | https://www21.in.tum.de/~nipkow/pubs/ijcar10.pdf |
| Kühlwein et al., *Overview and Evaluation of Premise Selection Techniques*, IJCAR 2012 | http://grid01.ciirc.cvut.cz/~mptp/premisealgos.pdf |
| Kühlwein·Blanchette·Kaliszyk·Urban, *MaSh: Machine Learning for Sledgehammer*, ITP 2013 | https://www.tcs.ifi.lmu.de/staff/jasmin-blanchette/mash.pdf |
| Blanchette et al., *A Learning-Based Fact Selector for Isabelle/HOL*, JAR 57(3), 2016 | https://doi.org/10.1007/s10817-016-9362-8 |
| Kaliszyk & Urban, *Learning-Assisted Automated Reasoning with Flyspeck*, JAR 2014 | https://arxiv.org/abs/1211.7012 |
| Kaliszyk & Urban, *MizAR 40 for Mizar 40*, JAR 2015 | https://arxiv.org/abs/1310.2805 |
| Jakubův et al., *MizAR 60 for Mizar 50*, ITP 2023 | https://arxiv.org/abs/2303.06686 |
| Czajka & Kaliszyk, *Hammer for Coq*, JAR 61, 2018 | https://www.mimuw.edu.pl/~lukaszcz/coqhammer.pdf |
| Piotrowski & Urban, *ATPboost*, IJCAR 2018 | https://arxiv.org/abs/1802.03375 |
| Alemi et al., *DeepMath*, NeurIPS 2016 | https://arxiv.org/abs/1606.04442 |
| Mikuła et al., *Magnushammer*, 2023 | https://arxiv.org/abs/2303.04488 |
| *Premise Selection for a Lean Hammer*, 2025 | https://arxiv.org/abs/2506.07477 |
| Graf, *Term Indexing*, LNCS 1053, Springer 1996 | https://doi.org/10.1007/3-540-61040-5 |
| Schulz, *Fingerprint Indexing for Paramodulation and Rewriting*, IJCAR 2012 | https://doi.org/10.1007/978-3-642-31365-3_37 |
| Rocq/Coq Reference Manual — programmable proof search | https://coq.inria.fr/refman/proofs/automatic-tactics/auto.html |
