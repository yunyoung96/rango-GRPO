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
export NORMALIZE_NAMES=1 NORMALIZE_RATE=0.5 NORMALIZE_PREMISES=1 NORMALIZE_THEOREM=1
export STRIP_TARGET_NL=1
export PYTORCH_ALLOC_CONF=expandable_segments:True

# ── v9 에서 새로 넣은 것 (근거: docs/premise/final.md §10) ──
export RETRIEVAL_MODE=structural       # 랭커
export RETRIEVAL_STAGE1=5000           # 1단계 후보 수
export PREMISE_PACK=hybrid             # 담기
export PREMISE_PACK_TOPK=4             # 상위 K 는 무조건
export NORMALIZE_SKIP_STDLIB=1         # stdlib 이름은 정규화 안 함
export INJECT_SKIP_STDLIB=1            # stdlib 정의는 주입 안 함
export CUTS_PATH=data/cuts_train.jsonl # 미리 만든 cut
