"""환각 lemma 이름 필터 — 존재하지 않는 이름을 쓰는 후보를 Coq 에 보내기 전에 버린다.

★ 왜 이게 최대 레버인가 (rand200 실측, v2 step60000):
    INVALID 7,981건 중 '이름 못 찾음' 3,613건(45.3%)
      ☓ 코퍼스에 아예 없는 이름(지어냄)  2,810 (77.8%)   ← 전체 INVALID 의 35%
      ★ 실재하나 스코프에 없었음            434 (12.0%)
      로컬변수처럼 짧은 이름                314 ( 8.7%)
    지어낸 예: `apply ltu_shl`, `apply iprop_eqs`, `generalize (shl_shl_split ...)`
    — CompCert 명명 규칙을 흉내 낸 그럴듯한 조합이지만 실재하지 않는다.
    (실제로 같은 파일에 `shru_shl` 은 있는데 모델은 `ltu_shl` 을 만든다.)

★ 왜 '버리기'가 실질 이득인가: 이 워크로드는 **Coq 검증(~300ms)이 시간을 지배**한다.
    600초 예산에서 환각 후보를 미리 걸러내면 그만큼 유효 후보를 더 많이 시도할 수 있다.
    (INVALID 를 없앤다고 성공률이 그만큼 오르는 게 아니라, **탐색 예산이 늘어나는** 효과다.)

★ 오탐(정상 후보를 버림) 위험을 낮추는 설계:
    허용집합 = 코퍼스 전체 선언 이름(220,979) ∪ 프롬프트 premise 의 이름 ∪ goal/가설의 식별자.
    환각 이름은 코퍼스에 **아예 없으므로** 이 넓은 집합으로도 78%가 잡힌다.
    확신이 없으면(허용집합 로드 실패 등) 필터를 통째로 끄고 원본을 그대로 반환한다.
"""
from __future__ import annotations

import json
import os
import re
from typing import Iterable, Optional

# 인자가 **거의 항상 전역 lemma/정의**인 tactic 만 대상으로 한다.
#   ★ destruct/induction/inversion 은 제외: 인자가 로컬 가설(`destruct H`, `destruct used`)인
#     경우가 많아 오탐이 크다. 실측에서 오탐의 대부분이 여기서 나왔다.
_ARG_TACTICS = ("apply", "eapply", "rewrite", "erewrite", "unfold", "generalize",
                "exact", "eexact", "specialize", "elim")
# 인자 구간: tactic 뒤 ~ 절 끝(';' 또는 문장 끝 '.'). 단 **qualified 이름의 점은 살린다**
#   (`Archi.ptr64` 가 'Archi' 에서 잘리면 오탐). → 점 뒤에 공백/끝이 올 때만 종료로 본다.
_TAC_RE = re.compile(r"\b(" + "|".join(_ARG_TACTICS) + r")\b((?:[^;.]|\.(?=[A-Za-z_]))*)")
_IDENT = re.compile(r"[A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*")
# 이 뒤에 오는 것은 **새로 바인딩되는 이름**이거나 대상 지정 → 검사 제외
#   (`destruct H as [LOAD DECODE]`, `rewrite X in H`, `apply f with (n:=3)`, `destruct e eqn:E`)
_CUT = re.compile(r"\b(as|in|with|eqn|using|into|at)\b")

# 인자에 흔히 섞이는 키워드·수식어 — 이름이 아니므로 검사 대상에서 제외
_SKIP = {
    "in", "at", "with", "as", "by", "using", "eqn", "into", "within",
    "all", "auto", "eauto", "simpl", "try", "repeat", "now", "first", "left", "right",
    "intros", "intro", "subst", "reflexivity", "congruence", "lia", "omega", "ring",
    "field", "discriminate", "contradiction", "assumption", "constructor", "split",
    "exists", "forall", "fun", "match", "end", "let", "if", "then", "else", "return",
    "Type", "Prop", "Set", "true", "false", "nat", "bool", "list", "option", "unit",
    "S", "O", "None", "Some",
    # tactic 수식어(이름 아님)
    "dependent", "until", "after", "before", "beta", "iota", "zeta", "delta",
}

# Coq 이 **자동 생성**하는 이름 — 코퍼스에 선언문이 없어 허용집합에 안 잡힌다.
#   `bool_ind`, `nat_rect`, `list_rec`, `xxx_sind` 등. 접미사로 통과시킨다.
_AUTO_SUFFIX = ("_ind", "_rec", "_rect", "_sind", "_ind_dep", "_inv", "_equation",
                "_eq", "_dec", "_sig", "_sig2", "_uncurried")

_KNOWN: Optional[frozenset] = None
_DISABLED = False


def _known() -> frozenset:
    """코퍼스 선언 이름 집합. 없으면 빈 집합 → 필터 자동 비활성(안전)."""
    global _KNOWN, _DISABLED
    if _KNOWN is None:
        path = os.environ.get("KNOWN_NAMES_PATH", "data/known_names.json")
        try:
            with open(path) as f:
                _KNOWN = frozenset(json.load(f))
        except OSError:
            _KNOWN = frozenset()
            _DISABLED = True
    return _KNOWN


def local_names(goal: str, premises: Optional[Iterable[str]] = None) -> set:
    """이 스텝에서 **추가로** 허용할 이름 — goal/가설의 식별자 + premise 에 등장하는 이름."""
    out = set()
    for t in _IDENT.findall(goal or ""):
        out.add(t.split(".")[-1])
    for p in (premises or ()):
        for t in _IDENT.findall(p or ""):
            out.add(t.split(".")[-1])
    return out


def unknown_names(tactic: str, allow: set) -> list:
    """tactic 의 인자 자리에서 허용집합에 없는 이름들. 빈 리스트면 통과."""
    known = _known()
    if not known:
        return []
    bad = []
    for m in _TAC_RE.finditer(tactic or ""):
        arg = m.group(2)
        cut = _CUT.search(arg)
        if cut:
            arg = arg[:cut.start()]      # as/in/with 이후는 새 이름 바인딩 → 제외
        for t in _IDENT.findall(arg):
            s = t.split(".")[-1]
            if len(s) <= 4 or s in _SKIP:
                continue    # 4글자 이하는 로컬 변수(H0, used, tac...)일 수 있어 판정 보류(오탐 방지)
            if s in allow or s in known:
                continue
            if s.endswith(_AUTO_SUFFIX) and any(s[:-len(sf)] in known
                                                for sf in _AUTO_SUFFIX if s.endswith(sf)):
                continue          # 자동생성 파생이름(bool_ind 등) — 기반 타입이 실재하면 통과
            bad.append(s)
    return bad


def filter_result(result, goal: str, premises: Optional[Iterable[str]] = None):
    """ModelResult 에서 환각 이름을 쓴 후보를 제거. 전부 걸러지면 **원본 유지**.

    ★ 전부 걸러졌을 때 원본을 돌려주는 이유: 후보가 0개가 되면 탐색이 그 노드에서 즉시 막힌다.
      필터는 '예산 절약'이 목적이지 '탐색 차단'이 아니다.
    """
    if os.environ.get("FILTER_UNKNOWN_NAMES", "0") != "1":
        return result, 0
    if not _known():
        return result, 0
    tactics = getattr(result, "next_tactic_list", None)
    if not tactics:
        return result, 0
    allow = local_names(goal, premises)
    keep = [i for i, t in enumerate(tactics) if not unknown_names(t, allow)]
    dropped = len(tactics) - len(keep)
    if not keep or dropped == 0:
        return result, 0
    result.next_tactic_list = [tactics[i] for i in keep]
    for attr in ("score_list", "num_tokens_list", "costs"):
        v = getattr(result, attr, None)
        if isinstance(v, list) and len(v) == len(tactics):
            setattr(result, attr, [v[i] for i in keep])
    return result, dropped
