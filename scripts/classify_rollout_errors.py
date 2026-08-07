#!/usr/bin/env python3
"""롤아웃 gz의 coq_error(RECORD_ERROR=1로 저장)를 '왜 INVALID인지'로 분류·집계.

목적: apply/rewrite 등에서 INVALID이 (a) hallucination(없는 참조) 인지
      (b) 틀린 인자(있는데 타입/문맥 안 맞음) 인지, coq-lsp 에러 메시지로 판정.

사용:  python scripts/classify_rollout_errors.py data/grpo_rollouts/<glob or dir>
       (인자 없으면 data/grpo_rollouts/*.gz 전부)

주의:  coq_error가 없는 옛 gz(RECORD_ERROR 꺼져 수집)는 'no_error_field'로 집계됨 → 재롤아웃 필요.
"""
import gzip, json, glob, re, sys, os, collections

# 판정 순서 중요(위에서부터 매칭). 각 카테고리 = (라벨, [정규식 키워드])
RULES = [
    # ── 없는 참조 = hallucination(모델이 존재하지 않거나 접근 불가한 이름을 지어냄) ──
    ("HALLUC_ref_not_found", [
        r"was not found", r"reference .* not found", r"Unknown (ident|reference|constant)",
        r"Cannot find", r"Unbound", r"is not defined", r"not a defined object",
        r"No such hypothesis", r"No such assumption",
    ]),
    # ── 타입 불일치 / 잘못된 인자(참조는 실존, 타입·형태가 안 맞음) ──
    ("TYPE_mismatch", [
        r"Unable to unify", r"Impossible to unify", r"not convertible",
        r"expected to have type", r"has type", r"Type mismatch",
        r"Illegal application", r"cannot be applied", r"not the right number",
        r"Cannot infer", r"cannot instantiate", r"Non strictly positive",
    ]),
    # ── 적용 불가(tactic 자체가 이 goal 형태에 안 맞음; 이름 문제 아님) ──
    ("APPLICABILITY", [
        r"No matching", r"Nothing to", r"found no subterm", r"does not occur",
        r"Not an equality", r"is not an inductive", r"Not a proposition",
        r"cannot rewrite", r"cannot find a relation", r"No such goal",
        r"unable to find", r"not a hypothesis",
    ]),
    # ── 문법 오류(생성이 애초에 깨진 토큰) ──
    ("SYNTAX", [
        r"Syntax error", r"Unexpected", r"Illegal begin", r"expected after",
        r"'\.'", r"is not a keyword", r"Stack overflow",
    ]),
]
COMPILED = [(lbl, [re.compile(p) for p in pats]) for lbl, pats in RULES]


def classify(msg: str) -> str:
    if not msg:
        return "empty"
    for lbl, pats in COMPILED:
        if any(p.search(msg) for p in pats):
            return lbl
    return "OTHER"


def head_of(tac: str):
    t = re.sub(r"^[\-\+\*\d\.\)\s]+", "", (tac or "").strip())
    m = re.match(r"([A-Za-z_]+)", t)
    return m.group(1) if m else None


def main(argv):
    args = argv[1:] or ["data/grpo_rollouts/*.gz"]
    files = []
    for a in args:
        files += glob.glob(os.path.join(a, "*.gz")) if os.path.isdir(a) else glob.glob(a)
    files = sorted(set(files))

    total_inv = 0
    no_field = 0
    by_cat = collections.Counter()
    by_head_cat = collections.defaultdict(collections.Counter)
    for gz in files:
        with gzip.open(gz, "rt") as fh:
            for line in fh:
                try:
                    g = json.loads(line)
                except Exception:
                    continue
                for att in g.get("attempts", []):
                    for st in att.get("steps", []):
                        if st.get("result") != "INVALID":
                            continue
                        total_inv += 1
                        if "coq_error" not in st:
                            no_field += 1
                            continue
                        cat = classify(st["coq_error"])
                        by_cat[cat] += 1
                        h = head_of(st.get("tactic", ""))
                        if h:
                            by_head_cat[h][cat] += 1

    print(f"파일 {len(files)}개 | INVALID step {total_inv}개")
    if no_field:
        print(f"⚠ coq_error 없는 step {no_field}개 (RECORD_ERROR 꺼진 옛 롤아웃) → 재롤아웃해야 분류됨")
    scored = total_inv - no_field
    if scored <= 0:
        print("분류 가능한(coq_error 있는) step 없음."); return
    print(f"\n=== 전체 원인 분류 (n={scored}) ===")
    for cat, n in by_cat.most_common():
        print(f"  {cat:24s} {n:6d}  ({100*n/scored:.1f}%)")
    h_of_interest = ("apply", "eapply", "rewrite", "erewrite")
    print("\n=== argument tactic별 (%는 그 head 내) ===")
    for h in h_of_interest:
        tot = sum(by_head_cat[h].values())
        if not tot:
            continue
        print(f"  [{h}] n={tot}")
        for cat, n in by_head_cat[h].most_common():
            print(f"     {cat:24s} {n:6d}  ({100*n/tot:.1f}%)")


if __name__ == "__main__":
    main(sys.argv)
