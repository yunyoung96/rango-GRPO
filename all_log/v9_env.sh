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
export AUGMENT_V2=1 RERANK_PREMISES=1 INJECT_TYPES=1 INJECT_DEFS=1 DYNAMIC_PADDING=1
export HARD_SEQ_LEN=2048 TYPES_TOKENS=300 DEFS_TOKENS=300
export FUNC_DEFS_PATH=data/func_defs_v3.json
# ★ NORMALIZE_RATE=1.0 — 예제를 **전부** 정규화한다.
#   목적이 "이름 암기 차단 → 미지 프로젝트로 전이"이므로 절반만 정규화하면
#   나머지 절반에서 여전히 이름을 외울 수 있다. 근거 없이 0.5 를 쓰고 있었다.
#   ※ 일관성: 추론에서도 정규화해야 train/test 가 어긋나지 않는다.
#     역매핑은 구현돼 있다 — 평가 때 NORMALIZE_INFERENCE=1 을 켤 것.
export NORMALIZE_NAMES=1 NORMALIZE_RATE=1.0 NORMALIZE_PREMISES=1 NORMALIZE_THEOREM=1
export STRIP_TARGET_NL=1
export PYTORCH_ALLOC_CONF=expandable_segments:True

# ── v9 에서 새로 넣은 것 (근거: docs/premise/final.md §10) ──
export RETRIEVAL_MODE=eqx       # 랭커
export RETRIEVAL_STAGE1=5000           # 1단계 후보 수
export PREMISE_PACK=hybrid             # 담기
export PREMISE_PACK_TOPK=4             # 상위 K 는 무조건
export NORMALIZE_SKIP_STDLIB=1         # stdlib 이름은 정규화 안 함
export INJECT_SKIP_STDLIB=1            # stdlib 정의는 주입 안 함
export CUTS_PATH=data/cuts_train.jsonl # 미리 만든 cut

# ── ★ 환각 제거 ──────────────────────────────────────────
#  가망 없는 스텝(gold 가 풀에도 없고 cut 도 못 세움)은 **학습에서 뺀다.**
#  그런 스텝의 정답은 프롬프트에 없는 이름을 쓰므로, 학습에 넣으면 모델에게
#  "볼 수 없는 이름을 지어내라"고 가르치는 셈이다. 정규화만 끄는 것으로는
#  부족하다 — 이름을 외우게 하는 것 자체가 문제다.
#  실측 제외율: gold lemma 사용 스텝의 28.3% = 전체 예제의 6.7%
export CUT_DROP_HOPELESS=1

# ── 유사 증명 검색 속도 (speed.md) ────────────────────────
#  비용이 극단적으로 치우쳐 있다 — 예제 중앙값 0.54초인데 최대 280초였고,
#  그 한 건이 표본 전체 시간의 85% 였다. 의존이 많은 파일은 후보 문서가 수만 개다.
#  원래 캐시(10,000)가 문서 수보다 작아 매 예제마다 통째로 밀렸다(적중률 0).
export TFIDF_DOC_CACHE=200000    # tf/idf 문서 캐시 (항목이 작은 dict 라 수백 MB 수준)
export DP_CACHE_SIZE=2048        # data_point LRU (의존 파일을 오래 들고 있는다)
