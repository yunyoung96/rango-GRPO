#!/usr/bin/env python3
"""ablation용 **corrupted** 인덱스 — 정의는 그럴듯하되 구조 사실만 틀리게 만든다.

목적: "모델이 [TYPES]/[DEFINITIONS] 를 실제로 읽는가"를 가르는 조건. clean 과 형식·길이는
같고 **생성자 개수·이름·순서**만 조작한다. 모델이 읽는다면 destruct 패턴이 무너져 성능이
떨어져야 하고, 안 읽는다면 clean 과 차이가 없다.

조작 규칙 (결정적 — seed 고정, 재현 가능):
  · Inductive/Variant 계열: 생성자 하나를 **삭제**하고 하나를 **가짜로 추가**(개수 유지하되
    실제와 불일치) + 남은 것 중 하나를 **개명**. → arity/개수/이름 모두 오염.
  · Definition/Fixpoint: match 분기의 생성자 이름을 개명(본문 구조 오염).
※ 문자열 길이·토큰 수는 clean 과 비슷하게 유지 — 길이 차이가 confound 되지 않도록.
"""
import json
import random
import re
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else "data/func_defs_v3.json"
OUT = sys.argv[2] if len(sys.argv) > 2 else "data/func_defs_corrupt.json"
SEED = 1234

_TYPE_HEAD = re.compile(r"^\s*(?:#\[[^\]]*\]\s*)?(?:Local\s+|Global\s+|Polymorphic\s+)*"
                        r"(Inductive|CoInductive|Variant|Record|Structure|Class)\b")
_FAKE = ["Cx", "Mk", "Nd", "Vq", "Zt", "Pr", "Ql", "Wb"]


def corrupt_inductive(defn, rnd):
    """':=' 뒤 생성자 목록을 조작. 개수는 유지하되 내용이 실제와 어긋나게."""
    if ":=" not in defn:
        return None
    head, body = defn.split(":=", 1)
    parts = [p.strip() for p in body.split("|") if p.strip()]
    if len(parts) < 2:
        return None
    # ① 하나 삭제, ② 가짜 하나 추가(개수 유지), ③ 남은 것 중 하나 개명
    drop = rnd.randrange(len(parts))
    kept = [p for i, p in enumerate(parts) if i != drop]
    fake_name = rnd.choice(_FAKE) + str(rnd.randrange(10))
    tail = kept[-1]
    fake = re.sub(r"^[A-Za-z_][\w']*", fake_name, tail, count=1)
    kept.append(fake)
    if len(kept) >= 2:
        j = rnd.randrange(len(kept) - 1)
        kept[j] = re.sub(r"^[A-Za-z_][\w']*", rnd.choice(_FAKE) + str(rnd.randrange(10)),
                         kept[j], count=1)
    return head + ":= " + " | ".join(kept)


def corrupt_body(defn, rnd):
    """함수 정의: match 분기의 생성자 이름을 개명해 구조 사실을 어긋나게."""
    names = re.findall(r"\|\s*([A-Za-z_][\w']*)", defn)
    if not names:
        return None
    tgt = rnd.choice(names)
    return re.sub(r"(\|\s*)" + re.escape(tgt) + r"\b",
                  r"\1" + rnd.choice(_FAKE) + str(rnd.randrange(10)), defn)


def main():
    idx = json.load(open(SRC))
    out = {}
    n_ind = n_body = n_keep = 0
    for name, slot in idx.items():
        rnd = random.Random(f"{SEED}:{name}")          # 이름별 결정적
        new = {}
        for key, defn in slot.items():
            c = corrupt_inductive(defn, rnd) if _TYPE_HEAD.match(defn) else corrupt_body(defn, rnd)
            if c:
                new[key] = c
                n_ind += 1 if _TYPE_HEAD.match(defn) else 0
                n_body += 0 if _TYPE_HEAD.match(defn) else 1
            else:
                new[key] = defn                        # 조작 불가(단순 별칭 등)는 그대로
                n_keep += 1
        out[name] = new
    json.dump(out, open(OUT, "w"), ensure_ascii=False)
    print(f"이름 {len(out):,}  타입조작 {n_ind:,}  본문조작 {n_body:,}  그대로 {n_keep:,}  → {OUT}")
    # 샘플
    for nm in ("Lst", "val", "list"):
        if nm in idx:
            k = next(iter(idx[nm]))
            print(f"\n  [{nm}] clean  : {idx[nm][k][:96]}")
            print(f"  [{nm}] corrupt: {out[nm][k][:96]}")


if __name__ == "__main__":
    main()
