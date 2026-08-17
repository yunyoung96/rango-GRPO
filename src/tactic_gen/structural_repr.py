"""**프로젝트 무관 구조 표현** — goal·premise 를 닫힌 어휘로 익명화한다.

## 왜

지금 검색이 이기는 신호에는 이름이 섞여 있다(`Zlt_le_succ` 를 `Zlt`·`le`·`succ` 로 쪼개는
subword). 이건 **그 라이브러리의 작명 관례**라 새 프로젝트로 전이하지 않고, v8 익명화
프롬프트에서는 모델이 볼 수도 없다.

## 핵심 아이디어 — 정렬(alignment) 기반 익명화

이름을 지우되 **"goal 과 premise 에 무엇이 함께 나오는가"** 는 남긴다.

    goal    : le (succ zero) a           premise : forall n m, lt n m -> le (succ n) m

    공유 상수 le→S0, succ→S1  (빈도 내림차순, 결정적)
    goal 고유 zero→G, 지역변수 a→V
    premise 고유 lt→P, 메타변수 n m→M

    goal 결론    : ( S0 ( S1 G ) V )
    premise 결론 : ( S0 ( S1 M ) M )      ← 구조가 맞물리는 게 이름 없이 보인다

**어휘가 닫힌다**: {S0..S9, S+, G, P, V, M, NUM} + 연산자(canon 으로 정규화) + 괄호.
50개 남짓이고 프로젝트 고유 이름이 하나도 없다. 그래서 TRAIN 에서 배운 것이 VAL/TEST 의
처음 보는 프로젝트에도 그대로 적용된다.

## 역할 구분 (goal+hypothesis 전용)

가설과 결론은 **하는 일이 다르다**.

  · goal 결론  = 증명할 것   ↔ premise 결론 = 제공하는 것   (apply 로 맞물린다)
  · goal 가설  = 이미 가진 것 ↔ premise 가설 = 요구하는 것   (충족되면 subgoal 이 준다)

그래서 네 자리에 **역할 토큰**을 붙여 모델이 "결론끼리·가설끼리" 를 구분해 배우게 한다.

    [GH] …가설… [GC] …결론… [SEP] [PH] …가설… [PC] …결론…

## 쓰는 법

    pair_tokens(goal_state, premise_text)  → (토큰 리스트, 통계)
    VOCAB                                   → 닫힌 어휘 (학습 임베딩 테이블 크기)
"""
from __future__ import annotations

import collections
import re
from typing import Optional

from tactic_gen.applicable import (canon, decompose, goal_conclusion, parse,
                                   parse_toks, _INFIX)

# ── 닫힌 어휘 ────────────────────────────────────────────────────────────────
N_SHARED = 10                       # 공유 상수에 줄 고유 슬롯 수 (나머지는 S+)
ROLE = ["[GH]", "[GC]", "[PH]", "[PC]", "[SEP]", "[CLS]"]
SPECIAL = ["(", ")", "V", "M", "NUM", "G", "P", "S+", "OPQ"]
SHARED = [f"S{i}" for i in range(N_SHARED)]
OPS = sorted(set(_INFIX.keys()) | {"impl", "eq", "iff", "and", "or", "not"})
VOCAB = ROLE + SPECIAL + SHARED + OPS
VOCAB_INDEX = {t: i for i, t in enumerate(VOCAB)}

_NUM = re.compile(r"^\d+$")


def _consts(t, out=None):
    """트리에 나오는 **식별자**(연산자 아님) 를 센다. 지역/메타 판정은 호출부에서."""
    if out is None:
        out = collections.Counter()
    if t is None:
        return out
    if t[0] == "id":
        out[t[1]] += 1
    elif t[0] == "app":
        _consts(t[1], out)
        _consts(t[2], out)
    elif t[0] == "op":
        _consts(t[2], out)
        _consts(t[3], out)
    return out


def _emit(t, sym, out):
    """트리를 전위 순회로 선형화. 괄호로 구조를 보존한다."""
    if t is None:
        out.append("OPQ")
        return
    k = t[0]
    if k == "opq":
        out.append("OPQ")
    elif k == "id":
        out.append(sym(t[1]))
    elif k == "app":
        out.append("(")
        _emit(t[1], sym, out)
        _emit(t[2], sym, out)
        out.append(")")
    elif k == "op":
        out.append("(")
        out.append(t[1] if t[1] in VOCAB_INDEX else "S+")
        _emit(t[2], sym, out)
        _emit(t[3], sym, out)
        out.append(")")
    else:
        out.append("OPQ")


def _goal_parts(state: str):
    """goal → (가설 트리들, 결론 트리, 지역이름). 전부 canon 정규형."""
    body = (state or "").split("[GOAL]")[0]
    parts = re.split(r"\n\s*\n", body)
    hyps, locs = [], set()
    if len(parts) > 1:
        for ln in parts[0].split("\n"):
            seg = ln.split(":", 1)
            if len(seg) != 2:
                continue
            locs |= {x.strip() for x in seg[0].split(",") if x.strip()}
            ht = parse(seg[1])
            if ht is not None:
                hyps.append(canon(ht))
    c = parse(goal_conclusion(state))
    return hyps, (canon(c) if c is not None else None), locs


def _prem_parts(text: str):
    """premise → (가설 트리들, 결론 트리, 메타변수). 전부 canon 정규형."""
    d = decompose(text)
    if d is None:
        return [], None, set()
    mv, hyp_toks, concl_toks = d
    hyps = []
    for h in hyp_toks:
        ht = parse_toks(h)
        if ht is not None:
            hyps.append(canon(ht))
    c = parse_toks(concl_toks)
    return hyps, (canon(c) if c is not None else None), set(mv)


def pair_tokens(goal_state: str, premise_text: str,
                max_len: int = 256) -> tuple[list[str], dict]:
    """(goal, premise) → **닫힌 어휘의 토큰 리스트**.

    공유 상수는 goal·premise 양쪽 등장 빈도 합 내림차순으로 S0..S9 를 받는다(결정적).
    같은 이름이라도 **쌍이 달라지면 다른 슬롯**을 받을 수 있는데, 그게 의도다 — 절대
    이름이 아니라 **상대적 겹침**만 남기는 것이 전이의 조건이다.
    """
    gh, gc, glocs = _goal_parts(goal_state)
    ph, pc, pmv = _prem_parts(premise_text)

    gcnt = collections.Counter()
    for t in gh + ([gc] if gc is not None else []):
        _consts(t, gcnt)
    pcnt = collections.Counter()
    for t in ph + ([pc] if pc is not None else []):
        _consts(t, pcnt)

    # 지역변수·메타변수는 상수가 아니므로 공유 판정에서 뺀다
    g_const = {k: v for k, v in gcnt.items() if k not in glocs and not _NUM.match(k)}
    p_const = {k: v for k, v in pcnt.items() if k not in pmv and not _NUM.match(k)}
    shared = set(g_const) & set(p_const)
    order = sorted(shared, key=lambda k: (-(g_const[k] + p_const[k]), k))
    slot = {k: f"S{i}" if i < N_SHARED else "S+" for i, k in enumerate(order)}

    def gsym(name: str) -> str:
        if _NUM.match(name):
            return "NUM"
        if name in glocs:
            return "V"
        return slot.get(name, "G")

    def psym(name: str) -> str:
        if _NUM.match(name):
            return "NUM"
        if name in pmv:
            return "M"
        return slot.get(name, "P")

    out: list[str] = ["[CLS]"]
    for t in gh[:6]:                       # 가설이 많으면 앞 6개만 (길이 폭주 방지)
        out.append("[GH]")
        _emit(t, gsym, out)
    out.append("[GC]")
    _emit(gc, gsym, out)
    out.append("[SEP]")
    for t in ph[:6]:
        out.append("[PH]")
        _emit(t, psym, out)
    out.append("[PC]")
    _emit(pc, psym, out)

    stats = {"shared": len(shared), "g_only": len(set(g_const) - shared),
             "p_only": len(set(p_const) - shared), "len": len(out),
             "goal_parsed": gc is not None, "prem_parsed": pc is not None}
    return out[:max_len], stats


def token_ids(toks: list[str]) -> list[int]:
    """토큰 → 어휘 인덱스. 어휘 밖은 S+ 로 접는다(닫힌 어휘 보장)."""
    fb = VOCAB_INDEX["S+"]
    return [VOCAB_INDEX.get(t, fb) for t in toks]
