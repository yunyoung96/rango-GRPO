#!/usr/bin/env python3
"""샤드 출력(sft2_pairs_train.jsonl.part*) 병합 → 지점 셔플 → 통계. 사용: python3 scripts/sft_merge_shuffle.py [OUT]"""
import collections, glob, json, sys
sys.path.insert(0, "scripts")
OUT = sys.argv[1] if len(sys.argv) > 1 else "all_log/sft2_pairs_train.jsonl"
_A = sys.argv[:]; sys.argv = ["sft_build.py", "train"]
import logging; logging.disable(logging.CRITICAL)
import sft_build as SB
sys.argv = _A
parts = sorted(glob.glob(OUT + ".part*"))
assert parts, "샤드 출력 없음"
n_in = 0
with open(OUT, "w") as fo:
    for pf in parts:
        for l in open(pf):
            if l.strip(): fo.write(l if l.endswith("\n") else l + "\n"); n_in += 1
print(f"■ 병합: 샤드 {len(parts)} · 행 {n_in}")
n = SB.point_shuffle(OUT)
rows = [json.loads(l) for l in open(OUT)]
assert len(rows) == n_in == n, f"행 수 불일치 {len(rows)} {n_in} {n}"
c = collections.Counter(r["case"] for r in rows); f = collections.Counter(r.get("form") for r in rows)
pts = len({(r["proj"], r["thm"], r["thmi"], r["k"]) for r in rows})
print(f"■ {n}행 · 지점 {pts} · 지점 셔플 완료 · 케이스 {dict(c)} · 형태 상위 {f.most_common(8)}")
print("SFTBUILD2_DONE")
