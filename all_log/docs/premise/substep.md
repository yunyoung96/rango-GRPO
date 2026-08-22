# cut 을 여러 스텝으로 쪼갠다 (안 B)

## 왜

지금은 cut 이 **한 스텝의 정답 하나**다.

    원래:  apply L
    cut :  assert (P) as H_asrt0. { exact L. } apply H_asrt0.      ← 통째로 하나

그런데 cut 을 만든 이유가 **"L 이 프롬프트에 없어서"** 다. 그러면 모델은
`exact L` 의 `L` 을 **볼 수 없는 상태로** emit 하도록 학습된다 — cut 이 막으려던
바로 그것이다.

C 측정(`assert 후 재검색하면 L 이 잡히나`, eqx 88.6%)은 **2스텝 추론**을 가정한다:
① assert 를 세우고 → ② 새 goal(=P)로 **다시 검색**해서 `exact L`.
학습 데이터가 1스텝이라 그 가정과 어긋나 있다.

## 무엇으로 쪼개나

missing lemma 가 `k` 개면 **2k+1** 개.

    step_idx=10:  apply L1 L2        (L1, L2 둘 다 검색 실패)

      sub 0:  assert (P1) as H_asrt0.     상태 Γ ⊢ G
      sub 1:  exact L1.                   상태 Γ ⊢ P1                ★ 검색이 L1 을 찾는다
      sub 2:  assert (P2) as H_asrt1.     상태 Γ, H0:P1 ⊢ G
      sub 3:  exact L2.                   상태 Γ, H0:P1 ⊢ P2         ★ L2
      sub 4:  apply H_asrt0 H_asrt1.      상태 Γ, H0:P1, H1:P2 ⊢ G

`assert (P) as H.` 는 goal 을 **둘로** 만든다 — `P` 가 먼저, 그 다음 `H:P` 가 추가된
원래 goal. 그래서 상태가 위처럼 번갈아 간다. **Coq 실행이 필요 없다** — `P`·`Γ`·`G` 를
전부 알고 있다.

## 왜 안 B 인가 (인덱스를 안 늘린다)

데이터셋은 `ShuffledIndex` 로 `(file, proof_idx, step_idx)` 를 인덱싱한다. 한 스텝을
2k+1 로 늘리면 `__len__` 이 바뀌고 스케줄러·재개·`max_steps` 계산이 전부 흔들린다.

    안 A: 데이터셋을 늘린다        정확하지만 인덱스 체계 변경
    안 B: 하위스텝 **하나**를 결정적으로 고른다   `__len__` 불변         ← 채택
    안 C: 1스텝 유지 + out_tokens 상향           ②를 못 배움

안 B 는 `sub = H(sid) mod (2k+1)` 로 고른다. cut 이 걸린 스텝이 전체의 ~8% 이므로
한 에폭이면 세 유형(assert / exact / 마무리)이 모두 충분히 나온다.

## ★ 핵심 걸림돌 — 검색을 **그 하위스텝의 상태로** 다시 해야 한다

`sub 1` 의 정답은 `exact L1` 이고, 그게 학습되려면 **프롬프트에 L1 이 있어야** 한다.
그러려면 검색 질의가 `Γ ⊢ G` 가 아니라 `Γ ⊢ P1` 이어야 한다.

    lm_example.example_from_step
      → premise_client.get_ranked_premises(step_idx, proof, dp_obj, …)
      → 질의는 `proof.steps[step_idx].goals[0]` 에서 뽑는다        ← 원래 상태에 묶여 있다

그래서 **하위스텝 선택이 검색보다 먼저** 일어나야 하고, 합성 `Goal(hyps, goal)` 을
검색에 넘길 수 있어야 한다. `Goal` 은 `(hyps, goal)` 뿐인 단순 자료구조라 합성은 쉽다.

    example_from_step(..., goal_override: Goal | None = None)

## 점검 항목 (학습 코드를 빡세게 봐야 하는 자리)

  G1 ★ 검색 질의가 **그 하위스텝의 상태**로 갔는가
       `sub 1` 인데 원래 goal 로 검색하면 L1 이 안 나온다 = 아무것도 안 고친 것.
  G2 ★ 프롬프트의 `[STATE]` 가 그 하위스텝 상태인가
       검색만 바꾸고 STATE 를 안 바꾸면 모델이 **다른 goal 을 보고** 답하게 된다.
  G3 ★ 정답이 그 하위스텝의 tactic 하나인가 (통째로 남아 있으면 안 된다)
  G4 ★ `H_asrt` 이름이 하위스텝 사이에서 **일관**되는가
       sub 0 이 `H_asrt0` 을 만들었으면 sub 4 도 `H_asrt0` 을 써야 한다.
  G5 ★ 선택이 **결정적**인가 (같은 인덱스 → 항상 같은 하위스텝)
       아니면 캐시·재개가 어긋난다.
  G6 ★ `2k+1` 이 실제 missing 개수 `k` 를 따르는가 (계획의 lem 전부가 아니라)
  G7   하위스텝별 정답이 `out_tokens` 안에 들어가는가 (쪼개면 훨씬 짧아진다 — 이득)
  G8   cut 이 아닌 스텝은 **아무 영향이 없는가**

## 재생성이 필요한가 — **아니다**

계획 파일의 `lem`(이름 + statement)만 있으면 하위스텝을 전부 유도할 수 있다.
지금 돌고 있는 생성은 그대로 쓰면 된다.

## 부수 효과: `out_tokens` 문제가 완화된다

    statement 24,799개 · 토큰 중앙 23 · 90% 54 · 99% 133 · 최대 1,053
    assert 선언만 128 초과   381 (1.54%)
    전체 cut  128 초과       666 (2.69%)

쪼개면 각 하위스텝이 짧아져 `assert 선언` 하나만 예산에 들어가면 된다 →
초과가 2.69% → 1.54% 로 준다. `out_tokens` 를 192 로 올리면 0.48% 까지 내려간다.

---

## 실측: 분해와 선택이 설계대로 작동한다 (2026-08-22)

계획 파일 `data/cut_plans_all.jsonl` 의 앞 30,000건을 `_split_substeps` 로 직접 분해
(프롬프트를 짓지 않으므로 즉시 나온다).

    하위스텝 개수     3: 26,871 (89.6%)   5: 2,363   7: 553   9: 132   …  23: 1
    전체 하위스텝     assert 34,242 · close 34,242 · final 30,000

    ★ sha1(sid) % n 으로 **선택된** 종류
        assert   10,305   34.4%
        close    10,171   33.9%
        final     9,524   31.7%

`2k+1` 이 맞고(k=1 이 89.6%), 선택이 셋에 고르게 퍼진다.

## ★ 검사기 함정 — `H_asrt` 로 cut 을 판정하면 close 를 통째로 놓친다

`close` 하위스텝의 정답은 **`{ exact L. }` 뿐**이라 `H_asrt` 가 들어가지 않는다.
그래서 `if "H_asrt" in target` 으로 cut 여부를 판정하면 close 가 전부
"cut 아님" 으로 분류된다.

    첫 판 verify_u1 결과:  assert 122 · final 128 · close 0 · "cut 미적용" 390
                           exact 대상이 **3개**뿐이었다

**U1(=exact 대상이 프롬프트에 없다)이 사는 자리가 정확히 close 다.** 그걸 버리면
U1 을 측정하지 못한 채 "U1 없음" 이라는 답을 얻는다. `^\{\s*e?exact\b` 도 cut 으로
인정하도록 고쳤다.

## close 에서 U1 이 해소되는가 — **절반만**

`close` 스텝은 assert 의 명제 `P` 를 goal 로 삼아 **검색을 다시 돌린다**
(`_example_with_goal`, 캐시 없음). 찾는 것이 `P` 이고 `L` 의 명제가 `P` 이므로
`eqx` 의 지시자 `1[⟦p⟧=⟦g⟧]` 가 **바로 이때** 발화한다 — α-동치가 성립하기 때문이다.
하위스텝 설계와 `eqx` 의 지시자는 **같은 성질(강제성)의 두 얼굴**이다.

### 실측 (cut 프롬프트 300건 · close 83건)

    exact 대상          85
    ✓ 프롬프트에 있다    39
    ★ 없다              46      **가시율 45.9%**

원래 값이 52% 였으니 **하위스텝만으로는 U1 이 고쳐지지 않는다.**

원인은 재검색이 아니다. 단계별로 추적하면 재검색은 정확히 작동한다 —

    idx=1796002  'exact negb_involutive.'
      assert P   forall b : bool, negb (negb b) = b
      재검색 후  premises 81개 · goal = 'forall b : bool, negb (negb b) = b'   ✓
      L 이 검색 결과에 있나                                              **아니오**

`negb_involutive` 는 **stdlib** 이고, `PremiseFilter` 가 `lib/coq/theories` 의
LEMMA/THEOREM 을 풀에서 제외한다(rango 원본 설계). 랭커는 **풀에 없는 것을 올릴 수 없다.**

### 고침 — 하위스텝 셋은 성격이 다르다

    assert  goal 로부터 **필요한 명제를 추론**한다   → 프롬프트만으로 풀 수 있다
    final   `apply H_asrt0.`                        → 자명
    close   `exact L.` = **순수 이름 회상**          → L 을 못 보면 환각 학습

close 만 검색에 의존한다. 그래서 재검색 뒤에도 L 이 안 보이면 **같은 lemma 의
assert 스텝(pick−1)으로 물러선다**(`_apply_substep` G1b).

설계가 틀린 것은 아니다 — 39/85 는 재검색으로 실제로 찾았다. 풀에 있는 lemma 에는
의도대로 작동하고, 없는 경우의 가드가 빠져 있었을 뿐이다.
