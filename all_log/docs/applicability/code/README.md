# 코드 지도

| 문서 | 내용 |
|---|---|
| [plugin.md](plugin.md) | OCaml 플러그인 — 함수별 설명 · 빌드 |
| [scripts.md](scripts.md) | 파이썬 스크립트 17개 — 무엇을 재나 · 어떻게 돌리나 |

## 한눈에

```
ocaml/applic/                     ★ 필터 본체 (Coq 플러그인)
├── applic_main.ml                1,244줄 — 색인·판정·신호
├── applic.mlg                    tactic/vernac 선언
├── _CoqProject · findlib/        빌드 설정
└── (make → applic_plugin.cmxs)

scripts/
├── dn_rank_eval.py               ★ 필터 → 랭킹 → 프롬프트 (tactic 별 표)
├── applic_rank.py                ★ applic-idf · 비트합 · 나이브베이즈
├── dn_why.py                     gold 생존 진단 (사슬 단계별)
├── dn_verify.py                  실제 구문 실행으로 정밀도·위음성
├── dn_multi_eval.py              프로젝트를 넘어선 일반성 (VAL/TEST/CUTOFF)
├── channel_budget.py             물채우기 슬롯 배분 계산
├── inject_wf.py                  채널별 물채우기 주입기
├── why_rank_drop.py              필터 후 @10 이 왜 떨어지나
├── rw_analyze.py                 dn_why 결과를 tactic 별로
├── arrows_sweep.py               max_arrows 민감도
├── dn_eval.py                    전체 재현율 (rand200)
├── dn_sweep.py                   플러그인 설정 A/B
└── (구판) apply_verify_eval.py · coq_search_eval.py · search_demo.py
        · killer_query.py · applic_filter_eval.py

src/premise_selection/
├── coq_search_pool.py            검색 결과를 풀에 주입 (추론 경로)
├── coq_query.py                  Coq 내장 색인 질의 생성 (r1 이전 계열)
└── fingerprint.py                지문·판별·치환트리 (실패한 8판본)

src/tactic_gen/
└── normalize_config.py           익명화 설정 (파이썬 상수)
```

## 실행 순서

```
1. 플러그인 빌드
   cd ocaml/applic && export OCAMLPATH=$PWD/findlib:$OCAMLPATH && make

2. 필터 → 랭킹 → 프롬프트
   python3 scripts/dn_rank_eval.py          → all_log/dn_pool.jsonl · dn_rank.jsonl

3. 랭커 평가
   python3 scripts/applic_rank.py           → 신호별 변별력 · tactic 별 표

4. 일반성
   python3 scripts/dn_multi_eval.py VAL 25
   python3 scripts/dn_multi_eval.py TEST 20
```
