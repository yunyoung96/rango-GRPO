"""★ 미리 만들어 둔 cut 을 **조회만** 한다 — 학습 머신에 Coq 이 없어도 되게.

## 용어

  · **cut**  증명에서 보조 명제를 세워 쓰는 것. Coq 에서는 `assert (P) as H`.
             논리학의 cut rule 과 같다.
  · **collate**  학습 예제 하나를 (프롬프트 + 정답) 한 문자열로 조립하는 단계.

## 왜 조회만 하나

cut 의 명제를 정확히 얻으려면 그 증명 지점에서 Coq 에 `Check (L a b).` 를 물어야 한다.
학습 머신(Vast.ai)에는 Coq 도 원본 `.v` 13G 도 없다. 그래서 **데이터 준비 머신에서**
`scripts/build_cuts.py` 로 만들어 jsonl 로 넘기고, 여기서는 사전 조회만 한다.

## 파일 형식

    {"kind":"stmt", "name":"Nat.add_comm", "ty":"forall n m : nat, n + m = m + n"}
    {"kind":"step", "sid":"파일#증명#스텝", "miss":["Nat.add_comm"], "cut":"assert (…) …"}

같은 lemma 가 여러 스텝에서 빠지면 명제가 같으므로 **사전 하나 + 스텝별 목록**으로
정규화한다(실측 TRAIN: cut 168,000개 · 파일 28MB).

사용: 환경변수 `CUTS_PATH=data/cuts_train.jsonl` 이 있으면 collate 가 자동으로 쓴다.
"""
from __future__ import annotations

import json
import os
import threading

_lock = threading.Lock()
_loaded = False
_steps: dict[str, dict] = {}
# ★ 계획(plan) — **검색과 무관한 재료**만 담는다.
#     {"sid": …, "tac": 원래 tactic, "lem": [[이름, statement], …],
#      "fn": [함수·타입 이름 …], "cut": 전부 assert 한 조립본}
#   옛 형식(`step` 의 `cut` 문자열)은 생성 시점의 검색 결과에 묶여 있어서,
#   검색 정책을 바꾸면 전제가 틀린 산출물이 된다. 계획은 그렇지 않다.
_plans: dict[str, dict] = {}
_stmts: dict[str, str] = {}
_stat = {"조회": 0, "적중": 0, "미적중": 0}
_meta: list = []


def load(path: str | None = None) -> bool:
    """jsonl 을 한 번만 읽는다. 파일이 없으면 조용히 비활성(학습이 죽으면 안 된다)."""
    global _loaded
    if _loaded:
        return bool(_steps)
    with _lock:
        if _loaded:
            return bool(_steps)
        p = path or os.environ.get("CUTS_PATH", "")
        _loaded = True
        if not p or not os.path.exists(p):
            return False
        with open(p) as f:
            for line in f:
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if d.get("kind") == "step":
                    _steps[d["sid"]] = d
                elif d.get("kind") == "plan":
                    _plans[d["sid"]] = d
                elif d.get("kind") == "stmt":
                    _stmts[d["name"]] = d["ty"]
                elif d.get("kind") == "meta":
                    # ★ 이 파일이 덮는 인덱스 범위. 여러 샤드를 병합하면 여러 개가 온다.
                    _meta.append(d)
        return bool(_steps or _plans)


def plan_for(sid: str):
    """이 스텝의 cut **계획**. 없으면 None.

    ★ 계획은 "무엇을 assert 할 수 있는가" 라는 **사실**이지 "assert 할 것인가" 라는
      **결정**이 아니다. 결정은 학습 시점에 완성된 프롬프트를 보고 내린다
      (`tactic_data.collate` ①-b) — 그래야 검색 정책을 바꿔도 계획이 유효하다.
    """
    if not load():
        return None
    return _plans.get(sid)


def enabled() -> bool:
    return load()


def stmt_of(name: str) -> str | None:
    load()
    return _stmts.get(name)


def cut_for(sid: str) -> str | None:
    """그 스텝의 **cut 으로 치환된 tactic**. 없으면 None(원래 gold tactic 을 쓴다)."""
    if not load():
        return None
    _stat["조회"] += 1
    d = _steps.get(sid)
    if d is None or not d.get("cut"):
        _stat["미적중"] += 1
        return None
    _stat["적중"] += 1
    return d["cut"]


def is_hopeless(sid: str) -> bool:
    """그 스텝이 **어떻게 해도 프롬프트에서 읽을 수 없는 이름**을 쓰는가.

    ★ how-to-learn.txt §3 의 (3): gold lemma 가 검색에도 없고 cut 으로도 못 건진 경우.
      이때는 **정규화를 끄는 편이 낫다.** 정규화하면 정답이 `L92` 같은 프롬프트에 없는
      무의미 토큰이 되어 모델이 **틀린 답을 외운다**. 진짜 이름은 최소한 의미 힌트
      (`add_comm` → 교환법칙)라도 남아 goal 모양에서 유추할 여지가 있다.
    """
    if not load():
        return False
    d = _steps.get(sid)
    return bool(d and d.get("hopeless"))


def scanned_range() -> tuple:
    """이 cut 파일이 실제로 훑은 **연속** 인덱스 범위 [start, end).

    ★ 없으면 (0, 0) — **범위를 모른다**는 뜻이고, 그건 곧 커버리지를 보장할 수
      없다는 뜻이다. 학습 전 가드가 이 값을 보고 막는다.

    ★★ 반드시 **연속**이어야 한다. 예전 구현은 `(min(start), max(end))` 를 돌려줬는데,
      cut 파일은 청크 81개를 이어붙여 만든다. 가운데 청크 하나가 빠져도 min/max 는
      전 구간을 커버한다고 답한다 — 가드가 통과하고, 그 구멍 구간의 스텝은 cut 치환도
      CUT_DROP_HOPELESS 도 조용히 안 걸린다. 정확히 우리가 한 번 당한 사고다.
      그래서 구간을 정렬해 **첫 구멍에서 끊고** 거기까지만 보장한다.
    """
    load()
    if not _meta:
        return (0, 0)
    iv = sorted((int(m.get("scan_start", 0)), int(m.get("scan_end", 0)))
                for m in _meta)
    start = iv[0][0]
    end = iv[0][1]
    for a, b in iv[1:]:
        if a > end:                 # 구멍 — 여기서 끊는다
            break
        end = max(end, b)
    return (start, end)


def stats() -> dict:
    return dict(_stat, 스텝수=len(_steps), 계획수=len(_plans), 명제수=len(_stmts))
