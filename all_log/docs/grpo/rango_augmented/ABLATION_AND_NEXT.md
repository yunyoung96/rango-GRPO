# Type-ablation 결론과 다음 수: 왜 타입 주입이 실패했나

작성 2026-08-08. 브랜치 `rango-augmented`. 관련: [[RESULT_AUGMENTED_RETRAIN]] · [[COMPOSITION_IS_THE_WALL]] · [[PHASE2_DECIDER_GUIDE]]

---

## 0. 한 줄

**모델은 [TYPES]/[DEFINITIONS] 의 내용을 읽지 않는다.** 올바른 정의를 줘도 틀린 정의를 줘도
결과가 같다(McNemar p = 1.000). 원인은 정보 부족이 아니라 **loss 가 그 섹션을 읽으라고
강제하지 않는 것**이다.

---

## 1. 결정적 증거 — Type-ablation

같은 모델(v2 step 60000)·같은 정리·같은 조건(600s, `g2×w6=12`, Blackwell ×2)에서
프롬프트 **형식은 고정**하고 [TYPES]/[DEFINITIONS] **내용만** 바꿔 비교했다.

| 조건 | 내용 | 성공/완료 | 성공률 |
|---|---|---|---|
| **clean** | 파일 단위로 고친 **올바른** 정의 | 63/191 | 33.0% |
| **wrong** | 다른 파일의 동명 정의 (**학습과 동일**) | 66/194 | 34.0% |
| corrupt | 생성자 개수·이름 조작 | (중단) | — |
| empty | 헤더만, 내용 `(none)` | (미실행) | — |

```
clean vs wrong — 같은 정리 187개
  clean 63  vs  wrong 63      차이 ±0
  clean만 8  |  wrong만 8      McNemar p = 1.000
```

**해석**: 어제 발견한 인덱스 오염(goal 은 `Lst` 인데 `lst` 정의를 주입)을 고쳐 **올바른 정의를
넣어도 성능이 전혀 변하지 않는다.** "오염 때문에 증강이 실패했다"는 가설은 기각된다.

> corrupt/empty 는 자원 배분 때문에 중단했다. clean == wrong 이 이미 결정적이므로
> (내용의 정오를 구분 못 함) 추가 조건은 결론을 바꾸지 않는다고 판단했다. **미측정임을 명시한다.**

### 같은 방향의 독립 증거 3개

| 증거 | 값 |
|---|---|
| v1(생성자 이름만) vs v2(정의문+재귀) loss 기울기 | **−0.1426 vs −0.1425** (넷째 자리까지 동일) |
| [TYPES] 주입된 151개의 destruct 패턴 오류율 | 2.77% (미주입 49개는 3.70%) — **개선 없음** |
| rand200 v2 vs rango | −2 (p = 0.80), 전이 473정리 −9 (p = 0.23) |

---

## 2. 왜 안 읽나

loss 가 **tactic 토큰에서만** 계산된다. 그런데 학습 타깃의 대부분은 섹션 없이도 예측된다:

```
[TYPES]
Inductive natprod : Type := | pair: nat -> nat -> natprod.
[DEFINITIONS]
Definition swap_pair (p: natprod) : natprod := match p with | (m,n) => (n,m) end.
[TACTIC]
Proof.                       ← 타깃. 위 두 섹션을 볼 이유가 없다.
```

실제 학습 예제에서 gold 가 `destruct`/`induction` 인 비율은 **10.5%** 뿐이다
(destruct 6.7% + induction 3.8%). 나머지 89.5% 의 gradient 는 타입과 무관한 토큰으로 간다.

→ **섹션을 무시하는 것이 최적해**다. 정보를 아무리 정확히 넣어도 학습이 그것을 쓰도록
유도하지 않는다. 이것이 "신호 희석(signal dilution)"이다.

---

## 3. 다음 수 (구현 완료, 검증 대기)

### 3-1. ★ 인용 타깃 — `CITE_TARGET=1` (근본 대응)

타깃 앞에 **무엇을 썼는지** 인용시킨다.

```
[TACTIC]
[USES] Lst(2 ctors)
destruct x as [| n l].
```

정답을 내려면 프롬프트의 [TYPES] 에서 `Lst` 를 찾아 생성자를 세야 한다.
**섹션을 읽지 않으면 loss 가 오르므로** gradient 압력이 생긴다.
(아이디어 목록 **12** CoT 중간표현 강제 + **10** RAFT 의 verbatim 인용 결합)

- 구현: `src/tactic_gen/cite_target.py` (`make_cite` / `strip_cite`)
- 학습 배선: `ProofPremiseCollator.collate` — 주입된 정의만 인용 대상(없는 걸 인용시키면 환각 조장)
- 추론 배선: `tactic_gen_client.get_recs` 에서 `strip_cite` 로 제거 후 Coq 에 전달
- 인용 불필요한 스텝은 `[USES] -` 로 **포맷 고정**(형식이 흔들리면 그 자체가 노이즈)
- 학습 설정: `all_log/ft_rango_augmented_v3_conf.yaml`, 런처 `run_augmented_v3_ddp.sh`
  - 인덱스도 `func_defs_v3.json`(파일 단위)로 교체
  - 나머지는 v2 와 동일(코퍼스·셔플·LoRA·LR·max_steps 60000·유효배치 32) → 직접 비교 가능

### 3-2. ★ 환각 이름 필터 (우선순위 14의 경량 1단계, 학습 불필요)

**측정된 최대 단일 레버**다. rand200 실측:

```
INVALID 7,981건 중 '이름 못 찾음' 3,613 (45.3%)
  ☓ 코퍼스에 아예 없는 이름(지어냄)  2,810 (77.8%)  ← 전체 INVALID 의 35%
  ★ 실재하나 스코프에 없었음            434 (12.0%)
  로컬변수처럼 짧은 이름                314 ( 8.7%)
```

지어낸 예: `apply ltu_shl`, `apply iprop_eqs`, `generalize (shl_shl_split ...)`.
CompCert 명명 규칙을 흉내 낸 그럴듯한 조합이지만 실재하지 않는다
(같은 파일에 `shru_shl` 은 있는데 모델은 `ltu_shl` 을 만든다).

**Coq 검증(~300ms)이 시간을 지배**하므로, 환각 후보를 검증 전에 버리면 절감분이 곧 탐색예산이 된다.

- 구현: `src/model_deployment/name_filter.py`, 허용집합 `scripts/build_known_names.py`
- 허용집합 252,807개 = 선언 + **생성자** + 레코드 필드
  (생성자를 빼면 `destruct (... Readable)` 같은 정상 후보를 오탐 → 반드시 포함)
- 오프라인 검증(allow=∅ 최악값): **INVALID 23.4% 선제 차단 / 유효후보 손실 0.32%**
  - 정밀화 과정: 2.72% → 0.32%
    (`as`/`in`/`with` 이후 제외 · qualified 이름 보존 · `_ind`/`_rec` 자동생성 예외)
- 검증: `all_log/eval_name_filter.sh` — 같은 모델·같은 정리로 ON/OFF 비교

---

## 4. 하지 않기로 한 것과 이유

| 항목 | 판단 |
|---|---|
| 정의 그래프 인코딩 / TyFlow / Graph2Tac | 아키텍처 교체급. 수개월 규모로 현재 자원에 안 맞음 |
| ICL 대조군 | 이 서버에 대조군이 될 큰 모델이 없음(Qwen-7B 뿐) |
| docstring 부착 (Tacq) | 코퍼스에 주석이 거의 없어 재료 부족 |
| 손실 가중(항목 11) | 인용 타깃이 같은 목적을 더 직접적으로 달성. 인용이 실패하면 그때 |

---

## 5. 미해결

- **통제군 없음**: "증강 자체가 loss +0.065 를 만들었나"는 여전히 미확정.
  통제군(증강 OFF, 같은 60k)을 `max_steps: 60000` 유지한 채 돌려야 한다
  (이전 시도는 `max_steps: 2000` 으로 LR 스케줄이 어긋나 무효였다).
- **corrupt/empty 조건 미측정** (§1).
- **인용 타깃의 부작용 미검증**: 생성 토큰이 늘어 탐색 속도가 떨어질 수 있다.
  학습 후 rand200 에서 탐색 횟수(초당)를 함께 봐야 한다.
