"""진단 스크립트가 **학습과 같은 설정**을 쓰도록 `all_log/v9_env.sh` 를 읽어 적용한다.

## 왜 필요한가

값을 스크립트마다 하드코딩하면 **반드시 어긋난다.** 하루에 두 번 겪었다:

  · `v9_env.sh` 는 옛 `CUTS_PATH=data/cuts_train.jsonl` 을 가리키고 있었고,
    `scan_prompts.py` 가 그걸 읽어 **폐기된 cut** 으로 U1 을 쟀다 (12건이 나왔다).
  · `audit_train_path.py` · `section_budget.py` 는 `RETRIEVAL_MODE="structural"` 을
    기본값으로 박아 두고 "학습과 같은 설정으로 태운다"고 주석에 적어 두었다.
    학습은 `eqx` 였다.

둘 다 **오류를 내지 않는다** — 조용히 다른 실험을 재고, 그 숫자가 보고서에 들어간다.
그래서 설정의 출처를 하나로 못박는다: `all_log/v9_env.sh`.

## 쓰는 법

    import sys; sys.path.insert(0, "scripts")
    from _env_from_v9 import apply_v9_env
    apply_v9_env()                    # os.environ 에 setdefault 로 채운다

이미 셸에서 `source all_log/v9_env.sh` 를 했다면 아무것도 덮어쓰지 않는다
(setdefault 이므로). 안 했다면 여기서 같은 값이 들어간다.
"""
import os
import re
from pathlib import Path

V9 = Path(__file__).resolve().parent.parent / "all_log" / "v9_env.sh"
_EXPORT = re.compile(r"^\s*export\s+(.*)$")
# ★ `export A=1 B=1 C=1` 처럼 **한 줄에 여러 대입**이 온다. 줄 전체를 값으로 잡으면
#   `HARD_SEQ_LEN=2048 TYPES_TOKENS=300 …` 이 통째로 HARD_SEQ_LEN 의 값이 되어
#   `int(os.environ["HARD_SEQ_LEN"])` 가 터진다. 토큰 단위로 쪼갠다.
_ASSIGN = re.compile(r"^([A-Z_][A-Z0-9_]*)=(.*)$")


def read_v9_env(path=V9) -> dict:
    """`export K=V [K=V ...]` 을 뽑는다. 주석·따옴표를 벗기고 셸 확장은 하지 않는다."""
    out = {}
    try:
        text = Path(path).read_text()
    except Exception:
        return out
    for line in text.splitlines():
        m = _EXPORT.match(line)
        if not m:
            continue
        rest = m.group(1)
        # 줄 끝 주석 제거 — 따옴표가 없을 때만 (따옴표 안의 # 는 값이다)
        if '"' not in rest and "'" not in rest:
            rest = rest.split("#", 1)[0]
        try:
            import shlex
            toks = shlex.split(rest, comments=False)
        except ValueError:
            toks = rest.split()
        for tok in toks:
            a = _ASSIGN.match(tok)
            if not a:
                continue
            k, v = a.group(1), a.group(2).strip().strip('"').strip("'")
            if "$" in v:        # 셸 확장이 필요한 값은 넘긴다
                continue
            out[k] = v
    return out


def apply_v9_env(path=V9, verbose=False) -> dict:
    env = read_v9_env(path)
    applied = {}
    for k, v in env.items():
        if k not in os.environ:
            os.environ[k] = v
            applied[k] = v
    if verbose and applied:
        print(f"   [v9_env] {len(applied)}개 적용: "
              + " ".join(f"{k}={v}" for k, v in sorted(applied.items())[:6])
              + (" …" if len(applied) > 6 else ""))
    return env


if __name__ == "__main__":
    import sys
    e = read_v9_env()
    print(f"■ {V9} 에서 읽은 설정 {len(e)}개\n")
    for k, v in sorted(e.items()):
        print(f"   {k:26s} {v}")
    # 핵심 값이 비면 배선이 끊긴 것이다
    need = ["RETRIEVAL_MODE", "CUTS_PATH", "HARD_SEQ_LEN"]
    miss = [k for k in need if not e.get(k)]
    print()
    if miss:
        print("★ 필수 값 없음:", miss)
        sys.exit(1)
    print("✓ 필수 값 확인")
