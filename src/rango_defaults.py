"""★ **프로덕션 기본값의 단일 출처.** shell `export` 로 두지 않는다.

## 왜 파이썬인가

shell env 는 구조적으로 불안정하다 — `source` 를 잊거나, 다른 진입점으로 새거나,
한 스크립트가 덮어쓰면 **조용히 다른 설정으로 돈다.** 그러면 결과만 보고는
"설정이 빠진 것"인지 "방법이 나쁜 것"인지 구분할 수 없다.

실제로 두 번 당했다.
  · `RERANK_PREMISES` 파이썬 기본값이 "0" 인데 프로덕션은 "1" 이라, env 를 안 주면
    타입-지향 재랭킹이 통째로 꺼진 채 돌았다.
  · `NORMALIZE_INFERENCE=1` 을 전역 env 로 켜자 **학습 경로로 새어**, 프롬프트는
    `Lemma L##` 인데 정답은 실명으로 남아 어긋난 채 학습됐다(CompCert 결손 27 → 99).

그래서 값은 **여기가 유일한 출처**이고, env 는 **절제 실험용 덮어쓰기**로만 쓴다.

    RETRIEVAL_MODE=tfidf AUGMENT_V2=0 python3 scripts/...

## 쓰는 법

    from rango_defaults import get, flag, num, fnum
    if flag("AUGMENT_V2"): ...
    budget = num("TYPES_TOKENS")

★ **인자로 받는 쪽이 더 안전하다.** 진입점(모델 래퍼·평가 스크립트)은 가능한 한
  파이썬 인자로 받아 넘겨라 — `DecoderLocalWrapper(..., normalize_inference=True)`.
  이 표는 그 인자를 안 준 경우의 기본값이다.
"""
import os

# ── 프로덕션 기본값 (all_log/v9_env.sh 에서 옮겨 옴) ─────────────────────────
# ★ NORMALIZE_* 일곱 개는 여기서 **제거**했다.
#   `src/tactic_gen/normalize_config.py` 의 파이썬 상수로 옮겼다 —
#   문자열 env 는 `source` 를 잊거나 다른 진입점으로 새면 조용히
#   다른 설정으로 돈다(실제로 두 번 당했다). 악용할 여지를 없앤다.
PROD_DEFAULTS: dict[str, str] = {
    'ADMIT_MIN_FILES'         : '2',
    'AUGMENT_V2'              : '1',
    'CUTS_PATH'               : 'data/cut_plans_all.jsonl',
    'CUT_DROP_HOPELESS'       : '1',
    'DEFS_TOKENS'             : '300',
    'DP_CACHE_SIZE'           : '2048',
    'DROP_HALLUC'             : '1',
    'DYNAMIC_PADDING'         : '1',
    'FUNC_DEFS_PATH'          : 'data/func_defs_v3.json',
    'HARD_SEQ_LEN'            : '3072',
    'INJECT_DEFS'             : '1',
    'INJECT_NOTATION'         : '1',
    'INJECT_SKIP_STDLIB'      : '1',
    'INJECT_TYPES'            : '1',
    # ★ 펑터 인스턴스 전개 — 아직 **실험 중**이라 기본값은 꺼짐.
    #   Module N := F(A). 로 생겨나는 N.member 를 검색 풀에 되살린다.
    #   근거·측정은 all_log/docs/premise/functor-names.md
    'FUNCTOR_EXPAND'          : '0',
    'FUNCTOR_EXPAND_MAX'      : '4000',
    'FUNCTOR_EXPAND_CONCRETE' : '1',   # 전개 시 elt/X.t 를 인자 모듈의 t 로 치환
    'OUT_TOKENS'              : '256',
    'NOTATION_PROJ'           : '1',
    'NOTATION_PROJ_MAX'       : '20',
    'NOTATION_TOKENS'         : '220',
    'PREMISE_ADMIT_USED'      : '1',
    # ── ★ v10 (현행) — gold lemma 를 프롬프트에 **끼워 넣어** 조립을 가르친다 ──────
    #
    #   ★★ **v10 설정은 여기 없다.** `src/tactic_gen/v10_inject.py` 상단의
    #     **파이썬 변수**가 단일 출처다 (ENABLED · MAX_INJECT · REQUIRE_ALL · …).
    #     이 표는 env 이름 → 기본값 매핑이라 결국 shell 로 덮어쓸 수 있는데,
    #     그러면 `source` 를 잊었을 때 조용히 다른 설정으로 돈다.
    #     새 설정은 env 로 만들지 않는다.
    #
    #   근거: all_log/docs/v10/README.md
    #         all_log/docs/v9/checkpoint25000/assert_reality.md
    #   절제(v9 재현):  import tactic_gen.v10_inject as v10;  v10.ENABLED = False
    'PREMISE_PACK'            : 'hybrid',
    'PREMISE_PACK_TOPK'       : '4',
    'RERANK_PREMISES'         : '1',
    'RETRIEVAL_MODE'          : 'afh70',
    'RETRIEVAL_STAGE1'        : '5000',
    'STRIP_TARGET_NL'         : '1',
    'TFIDF_DOC_CACHE'         : '200000',
    'TYPES_TOKENS'            : '300',
    'UNFOLD_MAX'              : '6',
    'UNFOLD_SEEDS'            : '1',
}


def get(key: str, fallback: str = "") -> str:
    """설정값. env 가 있으면 그것, 없으면 프로덕션 기본값, 그것도 없으면 fallback."""
    v = os.environ.get(key)
    if v is not None and v != "":
        return v
    return PROD_DEFAULTS.get(key, fallback)


def flag(key: str) -> bool:
    return get(key, "0") == "1"


def num(key: str, fallback: int = 0) -> int:
    try:
        return int(get(key, str(fallback)))
    except ValueError:
        return fallback


def fnum(key: str, fallback: float = 0.0) -> float:
    try:
        return float(get(key, str(fallback)))
    except ValueError:
        return fallback
