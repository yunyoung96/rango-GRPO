# ★★ **v10 설정값은 `src/rango_defaults.py` 에 있다. 이 파일은 아무것도 export 하지 않는다.**
#
#   shell env 는 구조적으로 불안정하다 — `source` 를 잊거나, 다른 진입점으로 새거나,
#   한 스크립트가 덮어쓰면 조용히 다른 설정으로 돈다. v9 에서 두 번 당했다
#   (`RERANK_PREMISES` 가 꺼진 채 돌았고, `NORMALIZE_INFERENCE` 가 학습 경로로 샜다).
#   그래서 v9 도 전부 파이썬으로 옮겼고(위 v9_env.sh 의 `[파이썬으로 이관]` 주석),
#   v10 도 처음부터 파이썬에 둔다.
#
#   [파이썬으로 이관] export V10_PREMISE_INJECT=1   # gold 를 premise 창 안에 끼운다
#   [파이썬으로 이관] export CUT_SUBSTEP=0          # assert(cut) 는 쓰지 않는다 — v10 의 핵심
#   [파이썬으로 이관] export V10_INJECT_MAX=3       # 한 스텝 최대 3개
#   [파이썬으로 이관] export V10_DB_FALLBACK=1      # 계획이 없으면 sentence DB 로 선언문 조회
#
#   값을 바꾸려면 `src/rango_defaults.py` 의 PROD_DEFAULTS 를 고친다.
#   절제 실험(= v9 재현)은 env 로 덮어쓴다:
#       V10_PREMISE_INJECT=0 CUT_SUBSTEP=1 python3 src/tactic_gen/train_decoder.py …
#
#   사용:  source all_log/v10_env.sh
#          python3 src/tactic_gen/train_decoder.py all_log/ft_qwen3b_v10_conf.yaml
#
#   ※ v9_env.sh 는 PYTHONPATH·HF_HUB_OFFLINE 등 **환경 자체**만 세팅한다(설정값 아님).
source "$(dirname "${BASH_SOURCE[0]}")/v9_env.sh"
