# ★★ **v10 설정은 파이썬 변수다. 이 파일은 아무것도 export 하지 않는다.**
#
#   단일 출처:  src/tactic_gen/v10_inject.py 상단
#       ENABLED      = True    # v10 주입을 켠다 (끄면 cut/assert 경로가 살아난다)
#       MAX_INJECT   = 0       # 한 스텝에 끼울 gold 개수 상한. 0 = 무제한
#       REQUIRE_ALL  = True    # 하나라도 못 넣으면 그 예제를 버린다
#       DB_FALLBACK  = True    # 계획이 없으면 sentence DB 로 선언문 조회
#
#   shell env 는 구조적으로 불안정하다 — `source` 를 잊거나, 다른 진입점으로 새거나,
#   한 스크립트가 덮어쓰면 조용히 다른 설정으로 돈다. v9 에서 두 번 당했다
#   (`RERANK_PREMISES` 가 꺼진 채 돌았고, `NORMALIZE_INFERENCE` 가 학습 경로로 샜다).
#   결과만 보고는 설정이 빠진 건지 알고리즘이 나쁜 건지 구분할 수 없다 — 그게 최악이다.
#
#   절제 실험(= v9 재현)은 **파이썬에서** 한다:
#       import tactic_gen.v10_inject as v10
#       v10.ENABLED = False
#
#   사용:  source all_log/v10_env.sh          # PYTHONPATH 등 환경만 세팅
#          python3 src/tactic_gen/train_decoder.py all_log/ft_qwen3b_v10_conf.yaml
#
#   ※ v9_env.sh 는 PYTHONPATH·HF_HUB_OFFLINE 등 **환경 자체**만 세팅한다(설정값 아님).
source "$(dirname "${BASH_SOURCE[0]}")/v9_env.sh"
