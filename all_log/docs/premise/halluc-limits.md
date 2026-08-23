# 환각의 원리적 한계와 cut(assert) 의 위치

> 근거는 전부 이 저장소에서 실측한 값이다. 상세 로그는 `experiment.txt` §27~§29,
> `substep.md`, `eqx.md`, `rankers.md`.
>
> **읽기 전 두 가지**
> 1. 사례의 프롬프트에서 premise 이름이 `L9`·`T0`·`f5` 로 보이는 것은 **v8 이름 익명화**
>    때문이다(`NORMALIZE_PREMISES=1`). 사전학습 암기를 막으려고 프롬프트와 정답에
>    **같은 매핑**을 적용한 것이고, 추론 시 역매핑한다. 원래 이름이 아니다.
> 2. 토글 안쪽은 **왼쪽에 파란 세로선**으로 표시했다.

---

## 0. 먼저 "환각 제거" 를 두 뜻으로 갈라야 한다

이 문서에서 **환각** = *정답 tactic 이 프롬프트 어디에도 없는 이름을 부른다.*
모델이 그걸 맞히려면 (a) 사전학습 가중치에서 꺼내거나 (b) 찍는 수밖에 없다.
둘 다 프롬프트에 근거가 없다.

| | 뜻 | 가능한가 |
|---|---|---|
| **약한 뜻** | 모델이 프롬프트에 없는 이름을 **뱉지 않게** 한다 | **지금도 가능**. `DROP_HALLUC=1` 로 학습에서 빼거나 디코딩을 프롬프트 어휘로 제약하면 0% |
| **강한 뜻** | 그런 스텝에서도 **올바른 이름을 근거 있게** 내놓게 한다 | 아래 이유들로 막힌다 |

약한 뜻은 환각을 **실패로 옮길 뿐** 성능을 만들지 않는다. 이 문서는 강한 뜻을 다룬다.

---

## 1. 왜 원리적으로 막히나

### 1-1. ★ 필요한 lemma 는 goal 의 함수가 아니다

검색기는 `필요한 premise ≈ argmax_p sim(goal, p)` 를 가정한다. 이 가정은
**필요한 것이 goal 에 의해 결정된다**는 전제를 깔고 있다. 그런데 다음에 쓸 lemma 는
goal 이 아니라 **증명 전략**이 정한다. §4-1 에 완전한 사례가 있다.

**실측** — 풀을 +15.9% 넓혀 제외 종류를 실제로 승격시킨 뒤 순위를 쟀다(예제 800):

| 항목 | 값 | 분모 / 분자 |
|---|---|---|
| 결손 이름 | 19 | — |
| 검색 100개 안에도 없음(느슨히 봐도) | **15 (78.9%)** | 15 / 19 결손 이름 |
| 검색 결과에는 있음 | 3 (15.8%) | 3 / 19 |
| └ 그중 예산에 들어갈 상위 22위 안 | **1 (5.3%)** | 1 / 19 |
| 순위 분포 | 중앙 **70위** · p25 21 · p75 77 | 검색에 있는 것만 |

유사도 신호가 약한 게 아니라 **없다.** 예산을 4.5배 늘려 상위 100까지 실어도
19건 중 3건만 건진다.

### 1-2. ★ 이름은 임의적이다 → 익명화와 정면 충돌

`Nat.add_comm` 은 `foo_17` 이어도 논리적으로 아무 문제가 없다. **lemma 이름은
논리적 내용을 담지 않는다.** "이 이름이 이 명제를 가리킨다" 는 라이브러리의 관습이지
수학에서 유도되지 않는다.

따라서 이름이 프롬프트에 없으면 맞히는 경로는 **암기** 하나뿐이다. 여기서 충돌이 생긴다:

> **근거 있는 모델**을 만들려고 익명화하면 → 프롬프트 밖 이름을 맞히는 유일한 경로가 사라진다.
> **프롬프트 밖 이름을 맞히게** 두면 → 그건 정의상 근거 없는 생성, 곧 환각이다.

**실측** — 그 암기 채널의 크기. Qwen2.5-Coder-3B · 가짜는 `_` 조각을 섞어 만들어
토큰 구성이 동일 · 맥락은 전 부류 동일(프로젝트명만).
**분모 = 부류당 표본 400개, 분자 = 실명의 NLL 이 가짜보다 낮았던 횟수.**

| 부류 | 실명 선호 | 분자/분모 | 우연(50%) 대비 |
|---|---|---|---|
| 프로젝트 Lemma | 61.8% | 247/400 | 4.7σ |
| 프로젝트 Ltac | 61.5% | 246/400 | 4.6σ |
| notation 이 가린 이름 | 53.5% | 214/400 | 1.4σ **(유의하지 않음)** |
| stdlib Lemma (대조) | 62.5% | 250/400 | 5.0σ |

익명화는 이 61.8% 를 50%(우연)로 끌어내리는 장치, 즉 **의도적으로 환각 경로를 죽이는
것**이다. "환각도 없애고 프롬프트 밖 이름도 맞힌다" 는 동시에 성립할 수 없다.

### 1-3. ★ goal 은 항(term)의 **손실 있는 렌더링**이다

Coq 이 보여 주는 goal 문자열은 내부 항의 투영이고, 그 과정에서 이름이 **설계상** 지워진다.

| 지우는 장치 | 실측 사례 |
|---|---|
| notation | goal `A ⊢I phi` ← 실제 `@prv _ _ _ **intu** A phi` · 정답이 `intu` 를 쓴다 |
| notation (Inductive `where`) | goal `st =[ c ]=> st'` ← `ceval` · 정답이 생성자 `E_IfFalse` 를 쓴다 |
| 축약 notation | `Notation ZeroR := ([0]:R).` · goal 엔 `[0]` 만 보인다 |
| 정의 펼침 | goal `Tr (-1) (hfiber ...)` ← `merely A := Build_HProp (Tr (-1) A)` |
| implicit 인자 · coercion · canonical structure · typeclass instance | 이름 없이 해소된다 |

앞의 넷은 색인을 만들어 되돌렸다(`notation_index.json` · `unfold_index.json`).
그러나 **렌더링은 단사가 아니므로 일반적으로 역상을 복원할 수 없다.**

극단적 실측: `apply Build_PartFunct with (fun x : F => x [#] [0]) (cf_rcpcl F).` 의
goal 은 **식별자가 0개**다 — 전부 `[#]`·`[0]` 같은 notation 기호다. 검색할 어휘 자체가 없다.

### 1-4. 롱테일 — 통계적 서명이 없다

결손 이름의 프로젝트 내 등장 빈도 순위 (**분모 = 그 프로젝트의 서로 다른 식별자 수**):

    merely               84위 / 11,920
    isequiv_adjointify  335위 / 11,920
    cancelL           2,639위 / 11,920
    inv_pp            4,426위 / 11,920
    setU2_2           2,614위 / 12,045   프로젝트 전체에서 **1회** 등장
    cs_bin_op_strext  4,116위 / 11,324   1회
    cartpairB_Out     7,826위 / 10,297   1회

**한 번 등장하는 이름은 통계가 없다.** 빈도 사전도 공기(co-occurrence) 패턴도 안 걸린다.
Zipf 꼬리라 유한한 주입 예산은 머리만 덮는다. 실측으로 top-30 은 아무것도 못 잡았고
top-500 은 2,000토큰이라 예산(896)에 안 들어간다. → **"관용구 사전" 안은 접었다.**

### 1-5. 순환성 — 무엇을 넣을지 알려면 증명을 알아야 한다

"필요한 premise 를 넣어 주면 되지 않나" 는 **오라클**이다. 무엇이 필요한지는 정답을 봐야 안다.

**실측** — `eqx` 의 지시자 `1[d_AU(p,g)=0]` 이 발화한 질의 비율
(**분모 = 그 영역의 질의 수, 분자 = 지시자가 1이 된 질의 수**):

    A 영역(원래 goal)          7.0%
    C 영역(assert 후 재검색)   95.8%      ← 90pp 차이

C 는 lemma 진술로부터 goal 을 만든 영역이라 "딱 맞는 premise 가 존재한다" 가 자동으로
참이었다. 그 차이가 순환성의 크기다. (이 때문에 `eqx` 를 랭커에서 뺐다 — `rankers.md` §6-3)

### 1-6. 예산 — 부차적이지만 곱해진다

premise 예산 896토큰 ≈ **22개**. 프로젝트 선언은 1~2만 개다. 700:1 압축이다.
다만 이건 **1-1 이 없었다면 풀 수 있는 문제**다 — 신호가 있으면 22개 안에 넣을 수 있다.
신호가 없는 상태에서 예산만 늘리는 건 소용이 없다(위 순위 분포).

---
## 2. 실측 — 환각의 구성

### 2-0. ★ 퍼센트를 읽는 법 — 분모와 분자

이 문서의 비율은 **네 가지 서로 다른 분모**를 쓴다. 헷갈리면 결론이 뒤집히므로 먼저 정의한다.

측정 절차는 이렇다.

    1. TRAIN 에서 스텝을 무작위로 N개 뽑는다              → **표본 예제**
    2. 각 예제 = (프롬프트, gold tactic)
    3. gold tactic 의 식별자에서 다음을 **뺀다**
         · Coq 핵심 어휘 (`forall`·`nat`·`True`·`Qed` …)
         · `[STATE]` 의 가설·바인더 이름
         · 이 tactic 이 **도입하는** 이름 (`as H` · `intros x` · `have h :` ·
           `assert (H : T)` · `forall` 바인더 · `eqn:E` · 중첩 `[a [b _] c]`)
         · tactic 이름 (첫 토큰 및 `;`·`by` 뒤의 첫 토큰) — 이름이 아니라 문법
         · 힌트 DB 이름 (`auto with arith` 의 `arith`)
         · 문자열 리터럴 안 (`Search "foo"`)
         · 3글자 미만
    4. 남은 것 = **외부 참조 이름**
    5. 그중 **절단 후 보이는 프롬프트**에 없는 것 = **결손 이름**
         └ 결손 중 stdlib 이름은 "모델이 안다고 가정" 하여 **따로 센다**
    6. 결손 이름이 하나라도 있는 예제 = **환각 예제**

| 지표 | 분자 | 분모 | H1 실측 |
|---|---|---|---|
| **환각률** (이 문서의 기본 지표) | 환각 예제 | **외부 참조를 쓰는 예제** | 42 / 262 = **16.0%** |
| 전체 예제 대비 | 환각 예제 | 표본 예제 | 42 / 2,000 = **2.1%** |
| 종류별 비중 | 그 종류의 **결손 이름** | 전체 **결손 이름** | 예: Definition 24 / 48 = 50.0% |
| 종류별 "안 보임" 비율 | 그 종류의 결손 이름 | 그 종류의 **외부 참조 이름** | 예: Definition 24 / 131 = 18.3% |

**왜 분모가 "전체 예제" 가 아닌가**: 표본 2,000건 중 **1,738건(86.9%)은 외부 이름을
아예 안 쓴다**(`reflexivity` · `intros x` · `lia` 등). 그런 예제는 환각할 기회 자체가
없으므로 분모에 넣으면 비율이 기회 없는 예제로 희석된다. 그래서 **"외부 이름을 쓰는
예제 중 몇 %가 환각인가"** 를 기본 지표로 쓴다.

> ⚠ **서로 다른 실행의 절대값을 비교하지 말 것.** 검사기를 고치면 분모(외부 참조 예제)와
> 분자가 **함께** 바뀐다. 실제로 오탐을 고치자 분모가 274 → 262 로 줄어 비율이
> 15.3% → 16.0% 로 **올라갔다** — 환각이 늘어난 게 아니라 오탐이던 이름이 *외부 참조*
> 집계에서 빠졌기 때문이다. 비교는 **같은 실행 안의 H1↔H2↔H3** 로만 한다.

### 2-1. H1 · H2 · H3 가 각각 무엇인가

세 실행은 **같은 스크립트에서 순차로, 같은 seed(4)·같은 표본 2,000건·같은 캐시**로
돌렸다. 바뀌는 것은 환경변수뿐이다.

| | `INJECT_NOTATION` | `NOTATION_PROJ` | `UNFOLD_SEEDS` | `PREMISE_ADMIT_USED` |
|---|---|---|---|---|
| **H1** 기준 | 0 | 0 | 0 | 0 |
| **H2** + 주입 | 1 | 1 | 1 | 0 |
| **H3** + 풀 확대 | 1 | 1 | 1 | 1 (`ADMIT_MIN_FILES=2`) |

각 스위치가 하는 일:

- **`INJECT_NOTATION`** — 그 **파일 안에** 정의된 `Notation` 을 `[NOTATION]` 섹션으로 넣는다.
  비용 실측: 파일 내 중앙 0개 · p90 552토큰. (파일 밖은 중앙 194개라 통째로는 못 넣는다.)
- **`NOTATION_PROJ`** — 파일 밖 notation 을 **프로젝트로 좁히고 goal 의 기호로 앵커링**해
  넣는다. `Notation "A ⊢I phi" := (@prv _ _ _ intu A phi)` 의 `⊢I` 가 goal 에 있으면
  그 줄을 넣는다. 실측: 프로젝트 419개 중 **1개만 발화, 그게 정답**. 비용 p90 39토큰.
- **`UNFOLD_SEEDS`** — goal 에 정의의 **본문**이 보일 때 이름을 되찾는 역인덱스.
  goal `Tr (-1) (hfiber ...)` → 조각 `Tr(-1)` → `merely`. 비용 p90 1개.
- **`PREMISE_ADMIT_USED`** — rango 가 풀에서 빼는 종류라도 그 프로젝트에서 **실제로
  tactic 인자로 쓰인** 이름이면 되살린다. 누출을 막으려 **서로 다른 파일 2개 이상**을
  요구한다(평가 대상 파일 자신만으로는 승격 불가). 풀 증가 +15.9%.

**결과**

| 실행 | 환각 예제 / 외부참조 예제 | 환각률 | 결손 이름 수 |
|---|---|---|---|
| **H1** 기준 | 42 / 262 | **16.0%** | 48 |
| **H2** + 주입 3종 | 40 / 264 | **15.2%** | 46 |
| **H3** + 풀 확대 | 39 / 261 | **14.9%** | 42 |

세 개입을 다 합쳐 **−1.1pp**, 결손 이름은 48 → 42 (−12.5%).
전체 예제 대비로는 2.1% → **2.0%** 다.

### 2-2. 환각 이름의 종류별 비중 — 그리고 "풀에서 제외" 가 무슨 말인가

**분모 = H3 의 결손 이름 42개, 분자 = 그 종류의 결손 이름 수.**

| 종류 | 결손 / 그 종류 외부참조 | 종류별 "안 보임" | **결손 중 비중** | 풀에서 제외되나 |
|---|---|---|---|---|
| **Definition** | 21 / 129 | 16.3% | **50.0%** | ★ 제외 |
| Lemma | 9 / 51 | 17.6% | 21.4% | 아니오 |
| 미상 | 5 / 45 | 11.1% | 11.9% | — |
| **Constructor** | 4 / 21 | 19.0% | 9.5% | ★ 제외 (`Inductive` 의 일부) |
| Fact | 2 / 5 | 40.0% | 4.8% | 아니오 |
| **Field** | 1 / 50 | 2.0% | 2.4% | ★ 제외 (`Record` 의 일부) |

**"풀에서 제외" 란**

rango 는 검색을 돌리기 전에 `PremiseFilter` 로 **후보 목록(pool)** 을 만든다.
그때 문장 종류로 거른다.

```python
PROJ_THM_FILTER_CONF = PremiseFilterConf(
    coq_excludes=[      # lib/coq/theories (= stdlib) 에서 뺄 것
        "THEOREM", "LEMMA", "DEFINITION", "NOTATION", "INDUCTIVE", ... ],   # 사실상 전부
    non_coq_excludes=[  # 프로젝트 자기 파일에서 뺄 것
        "DEFINITION", "NOTATION", "INDUCTIVE", "COINDUCTIVE", "RECORD",
        "CLASS", "INSTANCE", "FIXPOINT", "COFIXPOINT", "SCHEME", "VARIANT",
        "OBLIGATION", "TACTIC", "RELATION", "SETOID", "FUNCTION", "DERIVE", "OTHER" ])
```

풀에 남는 것은 `LEMMA`·`THEOREM`·`FACT`·`REMARK`·`COROLLARY`·`PROPOSITION`·
`PROPERTY`·`AXIOM` 정도다.

> **"제외" = 랭커가 점수를 매기는 후보 목록에 애초에 안 들어간다.**
> 순위가 1위인지 100위인지가 아니라 **존재하지 않는다.** 검색으로는 절대 도달 불가다.
> `Constructor` 는 `Inductive` 선언의 일부라 `Inductive` 가 빠지면 같이 빠지고,
> `Field` 는 `Record` 의 일부라 마찬가지다.

이 넷을 합치면 **26 / 42 = 61.9%** 다. 다만 §1-1 의 순위 측정이 보여 주듯
**되살려도 검색이 못 찾는다** — 병목은 풀이 아니라 검색 가능성이다.

### 2-3. stdlib 은 이미 걷어냈다 — 그런데도 남는다

`PremiseFilter` 는 두 목록을 따로 쓴다(위 코드). stdlib 은 `THEOREM`·`LEMMA` 까지
전부 빠지므로 **검색으로 도달 불가**이고, 그래서 "모델이 안다고 가정" 하여 환각 집계에서
분리한다. 그 효과 (**분모 = 표본 2,000**):

| | 건수 |
|---|---|
| stdlib 포함하면 결손 있는 예제 | **70** |
| ─ stdlib 이라 뺀 것 | **28 (40.0%)** |
| 남은 환각 예제 | **42** |

즉 stdlib 가정이 결손의 40% 를 이미 지웠고, **남은 42건은 전부 프로젝트 자기 파일의
이름**이다. `isequiv_adjointify` 는 HoTT 자기 정리, `cs_bin_op_strext` 는 CoRN 자기
정의다 — stdlib 가정이 닿지 않는다.

### 2-4. 프로젝트별 풀 비율 — 왜 HoTT 가 특히 심한가

문장 DB 전수 (**분모 = 그 프로젝트의 전체 선언 문장**):

| 프로젝트 | 풀에 드는 것 | 제외 | 제외율 |
|---|---|---|---|
| HoTT-Coq-HoTT | 3,157 | 15,400 | **83.0%** |
| snu-sf-class | 191 | 587 | 75.4% |
| AbsInt-CompCert | 6,314 | 6,326 | 50.0% |
| coq-community-corn | 6,575 | 3,561 | 35.1% |
| coq-community-gaia | 9,648 | 2,451 | 20.3% |

HoTT 는 **정리를 `Definition` 으로 선언**한다 → 검색기가 라이브러리의 17%만 본다.

### 2-5. ★ 환각이 **gold 원본**에서 나왔나, **우리가 만든 cut** 에서 나왔나

둘은 처방이 정반대라 반드시 갈라야 한다.

    gold 원본  사람이 쓴 tactic 이 프롬프트에 없는 이름을 부른다.
               **데이터의 성질**이므로 주입·풀·학습으로만 건드릴 수 있다.
    cut 생성   우리 `assert_split` 이 만든 하위스텝이 이름을 부른다.
               **우리가 만든 문제**이므로 생성 규칙을 바꿔 없앨 수 있다.

분류 표지 — `H_asrt` 가 우리 생성물의 고유 표지다.

    target 에 `H_asrt` 가 있다               → cut 생성 (assert 또는 final)
    cut 계획이 있고 target 이 `exact L.` 뿐   → cut 생성 (close)
    그 외                                    → gold 원본

**표본 2,500 (분모 = 표본 예제 2,500)**

| 출처 | 예제 | 비중 |
|---|---|---|
| gold 원본 | 2,334 | 93.4% |
| **cut 생성** | **166** | **6.6%** |
| ├ assert / final | 114 | 4.6% |
| └ close (`exact L`) | 52 | 2.1% |

**출처별 환각률** (분모 = 그 출처에서 **외부 참조를 쓰는** 예제)

| 출처 | 외부참조 예제 | 환각 | **환각률** |
|---|---|---|---|
| gold 원본 | 235 | 38 | **16.2%** |
| **cut 생성** | 74 | 5 | **6.8%** |
| 합계 | 309 | 43 | 13.9% |

> **환각 예제 중 gold 원본이 88.4%(38/43), cut 생성이 11.6%(5/43).**
> 그리고 **cut 스텝의 환각률(6.8%)은 gold 스텝(16.2%)의 절반 이하다.**

주의할 점 — cut 예제는 외부 참조를 훨씬 자주 쓴다(74/166 = **44.6%** vs
gold 235/2,334 = **10.1%**). 당연하다. cut 이 걸리는 스텝이 **원래 lemma 를 필요로 하던
스텝**이기 때문이다. 그런 어려운 스텝만 모아 놓고도 환각률이 절반이라는 뜻이다.

**cut 생성 환각 5건은 두 부류다**

    ① assert 명제가 goal 에 없는 기호를 담는다 — **우리 책임** (3건)
       assert (forall n, ZeroR [<] f0 (S n)) as H_asrt0.       ← ZeroR 이 프롬프트에 없다
       assert (forall (op : CSetoid_bin_op) (x1 x2 y1 y2 : S), x1 [=] x2 ...) as H_asrt0.
       assert (forall a b, ~ inc b a -> cardinal (a +s1 b) = csucc ...) as H_asrt0.

    ② final 스텝이 원래 tactic 을 그대로 물려받았다 — **gold 에서 온 것** (2건)
       rewrite /f1/f2/CNFbvo/CNFbv H_asrt0.
       elim H_asrt0 with (r1 := k) (r2 := 0); ...

①만 우리 책임이고 규모는 **3건 = 표본 2,500 의 0.12%** 다. 기존 잔여
(hopeless 제외 6.60% · 2048 초과 8.50% · P4 0.67%)보다 한두 자릿수 작아 우선순위는
낮지만, **논문에서는 분리해 보고해야 한다.**
고칠 길: (a) 명제 안 이름이 다 보이는 cut 만 세운다 (b) 결손 이름을 씨앗으로 강제 주입.

### 2-6. ★ 익명화 때문에 "못 찾았다" 고 잘못 신고한 것은 없나 — **0건**

자연스러운 의심이다. `[DEFINITIONS]`·`[TYPES]`·`[PREMISES]` 의 이름은 v8 정규화로
`T0`·`f5`·`L9` 가 된다. **프롬프트는 `f5` 인데 정답은 `foo` 로 남았다면** 검사기는 `foo` 를
찾다 못 찾고 환각으로 오신고한다. 그건 환각이 아니라 측정 버그다.

`collate` 가 프롬프트와 정답에 **같은 매핑**을 적용하므로 이론상 생길 수 없지만,
매핑을 밖으로 꺼내(`last_train_mapping()`) 실측했다. **분모 = 결손 이름 42개.**

| 점검 | 건수 |
|---|---|
| 정규화가 적용된 예제 | 1,964 / 2,000 (98.2%) · 매핑 항목 43,373개 |
| ① 결손 이름이 익명 토큰(`T0`/`f5`/`L9`/`C2`/`K1`/`G0`)인가 | 0 |
| ② 결손 이름이 **매핑의 키**인가 (= 정답에 실명이 남음) | 0 |
| ③ 그 이름의 **익명형**이 프롬프트에 있나 | 0 |
| ④ 정답은 익명인데 프롬프트엔 **실명**이 있나 | 0 |
| **★★ 익명화 탓 오신고** | **0 / 42 = 0.00%** |

가설은 기각됐다. 절단 후 안 보이는 premise 를 매핑에서 빼는 가드(L3)도 함께 검증된 셈이다.

---
## 3. ★ gold 원본 환각만 따로 — 원인과 실제 사례

§2-5 에서 환각의 **88.4%가 gold 원본**임을 봤다. 우리가 만든 게 아니라 사람이 쓴 증명이
프롬프트에 없는 이름을 부르는 것이다. 여기서는 그것만 떼어 원인별로 본다.

TRAIN 3,000건에서 **gold 원본 환각 25건**을 프롬프트 전문과 함께 덤프해 분류했다
(**분모 = 25건**).

| 원인 | 건수 | 비율 | 무슨 뜻인가 | 고칠 수 있나 |
|---|---|---|---|---|
| **A** | 12 | **48.0%** | `func_defs` 인덱스에도 검색 결과 100개에도 없다 — **넣을 재료 자체가 없다** | ✗ 인덱스를 넓히는 것 외엔 길이 없다 |
| **B** | 8 | 32.0% | 검색 결과에는 있는데 재랭킹·896토큰 예산에 밀려 프롬프트에 안 실렸다 | △ 예산/재랭킹 문제 |
| **C** | 3 | 12.0% | 재료는 인덱스에 있는데 **씨앗이 닿지 않는다** (이름이 goal·SCRIPT·PROOFS 어디에도 없다) | ✗ §4 의 방향 문제 |
| **D** | 2 | 8.0% | 씨앗은 닿는데 300토큰 예산·개수 캡에 밀렸다 | ○ 예산을 늘리면 된다 |

### 3-1. B 부류를 더 쪼개면 — "패킹이 버린" 것은 2.9%뿐이다

원인 B("검색 결과에는 있는데 프롬프트에 없다")는 두 가지가 섞여 있다. 하나는
**순위가 낮아서**이고, 하나는 **순위는 높은데 패킹이 버려서**다. 뒤엣것은 §1 의 원리적
한계가 아니라 **엔지니어링 문제**라 고칠 수 있으므로 갈라서 쟀다.

표본 1,500 · **분모 = 결손 이름 35개** (`scripts/probe_pack_loss.py`):

| 갈래 | 건수 | 비율 |
|---|---|---|
| ① 검색 결과 100개 **어디에도 없다** | 27 | **77.1%** |
| ② ★ **패킹 손실** — 검색 상위 22위 안인데 프롬프트에 없다 | 1 | **2.9%** |
| ③ 23위 밖 — 순위 문제 | 7 | 20.0% |
| (참고) 그 이름의 **선언 자체**가 검색 결과에 있음 | 6 | 17.1% |

**패킹 손실은 2.9% 로 미미하다.** 유일한 표본은 이랬다:

    equiv_iff_hprop   검색 순위 21(선언도 21위)   ← apply equiv_iff_hprop.
      premise: Definition equiv_iff_hprop `{IsHProp A} `{IsHProp B} :
               (A -> B) -> (B -> A) -> (A <~> B) : ...

순위 21은 경계선(예산 ≈22개)이라 `rerank_premises` 이후 밀려났다. 예산을 조금 늘리면
이런 것은 살릴 수 있지만, **전체의 2.9%** 다.

> ⚠ 사례 2(`whiskerL_pp`, 순위 4)는 이 부류의 극단값이다. 다른 표본(seed 11)에서 나왔고,
> seed 4 기준 1,500건에서는 그런 사례가 1건뿐이었다. **일반적인 현상이 아니다.**

**결론: 결손의 77.1% 는 검색이 아예 못 찾은 것**이고, 이것이 §1-1·§4 가 말하는 구조적
한계다. 패킹·예산은 나머지의 일부일 뿐이다.

> **진단표의 "검색 100개 중 순위" 를 읽을 때 주의** — 이건 검색기가 매긴 **원본 순서**다.
> 프롬프트는 그 100개를 `rerank_premises` 로 다시 정렬한 뒤 **896토큰에 맞게 하이브리드
> 패킹**해 ~22개만 싣는다. 그래서 **순위 4 = 프롬프트 4번째가 아니다.**
> 실제로 사례 2(`whiskerL_pp`)는 순위 4인데도 프롬프트에 없다 — §3-1 참고.

아래는 각 원인의 실제 사례다. **모델이 보는 프롬프트 전문**(절단 후)과 **gold tactic** 을
그대로 싣는다. premise 이름이 `L9`·`T0`·`f5` 로 보이는 것은 v8 익명화 때문이다(§2-6).

<details>
<summary><b>사례 1 — <code>cf_rcpcl</code> (Field) · 원인 A</b></summary>

<blockquote style="border-left:4px solid #4a9eff; padding-left:1em; margin-left:0">

**파일** `repos/coq-community-corn/algebra/CFields.v`  ·  **idx** `829479`

**① 모델이 보는 프롬프트 — 전문** (2048토큰 절단 **후** = 실제 입력)

```

[PREMISES]
Lemma L9 : forall p : positive, nat_of_P p = Zpos p :>Z.
Lemma L8:forall (a b c:nat),(c<=b<=a)-> a+(b-c)=b+(a-c).
Lemma L7 : forall n m (H1 H2:le n m), H1=H2.
Lemma L6 : forall x y z : nat, x <= y -> x * z <= y * z.
Lemma L5 : forall x y z : nat, x < y -> 0 < z -> x * z < y * z.
Lemma L3 : forall n m : nat, {n < m} + {m <= n}.
Lemma L4 : 0 < 2.
Lemma L2 {A} (x y: list A): list_eq eq x y <-> x = y.
Lemma L1 {A} (x: A) (l: list A): In x l → exists l', Permutation (x :: l') l.
Lemma Zis_gcd_unique : forall a b d e : Z, Zis_gcd a b d -> Zis_gcd a b e -> d = e.
Lemma prime_rel_prime : Prime -> forall x : positive, (Zpos x < Zpos p)%Z -> Zrelprime (Zpos p) (Zpos x).
Lemma Zmod_small : forall m a : Z, (m > 0)%Z -> (0 <= a < m)%Z -> (a mod m)%Z = a.
Lemma Zgcd_is_gcd : forall a b : Z, Zis_gcd a b (Zgcd a b).
Lemma inv : forall A B (f:CSetoid_fun A B), bijective f -> forall b : B, {a : A | f a [=] b}.
Lemma Exists_map : forall (P:Stream B -> Prop) (S:Stream A), Exists (fun s => P (map s)) S -> Exists P (map S).
Lemma Zsgn_neg : forall z : Z, Z.sgn z = (-1)%Z -> (z < 0)%Z.
Lemma Zabs_Zopp : forall a : Z, Z.abs (- a) = Z.abs a.
Lemma Zsgn_pos : forall z : Z, Z.sgn z = 1%Z -> (z > 0)%Z.
Lemma Zle_neg_pos : forall p q : positive, (Zneg p <= Zpos q)%Z.
Lemma Zmult_minus_distr_r : forall n m p : Z, (p * (n - m))%Z = (p * n - p * m)%Z.
Lemma mult_assoc : associative (cr_mult (c:=R)).
Lemma le_minus : forall n k : nat, n - k <= n.
Lemma minus_plus : forall x y z : G, x[-] (y[+]z) [=] x[-]y[-]z.
Lemma plus_assoc : associative (csg_op (c:=G)).
Theorem well_founded_ltof : well_founded A ltof.
Lemma le_trans : forall l k n : nat, k <= l -> l <= n -> k <= n.
Lemma not_or:(forall (p q:nat), (p<>q)-> p<q or q<p):CProp.
Definition flip (X Y Z : T0) : (X-->Y-->Z)-->Y-->X-->Z.
Definition compose (X Y Z : T0) : (Y-->Z) --> (X --> Y) --> X --> Z.
Theorem well_founded_induction_type : forall P : A -> Type, (forall x : A, (forall y : A, R y x -> P y) -> P x) -> forall a : A, P a.
Lemma le_pred : forall n m : nat, n <= m -> pred n <= pred m.
Lemma Acc_inv : forall x : A, Acc R x -> forall y : A, R y x -> Acc R y.
Lemma L0 : forall S (F : PartFunct S) x y Hx Hy, x [=] y -> F x Hx [=] F y Hy.
[PROOFS]
Lemma included_FInv : included R P -> included R (Dom T5).
Proof.
 intro; simpl in |- *; assumption.
Qed.
Definition f1 : T2 S -> PartFunct S.
Proof.
 intros f.
 apply Build_PartFunct with (fun x : S => True) (fun (x : S) (H : True) => f x).
  red in |- *; intros; auto.
 intros x y Hx Hy H.
 exact (csf_strext _ _ f _ _ H).
Defined.
Lemma L10 : included R' P -> forall c, included R' (Dom (c{**}F)).
Proof.
 intros; simpl in |- *; apply included_conj.
  red in |- *; intros; auto.
 assumption.
Qed.
Lemma part_function_comp_dom_wd : pred_wd S R.
Proof.
 red in |- *; intros x y H H0.
 unfold R in |- *; inversion_clear H.
 exists (dom_wd _ F x y x0 H0).
 apply (dom_wd _ G) with (F x x0).
  assumption.
 apply L0; assumption.
Qed.
[STATE]
F: CField

PartFunct F
[SCRIPT]
Definition f0 (F : CField) : PartFunct F.
Proof.
[TYPES]
Structure T0: Type := { st_car :> Type; st_eq : Equiv st_car ; st_isSetoid : Setoid st_car }.
Inductive assumption : Type := | assume : nat -> type -> assumption .
Record T1 : Type := {cr_crr : CAbGroup; cr_one : cr_crr; cr_mult : CSetoid_bin_op cr_crr; cr_proof : is_CRing cr_crr cr_one cr_mult}.
[DEFINITIONS]
Definition f0 (F : CField) : PartFunct F.
Definition red (x : t) : t := match x with | Qz z => x | Qq n d => norm n d end.
Definition unfold (t : F(later (mu F))) : mu F := eq_rect _ (id(A:=Type)) t _ (eq_sym eqmu).
Definition f1 : T2 S -> PartFunct S.
Definition T2 := CSetoid_fun S S.
Definition generalize(T:Type)(t:T)(r:string)(ts:string)(s':string)(e0: tag t r ts s'): { s:string & T }.
Definition T3 := Build_PartFunct R _ (conj_wd (dom_wd _ F) (dom_wd _ G)) (fun x Hx => F x (Prj1 Hx) [*]G x (Prj2 Hx)) ...
Definition T4 := Build_PartFunct G _ (conj_wd (dom_wd _ F) (dom_wd _ F')) (fun x Hx => F x (Prj1 Hx) [+]F' x (Prj2 Hx)) ...
Definition T5 := Build_PartFunct _ _ (dom_wd _ F) (fun x Hx => [--] (F x Hx)) part_function_inv_strext.
```

**② gold tactic** (모델이 맞혀야 하는 것)

```coq
apply Build_PartFunct with (fun x : F => x [#] [0]) (cf_rcpcl F).
```

**③ 진단** — 위 프롬프트 어디에도 `cf_rcpcl` 이 없다.

| 항목 | 값 |
|---|---|
| 선언 종류 | `Field` |
| rango 풀에서 빠지는 종류인가 | **예** — 검색 후보에 애초에 안 들어간다 |
| 검색 100개 중 순위 | 검색 100개 안에 없음 |
| `func_defs` 에 정의 재료가 있나 | 없다 |
| 주입 가능한 형태인가(`pick_def`) | 아니오 |
| 씨앗이 닿는 출처 | **어디에도 없음** |
| 프로젝트 내 tactic 사용 | 2회 · 1개 파일 |

</blockquote>
</details>

<details>
<summary><b>사례 2 — <code>whiskerL_pp</code> (Definition) · 원인 B</b></summary>

<blockquote style="border-left:4px solid #4a9eff; padding-left:1em; margin-left:0">

**파일** `repos/HoTT-Coq-HoTT/theories/Spaces/BAut.v`  ·  **idx** `574649`

**① 모델이 보는 프롬프트 — 전문** (2048토큰 절단 **후** = 실제 입력)

```

[PREMISES]
Proposition predeqminus1 { n : nat } : n - 1 = pred n.
Notation IsHProp := (T0 minus_two.+1).
Lemma L19 p : 1 + p = pos_succ p.
Notation Contr := (T0 minus_two).
Lemma L18 p : p + 1 = pos_succ p.
Lemma L17 n : n * 1 = n.
Lemma L16 n : 1 * n = n.
Lemma L15 p : p * 1 = p.
Lemma L14 p : 1 * p = p.
Corollary L13 : IsHSet Bool.
Definition L12 (X : Type@{u}) := { Z : Type@{u} & merely (Z = X) }.
Notation IsHSet := (T0 minus_two.+2).
Definition L11 {A : Type} {x y : A} (p : x = y) : 1 @ p = p := match p with idpath => 1 end.
Definition f3 {A : Type} {x y : A} (p : x = y) : p @ 1 = p := match p with idpath => 1 end.
Definition L8 {A B : Type} (p : A = B) : path_universe (equiv_path A B p) = p := eissect (equiv_path A B) p.
Definition L10 {A : Type} {x y z : A} (p : x = z) (q : y = z) (r : x = y) : p = r @ q -> r^ @ p = q.
Lemma L4 {A} {x : A} (p : x = x) (q : p = 1) : f3 p @ q = ap (fun p' => p' @ 1) q.
Definition L1 {A} {x : A} (h : idpath x = idpath x) : whiskerL 1 h = h.
Definition L9 {A : Type} {x y : A} (p : x = y) : p^ @ p = 1 := match p with idpath => 1 end.
Definition f4 {A : Type} : path_universe (equiv_idmap A) = 1 := L8 1.
Definition L0 {A B : Type} (f g : A <~> B) : (f == g) <~> (path_universe f = path_universe g).
Definition L7 {A : Type} {x y : A} (p : x = y) : 1 @ p = p @ 1 := L11 p @ (f3 p)^.
Definition L6 {A : Type} {x y : A} (p : x = y) : p @ 1 = 1 @ p := f3 p @ (L11 p)^.
Theorem L5 {A U V : Type} (w : U <~> V) : forall f : U -> A, transport (fun E : Type => E -> A) (path_universe w) f = (f o w^-1).
Definition L3 {A : Type} {x y : A} {p q : x = y} (h : p = q) : (f3 p)^ @ whiskerR h 1 @ f3 q = h := match h with idpath => match p with idpath => 1 end end.
Definition L2 {A B : Type} (f : A -> B) {feq : IsEquiv f} (z : B) : transport (fun X:Type => X) (path_universe f)^ z = f^-1 z := transport_path_universe_V_uncurried (Build_Equiv _ _ f feq) z.
[PROOFS]
Definition dpath_paths2 {A : Type} {x y : A} (p : x = y) (q : idpath x = idpath x) (r : idpath y = idpath y) : (L11 p)^ @ whiskerR q p @ L11 p = (f3 p)^ @ whiskerL p r @ f3 p <~> transport (fun a => idpath a = idpath a) p q = r.
Proof.
  destruct p. simpl.
  refine (_ oE (equiv_whiskerR _ _ 1)^-1).
  refine (_ oE (equiv_whiskerL 1 _ _)^-1).
  refine (equiv_concat_lr _ _).
  - symmetry; apply whiskerR_p1_1.
  - apply L1.
Defined.
[STATE]
H: Univalence
X: Type
H0: T0 1 X
X0: forall Z : L12 X, IsHSet (1 = 1)
f: 1%equiv == 1%equiv
g: X <~> X

((((f3 (path_universe g))^ @
   whiskerL (path_universe g) f4^) @
  whiskerL (path_universe g) (L0 1 1 f)) @
 whiskerL (path_universe g) f4) @ f3 (path_universe g) =
((f3 (path_universe g))^ @
 whiskerL (path_universe g)
   ((f4^ @ L0 1 1 f) @ f4)) @
f3 (path_universe g)
[SCRIPT]
Definition G0 `{Univalence} X `{T0 1 X} : { f : forall x:X, x=x & forall (g:X<~>X) (x:X), ap g (f x) = f (g x) } <~> (forall Z:L12 X, (idpath Z) = (idpath Z)).
  Proof.
    refine ((equiv_functor_forall_id
               (fun Z => (equiv_concat_lr _ _)
                           oE (equiv_ap (equiv_path_sigma_hprop Z Z) 1%path 1%path))) oE _).
    { symmetry; apply path_sigma_hprop_1. }
    { apply path_sigma_hprop_1. }
    assert (forall Z:L12 X, IsHSet (idpath Z.1 = idpath Z.1)) by exact _.
    refine (baut_ind_hset X (fun Z => idpath Z = idpath Z) oE _).
    simple refine (equiv_functor_sigma' _ _).
    { refine (_ oE L0 1 1).
      apply equiv_concat_lr.
      - symmetry; apply f4.
      - apply f4. }
    intros f.
    apply equiv_functor_forall_id; intros g.
    refine (_ oE equiv_path3_universe _ _).
    refine (dpath_paths2 (path_universe g) _ _ oE _).
    cbn.
    change (equiv_idmap X == equiv_idmap X) in f.
    refine (equiv_concat_lr _ _).
    - refine (_ @ (path2_universe_postcompose_idmap f g)^).
      abstract (rewrite !whiskerR_pp, !concat_pp_p; reflexivity).
    - refine (path2_universe_precompose_idmap f g @ _).
[TYPES]
Class T0 (n : trunc_index) (A : Type) : Type := Trunc_is_trunc : IsTrunc_internal n A.
Record f0 := { pointed_type : Type ; ispointed_type : T1 pointed_type }.
Record f1 (A : f0) := { pfam_pr1 :> A -> Type; dpoint : pfam_pr1 (point A)}.
Record f2 (A : f0) (P : f1 A) := { pointed_fun : forall x, P x ; dpoint_eq : pointed_fun (point A) = dpoint P ; }.
Class T1 (A : Type) := point : A.
[DEFINITIONS]
Definition f3 {A : Type} {x y : A} (p : x = y) : p @ 1 = p := match p with idpath => 1 end.
Definition f4 {A : Type} : path_universe (equiv_idmap A) = 1 := L8 1.
[NOTATION]
Notation "'forall' x .. y , P" := (forall x , .. (forall y, P) ..).
Notation "'forall' x .. y , P" := (forall x, .. (forall y, P) ..)%type : type_scope.
Notation "A <~> B" := (Equiv A B) : type_scope.
```

**② gold tactic** (모델이 맞혀야 하는 것)

```coq
abstract (rewrite !whiskerL_pp, !concat_pp_p; reflexivity).
```

**③ 진단** — 위 프롬프트 어디에도 `whiskerL_pp` 이 없다.

| 항목 | 값 |
|---|---|
| 선언 종류 | `Definition` |
| rango 풀에서 빠지는 종류인가 | **예** — 검색 후보에 애초에 안 들어간다 |
| 검색 100개 중 순위 | 4 |
| `func_defs` 에 정의 재료가 있나 | **있다** |
| 주입 가능한 형태인가(`pick_def`) | 예 |
| 씨앗이 닿는 출처 | PROOFS·PREMISES(상위12) |
| 프로젝트 내 tactic 사용 | 4회 · 3개 파일 |

**④ 참고 — 인덱스에 있는 정의문** (넣을 재료는 있었다)

```coq
Definition whiskerL_pp {A} {x y z : A} (p : x = y) {q q' q'' : y = z} (r : q = q') (s : q' = q'') : whiskerL p (r @ s) = whiskerL p r @ whiskerL p s.
```

</blockquote>
</details>

<details>
<summary><b>사례 3 — <code>finite_c</code> (Definition) · 원인 C</b></summary>

<blockquote style="border-left:4px solid #4a9eff; padding-left:1em; margin-left:0">

**파일** `repos/coq-community-gaia/theories/ordinals/ssete5.v`  ·  **idx** `1140843`

**① 모델이 보는 프롬프트 — 전문** (2048토큰 절단 **후** = 실제 입력)

```
_2omega: \2o <=o omega0.
Lemma opow1x x: \1o ^o x = \1o.
Lemma L13: osucc \1o = \2o.
Lemma L11: \1o <o omega0.
Lemma L12 n: n <o omega0 -> n +o omega0 = omega0.
Lemma L5 a: \2o <=o a <-> \1o <o a.
Lemma L6 a: ordinalp a -> a *o \2o = a +o a.
Lemma L10 a: ordinalp a -> (\1o +o a = a <-> omega0 <=o a).
Lemma L4: \1o <o \2o.
Lemma L3 a: omega0 <=o a -> (a +o \1o) -o \1o <> a.
Lemma L9 n: \0o <o n -> n <o omega0 -> (osucc n -o \1o) = osucc (n -o \1o).
Lemma L7 (a := \1o) (b := omega0): a +o b <> b +o a.
Lemma L1 a: omega0 <=o a -> \1o +o a = a.
Lemma L0: \1o +o \1o = \2o.
Lemma L2 a: ordinalp a -> a +o \1o = osucc a.
Lemma L8: \0o ^o \0o = \1o.
[PROOFS]
Lemma omega_log_p1 x: \0o <o x -> exists y, [/\ ordinalp y, oopow y <=o x & x <o oopow (osucc y)]. 
Proof.
move => ox.
have x1: \1o <=o x by apply/oge1P.
have o2:= ole_2omega.
move: ord_pow_axioms => [[ax1 _ _ _ ] _ _ _].
move: (ord_induction_p12 (erefl opow') ax1 o2 x1) => [y []].
rewrite - (opow2x _ o2) -(opow2x _ o2) => sa sb sc.
by have oy:=(proj31 sa); exists y. 
Qed.
[STATE]
 ->
 z0 <=o y ->
 exists t0 : Set, [/\ ordinalp t0, indecomposable t0 & y = z0 ^o t0])
Hb: critical_ordinal \1o oprod2 y <->
(exists2 n : Set, ordinalp n & y = oopow (oopow n))
ify: infinite_o y
oy: ordinalp y
hy: forall z0 : Set,
\1o <o z0 -> z0 <=o y -> exists2 t0 : Set, ordinalp t0 & y = z0 ^o t0
loy: omega0 <=o y
lt1y: \1o <o y
x: Set
le1x: \1o <=o x
ltxy: x <o y
lexy: x <=o y
nexy: x <> y
ox: ordinalp x
xp: \0o <o x
xl1: \1o <o x
t: Set
ot: ordinalp t
yn1: y <> \1o
xl2: \2o <=o x
tf: t <o omega0
tnz: \0o <o t
yt: y = x ^o t
os0: ordinalp \0o
os1: ordinalp \1o
os2: ordinalp \2o
l02: \0o <o \2o
tnt: t <> \2o
tb: natp t
tnz': t <> \0o
u: Set
uB: natp u
tsu: t = csucc u
uo: u <o omega0
ou: ordinalp u
us: t = osucc u
z: Set
unz: u <> \0o
z1: \1o <o z
oz: ordinalp z
z2: z <=o y
v: Set
ov: ordinalp v
v2: \2o <=o v
le1: u +o u <=o u *o v
oB: natp \1c
tB: natp \2c
su: natp (osucc u)

\1o +o osucc u = u +o \2o
[GOAL]
CP: Set -> Prop
p1: Set -> Prop
y: Set
Hc: infinite_o y /\ ordinalp y <-> omega0 <=o y
Ha: (exists2 n : Set, ordinalp n & y = oopow (oopow n)) <->
omega0 <=o y /\
(forall z0 : Set,
 \1o <o z0 ->
 z0 <=o y ->
 exists t0 : Set, [/\ ordinalp t0, indecomposable t0 & y = z0 ^o t0])
Hb: critical_ordinal \1o oprod2 y <->
(exists2 n : Set, ordinalp n & y = oopow (oopow n))
ify: infinite_o y
oy: ordinalp y
hy: forall z0 : Set,
\1o <o z0 -> z0 <=o y -> exists2 t0 : Set, ordinalp t0 & y = z0 ^o t0
loy: omega0 <=o y
lt1y: \1o <o y
x: Set
le1x: \1o <=o x
ltxy: x <o y
lexy: x <=o y
nexy: x <> y
ox: ordinalp x
xp: \0o <o x
xl1: \1o <o x
t: Set
ot: ordinalp t
yn1: y <> \1o
xl2: \2o <=o x
tf: t <o omega0
tnz: \0o <o t
yt: y = x ^o t
os0: ordinalp \0o
os1: ordinalp \1o
os2: ordinalp \2o
l02: \0o <o \2o
tnt: t <> \2o
tb: natp t
tnz': t <> \0o
u: Set
uB: natp u
tsu: t = csucc u
uo: u <o omega0
ou: ordinalp u
us: t = osucc u
z: Set
unz: u <> \0o
z1: \1o <o z
oz: ordinalp z
z2: z <=o y
v: Set
ov: ordinalp v
v2: \2o <=o v
le1: u +o u <=o u *o v

u +o \2o <=o u +o u
[SCRIPT]
 (opowx1 ox)  - opow_sum //.
have tb: natp t by  apply /olt_omegaP.
have tnz':= nesym (proj2 tnz).
move: (cpred_pr tb tnz') => []; set u := (cpred t) => [uB tsu].
have uo: u <o omega0 by apply /olt_omegaP.
have ou:= proj31_1 uo.
have us: t = osucc u.
  by rewrite tsu; apply: succ_of_finite; move: uB => /NatP.
set z := x ^o u.
case: (equal_or_not u \0o) => unz.
   case: nexy; rewrite yt tsu unz // succ_zero opowx1 //.
have z1: \1o <o z. 
  by rewrite /z  - (opowx0 x) - opow_Meqltr //; apply:ord_ne0_pos.
have oz:= proj32_1 z1.
have z2: z <=o y. 
   rewrite /z yt; apply: opow_Meqle => //.
   by rewrite us;move: (oltS ou) => [ok _].
move: (hy _ z1 z2) => [v ov].
case: (ord2_trichotomy ov).
    by move => ->; rewrite opowx0.
  move => ->; rewrite opowx1 // /z us yt.
  move=> se; move: (opow_regular xl2 ot ou se); rewrite us => bad.
  by move: (oltS ou) => [_]; rewrite bad. 
move=> v2.
have le1: (u +o u <=o (u *o v)).
  rewrite - (L6 ou); apply: oprod_Meqle => //.
suff aux : ((\1o +o osucc u) <=o (u +o u)).
  move => yv; rewrite yv /z - opow_prod //.
  apply: opow_Meqle => //; rewrite us; exact: (oleT aux le1).
have ->: \1o +o osucc u = u +o \2o.
  have oB := NS1.
  have tB:= NS2.
  have su: natp (osucc u) by ue.
```

**② gold tactic** (모델이 맞혀야 하는 것)

```coq
have fcu: finite_c u by apply /NatP.
```

**③ 진단** — 위 프롬프트 어디에도 `finite_c` 이 없다.

| 항목 | 값 |
|---|---|
| 선언 종류 | `Definition` |
| rango 풀에서 빠지는 종류인가 | **예** — 검색 후보에 애초에 안 들어간다 |
| 검색 100개 중 순위 | 검색 100개 안에 없음 |
| `func_defs` 에 정의 재료가 있나 | **있다** |
| 주입 가능한 형태인가(`pick_def`) | 예 |
| 씨앗이 닿는 출처 | **어디에도 없음** |
| 프로젝트 내 tactic 사용 | 1회 · 1개 파일 |

**④ 참고 — 인덱스에 있는 정의문** (넣을 재료는 있었다)

```coq
Definition finite_c := finite_o.
```

</blockquote>
</details>

<details>
<summary><b>사례 4 — <code>transport_paths_FFlr</code> (Definition) · 원인 D</b></summary>

<blockquote style="border-left:4px solid #4a9eff; padding-left:1em; margin-left:0">

**파일** `repos/HoTT-Coq-HoTT/theories/Colimits/Coeq.v`  ·  **idx** `1900516`

**① 모델이 보는 프롬프트 — 전문** (2048토큰 절단 **후** = 실제 입력)

```

[PREMISES]
Definition complement {A} (R : Relation A) : Relation A := fun x y => ~ (R x y).
Theorem L13 `{H : IsHProp A} : forall x y : A, x = y.
Notation concatR := (fun p q => concat q p).
Notation compose := (fun g f x => g (f x)).
Definition const {A B} (b : B) := fun x : A => b.
Global Instance iff_compose : Transitive iff | 1 := fun A B C f g => (fst g o fst f , snd f o snd g).
Definition L12 : ~ (true = false) := fun H => false_ne_true (symmetry _ _ H).
Definition L11 {A : Type} {x y : A} (p : x = y) : y = x := match p with idpath => idpath end.
Notation idmap := (fun x => x).
Definition L10 {A : Type} {x y : A} (p : x = y) : ap idmap p = p := match p with idpath => 1 end.
Definition f1 {B A f g} b : @coeq B A f g (f b) = coeq (g b) := gqglue (b; (idpath,idpath)).
Definition L9 {A} {x : A} (h : idpath x = idpath x) : whiskerL 1 h = h.
Definition L8 {A} {x : A} (h : idpath x = idpath x) : whiskerR h 1 = h.
Definition L7 {A B : Type} (z : A + B) (w : is_inr z) : inr (un_inr z w) = z.
Definition L6 {A : Type} {x y : A} (p q : x = y) : q^ @ p = 1 -> p = q.
Definition L4 {A B : Type} {x y : A} (p : x = y) (z : B) : ap (fun _ => z) p = 1 := match p with idpath => idpath end.
Definition L3 {A : Type} : path_universe (equiv_idmap A) = 1 := eta_path_universe 1.
Definition L2 {A : Type} {x y : A} (p : x = y) : p^ @ p = 1 := match p with idpath => 1 end.
Definition L5 {A : Type} {x1 x2 y : A} (p : x1 = x2) (q : x1 = y) : f0 (fun x => x = y) p q = p^ @ q.
Lemma f3 {A B} {x y : A} (P : B -> Type) (f : A -> B) (p : x = y) (z : P (f x)) : f0 (fun x => P (f x)) p z = f0 P (ap f p) z.
Definition f2 {A B : Type} {x1 x2 : A} (p : x1 = x2) (y : B) : f0 (fun x => B) p y = y.
Lemma L0 {A B C} (f : A -> B) (g g' : B -> C) (p : g = g') : f0 (fun h : B -> C => g o f = h o f) p 1 = ap (fun h => h o f) p.
Lemma L1 {B A f g} (P : @T0 B A f g -> Type) (coeq' : forall a, P (coeq a)) (cglue' : forall b, (f1 b) # (coeq' (f b)) = coeq' (g b)) (b:B) : apD (Coeq_ind P coeq' cglue') (f1 b) = cglue' b.
[PROOFS]
Definition isequiv_Coeq_rec `{T2} {B A} (f g : B -> A) P : IsEquiv (fun p : {h : A -> P & h o f == h o g} => Coeq_rec P p.1 p.2).
Proof.
  srapply (isequiv_adjointify _ (Coeq_unrec f g)).
  - intros h.
    apply path_arrow.
    srapply Coeq_ind; intros b.
    1: cbn;reflexivity.
    cbn.
    nrapply transport_paths_FlFr'.
    apply equiv_p1_1q.
    nrapply Coeq_rec_beta_cglue.
  - intros [h q]; srapply path_sigma'.
    + reflexivity.
    + cbn.
      rapply path_forall; intros b.
      apply Coeq_rec_beta_cglue.
Defined.
[STATE]
B: Type
A: Type
f, g: B -> A
b: B

f0 (fun w : T0 g f => T1 f g (T1 g f w) = w)
  (f1 b) 1 = 1
[SCRIPT]
Lemma G0 {B A} {f g : B -> A} : (T1 f g) o (T1 g f) == idmap.
Proof.
  srapply @Coeq_ind.
  - reflexivity.
  - intro b.
    simpl.
[DEFINITIONS]
Definition f0 {A : Type} (P : A -> Type) {x y : A} (p : x = y) (u : P x) : P y := match p with idpath => u end.
Definition T0@{i j u} {B : Type@{i}} {A : Type@{j}} (f g : B -> A) : Type@{u}
Definition T1 {B A} (f g : B -> A) : T0 f g -> T0 g f := Coeq_rec (T0 g f) coeq (fun b : B => (f1 b)^).
Definition f1 {B A f g} b : @coeq B A f g (f b) = coeq (g b) := gqglue (b; (idpath,idpath)).
Definition f2 {A B : Type} {x1 x2 : A} (p : x1 = x2) (y : B) : f0 (fun x => B) p y = y.
Definition f3 {A B} {FibA: Fibrant A} {FibB: Fibrant B} {x y: A} (P: B → Type) {FibP : FibrantF P} (f : A → B) ...
Monomorphic Axiom T2 : Type0.
```

**② gold tactic** (모델이 맞혀야 하는 것)

```coq
abstract (rewrite transport_paths_FFlr, Coeq_rec_beta_cglue, ap_V, Coeq_rec_beta_cglue; hott_simpl).
```

**③ 진단** — 위 프롬프트 어디에도 `transport_paths_FFlr` 이 없다.

| 항목 | 값 |
|---|---|
| 선언 종류 | `Definition` |
| rango 풀에서 빠지는 종류인가 | **예** — 검색 후보에 애초에 안 들어간다 |
| 검색 100개 중 순위 | 검색 100개 안에 없음 |
| `func_defs` 에 정의 재료가 있나 | **있다** |
| 주입 가능한 형태인가(`pick_def`) | 예 |
| 씨앗이 닿는 출처 | PROOFS |
| 프로젝트 내 tactic 사용 | 8회 · 6개 파일 |

**④ 참고 — 인덱스에 있는 정의문** (넣을 재료는 있었다)

```coq
Definition transport_paths_FFlr {A B : Type} {f : A -> B} {g : B -> A} {x1 x2 : A} (p : x1 = x2) (q : g (f x1) = x1) : transport (fun x => g (f x) = x) p q = (ap g (ap f p))^ @ q @ p.
```

</blockquote>
</details>

## 4. ★ 왜 `[TYPES]` / `[DEFINITIONS]` 주입으로 안 잡히나

> "goal 이나 가설에서 읽어서 필요한 애들을 미리 프롬프트에 다 넣으면 되지 않나?"
>
> **그게 지금 하고 있는 일이다.** `[DEFINITIONS]`/`[TYPES]` 는 goal 결론 · 가설 ·
> `[PREMISES]` 상위 12개 · `[SCRIPT]` · `[PROOFS]` 에서 이름을 뽑아 씨앗으로 삼고,
> `func_defs` 인덱스를 따라 **재귀 depth 1** 로 펼쳐 각각 300토큰까지 넣는다.
> 그런데도 안 잡힌다. 이유는 **방향**이다.

### 4-1. 두 방향은 다르다 — 완전한 사례 `IsPullback` / `isequiv_adjointify`

    goal    IsPullback (fun z : {d : D & P d * Q d} => 1 : (z.1; fst z.2).1 = (z.1; snd z.2).1)
    가설    D : Type    P : D -> Type    Q : D -> Type
    정답    srapply isequiv_adjointify.

HoTT 저장소에서 관련 선언을 그대로 꺼내면 이렇다.

```coq
(* theories/Limits/Pullback.v *)
Definition IsPullback {A B C D} {f : A -> B} {g : C -> D} {h : A -> C} {k : B -> D}
           (p : k o f == g o h) := IsEquiv (pullback_corec p).

(* theories/Basics/Overture.v *)
Class IsEquiv {A B : Type} (f : A -> B) := {
  equiv_inv : B -> A ;
  eisretr : f o equiv_inv == idmap ;
  eissect : equiv_inv o f == idmap ;
  eisadj : forall x : A, eisretr (f x) = ap f (eissect x) ; }.

(* theories/Basics/Equivalences.v *)
Definition isequiv_adjointify : IsEquiv f := Build_IsEquiv A B f g isretr issect' is_adjoint'.
```

여기서 **두 방향을 구분해야 한다.**

| 방향 | 무엇인가 | 누가 하나 |
|---|---|---|
| **아래로 (unfold)** | goal 의 이름 → 그 **정의** → 그 정의가 쓰는 이름 → … <br>= goal 이 **무엇으로 만들어졌나** | `[TYPES]` / `[DEFINITIONS]` 주입 |
| **위로 (mention)** | goal 의 어휘를 **언급하는** 선언들 <br>= goal 에 **관한** 정리 | 검색기(랭커) |

`isequiv_adjointify` 는 `IsPullback` 의 **재료가 아니다.** `IsPullback` 을 아무리 펼쳐도
그 안에 없다 — 펼치면 `IsEquiv`, `pullback_corec`, 그 다음엔 `equiv_inv`·`eisretr`·
`eissect`·`eisadj` 가 나온다. `isequiv_adjointify` 는 **`IsEquiv` 를 만들어 주는 도구**이지
`IsEquiv` 의 구성요소가 아니다.

그리고 **원래 goal 의 어휘로는 위로도 못 올라간다.** 실측:

| 항목 | 값 |
|---|---|
| goal 의 식별자 (3글자 이상 · Coq 핵심어휘 제외) | `{IsPullback}` — **단 1개** |
| `isequiv_adjointify` 선언의 식별자 | `{IsEquiv, Build_IsEquiv, isretr, issect', is_adjoint', isequiv_adjointify}` |
| **두 집합의 교집합** | **공집합** |

그래서 tf-idf 든 무엇이든 goal 을 질의로 쓰는 랭커는 이 lemma 에 **0점**을 준다.
순위 70위는 점수가 낮아서가 아니라 **점수가 없어서** 생긴 값이다.

### 4-2. 경로가 아예 없는 건 아니다 — **아래로 1 + 위로 1**

`IsPullback` 을 **한 걸음만** 펼치면 `IsEquiv` 가 나오고, `isequiv_adjointify` 의
**타입이 바로 `IsEquiv`** 다. 즉 아래로 한 걸음 → 위로 한 걸음이면 닿는다.
문제는 **그 한 걸음에서 후보가 몇 개로 벌어지는가**다.

> ⚠ 표현 주의 — 이건 "부채꼴" 이나 "exponential 폭발" 이 **아니다.**
> 아래 ①②③ 에서 보듯 **한 번 크게 벌어지고 곧바로 포화**한다(405 → 628 → 628).
> 모양은 부채(점진적으로 넓어짐)도 나무(가지가 계속 갈라짐)도 아니고,
> **허브를 거쳐 한 번에 펼쳐지는 별**이다:
>
>     IsPullback ──펼침──► IsEquiv ──언급──► 752개
>       (변두리, 27개)      (HoTT 2위 허브)      └── 여기서 끝
>
> 이 구분이 처방을 가른다. 진짜 exponential 이면 **깊이를 낮추면** 되는데,
> 실제로는 depth 0 = 14개(정답 없음) / depth 1 = 405개(정답 있음) 로 **중간이 없다.**
> 깊이는 손잡이가 아니다.

| 단계 | 개념 수 | 그 개념을 언급하는 HoTT 선언 | 정답 포함 |
|---|---|---|---|
| goal 그대로 | 1 (`IsPullback`) | 14 | ✗ |
| **아래로 1걸음** | 3 (`IsPullback`, `IsEquiv`, `pullback_corec`) | **405** | **✓** |
| └ `IsEquiv` 하나로만 좁혀도 | 1 | **392** | ✓ |
| 아래로 2걸음 | 9 | 628 | ✓ |
| **프롬프트 premise 예산** | | **≈ 22개** | |

**405개 중 22개를 고르는 문제**가 된다. 그리고 그 405개 안에는 `isequiv_biinv` ·
`isequiv_homotopic` · `equiv_adjointify` · `isequiv_commsq` … 가 전부 들어 있다.
어느 것이 정답인지는 **"역함수를 직접 주자" 라는 증명 전략**이 정하고,
그 전략은 goal 텍스트 어디에도 안 적혀 있다. 이것이 §1-1 이다.

**★ 이건 exponential 폭발이 아니다 — 허브 점프 + 포화다.**

깊이를 늘리며 후보가 어떻게 커지는지 재면 이렇다 (HoTT 선언 16,264개 기준):

| depth | 개념 수 | 증가 | 언급 선언 수 | 증가 | 라이브러리 대비 | 정답 포함 |
|---|---|---|---|---|---|---|
| 0 (goal 그대로) | 1 | — | **14** | — | 0.1% | ✗ |
| 1 | 3 | ×3.00 | **405** | **×28.93** | 2.5% | ✓ |
| 2 | 9 | ×3.00 | 628 | ×1.55 | 3.9% | ✓ |
| 3 | 9 | ×1.00 | 628 | ×1.00 | 3.9% | ✓ |
| 4 | 9 | ×1.00 | 628 | ×1.00 | 3.9% | ✓ |

exponential 이면 405 → 1,600 → 6,400 이어야 하는데 **628에서 고정점에 도달한다.**
폭발이 아니라 **포화**다. 구조는 두 가지다.

**① 허브를 한 번 밟으면 29배 점프한다.** `IsPullback` 은 27개 선언만 언급하는 변두리
개념인데, 한 걸음 펼치면 `IsEquiv` 가 나온다. HoTT 에서 `IsEquiv` 를 언급하는 선언은
**752개, 전체 2위 허브**다. 언급 관계의 out-degree 분포(개념 10,782개):

    중앙 2 · p75 4 · p90 10 · p99 68 · 최대 989(`Funext`)
    상위 허브: Funext×989 · IsEquiv×752 · Univalence×663 · pType×639 · AbGroup×627

전형적인 **멱법칙(허브 구조)** 이지 exponential 분기가 아니다. 수학 라이브러리는
나무가 아니라 소수의 허브에 다 매달린 그래프다.

**② 그래서 depth 로는 22개로 못 줄인다 — 쓸 만한 중간 눈금이 없다.**

    depth 0 → 14개   예산(22)에 들어간다.  그런데 **정답이 없다**
    depth 1 → 405개  정답이 있다.          예산 **18배 초과**
    그 사이 → 없다

문제는 "너무 빨리 커진다" 가 아니라 **"고를 수 있는 크기의 후보 집합이 존재하지 않는다"** 다.
405 → 22 로 줄이려면 depth 가 아니라 **랭킹**이 필요한데, 그 405개는 전부 `IsEquiv` 를
언급하므로 `IsEquiv` 기준 유사도로는 **하나도 구분되지 않는다.**
구분하는 정보는 **증명 전략**뿐이고, 그것이 §1-1 이다.

**③ 다만 도달 가능 집합이 작다는 건 희망적이다.**

628개는 라이브러리의 **3.9%** 다. 전체가 아니다. 그 안에서 22개를 고를 신호만 있으면 된다.
그리고 그 신호의 후보가 하나 있다 — **`[PROOFS]`(유사 증명) 섹션**이다. "이 goal 과
비슷한 것" 이 아니라 **"이런 상황에서 사람들이 무엇을 했나"** 라는 **다른 축**이다.
실측 사례(§3 사례 2, `whiskerL_pp`)에서 `[PROOFS]` 에는 이게 들어 있었다:

```coq
[PROOFS]  abstract (rewrite !whiskerR_pp, !concat_pp_p; reflexivity).   (* 형제 — R *)
gold      abstract (rewrite !whiskerL_pp, !concat_pp_p; reflexivity).   (* 정답 — L *)
```

**전략은 정확히 맞았고 이름 한 글자만 달랐다.** goal 유사도 축에서는 영영 못 찾을 것을
증명 유사도 축은 거의 잡고 있었다는 뜻이다. 다만 그 축을 **검색에** 쓰고 있지는 않다 —
지금은 `[PROOFS]` 를 프롬프트에 보여 주기만 하고, premise 랭킹에는 안 쓴다.
(유사 증명이 부르는 이름을 premise 후보로 승격시키는 것 = **앞으로 해 볼 만한 방향**.)

**일반화 — 덤프한 결손 이름 40개 전수** (분모 = 결손 이름 40개):

| 경로 | 닿음 | 비율 |
|---|---|---|
| 아래로만 (depth 3 까지) | 5 / 40 | 12.5% |
| 위로만 (원래 goal 어휘) | 7 / 40 | 17.5% |
| **아래로 1 + 위로** | **8 / 40** | **20.0%** |
| 그때의 후보 수 | 중앙 **1,203개** · p75 3,031 · 최대 4,768 | 예산 22개 |

즉 **80% 는 어느 경로로도 안 닿고, 닿는 20% 도 후보가 중앙 1,203개**다.
"필요한 애들을 미리 다 넣기" 에서 **'필요한' 을 판정할 근거가 프롬프트에 없다.**

### 4-3. 그래서 주입이 실패하는 네 가지 방식

덤프한 gold 원본 환각 25건을 원인별로 나누면 (분모 = 25건):

| 원인 | 건수 | 비율 | 무슨 뜻인가 |
|---|---|---|---|
| **A** | 12 | **48.0%** | `func_defs` 인덱스에도 검색 결과에도 없다 — **넣을 재료 자체가 없다** |
| **B** | 8 | 32.0% | 검색 결과에는 있는데 재랭킹·예산에 밀려 프롬프트에 안 실렸다 |
| **C** | 3 | 12.0% | 재료는 인덱스에 있는데 **씨앗이 닿지 않는다**(이름이 goal·SCRIPT·PROOFS 어디에도 없다) |
| **D** | 2 | 8.0% | 씨앗은 닿는데 300토큰 예산·개수 캡에 밀렸다 |

**C 가 §4-1 의 방향 문제를 그대로 보여 준다.** 재료는 있는데 그리로 가는 길이 없다.

### 4-4. 원인 C 의 실제 사례 — 재료는 있는데 길이 없다

아래 둘은 `func_defs` 인덱스에 **정의문이 그대로 들어 있다**(진단표 ④ 참고).
그런데 그 이름이 goal·`[SCRIPT]`·`[PROOFS]`·`[PREMISES]` 어디에도 없어서
씨앗이 출발할 곳이 없다. 넣을 재료를 손에 쥐고도 **누구를 넣어야 하는지 모른다.**

<details>
<summary><b>사례 1 — <code>restriction2</code> (Definition) · 원인 C</b></summary>

<blockquote style="border-left:4px solid #4a9eff; padding-left:1em; margin-left:0">

**파일** `repos/coq-community-gaia/theories/ordinals/ssete2.v`  ·  **idx** `1430738`

**① 모델이 보는 프롬프트 — 전문** (2048토큰 절단 **후** = 실제 입력)

```

[PREMISES]
Definition union (X: Set) := uniont (@Ro X).
Lemma L28 (x : Set) (a : x): f7 (Ro a) x.
Definition L27 (x: Set) := triple f0 x f0.
Definition complement (A B : Set) := T1 A (fun x : Set => ~ f7 x B).
Definition L25 (x : Set) := Lg x id.
Axiom R_inj : forall (x : Set), injective (@Ro x).
Definition L26 r X := the_greatest (f3 r (T1 (f5 r) (lower_bound r X))).
Definition singleton (x : Set) := doubleton x x.
Definition L24 r X x := greatest (f3 r X) x.
Definition L22 (x : Set) := T1 (union x) (fun y : Set => forall z : Set, f7 z x -> f7 y z).
Definition sub (x y : Set) := forall z : Set, f7 z x -> f7 z y.
Definition L23 r X x := least (f3 r X) x.
Definition L19 (x : Set) := choose (fun y : Set => f7 y x).
Definition L18 (x: Set) := exists y: Set, f7 y x.
Definition f3 r a := r \cap (coarse a).
CoInductive f0 : Set :=.
Lemma L21 r A: left_directed r -> coinitial r A -> left_directed (f3 r A).
Lemma L20 r A: right_directed r -> cofinal r A -> right_directed (f3 r A).
Lemma L17 r x y: sub (segment (f3 r x) y) x.
Lemma L16 r a: sub a (f5 r) -> preorder r -> preorder (f3 r a).
Definition f13 r x := (f3 r (segment r x)).
Definition L15 r := order r /\ forall x, sub x (f5 r) -> L18 x -> has_least (f3 r x).
Definition f10 f r r' := [/\ order r, order r', f11 f (f5 r) (f5 r') & f6 f r r'].
Lemma L14 r x: order r -> commutes_at (f3 ^~ x) (opp_order) r.
Lemma L13 r A: L15 r -> sub A (f5 r) -> L15 (f3 r A).
Lemma L12 r x: sub x (f5 r) -> equivalence r -> equivalence (f3 r x).
Lemma L11 r x: f8 r -> sub x (f5 r) -> f8 (f3 r x).
Lemma L10 r r': order r -> order r' -> f12 (f5 r) -> f12 (f5 r') -> r \Is r'.
Lemma L8 x y: f8 x -> order y -> sub x y -> (sub (f5 x) (f5 y) /\ x = (f3 y (f5 x))).
Lemma L9 r a: order r -> sub a (f5 r) -> f9 (f3 r a) a.
Lemma L7 r a: preorder r -> sub a (f5 r) -> f5 (f3 r a) = a.
Lemma L6 r: order r -> r \Is r.
Lemma L5 r r': r \Is r' -> r' \Is r.
Lemma L3 r: f3 r f0 = f0.
Lemma L4 r' r r'': r \Is r' -> r' \Is r'' -> r \Is r''.
Lemma L2 r a: order r -> sub a (f5 r) -> f5 (f3 r a) = a.
Lemma L1 a b c: sub c b -> f3 (f3 a b) c = f3 a c.
Lemma L0 r: order r -> f3 r (f5 r) = r.
[PROOFS]
Lemma increasing_compose f g r r' r'': f10 f r r' -> f10 g r' r'' -> [/\ g \coP f, (forall x, f7 x (source f) -> T0 (g \co f) x = T0 g (T0 f x)) & f10 (g \co f) r r''].
Proof.
move=>  [or or' [ff sf tf] icf][_ or'' [fg sg tg] icg].
have cgf: (g \coP f) by split => //; ue.  
have p:(forall x, f7 x (source f) -> T0 (g \co f) x = T0 g (T0 f x)).
  move=> x xsf; rewrite compfV//.
split => //; split => //; first by saw; fct_tac.
move => x y xy.
have xsf: f7 x (source f) by rewrite sf; order_tac.
have ysf: f7 y (source f) by rewrite sf; order_tac.
by rewrite p // p //; apply: icg; apply: icf.
Qed.
[STATE]
r, r', f, g: Set
A: Set
B: Set
o1: order r
o2: order r'
ff: f4 f
sf: source f = f5 r
tf: target f = f5 r'
incf: f6 f r r'
fg: f4 g
sg: source g = f5 r'
tg: target g = f5 r
incg: f6 g r' r
p1: forall x : Set, f7 x A -> f7 (T0 f x) B
p2: forall x : Set, f7 x B -> f7 (T0 g x) A

f3 r A \Is f3 r' B
[SCRIPT]
Lemma G0 r r' f g: let A := T1 (f5 r) (fun z => T0 g (T0 f z) = z) in let B := T1 (f5 r') (fun z => T0 f (T0 g z) = z) in f10 f r r' -> f10 g r' r -> (f3 r A) \Is (f3 r' B).
Proof. 
move=>  A B [o1 o2 [ff sf tf] incf][_ _ [fg sg tg] incg].
have p1: (forall x, f7 x A -> f7 (T0 f x) B). 
  by move=> x /Zo_P [xsr r1]; apply: Zo_i; [Wtac | rewrite r1].
have p2: (forall x, f7 x B -> f7 (T0 g x) A). 
  by move=> x /Zo_P [xsr r1]; apply: Zo_i ; [Wtac | rewrite r1].
[TYPES]
CoInductive f0 : Set :=.
Inductive f1 (s : infseq T) : infseq T -> Prop := | C0 : f1 s s | C1 : forall x s0, f1 s s0 -> f1 s (Cons x s0).
Inductive f2 := plus | mult | zero | one | negate.
[DEFINITIONS]
Definition f3 r a := r \cap (coarse a).
Definition f4 f := [/\ correspondence f, fgraph (graph f) & source f = domain (graph f)].
Definition f5 r := (domain r) \cup (range r).
Definition f6 f r r' := forall x y, gle r x y -> gle r' (T0 f x) (T0 f y).
Definition f7 (x y : Set) := exists a : y, Ro a = x.
Definition T0 f x := Vg (graph f) x.
Definition f8 r := order r /\ {f7 (f5 r) &, (forall x y, ocomparable r x y)}.
Definition f9 r E := order r /\ f5 r = E.
Definition f10 f r r' := [/\ order r, order r', f11 f (f5 r) (f5 r') & f6 f r r'].
Definition f11 f s t:= [/\ f4 f, source f = s & target f = t].
Definition f12 (x:Set) := exists u, x = singleton u.
Definition T1 (x:Set) (p:property) := IM (fun (z : Zorec (fun (a : x) => p (Ro a))) => let (a, _) := z in Ro a).
Definition f13 r x := (f3 r (segment r x)).
[NOTATION]
Notation "x \Is y" := (order_isomorphic x y).
```

**② gold tactic** (모델이 맞혀야 하는 것)

```coq
have Ha: source (restriction2 f A B) = A by rewrite / restriction2; aw.
```

**③ 진단** — 위 프롬프트 어디에도 `restriction2` 이 없다.

| 항목 | 값 |
|---|---|
| 선언 종류 | `Definition` |
| rango 풀에서 빠지는 종류인가 | **예** — 검색 후보에 애초에 안 들어간다 |
| 검색 100개 중 순위 | 검색 100개 안에 없음 |
| `func_defs` 에 정의 재료가 있나 | **있다** |
| 주입 가능한 형태인가(`pick_def`) | 예 |
| 씨앗이 닿는 출처 | **어디에도 없음** |
| 프로젝트 내 tactic 사용 | 77회 · 12개 파일 |

**④ 참고 — 인덱스에 있는 정의문** (넣을 재료는 있었다)

```coq
Definition restriction2 f x y := triple x y ((graph f)\cap (x \times (target f))).
```

</blockquote>
</details>

<details>
<summary><b>사례 2 — <code>isEqualizer_PfPg</code> (Definition) · 원인 C</b></summary>

<blockquote style="border-left:4px solid #4a9eff; padding-left:1em; margin-left:0">

**파일** `repos/k27c8ff627uxz-quotient_in_coq/src/Construction/construction_of_coequalizer.v`  ·  **idx** `98907`

**① 모델이 보는 프롬프트 — 전문** (2048토큰 절단 **후** = 실제 입력)

```

[PREMISES]
Lemma L28 : f13 (power_f kappa).
Lemma L26 : forall p, to_power (of_power p) = p.
Lemma L25 : forall p, of_power (to_power p) === p.
Lemma L24 {A} : f13 (@to_power A).
Theorem L23 : isEqualizer f1 f2 T0.
Lemma L22 : g' === f11 T0 CEqualizer_factor.
Lemma L21 : f11 f1 T0 === f11 f2 T0.
Lemma L20 : forall u', g' === f11 T0 u' -> u' === CEqualizer_factor.
Lemma L19 : forall {A : Type}, f11 (power_f (f10 A)) (f10 (power A)) === id.
Definition f10 (A : Type) : A -> power (power A) := fun a => to_power (fun pa => (of_power pa) a).
Lemma L18 : forall {A B : Type} (f : A -> B), power_f f (empty_power B) === empty_power A.
Lemma L16 : forall b, b = false -> ~b = true.
Lemma L17 : proof_irrelevance -> equalizer_exists.
Lemma L15 : forall b, ~b = true -> b = false.
Lemma L14 : forall {A : Type}, power_f (@id A) === id.
Lemma L13 : forall {A B} (f1 f2 : A -> B), f1 === f2 -> (forall a, f1 a = f2 a).
Lemma L12 : coequalizer_exists -> quotient_exists.
Lemma L11 : forall {A} (P : A -> Prop), (~exists x, P x) -> forall x, ~P x.
Lemma L10 : forall {A B C : Type} (f g : A -> B) (h : B -> C), isSplitCoequalizer f g h -> isCoequalizer f g h.
Lemma L9 : forall (f : C -> D) (g : B -> C) (h : A -> B), f11 (f11 f g) h === f11 f (f11 g h).
Definition power (A : Type) : Type := q_type _ _ (proof_power_exists A).
Lemma L8 : forall {A B C : Type} (f1 f2 : B -> A) (g : C -> B), isEqualizer f1 f2 g -> isEqualizer f2 f1 g.
Definition f11 (f : B -> C) (g : A -> B) : A -> C := fun a => f (g a).
Lemma L6 : forall {A B : Type} (f : A -> B), f11 id f === f.
Lemma L7 : forall {C : Type} (g : B -> C), isCoequalizer g -> f13 g.
Lemma L5 : forall {A B : Type} (f : A -> B), f11 f id === f.
Lemma f12 : forall {A : Type}, f13 (@id A).
Definition f11 {A B C : Type} (f : B -> C) (g : A -> B) : A -> C := fun a => f (g a).
Lemma L4 : forall f, f7 f -> forall a1 a2, f a1 = f a2 -> a1 = a2.
Lemma L3 : forall A, f7 (f10 A).
Lemma f9 : forall {A : Type}, f7 (@id A).
Lemma L2 : forall f, (forall a1 a2, f a1 = f a2 -> a1 = a2) -> f7 f.
Lemma L1 : forall {C : Type} (g : C -> B), isEqualizer g -> f7 g.
Lemma L0 : f7 T0.
[PROOFS]
Lemma L29 : (f10 A) === f11 kappa epsilon'.
    Proof.
      generalize (proj2_sig epsilon'_equalizer_univ); intro HH.
      destruct HH as [HH _].
      unfold epsilon'.
      apply HH.
    Qed.
Lemma L27 : forall A, f13 (power_f (f10 A)).
  Proof.
    intro A.
    apply (L7 _ _ _ (isCoequalizer_power_epsilon A)).
  Qed.
Lemma L4 : forall f, f7 f -> forall a1 a2, f a1 = f a2 -> a1 = a2.
  Proof.
    intros f monof a1 a2 eqfa.
    cut ( (fun (i : True) => a1) === (fun (i : True) => a2)).
    {
      intro eH.
      apply (eH I).
    }
    apply monof.
    unfold f11.
    intro i.
    assumption.
  Qed.
Lemma L3 : forall A, f7 (f10 A).
  Proof.
    intro A.
    apply (L1 _ _ _ (isEqualizer_power_epsilon A)).
  Qed.
[STATE]
instance_proof_irrelevance: f0
instance_power_exists: f3
instance_preserve_reflexive_equalizer: f4
instance_power_reflects_iso: f5
instance_power_f_faithful: f6
B: Type
A: Type
f, g: B -> A

f7 f8
[SCRIPT]
Lemma G0 : f7 f8.
  Proof.
[TYPES]
Class f0 := { proof_proof_irrelevance : proof_irrelevance }.
Class f3 := { proof_power_exists : power_exists }.
Class f4 := { proof_preserve_reflexive_equalizer : preserve_reflexive_equalizer }.
Class f5 := { proof_power_reflects_iso : power_reflects_iso }.
Class f6 := { proof_power_f_faithful : power_f_faithful }.
[DEFINITIONS]
Definition f7 (f : A -> B) := forall (X : Type) (u1 u2 : X -> A), f11 f u1 === f11 f u2 -> u1 === u2.
Definition f8 : V -> power A := equalizer_fun _ _ Vtau_equalizer.
Definition T0 : T1 -> B := fun c => proj1_sig c.
Program Definition f9 (C:category) (A:C) := Monomorphism C A A (id(A)) _.
Definition f10 (A : Type) : A -> power (power A) := fun a => to_power (fun pa => (of_power pa) a).
Definition f11 (f : B -> C) (g : A -> B) : A -> C := fun a => f (g a).
Program Definition f12 (C:category) (A:C) := Epimorphism C A A (id(A)) _.
Definition f13 (f : A -> B) := forall (X : Type) (u1 u2 : B -> X), f11 u1 f === f11 u2 f -> u1 === u2.
Definition T1 : Type:= { b : B | f1 b = f2 b }.
Definition unfold (t : F(later (mu F))) : mu F := eq_rect _ (id(A:=Type)) t _ (eq_sym eqmu).
```

**② gold tactic** (모델이 맞혀야 하는 것)

```coq
apply (L1 _ _ _ isEqualizer_PfPg).
```

**③ 진단** — 위 프롬프트 어디에도 `isEqualizer_PfPg` 이 없다.

| 항목 | 값 |
|---|---|
| 선언 종류 | `Definition` |
| rango 풀에서 빠지는 종류인가 | **예** — 검색 후보에 애초에 안 들어간다 |
| 검색 100개 중 순위 | 검색 100개 안에 없음 |
| `func_defs` 에 정의 재료가 있나 | **있다** |
| 주입 가능한 형태인가(`pick_def`) | 예 |
| 씨앗이 닿는 출처 | **어디에도 없음** |
| 프로젝트 내 tactic 사용 | 1회 · 1개 파일 |

**④ 참고 — 인덱스에 있는 정의문** (넣을 재료는 있었다)

```coq
Definition isEqualizer_PfPg : isEqualizer (power_f f) (power_f g) tau := equalizer_isequalizer _ _ Vtau_equalizer.
```

</blockquote>
</details>

### 4-5. 정리 — 주입을 더 키워도 안 되는 이유

| 손볼 수 있는 것 | 왜 안 되나 |
|---|---|
| 씨앗 출처를 넓힌다 (이미 goal·가설·premises·SCRIPT·PROOFS 전부 씀) | 원인 C 는 **어디에도 이름이 없다.** 넓힐 출처가 남아 있지 않다 |
| 재귀 depth 를 올린다 (1 → 2, 3) | 방향이 **아래로**다. `isequiv_adjointify` 는 `IsPullback` 의 재료가 아니라 **도구**라 아무리 펼쳐도 안 나온다 (실측: depth 3 까지 12.5%만 도달) |
| 토큰 예산을 늘린다 (300 → 600) | 실측: 환각률 17.6% → 17.6% (변화 없음), premise 만 14.4개 → 13.5개로 줄었다. **되돌렸다** |
| 개수 캡을 올린다 (8 → 20) | 실측: **효과 0**. 실제로 생성되는 정의가 5·3·2개라 캡이 닿지도 않았다 |
| 위로(언급) 색인을 만든다 | 후보가 중앙 **1,203개** (예산 22개). 그 안에서 고르는 정보가 goal 에 없다 |

**남는 결론**: `[TYPES]`/`[DEFINITIONS]` 는 **goal 을 이해하는 데** 필요한 것을 넣는 장치다
(정의·생성자·필드). 그건 잘 작동한다 — `Field` 는 결손률 2.0%, `Fixpoint` 0.0% 다.
그러나 **다음에 쓸 lemma 를 고르는 것**은 다른 문제이고, 주입으로는 원리적으로 못 한다.

---
## 5. cut(assert) 이 이걸 푸는가

### 5-1. 무엇을 하는가 — **질의를 바꾼다**

    원래   apply L.                                    ← L 이 검색 안 됨
    cut    assert (P) as H_asrt0.   Γ ⊢ G             ← 명제 P 를 **만든다**
           { exact L. }             Γ ⊢ P             ← 이제 goal 이 P 다
           apply H_asrt0.           Γ, H:P ⊢ G        ← 자명

핵심은 두 번째 줄이다. `P` 는 `L` 의 **진술**이므로, goal 이 `P` 가 되는 순간
`sim(P, L)` 이 최대가 된다. **§1-1 이 정확히 이 지점에서 무력화된다** — 필요한 lemma 가
goal 의 함수가 아니었는데, **goal 을 그 lemma 의 진술로 바꿔** 함수로 만들어 버린다.

**실측**
- assert 후 재검색하면 `L` 이 잡히는 비율 **88.6%** (`eqx` C 측정)
- 그때 지시자 `1[d_AU=0]` 발화율 **95.8%** (§1-5 표)

### 5-2. §1 의 이유별로 무엇을 푸는가

| §1 의 이유 | cut 이 푸는가 |
|---|---|
| 1-1 lemma 가 goal 의 함수가 아님 | ✅ **푼다.** goal 을 lemma 진술로 바꿔 함수로 만든다 |
| 1-2 이름이 임의적 | ✅ **우회한다.** `assert` 스텝은 **이름이 아니라 명제**를 요구한다. 명제는 논리적 내용을 담고 goal 의 어휘로 쓰인다 |
| 1-3 손실 있는 렌더링 | ➖ 부분적. `P` 를 세울 때 렌더링된 goal 에서 출발하므로 지워진 이름은 여전히 안 보인다 |
| 1-4 롱테일 | ✅ **우회한다.** 이름의 희소성과 무관하다 — 명제만 맞으면 된다 |
| 1-5 순환성 | ❌ **그대로다.** cut 계획을 **정답에서 뽑는다.** 학습 데이터 생성에는 정당하지만, 추론 시에는 모델이 `P` 를 스스로 세워야 한다 |
| 1-6 예산 | ➖ 무관 |

**한 줄 요약**: cut 은 "이름 회상" 문제를 **"명제 합성 + 정확히 맞는 검색"** 으로 바꾼다.
후반부는 88.6% 로 풀리고, 전반부(명제 합성)는 **원래 증명의 창의적인 부분**이다.
문제를 없앤 게 아니라 **풀 수 있는 형태로 옮겼다.**

### 5-3. cut 자신이 만드는 환각 — 그러나 gold 보다 적다

하위스텝 셋은 성격이 다르다 (**분모 = 전체 하위스텝 30,000개**):

| 종류 | 개수 | 비중 | 성격 |
|---|---|---|---|
| `assert` | 10,305 | 34.4% | goal 로부터 명제를 추론 → **프롬프트만으로 풀 수 있다** |
| `close` | 10,171 | 33.9% | `exact L.` = **순수 이름 회상** → L 을 못 보면 환각 학습 |
| `final` | 9,524 | 31.7% | `apply H_asrt0.` → 자명 |

`close` 는 cut 이 막으려던 바로 그 문제를 되불러온다.
**실측 (분모 = cut 프롬프트 300건 안의 `exact` 대상 85개)**:

    ✓ 프롬프트에 있다    39      가시율 45.9%
    ★ 없다              46

원인은 재검색 실패가 아니었다. 재검색은 정확히 작동했고, 대상이 대부분 **stdlib** 이라
`PremiseFilter` 가 풀에서 뺐다 — 랭커는 풀에 없는 것을 못 올린다.

**고침**: `close` 스텝에서 `L` 이 재검색 뒤에도 안 보이면 **같은 lemma 의 `assert`
스텝으로 물러선다**(가드 G1b, stdlib 은 예외). 가시율 45.9% → 95.5% →
`_fit_premises` 에 `rerank_premises` 누락을 고쳐 **100.0%** (`verify_u1 300`, 22/22).

### 5-4. 적용 범위

    cut 이 걸리는 스텝                12.34%   (분모 = 전체 학습 스텝)
    hopeless(cut 도 못 세움) 학습 제외   6.60%
    계획 cut 이 Coq 에서 실패          4.8% × 12.34% = 전체의 0.59%

cut 은 전체의 **약 1/8** 을 다룬다. 나머지는 애초에 검색이 성공하거나, 가망이 없어 제외된다.

---
## 6. 결론 — 실제로 가능한 것

프롬프트에 없는 이름을 **근거 있게** 맞히는 것은 §1-1·1-2·1-3 때문에 원리적으로 막힌다.
1-4·1-5·1-6 은 그 위에서 규모를 키우는 요인이다. 세 개입(프로젝트 notation · 역인덱스 ·
사용 기반 풀 확대)을 다 합쳐 **약 −1pp** 밖에 안 나온 것은 구현이 부족해서가 아니라
이 구조 때문이다.

남는 길은 셋이다.

**① 이름이 필요 없게 만든다 — cut/assert 가 이쪽이다.**
명제는 goal 에서 유도되므로 §1-1·1-2·1-4 를 우회한다. `auto`/`eauto`/`typeclasses eauto`
같은 검색 tactic 도 같은 성질이다 — 이름을 부르지 않고 Coq 에게 찾게 한다.
**가장 원리적으로 옳은 방향이고, 우리가 이미 가진 기계다.**
실측으로도 cut 스텝의 환각률이 gold 스텝의 **절반 이하**다(§2-5).

**② 모델이 그 프로젝트를 알게 한다.**
프로젝트별 적응. 환각을 없애는 게 아니라 **암기를 정확하게** 만드는 것이고,
§1-2 상 익명화와 트레이드오프다.

**③ 환각을 없애지 말고 싸게 만든다.**
정리증명기에서 환각은 산문 LLM 의 환각과 성질이 다르다 — Coq 이
`The reference X was not found` 로 **즉시·확실하게** 거부한다. 조용히 틀린 답이
통과하지 않는다. 즉 **검출 가능한 안전 실패**다. 그렇다면 목표는 "0으로 만들기" 가 아니라
**"거부당했을 때 싸게 회복하기"**(재시도 예산 · 에러 조건부 생성)가 된다.

남은 환각은 `DROP_HALLUC=1` 이 이미 0.00% 로 만든다(학습데이터 비용 2.4%).
그 이상은 ①②③ 의 문제이지 프롬프트 구성의 문제가 아니다.

---

## 부록 A. 이 문서에 쓰인 스크립트

| 스크립트 | 무엇을 재나 |
|---|---|
| `scripts/probe_extref_halluc.py` | 외부 참조를 쓰는 예제 중 환각률 (H1/H2/H3) |
| `scripts/probe_halluc_source.py` | 출처별(gold vs cut) 분류 |
| `scripts/probe_admit_rank.py` | 풀에 넣은 premise 가 몇 위에 오는가 |
| `scripts/probe_reach_direction.py` | 아래로 / 위로 / 아래1+위로 도달성 |
| `scripts/probe_name_recall.py` | 부류별 사전학습 회상률 (익명화 근거) |
| `scripts/probe_anon_confound.py` | 익명화 탓 오신고가 있나 (측정 버그 점검) |
| `scripts/dump_halluc_cases.py` | 사례를 프롬프트 전문 + 진단으로 덤프 |
| `scripts/gen_halluc_examples.py` | 덤프를 md 토글 조각으로 변환 |
