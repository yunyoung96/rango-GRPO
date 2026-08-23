#!/usr/bin/env python3
"""★ **프로젝트별 notation 색인** — goal 의 기호로 가려진 이름을 되찾기 위한 것.

동기(실측): 결손 사례 `intu` 의 goal 은 `A ⊢I phi` 인데, 그 이름은
`Notation "A ⊢I phi" := (@prv _ _ _ intu A phi)` 안에만 있다. NOTATION 은 rango 의
PremiseFilter 가 풀에서 빼므로 **검색으로는 절대 오지 않는다.**

파일 밖 notation 은 중앙 194개라 통째로는 못 넣는다. 그래서 **프로젝트로 좁히고
goal 에 실제로 나타나는 기호(anchor)만** 고른다 — 실측: 419개 → 2개, 그중 정답.

문장 형태 네 가지를 모두 잡는다(놓치면 CoRN 의 `[#]` 처럼 통째로 빠진다):
    Notation "..." := (...)          Infix "..." := (...)
    Reserved Notation "..."          ← RHS 없음, 버린다
    Inductive T ... where "..." := (...)   ← 993개. 이건 **타입 씨앗**으로 쓴다

출력 data/notation_index.json
    {proj: {"n": [[anchors, names, text], ...],     # 주입할 notation
            "s": [[anchors, typename], ...]}}       # [TYPES] 씨앗용
사용: python3 scripts/build_notation_index.py
"""
import collections
import json
import re
import sqlite3

DBS = ["raw-data/coq-dataset/sentences.db"]
OUT = "data/notation_index.json"

_NOTA = re.compile(r'(?:Notation|Infix)\s+"([^"]+)"\s*:=', re.S)
_RESERVED = re.compile(r'Reserved\s+Notation')
_WHERE = re.compile(r'\bwhere\s+"([^"]+)"\s*:=')
_LEVEL = re.compile(r'\s*\(\s*(?:at\s+level|in\s+custom|only\s+parsing|format)\b.*$', re.S)

# 어디에나 있어 식별력이 없는 기호
_TOO_COMMON = {
    "=", "->", "<-", "*", "+", "-", "/", "(", ")", ",", ":", ";", "|", "_",
    "<", ">", "<=", ">=", "/\\", "\\/", "~", "@", "{", "}", "[", "]", ".",
    "==", "<>", "^", "%", "&", "&&", "||", "::", "++", "..", ":=", "=>", "!",
    "?", "#", "$", "'", '"', "()", "[]", "{}", "|-",
}
_STOPWORD = {"if", "then", "else", "end", "let", "in", "with", "fun", "match",
             "return", "as", "for", "of", "is", "do", "and", "or", "not", "at"}


def anchors(key: str) -> list:
    """식별력 있는 기호 앵커. **기호를 포함한 것만** 쓴다 —
    `'then'` 같은 순수 단어는 goal 마다 수십 개가 걸려 잡음이 된다(실측 31개→).
    다만 `⊢I` 처럼 기호+글자가 붙은 것은 놓치면 안 되므로 함께 잡는다."""
    out = set()
    stripped = re.sub(r"'[^']*'", " ", key)
    # 기호 덩어리 + 뒤에 붙은 글자(⊢I, =[, ]=>, [#])
    for m in re.finditer(r"[^\w\s]+[A-Za-z]?", stripped):
        s = m.group(0).strip()
        # ★ **비ASCII 기호는 1글자여도 살린다** — `P ⪯ Q` 의 `⪯`, `A ⊢ B` 의 `⊢`.
        #   유니코드 수학기호는 그 자체로 식별력이 있다(실측: 이걸 버려서 색인에서
        #   `reduces` 가 통째로 빠졌다).
        if not s or s in _TOO_COMMON:
            continue
        if len(s) >= 2 or any(ord(ch) > 127 for ch in s):
            out.add(s)
    # 인용 키워드는 **길고 흔하지 않은 것만** (`'graphCR'` 은 되고 `'if'` 는 안 된다)
    for q in re.findall(r"'([^']+)'", key):
        q = q.strip()
        if len(q) >= 4 and q.lower() not in _STOPWORD:
            out.add(q)
    return sorted(out, key=len, reverse=True)


def rhs_names(rhs: str) -> list:
    rhs = _LEVEL.sub("", rhs).strip().rstrip(".")
    return list(dict.fromkeys(re.findall(r"[A-Za-z_][\w']*", rhs)))[:8]


def main():
    idx = collections.defaultdict(lambda: {"n": [], "s": []})
    seen = collections.defaultdict(set)
    st = collections.Counter()
    for db in DBS:
        c = sqlite3.connect(db)
        rows = c.execute(
            "select text, file_path, sentence_type from sentence "
            "where text like '%Notation%' or text like 'Infix %' or text like '% where \"%'"
        ).fetchall()
        st["문장"] += len(rows)
        for text, fp, stype in rows:
            m = re.search(r"/repos/([^/]+)/", fp or "")
            if not m:                       # stdlib(/root/.opam) 은 모델이 안다고 가정
                st["stdlib 제외"] += 1
                continue
            proj = m.group(1)
            text = (text or "").strip()
            # ① Inductive ... where "..." := (T ...)  → 타입 씨앗
            if "INDUCTIVE" in str(stype) or _WHERE.search(text):
                for key in _WHERE.findall(text):
                    tn = re.match(r"\s*(?:Inductive|Fixpoint|CoInductive)\s+([A-Za-z_][\w']*)",
                                  text)
                    if not tn:
                        continue
                    for a in anchors(key):
                        k = (a, tn.group(1))
                        if k not in seen[proj]:
                            seen[proj].add(k)
                            idx[proj]["s"].append([a, tn.group(1)])
                            st["씨앗"] += 1
                if "INDUCTIVE" in str(stype):
                    continue
            # ② Notation / Infix
            if _RESERVED.search(text):
                st["Reserved 제외"] += 1
                continue
            mm = _NOTA.search(text)
            if not mm:
                continue
            key = mm.group(1)
            names = rhs_names(text[mm.end():])
            if not names:
                continue
            an = anchors(key)
            if not an:
                st["앵커 없음"] += 1
                continue
            body = _LEVEL.sub("", text).strip()
            if not body.endswith("."):
                body += "."
            if len(body) > 220:
                body = body[:217] + "..."
            k = (key, tuple(names))
            if k in seen[proj]:
                continue
            seen[proj].add(k)
            idx[proj]["n"].append([an, names, body])
            st["notation"] += 1
    out = {p: v for p, v in idx.items() if v["n"] or v["s"]}
    json.dump(out, open(OUT, "w"), ensure_ascii=False)
    import os
    print(f"■ {OUT}  {os.path.getsize(OUT)/1e6:.1f} MB · 프로젝트 {len(out)}")
    for k in sorted(st):
        print(f"   {k:16s} {st[k]:>8,}")
    big = sorted(out.items(), key=lambda x: -len(x[1]["n"]))[:5]
    print("   최다 프로젝트:", ", ".join(f"{p}={len(v['n'])}" for p, v in big))


if __name__ == "__main__":
    main()
