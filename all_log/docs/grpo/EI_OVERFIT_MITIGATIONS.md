# EI overfitting 완화책 — 정확한 구현 설계

작성 2026-07-28. 관련: [[EI_PROGRESS]], [[HARVEST_ROUND]], [[research-direction-2026-07]].
배경: EI(rollout→RFT→GRPO ×3)에서 **train coverage↑(36→43%)인데 held-out 정체 우려**. 징후 = grp_std 0.133→0.116, mixed 31→28%, (RFT가 자기 성공에 sharpening + KL이 base 아닌 직전 라운드에 앵커 → **누적 drift**).

각 완화책을 **우리 코드 기준 정확히 어떻게** 바꾸는지 정리. (리서치 근거는 §6.)

---

## 1. 라운드 축소 + held-out early-stop (가장 중요·리스크 0)

**핵심**: rand200(테스트)으로 라운드를 고르면 **선택 편향(leakage)** — 그 숫자가 낙관적으로 부풀려짐. → **별도 val 셋**으로 라운드 선택하고, rand200은 **최종 1회만** 판정.

**구현**:
1. **val 셋 분리** (train 300·rand200 200과 **disjoint** CompCert 정리 ~60개):
   `data/compcert_bs2_val_idx.txt` 생성. (train·rand200 인덱스 제외한 나머지에서 60개 샘플. 검증: `set(val) ∩ set(train) == ∅ and set(val) ∩ set(rand200) == ∅`.)
2. **라운드마다 val eval**(싸게, w2 GPU1, 60개면 ~3.5h):
   `run_ei_cont.sh`에 이미 per-round eval 골격 있음 → RAND 대신 VAL로 한 줄 추가:
   ```bash
   VAL=data/compcert_bs2_val_idx.txt
   VD=all_results/val_ei_r${k}_w2
   python3 scripts/run_all.py --alias rango-grpo-ei-r${k} --idx-file "$VAL" \
       --timeout 600 --gpus 1 --workers 2 --out "$VD"
   VS=$(python3 -c "import json;r=json.load(open('$VD/summary.json'))['results'];print(sum(x['success'] for x in r),len(r))")
   ```
3. **early-stop 규칙**: val 성공률이 **연속 1라운드 개선 없으면 정지**, **best-val 라운드**를 최종 모델로 확정 → 그 모델만 rand200으로 판정.
4. **NROUNDS 상한**도 병행: `run_ei.sh:15 NROUNDS=${NROUNDS:-3}` → 무한 루프 방지용 상한(예: 5)만 두고 실제 종료는 early-stop이.

**비용**: val 60개 × 라운드당 ~3.5h (rand200 12.5h보다 훨씬 쌈). 라운드 선택을 여기서 하니 test 오염 없음.

---

## 2. KL을 base(π₀)에 앵커 — 누적 drift 차단

**현재 문제**(코드): `grpo_train.py:833 ref_model = copy.deepcopy(policy).eval()` + `policy = PeftModel.from_pretrained(base, args.init_adapter)`(L.822). → **ref = 그 라운드 init(직전 라운드 모델)**. RFT(`sft_batch_loss` L.524)·GRPO(`grpo_batch_loss` L.535) 둘 다 이 ref에 KL. → 라운드마다 기준점이 바뀌어 **π₀에서 멀어지는 drift가 누적**.

**변경**: `--ref_adapter` 인자 추가 → 주면 ref를 **고정 π₀**(=`models/rango-grpo/adapter`, SFT→GRPO)에서 로드:
```python
# grpo_train.py argparse (L.720 근처)
ap.add_argument("--ref_adapter", default=None,
    help="KL 기준 정책(고정). 미지정 시 init_adapter(직전 라운드)에 앵커=기존 동작.")
# ref_model 구성 (L.833 교체)
if args.ref_adapter:
    _rbase = load_base(args.model_name)                       # 새 base 인스턴스
    ref_model = PeftModel.from_pretrained(_rbase, args.ref_adapter).eval()
else:
    ref_model = copy.deepcopy(policy).eval()                  # 기존 동작 보존
```
- 사용: `run_ei.sh`의 gtrain에 `--ref_adapter models/rango-grpo/adapter` 추가 → **모든 라운드가 π₀에 앵커**.
- 효과: β·KL(π‖π₀)이 매 라운드 π₀ 근처로 당김 → 3라운드 drift 누적 차단. RFT+GRPO 동시 적용.
- **메모리**: ref가 deepcopy 대신 별도 adapter 로드라 VRAM은 비슷(현 gtrain 42GB/49GB, 여유 OK). base 공유 안 하면 base 한 벌 추가(~2.6GB fp16) — GPU1 여유 내.
- **주의**: β=0.04가 π₀ 앵커에선 너무 셀 수 있음(π₀에 과하게 묶임) → β 튜닝 필요할 수도. 라운드가 진행돼도 π₀에 묶여 개선이 막히면 β↓.

---

## 3. entropy bonus / clip-higher — collapse 방지

**현재**(코드): entropy는 **모니터링만**(`grpo_train.py:695 "entropy": ...`), 손실 항 없음. clip-higher(`clip_eps_high`)는 DAPO/LUFFY 경로(L.557,575)에만 있고 **EI가 쓰는 plain GRPO(L.534-536)엔 미적용**(대칭 clip).

**옵션 A — entropy bonus 추가**(가장 직접적, entropy 이미 계산됨):
```python
# argparse
ap.add_argument("--entropy_coef", type=float, default=0.0)
# grpo 손실 계산부: entropy 이미 m_ent로 산출 → 손실에서 빼기
loss = loss - args.entropy_coef * entropy_mean   # 확률분포 평평하게 유지
```
- 권장 시작값 `--entropy_coef 0.001~0.01`. std/mixed 하락이 멈추는지 로그로 확인.

**옵션 B — 기존 clip-higher를 EI GRPO에 노출**(DAPO식, 코드 재사용):
```python
ap.add_argument("--clip_eps_high", type=float, default=None)  # ε_high>ε_low
# L.535 plain GRPO 호출에 clip_eps_high=args.clip_eps_high 전달
```
- ε_low=0.2, ε_high=0.28(DAPO 값) → 저확률 토큰 상승 여지↑ = entropy collapse 방지. **코드 이미 있음**(grpo.py:322), 호출에 인자만 연결.

→ **B가 코드 변경 최소**(이미 구현된 clip-higher 재사용). A는 더 직접적이지만 새 항.

---

## 4. LR↓ / epochs↓ — 보수적 업데이트

**현재**(EI): `run_ei.sh` gtrain `--lr 1e-6 --epochs 2`.
**변경**: `--lr 5e-7`(절반) + RFT는 `--epochs 1`(자기 성공 과암기 방지). GRPO도 `--epochs 1`부터.
- 가장 싸고 안전한 노브. 먼저 시도해볼 것.

---

## 5. 진단 — R1·R2 held-out 재평가 (어느 라운드서 꺾였나)

현재 R0(π₀ SFT→GRPO)=37.5%, R3=측정중. **R1·R2 held-out을 재서** 곡선을 그리면 overfitting 시점 특정:
```bash
for k in 1 2; do
  python3 scripts/run_all.py --alias rango-grpo-ei-r${k} --idx-file data/compcert_bs2_rand200_idx.txt \
      --timeout 600 --gpus 1 --workers 2 --out all_results/rand200_ei_r${k}_w2
done
```
- 별칭 `rango-grpo-ei-r1/-r2`는 `run_thm.py`에 이미 있음(+ 일반 가드).
- **비용 각 ~12.5h** (총 25h) → held-out 곡선(R0→R1→R2→R3)이 **오르다 꺾이면 overfitting 시점 확정**. 단조 하락이면 EI 자체가 해로움.

---

## 6. 우선순위 / 권장 조합

| 순위 | 완화책 | 비용 | 리스크 | 근거 |
|---|---|---|---|---|
| 1 | **held-out early-stop + val 셋 분리**(§1) | 낮 | 0 | 라운드 과다가 근본원인이면 이걸로 해결 |
| 2 | **LR↓·epochs↓**(§4) | 낮 | 낮 | 가장 싼 과암기 억제 |
| 3 | **clip-higher(§3 B) 또는 entropy_coef(§3 A)** | 중 | 낮 | std/mixed 하락(collapse) 직접 차단 |
| 4 | **KL→π₀ 앵커(§2)** | 중 | 중(β 튜닝) | 누적 drift 차단, but 개선도 묶일 수 있음 |
| 5 | R1·R2 held-out 재평가(§5) | 높(25h) | 0 | 진단용(원인 특정) — 필요 시만 |

**권장 순서**: 먼저 **R3 held-out 숫자 확인** → 37.5% 밑이면 overfitting 확정 → **§1(early-stop)+§4(lr/epochs)**를 R4부터 적용해 재실험. 그래도 std 하락이 문제면 **§3 clip-higher** 추가. §2(KL 앵커)는 drift가 주범일 때.

---

## 7. 문헌 조사 (2026-07-28, arXiv ID 전부 fetch 검증)

### §1 근거 — 라운드 조기중단(held-out 선택)
- **[ReST-EM, Singh 2023, arXiv:2312.06585]** ★핵심. generate→filter(binary reward)→SFT 반복(=EI의 EM view). **"train 성능은 iteration에 선형 상승하나 test는 아님"**, 작은 데이터셋(APPS)은 **iter 1~2 후 overfitting으로 regression**. D_val로 체크포인트 선택. → **우리 1.3B/작은 Coq = APPS 케이스**. train coverage 말고 held-out으로 라운드 선택하라는 직접 근거.
- [STaR, Zelikman 2022, 2203.14465] 패러다임 원조(중단규칙은 없음). [ExIt, Anthony 2017, 1705.08439] EI 계보. [Polu-Sutskever 2022, 2202.01344] 정리증명 EI — 이득은 **새로 풀린 statement가 늘 때만**(새 solve 마르면 라운드=overfit).
- [V-STaR, Hosseini 2024, 2402.06457] 실패 롤아웃으로 verifier 학습(생성기 과학습 회피). [RFT, Yuan 2023, 2308.01825] **"distinct reasoning path 다양성"이 이득을 견인** → 유지 성공증명 **dedup/다양성 가중** 권장.

### §2 근거 — KL을 고정 base에 앵커
- **[Reward Overoptimization scaling, Gao 2022, arXiv:2210.10760]** ★. Goodhart: true reward가 올랐다 꺾이며, 전 곡선이 **초기정책 대비 KL거리**로 파라미터화. → **base 기준 KL이 곧 over-opt 측정축**. 직전 라운드로 재앵커=그 계기판을 리셋해 누적 drift를 숨김. 우리 std/mixed 하락 = proxy over-opt.
- [Ziegler 2019, 1909.08593]·[Stiennon 2020, 2009.01325] RLHF 표준 `r−β·KL(π‖π_ref)`의 π_ref=**고정 SFT/base**(manifold 이탈 방지). → GRPO KL은 **원 SFT-base(π₀)에 3라운드 내내 고정**해야.
- **[TR-DPO, Gorbatovski 2024, arXiv:2404.09656]** 고정 vs 갱신 레퍼런스 정면 연구: **hard swap 위험**, **soft/주기적(EMA) 갱신이 over-opt 완화**. → 3라운드는 우선 고정 base, base KL이 개선을 막으면 그때 soft 갱신.
- **[Yue 2025, arXiv:2504.13837]** RLVR은 분포를 **좁힘**: pass@1↑지만 대형 pass@k는 base가 이김(support 축소). → **held-out을 pass@1뿐 아니라 pass@k로** 측정, 줄면 collapse.

### §3 근거 — entropy 보존/collapse 방지
- **[Entropy Mechanism, Cui 2025, arXiv:2505.22617]** ★ 우리 증상 명명·처방. entropy가 조기 붕괴(logp·advantage 공분산이 원인) → **Clip-Cov / KL-Cov**로 고공분산 토큰 업데이트 억제해 entropy 유지. GRPO 호환·1.3B 적용성 높음.
- **[DAPO, Yu 2025, arXiv:2503.14476]** ★ **Clip-Higher**(상·하 clip 분리, ε_high↑ → 저확률 탐색토큰 상승여지=entropy collapse 방지) + **Dynamic Sampling**(all-pass/all-fail 그룹 버리고 다시 뽑아 mixed로 배치 채움). → 둘 다 우리 loop에 거의 무료로 추가. **Coq는 그룹이 all-fail/all-pass 많아 Dynamic Sampling이 특히 유효.**
- [Wang 2025, 2506.01939] 고엔트로피 20% "forking token"만 PG(다양성 견인) — 8B↑서 효과 커 1.3B엔 선택적. [ProRL, Liu 2025, 2505.24864] KL control+주기적 ref 리셋+다양 태스크면 **장기 RL도 경계 확장**(Yue 반례). [A3C, Mnih 2016, 1602.01783] entropy bonus `+β·H(π)` 원조(REINFORCE Williams'92는 pre-arXiv).

### §4 근거 — 보수적 업데이트 / 데이터 누적·혼합
- **[Curse of Recursion / Model Collapse, Shumailov 2023(→Nature'24), arXiv:2305.17493]** ★. 자기생성 데이터 재귀학습은 **분포 꼬리(희귀·다양 모드)를 먼저 소실**. → 우리 entropy 하락 = tail 침식. 진짜/base 데이터 유지가 해독제.
- **[Accumulating Real+Synthetic, Gerstgrasser 2024, arXiv:2404.01413]** ★ 구체 처방: collapse는 매 라운드 real을 synthetic으로 **교체**해서 생김. **누적**(이전 real+synthetic 다 유지)하면 **test error가 iteration 수와 무관하게 유한 상한** = collapse 없음. → **라운드 n을 n-round 성공만으로 학습하지 말고, 원 SFT/base Coq 코퍼스 + 이전 라운드 성공을 항상 섞어라.** 싸고 임팩트 큼.
- ReST-EM(2312.06585) 실무 가드: **낮은 epoch(1~2) + val 체크포인트 선택**. RFT/RAFT 계열은 늘 base에서 fine-tune(업데이트 누적 안 함).

### 정리증명 특정
- [DS-Prover-V1, 2405.14333] 8M Lean statement=**데이터 폭**으로 collapse 회피(우린 못 따라감→§1-4 의존).
- **[DS-Prover-V1.5, 2408.08152]** ★ 우리 다양성 우려에 가장 관련: GRPO(RLPAF) + **RMaxTS(intrinsic-reward 탐색 보너스로 다양 증명경로 생성, mode collapse 방지)**. → GRPO-on-proofs엔 **명시적 다양성 기제**가 필요하다는 직접 선례.
- [DS-Prover-V2, 2504.21801] subgoal 분해 RL(우리 subgoal-GRPO와 계열, 671B). [Lean-STaR, 2407.10040]·[Goedel, 2502.07640] 필드 패턴=**다양·성장하는 solved pool + 추론시 다양성**으로 collapse 제어(명시적 정규화 대신). → 1.3B는 데이터폭이 없으니 **일반 RLVR의 정규화 가드(§1-4)를 import**해야.

### Top 5 takeaway (우리 상황)
1. **라운드 중단은 held-out으로, train coverage로 하지 마라.** ReST-EM이 정확히 우리 케이스(작은 데이터 iter1~2 후 regression). held-out **pass@1 + pass@k** 추적, last 아닌 **best 라운드** 채택.
2. **GRPO KL을 매 라운드 고정 π₀에 앵커**(직전 라운드 재앵커 금지). Gao=over-opt 축이 base-KL. 막히면 soft 갱신(TR-DPO).
3. **entropy 보존 항 지금 추가**: DAPO **Clip-Higher + Dynamic Sampling**(Coq all-fail/all-pass 그룹에 특효) 또는 **KL-Cov**(Cui).
4. **자기데이터만으로 학습 금지 — base/원 SFT 코퍼스 혼합 + 이전 라운드 누적**(Gerstgrasser 상한보장, Shumailov tail 소실 방지). + 낮은 LR·1~2 epoch.
5. **다양성은 명시적으로 사야 함**: 정리증명 유일 선례=DS-Prover-V1.5 RMaxTS intrinsic-reward. 데이터폭 없는 1.3B는 §1-4 정규화로 대체.

---

## 8. 조사로 강화된 신규 실행항목 (기존 §1-5에 추가)

- **[신규 A] 데이터 누적 + base 혼합** (Gerstgrasser 2404.01413 · Shumailov 2305.17493): 라운드 RFT/GRPO를 **그 라운드 성공만**이 아니라 **원 SFT 코퍼스 + 전 라운드 성공 누적**과 섞어서. → `extract_successes` 출력을 라운드마다 append하는 buffer + SFT 코퍼스 일부 concat. **가장 이론근거 강한 추가(collapse 유한상한 보장)**. 우선순위 **2위급**으로 격상.
- **[신규 B] Dynamic Sampling** (DAPO 2503.14476) — ⚠ **우리에겐 실익 미미(정정 2026-07-28)**: DAPO의 DS는 "zero-adv 그룹이 배치를 채워 gradient 희석/정체"를 막는 건데, **우리 코드는 이미 dead를 스킵**한다(`grpo_train.py:454-458`: `outcome_dead=all(|adv|<1e-8)` → `continue`). all-fail·all-pass 둘 다 std=0→adv=0→배치에서 제외 = dilution·연산낭비 없음. → **DS는 dead에서 신호를 만들지 않음**(advantage 여전히 0). 유일 효과 = 남는 mixed(~28%, ~80그룹)를 더 뽑아 유효배치를 키우는 것(롤아웃 연산↑, dead는 그대로). **dead를 살리려면 advantage를 0이 아니게 해야 함 → search-rollout(dead→mixed 크래킹)이나 process/dense reward(`grpo_train.py:160` 지점)로. DS 아님.**
- **[신규 C] held-out을 pass@k로도 측정** (Yue 2504.13837): rand200 eval에 pass@k(예 k=8) 병행 → collapse(=pass@k 축소) 조기 감지. eval 시 G회 샘플 성공률 기록.
