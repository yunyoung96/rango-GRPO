# 나중에 해볼 것 — 검색 개선 아이디어

> 지표 정의는 [README](README.md). 현재 최선은 [final.md](final.md) 의 `eqcov`
> (목표지표 ALL@50 TEST 95.6 / VAL 94.9 / TRAIN 97.2%).
>
> ★ **추측으로 순서를 정하지 말 것.** 이 프로젝트에서 작은 표본·약한 기준선만 보고
> "된다" 고 판단했다가 뒤집힌 적이 네 번 있다(학습 랭커 · Coq `Fail` 필터 ·
> 계층 랭커 · contrastive). 아이디어마다 **먼저 여지를 재고** 착수한다.

---

## 우선순위

| # | 아이디어 | 겨냥하는 손실 | 여지 |
|---|---|---|---|
| ① | **파서 recall 개선** | 구조 신호 전체 | gold 파싱 실패가 절반 |
| ② | **head 역인덱스로 후보 확장** | stage1 상한 25.7% | 측정 필요 |
| ③ | 가설부 매칭(E) 신호 추가 | apply 계열 | 특징으론 있으나 미사용 |
| ④ | 다중 lemma 다양성 재랭킹 | R−ALL 격차 9.2pp | 격차만큼 |
| ⑤ | 부분항별 다중 질의 | rewrite 계열 | 측정 필요 |
| ⑥ | Definition 특별 처리 | 구조 신호가 안 통함 | 비중 측정 필요 |
| ⑦ | 증명 동시출현 사전확률 | 전반 | 측정 필요 |
| ⑧ | contrastive 재시도 | — | **낮음** (아래) |
| ⑨ | `NORMALIZE_RATE` ablation | 암기 vs 읽기 | 근거 없이 0.5 |
| ⑩ | 추론 정규화 시 역매핑 | **켜면 즉시 깨짐** | 안전장치 |
| ⑪ | **built-in 은 익명화·주입 제외** | 사전학습 지식을 막고 있다 | **구현 예정** |

---

## ① 파서 recall 개선 ★ 가장 큰 지렛대

**증상**: 적용가능 판정의 **gold recall 이 46~50%** 다. `decompose`/`parse` 가
notation·mathcomp 표기에서 실패하면 그 premise 는 구조 신호가 **전부 0** 이 된다.

**왜 중요한가**: C'(결론구조) · eq(트리일치) · 적용가능 — **세 신호가 같은 파서를 쓴다.**
파서를 고치면 셋이 동시에 좋아진다. 지금 `eq` 가 C 에서만 통하고 A 에서 무해에 그치는 것,
적용가능을 필터로 못 쓰는 것(§16 에서 R@50 −9pp)이 전부 여기서 온다.

**할 일**
  · 파싱 실패 premise 를 유형별로 모은다 (어떤 notation 이 얼마나?)
  · 상위 몇 개 유형만 처리해도 recall 이 얼마나 오르는지 본다
  · `Set Printing All` 로 얻은 형태를 파서에 넣는 경로도 검토 (notation 이 펴진다)

---

## ② head 역인덱스로 후보 확장 ★ 상한을 통째로 올린다

**증상**: 후보가 **tfidf 상위 N** 에서만 온다. gold 가 tfidf 5000위면 재랭킹이 손댈 수 없다.

```
gold 전부가 tfidf 상위  400 안   56.7%
gold 전부가 tfidf 상위 2000 안   74.3%   ← 나머지 25.7% 는 원리적으로 못 잡는다
```

**아이디어**: 결론 **head 심볼**로 역인덱스를 만들어 후보를 합친다. goal 결론 head 가
`le` 면 결론이 `le …` 인 premise 를 tfidf 순위와 무관하게 후보에 넣는다.

    후보 = tfidf 상위 N  ∪  head 인덱스[goal 결론 head]

head 인덱스가 작으면 비용이 거의 없고 상한이 통째로 올라간다. 크면 head+두번째 심볼로
좁힌다. `scripts/headroom.py` 가 크기와 gold 포함률을 잰다.

---

## ③ 가설부 매칭(E) 신호 추가

`sig_hyp_match` — lemma 의 **가설**이 goal 문맥에 이미 있는가. `apply X` 는 X 의 가설을
새 subgoal 로 남기는데, 이미 있으면 바로 닫히므로 훨씬 유망하다.

**GBDT 특징(12개)에는 들어 있지만 `eqcov` 에는 빠져 있다.** RRF 네 번째 항으로 넣어
A 를 해치지 않는지 확인한다. 구현은 이미 `tier_rank.sig_hyp_match` 에 있다.

---

## ④ 다중 lemma 다양성 재랭킹

**증상**: TEST R@50 54.6% vs ALL@50 45.4% — **9.2pp 를 다중 lemma 스텝에서 잃는다.**
lemma 2개 이상 필요한 스텝이 23.7% 이므로, 그중 약 40% 가 부분적으로만 잡힌다.

**원인 가설**: 한 번 정렬해 상위 k 를 자르면, 두 lemma 의 성격이 다를 때
(하나는 rewrite 용 등식, 하나는 apply 용 함의) 비슷한 것들이 상위를 채워 두 번째가 밀린다.

**아이디어**: MMR — 하나 고르면 그와 **너무 비슷한 것을 감점**한다. 유사도는 결론 head
다중집합 코사인을 재활용한다(이미 계산돼 있다).

---

## ⑤ 부분항별 다중 질의

`rewrite L` 은 L 이 goal 의 **부분항**에 맞는다. 지금은 결론 **전체**로 한 번만 질의한다.

**아이디어**: goal 결론의 부분항마다 질의를 만들어 RRF 로 합친다.
`src/tactic_gen/search_query.py` 에 추상화 사다리(depth 3→2→4→1)를 만들어뒀는데
**아직 쓰지 않고 있다.**

주의: 질의가 늘면 비용이 선형으로 늘고, 흔한 부분항(`nat`, `true`)은 노이즈만 만든다
→ IDF 가 낮은 부분항은 건너뛴다.

---

## ⑥ Definition 특별 처리

gold 가 `Definition` 이면 "결론" 이 명제가 아니라 **본문**이라 C'·eq 가 무의미하다.

```
gold   Definition ulp x := match Req_bool x 0 with | true => … end.
질의   match Req_bool x 0 with …          ← 명제가 아니다
```

`unfold`·`rewrite` 로 정의를 쓰는 경우다. **정의된 이름이 goal 에 나타나는가**로 잡아야
한다. 먼저 gold 중 Definition 비중을 재고(`headroom.py` ⑤), 크면 별도 신호를 만든다.

---

## ⑦ 증명 동시출현 사전확률

"이 goal 의 상수를 쓰는 **이전 증명들**이 자주 쓴 lemma" — 학습 없이 **카운트만**으로
만드는 사전확률. rango 에 proof retrieval 이 이미 있어 재료가 있다.

지역성 신호 H 가 단독으로는 약했지만(R@50 26.6%) RRF 에 넣으니 **이름 신호를 대체**했다
(§10.5b). 이것도 단독으로는 약해도 조합에서 값이 있을 수 있다.

**주의**: 같은 파일·프로젝트 안에서만 세야 한다. 전역 통계는 프로젝트 전이를 깬다.

---

## ⑧ contrastive 재시도 — 우선순위 낮음

### 지금까지의 결과

**분모: gold 가 후보 풀에 있는 TEST 스텝 40건 (예비)**

| 랭커 | 목표지표 ALL@50 |
|---|---|
| rrf / eq | **95.0%** |
| ctr (RRF 융합) | 91.8% |

**RRF 에 얹어도 아무것도 더하지 못한다.** 학습 당시 지표는 좋아 보였다 —

```
epoch 13: 재랭킹 top1 7.0% top5 21.6% top10 36.9%
          (tfidf 원본  3.1%      11.2%      17.0%)
```

top10 이 두 배지만, **tfidf 는 이미 RRF 에 크게 뒤지는 약한 기준선**이었다.

### 왜 안 되나 — 진단

| 의심 | 근거 |
|---|---|
| 손실 정체 | 12~13 epoch 내내 2.89~2.90 |
| **정보 중복** | RRF 의 C' 도 구조 신호다. 익명 구조 n-gram(F)·anti-unification(G) 도 RRF 에 넣으면 개선 0 이었다 |
| 표현이 거칠다 | 57토큰 익명화가 깊은 중첩을 `max_len=192` 에서 자른다 |
| negative 가 쉽다 | hard negative 를 **tfidf 상위**에서 뽑았다 — 기준선이 RRF 인데 |

### 재시도한다면

1. **negative 를 RRF(또는 eqcov) 상위로** — 지금 기준선에서 뽑아야 진짜 hard 다
2. **`eq` 신호를 입력 특징으로 주입** — 트리 완전일치를 모델이 직접 보게
3. 손실 정체 해소 — 학습률 스케줄, 층/차원 확대, `max_len` 확대
4. **큰 표본으로 전이 재측정** — 지금 40건은 결론을 내기에 부족하다

### 다만

`eqcov` 가 **학습 없이** 목표지표 95%대를 낸다. contrastive 가 이기려면 그보다 나아야
하는데, 위 진단대로면 **정보가 중복**이라 크게 기대하기 어렵다.
①~④ 를 먼저 하고, 그래도 남는 손실이 구조적이면 그때 돌아온다.

---

## ⑨ `NORMALIZE_RATE` — 근거 없이 0.5 다

### 지금 상태

`normalize_names.should_normalize` 의 주석이 근거다.

> 전부 정규화하면 테스트(실제 이름)와 분포가 어긋난다. 섞어야 모델이 메커니즘을 배우고
> 실제 이름에도 적용한다.

**그런데 ablation 이 없다.** 0.5 를 고른 측정 근거가 문서 어디에도 없다.

### 양쪽 논리

| rate | 근거 |
|---|---|
| 낮게 (0.5) | 추론은 진짜 이름이므로 분포를 맞춘다. 진짜 이름에는 **의미 힌트**가 있다(`add_comm` → 교환법칙) |
| 높게 (1.0) | 절반이 진짜 이름이면 모델은 **그 절반에서 여전히 외울 수 있다**. 암기 경로가 남으면 읽는 능력을 안 기른다 |

### 왜 높여도 될 가능성이 있나

정규화는 **일관된 개명**이다 — 프롬프트와 정답에 같은 매핑을 쓴다. 실측(익명화 손실 검사,
TRAIN 400건)에서 읽기 가능성이 **소수점까지 동일**했다.

| | 익명화 OFF | 익명화 ON |
|---|---|---|
| 정답 식별자가 프롬프트에 있음 | 80.8% | **80.8%** |
| 어디에도 없음(환각) | 7.7% | **7.7%** |

즉 모델이 배우는 것은 "프롬프트에서 이름을 찾아 베껴라"이고, 그 능력은 이름이 `L0` 든
`Nat.add_comm` 든 그대로 전이된다. 분포 불일치 우려는 **표면 형태**에 대한 것이지
능력에 대한 것이 아닐 수 있다.

### 어떻게 잴 것인가

`NORMALIZE_RATE` 0.5 / 0.8 / 1.0 으로 각각 학습해 rand200 성공률 비교.

★ **순서 주의**: cut 을 먼저 넣어야 한다. cut 이 들어가면 "프롬프트에 없는 이름을 쓰는
15.2%" 가 줄어들어 **정규화의 부작용 자체가 달라진다.** cut 없는 상태에서 rate 를 재면
그 결과가 cut 도입 후에 뒤집힐 수 있다.

---

## ⑩ 추론에서 정규화를 켜려면 **역매핑이 필요하다** (지금 없다)

| 경로 | 정규화 |
|---|---|
| 학습 `collate` | ✅ 적용 (rate 만큼) |
| 추론 `collate_input` | ❌ **안 함** |
| 역매핑 코드 | ❌ **없음** |

지금은 추론에서 정규화를 안 하므로 되돌릴 것이 없다 — 모델이 진짜 이름을 보고 진짜
이름을 생성하고 Coq 이 그대로 실행한다.

**★ 위험**: 학습과 형태를 맞추려고 추론 정규화를 켜면, 모델이 `apply L0.` 를 생성하고
Coq 은 `L0` 를 모른다. 켜기 전에 **반드시 역매핑을 구현**해야 한다
(`mapping` 을 저장해 두고 생성된 tactic 에 역방향 치환).

---

## ⑪ ★ built-in(stdlib)은 익명화도 [TYPES] 주입도 하지 말 것 — **구현 예정**

### 왜

익명화의 목적은 "**그 프로젝트에만 통하는 이름**을 외워서 찍는 습관"을 끊는 것이다.

| lemma | 외우면 | 익명화하면 |
|---|---|---|
| `gpaco5_unfold` (프로젝트 전용) | 그 프로젝트에만 통함 | **이득** — 끊는 게 맞다 |
| `Nat.add_comm` (stdlib) | **어느 프로젝트에서나 통함 = 진짜 지식** | **손해** |

사전학습 모델은 이미 `Nat.add_comm : forall n m, n+m = m+n` 을 안다.
`L0` 으로 바꾸면 **그 지식을 못 쓰게 막는 셈**이다.

`[TYPES]` 주입도 마찬가지다. `Inductive list A := nil | cons` 를 프롬프트에 넣는 것은
토큰 낭비다 — 모델이 이미 안다. 그 토큰으로 premise 를 더 넣는 편이 낫다.

### 지금 코드는 어떻게 되어 있나

`normalize_names.renameable()` 에 **원칙은 이미 있다**.

```python
def renameable(name):
    if name in _PROTECTED: return False          # nat, bool, list, S, O, nil, cons ...
    slot = _index().get(name)
    return any(k != "stdlib" for k in slot)      # ★ stdlib 전용 이름은 제외
```

**그런데 premise lemma 이름에는 이 검사가 안 걸린다.**

```python
# build_mapping 안
# ★ renameable() 을 쓰면 안 된다 — 정의 인덱스(func_defs)에 있는 이름만 허용하는데
#   premise 는 lemma 라 인덱스에 없다(실측 235건 중 134건이 걸려 치환 0).
if pn not in _PROTECTED and pn not in _HEADERS and len(pn) > 1:
    prem_names.append(pn)
```

`_PROTECTED` 에는 `nat`·`S`·`nil` 같은 **타입·생성자**만 있고 `Nat.add_comm`·`app_assoc`
같은 **lemma 이름**은 없다 → **stdlib lemma 도 `L0` 이 된다.**

### 어떻게 고치나

premise 는 `Sentence` 객체라 **출처 파일 경로**를 안다. 이름 인덱스가 아니라 **경로로**
판정하면 위 문제가 없다.

```python
_STD_PATH = re.compile(r"(coq/theories|/stdlib/|/Coq/|theories/(Init|Lists|Arith|ZArith|"
                       r"NArith|Bool|Logic|Reals|QArith|Sets|Relations|Classes|Numbers|"
                       r"Strings|Sorting|Structures|Program|Wellfounded|FSets|MSets)/)", re.I)

def is_stdlib(premise) -> bool:
    return bool(_STD_PATH.search(getattr(premise, "file_path", "") or ""))
```

  1. `build_mapping(premises=...)` 이 `Sentence` 를 받아 `is_stdlib` 인 것은 `prem_names`
     에서 제외 (지금은 텍스트만 받아 경로를 모른다 — 시그니처 변경 필요)
  2. `augment.selective_types` 가 stdlib 타입을 `[TYPES]` 에서 제외
  3. 환경변수로 켜고 끌 수 있게: `NORMALIZE_SKIP_STDLIB=1` · `INJECT_SKIP_STDLIB=1`

### 기대 효과

  · stdlib gold 는 이름이 살아남아 **사전학습 지식을 쓸 수 있다**
  · `[TYPES]` 에서 stdlib 타입이 빠져 **토큰이 절약**된다 → premise 를 더 넣는다
  · 프로젝트 전용 이름은 그대로 익명화 → 암기 차단 목적은 유지

### 측정

`scripts/stdlib_share.py` — 후보 풀·gold 중 stdlib 비중.
비중이 크면 효과가 크고, 작아도 **해가 없는 변경**이다(진짜 지식을 막지 않는 것뿐).

---

## 측정 도구

| 스크립트 | 재는 것 |
|---|---|
| `scripts/headroom.py` | 파서 recall · stage1 상한 · head 인덱스 여지 · 다중 lemma · gold 종류 |
| `scripts/exp_abcd.py` | A/C/D + 목표지표 (랭커 여러 종을 한 번에) |
| `scripts/hunt_assert_errors.py` | B — assert 생성 · suffix · 필터 정확도 |
| `scripts/why_not_top1.py` | 왜 1위가 아닌가 (사례별 원인 분류) |
