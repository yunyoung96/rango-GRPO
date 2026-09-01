# 용어

용어 하나당 파일 하나. 본문에서 `[[이름]]` 으로 건다.

## Coq / OCaml 내부

| | |
|---|---|
| [sigma](sigma.md) | 미지수 장부 (`Evd.evar_map`) |
| [evar](evar.md) | 아직 안 정해진 항 |
| [econstr](econstr.md) | `EConstr` vs `Constr` |
| [de-bruijn](de-bruijn.md) | 이름 없는 변수 (`Rel n`) |
| [noccurn](noccurn.md) | "그 변수 안 쓰나?" — 의존/비의존 가르기 |
| [prod](prod.md) | `Prod`/`Lambda`/`App` — 커널 항 모양 |
| [index](index.md) | **색인** — 미리 만들어 두는 조회용 자료구조 |
| [globref](globref.md) | 전역 참조 — 판별트리의 라벨 |
| [qualid](qualid.md) | 지금 통하는 가장 짧은 이름 |
| [w-unify](w-unify.md) | 단일화 — 필터의 판정기 |
| [transparent-state](transparent-state.md) | 어느 상수를 펼칠까 |
| [delta-reduction](delta-reduction.md) | βδιζη 다섯 환원 |
| [keyed-unification](keyed-unification.md) | rewrite 의 매칭 규칙 |

## 우리 방법

| | |
|---|---|
| [tf-idf](tf-idf.md) | 자연어 검색의 기본 점수 — 현행 rango 가 쓰는 것 |
| [idf](idf.md) | 원래 자연어 idf |
| [applic-idf](applic-idf.md) | **우리 변종** — 적용가능성 위에서 다시 정의 |
| [lex](lex.md) | 어휘 겹침 — goal 텍스트 ↔ 후보 진술문 |
| [nov](nov.md) | 이름 겹침 — goal 이름 조각 ↔ 후보 이름 |
| [gnames](gnames.md) | goal 쪽 이름 조각 집합 — `nov` 의 상대편 |
| [lcp](lcp.md) | 최장 공통 접두사 |
| [naive-bayes](naive-bayes.md) | 신호 합치기 |
| [cross-validation](cross-validation.md) | 교차검증 — 배운 데이터로 채점하지 않기 |

## 도구·함정

| | |
|---|---|
| [regex-group](regex-group.md) | 정규식 캡처 / 비캡처 그룹 — **조용한 0** 사고의 원인 |

> 더 큰 개념(격자·초거리·채널·예산·한계)은 [../concepts/](../concepts/) 에 있다.
