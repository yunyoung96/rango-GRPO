# DPO 설계 — SFT 다음에 무엇을, 왜, 어떤 순서로

> 근거는 전부 `checkpoint-12000` 의 CompCert rand200 부분 실행(26정리 · 생성 15,453개)
> 실측이다. 추측으로 정한 것은 그렇다고 적었다.

---

## 0. 이미 있는 것 — 다시 만들지 않는다

| 자산 | 역할 |
|---|---|
| `src/tactic_gen/dpo.py` | DPO 손실 코어 (β, 정책−레퍼런스 우위) |
| `src/tactic_gen/dpo_train.py` | LoRA DPO 학습 루프 |
| `scripts/build_divergence_dpo.py` | **divergence 쌍** 생성기 — gold 경로를 처음 벗어난 지점에서 `chosen=gold`, `rejected=정책의 VALID-but-off-path` |
| trl 0.28.0 · peft 0.18.1 | 설치돼 있음 |

`build_divergence_dpo.py` 의 주석은 negative 를 INVALID 가 아니라 **VALID-but-wrong** 으로
잡은 이유를 "우리 실패의 80%+ 유형"이라고 적어 두었다. **실측이 이를 확인한다 — 84.1%.**
즉 방향은 이미 맞다. 아래는 그 위에 얹는 설계다.

---

## 1. 무엇을 고쳐야 하는가 — 실패의 실제 구성

생성 15,453개 (26정리)

| 결과 | 건수 | 비중 |
|---|---|---|
| VALID (Coq 통과, 증명 안 끝남) | 13,000 | **84.1%** |
| INVALID | 2,447 | 15.8% |
| COMPLETE | 6 | 0.04% |

이름 인자를 쓰는 tactic 3,715개(전체의 24.0%) 중 INVALID 842 = **22.7%**
(일반 tactic 은 5.9% — **3.8배**). 그 842건의 내역:

| 종류 | 건수 | 비중 |
|---|---|---|
| 이름 자체가 없음(환각) | 311 | 36.9% |
| `rewrite` 대상 없음 | 274 | 32.5% |
| 암묵 인자·방향·`unfold` 대상 오류 등 | 155 | 18.4% |
| 패턴/분기 개수 | 43 | 5.1% |
| 적용 대상 아님 | 27 | 3.2% |
| 진전 없음·단일화 실패 | 32 | 3.8% |

→ **이름은 실재하는데 형태가 틀린 것이 약 60%.**

그리고 탐색 구조:

```
시도(attempt) 2,473회 · INVALID 2,447 → 시도당 0.99
도달 깊이 중앙 4
try_candidates = 1   ← 노드마다 후보를 딱 하나 뽑는다
```

**시도 하나가 잘못된 tactic 딱 하나로 죽는다.** 이것이 DPO 설계에 두 가지를 시사한다.
① 형태 실수 하나의 대가가 크므로, 절대량(생성의 3.3%)보다 레버리지가 크다.
② `try_candidates>1` 로 바꾸면 **노드마다 라벨된 후보가 n개** 생겨 선호쌍이 공짜로 나온다.

---

## 2. ★ 반드시 먼저 고칠 것 — 정규화 공간 불일치

`dpo_train.py:117`

```python
collate_fn = lambda ej: collator.collate_input(tokenizer, LmExample.from_json(ej))
```

`collate_input` 의 `normalize` 기본값이 `True` 다. 그래서

* 프롬프트는 `_L3`·`_T1` 로 **익명화**되고
* `chosen`/`rejected` 는 롤아웃 로그에서 온 **실명** tactic 이다

이 상태로 학습하면 "프롬프트엔 `_L3` 인데 정답은 `Nat.add_comm`" 을 강화한다.
SFT 는 정확히 그 반대로 학습됐다(프롬프트·정답에 **같은 매핑**). 그대로 두면
DPO 가 SFT 의 익명화 계약을 깨뜨린다.

**고침 — 쌍을 만들 때 프롬프트와 같은 매핑을 tactic 에도 건다:**

```python
prompt = collator.collate_input(tokenizer, ex, normalize=True)
m = last_inference_mapping()                 # 그 프롬프트가 쓴 매핑
chosen   = apply_mapping(chosen_raw,   m)    # 같은 공간으로
rejected = apply_mapping(rejected_raw, m)
```

`normalize=False` 로 도망가면 안 된다 — 그러면 DPO 프롬프트가 SFT·추론과 달라진다.
**세 경로(SFT·DPO·추론)가 전부 같은 공간이어야 한다.**

자기검사: 쌍을 만든 뒤 `chosen`·`rejected` 안의 모든 `_[TfCLGK]\d+` 이
그 프롬프트 안에 선언을 갖는지 확인한다. 안 그러면 그 쌍은 버린다.

---

## 3. 데이터 — 탐색 자체를 생성기로 쓴다

**핵심 착상**: `try_candidates = n` 으로 바꾸면 노드 하나에서 **같은 프롬프트**에 대해
n개의 후보가 나오고, Coq 이 각각을 무료로 채점한다. 선호쌍의 정의가 그대로다
(같은 x, 다른 y). 추가 Coq 비용은 노드당 1.00 → 1.19회뿐이다(첫 VALID 에서 끊기므로).

즉 **탐색 성능 개선과 DPO 데이터 수집이 같은 한 줄**이다.

### 수집 대상

**TRAIN split 프로젝트에서만 수집한다. CompCert 는 held-out 이므로 절대 쓰지 않는다.**
(rand200 이 평가셋이다 — 여기서 수집하면 평가가 무의미해진다.)

### 세 종류의 쌍

**Tier A — 형태 쌍 (form)**  ★ 새로 추가하는 축

같은 lemma 이름, 형태만 다르게. 정책이 실패한 형태를 rejected, Coq 이 받아준 형태를 chosen.

```
apply L        INVALID  (Unable to find an instance for x)
eapply L       VALID     ← chosen
rewrite L      INVALID  (Found no subterm matching)
rewrite <- L   VALID     ← chosen
apply L        INVALID  (Unable to apply lemma on hyp)
apply L in H   VALID     ← chosen
unfold f       INVALID  (f is opaque)
                          → chosen 없음. 이 쌍은 버린다
```

변형 집합(정책이 낸 이름 하나당):
`apply` / `eapply` / `apply … in H` / `eapply … in H` / `rewrite` / `rewrite <-` /
`erewrite` / `symmetry; apply` / `exact` — 9형태, 첫 VALID 에서 멈추므로 기대 3~4회.

겨누는 것: 이름-tactic INVALID 의 **약 60%**. 라벨이 **모호하지 않다**(Coq 이 정한다).

**Tier B — 경로 쌍 (divergence)**  이미 구현돼 있음

`build_divergence_dpo.py` 그대로. `chosen = gold`, `rejected = 정책의 VALID-but-off-path`.
겨누는 것: **84.1%** 의 VALID-무진전. 표적은 가장 크지만 **신용 할당이 시끄럽다** —
"경로를 벗어났다"가 곧 "그 수가 나쁘다"는 아니다(다른 경로로도 풀릴 수 있다).

**Tier C — 환각 쌍**  만들지 않는다

이름이 없는 311건은 형태 문제가 아니라 도달성 문제다. SFT 의 `DROP_HALLUC` 이
이미 학습 데이터에서 걷어내고 있고, DPO 로 "없는 이름을 쓰지 마라"를 가르치면
**모델이 이름 쓰기 자체를 회피**하게 될 위험이 있다(이미 이름 사용률이 24%뿐이다).

### 순서

**Tier A 먼저.** 라벨이 깨끗하고, 측정된 실패에 정확히 대응하며, 붕괴 위험이 낮다.
Tier A 가 효과를 보이면 그때 Tier B 를 섞는다(A:B = 1:1 부터).

---

## 4. 학습 설정

| 항목 | 값 | 근거 |
|---|---|---|
| 레퍼런스 모델 | SFT 어댑터를 **끈** 같은 모델 | LoRA 라 메모리 두 배 안 든다 (`disable_adapter()`) |
| β | 0.1 로 시작, 0.3 까지 스윕 | 데이터가 작을수록 크게 |
| 손실 | DPO + **chosen 에 SFT(NLL) 항** (λ≈0.1) | 순수 DPO 는 chosen 확률까지 같이 낮추며 드리프트한다 |
| 길이 정규화 | 켠다 | `eapply L` 이 `apply L` 보다 길다 → 길이 편향을 DPO 가 악용한다 |
| LoRA | SFT 어댑터에서 **이어서** (r=64, α=16) | 새 어댑터를 얹으면 SFT 형식을 잃는다 |
| lr | 5e-6 ~ 1e-5 | SFT(1e-4)보다 한 자릿수 낮게 |
| 에폭 | 1 | DPO 는 과적합이 빠르다 |

---

## 5. 붕괴 방지 — 무엇이 잘못될 수 있나

1. **"항상 `eapply`" 로 붕괴.** Tier A 는 `eapply` 가 chosen 인 쌍이 많다.
   → (형태쌍 종류)별로 쌍 수에 **상한**을 둔다. `eapply` 쌍이 전체의 30%를 넘지 않게.
2. **이름 회피.** DPO 가 "이름 쓰면 손해"를 배우면 일반 tactic 비중(이미 53.8%)이 더 는다.
   → 평가에 **이름-tactic 비율**을 지표로 넣는다. 24%보다 떨어지면 실패로 본다.
3. **길이 편향.** 위의 길이 정규화 + SFT 항.
4. **프롬프트 공간 오염.** §2. 자기검사를 CI 처럼 매 데이터 생성마다 돌린다.
5. **평가 누출.** TRAIN 에서만 수집. 수집 로그에 CompCert 경로가 하나라도 있으면 중단.

---

## 6. 평가 — 성공률 하나로 보지 않는다

지금 우리에겐 실패를 **분해**하는 계기가 있다. DPO 전후로 같이 본다.

| 지표 | 현재값 | DPO 가 맞다면 |
|---|---|---|
| rand200 성공률 (w2, 600s) | 23.1% (26정리 부분) | ↑ |
| 이름-tactic INVALID 비율 | 22.7% | **↓** (직접 표적) |
| └ 그중 형태 오류 | 60% | **↓↓** |
| 이름-tactic 사용 비율 | 24.0% | 유지 이상 (↓면 붕괴) |
| 전체 INVALID | 15.8% | ↓ |
| 시도당 도달 깊이 중앙 | 4 | ↑ |

**성공률만 보면 무엇이 좋아졌는지 알 수 없다.** 위 분해가 있어야 "형태를 배웠다"와
"그냥 안전한 tactic 만 친다"를 구분할 수 있다.

---

## 7. 그런데 순서상 DPO 가 먼저가 아니다

측정이 가리키는 우선순위는 이렇다.

1. **`try_candidates` 1 → 8** — Coq 비용 +19%, 한 줄. 시도가 INVALID 하나로 죽는 것을 없앤다.
2. **`ERROR_REPAIR=1`** — 이미 구현돼 있고 꺼져 있다. Tier A 가 학습으로 하려는 일을
   **추론에서 brute-force 로** 한다.
3. 1·2 로 얼마나 오르는지 본 **뒤에** DPO. 이유:
   * 1·2 는 학습 없이 **같은 가설을 검증**한다. 안 오르면 DPO 도 안 오른다.
   * 1 을 켜야 Tier A 데이터가 **공짜로** 나온다.
   * 2 의 변형 집합이 곧 Tier A 의 변형 집합이다 — 한 번 만들면 둘 다 쓴다.
4. 그다음 GRPO (기록상 SFT→GRPO 37.5% 가 최고).

즉 **DPO 는 3번**이고, 1·2 가 그 데이터 생성기이자 사전 검증이다.

---

## 부록 — 구현 순서 (파일 단위)

1. `run_thm.py get_searcher_conf` — `straight_line_conf` 에 `try_candidates=8`
2. `scripts/build_form_dpo.py` (신규) — 탐색 로그에서 Tier A 쌍 생성 + §2 자기검사
3. `src/tactic_gen/dpo_train.py` — `collate_fn` 에서 매핑을 tactic 에도 적용 (§2)
4. `src/model_deployment/error_repair.py` — 변형 집합을 §3 의 9형태로 맞춤
5. 평가 — `scripts/run_all.py --alias rango-v9` + §6 분해 지표
