# 채널 — tactic 마다 술어가 다르다

## 근거

외부 이름을 쓰는 스텝은 전체의 **50.5%**. 그중 apply+rewrite 는 **54.2%** 뿐이다.

| tactic | 비중 |
|---|---|
| apply + eapply | 32.0% |
| rewrite + erewrite | 22.1% |
| destruct | 17.1% |
| unfold | 10.2% |
| induction·case·elim | 4.3% |
| exact·eexact | 2.3% |

## 채널이 서로 다른 집합이라는 증거

**등식 goal 에서조차** apply ∩ rewrite 자카드 **5.0%**:

```
apply 230 · rewrite 275 · 교집합 24

apply 만    Acc_rect · Basics.apply          (등식이 아니라 rewrite 불가)
rewrite 만  Combinators.compose_id_left      (goal 이 그 등식이 아니라 apply 불가)
둘 다       Eqdep.EqdepTheory.eq_dep_eq
```

경로별 적중도 비대칭이다 — **rewrite gold 을 apply 경로는 3.0% 만 찾는다.**


```
        후보 lemma 전체 (프로젝트 색인)
   ┌───────────────────────────────────────────┐
   │   ┌─────────┐                             │
   │   │ apply   │ 230       ┌──────────┐      │
   │   │         │◀── 24 ──▶ │ rewrite  │ 275  │   자카드 5.0%
   │   └─────────┘           └──────────┘      │
   │        ┌──────────────┐                   │
   │        │ apply…in 456 │  (가설 쪽)         │
   │        └──────────────┘                   │
   │   ┌────────┐  ┌──────┐  ┌──────────┐      │
   │   │unfold 5│  │dstr 3│  │ decide 91│      │
   │   └────────┘  └──────┘  └──────────┘      │
   └───────────────────────────────────────────┘

   ★ 겹치지 않는다.  한 줄로 합쳐 정렬하면 큰 것이 작은 것을 덮는다.
```
## 각 채널은 tactic 의 규칙 그대로다

| 채널 | 판정 | 지점당 |
|---|---|---|
| apply | Π-바인더를 evar 로 벗긴 결론이 goal 과 단일화 | ~350 |
| apply…in | **비의존** 전제가 **명제** 가설과 단일화 | ~456 |
| rewrite | 등식 한 변이 **닫힌 부분항**과 keyed 매칭 + 추상 타입검사 | ~310 |
| unfold | goal 에 나타나고 **δ-환원 가능**한 상수 (⚠ 검색이 아니다 → [unfold.md](unfold.md) §4.5) | **4~7** |
| destruct | 타입이 귀납형인 항 | ~3 |
| decide | 결론이 귀납형이고 인자가 goal 부분항과 **단일화** | ~91 |

발명한 게 아니라 규칙을 옮긴 것이다. 그래서 정밀도가 apply **96.9%** · apply…in **99.8%** 다.


### 어느 쪽(goal / 가설)을 보나

```
                       goal 쪽              가설 쪽
                  ─────────────────    ─────────────────
   결론을 맞춘다      apply                apply … in
   부분항을 고친다     rewrite             rewrite … in
                        │                      │
                   goal 의 부분항           가설의 부분항

   r10 에서 rewrite 를 둘로 갈랐다:
       rewrite(goal)  268        ← gold PTree.gso 는 여기
       rewrite(hyp)   147        ← 겹치지 않는 147개
```

`rewrite <-` / `rewrite ->` 는 **채널을 나누지 않는다.** 등식 lemma 를 색인할 때
**좌변과 우변을 둘 다** 넣기 때문이다 (`dig_sides`, 태그 `깊이*2+변`).

```coq
Lonly_l : z + 0 = z * 1     goal 에 z+0 있음 → rewrite Lonly_l   OK
Lonly_r : z * 1 = z + 0     goal 에 z+0 있음 → rewrite <- Lonly_r OK
                                              rewrite Lonly_r    NO
둘 다 CHECK rw=1 로 잡힌다.
```
## 결정적인 채널 vs 추측이 필요한 채널

| | 채널 | 성격 |
|---|---|---|
| 결정적 | unfold · destruct | goal 만 보면 정해진다. 4~7개 |
| 추측 필요 | apply · apply…in · rewrite · decide | 수백 개. 랭킹이 필요하다 |

## Coq 에게 직접 물어 확인한 것

```coq
Liff : n = 0 <-> n + 0 = 0     goal 3 + 0 = 0
Land : n + 0 = n /\ n * 1 = n  goal 3 + 0 = 3
```

| 형태 | Coq | 대응 |
|---|---|---|
| `apply Liff` · `apply <- Liff` | OK | 결론을 `<->` 로 분해 |
| `apply Land` | OK | `/\` 로도 분해 |
| `rewrite Land` | **NO** | 맞게 거부 |
| `destruct/elim/case (Lex 3)` | OK | decide 채널 |

**`iff` 는 귀납형이 아니라 `Definition`** 이다 — `Const` 로 온다.

## 코드

`applic_main.ml` — `unifies_upto` · `dig_sides` · `unfold_cands` · `destruct_cands` · `decide_cands`
