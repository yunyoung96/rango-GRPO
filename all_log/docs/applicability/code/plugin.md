# OCaml 플러그인

`ocaml/applic/applic_main.ml` (1,244줄) · Coq 8.18 / OCaml 4.14

## 빌드

```bash
cd ocaml/applic
export OCAMLPATH=$PWD/findlib:$OCAMLPATH
make                       # → applic_plugin.cmxs
```

`findlib/coq-applic/META` 가 있어야 `coqdep` 이 `Declare ML Module` 을 푼다.
`directory = "../.."` 로 상대 경로를 잡는다.


---

## 0. 어디까지가 Coq 것이고 어디부터가 우리 것인가

```
   ┌──────────────────── Coq 안에 원래 있던 것 ────────────────────┐
   │  clib/trie.ml         일반 트라이            (건드리지 않음)    │
   │  tactics/dn.ml        판별망 (add/lookup)    (건드리지 않음)    │
   │  tactics/btermdn.ml   constr_val_discr       (건드리지 않음)    │
   │  Unification.w_unify  단일화                 (호출만)          │
   │  Rewrite.is_applied_rewrite_relation         (호출만)          │
   │  Typing.type_of · Retyping.get_type_of       (호출만)          │
   │  Termops.subst_term · Evarutil.new_evar      (호출만)          │
   │  Nametab.shortest_qualid_of_global           (호출만)          │
   │  Environ.fold_constants / fold_inductives    (호출만)          │
   └───────────────────────────────────────────────────────────────┘
                              ▲  이 위를 우리는 한 줄도 안 고쳤다
   ┌───────────────────── 우리가 새로 쓴 것 ───────────────────────┐
   │  ocaml/applic/applic_main.ml   ~1,250줄   전부 새로 씀         │
   │  ocaml/applic/applic.mlg       tactic·vernac 선언              │
   │  scripts/applic_rank.py        랭커 (IDF·비트·나이브베이즈)     │
   │  scripts/channel_budget.py     물채우기 배분                   │
   │  scripts/dn_rank_eval.py 등    평가 하네스                     │
   └───────────────────────────────────────────────────────────────┘
```

**한 줄 요약**: Coq 의 판별트리를 **고치지 않고 호출**한다. 우리가 만든 것은
① 무엇을 색인할지, ② 무엇을 조회할지, ③ 결과를 어떻게 채널로 가르고 순위 매길지 —
그 위층 전부다.

| | Coq 것 | 우리 것 |
|---|---|---|
| 자료구조 | 트라이 · 판별망 · `constr_val_discr` | 세 색인 셋 (`dn_apply`/`dn_prem`/`dn_rw`) |
| 항 → 라벨 | `constr_val_discr` | — |
| **무엇을 넣나** | — | `index_cand` — 결론 접미사 · 비의존 전제 · 등식 양변 |
| **무엇을 빼나** | `Dn.lookup` | 6채널 조회 + `suffix_compat` 선별 |
| 판정 | `w_unify` (전술과 같은 flags) | `descend`·`unifies_upto`·`abstract_ok` |
| 채널 | — | `unfold_cands`·`destruct_cands`·`decide_cands`·`local_hyps` |
| 신호 | — | `lgg_size`·`preorder_of`/`lcp`·`term_size` |
| 랭킹·배분 | — | `applic_rank.py`·`channel_budget.py` |

> `auto`/`eauto` 도 같은 트리를 쓴다. 다른 점은 **auto 는 증명을 하려고** 쓰고
> 우리는 **프롬프트에 무엇을 실을지 고르려고** 쓴다는 것이다. 그래서
> auto 에는 없는 것들이 필요했다 — 채널 분리, IDF, 슬롯 배분.

---
## tactic · vernac

| 이름 | 종류 | 하는 일 |
|---|---|---|
| `applic_filter` | tactic | 6채널 필터 + 신호 출력 |
| `applic_check <ref>` | tactic | 그 이름이 실제 파이프라인에서 살아남나 (진단) |
| `applic_why <ref>` | tactic | 사슬 어디서 끊겼나 |
| `applic_sample <n>` | tactic | 후보 우주에서 1/n 균등 표본 (위음성 측정용) |
| `ApplicPrintTypes <0/1>` | vernac | 진술문까지 출력 |
| `ApplicArrows <n>` | vernac | `max_arrows` |
| `ApplicSetoid <0/1>` | vernac | setoid 관계 판정 |
| `ApplicRigid <0/1>` | vernac | `TransparentState` 경직/투명 |
| `ApplicExact <0/1>` | vernac | 깊이 제한 검증 |
| `ApplicApplyDN <0/1>` | vernac | apply 를 트리로 좁힐지 |
| `ApplicTypeCheckRW <0/1>` | vernac | rewrite 추상 타입검사 |
| `ApplicTransparent <ref>` | vernac | 그 상수를 투명 집합에 추가 |

## 함수

### 색인

| 함수 | 하는 일 |
|---|---|
| `module DN` | `Btermdn.Make(Key)` — Coq 의 판별트리 |
| `ts ()` | `TransparentState` 선택 |
| `index_cand` | 후보 하나를 세 색인에 (apply 접미사 · 첫 전제 · rw 좌우변) |
| `build_index` | `fold_constants` + `fold_inductives` 로 전체 열거. 파일당 1회 |

### 판정

| 함수 | 하는 일 |
|---|---|
| `descend` | Π-바인더를 evar 로 d개 벗긴다. **evar 를 만든 sigma 를 계속 들고 가야** 한다 |
| `unifies_upto` | 0~`max_arrows` 를 훑으며 goal 과 맞춘다 |
| `unifies_at` | 트리가 알려준 **그 깊이만** 확인 |
| `unify_ap` | `w_unify ~flags:(elim_flags ())` — apply 와 같은 플래그 |
| `concl_parts` | 결론을 `/\`·`<->` 로 분해. **`iff` 는 `Definition`** |
| `suffix_compat` | 값싼 머리-라벨 선별. `Prod` 에 고유 라벨 필요 |
| `rw_sides` | `eq`/`iff` 직접, 그 밖은 `Rewrite.is_applied_rewrite_relation` (캐시) |
| `dig_sides` | 바인더를 벗기며 관계를 찾는다. 지역 가설에 필수 |
| `abstract_ok` | `subst_term` → `λx.C[x]` → `Typing.type_of`. rewrite 의 실제 부수조건 |

### 채널

| 함수 | 채널 |
|---|---|
| `unfold_cands` | goal 의 상수 중 `const_body = Def _` |
| `destruct_cands` | 닫힌 부분항의 타입 머리가 `Ind` |
| `decide_cands` | 결론이 귀납형이고 인자가 goal 부분항과 `unify1` 성공 |
| `local_hyps` | `Environ.named_context` |

### 신호

| 함수 | 신호 |
|---|---|
| `lgg_size` | 반단일화 크기 |
| `preorder_of` · `lcp` | Baire 초거리 |
| `term_size` | 항 크기 |

### 본체

| 함수 | 하는 일 |
|---|---|
| `compute` | 6채널을 다 돌려 결과·신호를 반환. `filter_tac` 과 `check_tac` 이 공유 |
| `filter_tac` | 결과 + 신호 + `HYPS`/`GBIND` + `APPLIC_STAT` 출력 |
| `check_tac` | 한 이름이 살아남았나만 출력 (`CHECK`) |

## 출력 형식

```
APPLIC PTree.gso lgg=15 e=6 lcp=15 g=20 :: (forall …)
APPLICIN <이름> …
DNRW   PTree.gso z=5 d=6 lcp=4 nm=1 ing=1 g=20
UNFOLD PTree.set occ=2 z=6 g=20
DESTRUCT PTree.tree
DECIDE Nat.zero_one lgg=4 lcp=1 g=20
HYPS   H m x j i A
GBIND  l n
APPLIC_STAT ver=r9 cand=12652 pat=87139 build=0.82 hyps=6 redex=20
            raw=34461 keypass=5821 apply=349 applyin=456 rewrite=310
            unfold=4 destruct=3 decide=91 sec=0.54
```

**주의**: OCaml 문자열 줄바꿈이 공백을 남긴다. 파이썬 정규식은 `\s+` 를 써야 한다.
단일 공백으로 짜면 조용히 0 지점이 된다.
