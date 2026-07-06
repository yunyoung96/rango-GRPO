#!/usr/bin/env python3
"""MR2 expert iteration용: 모든 실험 로그에서 성공한 (정리, 증명) 수집·중복제거.
사용: python3 scripts/collect_successes.py  → all_log/successes.jsonl
각 로그의 'CURRENT RESULT: SUCCESS' + 'CURRENT PROOF:' 블록에서 증명 스크립트 추출.
"""
import glob, os, re, json

OUT = "all_log/successes.jsonl"


def extract(path):
    """성공 로그에서 정리명·증명 스크립트 추출. 실패면 None."""
    try:
        txt = open(path, errors="replace").read()
    except Exception:
        return None
    if "CURRENT RESULT: SUCCESS" not in txt:
        return None
    # 'CURRENT PROOF:' 이후 블록 (다음 빈 줄 2개 or 파일끝까지, Qed까지)
    m = re.search(r"CURRENT PROOF:\s*\n(.*?)(?:\nQed\.|\nDefined\.|\Z)", txt, re.DOTALL)
    if not m:
        return None
    proof_block = m.group(1)
    # Qed 포함해서 마무리
    qed_m = re.search(r"CURRENT PROOF:\s*\n(.*?\n(?:Qed|Defined)\.)", txt, re.DOTALL)
    proof_full = qed_m.group(1) if qed_m else proof_block
    # 정리명 (첫 Theorem/Lemma/... 줄)
    thm_m = re.search(r"^\s*(Theorem|Lemma|Remark|Corollary|Definition|Fixpoint|Fact|Property|Proposition)\s+([A-Za-z_][\w']*)", proof_full, re.MULTILINE)
    thm_name = thm_m.group(2) if thm_m else None
    return {"thm": thm_name, "proof": proof_full.strip()}


def main():
    seen = {}  # thm_name or proof-hash -> record
    n_logs = 0
    for path in glob.glob("all_results/*/logs/*.txt"):
        r = extract(path)
        if r is None:
            continue
        n_logs += 1
        key = r["thm"] or hash(r["proof"])
        # 더 짧은 증명 선호(간결한 것)
        if key not in seen or len(r["proof"]) < len(seen[key]["proof"]):
            r["src"] = path
            seen[key] = r
    with open(OUT, "w") as f:
        for r in seen.values():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"성공 로그 {n_logs}개 → 중복제거 {len(seen)}개 고유 증명 → {OUT}")
    # 샘플
    for r in list(seen.values())[:3]:
        print(f"  [{r['thm']}] {r['proof'][:80]}...")


if __name__ == "__main__":
    main()
