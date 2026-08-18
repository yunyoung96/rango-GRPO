"""★ 이름 할당을 **한 곳으로** 통합한다 — 정규화(T/f/C/L/G)와 assert(H_asrt) 공통.

## 왜 통합하나

이름 규칙이 두 곳에 흩어져 있었다.

  · `normalize_names.build_mapping` 의 `fresh()` — 정규화용 (T0, f0, C0, L0, G0)
  · `assert_split._fresh` — assert 가설용 (H_asrt0)

규칙이 갈라지면 한쪽만 고쳐진다. 실제로 그런 일이 있었다 — 정규화는 `taken` 으로
이미 쓰인 인덱스를 건너뛰는데, assert 쪽은 **맨 이름(`H_asrt`)을 첫 번째로** 쓰고
있었고 뒤 증명을 안 봤다.

## 규칙 (하나로 통일)

**컨텍스트마다 이름 집합을 만들고, 이름을 붙일 때마다 그 집합에 있는지 검사해서
있으면 다음 인덱스로 건너뛴다.** 동작 차이는 **플래그**로만 준다.

    scan_family   후보로 **시작하는** 이름도 충돌로 본다 (H_asrt0 vs H_asrt01)
    scan_text     집합뿐 아니라 **원문 텍스트**를 단어 단위로 직접 대조한다
    avoid_family  기저 이름이 어떤 식별자의 접두사도 안 되게 기저 자체를 바꾼다
                  (Coq 이 intros 때 자동 개명해 우리 가족을 침범하는 것을 막는다)

정규화는 가볍게(집합만), assert 는 빡세게(전부) 쓴다 — 정규화는 프롬프트 8KB 를 매
예제마다 훑으면 비용이 크고, assert 는 틀리면 증명이 조용히 오염되기 때문이다.
"""
from __future__ import annotations

import re

_WORD = "[A-Za-z_][\\w']*"


class NameAllocator:
    """한 컨텍스트의 이름 집합. `alloc(prefix)` 로 겹치지 않는 이름을 받는다."""

    def __init__(self, taken=None, texts=(), *, scan_family: bool = False,
                 scan_text: bool = False, avoid_family: bool = False,
                 family_suffixes: str = "abcdefghijkl"):
        self.taken: set[str] = set(taken or ())
        self.texts: tuple[str, ...] = tuple(t for t in texts if t)
        self.scan_family = scan_family
        self.scan_text = scan_text
        self.avoid_family = avoid_family
        self.family_suffixes = family_suffixes
        self._next: dict[str, int] = {}
        self._base: dict[str, str] = {}

    # ── 컨텍스트 만들기 ──────────────────────────────────────────────────
    @classmethod
    def from_texts(cls, *texts, **kw):
        """텍스트들에 나오는 **식별자 전부**를 집합으로 삼는다 (빡센 쪽)."""
        out: set[str] = set()
        for t in texts:
            out |= set(re.findall(_WORD, t or ""))
        return cls(out, texts, **kw)

    @classmethod
    def from_pattern(cls, avoid_text: str, pattern: str, extra=(), **kw):
        """정해진 형태(`[TfCLG]\\d+` 등)만 훑는다 (가벼운 쪽 — 프롬프트가 크다)."""
        return cls(set(re.findall(pattern, avoid_text or "")) | set(extra), **kw)

    # ── 할당 ────────────────────────────────────────────────────────────
    def _free(self, cand: str) -> bool:
        if cand in self.taken:
            return False
        if self.scan_family and any(u.startswith(cand) for u in self.taken):
            return False
        if self.scan_text and self.texts:
            pat = re.compile(r"(?<![\w'])" + re.escape(cand) + r"(?![\w'])")
            if any(pat.search(t) for t in self.texts):
                return False
        return True

    def base_for(self, prefix: str) -> str:
        """`avoid_family` 면 어떤 식별자의 접두사도 아닌 기저를 고른다."""
        if not self.avoid_family:
            return prefix
        if prefix in self._base:
            return self._base[prefix]
        b = prefix
        for suf in ("",) + tuple(self.family_suffixes):
            cand = prefix + suf
            if not any(u.startswith(cand) for u in self.taken):
                b = cand
                break
        else:
            b = prefix + "_zz"
        self._base[prefix] = b
        return b

    def alloc(self, prefix: str, start: int | None = None) -> str:
        """`prefix` 계열에서 **겹치지 않는 첫 이름**. 겹치면 다음 인덱스로 건너뛴다."""
        base = self.base_for(prefix)
        k = self._next.get(base, 0) if start is None else start
        for _ in range(10000):
            cand = f"{base}{k}"
            k += 1
            if self._free(cand):
                self.taken.add(cand)
                self._next[base] = k
                return cand
        self._next[base] = k
        return f"{base}_zz"

    def is_free(self, name: str) -> bool:
        """최종 방어선 — 반환 직전에 다시 확인한다."""
        if name in self.taken and name not in getattr(self, "_issued", ()):
            pass
        pat = re.compile(r"(?<![\w'])" + re.escape(name) + r"(?![\w'])")
        return not any(pat.search(t) for t in self.texts)
