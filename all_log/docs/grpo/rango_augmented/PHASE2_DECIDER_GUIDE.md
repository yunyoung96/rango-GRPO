# 2차 구현 가이드 — decider 주입 (저쪽 서버용)

작성 2026-08-02, **개정 2026-08-02(심층분석 후)**. 1차([TYPES]+재랭킹) 이후 decider.

## ⚠️⚠️ 개정 요지 (반드시 먼저) — [[DECIDER_DEEP_DIVE]]
심층분석 결과 **초기 이 가이드의 "decider 인덱스 조회+랭킹" 접근은 재설계됨**:
- **"커버 79%"는 주입에 못 씀** — 역방향 측정(gold 알 때)이었음. 정방향(goal만) 조회는 gold **1%**.
- decider 조회하면 goal당 **89개(노이즈)**. 랭킹+캡 해도 gold 3~5%. **무거운 인덱스+랭킹 = 과설계.**
- **compound destruct 완전분해**:
  | 부류 | 비율(gold) | 방법 | 프로젝트독립 |
  |---|---|---|---|
  | **A: goal 스캔** | **62%** | goal의 `if E`/`match E`에서 E 추출 → `destruct (E)` | ✅ **완전 독립** |
  | B1a: decider+인자타입 goal에 | 7% | 타입→sumbool 자동인덱스(AST) | ⚠️ 원리상 독립, 상한 7% |
  | B1b/B2 | 31% | 타입정보부족 / 도메인lemma | ❌ capacity·표현 |
- **★ 결론: decider의 주력은 "부류A = goal 스캔"(62%)이고, 이건 이미 `_targeted_cands`의 ②scrutinee가 구현함.**
  → **[DECIDERS] 전용 프롬프트 섹션·인덱스·랭킹은 낮은 우선순위(과설계).** 아래 §새권장 참조.

## ★ 새 권장 (심층분석 기반)
"decider 인덱스 조회" 대신:
1. **부류A(62%, 주력)** = goal의 `if`/`match` scrutinee 추출. **`_targeted_cands`(②)가 이미 함** — src/tactic_gen/grpo_rollout.py `_scrutinees()`/`_targeted_cands()`. **하드코딩 0, 프로젝트·split 독립(train64%≈test62%).**
2. **부류B1(7%, 선택)** = 타입→sumbool decider 자동인덱스(코퍼스 `{_}+{_}` 추출, AST면 정확). `_targeted_cands` ③ _DEC_* 테이블은 **CompCert 특정(전이 안 됨)** → 자동인덱스로 대체 시 프로젝트독립되나 이득 7%.
3. **부류B2(29%)** = 포기(capacity, 학습 담당).
→ **decider를 프롬프트 섹션으로 넣기보다, `_targeted_cands` 후보를 rollout에서 시도**하는 기존 방식이 대부분(부류A) 커버. 별도 인덱스 불필요.

## train/CompCert 공통성 (검증됨)
부류A 비율: gold train300 **64%** ≈ gold train5091 **62%** (거의 동일) → **train/test(CompCert 전체) 공통**. goal 스캔은 텍스트만이라 프로젝트-독립.
(단 모델 롤아웃은 37~40%로 낮음 — 모델이 goal에 없는 걸 더 시도. 학습목표=gold라 62%가 관련 수치.)

---

## [이하 원래 가이드 — decider를 굳이 프롬프트 섹션으로 넣을 경우만 참조. 위 권장이 우선]

## 0. 먼저 읽을 파일 (순서대로)
| 파일 | 왜 |
|---|---|
| **[DECIDER_DEEP_DIVE.md](DECIDER_DEEP_DIVE.md)** | **★ 최우선** — decider 완전분해(A62%/B1/B2), 프로젝트독립성, 왜 인덱스+랭킹이 과설계인지 |
| **[INDEX_VS_PROMPT.md](INDEX_VS_PROMPT.md)** | 인덱스(사전) vs 프롬프트 구분 |
| **[NOTATION_AND_COVERAGE.md](NOTATION_AND_COVERAGE.md)** §5b | 커버 측정(단 79%는 역방향 아티팩트 — DEEP_DIVE §0 정정) |
| [REVIEW.md](REVIEW.md) §R4 | decider 1차서 뺀 이유(노이즈) |
| `scripts/improve_decider_coverage.py` | 커버 측정 실측 코드 |
| `src/tactic_gen/grpo_rollout.py` `_targeted_cands`/`_scrutinees` | **★ 부류A 구현 이미 있음** — 재사용 |

**따라할 패턴(굳이 프롬프트 섹션 넣을 때) = 재랭킹**: `RERANK_PREMISES` 배선(L431, L512). `INJECT_DECIDERS=1` env 가드.

---

## 1. 핵심 사실 (최신, 검증됨)

### decider가 커버하는 대상 = compound destruct (`destruct (E)`)
- [TYPES]는 **단순변수 destruct**(`destruct v`, v:타입) 커버 → 87~100%.
- decider는 **compound destruct**(`destruct (decider ...)`) 커버 → 아래 레시피로 79%.
- **둘은 다른 대상**(겹치지 않음). "순증분" 아니라 별도 영역. (이전 "순증분 27%"는 오측정, 정정됨)

### 프롬프트 크기 = 안 터짐
- [DECIDERS] 주입: goal 연산당 1줄(`block: eq_block`), ≤5줄 = **~수십토큰**.
- notation-map은 **매칭 계산용**(0토큰, goal 안 건드림). Set Printing All(3~8배=터짐)과 다름.

---

## 2. decider 커버 79% 만드는 레시피 (누적, `improve_decider_coverage.py` 검증)
| 단계 | 커버 | 무엇 |
|---|---|---|
| baseline (인덱스 정확일치만) | 2% | ddr_index.json 조회 |
| +notation-map | 25% | 심볼→함수 (`^`→Zpower). coqstoq Notation 자동추출(178심볼) |
| +순서/삼분 decider | 32% | `Rle_or_lt`,`Zle_or_lt` (이름이 _dec/_spec 아님) — goal에 `<`/`Rle`면 후보 |
| +CompCert 소스인덱스 | 36% | `raw-data/coqstoq-test/repos/compcert/**/*.v` 스캔 decider |
| **★ +조회 base매칭** | **79%** | **최대레버(+43pp).** gold `destruct (reg_eq a b)` → `reg_eq` 정확매칭 실패해도 base(`reg`)가 goal에 있으면 인정 |
| +Mode1 union | 80% | goal 부분식 직접(decider 아닌 함수destruct) |

**★ 조회 base매칭이 핵심.** 코드는 `improve_decider_coverage.py`의 `measure(base_fix=True)` 로직 그대로:
```python
# gold head hs의 base(연산이름)가 goal에 있으면 인정 (오탐 검증됨: 실제 67% vs 가짜 0%)
base = re.sub(r'(_dec|eq_dec|_spec|_lt_dec|_le_dec)$', '', hs)
if base and re.search(r'\b'+re.escape(base)+r'\b', goal): ok = True
```
단 **주입(생성) 시엔 조회를 반대로**: goal 연산 head → 인덱스에서 그 head의 decider들을 뽑아 [DECIDERS] 줄 생성. (base매칭은 "커버 측정"용, 주입은 "goal head → decider" 정방향)

---

## 3. 구현 단계 (저쪽 서버)

### Step A — notation-map 인덱스 빌드 (신규 스크립트)
`scripts/build_notation_map.py` 작성 (로직은 `improve_decider_coverage.py` 상단 NMAP 빌드 그대로):
```python
# coqstoq Notation 선언 → 심볼→함수명 맵. + CompCert 소스 decider 확장.
# 출력: data/notation_map.json, data/ddr_index_expanded.json
```
- notation 파싱: `improve_decider_coverage.py`의 `_NOTA`/`NMAP` 블록.
- CompCert 확장: `build_cc_index()` 블록.
- ⚠️ **정규식 문장분할은 조잡**(decider 219개만). 여유되면 coqc/coq-lsp AST로 더 정확히.

### Step B — augment.py에 deciders() 추가 (canonical 로직)
`src/tactic_gen/augment.py`에 `selective_types` 옆에 추가:
```python
def deciders(goal, ddr_index, nota_map=None, order_dec=None, max_lines=5):
    """goal 결론의 연산/술어 head → decider 후보 줄. 노이즈방지: 결론부·키워드제외·자기매칭제외.
    반환 [(head, "block: eq_block"), ...]. train/infer 공유(RERANK처럼)."""
    concl = goal.split('\n\n',1)[1] if '\n\n' in goal else goal
    te, pd, os_ = ddr_index['type_eq'], ddr_index['pred_dec'], ddr_index['op_spec']
    heads = {i for i in re.findall(r"[A-Za-z_][\w'\.]*", concl)
             if not _bad_head(i)}            # _bad_head = 키워드·1글자 제외 (augment.py 기존)
    # notation 확장: goal 심볼 → 숨은 함수명도 head에 추가
    if nota_map:
        for sym, names in nota_map.items():
            if sym in goal: heads.update(names)
    out = []
    for h in heads:
        hs = h.split('.')[-1]
        for d in (os_.get(hs,[]) + pd.get(hs,[]) + te.get(hs,[]))[:1]:
            if d.split('.')[-1] != hs:       # 자기매칭 제외(노이즈)
                out.append((h, f"{h}: {d}"))
    return sorted(set(out))[:max_lines]
```
**★ 노이즈 필터 필수**(렌더링서 `forall: forall_dec`, `d: Equal_dec` 나왔음): `_bad_head`(키워드·1글자) + 결론부만 + 자기매칭 제외.

### Step C — collator 배선 (RERANK와 동일 패턴)
`src/tactic_gen/tactic_data.py` `ProofPremiseCollator.collate_input` (L428~451) 수정.
**정확한 위치**: `combined_str` 조립에서 `[STATE]` 앞에 `[TYPES]`/`[DECIDERS]` 삽입.
```python
def collate_input(self, tokenizer, example):
    proof_str = allocate_and_fmt(tokenizer, example.proofs, self.proof_tokens)
    _prem = example.premises
    if os.environ.get("RERANK_PREMISES","0") == "1":
        _prem = rerank_premises(example)
    premise_str = allocate_and_fmt(tokenizer, _prem, self.premise_tokens)
    state_str, _ = allocate_tokens(tokenizer, example.proof_state, self.state_tokens)
    script_str, _ = allocate_tokens(tokenizer, example.proof_script, self.script_tokens)
    # ★ 구조컨텍스트 (INJECT_TYPES / INJECT_DECIDERS). 독립예산 — premise 안 뺏음.
    struct = ""
    if os.environ.get("INJECT_TYPES","0") == "1":
        struct += _make_types_block(tokenizer, example)      # [TYPES]\n... (augment.selective_types)
    if os.environ.get("INJECT_DECIDERS","0") == "1":
        struct += _make_deciders_block(tokenizer, example)   # [DECIDERS]\n... (augment.deciders)
    combined_str = (
        self.PREMISE_SEP + premise_str
        + self.PROOF_SEP + proof_str
        + struct                          # ★ [STATE] 앞에 삽입
        + self.STATE_SEP + state_str
        + self.SCRIPT_SEP + script_str
        + NEWLINE_RESPONSE_TEMPLATE
    )
    return combined_str
```
- `_make_types_block`/`_make_deciders_block`: 인덱스 lazy-load(env `TYPES_INDEX`/`DDR_INDEX` 경로) + augment 호출 + `[TYPES]\n`/`[DECIDERS]\n` 헤더.
- **독립예산**: `TYPES_BUDGET`(≤200), decider는 ≤5줄. premise_tokens 건드리지 말 것.
- ⚠️ **3곳** collator에 premise 배선 있음(L428/L510 등) — **[TYPES]/[DECIDERS] 쓰는 건 ProofPremiseCollator만**이면 되지만, 학습·추론이 같은 collator 쓰는지 확인(training_conf.yaml `example_collator.alias: proof-premise`).

### Step D — 학습·추론 동일 env (R1 필수)
학습·롤아웃·평가 **전부** 같은 env로:
```bash
RERANK_PREMISES=1 INJECT_TYPES=1 INJECT_DECIDERS=1   # 셋 다, 학습·추론 동일
```
안 그러면 OOD(학습 프롬프트 ≠ 추론 프롬프트) → 성능 붕괴.

### Step E — 검증 (학습 전 CPU, 필수)
```bash
# 렌더링으로 [DECIDERS] 노이즈 확인 (forall:/d: 같은 잡음 없나)
python3 scripts/render_augmented_examples.py    # (decider 포함하게 확장)
# 커버 재현
python3 scripts/improve_decider_coverage.py     # 79% 나오나
```
노이즈 있으면 Step B 필터 강화 후 재확인. **비싼 학습 전에 반드시.**

---

## 4. 실험 설계 (2차 A/B)
- **통제군**: 1차 모델(재랭킹+[TYPES], INJECT_DECIDERS=0)
- **처리군**: +[DECIDERS] (INJECT_DECIDERS=1)
- 같은 split·학습·평가. decider 순효과 격리.
- 평가: (a) gold compound destruct top-1 (b) rand200 성공률.

## 5. 리스크 (반드시 체크)
| R | 리스크 | 대응 |
|---|---|---|
| R1 | 학습≠추론 env | 셋 env 양쪽 동일 |
| R2 | [DECIDERS] 노이즈(`forall:_dec`) | _bad_head + 결론부 + 자기매칭제외 (Step B). 렌더링 검증 |
| R3 | notation 없으면 decider 1% | notation-map 반드시(Step A). 안 하면 무의미 |
| R4 | 누수 | decider 인덱스가 test 정리 lemma 포함 가능 → premise_filter exclusion 적용(1차 [TYPES]는 인프라라 면제였으나 decider는 lemma라 주의) |
| R5 | 혼입 | 1차 효과 확인 후 2차. 재랭킹+TYPES+decider 한번에 넣으면 귀속 불가 |

## 6. 결론 (해볼 가치)
decider = compound destruct 79% 커버(레시피 확정, 0~수십토큰, 안 터짐). 단 [TYPES](87~100%)보다 대상 좁고 세팅 복잡(notation+순서+base매칭+노이즈필터). **1차 효과 본 뒤 순효과 격리 측정 권장.**

관련: [[INDEX_VS_PROMPT]] · [[NOTATION_AND_COVERAGE]] · [[REVIEW]] · [[EXPERIMENT_SETUP]] · [[../opener/DDR_INVESTIGATION_SUMMARY]]
