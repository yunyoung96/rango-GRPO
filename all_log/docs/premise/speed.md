# 학습 속도 — 왜 느렸고 무엇을 고쳤나

> **결론**: 우리가 rango 를 느리게 만든 게 아니다. 병목 코드는 한 줄도 안 건드렸다.
> 느려 **보인** 이유는 세 가지가 곱해진 것이다 —
> ① step 당 예제 8배 ② 코어 12개 ③ rango 원래 설계의 낭비.
> 그 ③을 고쳐 **의존 파일 로드를 132배** 빠르게 했고, **프롬프트는 바이트 단위로 동일**하다.

관련 문서: [repair.md](repair.md)(환각 제거) · [final.md](final.md)(최종 스펙)

---

## 0. 용어

| 용어 | 뜻 |
|---|---|
| **예제 (example)** | 학습 인스턴스 하나 = (프롬프트, 정답 tactic) 한 쌍. 증명의 **스텝 하나**가 예제 하나 |
| **step** | 옵티마이저가 한 번 갱신되는 단위. 여러 예제를 묶어서 처리한다 |
| **유효 배치** | `per_device_batch × grad_accum × GPU수`. step 당 예제 수 |
| **data_point** | 파일 하나를 전처리한 JSON. 평균 **470KB** |
| **`[PROOFS]`** | 프롬프트에 넣는 **유사 증명**. rango 방법의 핵심 축 |
| **의존 (dependency)** | 그 파일이 `Require` 하는 다른 파일. 유사 증명을 여기서도 가져온다 |

---

## 1. rango 는 예제 하나를 어떻게 만드나

**학습 중 예제마다 실시간으로 검색한다.** 미리 계산해 두지 않는다.

```
LmDataset.__getitem__(i)
 └─ raw_example(i)
     └─ formatter.example_from_step(...)
         ├─ SparseClient.get_premise_scores(...)          → [PREMISES]
         └─ SparseProofRetriever.get_similar_proofs(...)   → [PROOFS]
             └─ get_available_proofs(...)
                 └─ for dep in dp_obj.dependencies:        ← ★ 병목
                        dp_cache.get_dp(dep, ...)            의존 파일을 **전부** 로드
```

`[PROOFS]` 를 만들려면 후보 증명을 모아야 하고, 그러려면 **그 파일이 의존하는 모든
파일의 data_point** 를 읽어야 한다. data_point 하나가 평균 470KB JSON 이므로
의존이 100개면 예제 하나에 **47MB 파싱**이다.

### 1-1. `.v` 원본 없이 어떻게 되나 (자주 나오는 질문)

**data_point 만 있으면 된다.** 전처리 때 전부 뽑아 놨다.

```json
file_context[0] = {"file": "/coq-dataset/repos/choukh-MetaZF/HF/HF.v", …}  ← 문자열 식별자
file_context[1] = {"type": "stored", "id": 1}     ← sentences.db 참조
file_context[2] = {"type": "stored", "id": 2}
…                                                   (이 파일은 1,139개)
```

`sentences.db` 에 **582,037개 문장의 원문**이 들어 있다.

| 호출 | 무엇을 읽나 | `.v` 필요? |
|---|---|---|
| `available_premises` | `file_context` 의 id → `sentences.db` | ❌ |
| `dependencies` | premise 들의 `file_path` 에서 유도 | ❌ |
| `get_available_proofs` | 그 dependency **이름의 다른 data_point** | ❌ |

실측 — data_point 하나만 읽었을 때:

```
proofs                    2
in_file 가용 premise       3
out_of_file 가용 premise   2,522     ← 다른 파일 것도 이미 들어있다
dependencies              0
premise 예: Theorem reverse_reverse : forall (A : Type) (xs : list A), …
```

`repos/...` 경로는 파일처럼 보이지만 **열리지 않는 이름표**다. 학습 프로세스가 연 파일을
직접 확인해도 `sentences.db` 와 로그뿐이고 `repos` 경로는 0개다.

---

## 2. 증상 — 평균이 아니라 버스티

```
46/20000 [1:03:44<…,  63.27s/it]
47/20000 [1:07:47<…, 117.07s/it]   ← 4분
48/20000 [1:07:52<…,  83.61s/it]   ← 5초
```

**일부 예제가 통째로 막고 있었다.** GPU 사용률이 0%↔100% 를 오갔다 — 데이터가
안 만들어져 **GPU 가 굶고 있었다.**

| | 값 |
|---|---|
| GPU 연산 추정 | step 당 2~4초 |
| CPU 데이터 준비 | step 당 80초+ |

---

## 3. ★ 진짜 원인 — rango 원래 설계의 낭비

`get_available_proofs` 는 의존 파일에서 **`proofs` 만** 필요하다.
그런데 `DatasetFile.load` 는 기본값으로 **`avail_premises` 까지 전부 해석**한다 —
파일당 1,000개 넘는 문장을 `sentences.db` 에서 하나씩 꺼낸다.

**실측 (data_point 14개 평균)**

| | 로드 시간 | 얻는 proofs |
|---|---|---|
| `metadata_only=False` (기본) | **2.772초** | 24개 |
| `metadata_only=True` | **0.021초** | 24개 |

**132배. 그리고 얻는 게 똑같다.**

`metadata_only` 인자는 **rango 코드에 원래 있었는데** 이 경로에서 안 쓰이고 있었다.
반환된 `dep_obj` 에서 실제로 쓰이는 건 `dp_name` 하나뿐이고
(`empty_context_from_lines` 가 파일 경로를 보존한다), 켜도 아무것도 안 바뀐다.

### 3-1. 검증 — 내용이 정말 동일한가

속도만 얻고 방법이 훼손되면 최악이다. 같은 예제를 최적화 켠 채 / 끈 채로 만들어
**프롬프트 전체를 바이트 단위로 비교**했다.

```
■ 프롬프트 완전 일치 30/30 · 불일치 0
  ✓ 최적화가 내용을 바꾸지 않는다
```

스크립트: `scratchpad/verify_proofs_same.py` (원본 `DPCache.get_dp` 를 감싸 플래그를 강제)

---

## 4. 왜 rango 는 이걸로 안 죽었나 — step 당 예제 수

| | 원본 rango (`ft6.7b_conf.yaml`) | 우리 v9 |
|---|---|---|
| `per_device_train_batch_size` | **1** | **4** |
| `gradient_accumulation_steps` | 4 | 4 |
| GPU 수 | 1 | **2** |
| **step 당 예제** | **4** | **32** |
| `max_steps` | 20,000 | 20,000 |
| **총 학습 예제** | 80,000 | **640,000** |

**step 당 8배**다. 예제 하나 비용이 같아도 step 시간은 8배로 보인다.

원본이 `batch 1` 인 것은 **6.7B 모델 메모리 때문**이고(conf 주석: "6.7B라 배치 축소"),
우리는 3B 라 4까지 올릴 수 있어 유효배치 32 로 잡았다(v8 결정).

> **예제당 처리량은 우리가 더 낫다.** `max_steps` 가 고정이라 wall-clock 이 길어
> 보일 뿐, 같은 시간에 더 많은 데이터를 본다.

---

## 5. 이 머신의 제약 — 코어 12개

```
nproc → 12
```

이 학습은 **GPU 가 아니라 CPU 병목**이다. 2 GPU × 6 워커 = 12 워커가 12 코어를
나눠 쓴다. rango 논문 환경은 코어가 훨씬 많았을 것이다.

★ **Vast.ai 로 옮길 때 GPU 기준으로 고르면 손해다.** 4090 + 8 vCPU 인스턴스는
여기보다 **느리다**. `vCPU ≥ 32` 로 거르고, GPU 는 3B LoRA 라 **8GB 면 충분**하다
(실측 7.9GB). 자세한 것은 [vast-ai.md](vast-ai.md).

---

## 6. 우리가 추가한 것들의 비용 — 전부 합쳐 0.12초

| 항목 | v9 | 원본 | 비고 |
|---|---|---|---|
| `num_premises` | **100** | 50 | 랭킹 대상 2배 |
| `RETRIEVAL_MODE` | **structural** | tfidf | 구조 신호 계산 |
| `RETRIEVAL_STAGE1` | **5000** | — | 상위 5000 재랭킹 |
| `INJECT_TYPES` / `INJECT_DEFS` | 켬 | 끔 | 정의 주입 |
| `NORMALIZE_NAMES` | 켬 | 끔 | 이름 치환 |
| `CUT_DROP_HOPELESS` | 켬 | — | 제외분 재로드 ~5% |
| `num_proofs` | 12 | **20** | 오히려 **줄임** |

**이걸 전부 켠 채로 `proof_ret` 만 빼면 예제당 0.12초다.**
나머지 1.4초가 전부 `proof_ret` 의 의존 로드였다.

---

## 7. 실측 — 무엇이 효과가 있었나

**실제 학습을 40 step 씩 돌려 잰 값** (추정이 아니라 측정)

| 시도 | 결과 | 판정 |
|---|---|---|
| DP캐시 128 → **8192** (64배) | ~130 s/it → ~130 s/it | **효과 0** |
| `num_proofs` 12 → **4** | ~130 s/it → ~130 s/it | **효과 0** |
| `proof_ret` **제거** | ~130 → **5.16 s/it** | 25배 — 하지만 **방법 훼손** |
| **`metadata_only`** | 로드 132배 · 내용 동일 | ✅ **채택** |

> **교훈 ①** 느린 원인을 추측해 파라미터를 만지지 말고, 후보를 하나씩 **꺼서** 실제
> 학습으로 재라. 캐시 확대는 그럴듯했지만 0 이었다.
>
> **교훈 ②** `num_proofs` 는 *프롬프트에 몇 개 넣을지*만 정한다. 의존 로드는 그대로다.
> "개수를 줄이면 빨라지겠지"가 안 통하는 구조였다.
>
> **교훈 ③** `proof_ret` 제거는 25배로 가장 빨랐지만 **`[PROOFS]` 를 비운다.**
> 그건 rango 방법의 핵심 축이라 속도 선택지로 올려서는 안 되는 것이었다.
> 빠른 것이 아니라 **내용을 안 바꾸면서 빠른 것**을 찾아야 했다.

---

## 8. 곁들여 고친 것 — `DPCache`

속도 문제의 답은 아니었지만 구현 결함이라 고쳤다.

```python
# 전: list.index() + insert(0)   → 적중할 때마다 O(n). 캐시를 키울수록 느려진다.
# 후: OrderedDict.move_to_end()  → O(1). 크기는 DP_CACHE_SIZE 로 조절.
```

캐시 키에 `metadata_only` 플래그를 넣어 **섞이지 않게** 했다 —
metadata_only 로 담긴 객체를 premise 쪽이 받으면 premise 가 빈 채로 **조용히**
잘못 동작한다.

---

## 9. 최종 차이표 — 원본 rango 대비

| 항목 | 원본 rango | v9 | 성격 |
|---|---|---|---|
| `proof_retriever.py` | — | **동일** | 안 건드림 |
| 의존 파일 로드 | 전체 해석 | **`metadata_only`** | **순수 최적화** (내용 동일) |
| `DPCache` LRU | `list.index()` O(n) | `OrderedDict` O(1) | 순수 최적화 |
| `num_proofs` | 20 | 12 | v8 에서 축소 |
| `num_premises` | 50 | 100 | 기능 |
| 랭커 | tfidf | **structural** | 기능 |
| 담기 | greedy | **hybrid K=4** | 기능 |
| cut | 없음 | **있음** | 기능 |
| 가망없는 예제 | 학습에 포함 | **제외** | 기능 |
| step 당 예제 | 4 | 32 | 하드웨어 |

**`[PROOFS]` 는 원래대로 들어간다.**

---

## 10. 바뀐 파일

| 파일 | 변경 |
|---|---|
| `src/data_management/dataset_file.py` | `DPCache.get_dp(..., metadata_only=)` · `OrderedDict` LRU · `DP_CACHE_SIZE` |
| `src/proof_retrieval/proof_retriever.py` | `get_available_proofs` 의 의존 로드를 `metadata_only=True` 로 |

---

## 11. 남은 개선 여지

| 안 | 기대 | 비고 |
|---|---|---|
| 의존별 **proof 인덱스 사전생성** | 로드 자체를 없앰 | data_point 를 안 열고 조회만. 준비 비용 있음 |
| `dataloader_num_workers` 조정 | 소폭 | 코어 12개라 여유 없음 |
| 코어 많은 머신 | **선형** | 가장 확실 — CPU 병목이므로 |
