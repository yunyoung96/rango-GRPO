# ★★ **설정값은 `src/rango_defaults.py` 로 옮겼다.**
#
#   shell env 는 구조적으로 불안정하다 — `source` 를 잊거나, 다른 진입점으로 새거나,
#   한 스크립트가 덮어쓰면 조용히 다른 설정으로 돈다. 실제로 두 번 당했다
#   (`RERANK_PREMISES` 가 꺼진 채 돌았고, `NORMALIZE_INFERENCE` 가 학습 경로로 샜다).
#
#   아래 `[파이썬으로 이관]` 줄은 **근거 기록용 주석**이며 더 이상 적용되지 않는다.
#   값을 바꾸려면 `src/rango_defaults.py` 의 PROD_DEFAULTS 를 고친다.
#   절제 실험은 env 로 덮어쓴다:  RETRIEVAL_MODE=tfidf AUGMENT_V2=0 python3 ...
#
#   검증: scripts/verify_defaults_equiv.py — env 없이도 같은 프롬프트 (120/120 동일)
#
#!/bin/bash
# v9 환경변수 — **단일 출처**.
#
# ★ 이 파일이 있는 이유: 예전에는 학습 런처와 검증 스크립트가 각자 환경변수를 나열했다.
#   그러면 검증은 A 설정으로 통과하고 학습은 B 설정으로 도는 일이 생긴다
#   (실제로 INJECT_TYPES / FUNC_DEFS_PATH / NORMALIZE_PREMISES 가 검증 쪽에만 빠져 있었다).
#   "검증한 것과 학습하는 것이 같다"를 보장하려면 출처가 하나여야 한다.
#
#   사용:  source all_log/v9_env.sh
export PYTHONPATH=src
export HF_HUB_OFFLINE=1
export TOKENIZERS_PARALLELISM=false

# ── v8 에서 그대로 가져온 것 ──────────────────────────────
# [파이썬으로 이관] export AUGMENT_V2=1 INJECT_TYPES=1 INJECT_DEFS=1 DYNAMIC_PADDING=1
#  ※ RERANK_PREMISES 는 파이썬 기본값(_PROD_DEFAULTS)으로 옮겼다 — 여기서 안 준다.
# [파이썬으로 이관] export HARD_SEQ_LEN=2048 TYPES_TOKENS=300 DEFS_TOKENS=300
#  ★ 400/600 으로 올려 봤다가 **되돌렸다** (2026-08-22):
#    환각률 17.6% → 17.6% 로 **전혀 안 내려가는데** premise 만 14.4 → 13.5 (−0.9)
#    잃었다. 예산이 병목이 아니었다. 병목이 무엇인지는 probe_seed_reach 로 판정한다.
#  ↑ 300/300 → 400/600 (2026-08-22). 근거:
#    · 프롬프트 중앙이 1,118토큰 / 상한 2,048 — 여유 ~930 을 실측했다
#    · 주입이 premise 를 **안 밀어낸다**는 것도 실측했다(rango 대비 14.3 → 14.3).
#      augment_v2_section 이 `room` 을 계산해 자기 블록만 자르기 때문이다.
#    · 남은 환각(17.6%)이 전부 **풀에서 제외된 종류**(Definition·Constructor·
#      Field)이고 주입이 유일한 통로인데, 씨앗 8.2개/예제 중 2~5개만 들어가고
#      있었다 — 예산이 묶고 있었다.
# [파이썬으로 이관] export FUNC_DEFS_PATH=data/func_defs_v3.json
# ★ NORMALIZE_RATE=1.0 — 예제를 **전부** 정규화한다.
#   목적이 "이름 암기 차단 → 미지 프로젝트로 전이"이므로 절반만 정규화하면
#   나머지 절반에서 여전히 이름을 외울 수 있다. 근거 없이 0.5 를 쓰고 있었다.
#   ※ 일관성: 추론에서도 정규화해야 train/test 가 어긋나지 않는다.
#     ★ 그래서 **여기서 켠다**(아래 NORMALIZE_INFERENCE). 주석으로만 남겨 뒀더니
#       실제로는 꺼진 채였다 — 평가 때 실명 프롬프트를 넣게 되어 학습과 어긋난다.
#       추론 경로는 `collate_input`, 학습은 `collate` 로 분리돼 있어 학습에는 영향 없다.
# [파이썬으로 이관] export NORMALIZE_NAMES=1 NORMALIZE_RATE=1.0 NORMALIZE_PREMISES=1 NORMALIZE_THEOREM=1
# [파이썬으로 이관] export STRIP_TARGET_NL=1
export PYTORCH_ALLOC_CONF=expandable_segments:True

# ── v9 에서 새로 넣은 것 (근거: docs/premise/final.md §10) ──
# ★ 랭커와 stage1 은 **파이썬 상수가 단일 출처**다. 여기서 export 하지 않는다 —
#   `source` 를 잊으면 조용히 다른 랭커로 돌아가는데, 결과만 보고는 설정이 빠진 건지
#   랭커가 나쁜 건지 구분할 수 없다(오늘 NORMALIZE_INFERENCE 로 같은 사고를 겪었다).
#       premise_client.DEFAULT_RETRIEVAL_MODE = "afh70"
#       tier_rank.STAGE1                      = 5000
#   절제 실험에서만 덮어쓴다:  RETRIEVAL_MODE=tfidf python3 ...
#
#   afh70 근거 (CompCert TEST 1,200스텝 · 이름 개명 조건)
#       A·프롬프트 ALL   tfidf 30.2% → 42.0%      합성 ALL·P  90.1% → 97.2%
#   비용 (CompCert 40파일 147스텝 · 캐시 워밍 후)
#       검색 14.5ms → 25.0ms · 노드 300ms 대비 4.6% → 7.7%
#  ※ PREMISE_PACK · PREMISE_PACK_TOPK 도 파이썬 기본값으로 옮겼다
#    (tactic_data._PROD_DEFAULTS). 절제 실험에서만 env 로 덮어쓴다.
# [파이썬으로 이관] export NORMALIZE_SKIP_STDLIB=1         # stdlib 이름은 정규화 안 함
# [파이썬으로 이관] export INJECT_SKIP_STDLIB=1            # stdlib 정의는 주입 안 함
# [파이썬으로 이관] export CUTS_PATH=data/cut_plans_all.jsonl  # ★ 검색-독립 cut **계획** (TRAIN+VAL)
#  ↑ 옛 `data/cuts_train.jsonl` 은 랭커에 의존해 구워진 것이라 랭커를 바꾸면 무효다.
#    계획 파일은 검색과 무관하게 만들어지고, cut 을 넣을지는 **학습 시점에** 프롬프트를
#    보고 결정한다(cut_lookup.plan_for). 진단 스크립트도 전부 이 파일을 봐야 한다 —
#    옛 파일로 재면 하위스텝이 적용 안 된 수치가 나온다(U1 오측정의 원인이었다).

# ── ★ 환각 제거 ──────────────────────────────────────────
#  가망 없는 스텝(gold 가 풀에도 없고 cut 도 못 세움)은 **학습에서 뺀다.**
#  그런 스텝의 정답은 프롬프트에 없는 이름을 쓰므로, 학습에 넣으면 모델에게
#  "볼 수 없는 이름을 지어내라"고 가르치는 셈이다. 정규화만 끄는 것으로는
#  부족하다 — 이름을 외우게 하는 것 자체가 문제다.
#  실측 제외율: gold lemma 사용 스텝의 28.3% = 전체 예제의 6.7%
# [파이썬으로 이관] export CUT_DROP_HOPELESS=1

# ── 유사 증명 검색 속도 (speed.md) ────────────────────────
#  비용이 극단적으로 치우쳐 있다 — 예제 중앙값 0.54초인데 최대 280초였고,
#  그 한 건이 표본 전체 시간의 85% 였다. 의존이 많은 파일은 후보 문서가 수만 개다.
#  원래 캐시(10,000)가 문서 수보다 작아 매 예제마다 통째로 밀렸다(적중률 0).
# [파이썬으로 이관] export TFIDF_DOC_CACHE=200000    # tf/idf 문서 캐시 (항목이 작은 dict 라 수백 MB 수준)
# [파이썬으로 이관] export DP_CACHE_SIZE=2048        # data_point LRU (의존 파일을 오래 들고 있는다)

# ── 환각 감소: 이름이 프롬프트에 없어서 생기는 결손 (§27·§28) ────────────────
#  실측 효과는 -1.0pp 로 작다(15.3% → 14.3%). 다만 **비용이 중앙 0토큰**이라
#  손해가 없어 켜 둔다. 남은 14.3% 는 프롬프트 구성으로는 못 고친다 —
#  결손 이름의 79% 가 검색 100개 안에 아예 없고 순위 중앙값이 70위다(§28-2).
# [파이썬으로 이관] export INJECT_NOTATION=1         # 파일 내 notation (중앙 0개 · p90 552토큰)
# [파이썬으로 이관] export NOTATION_TOKENS=220
# [파이썬으로 이관] export NOTATION_PROJ=1           # 프로젝트 notation 을 goal 기호로 앵커링 (p90 39토큰)
# [파이썬으로 이관] export NOTATION_PROJ_MAX=20
# [파이썬으로 이관] export UNFOLD_SEEDS=1            # goal 에 정의 **본문**이 보일 때 이름 되찾기 (p90 1개)
# [파이썬으로 이관] export UNFOLD_MAX=6
# [파이썬으로 이관] export PREMISE_ADMIT_USED=1      # 제외 종류라도 tactic 인자로 쓰인 것은 풀에 되살린다
# [파이썬으로 이관] export ADMIT_MIN_FILES=2         # ★ 누출 방지 — 평가 대상 파일 자신만으로는 승격 불가
# ★ 파일 내 Ltac 이름도 익명화한다 — 프로젝트 Ltac 실명 선호가 **61.5%(4.6σ)** 로
#   프로젝트 Lemma(61.8%) 와 사실상 같다. 막을 지름길이 실재하고, 익명화하면
#   `[LTAC]` 섹션이 그 이름의 **유일한 경로**가 되어 실제로 읽힌다 (§27-4).
#   접두사는 K (lemma=L · 타입=T · 생성자=C · 함수=f · 정리=G 와 구분).
# [파이썬으로 이관] export NORMALIZE_LTAC=1
# notation 이 가린 이름은 회상 53.5%(우연 수준)라 **익명화 대상이 아니다** — 막을 게
# 없는데 "뜻 있는 이름" 신호만 잃는 순손실이다.

# ── 환각 예제는 **학습에서 제외** (2026-08-23 지시) ─────────────────────────
#  정답이 프롬프트에 없는 이름을 쓰는 예제는 모델에게 *볼 수 없는 이름을 지어내라* 고
#  가르치는 것이라 학습 가치가 없다. 실측: 환각률 1.00% → 0.00%.
#  대가는 학습 데이터 약 2.4% 다 (hopeless 제외 6.6% · 2048 초과 8.5% 와 같은 급).
# [파이썬으로 이관] export DROP_HALLUC=1

# ── 평가(추론) 정규화 ─────────────────────────────────────────────────────
#  모델은 `L0`·`T2`·`K1` 기준으로 학습됐으므로 **프롬프트도 같은 형태로** 넣어야 한다.
#  생성된 tactic 은 `model_wrapper` 가 `apply_inverse` 로 **자동 역매핑**한다 —
#  Coq 은 `L0` 를 모르기 때문이다. 매핑에 없는 이름(모델이 지어낸 것)은 그대로 둬서
#  Coq 에서 실패하게 한다(조용히 바꾸면 환각을 숨기게 된다).
#  ★ 이 값은 **추론 프로세스에서만** 읽힌다(model_wrapper 의 기본값). 학습 경로는
#    파이썬 인자로만 켜지므로 여기 값이 학습에 새지 않는다.
#    더 안전하게는 평가 설정에 {"normalize_inference": true} 를 주거나
#    DecoderLocalWrapper.from_checkpoint(..., normalize_inference=True) 를 쓴다.
#    체크포인트의 학습 설정에 normalize_names 가 있으면 **자동으로 따라간다.**
# [파이썬으로 이관] export NORMALIZE_INFERENCE=1
