"""Quarry (Planning to Hammer, arXiv:2606.17981) — 난이도 모델용 28차원 특징 φ(ℓ).

논문 φ = intros-state 19 + statement 9 = 28차원.
- statement 특징: 서브레마 문장(문자열) 그대로 파싱.
- intros-state 특징: `repeat intro` 후 상태. 우리 환경 제약(무거운 Coq 왕복 회피)상
  **텍스트 레벨 intro 시뮬레이션**으로 산출한다: `forall x.., body` 바인더와
  `P -> Q -> concl` 전제를 hypotheses로, 남은 concl을 goal로 분리(=intro가 하는 일).
  실제 Goal 객체가 있으면(재귀 중) 그 Goal로 대체 산출(featurize_goal) 가능.

★제약: OCaml/opam 버전 변경 없음. 순수 Python 문자열/coqpyt Goal 파싱.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from coqpyt.coq.lsp.structs import Goal, Hyp

FEATURE_NAMES = [
    # ── intros-state 19 ──
    "num_goals", "goal_len", "goal_tok_count", "forall_left", "goal_arrow",
    "goal_logic_ops", "cmp_ops", "is_contra_goal", "num_hyps", "hyp_total_len",
    "hyp_len_avg", "hyp_len_max", "hyp_tok_count_total", "hyp_tok_count_max",
    "hyp_logic_ops_total", "match_fix_let", "mapset_tokens", "goal_exists",
    "hyp_forall_total",
    # ── statement 9 ──
    "stmt_len", "stmt_tok_count", "stmt_forall", "stmt_exists", "stmt_arrow",
    "stmt_logic_ops", "stmt_cmp_ops", "stmt_match_fix_let", "stmt_is_eq_goal",
]
N_FEATURES = len(FEATURE_NAMES)
assert N_FEATURES == 28, N_FEATURES

_TOK = re.compile(r"[A-Za-z_][A-Za-z0-9_']*|[^\sA-Za-z0-9]")
_LOGIC = ["/\\", "\\/", "<->", "~"]
_CMP = ["<=", ">=", "<>", "=", "<", ">"]
_MAPSET = re.compile(r"\b(Map|Maps|PTree|PMap|ZMap|Set|list|option|nat|Z|positive)\b")
_MFL = re.compile(r"\bmatch\b|\bfix\b|\blet\b")


def _tok_count(s: str) -> int:
    return len(_TOK.findall(s))


def _count_any(s: str, subs: list[str]) -> int:
    return sum(s.count(x) for x in subs)


def _split_intros(stmt: str) -> tuple[list[str], str]:
    """텍스트 레벨 intro: forall 바인더 + `->` 전제를 hyp로, 남은 걸 goal로.
    반환 (hyp_types, conclusion). 완벽한 파서는 아니지만 특징 추출엔 충분."""
    s = stmt.strip().rstrip(".").strip()
    hyps: list[str] = []
    # 반복적으로 선행 forall / 전제 제거
    changed = True
    while changed:
        changed = False
        m = re.match(r"forall\s+(.+?)\s*,\s*(.*)$", s, re.DOTALL)
        if m:
            binders, rest = m.group(1), m.group(2)
            # 바인더 각각을 hyp로 (타입 있는 것 우선)
            hyps.append(binders)
            s = rest.strip()
            changed = True
            continue
        # 최상위 `->` 분리 (괄호 깊이 0에서 첫 화살표)
        arrow = _top_arrow(s)
        if arrow is not None:
            hyps.append(s[:arrow].strip())
            s = s[arrow + 2:].strip()
            changed = True
    return hyps, s


def _top_arrow(s: str) -> Optional[int]:
    depth = 0
    i = 0
    while i < len(s) - 1:
        c = s[i]
        if c in "([":
            depth += 1
        elif c in ")]":
            depth -= 1
        elif depth == 0 and s[i] == "-" and s[i + 1] == ">":
            return i
        i += 1
    return None


def _goal_feats(goal_text: str, hyp_texts: list[str], num_goals: int) -> list[float]:
    """intros-state 19차원."""
    gt = goal_text
    hyp_lens = [len(h) for h in hyp_texts]
    hyp_toks = [_tok_count(h) for h in hyp_texts]
    return [
        float(num_goals),                                    # num_goals
        float(len(gt)),                                      # goal_len
        float(_tok_count(gt)),                               # goal_tok_count
        float(gt.count("forall")),                           # forall_left
        float(_top_arrow(gt) is not None) + float(gt.count("->")),  # goal_arrow
        float(_count_any(gt, _LOGIC)),                       # goal_logic_ops
        float(_count_any(gt, _CMP)),                         # cmp_ops
        float(gt.strip() in ("False", "False.")),            # is_contra_goal
        float(len(hyp_texts)),                               # num_hyps
        float(sum(hyp_lens)),                                # hyp_total_len
        float(sum(hyp_lens) / len(hyp_lens)) if hyp_lens else 0.0,  # hyp_len_avg
        float(max(hyp_lens)) if hyp_lens else 0.0,           # hyp_len_max
        float(sum(hyp_toks)),                                # hyp_tok_count_total
        float(max(hyp_toks)) if hyp_toks else 0.0,           # hyp_tok_count_max
        float(sum(_count_any(h, _LOGIC) for h in hyp_texts)),  # hyp_logic_ops_total
        float(len(_MFL.findall(gt))),                        # match_fix_let
        float(len(_MAPSET.findall(gt))),                     # mapset_tokens
        float(gt.count("exists")),                           # goal_exists
        float(sum(h.count("forall") for h in hyp_texts)),    # hyp_forall_total
    ]


def _stmt_feats(stmt: str) -> list[float]:
    """statement 9차원."""
    return [
        float(len(stmt)),                            # stmt_len
        float(_tok_count(stmt)),                     # stmt_tok_count
        float(stmt.count("forall")),                 # stmt_forall
        float(stmt.count("exists")),                 # stmt_exists
        float(stmt.count("->")),                     # stmt_arrow
        float(_count_any(stmt, _LOGIC)),             # stmt_logic_ops
        float(_count_any(stmt, _CMP)),               # stmt_cmp_ops
        float(len(_MFL.findall(stmt))),              # stmt_match_fix_let
        float(bool(re.search(r"(^|\s)@?eq\b|=", stmt))),  # stmt_is_eq_goal
    ]


def featurize_statement(stmt: str) -> list[float]:
    """서브레마 문장(문자열)만으로 28차원 φ(ℓ). 텍스트 레벨 intro 시뮬레이션."""
    hyps, concl = _split_intros(stmt)
    intros = _goal_feats(concl, hyps, num_goals=1)
    return intros + _stmt_feats(stmt)


def featurize_goal(goals: list[Goal], stmt: str) -> list[float]:
    """실제 coqpyt Goal 상태(재귀 중 intros 후)로 intros-state 19차원 + stmt 9차원."""
    if not goals:
        return [0.0] * 19 + _stmt_feats(stmt)
    g = goals[0]
    hyp_texts: list[str] = []
    for h in g.hyps:
        names = " ".join(h.names) if h.names else ""
        hyp_texts.append(f"{names} : {h.ty}" if h.ty else names)
    intros = _goal_feats(g.ty or "", hyp_texts, num_goals=len(goals))
    return intros + _stmt_feats(stmt)
