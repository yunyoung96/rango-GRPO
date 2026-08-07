#!/usr/bin/env python3
"""함수 정의 인덱스 — goal 에 등장하는 함수의 정의를 프롬프트에 복원하기 위한 재료.

근거: docs/grpo/rango_augmented/PHASE2_DECIDER_GUIDE.md §D2.
  현재 프롬프트는 함수 **이름만** 주고 정의는 0% → Coq 커널이 보는 "완전한 상태"와 다르다.
  코퍼스의 Definition/Fixpoint 를 {함수명: 정의문} 으로 뽑아 [DEFINITIONS] 주입 재료로 쓴다.

사용: python3 scripts/build_func_defs.py [sentences.db|.v루트] [출력]
출력: data/func_defs.json  {함수명: "Definition foo (x:T) : U := body."}
"""
import json
import os
import re
import sqlite3
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else "data/coq-dataset/sentences.db"
OUT = sys.argv[2] if len(sys.argv) > 2 else "data/func_defs.json"

# ★ 정의 종류를 넓게 커버 — goal 에 나오는 대상은 함수만이 아니다.
#   Definition/Fixpoint(함수) · Inductive/CoInductive/Variant(데이터) · Record/Structure/Class(구조체)
#   · Instance(인스턴스) · Function/Program(파생) · Let/Parameter/Axiom(선언, 시그니처가 정보)
_KINDS = (r"Definition|Fixpoint|CoFixpoint|Inductive|CoInductive|Variant|Record|Structure|"
          r"Class|Instance|Function|Program\s+Definition|Program\s+Fixpoint|Let|"
          r"Parameter|Parameters|Axiom|Axioms|Conjecture|Hypothesis|Variable|Variables")
DEFN = re.compile(r"^\s*(?:#\[[^\]]*\]\s*)?(?:Local\s+|Global\s+|Polymorphic\s+|Monomorphic\s+|#\[[^\]]*\]\s*)*"
                  r"(?:" + _KINDS + r")\s+([A-Za-z_][\w']*)")
DEFN_ANY = re.compile(r"\b(?:" + _KINDS + r")\s+([A-Za-z_][\w']*)")
# sentences.db 의 sentence_type (넓게)
_DB_TYPES = ("TermType.DEFINITION", "TermType.FIXPOINT", "TermType.COFIXPOINT",
             "TermType.INDUCTIVE", "TermType.COINDUCTIVE", "TermType.VARIANT",
             "TermType.RECORD", "TermType.CLASS", "TermType.INSTANCE",
             "TermType.STRUCTURE", "TermType.FUNCTION", "TermType.RELATION",
             "TermType.SETOID", "TermType.SCHEME", "TermType.DERIVE", "TermType.OTHER")
END_DOT = re.compile(r"\.(?=\s|$)")
_WS = re.compile(r"\s+")


def _clean(t: str) -> str:
    return _WS.sub(" ", t.strip())


def _file_key(file_path: str) -> str:
    """정의가 나온 **파일** 키. 조회 시 같은 파일 → 같은 디렉토리 → 같은 프로젝트 순으로 좁힌다.

    ★ 왜 파일 단위인가 (실패에서 배움):
      처음엔 프로젝트 단위로만 보관하고 "같은 이름이 여럿이면 짧은 쪽"을 남겼다. 그 결과
      `qsctr-coq-quantified-theorems` 처럼 **한 저장소가 독립 벤치마크 수십 개를 담은 경우**
      goal 이 `forall x : Lst, append x nil = x` 인데 다른 파일의
      `Fixpoint append (l1 : lst) ... | Nil => ... | Cons ...` 를 주입했다(대소문자·생성자 전부 불일치).
      정작 그 파일 자신에 `Fixpoint append (append_arg0 : Lst) ... : Lst` 라는 정답이 있었는데
      "짧은 쪽" 규칙이 버렸다. → 이름 충돌은 프로젝트 간에만 나는 게 아니라 **같은 저장소 안에서도**
      난다. 파일 경로를 키로 두고 조회 시 거리순으로 고른다.
    """
    p = (file_path or "").replace("\\", "/")
    if "/.opam/" in p or "/lib/coq/theories/" in p or "/lib/coq/user-contrib/" in p:
        return "stdlib"
    m = re.search(r"/repos/(.+)$", p)
    return m.group(1) if m else p.lstrip("/")


def from_db(db: str) -> dict:
    """{이름: {파일경로: 정의문}} — 파일별로 보관(같은 저장소 안 이름 충돌까지 대응)."""
    c = sqlite3.connect(db)
    out: dict = {}
    ph = ",".join("?" * len(_DB_TYPES))
    q = f"SELECT text, file_path FROM sentence WHERE sentence_type IN ({ph})"
    for t, fp in c.execute(q, _DB_TYPES):
        m = DEFN.match(t or "")
        if not m:
            continue
        name = m.group(1).split(".")[-1]
        key = _file_key(fp)
        body = _clean(t)
        slot = out.setdefault(name, {})
        # 같은 (이름, 파일)이 여럿이면 **먼저 나온 것**(파일 내 최초 정의)을 유지.
        #   ※ 길이로 고르지 않는다 — 그 규칙이 위 §_file_key 의 오염을 만들었다.
        if key not in slot:
            slot[key] = body
    return out


def from_vfiles(root: str) -> dict:
    """.v 트리 폴백(sentences.db 없는 서버). 같은 {이름: {파일경로: 정의}} 스키마."""
    out: dict = {}
    for dirpath, _, files in os.walk(root):
        for fn in files:
            if not fn.endswith(".v"):
                continue
            path = os.path.join(dirpath, fn)
            try:
                text = open(path, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            key = _file_key(path)
            for m in DEFN_ANY.finditer(text):
                e = END_DOT.search(text, m.end())
                block = _clean(text[m.start(): e.end() if e else min(len(text), m.end() + 3000)])
                name = m.group(1).split(".")[-1]
                slot = out.setdefault(name, {})
                if key not in slot:
                    slot[key] = block
    return out


def main():
    raw = from_vfiles(SRC) if os.path.isdir(SRC) else from_db(SRC)
    # 정제: 1글자·비정상 이름 제거(로컬변수 오염 방지)
    clean = {k: v for k, v in raw.items() if len(k) > 1 and (k[0].isalpha() or k[0] == "_")}
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    json.dump(clean, open(OUT, "w"), ensure_ascii=False)
    n_defs = sum(len(v) for v in clean.values())
    lens = sorted(len(d.split()) for v in clean.values() for d in v.values())
    multi = sum(1 for v in clean.values() if len(v) > 1)
    med = lens[len(lens) // 2] if lens else 0
    print(f"이름 {len(raw)} → 정제 {len(clean)} (정의 총 {n_defs}, 파일간 충돌 이름 {multi})  저장: {OUT}")
    print(f"  정의 길이(단어): 중앙 {med}, 최대 {lens[-1] if lens else 0}")
    print("  예:", list(clean)[:8])


if __name__ == "__main__":
    main()
