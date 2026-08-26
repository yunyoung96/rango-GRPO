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
    'NORMALIZE_INFERENCE'     : '1',
    # ★ 펑터 인스턴스 전개 — 아직 **실험 중**이라 기본값은 꺼짐.
    #   Module N := F(A). 로 생겨나는 N.member 를 검색 풀에 되살린다.
    #   근거·측정은 all_log/docs/premise/functor-names.md
    'FUNCTOR_EXPAND'          : '0',
    'FUNCTOR_EXPAND_MAX'      : '4000',
    'FUNCTOR_EXPAND_CONCRETE' : '1',   # 전개 시 elt/X.t 를 인자 모듈의 t 로 치환
    'OUT_TOKENS'              : '256',
    'NORMALIZE_LTAC'          : '1',
    'NORMALIZE_NAMES'         : '1',
    'NORMALIZE_PREMISES'      : '1',
    'NORMALIZE_RATE'          : '1.0',
    'NORMALIZE_SKIP_STDLIB'   : '1',
    'NORMALIZE_THEOREM'       : '1',
    'NOTATION_PROJ'           : '1',
    'NOTATION_PROJ_MAX'       : '20',
    'NOTATION_TOKENS'         : '220',
    'PREMISE_ADMIT_USED'      : '1',
    # ── ★ v10 (현행) — gold lemma 를 프롬프트에 **끼워 넣어** 조립을 가르친다 ──────
    #
    #   v9 의 assert(cut) 는 "이름을 모를 때 빠져나갈 구멍" 을 가르쳤다. 실측:
    #     · 생성 assert 의 명제 ↔ gold signature 겹침 **중앙 43%** (≥80% 가 15.8%)
    #       = 절반 가까이가 gold lemma 의 **재진술**이다
    #     · 그런데 `{ exact L }` 로 이어지는 것은 **18.3%** 뿐이고
    #       **54.2%** 가 `Proof.` 무의미 반복으로 샌다
    #     · `NO_ASSERT=1` A/B 는 무효과였다 (30.0% → 30.5%, b=0 c=1, p=1.000)
    #     · 오라클: 이름만 정해 주면 **70~74%** 조립. 같은 이름을 premise 에 꽂으면 13~34%
    #   → 못하는 것은 조립이 아니라 **고르기**다. 그러면 학습에서 할 일은
    #     "고를 것이 반드시 거기 있는" 예제를 주는 것이다.
    #   근거 전문: all_log/docs/v10/README.md
    #             all_log/docs/v9/checkpoint25000/assert_reality.md
    #
    #   ★ **여기가 v10 의 단일 출처다.** shell 로 export 하지 않는다 —
    #     `source` 를 잊으면 조용히 v9 로 도는데, 결과만 보고는 설정이 빠진 건지
    #     알고리즘이 나쁜 건지 구분할 수 없다(v9 에서 RERANK_PREMISES 로 겪었다).
    #   ※ v9 재현(절제 실험)은 env 로 덮어쓴다:
    #        V10_PREMISE_INJECT=0 CUT_SUBSTEP=1 python3 ...
    #   ※ 이 값들은 **학습 경로(`collate`)에서만** 읽힌다. 추론은 `collate_input` 이라
    #     평가에 새지 않는다(model_wrapper.py:293 과 같은 이유).
    'V10_PREMISE_INJECT'      : '1',   # 주입 ON (cut/assert 는 자동으로 꺼진다)
    'CUT_SUBSTEP'             : '0',   # ★ assert(cut) 안 씀 — v10 의 핵심
    'V10_INJECT_MAX'          : '3',   # 한 스텝에 끼워 넣을 gold 개수 상한
    'V10_INJECT_STATS'        : '0',   # 분기 통계를 주기적으로 찍는다
    'V10_DB_FALLBACK'         : '1',   # 계획이 없으면 sentence DB 로 선언문을 찾는다
    'V10_SENTENCE_DB'         : '/tmp/coq-dataset/sentences.db',
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
