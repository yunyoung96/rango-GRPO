# 구현 디테일 — 정규화와 cut 이 실제로 어떻게 도는가

> `how-to-learn.txt` 의 방식이 코드에서 **정확히 어느 지점에, 어떤 순서로** 도는지 적는다.

---

## 0. 용어

| 용어 | 뜻 |
|---|---|
| **collate** | 학습 예제 하나를 **(프롬프트 + 정답)** 한 문자열로 조립하는 함수. `src/tactic_gen/tactic_data.py` |
| **collate_input** | 그중 **프롬프트만** 만드는 함수. 추론에서도 이것만 쓴다(정답이 없으므로) |
| **정규화(익명화)** | 프롬프트의 lemma·정의 이름을 `L0` `T0` `f0` `C0` `G0` 로 바꾸는 것 |
| **매핑** | `{원래이름: 새이름}` 사전. 예 `{"Nat.add_comm": "L0"}` |
| **cut** | 보조 명제를 세워 쓰는 것. Coq 에서는 `assert (P) as H`. 논리학의 cut rule |
| **gold tactic / gold lemma** | 데이터셋의 정답 tactic / 그 tactic 이 참조하는 lemma |

---

## 1. ★ 정규화는 **미리 만든 데이터가 아니다** — 학습 중 즉석에서 한다

질문: *"이미 있는 데이터를 정규화하는 건가, 아니면 학습 전에 정규화한 새 데이터로 학습하는 건가?"*

**전자다. 원본 데이터는 그대로 두고, 예제를 꺼낼 때마다 `collate` 안에서 정규화한다.**

```
data_points (원본, 정규화 안 됨)
     ↓  ds.raw_example(i)
LmExample (원본 이름 그대로)
     ↓  collate()          ← ★ 여기서 매번 정규화
"프롬프트(L0…) + 정답(L0…)"
     ↓
토크나이저 → 학습
```

### 1-1. 그래서 생기는 성질

| | 내용 |
|---|---|
| **결정적** | `should_normalize(key)` 가 `md5(파일:증명:스텝)` 해시로 정한다 → **같은 예제는 항상 같은 결정**. epoch 이 바뀌어도 안 흔들린다 |
| **매핑은 매번 재계산** | 결정은 고정이지만 매핑 자체는 그때그때 만든다. 입력이 같으면 결과도 같다(결정적 순서: 등장순) |
| **디스크 비용 0** | 정규화본을 따로 저장하지 않는다 |
| **CPU 비용 있음** | 예제마다 `build_mapping` + `apply_mapping`. 프롬프트가 8KB 라 작지 않다 |

### 1-2. `NORMALIZE_RATE`

`0.5` 면 **예제의 절반만** 정규화한다(해시로 결정). 근거는 코드 주석뿐이고 ablation 이 없다
— [future-idea.md](future-idea.md) ⑨ 참조.

---

## 2. `collate` 안의 순서 — 이 순서가 중요하다

```python
def collate(tokenizer, example):
    target = example.next_steps[0]                    # 정답 tactic (원본)

    # ①  프롬프트 조립 — [PREMISES] [PROOFS] [STATE] [SCRIPT] [TYPES] [DEFINITIONS]
    input_str = self.collate_input(tokenizer, example)

    # ①-b ★ cut 치환   (CUTS_PATH 가 있을 때)
    if cut := cut_lookup.cut_for(key):
        target = cut

    # ②  CITE_TARGET (지금은 꺼짐)

    # ③ ★ 정규화 — 프롬프트와 정답에 **같은 매핑**을 적용
    if 정규화 대상이면:
        mapping = build_mapping(...)
        input_str = apply_mapping(input_str, mapping)
        target    = apply_mapping(target,   mapping)

    return input_str + target
```

### 2-1. 왜 cut 이 정규화보다 **먼저**인가

cut 문장은 원본 이름으로 만들어져 있다(`exact Nat.add_comm`). 정규화 **후**에 끼워 넣으면
프롬프트는 `L0` 인데 cut 은 `Nat.add_comm` 이라 **서로 다른 이름**이 된다.
먼저 끼워 넣어야 둘 다 같이 `L0` 로 바뀐다.

### 2-2. 왜 프롬프트와 정답에 **같은 매핑**인가

같은 매핑이면 "프롬프트에서 읽을 수 있던 것"은 정규화 후에도 읽을 수 있다.
실측(TRAIN 400건)이 이를 확인한다 — 읽기 가능성이 **소수점까지 동일**하다.

| | 익명화 OFF | 익명화 ON |
|---|---|---|
| 정답 식별자가 프롬프트에 있음 | 80.8% | **80.8%** |
| tactic 키워드 | 10.7% | 10.7% |
| Coq 기본어휘 | 0.8% | 0.8% |
| **어디에도 없음(환각)** | **7.7%** | **7.7%** |

**즉 익명화가 환각을 만드는 것이 아니다.** 원래 있던 문제(예제의 15.2% 가 프롬프트에 없는
이름을 쓴다)를 **드러낸** 것이다. 익명화 전에는 이름을 외워서 맞힐 수 있었을 뿐이다.

---

## 3. cut 은 **미리 만들어 조회만** 한다

### 3-1. 왜

cut 의 명제를 정확히 얻으려면 그 증명 지점에서 Coq 에 `Check (L a b).` 를 물어야 한다
(암묵인자·Section 변수가 인스턴스화된다). 학습 머신(Vast.ai)에는 Coq 도, 원본 `.v` 13G 도
없다. → **데이터 준비 머신에서 만들어 jsonl 로 넘긴다.**

### 3-2. 파일 형식

```jsonl
{"kind":"stmt", "name":"Nat.add_comm", "ty":"forall n m : nat, n + m = m + n"}
{"kind":"step", "sid":"repos/a/b.v:12:3", "miss":["Nat.add_comm"],
                "cut":"assert (forall n m, n+m=m+n) as H_asrt0. { exact Nat.add_comm. }\nrewrite H_asrt0."}
{"kind":"step", "sid":"repos/c/d.v:7:1", "hopeless":true, "why":"gold 가 풀에 없음"}
```

같은 lemma 는 명제가 같으므로 **`name → 명제` 사전 하나 + 스텝별 목록**으로 정규화한다.
실측 TRAIN: cut 168,000개 · 파일 약 28MB (`data_points` 6.6G 대비 0.4%).

★ **키는 `file_name:proof_idx:step_idx`** 다. `collate` 가 계산할 수 있는 형태여야 한다
(`sid.file` 은 평탄화된 이름이라 다르다 — 여기서 한 번 틀렸다).

★ **원자적 쓰기**: 임시 이름(`.building`)에 쓰고 끝나면 `os.replace`. 그러지 않으면
생성 중인 반쪽 파일을 학습이 읽는다(실제로 당했다).

### 3-3. 3단계 판정 (how-to-learn.txt §3)

| 단계 | 조건 | 학습 target | 정규화 |
|---|---|---|---|
| **(1)** | gold lemma 가 검색 상위에 있다 | **gold tactic 그대로** | 평소대로(rate 만큼) |
| **(2)** | 없지만 cut 을 만들었고, 그 L' 로 재검색하니 L 이 잡힌다 | **cut 으로 치환** | 평소대로 |
| **(3)** | cut 을 만들어도 L 이 안 잡힌다 / gold 가 풀에 아예 없다 | gold tactic 그대로 (환각 감수) | **★ 끈다** |

**(3) 에서 정규화를 끄는 이유**: 정답이 프롬프트에 없는 이름을 쓰는데 정규화까지 하면
`L92` 같은 **무의미 토큰을 외우게** 된다. 진짜 이름(`add_comm`)은 최소한 의미 힌트가 있어
goal 모양에서 유추할 여지라도 있다. `cut_lookup.is_hopeless(sid)` 로 판정한다.

### 3-4. 실측 — **전체 TRAIN** (gold lemma 사용 14,292 스텝)

| 단계 | 건수 |
|---|---|
| (1) 검색 성공 → gold 그대로 | 4,973 |
| (2) cut 유효 → 치환 | **5,278** |
| (3) 가망 없음 → gold + 정규화 끔 | 3,852 |
| gold 가 후보 풀에 아예 없음 | 2,591 |

cut 파일: `data/cuts_train.jsonl` · 3.0 MB · 스텝 9,318 · 고유 명제 3,634.

**cut 조립 성공률은 시도분 대비 98.0%** 다. 실패 이유:

| 건수 | 이유 |
|---|---|
| 150 | 재검색 실패 — L' 로도 L 이 안 잡힘 |
| 116 | statement 추출 실패 (정의에 본문이 있음) |
| 7 | L' 명제 자체를 못 만듦 |

### 3-5. ★ cut 품질 게이트 — 자르지 말고 버린다

예전 `build_cuts.py` 는 `cut_tac[:800]` 으로 **잘랐다**. 잘린 `assert` 는 Coq 문법이
깨지므로 모델이 **깨진 문자열을 외운다**. 아래를 하나라도 어기면 cut 을 버리고
(3) hopeless 로 강등한다.

| 검사 | 왜 |
|---|---|
| `assert (` / `eassert (` 로 시작 | 형태 |
| `as H_asrt<n>.` 이름표 존재 | 없으면 문장이 잘린 것 |
| `{` `}` 증명 블록 존재 | 없으면 잘린 것 |
| 괄호 개수 균형 | 없으면 잘린 것 |
| **≤ 128 토큰** | conf 의 `out_tokens`. 넘으면 **collator 가 라벨을 잘라 깨뜨린다** |

실측 강등 **188 / 5,466 = 3.4%** — 그중 183건이 128토큰 초과, 5건이 잘림.

---

## 4. cut 문장의 형태 — 왜 bullet 이 아니라 중괄호인가

`how-to-learn.txt` §4 는 bullet(`-`)을 쓰라고 하지만 **bullet 은 원리적으로 안 된다.**

```coq
split.
- assert (P) as H.     ← 바깥 bullet 이 아직 열려 있는데
- exact L.             ← [Focus] Wrong bullet -: Current bullet - is not finished
```

증명 스크립트만 봐서는 `-` 가 아직 열려 있는지 알 수 없다. 그래서 중괄호를 쓴다.

```coq
assert (forall n, n <= n) as H_asrt0. { exact L. }
apply H_asrt0.
```

`{ }` 는 나란히 놓으면 되고 **바깥 bullet 과 절대 충돌하지 않는다.** 의미는 같다 —
첫 subgoal(P 증명)을 `{ exact L. }` 로 닫고 원래 goal 을 `apply H_asrt0` 로 처리한다.

---

## 5. 이름 충돌 방지 (how-to-learn.txt §4)

이름 할당은 `src/tactic_gen/name_alloc.py` **한 곳**으로 통합했다. 동작 차이는 플래그로만 준다.

| 플래그 | 하는 일 | 정규화 | cut |
|---|---|---|---|
| `scan_family` | 후보로 **시작하는** 이름도 충돌로 봄 (`H_asrt0` vs `H_asrt01`) | ✗ | ✅ |
| `scan_text` | 집합뿐 아니라 **원문을 단어 단위로** 직접 대조 | ✗ | ✅ |
| `avoid_family` | 기저가 어떤 식별자의 접두사도 안 되게 | ✗ | ✅ |

정규화는 가볍게(프롬프트 8KB 를 매번 훑으면 비싸다), cut 은 빡세게(틀리면 증명이 조용히
오염된다).

★ **Coq 자동 개명 함정**: Coq 은 `intros` 때 이름이 이미 쓰이면 숫자를 붙여 개명한다.
전역에 `H_asrt0` 이 있으면 `forall H_asrt0` 을 intro 할 때 **`H_asrt1` 이 생긴다** —
프롬프트 어디에도 안 나오므로 텍스트 대조로 못 잡는다. 그래서 기저 이름 자체를
`H_asrta` 로 바꿔 **가족을 분리**한다.

**실측: 이름 침범 0건** (TEST/VAL/TRAIN 각 250건).

---

## 6. 추론에서의 정규화와 **역매핑**

| 경로 | 정규화 | 환경변수 |
|---|---|---|
| 학습 `collate` | 프롬프트 + 정답에 **같은 매핑** | `NORMALIZE_NAMES=1 NORMALIZE_RATE=r` |
| 추론 `collate_input` | 프롬프트만 (정답이 없다) | `NORMALIZE_INFERENCE=1` |

**추론 정규화를 켜면 역매핑이 필수다.** 모델은 프롬프트에서 본 `L0` 를 그대로 생성하는데
Coq 은 `L0` 를 모른다.

```
프롬프트 정규화 → 모델 생성 `apply L0.` → ★ 역매핑 → `apply Nat.add_comm.` → Coq
```

구현:

| 함수 | 위치 |
|---|---|
| `_maybe_normalize_input(text, example)` | `tactic_data.py` — 프롬프트 정규화 + 매핑 보관 |
| `last_inference_mapping()` | `tactic_data.py` — 매핑을 꺼내는 창구 |
| `invert(mapping)` / `apply_inverse(text, mapping)` | `normalize_names.py` |
| 생성 직후 역매핑 | `model_wrapper.py` `get_recs` |

★ **매핑에 없는 이름은 그대로 둔다.** 모델이 지어낸 `L99` 는 Coq 에서 실패하는 것이 맞다
— 조용히 다른 이름으로 바꾸면 환각을 숨기게 된다.

★ 매핑은 **단사**다(`fresh` 가 이미 쓰인 이름을 건너뛴다) → 역이 잘 정의된다.

### 실험 조합

| 학습 | 추론 | 환경변수 |
|---|---|---|
| ✗ | ✗ | `NORMALIZE_NAMES=0` |
| 50% | ✗ (현재 기본) | `NORMALIZE_NAMES=1 NORMALIZE_RATE=0.5` |
| 100% | ✗ | `NORMALIZE_RATE=1.0` |
| 100% | ✅ | `NORMALIZE_RATE=1.0 NORMALIZE_INFERENCE=1` ← 분포 완전 일치 |

---

## 7. 알려진 미해결

| 문제 | 내용 |
|---|---|
| **잘린 premise 가 매핑에 남는다** | `build_mapping` 은 `example.premises` **전부**를 대상으로 하는데, 프롬프트는 `premise_tokens=896` 에서 잘린다. 잘려나간 premise 의 이름이 정답에 있으면 `L92` 가 프롬프트에 없는 상태가 된다. §3-3 의 (3) 처리로 일부만 막힌다 — 근본 수정은 **프롬프트에 살아남은 premise 만 매핑**하는 것 |
| `NORMALIZE_RATE` 근거 없음 | ablation 미실시 — [future-idea.md](future-idea.md) ⑨ |
| 학습 속도 | 모의학습 실측 **정상속도 38 s/step**(1 GPU · 워커 6, 워밍업 제외). 20,000 step 이면 **약 9일**. **CPU 12코어가 병목**이고 GPU 가 아니다 — 데이터 준비(검색·토크나이즈)가 지배한다. 첫 측정치 85 s/step 은 인덱스 로딩(238 MB)을 포함한 초반 구간이라 과대추정이었다 |

## 8. 검증 스크립트의 오탐 — 두 가지를 고쳤다

검증이 실패를 뱉는다고 해서 **코드가 틀린 것은 아니다.** 실제로 두 건 다 검사 쪽이 틀렸다.

| 검사 | 오탐 내용 | 고친 방법 |
|---|---|---|
| `preflight_all.py` **C. 라벨==정답** | 라벨을 **원본 gold** 와만 비교했다. cut 치환은 라벨을 **의도적으로** 바꾸므로 정상 동작이 실패로 잡혔다 (275/300 = 91.7%) | `CUTS_PATH` 가 있으면 기대값을 **cut** 으로 바꿔서 비교 |
| `verify_cut_collate.py` **hopeless 정규화** | 정규식 `\b[TfCLG]\d+\b` 로 판정해서 **원본 식별자** `f1` `T1` `C0` 를 정규화 산출물로 오인했다 (3건 전부 오탐) | 같은 예제를 `NORMALIZE_NAMES=0` 으로 한 번 더 만들어 **타깃이 동일한지**로 판정 |

> 교훈: "정규화되었는지"를 **결과 문자열의 생김새**로 추측하지 말고,
> **정규화를 끈 것과 비교**해서 판정한다. 생김새 판정은 원본에 우연히
> 같은 모양(`f1`, `T1`)이 있으면 반드시 틀린다.
