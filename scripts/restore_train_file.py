#!/usr/bin/env python3
"""TRAIN 프로젝트의 .v 파일을 **sentences.db 로 복원**해 Coq 을 돌릴 수 있는지 시험한다.

## 왜

TRAIN 프로젝트는 원본 소스가 없어 Coq 실행이 불가능하다(assert 변환을 동적으로 검증할 수
없다). 그런데 sentences.db 에는 TRAIN repos 의 문장 541,835개가 **줄 번호와 전체 텍스트**로
남아 있다. 선언을 줄 순서로 재배치하면 파일 골격이 복원된다.

## 빠진 것과 대체

  · 증명 본문(`Proof. … Qed.`)  → `Admitted.` 로 대체 (선언만 있으면 쓸 수 있다)
  · `Require Import`            → sentence 에 없다. **표준 라이브러리를 추측**해 넣는다
  · 파일 밖 의존(다른 프로젝트) → 그 선언들을 `Axiom` / 원문으로 앞에 붙인다

## 무엇을 재나

파일마다 복원 → Coq 컴파일 → 성공률. 성공하는 파일이 많으면 TRAIN 에서도 동적 검증이
가능해진다. 실패가 대부분이면 가용한 20개 프로젝트(VAL 6 + TEST 12 + cutoff 2)로 대신한다.

사용: python3 scripts/restore_train_file.py [파일수]
"""
import collections
import os
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, "src")
from coqpyt.coq.base_file import CoqFile  # noqa: E402

NFILE = int(sys.argv[1]) if len(sys.argv) > 1 else 8
DB = "/tmp/coq-dataset/sentences.db"
OUT = Path("/tmp/claude-0/-app-coq-modeling/e02d0688-7cb1-43a8-aa0e-ee8afd60ce19/"
           "scratchpad/restore")
OUT.mkdir(parents=True, exist_ok=True)

# 증명이 필요 없는 선언은 그대로, 증명이 필요한 것은 Admitted 로 닫는다
_NEEDS_PROOF = {"LEMMA", "THEOREM", "COROLLARY", "FACT", "REMARK", "PROPOSITION",
                "PROPERTY", "EXAMPLE"}
# 표준 라이브러리 추측용: 텍스트에 이 이름이 보이면 해당 모듈을 Require 한다
_HINT = [
    (r"\b(nat|S\b|O\b|plus|mult|Nat\.)", "Arith"),
    (r"\b(list|nil|cons|app|map|filter|In\b)", "List"),
    (r"\b(Z\.|Zplus|Zmult|BinInt)", "ZArith"),
    (r"\b(bool|andb|orb|negb|true|false)", "Bool"),
    (r"\b(R\b|Rplus|Rmult|Rle)", "Reals"),
    (r"\b(string|String)", "String"),
    (r"\b(Qmake|Qplus|Qle)", "QArith"),
    (r"\b(Ensemble|Included|Union)", "Sets.Ensembles"),
    (r"\b(FMap|FSet|Map\.)", "FSets.FMapList"),
    (r"\b(Program|Obligation)", "Program"),
    (r"\b(Setoid|Morphisms|Proper)", "Setoid"),
    (r"\b(lia|omega|Lia)", "Lia"),
]

db = sqlite3.connect(DB)
files = [r[0] for r in db.execute(
    "select file_path, count(*) c from sentence "
    "where file_path like '%coq-dataset/repos%' "
    "group by file_path having c between 8 and 60 order by c limit ?", (NFILE * 4,))]

stat = collections.Counter()
detail = collections.Counter()

for fp in files[:NFILE * 4]:
    if stat["시도"] >= NFILE:
        break
    rows = list(db.execute(
        "select text, sentence_type, line from sentence where file_path=? order by line",
        (fp,)))
    # 같은 줄에 중복 저장된 것 제거
    seen = set()
    uniq = []
    for t, ty, ln in rows:
        k = (t.strip(), ln)
        if k in seen:
            continue
        seen.add(k)
        uniq.append((t.strip(), str(ty).replace("TermType.", ""), ln))
    if len(uniq) < 5:
        continue

    body_txt = "\n".join(t for t, _, _ in uniq)
    reqs = []
    for pat, mod in _HINT:
        if re.search(pat, body_txt):
            reqs.append(mod)
    head = "\n".join(f"Require Import {m}." for m in dict.fromkeys(reqs))
    if "List" in reqs:
        head += "\nImport ListNotations."

    parts = [head, ""]
    for t, ty, _ln in uniq:
        t = t.rstrip()
        if not t.endswith("."):
            t += "."
        if ty in _NEEDS_PROOF:
            parts.append(t + "\nAdmitted.")
        elif ty in ("DEFINITION", "FIXPOINT", "COFIXPOINT", "INSTANCE", "OBLIGATION"):
            # 본문이 없으면(`:` 만 있고 `:=` 없음) 컴파일 불가 → Axiom 으로
            parts.append(t if ":=" in t else re.sub(r"^\w+", "Axiom", t))
        else:
            parts.append(t)
    src = "\n".join(parts) + "\n"

    name = re.sub(r"[^\w]", "_", fp.split("/")[-1])[:40]
    f = OUT / f"{name}.v"
    f.write_text(src)
    stat["시도"] += 1
    try:
        cf = CoqFile(str(f), timeout=120, workspace=str(OUT.resolve()))
        cf.run()
        n_err = len(cf.errors)
        msgs = [getattr(d, "message", "")[:80] for d in cf.errors[:2]]
        cf.close()
    except Exception as ex:
        n_err, msgs = -1, [f"예외: {str(ex)[:70]}"]
    if n_err == 0:
        stat["✓ 컴파일 성공"] += 1
        print(f"  ✓ {fp.split('/')[-1]:34s} 문장 {len(uniq)}")
    else:
        stat["✗ 실패"] += 1
        k = re.sub(r'"[^"]*"', '"…"', msgs[0] if msgs else "?")[:60]
        detail[k] += 1
        print(f"  ✗ {fp.split('/')[-1]:34s} 오류 {n_err} — {msgs[0][:70] if msgs else ''}")

print(f"\n■ TRAIN 파일 복원 시험")
for k in sorted(stat, key=lambda x: -stat[x]):
    print(f"   {k:18s} {stat[k]}")
if detail:
    print(f"\n   실패 유형:")
    for k, v in detail.most_common(6):
        print(f"     [{v}] {k}")
