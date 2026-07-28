# 더 큰 / teacher 모델 후보 + 로컬 실행 가능성

작성 2026-07-27. 목적: "더 큰 prover로 gold를 만들어 LUFFY/distill" 논의(§`GOLD_PROOF_METHODS.md`, `IDEAS.md` ⑪스케일)의 재료. 웹 확인(2026-07). 출처는 하단.

## 0. 우리 하드웨어 & 로컬 실행 규칙
- **2× NVIDIA RTX 6000 Ada, 각 48GB (총 96GB VRAM).**
- 대략 규칙: **fp16 ≈ 2GB/1B**, **4-bit ≈ 0.5GB/1B** (+KV캐시·컨텍스트 여유).
- 판정: ✓=한 GPU fp16 / ✓TP=두 GPU 나눠 fp16 / ✓4bit=4-bit면 로컬 / ✗=불가.

| 파라미터 | fp16 VRAM | 48GB 한 장 | 96GB 두 장 |
|---|---|---|---|
| 7~8B | ~16GB | ✓ | ✓ |
| 14~16B | ~30GB | ✓ | ✓ |
| 32~33B | ~66GB | ✓4bit(~18GB) | ✓TP fp16 |
| 70~72B | ~144GB | ✓4bit(~40GB, 빡빡) | ✓4bit 여유 |
| 236B(MoE) | ~470GB | ✗ | ✗(4bit도 ~120GB) |
| 671B | ~1.3TB | ✗ | ✗ |

## 1. ⚠️ 가장 중요한 사실 — 이들은 전부 **Lean 4**, 우리는 **Coq**
DeepSeek-Prover / Goedel / Kimina / InternLM-StepProver / BFS-Prover **모두 Lean 4 전용**. **Coq(우리 CompCert)엔 그대로 못 씀** — tactic 언어·라이브러리·증명 스타일이 다름. → **"DeepSeek-Prover-671B 받아서 Coq teacher로"는 불가.** Coq teacher가 필요하면 **우리가 직접 더 큰 Coq 모델(Rango 파이프라인)로 학습**해야 함(=스케일 작업 그 자체).

## 2. DeepSeek-Prover 계열 (Lean 4) — 크기
| 모델 | 크기 | 베이스 | 로컬(48GB) | 비고 |
|---|---|---|---|---|
| DeepSeek-Prover-V1 | 7B | DeepSeek-Math-7B | ✓ | 최초 |
| DeepSeek-Prover-V1.5 | 7B | (Base/SFT/RL) | ✓ | |
| DeepSeek-Prover-V2-7B | **7B** | V1.5-Base, 32K ctx | ✓ | **로컬 가능한 최대 DS-Prover** |
| DeepSeek-Prover-V2-671B | **671B**(MoE) | DeepSeek-V3-Base | **✗** | SOTA(miniF2F 88.9%) 지만 로컬 불가 |

→ **DeepSeek-Prover는 7B 아니면 671B, 중간(13/33/70B) 없음.** 로컬로 쓸 수 있는 건 **7B뿐.**

## 3. 다른 오픈 Lean 4 prover
| 모델 | 크기 | 베이스 | 로컬(48GB) | 비고 |
|---|---|---|---|---|
| Goedel-Prover(V1) | 7B | DeepSeek-Prover-V1.5 | ✓ | miniF2F 57.6%(pass@32) |
| Goedel-Prover-V2 | ~8B / ~32B | (Princeton, 2508.03613) | ✓ / ✓4bit·TP | 32B가 671B급 성능 주장 |
| InternLM2.5-StepProver | 7B | InternLM2.5 | ✓ | expert-iteration + critic best-first |
| BFS-Prover | ~7B | Qwen2.5-Math-7B | ✓ | best-first + critic |
| Kimina-Prover | **72B** (+ distill 1.7B/7B) | Qwen2.5-72B | 72B ✓4bit / distill ✓ | RL, NL+Lean 인터리브 |
| Seed-Prover | 대형/agentic | (ByteDance, 2507) | 대체로 ✗ | 에이전트형, 로컬 부적합 |

→ 로컬(48GB)로 편한 Lean prover: **7~8B급(DS-Prover-V2-7B, Goedel, InternLM-StepProver, BFS-Prover)**. 32B(Goedel-V2)는 4bit/TP로 가능. 72B(Kimina)는 4bit로 빡빡하게.

## 4. Coq 네이티브 (우리 도메인)
| 모델 | 유형 | 비고 |
|---|---|---|
| **Rango** (우리 것) | DeepSeek-Coder-1.3B + BM25/TF-IDF retrieval | CoqStoq(196,929 정리). 현재 우리 base |
| Graph2Tac | GNN(비-LLM) | Tactician API, **노트북/무-GPU 실행**, 새 정의 일반화 강점 |
| Tactician | k-NN(비-LLM) | in-project 유사 상태 검색 |
| Proverbot9001 | RNN | 구형 |

→ **Coq엔 큰 LLM prover가 없음.** Rango(=우리)가 사실상 유일한 LLM 기반. teacher를 키우려면 **DeepSeek-Coder를 키워 Rango로 재학습**해야 함(아래).

## 5. Rango를 키울 때 쓸 범용 코드 base (Coq용으로 학습 가능)
| 모델 | 크기 | 로컬(48GB) | 비고 |
|---|---|---|---|
| DeepSeek-Coder-instruct | **1.3B**(현재) / 6.7B / 33B | ✓ / ✓ / ✓4bit·TP | 현재 1.3B → **6.7B/33B로 스케일 현실적** |
| DeepSeek-Coder-V2 | 16B-Lite(2.4B active) / 236B | ✓ / ✗ | Lite는 MoE로 가벼움 |
| Qwen2.5-Coder-instruct | 0.5~32B (0.5/1.5/3/7/14/32) | 32B까지 ✓4bit·TP | 코드 강함, 대안 base |

## 5.5 Qwen 계열 (DeepSeek 대안 base) — 로컬 상세

Qwen은 정리증명 base로 실제 널리 쓰임: **Kimina-Prover = Qwen2.5-72B, BFS-Prover = Qwen2.5-Math-7B**. 대부분 **Apache 2.0** 라이선스(상업/수정 자유)도 장점.

### Qwen2.5 계열 (안정·검증됨)
| 모델 | 크기 | 로컬(48GB) | 비고 |
|---|---|---|---|
| Qwen2.5-Coder-Instruct | 0.5 / 1.5 / 3 / 7 / 14 / **32B** | 32B까지 ✓(4bit 한장·fp16 TP) | 코드 특화, **DeepSeek-Coder 직접 대안** |
| Qwen2.5-Math-Instruct | 1.5 / 7 / **72B** | 7B ✓ · 72B ✓4bit | 수학 특화(여러 prover base) |
| Qwen2.5 (범용) | 0.5 … **72B** | 32B ✓ · 72B ✓4bit | |

### Qwen3 계열 (2025-04, Apache 2.0, 최신 — thinking 내장)
| 모델 | 크기 | 로컬(48GB) | 비고 |
|---|---|---|---|
| Qwen3 dense | 0.6 / 1.7 / 4 / 8 / 14 / **32B** | 32B까지 ✓ | |
| **Qwen3-30B-A3B** (MoE) | 30B총 / **3B active** | ✓(4bit 한장·fp16 TP) | **효율 최고**(active 3B라 빠름) + 강력 |
| Qwen3-Coder-Next (MoE) | 80B총 / 3B active, 256K ctx | ✓4bit(빡빡)·TP | 큰데 빠름, 코드 |
| Qwen3-235B-A22B (MoE) | 235B총 / 22B active | ✗ (4bit도 ~120GB) | 로컬 불가 |

→ **로컬 최적 대안 base**: **Qwen2.5-Coder-32B**(안정) 또는 **Qwen3-30B-A3B**(MoE, 빠름). 둘 다 48GB 한 장(4-bit) 또는 두 장(fp16 TP)에 올라감 — 우리 1.3B보다 훨씬 큰 base/teacher로 **현실적이고 DeepSeek보다 라이선스 자유.** 단 **Coq는 여전히 Rango 파이프라인으로 우리가 SFT 재학습해야 함**(base만 바꾸는 것).

## 6. 우리 상황 결론
- **로컬(2×48GB)에서 teacher로 현실적인 최대치 = ~33B(4-bit/TP) 급.** 72B는 4-bit로 겨우, 236B/671B는 불가.
- **DeepSeek-Prover(Lean)는 Coq에 못 씀** → Coq teacher = **DeepSeek-Coder-6.7B/33B(또는 Qwen2.5-Coder-14/32B)를 Rango 파이프라인으로 우리가 학습**해야 함.
- 단, §`GOLD_PROOF_METHODS.md`·`IDEAS.md`대로 **"큰 teacher distill/LUFFY"는 성능은 올려도 contribution 낮음** — 강한 teacher를 만들면 그냥 그걸 쓰지 1.3B로 내릴 이유는 배포뿐. 스케일은 "숫자" 목표일 때의 축(⑪).

## 7. Qwen vs DeepSeek-Prover — 근본 차이 (같은 층위가 아님)

**핵심: Qwen = 범용 foundation(재료), DeepSeek-Prover = 완성된 Lean 전용 prover(완제품).** 비교 대상이 아니라 서로 다른 계층.

| 축 | **Qwen** (2.5-Coder/Math · 3) | **DeepSeek-Prover** (V1~V2) |
|---|---|---|
| 정체 | 범용 base LLM (코드/수학/일반) | **특화 정리증명 모델**(SFT+RL 완료) |
| 대상 형식언어 | 없음(범용) | **Lean 4 전용** |
| 즉시 증명력 | 약함(증명 튜닝 안 됨) | **SOTA**(miniF2F 88.9%@671B) |
| **Coq(우리)에 사용** | **가능** — Rango base로 교체 후 재SFT | **불가** — Lean 전용, Coq 전이 안 됨 |
| 우리 활용법 | base 갈아끼워 더 큰 Coq prover **우리가 학습** | **방법만 참고**(subgoal분해·RMaxTS·EI) |
| 크기 | 0.5~32B dense + MoE(30B-A3B/235B) | 7B / 671B (중간 없음) |
| 로컬(48GB) | 32B·30B-A3B ✓ / 235B ✗ | 7B ✓ / 671B ✗ |
| 라이선스 | 대부분 Apache 2.0 | DeepSeek 라이선스(허용적) |
| prover와의 관계 | **prover의 재료**: Kimina=Qwen2.5-72B, BFS-Prover=Qwen2.5-Math-7B | DeepSeek base 위에 구축된 완제품 |

**비유**: `Qwen : (Kimina/BFS-Prover) = DeepSeek-base : DeepSeek-Prover`.
- **Qwen을 "쓴다"** = 그 위에 prover를 **우리가 학습**한다는 뜻(재료).
- **DeepSeek-Prover를 "쓴다"** = 완제품을 그냥 돌린다는 뜻 — **단 Lean 문제만.**

**우리(Coq) 결론**: DeepSeek-Prover는 **모델로는 못 씀(Lean)**, 논문 **방법만** 참고. 실제 스케일 base = **Qwen2.5-Coder-32B / Qwen3-30B-A3B / DeepSeek-Coder-33B 중 택1 → Rango로 재SFT.** (Qwen과 DeepSeek을 고를 때 비교하는 건 "prover"가 아니라 "**base**"끼리 — Qwen2.5-Coder-32B vs DeepSeek-Coder-33B.)

## 8. 순수 base 비교: DeepSeek vs Qwen (naive, fine-tuning 전제)

어차피 Rango로 재SFT할 거라 **prover 특화 말고 naive base의 역량·크기·라이선스만** 비교. **로컬(2×48GB) 대상만.**

| 모델(naive) | 크기(로컬) | 코드 | 수학/추론 | ctx | 라이선스 | 세대 |
|---|---|---|---|---|---|---|
| DeepSeek-Coder-1.3B | 1.3B ✓ | 하(구형) | 하 | 16K | DeepSeek | 2023 (현 Rango base) |
| DeepSeek-Coder-6.7/33B | ✓ / ✓4bit | 중(구형) | 중 | 16K | DeepSeek | 2023 |
| DeepSeek-Coder-V2-Lite | 16B MoE(2.4B act) ✓ | 중상(HumanEval 83.5) | 중 | 128K | DeepSeek | 2024 |
| DeepSeek-Math-7B | 7B ✓ | — | 중상 | 4K | DeepSeek | 2024 |
| **Qwen2.5-Coder-7/14/32B** | ✓ | **상 (32B HumanEval 88.4 = 오픈 SOTA)** | 중상 | 32K~128K | Apache2.0* | 2024 |
| Qwen2.5-Math-7/72B | 7B✓ / 72B✓4bit | — | 상 | 4K | Apache2.0 | 2024 |
| Qwen3 dense 8/14/32B | ✓ | 상 | **상(thinking 내장)** | 32K~128K | Apache2.0 | 2025 |
| **Qwen3-30B-A3B (MoE)** | 30B/3B act ✓ | 상 | 상 | 32K~256K | Apache2.0 | 2025 |

**근거(naive 벤치):**
- Qwen2.5-Coder는 **5.5T 코드 토큰**(DeepSeek-Coder V1의 ~5배) 학습 → 32B가 **오픈 코드 SOTA(HumanEval 88.4, GPT-4급), SWE-bench·LiveCodeBench 우위.** 로컬 DeepSeek(V2-Lite 16B=83.5, Coder-33B 구형)보다 코드 앞섬.
- **DeepSeek이 확실히 이기는 건 non-local 대형(V2-full 236B / V3)뿐** — 우리 하드웨어 밖.
- 정리증명 = 코드(tactic)+수학추론 → Qwen2.5-Coder(코드) or Qwen3(추론+thinking)이 둘 다 커버.

**추천 base (우리 fine-tune용):**
1. **Qwen2.5-Coder-32B** — 로컬 코드 최강·안정. tactic 생성=코드라 특히 적합.
2. **Qwen3-30B-A3B** — 최신·MoE로 빠르고(active 3B) 추론 강함. 실험 회전율↑.
3. DeepSeek 유지 시 **DeepSeek-Coder-V2-Lite-16B**(효율적) — 단 Qwen보다 한 수 아래.

⚠ **naive 벤치 우위 ≠ fine-tune 후 증명성능 보장**(도메인 시프트 + Rango는 retrieval-aug). 하지만 base 역량이 가장 합리적 prior. *Qwen2.5는 대부분 Apache2.0(3B·72B만 Qwen 라이선스), Qwen3 전부 Apache2.0. DeepSeek도 상업 허용.

---
**Sources**: [DeepSeek-Prover-V2-671B (HF)](https://huggingface.co/deepseek-ai/DeepSeek-Prover-V2-671B) · [DeepSeek-Prover-V2-7B (HF)](https://huggingface.co/deepseek-ai/DeepSeek-Prover-V2-7B) · [DeepSeek-Prover-V2 (GitHub)](https://github.com/deepseek-ai/DeepSeek-Prover-V2) · [Goedel-Prover](https://goedel-lm.github.io/) · [Goedel-Prover-V2 (arXiv 2508.03613)](https://arxiv.org/pdf/2508.03613) · [InternLM2.5-StepProver (arXiv 2410.15700)](https://arxiv.org/html/2410.15700v1) · [Rango (arXiv 2412.14063)](https://arxiv.org/html/2412.14063) · [Graph2Tac (arXiv 2401.02949)](https://arxiv.org/abs/2401.02949) · [Qwen3 blog](https://qwenlm.github.io/blog/qwen3/) · [Qwen3 Technical Report (arXiv 2505.09388)](https://arxiv.org/pdf/2505.09388) · [Qwen2.5-Coder (HF)](https://huggingface.co/Qwen/Qwen2.5-Coder-32B-Instruct)
