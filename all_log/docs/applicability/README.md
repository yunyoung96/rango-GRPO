# 적용가능성 기반 프리미스 선택

## 이 디렉토리

| | 내용 |
|---|---|
| **README.md** (이 문서) | 방법 요약 — 한눈에 |
| [algorithm/](algorithm/README.md) | **절차** — 입력·출력·모의코드·실행 예시 |
| [concepts/](concepts/README.md) | **공통 개념** — 격자 · Baire 초거리 · 정보이론 · 채널 · 물채우기 · 한계 |
| [terminology/](terminology/README.md) | **용어** — 하나당 파일 하나 (`sigma`·`noccurn`·`evar`·`w_unify`…) |
| [code/](code/README.md) | **코드 설명** — 플러그인 함수별 · 파이썬 스크립트 17개 |
| [versions/](versions/README.md) | **판본 이력** r1~r11 — 변경 · 이유 · 함정 |
| [results/](results/README.md) | **판본별 결과 보고서** |
| [future-work/](future-work/README.md) | **앞으로 할 것** — 학습에도 쓸 수 있나 |
| [search.md](search.md) | Coq 내장 색인(`SearchPattern`) — 질의 6족 · 전사 3건 |
| [applicability-filter.md](applicability-filter.md) | 밖에서 색인 만든 8판본 실패기 |
| [classical-lemma-retrieval.md](classical-lemma-retrieval.md) | 고전 선행 연구 |
| [requirements/](requirements/README.md) | **요구사항** — 환경·빌드·데이터·검증 (`setting.txt`) |

읽는 순서 — **concepts → terminology → code → versions → results**

관련 — [../premise/](../premise/README.md) · [../research/](../research/README.md)

---

> 한 줄: **검색의 술어를 "어휘가 겹치는가"에서 "그 자리에서 실제로 적용되는가"로 바꾼다.**
> 판정은 Coq 커널이 하고, 같은 판별트리가 랭킹 거리까지 준다.

관련 — [../premise/terms.md](../premise/terms.md) · [../premise/rankers.md](../premise/rankers.md)

---

## 1. 무엇이 문제였나

- 현행 rango 는 **tf-idf 로 어휘 유사도**를 잰다. 우리가 원하는 것은 **적용가능성**이다.
- 둘은 풀이 작을 때만 비슷하다. 풀이 넓어지면 무너진다 — 실측:
  - 현행 풀 top10 : stdlib **8.7%** · 보편 lemma **0.0%**
  - 필터후 풀 top10 : stdlib **43.3%** · 보편 lemma **19.3%**
  - `rewrite repr_canonical` — 현행 풀 148개에서 gold 순위 **0**, 필터후 풀 890개에서 순위 **31**.
    위에 올라온 것: `Ring_polynom.PEeval`, `Basics.const`, `eq_trans`, `True_rec`, `or_ind`
- v10 ckpt-32000 실측(487 스텝, gold prefix 오라클): **도달성 실패 45.4%** vs 조립 실패 15.4%.
  → 모델이 못 조립하는 게 아니라 **그 이름을 아예 모른다.**

---

## 2. 구조 — 하나의 격자에서 필터와 랭커가 쌍대로 나온다

- 항은 포섭 순서로 격자를 이룬다. `t₁ ≼ t₂ ⟺ ∃σ. σt₁ = t₂`
  - **join ⊔ = 단일화(mgu)** → **필터**: `g ⊔ concl(L)` 이 존재하는가
  - **meet ⊓ = 반단일화(lgg)** → **랭커**: `g ⊓ concl(L)` 이 얼마나 큰가  (Plotkin 1970)
- 판별트리는 전위 순회 문자열의 **트라이**다. 그 위의 자연 거리는 최장 공통 접두사:
  - `d(s,t) = 2^(−LCP(s,t))`, 강삼각부등식 `d(s,u) ≤ max(d(s,t), d(t,u))` — **초거리(Baire)**
  - 같은 트리가 **가지치기**(집합)와 **거리**(랭킹)를 둘 다 준다. 자료구조를 더 안 만든다.
- 실측으로 두 관점이 일치한다:
  ```
  PTree.gso (정답)   lgg=15  lcp=15  g=20
  Ring_polynom.PEeval lgg=1   lcp=1
  ```

---

## 3. 구현 — OCaml 플러그인 (`ocaml/applic/`)

- 빌드: `coq_makefile` + `findlib/coq-applic/META`. Coq 8.18 / OCaml 4.14.
  `export OCAMLPATH=$PWD/findlib:$OCAMLPATH && make`
- 핵심 API — 전부 **Coq 자신의 것**:

| 쓰는 것 | 위치 | 역할 |
|---|---|---|
| `Environ.fold_constants` / `fold_inductives` | `build_index` (`applic_main.ml:255`) | 환경 전체 열거 (12,652 후보) |
| `Btermdn.Make` | `module DN` (`:61`) | Coq 의 판별트리 (`auto`/`eauto` 가 쓰는 것) |
| `Unification.w_unify` + `elim_flags` | `unify_ap` (`:328`) | `apply` 와 **같은** 단일화 |
| `Rewrite.is_applied_rewrite_relation` | `rw_sides` (`:124`) | setoid 관계 판정 (Sozeau 2009) |
| `Retyping.get_type_of` · `Typing.type_of` | `abstract_ok` (`:527`) | rewrite 추상의 타입 검사 |
| `Nametab.shortest_qualid_of_global` | `cand_name` (`:44`) | **그 지점에서 유효한 이름** |

- 색인 셋 (`index_cand`, `:210`) — Coq 의 `hints.ml:252` 설계를 따름:
  ```
  dn_apply  후보의 모든 화살표 접미사 결론  → (후보, 깊이)
  dn_prem   비의존 전제                    → (후보, 깊이)     apply L in H
  dn_rw     rewrite 관계의 좌·우변         → (후보, 깊이·변)
  ```

---

## 4. 채널 — tactic 의 타입 규칙에서 유도한다

- 실측: 외부 이름을 쓰는 스텝은 전체의 **50.5%**, 그중 apply+rewrite 는 **54.2%** 뿐.
- 그래서 채널을 나눈다. 각 채널은 그 tactic 의 규칙 그대로다.
- 전부 한 파일 안에 있다 — [`ocaml/applic/applic_main.ml`](../../../ocaml/applic/applic_main.ml) (1,244줄).

### 4.1 채널별 판정 함수

| 채널 | 판정 규칙 | 함수 (파일:줄) | 지점당 후보 |
|---|---|---|---|
| **apply** | Π-바인더를 evar 로 벗긴 결론이 goal 과 단일화 | `unifies_upto` · `unifies_at` (`applic_main.ml:383` · `:377`) | ~350 |
| **apply…in** | **비의존** 전제가 **명제** 가설과 단일화 | `compute` 안 ②블록 (`:713`) + `is_prop` (`:474`) | ~456 |
| **rewrite** | 등식 한 변이 **닫힌 부분항**과 keyed 매칭 **+ 추상 타입검사** | `dig_sides` (`:359`) · `rw_sides` (`:124`) · `abstract_ok` (`:527`) | ~310 |
| **unfold** | goal 에 나타나고 **δ-환원 가능**한 상수 | `unfold_cands` (`:556`) | **4~7** |
| **destruct** | 타입이 귀납형인 항 | `destruct_cands` (`:570`) | ~3 |
| **decide** | 결론이 귀납형이고 그 인자가 goal 부분항과 **단일화** | `decide_cands` (`:607`) | ~91 |

### 4.2 각 함수가 실제로 하는 일

| 함수 | 위치 | 하는 일 |
|---|---|---|
| `descend` | `:340` | Π-바인더를 `Evarutil.new_evar` 로 d개 벗긴다. **evar 를 만든 sigma 를 계속 들고 가야** 한다 (안 그러면 `Unknown evar` 이상종료) |
| `unifies_upto` | `:383` | 0~`max_arrows` 단을 훑으며 `unify_ap` 로 goal 과 맞춘다 |
| `unifies_at` | `:377` | 판별트리가 알려준 **그 깊이만** 확인한다 (8단 재훑기를 없앰) |
| `concl_parts` | `:185` | 결론을 `/\`·`<->` 로 분해. **`iff` 는 `Definition`** 이라 `Const` 로 온다 |
| `suffix_compat` | `:455` | 값싼 머리-라벨 선별. `Prod` 에 고유 라벨을 줘야 실제로 거른다 |
| `rw_sides` | `:124` | 결론이 `eq`/`iff` 면 좌·우변. 그 밖은 `Rewrite.is_applied_rewrite_relation` (머리로 캐시) |
| `dig_sides` | `:359` | 바인더를 벗기며 관계를 찾는다. **지역 가설**(`IHcases : forall …, a = b`)에 필수 |
| `abstract_ok` | `:527` | `Termops.subst_term` 으로 redex 를 추상해 `λx.C[x]` 를 만들고 `Typing.type_of` 로 검사 — Coq `rewrite` 의 실제 부수조건 |
| `unfold_cands` | `:556` | goal·가설의 상수 중 `const_body = Def _` 인 것 |
| `destruct_cands` | `:570` | 닫힌 부분항의 **타입 머리**가 `Ind` 인 것 |
| `decide_cands` | `:607` | 결론이 귀납형 적용이고, 그 인자가 goal 부분항과 `unify1` 성공 |
| `local_hyps` | `:400` | `Environ.named_context` — gold 의 12.7% 가 지역 가설이다 |

### 4.3 색인 (`Btermdn`)

| | 위치 | 내용 |
|---|---|---|
| `module DN` | `:61` | `Btermdn.Make(Key)` — Coq 의 `auto`/`eauto` 가 쓰는 판별트리 |
| `index_cand` | `:210` | 후보 하나를 세 색인에 넣는다 (apply 접미사 · 첫 전제 · rw 좌우변) |
| `build_index` | `:255` | `fold_constants` + `fold_inductives` 로 전체 열거. 파일당 1회 (0.6~1.0s) |
| `ts ()` | `:72` | `TransparentState`. `Some empty`(경직) vs `None`(전부 투명, **40배 느림**) |

### 4.4 랭킹 신호

| 신호 | 계산 | 위치 |
|---|---|---|
| `lgg` | 반단일화 크기 — 포섭 격자의 meet | `lgg_size` (`:519`) |
| `lcp` | Baire 초거리 — 전위 순회 문자열의 최장 공통 접두사 | `preorder_of` (`:703`) · `lcp` (`:706`) |
| `e` | evar 수 — `eapply` 가 찍어야 할 인자 | `try_apply` 안 `depth_of` (`compute` 내부) |
| `z`·`nm`·`ing` | redex 크기 · 맞은 redex 수 · goal 안인가 | `compute` ③블록 |
| `occ` | unfold: goal 안 등장 횟수 | `compute` 의 `sig_uf` |

### 4.5 채널은 서로 다른 집합이다

등식 goal 에서조차 apply∩rewrite **자카드 5.0%** (`apply` 230 · `rewrite` 275 · 교집합 24):

```
apply 만    Acc_rect · Basics.apply · Algebra.list_nth
              (등식이 아니라 rewrite 불가)
rewrite 만  Combinators.compose_id_left · Decidable.not_not_iff
              (goal 이 그 등식이 아니라 apply 불가)
둘 다       Eqdep.EqdepTheory.eq_dep_eq · EqdepFacts.eq_sigT_fst
```

- gold 별 경로 적중: **rewrite gold 을 apply 경로가 3.0% 만 찾는다.** 하나의 순위로는 안 된다.
- 측정 코드 — [`scripts/why_rank_drop.py`](../../../scripts/why_rank_drop.py) (top10 구성 분석),
  [`scripts/dn_rank_eval.py`](../../../scripts/dn_rank_eval.py) (tactic 별 표)

### 4.6 프롬프트 슬롯 배분 — 물채우기

- 채널마다 필요한 개수가 다르므로 **한 줄로 합치면 안 된다.**
- 실측: 합치면 `unfold`(지점당 4~7개)이 수백 개짜리 채널에 묻혀 **슬롯 0칸**을 받는다.

| 배분 | E[gold 프롬프트에 실림] |
|---|---|
| 합쳐서 상위K | 58.0% |
| 균등 / 사전확률 비례 | 66.3% / 66.1% |
| **물채우기** | **69.5%** |

- 원리: 한계이득 `p_t·[F(b+1) − F(b)]` 이 큰 채널에 한 칸씩. 정보이론의 water-filling.
- 구현 — [`scripts/channel_budget.py`](../../../scripts/channel_budget.py) (배분 계산),
  [`scripts/inject_wf.py`](../../../scripts/inject_wf.py) (프롬프트 주입기)

## 5. Coq 에게 직접 물어 확인한 변종

```coq
Liff : n = 0 <-> n + 0 = 0     goal 3 + 0 = 0
Land : n + 0 = n /\ n * 1 = n  goal 3 + 0 = 3
```

| 형태 | Coq | 대응 |
|---|---|---|
| `apply Liff` / `apply <- Liff` | **OK** | `concl_parts` (`:185`) 가 `<->` 를 분해. **`iff` 는 `Definition`** 이라 `Const` 로 온다 |
| `apply Land` | **OK** | 같은 함수가 `/\` 도 분해. `suffix_compat`(`:455`) 선별에도 넣어야 한다 |
| `rewrite Land` | **NO** | 맞게 거부 |
| `destruct/elim/case (Lex 3)` | OK | `decide_cands` 를 일반 귀납형 결론으로 확장 |
| `rewrite L in H` · `!L` · `(L a)` · `setoid_rewrite` | OK | 전부 덮음 |

---

## 6. 랭킹 — 신호를 전부 **비트**로

- `bits(사건) = −log₂ P(사건)`. 단위가 같아지므로 그냥 더한다.

| 신호 | 뜻 | 출력 |
|---|---|---|
| **applic-idf** | `−log P(L 이 필터를 통과)`. 어디에나 되는 것 = **0비트** | 오프라인 집계 |
| **lgg** | 포섭 격자의 meet 크기 | `lgg=15` |
| **Baire LCP** | 트라이에서 갈라지는 깊이 | `lcp=15` |
| **evar** | `eapply` 가 찍어야 할 인자 수 | `e=6` |
| **z / nm / ing** | redex 크기 · 맞은 redex 수 · goal 안인가 | `z=5 nm=1 ing=1` |
| **occ** | unfold: goal 안 등장 횟수 | `occ=2` |
| **lex / nov** | 진술문 어휘 겹침 · **이름** 어휘 겹침 | 파이썬에서 계산 |

- 실제 출력 (`applic_filter` · `ApplicPrintTypes 1`):
  ```
  APPLIC PTree.gso lgg=15 e=6 lcp=15 g=20 :: (forall [A] [i j] x m, i <> j -> ...)
  DNRW  PTree.gso z=5 d=6 lcp=4 nm=1 ing=1 g=20
  UNFOLD PTree.set occ=2 z=6 g=20
  DECIDE Nat.zero_one lgg=4 lcp=1 g=20
  HYPS  H m x j i A
  GBIND                      ← goal 바인더 (induction l 의 l)
  ```
- **결합은 나이브 베이즈 로그가능도비** (`scripts/applic_rank.py`, `train_nb`):
  ```
  w(f) = log₂ [ P(f|gold) / P(f|¬gold) ]      score = Σ_f w(f)
  ```
  주변 통계만 주어졌을 때의 **최대엔트로피 결합**. 가중치를 손으로 안 고른다.
- 학습된 값 (해석 가능):
  ```
  ('e', 0)     +12.07   evar 0개 = goal 이 lemma 를 완전히 결정 (= exact 가능)
  ('nov', 3)    +8.04   이름 겹침 — repr_canonical ↔ goal 의 repr_*
  ('lex', 5)    +6.80   진술문 어휘 겹침
  ('ch','uf')   +5.68   unfold 채널
  ('idf', 4)    +5.06   희소한 lemma
  ('std', 1)    −1.99   stdlib 감점
  ('ch','in')   −2.75   apply…in 은 대부분 잡음
  ```

---

## 7. 실측 (CompCert rand200)

### 필터

| | |
|---|---|
| 후보 우주 | 21,627 |
| 필터 통과(중앙) | 1,157 = **5.35%** (19배 축소) |
| gold 생존 (전체) | **96.5%** |
| gold 생존 (rewrite, 정직한 분모) | **97.7%** (126/129) |
| 정밀도 apply / apply…in / rewrite | **96.9% / 99.8% / 64.5%** |
| 위음성 (거부 표본 중 실제로 되는 것) | 5.97% |
| 지점당 질의 | 0.31~0.5s · 색인 구축 0.6s (파일당 1회) |

### 랭킹 (312지점 · 5겹 교차검증 · **순위만**, 프롬프트 아님)

| 랭커 | @10 | @20 | @50 | @100 | 순위중앙 |
|---|---|---|---|---|---|
| 무작위 | 21.5% | 23.7% | 27.6% | 33.0% | 240 |
| applic-idf 단독 | 49.4% | 55.4% | 61.9% | 67.6% | 9 |
| 비트합(정보이론) | 53.5% | 60.6% | 67.6% | 71.2% | 6 |
| **나이브베이즈** | **76.6%** | **83.0%** | **86.2%** | **87.5%** | **1** |

| gold tactic | 지점 | 풀에 | @10 | @100 |
|---|---|---|---|---|
| **unfold** | 66 | 100% | **100%** | 100% |
| apply | 120 | 95.8% | 74.2% | 91.7% |
| rewrite | 57 | 94.7% | 68.4% | 84.2% |
| destruct | 50 | 96.0% | 52.0% | 84.0% |

- **`unfold` 은 현행 rango 가 0.0%** 다 — 유사도 기반이 구조적으로 못 찾는 채널.
- 정보 예산: `14.32 bit` 필요 = 필터 `5.08` + 랭커 `3.27` + 모델 몫 `5.97`

---

## 8. 검색과 익명화의 순서

- 검색·랭킹·절단은 **전부 실명** 위에서. 익명화는 조립이 끝난 문자열에 마지막 한 번.
  `_maybe_normalize_input` (`src/tactic_gen/tactic_data.py:1139`)
- 그래야 하는 이유: 최강 신호가 **이름 겹침**(`nov` +8.04 bit)인데 `_L3` 로는 계산 불가.
- 설정은 **파이썬 상수**다 — `src/tactic_gen/normalize_config.py`.
  env 로 두면 `source` 를 잊고 조용히 다른 설정으로 돈다(실제로 두 번 당했다).

---

## 9. 겪은 함정 (전부 실측으로 걸림)

| 증상 | 원인 | 교훈 |
|---|---|---|
| 전 지점 0 | OCaml 문자열 줄바꿈이 공백을 남겨 정규식 불일치 | 정규식은 `\s+`, **시동 자가검사** 필수 |
| 전 지점 0 | `capture_output` 을 `Popen` 에 넘겨 TypeError → `except` 가 삼킴 | 예외를 삼키는 코드에 assert |
| RSS 116GB · 좀비 17개 | setoid 판정(타입클래스 해석)을 10만 번 호출 | 머리 기호로 캐시 · `killpg` |
| 선별이 무용지물 (95% 통과) | `Prod` 를 유연 머리로 봄 — 깊이 0 은 거의 다 `forall` | `Prod` 에 고유 라벨 |
| 후보의 34.7% 가 항상 실패 | 모듈 정규화 없이 `eapply gso` (실제론 `PTree.gso`) | `shortest_qualid_of_global` |
| `induction` 재현율 9.5% | `induction l` 의 `l` 은 **goal 바인더** (intros 가 뒤에 옴) | `GBIND` 로 제외 |
| `apply` 재현율 83.5% | `max_arrows=8` — **암묵 인자도 바인더로 센다** | 20 으로 (실측 8→12→20 포화) |
| 200 중 183 정리 유실 | `head_of_file` 이 순진 | `theorem_start_pos.line` 우선 |

---

## 10. 코드 위치

```
ocaml/applic/applic_main.ml     플러그인 본체 (1,244줄)
ocaml/applic/applic.mlg         tactic/vernac 선언
  applic_filter                 5채널 필터 + 신호 출력
  applic_check <ref>            정답이 실제 파이프라인에서 살아남나 (진단)
  ApplicArrows/Setoid/Rigid/…   절제 실험용 손잡이

scripts/dn_rank_eval.py         필터 → 랭킹 → 프롬프트 (tactic 별 표)
scripts/applic_rank.py          applic-idf · 비트합 · 나이브베이즈
scripts/dn_why.py               gold 생존 진단 (사슬 단계별)
scripts/dn_verify.py            **실제 구문** 실행으로 정밀도·위음성
scripts/why_rank_drop.py        필터 후 @10 이 왜 떨어지나 (top10 구성)
scripts/dn_multi_eval.py        CompCert 밖 프로젝트로 일반성 확인
```

---

## 11. 남은 것

- `rewrite` 정밀도 **64.5%** — 추상 타입검사를 넣어도 안 올랐다. setoid 채널 A/B 로 귀속 필요.
- 위음성 **5.97%** — 고차 단일화(`N.binary_ind`, `Equivalence.equiv_symmetric`).
  `elim_flags` 로는 안 풀림. Coq 의 `apply` 는 `Clenv` 로 **메타변수**를 만들어
  `second_order_matching` 경로를 탄다 — 거기까지 가야 한다.
- 상한 셋이 임의값: `max_arrows=20` · `too_big=4000` · `dnet_depth=2`.
- 나이브 베이즈는 독립을 가정하는데 `lcp`·`lgg` 는 강하게 상관 — 이중 계산.
- 판별트리는 **구문적**이라 delta 가 필요한 매칭을 놓친다. 이건 내재적이고,
  심각도는 `TransparentState` 손잡이다 (Lean 의 `@[reducible]` 과 같은 자리).

