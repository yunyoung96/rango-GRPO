"""[USES] 인용 타깃 — 모델이 [TYPES]/[DEFINITIONS] 를 **읽을 수밖에 없게** 만드는 학습 신호.

## 왜 필요한가 (ablation 실측 결론)

v2(step60000)를 같은 정리 187개로 재평가했을 때:

    clean (올바른 정의)      63/191 = 33.0%
    wrong (틀린 정의, 학습과 동일) 66/194 = 34.0%
    clean vs wrong: 차이 ±0, clean만 8 / wrong만 8, McNemar p = 1.000

**올바른 정의를 줘도 틀린 정의를 줘도 결과가 같다.** 즉 모델은 섹션 내용을 읽지 않는다.
다른 증거도 일치한다:
  · v1(생성자 이름만) vs v2(정의문+재귀) 의 loss 기울기가 -0.1426 vs -0.1425 (넷째 자리까지 동일)
  · [TYPES] 주입된 151개에서 destruct 패턴 오류가 2.77% (미주입 대비 개선 없음)

## 원인

loss 가 **tactic 토큰에서만** 계산된다. 그런데 대부분의 tactic 은 [TYPES] 없이도 예측된다
(`intros.`, `simpl.`, `auto.` …). 따라서 섹션을 **무시하는 것이 최적해**다 — 읽어야 할
gradient 압력이 존재하지 않는다.

## 해법

타깃 앞에 **인용(citation)** 을 붙인다:

    [TACTIC]
    [USES] Lst(2 ctors)
    destruct x as [| n l].

이제 정답을 내려면 프롬프트의 [TYPES] 에서 `Lst` 를 찾아 생성자 개수를 세야 한다.
loss 가 인용 토큰에서도 계산되므로 **섹션을 읽지 않으면 손해**가 된다.
(항목 12 'CoT 중간 표현 강제' + 항목 10 'RAFT: 답 앞에 정의를 verbatim 인용' 의 결합)

인용이 필요 없는 스텝(`intros.` 등)은 `[USES] -` 로 두어 포맷을 고정한다 —
포맷이 흔들리면 그 자체가 노이즈가 된다.

추론 시에는 `strip_cite()` 로 인용부를 떼고 tactic 만 Coq 에 보낸다.
"""
from __future__ import annotations

import re
from typing import Iterable, Optional

CITE_PREFIX = "[USES]"
_CITE_LINE = re.compile(r"^\s*\[USES\][^\n]*\n?", re.M)

# 인자에서 '무엇을 썼는지' 뽑을 tactic 들.
#   destruct/induction/case → **타입**(생성자 개수가 중요)
#   unfold/rewrite/apply    → **정의/lemma 이름**
_SCRUT = re.compile(r"\b(?:destruct|induction|case|inversion)\s+([^;.\n]+)")
_UNFOLD = re.compile(r"\bunfold\s+([^;.\n]+)")
# ★ `as [| n l]` / `eqn:E` / `in H` 뒤는 **새로 바인딩되는 이름**이라 대상이 아니다.
#   (실측: `destruct x as [| n l]` 에서 n 을 대상으로 오인해 엉뚱한 타입을 인용했다)
_ARG_CUT = re.compile(r"\b(as|eqn|in|with|using)\b")
_IDENT = re.compile(r"[A-Za-z_][\w']*")
_KW = {"in", "at", "as", "with", "eqn", "using", "auto", "eauto", "simpl", "try"}


def _hyp_types(goal: str) -> dict:
    """가설 블록의 {변수명: 타입head}."""
    hyp = (goal or "").split("\n\n", 1)[0]
    out = {}
    for ln in hyp.split("\n"):
        m = re.match(r"^\s*([\w', ]+?)\s*:\s*(.+)$", ln)
        if not m:
            continue
        typ = m.group(2).strip().split()
        head = typ[0].split(".")[-1] if typ else ""
        for nm in re.split(r"[,\s]+", m.group(1).strip()):
            if nm and head:
                out[nm] = head
    return out


def _ctor_count(defn: str) -> Optional[int]:
    """정의문에서 생성자 개수. Inductive 계열이 아니거나 **잘린 정의**면 None.

    ★ 잘린 정의(' ...')에서 개수를 인용하면 안 된다: 프롬프트에 보이지 않는 숫자를 가르치는 셈이라
      모델이 '읽기'가 아니라 '추측'을 배운다. 인용은 **프롬프트에서 유도 가능해야만** 신호가 된다.
    """
    if ":=" not in defn or "..." in defn:
        return None
    head = defn.split(":=", 1)[0]
    if not re.search(r"\b(Inductive|CoInductive|Variant)\b", head):
        return None
    body = defn.split(":=", 1)[1]
    n = len([p for p in body.split("|") if p.strip()])
    return n if n > 0 else None


def make_cite(tactic: str, goal: str, injected: dict) -> str:
    """이 스텝의 인용 문자열. injected = {이름: 정의문} (프롬프트에 실제로 들어간 것만).

    반환 예: '[USES] Lst(2 ctors)'  /  '[USES] append'  /  '[USES] -'
    ★ 프롬프트에 **없는** 이름은 인용하지 않는다 — 없는 걸 인용하라고 가르치면 환각을 조장한다.
    """
    if not injected:
        return f"{CITE_PREFIX} -"
    hyp = _hyp_types(goal)
    used = []

    def add(name, with_ctors):
        if name in injected and name not in [u[0] for u in used]:
            n = _ctor_count(injected[name]) if with_ctors else None
            used.append((name, n))

    for m in _SCRUT.finditer(tactic or ""):
        arg = m.group(1).strip()
        cut = _ARG_CUT.search(arg)
        if cut:
            arg = arg[:cut.start()]
        for t in _IDENT.findall(arg):
            if t in _KW:
                continue
            add(hyp.get(t, t), True)      # 변수면 그 타입, 아니면 이름 자체
    for m in _UNFOLD.finditer(tactic or ""):
        for t in _IDENT.findall(m.group(1)):
            if t not in _KW:
                add(t, False)

    # ★ tactic 이 타입을 직접 안 쓰더라도, **goal 에 등장하는 타입**은 인용시킨다.
    #   이유: 위 규칙만 쓰면 실질 인용이 9.5%(=gold 가 destruct/induction 인 비율)뿐이라
    #   나머지 90.5% 가 '-' 가 되고, 모델이 "항상 '-'" 를 학습해 압력이 사라진다.
    #   생성자 개수는 **[TYPES] 를 읽어야만** 알 수 있는 정보이므로, 이걸 인용시키면
    #   tactic 종류와 무관하게 섹션을 읽어야 한다.
    if not used:
        hyp_heads = list(dict.fromkeys(hyp.values()))          # 가설 변수의 타입(등장순)
        for h in hyp_heads:
            add(h, True)
            if len(used) >= 2:
                break
        if not used:                                            # 가설이 없으면 결론의 식별자
            concl = (goal or "").split("\n\n", 1)[-1]
            for t in _IDENT.findall(concl):
                if t not in _KW:
                    add(t, True)
                if len(used) >= 2:
                    break

    if not used:
        return f"{CITE_PREFIX} -"
    parts = [f"{n}({c} ctors)" if c else n for n, c in used[:3]]
    return f"{CITE_PREFIX} " + ", ".join(parts)


def strip_cite(text: str) -> str:
    """생성 결과에서 인용부를 떼고 tactic 만 남긴다(추론 경로)."""
    if CITE_PREFIX not in (text or ""):
        return text
    return _CITE_LINE.sub("", text, count=1).lstrip("\n")
