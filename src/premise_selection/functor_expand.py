"""★ 펑터 인스턴스 이름을 검색 풀에 되살린다 — `FUNCTOR_EXPAND=1` 일 때만.

문제(`all_log/docs/premise/functor-names.md`)
    `Module Pregmap := EMap(PregEq).` 한 줄이 `Pregmap.gso` 를 만들어 내는데
    **그 이름의 선언은 소스 어디에도 없다.** 검색 풀은 선언문으로 만들어지므로
    증명이 40회 부르는 그 이름이 원리적으로 풀에 없다.
    CompCert 에서 tactic 인자 한정 참조의 **27.0%** 가 이런 이름이다.

여기서 하는 일
    풀에 **이미 있는** 펑터 F 의 선언을, 그 프로젝트의 인스턴스 N 이름으로 **복제**한다.
    없던 명제를 만들어 내는 게 아니라 **이름만 Coq 이 실제로 보는 것과 맞춘다.**
        풀에 있던 것:  module=["EMap"]  "Lemma gso: forall … i <> j -> (set j x m) i = m i."
        추가되는 것:   module=["Pregmap"] "Lemma Pregmap.gso: forall … (동일)"

    부수 효과로 **모호성도 준다** — `gso` 는 PTree·PMap·IMap·EMap·ITree 에 다 있어서
    풀에서 구분이 안 됐는데, 복제본은 완전 한정 이름이라 유일하다.

주의
    · 기본값 **꺼짐**. 아직 정식 채택이 아니다.
    · 풀이 커지므로 `FUNCTOR_EXPAND_MAX` 로 상한을 둔다.
    · 캐시 도장(`_CACHE_STAMP_KEYS`)에 반드시 들어가야 한다 — 풀이 바뀌면
      캐시된 `LmExample` 이 달라진다.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Optional

import rango_defaults as _D

_MAP: Optional[dict] = None
_ARG: Optional[dict] = None      # 프로젝트 -> {인자모듈: {"t": τ}}
_PROJ_RE = re.compile(r"(?:^|/)repos/([^/]+)/")
# 선언 머리 — 이름을 `N.name` 으로 바꿀 자리
_DECL = re.compile(
    r"^(\s*(?:Global\s+|Local\s+|Program\s+)?"
    r"(?:Lemma|Theorem|Corollary|Remark|Fact|Proposition|Definition|Fixpoint|"
    r"CoFixpoint|Inductive|Record|Instance|Axiom)\s+)([A-Za-z_][\w']*)")


def _load() -> dict:
    global _MAP
    if _MAP is None:
        _MAP = {}
        for k in ("FUNCTOR_INSTANCES_PATH",):
            p = os.environ.get(k)
            if p and Path(p).exists():
                _MAP = json.load(open(p))
                return _MAP
        # 기본: 학습·평가 맵을 둘 다 합친다(프로젝트 이름이 키라 충돌 없음)
        for p in ("data/functor_instances_train.json",
                  "data/functor_instances_test.json"):
            try:
                _MAP.update(json.load(open(p)))
            except Exception:
                pass
    return _MAP


def _argdefs() -> dict:
    """인자 모듈의 `Definition t := τ` — 추상 타입을 구체화하는 데 쓴다."""
    global _ARG
    if _ARG is None:
        _ARG = {}
        for p in ("data/functor_argdefs_train.json", "data/functor_argdefs_test.json"):
            try:
                _ARG.update(json.load(open(p)))
            except Exception:
                pass
    return _ARG


_ABS = re.compile(r"(?<![\w'])(?:elt|X\.t)(?![\w'])")


def _project(file_name: Optional[str]) -> Optional[str]:
    """`repos/<proj>/…` 또는 `<proj>/…` 에서 프로젝트 이름."""
    if not file_name:
        return None
    m = _PROJ_RE.search(file_name)
    if m:
        return m.group(1)
    parts = str(file_name).split("/")
    return parts[0] if parts else None


def expand(avail: list, file_name: Optional[str]) -> list:
    """펑터 멤버를 인스턴스 이름으로 복제해 풀에 더한다. 꺼져 있으면 그대로 돌려준다."""
    if not _D.flag("FUNCTOR_EXPAND"):
        return avail
    proj = _project(file_name)
    if not proj:
        return avail
    inst = _load().get(proj)
    if not inst:
        return avail
    cap = _D.num("FUNCTOR_EXPAND_MAX", 4000)
    out = list(avail)
    seen: set = set()
    added = 0
    for s in avail:
        mods = getattr(s, "module", None) or []
        for F in mods:
            for N in inst.get(F, ()):
                if added >= cap:
                    return out
                m = _DECL.match(getattr(s, "text", "") or "")
                if not m:
                    continue
                new_text = (m.group(1) + N + "." + m.group(2)
                            + (s.text[m.end():] if s.text else ""))
                # ★ **추상 타입을 구체화한다.** 안 하면 랭킹이 못 올린다 —
                #   `Lemma Pregmap.gso: … (i j: elt) …` 는 goal(preg 어휘)과 겹치는 게
                #   거의 없어 실측 **735위**였다(프롬프트는 상위 100). `elt → preg` 로
                #   바꾸면 어휘가 맞아 올라온다.
                #   치환은 **근사**다(`t A` 같은 파생 타입은 못 편다) — 랭킹용으로만 쓴다.
                if _D.flag("FUNCTOR_EXPAND_CONCRETE"):
                    tau = ((_argdefs().get(proj) or {}).get(N) or {}).get("t")
                    if tau:
                        new_text = _ABS.sub(tau, new_text)
                if new_text in seen:
                    continue
                seen.add(new_text)
                try:
                    import copy as _copy
                    ns = _copy.copy(s)
                    ns.text = new_text
                    ns.module = [N]
                    ns.db_idx = None          # 합성이므로 DB 식별자를 지운다
                    out.append(ns)
                    added += 1
                except Exception:
                    pass
    return out
