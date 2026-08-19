# Vast.ai 이관 — 무엇을 옮기고 무엇이 문제인가

> 학습은 Vast.ai 에서, **데이터 준비는 여기서** 한다. 이유는 §2.

---

## 0. 용어

| 용어 | 뜻 |
|---|---|
| **cut** | 증명에서 보조 명제를 세워 쓰는 것. Coq 에서는 `assert (P) as H`. 논리학의 cut rule 과 같다 |
| **gold tactic** | 데이터셋의 정답 tactic |
| **gold lemma** | 그 tactic 이 참조하는 lemma |
| **검색 실패** | gold lemma 가 프롬프트에 들어가는 상위 N 개 안에 없는 것 |
| **elaboration** | Coq 이 파일을 처음부터 실행해 타입을 확정하는 과정. 비싸다 |
| **collate** | 학습 예제 하나를 (입력 문자열 + 정답 문자열)로 조립하는 단계 |

---

## 1. 전송 목록

| 항목 | 크기 | 필수 | 비고 |
|---|---|---|---|
| `raw-data/coq-dataset/data_points` | **6.6G** | ✅ | 증명 데이터 |
| `raw-data/coq-dataset/sentences.db` | 211M | ✅ | premise 원문 |
| `data/func_defs_v3.json` | 12M | ✅ | 정의 주입 인덱스 |
| `data/ft6.7b-shuffled-index.json` | 작음 | ✅ | 예제 순서 |
| **`data/cuts_train.jsonl`** | **~28M** | ✅ | ★ 여기서 만들어 넘긴다 |
| 모델 가중치 (Qwen2.5-Coder-3B) | ~6G | ✅ | HF 캐시. `HF_HUB_OFFLINE=1` |
| 소스 코드 (`src/`, `scripts/`) | 작음 | ✅ | |
| `raw-data/coq-dataset/repos` | **13G** | ❌ | **cut 생성에만 필요 — 안 보낸다** |
| Coq / coq-lsp / opam | — | ❌ | **안 깐다** (§2) |

**합계 약 7G** (repos 13G 를 빼서 절반 이하).

---

## 2. ★ 왜 Coq 을 학습 머신에 안 두나

cut 의 명제를 정확히 얻으려면 **그 증명 지점에서** `Check (L a b).` 를 실행해야 한다.
암묵인자·Section 변수가 인스턴스화된 형태가 나오기 때문이다.

그런데 그러려면 학습 머신에 ⓐ Coq ⓑ opam 스위치 ⓒ 각 프로젝트가 빌드된 `.vo` ⓓ 원본
`.v` 13G 가 전부 있어야 한다. 프로젝트마다 의존 버전이 달라 재현이 느리고 불안정하다.

→ **cut 을 여기서 미리 만들어 `cuts_train.jsonl` 로 넘긴다.** 학습 때는 **조회만** 한다.

```
여기 (Coq 있음)                    Vast.ai (Coq 없음)
─────────────────────────          ─────────────────────────
검색 실패 스텝 탐색                   data_points + sentences.db
명제 확보 (① 원문 → ② Coq)           + cuts_train.jsonl  ← dict 조회
Coq 으로 검증                        + func_defs_v3.json
cuts_train.jsonl 저장                학습만 수행
```

---

## 3. cut 규모 (실측)

**분모: TRAIN 전체 2,009,606 스텝. 프롬프트 상위 100개 기준.**

| | 비율 | 건수 |
|---|---|---|
| gold lemma 사용 스텝 | 22.6% | 454,000 |
| ├ gold 가 풀에 없음 (cut 불가) | 3.9% | 78,000 |
| ├ 검색 성공 → cut 불필요 | 11.7% | 235,000 |
| └ **cut 필요** | **7.0%** | **141,000** |

**cut 총 168,000개 (스텝당 1.19개) · 파일 약 28MB**

스텝당 cut 개수 분포 — **85% 가 1개**다.

| cut 개수 | 스텝 |
|---|---|
| 1 | 238 (85.4%) |
| 2 | 35 |
| 3 | 3 |
| 4 | 3 |
| 5 | 1 (최대) |

cut 문장 길이는 **평균 50자 · 중앙 43자 · 최대 462자**. 같은 lemma 는 명제가 같으므로
**`name → 명제` 사전 + 스텝별 이름 목록**으로 정규화한다.

---

## 4. cut 생성 비용과 2단계 전략

Coq 을 스텝마다 부르면 **8~15초** 다. 141,000 스텝이면 단일 313시간 / 8병렬 39시간.

| 단계 | 방법 | 비용 |
|---|---|---|
| **①** | `sentences.db` 의 premise 원문에서 명제 추출 (`statement_of`) | **Coq 불필요, 즉시** |
| **②** | ① 이 실패한 것만 Coq `Check`. **파일 단위로 묶어** 한 번의 elaboration 으로 여러 지점 처리 | 파일당 평균 10 스텝 → 약 10배 절감 |

① 의 한계: 인스턴스화가 안 된 **일반형** 명제다. `Check` 는 `0 <= a` 를 주지만 원문은
`forall x, 0 <= x` 다. cut 으로 세울 때는 일반형도 유효하다(더 강한 명제를 세우고
`apply` 하면 된다) — 다만 `exact L` 로 바로 닫히는지는 검증이 필요하다.

---

## 5. 학습 명령 (Vast.ai)

```bash
HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONPATH=src \
AUGMENT_V2=1 RERANK_PREMISES=1 INJECT_TYPES=1 INJECT_DEFS=1 DYNAMIC_PADDING=1 \
HARD_SEQ_LEN=2048 TYPES_TOKENS=300 DEFS_TOKENS=300 \
FUNC_DEFS_PATH=data/func_defs_v3.json NORMALIZE_NAMES=1 NORMALIZE_RATE=0.5 \
STRIP_TARGET_NL=1 PYTORCH_ALLOC_CONF=expandable_segments:True \
CUTS_PATH=data/cuts_train.jsonl \
RETRIEVAL_MODE=structural RETRIEVAL_STAGE1=5000 \
  python3 -m torch.distributed.run --nproc_per_node=$NPROC \
    src/tactic_gen/train_v5.py <conf.yaml>
```

`conf.yaml` 의 `data_loc` · `sentence_db_loc` 를 Vast.ai 의 실제 경로로 바꾼다.

---

## 6. 이관 전 체크리스트

| 확인 | 방법 | 상태 |
|---|---|---|
| 모의 학습이 끝까지 도는가 | 30 step 로 `train_v5.py` | 진행중 |
| GPU 메모리 | 3B + seq 2048 + batch 4 → **26.7GB** | ✅ |
| step 속도 | 첫 step 492s(캐시 워밍) → 이후 **11~22s** | ✅ |
| 재랭킹이 학습 경로에서 도는가 | `RETRIEVAL_MODE=structural` | ✅ 통합됨 |
| cut 조회가 Coq 없이 되는가 | `CUTS_PATH` 만으로 collate | **미구현** |
| 오프라인 모델 로딩 | `HF_HUB_OFFLINE=1` + HF 캐시 동봉 | 확인 필요 |
| 디스크 | 7G(데이터) + 체크포인트 | 확인 필요 |

---

## 7. 주의

- **`repos` 를 안 보내므로 학습 머신에서는 cut 을 새로 만들 수 없다.** 데이터 준비를
  다시 해야 하면 여기서 하고 `cuts_*.jsonl` 만 다시 보낸다.
- **재랭킹이 학습 시간에 걸린다.** `structural_scores` 가 스텝당 ~140ms(stage1=5000).
  dataloader worker 8개면 가려지지만, 느리면 `RETRIEVAL_STAGE1` 를 낮춘다.
- 체크포인트는 Vast.ai 인스턴스가 사라지면 같이 사라진다. `keep_every` 로 남기고
  주기적으로 밖으로 복사한다.
