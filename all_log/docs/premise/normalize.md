# 이름 정규화 — rango 와 무엇이 다른가

> **목표**: 프롬프트를 **읽어야만** 풀 수 있게 만들어, 한 프로젝트에서 배운 모델이
> **미지의 프로젝트로 전이**되게 한다.
>
> rango 원본에는 이 장치가 **하나도 없다.** 아래는 전부 우리가 추가한 것이다.

관련: [final.md](final.md)(최종 스펙) · [repair.md](repair.md)(환각 제거) · [details.md](details.md)(구현)

---

## 0. 왜 필요한가 — ablation 이 말해준 것

정의를 **올바르게** 준 경우와 **틀리게** 준 경우를 비교했다.

```
clean(올바른 정의)  63/191 = 33.0%
wrong(틀린 정의)    66/194 = 34.0%
같은 정리 187개에서 차이 ±0 · McNemar p = 1.000
```

**올바른 정의를 줘도 틀린 정의를 줘도 결과가 같다 = 모델이 섹션을 안 읽는다.**

읽을 이유가 없기 때문이다. `destruct v as [|x|x|x|x|x x]` 는 학습 중 본
`val` 이라는 **이름에 대한 암기**로 낼 수 있다. 정의를 볼 필요가 없다.

### 0-1. 전이 관점에서 이게 왜 치명적인가

같은 이름이 프로젝트마다 **다른 명제**를 가리킨다. 실측 예:

```
rings.v          pow_succ_r : ∀ x y, x^(S y) = x^y * x
다른 프로젝트     pow_succ_r : 0<=b -> a^(S b) = a * a^b     ← 전제도 곱 순서도 다르다

Ranalysis3.v     Rplus_0_r  : forall n : R, n + 0 == n       ← setoid 등호
다른 프로젝트     Rplus_0_r  : r + 0 = r                      ← 보통 등호
```

**이름을 외운 모델은 프로젝트가 바뀌는 순간 틀린다.**
이름을 지우면 명제를 읽는 것 외에 방법이 없고, 그 능력은 이름과 무관하므로 전이된다.

---

## 1. 무엇을 어떻게 바꾸나 — 접두사가 종류를 알려준다

프로젝트 이름을 예제마다 **일관되게** 치환한다. 접두사로 **무엇인지**는 남긴다.

| 접두사 | 대상 | 예 |
|---|---|---|
| `T#` | 타입 (대문자로 시작하는 정의) | `val` → `T0` |
| `f#` | 함수 (소문자로 시작하는 정의) | `nds_ax` → `f0`, `osumf` → `f3` |
| `C#` | 생성자 | `Vundef` → `C0`, `Vint` → `C1` |
| `L#` | **`[PREMISES]` 의 lemma** | `gupaco5_mon` → `L91` |
| `G#` | **증명 중인 정리** | `my_thm` → `G0` |

> `L` 을 따로 둔 이유: 모델이 **"이건 인용할 수 있는 lemma 다"** 를 형태만으로 알게 한다.
> `G` 를 따로 둔 이유: **"증명 대상"과 "주어진 사실"** 을 구분해야 한다
> (증명 중인 정리 이름이 `[PREMISES]` 에도 있는 경우가 실측 1.3%).

### 1-1. α-치환이라 gold 가 그대로 gold 다

이름만 바꾸는 것은 **의미 보존**이다. 따라서 정답 tactic 이 여전히 정답이고
**Coq 재검증이 필요 없다.**

정의를 조작하는 counterfactual 과 결정적으로 다른 점이다 — 그쪽은 gold 를 다시 만들어야 한다.

---

## 2. 실제 예 — 학습 데이터 그대로

### 2-1. lemma 이름이 지워진다

```
파일: gpaco5.v (proof 20, step 32)

──── 정규화 OFF ────                    ──── 정규화 ON (학습) ────
[PREMISES]                              [PREMISES]
  Theorem paco2_fold:  …                  Theorem L83: …
  Theorem paco5_mon:   monotone5 …        Theorem L81: monotone5 …
  Corollary paco5_mult: …                 Corollary L77: …

[TACTIC]                                [TACTIC]
  assert (…) as H_asrt0.                  assert (…) as H_asrt0.
    { exact gupaco5_mon. }                  { exact L91. }
  eapply H_asrt0.                         eapply H_asrt0.
```

`paco5_mon` 을 외워서 "이름이 비슷하니 이거겠지"로 찍을 수 없다.
`L91` 을 고르려면 **명제를 읽어 goal 과 맞춰봐야 한다.**

### 2-2. 타입·함수도 지워지되 **goal 과 정답이 같은 기호**

```
파일: sset16b.v (proof 21, step 4)

──── 정규화 OFF ────                    ──── 정규화 ON ────
[STATE]                                 [STATE]
  ax: nds_ax X n                          ax: f0 X n

[TACTIC]                                [TACTIC]
  assert (forall n f, natp n ->            assert (forall n f, natp n ->
    ord_below f n -> ordinalp (osumf f n))   f2 f n -> ordinalp (f3 f n))
    as H_asrt0. { exact OS_osumf. }          as H_asrt0. { exact OS_osumf. }
```

**일관성이 핵심이다.** `nds_ax` 가 goal 에서 `f0` 이 되면 `[TYPES]`·`[DEFS]`·정답에서도
**전부 `f0`** 이다. 그래서 **조회 가능성은 유지**되면서 **이름 암기만 무력화**된다.

★ 검색·랭킹은 **정규화 이전**(원본 이름)에 돈다 — `collate_input` 에서 검색하고
`collate` 에서 정규화한다. 정규화가 랭킹을 바꾸지 않는다.

---

## 3. 안전장치 — 무엇을 **안** 바꾸나

| 대상 | 왜 |
|---|---|
| Coq 키워드 (`forall`, `match`, `fun`, `Type` …) | 문법이 깨진다 |
| tactic 이름 (`destruct`, `intros`, `auto` …) | 명령어다 |
| **stdlib 이름** (`nat`, `list`, `Z`, `S`, `cons` …) | 모델의 상식이고, 바꾸면 goal 자체가 이해 불가 |
| **프롬프트에 없는 이름** | 바꾸면 `L92` 같은 **프롬프트에 없는 무의미 토큰**을 외우게 된다 |

마지막 항목이 중요하다. 매핑 대상은 **실제로 주입·표시된 이름만**이다.

### 3-1. 이름 충돌 — 겹치면 다음 인덱스로

```python
alloc = NameAllocator.from_pattern(avoid_text, r"\b[TfCLG]\d+\b", extra=…)
def fresh(prefix, k):
    return alloc.alloc(prefix, start=k)   # 겹치면 건너뛴 첫 이름
```

프롬프트·정답·premise 에 이미 `T0` 이 있으면 `T1` 로 간다.
`assert` 가 만드는 `H_asrt#` 도 같은 원리로 기존 이름을 피한다
(게다가 Coq 이 `intros` 로 자동 생성하는 이름까지 피하도록 패밀리를 분리한다).

### 3-2. 순서는 **등장순**, 해시 아님

```python
# 결정적 순서(등장순) — 해시로 섞으면 예제마다 달라져 학습이 불안정
```

같은 예제를 두 번 만들면 **같은 매핑**이 나온다(`preflight_all` 의 재현성 검사 H).

---

## 4. rango 대비 차별점 — 목록

| # | 기능 | 환경변수 | rango | 우리 |
|---|---|---|---|---|
| ① | 타입·함수·생성자 정규화 | `NORMALIZE_NAMES` | ❌ | ✅ |
| ② | **premise lemma 이름 정규화** | `NORMALIZE_PREMISES` | ❌ | ✅ `L#` |
| ③ | **증명 중인 정리 분리** | `NORMALIZE_THEOREM` | ❌ | ✅ `G#` |
| ④ | **정규화 비율** | `NORMALIZE_RATE` | ❌ | ✅ **1.0** (§5) |
| ⑤ | **stdlib 제외** | `NORMALIZE_SKIP_STDLIB` | ❌ | ✅ |
| ⑥ | **타입 정의 주입** | `INJECT_TYPES` `TYPES_TOKENS` | ❌ | ✅ `[TYPES]` |
| ⑦ | **함수 정의 주입** | `INJECT_DEFS` `DEFS_TOKENS` | ❌ | ✅ `[DEFS]` |
| ⑧ | stdlib 정의는 주입 안 함 | `INJECT_SKIP_STDLIB` | ❌ | ✅ |
| ⑨ | **추론 시 정규화 + 역매핑** | `NORMALIZE_INFERENCE` | ❌ | ✅ (§6) |
| ⑩ | 생성자 개수·arity 사실 주입 | `TYPE_FACTS` | ❌ | 구현됨 · **끔** (§7) |
| ⑪ | 방해 premise 섞기 | `DISTRACTORS` | ❌ | 구현됨 · **끔** (§7) |
| ⑫ | 정의 ablation (clean/wrong) | `ABLATE_TYPES` `ABLATE_DEFS` | ❌ | 실험용 |

**⑥⑦이 ①과 짝이다.** 이름을 지우면 정의를 어디선가 읽어야 하는데, 그 자리가
`[TYPES]`·`[DEFS]` 다. 정규화만 하고 정의를 안 주면 **풀 수 없는 문제**가 된다.

```
[TYPES]   Inductive T0 := C0 | C1 : nat -> T0 | C2 : T0 -> T0 -> T0.
[DEFS]    Definition f0 (x : T0) : nat := …
[PREMISES] Lemma L0 : forall x, f0 (C1 x) = x.
[STATE]   goal: f0 (C1 n) = n
[TACTIC]  apply L0.        ← 전부 읽어야만 나온다
```

---

## 5. `NORMALIZE_RATE` — 0.5 에서 1.0 으로

| rate | 뜻 | 문제 |
|---|---|---|
| 0.5 (v8까지) | 예제의 **절반만** 정규화 | 나머지 절반에서 **여전히 암기 가능** |
| **1.0 (v9)** | **전부** 정규화 | 암기 경로가 완전히 차단 |

0.5 에는 근거가 없었다(`details.md §7` 에 "ablation 미실시"로 기록).
원래 의도는 "테스트는 실제 이름이므로 원본과 섞어야 실제 이름에도 적용된다" 였는데,
**추론에서도 정규화하면**(§6) 그 걱정이 사라진다.

### 5-1. 실현 가능성 (gold 400 step 실측)

```
goal 식별자 중 프로젝트 정의     중앙 8개 / 전체 12개
≥1개 치환 가능한 예제            378/400 = 94%
정답이 치환된 이름을 쓰는 예제     93/377 = 25%   ← 이 25%가 강한 압력을 받는다
```

---

## 6. 추론에서도 정규화 — 역매핑

전부 정규화해 학습하면 추론에서 원래 이름을 보는 것과 어긋난다. 그래서 추론도 정규화한다.

```
① 프롬프트 정규화        val → T0,  add_comm → L3        (매핑 M 을 기억)
② 모델 생성              apply L3.
③ ★ 역매핑               apply add_comm.                 (M⁻¹ 적용)
④ Coq 에 전달
```

구현: `normalize_names.invert()` · `apply_inverse()` ·
`model_wrapper` 의 생성 후 역매핑 · `tactic_data.last_inference_mapping()`.
환경변수 `NORMALIZE_INFERENCE=1`.

**이것이 `RATE=1.0` 의 전제다.** 평가 때 반드시 함께 켜야 한다.

---

## 7. 구현했지만 지금은 끈 것

### 7-1. `TYPE_FACTS` — 생성자 개수를 세어 준다

`[TYPES]` 의 `|` 를 모델이 직접 세는 대신 `"T0 has 3 constructors, arity 0/1/2"` 를 준다.

**끈 이유**: 프로브에서 3B 는 "소진 판단(M3)" 이 **100%** 였다. 세기를 대신해 줄 이유가
없다 — 1.3b 용 목발이었다.

### 7-2. `DISTRACTORS` — 방해 premise 섞기

`[PREMISES]` 에 **이름은 그럴듯한데 명제가 다른** lemma 를 k 개 섞는다.
이름으로 찍으면 틀리고 명제를 읽어야 맞는다.

**끈 이유**: v8 에서 "변수를 하나라도 줄여 **정규화 효과만 깨끗이** 보려고" 뺐다.
정규화 효과를 확인한 지금은 **되살릴 후보 1순위**다([future-idea.md](future-idea.md)).

---

## 8. 아직 답하지 못한 것 — 전이를 직접 재지 않았다

지금 지표는 전부 **검색 지표**(gold 가 프롬프트에 들어갔나)다.
**"읽어서 푸는 능력이 미지 프로젝트로 옮겨가나"는 한 번도 재지 않았다.**

```
평가 A: 학습에서 본 프로젝트의 held-out 파일    ← 프로젝트 내 일반화
평가 B: 학습에서 안 본 프로젝트                 ← 프로젝트 간 전이
전이 갭 = A − B          ← 이게 줄어드는 것이 목표 달성이다
```

정규화 ON/OFF 로 이 갭을 비교해야 **"정규화가 실제로 전이를 돕는가"** 에 처음 답할 수 있다.
지금은 CompCert 한 점만 있어 갭을 볼 수 없다.

**이것이 다음 우선순위 1번이다.**

---

## 9. 구현 위치

| 파일 | 역할 |
|---|---|
| `src/tactic_gen/normalize_names.py` | 매핑 생성·적용·역매핑·stdlib 판정 |
| `src/tactic_gen/name_alloc.py` | 충돌 없는 이름 할당(`NameAllocator`) |
| `src/tactic_gen/tactic_data.py` `collate` | 프롬프트+정답에 **같은 매핑** 적용 |
| `src/model_deployment/model_wrapper.py` | 생성 후 역매핑 |
| `scripts/check_anon_loss.py` | 정규화로 읽기 가능성이 떨어지는지 측정 |
