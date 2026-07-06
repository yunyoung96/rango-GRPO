#!/usr/bin/env python3
"""
한 실험 run 디렉토리에 대해 analysis.md 스타일 보고서를 생성한다.
사용: python3 scripts/make_report.py all_results/<ts> [--baseline all_results/20260701-061839]

- summary.json(architecture/description/timeout/results) + 각 idx 로그를 파싱
- baseline과 같은 idx 기준으로 성공 개수 비교(신규 해결/회귀)
- 서브모듈별 성공률, 케이스별 표, 실패 유형(간이) 요약
"""
import argparse, json, re, os
from pathlib import Path

RE_SUB = re.compile(r"^compcert (\w+)/")
RE_MATCH = re.compile(r"매칭 IDs\s*:\s*(\[.*\])")
RE_COMPLETE = re.compile(r"TacticResult\.COMPLETE|CURRENT RESULT: SUCCESS")
RE_ITER_SL = re.compile(r"내부iterate#")
RE_ITER_CL = re.compile(r"\[Search\] 호출")
RE_INVALID = re.compile(r"TacticResult\.INVALID")
RE_VALID = re.compile(r"TacticResult\.VALID")


def submodule(log_path):
    try:
        with open(log_path, errors="replace") as f:
            for line in f:
                m = RE_SUB.match(line)
                if m:
                    return m.group(1)
    except FileNotFoundError:
        pass
    return "(unknown)"


def fail_features(log_path):
    """실패 로그에서 신호 추출: retrieval best_match(첫 iter), 반복수, invalid비율, 포맷."""
    best_match = 0
    n_iter = 0
    n_inv = n_val = 0
    fmt = "?"
    first_iter_seen = False
    in_first = False
    import ast
    try:
        with open(log_path, errors="replace") as f:
            for line in f:
                if RE_ITER_SL.search(line):
                    fmt = "straight"
                    n_iter += 1
                    in_first = not first_iter_seen
                    first_iter_seen = True
                    continue
                if RE_ITER_CL.search(line):
                    fmt = "classical"
                    n_iter += 1
                    in_first = not first_iter_seen
                    first_iter_seen = True
                    continue
                if in_first or not first_iter_seen:
                    m = RE_MATCH.search(line)
                    if m:
                        try:
                            ids = ast.literal_eval(m.group(1))
                            nt = [i for i in ids if len(str(i)) > 1 and str(i) not in ("->", "/\\", "\\/")]
                            best_match = max(best_match, len(nt))
                        except Exception:
                            pass
                if RE_INVALID.search(line):
                    n_inv += 1
                elif RE_VALID.search(line):
                    n_val += 1
    except FileNotFoundError:
        pass
    inv_ratio = n_inv / (n_inv + n_val) if (n_inv + n_val) else 0.0
    return dict(best_match=best_match, n_iter=n_iter, inv_ratio=inv_ratio, fmt=fmt)


def categorize(feat):
    if feat["best_match"] <= 1:
        return "NO_RETRIEVAL(유사증명 부재)"
    if feat["fmt"] == "straight" and feat["inv_ratio"] >= 0.35:
        return "LLM_INVALID(불법 tactic 다발)"
    return "STUCK(timeout·미완)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--baseline", default=None,
                    help="미지정 시 실험 timeout에 맞는 all_results/baseline<timeout> 자동 선택(공정 비교)")
    args = ap.parse_args()
    run_dir = Path(args.run_dir)
    summ = json.loads((run_dir / "summary.json").read_text())
    arch = summ.get("architecture", "?")
    desc = summ.get("description", "")
    timeout = summ.get("timeout_sec", "?")
    results = summ.get("results", [])
    res = {r["idx"]: r for r in results}
    idxs = sorted(res)
    logs = run_dir / "logs"

    # baseline 자동선택: 같은 timeout의 named baseline(공정 비교) → 없으면 대실행 폴백
    if args.baseline is not None:
        baseline_dir = args.baseline
    else:
        cand = Path(f"all_results/baseline{timeout}")
        baseline_dir = str(cand) if (cand / "summary.json").exists() else "all_results/20260701-061839"
    args.baseline = baseline_dir

    # baseline (같은 idx만)
    base = {}
    bpath = Path(baseline_dir) / "summary.json"
    if bpath.exists():
        bd = json.loads(bpath.read_text())
        base = {r["idx"]: r.get("success", False) for r in bd["results"]}

    n = len(idxs)
    nsucc = sum(1 for i in idxs if res[i]["success"])
    # rango.json(published Rango) 기준 원래 성공
    has_orig = any(res[i].get("original_success") is not None for i in idxs)
    orig_succ = [i for i in idxs if res[i].get("original_success")]
    vs_orig_new = [i for i in idxs if res[i]["success"] and res[i].get("original_success") is False]
    vs_orig_reg = [i for i in idxs if (not res[i]["success"]) and res[i].get("original_success") is True]
    # baseline 대비 (겹치는 idx만)
    common = [i for i in idxs if i in base]
    base_succ = [i for i in common if base[i]]
    newly_solved = [i for i in common if res[i]["success"] and not base[i]]
    regressed = [i for i in common if (not res[i]["success"]) and base[i]]

    # 서브모듈
    subs = {}
    sub_of = {}
    for i in idxs:
        s = submodule(logs / f"{i}.txt")
        sub_of[i] = s
        subs.setdefault(s, [0, 0])
        subs[s][0 if res[i]["success"] else 1] += 1

    # 실패 분류
    fails = [i for i in idxs if not res[i]["success"]]
    cats = {}
    fail_feat = {}
    for i in fails:
        feat = fail_features(logs / f"{i}.txt")
        fail_feat[i] = feat
        c = categorize(feat)
        cats.setdefault(c, []).append(i)

    # ---- 보고서 작성 ----
    L = []
    L.append(f"# 실험 보고서 — `{arch}`")
    L.append("")
    L.append(f"> **run**: `{run_dir}` · **timeout**: {timeout}s · **데이터**: 앞 {n}개")
    if desc:
        L.append(f"> **아이디어**: {desc}")
    L.append(f"> **baseline**: `{args.baseline}` (동일 idx 기준 비교)")
    L.append("")
    L.append("## 1. 요약")
    L.append("")
    L.append("| 항목 | 수치 |")
    L.append("|------|------|")
    L.append(f"| 성공 | **{nsucc}/{n}** ({100*nsucc/n:.1f}%) |")
    if common:
        delta = nsucc - len(base_succ) if len(common) == n else None
        L.append(f"| baseline 성공(같은 {len(common)}개) | {len(base_succ)}/{len(common)} |")
        L.append(f"| **신규 해결** (baseline 실패→성공) | **{len(newly_solved)}**개: {newly_solved} |")
        L.append(f"| **회귀** (baseline 성공→실패) | **{len(regressed)}**개: {regressed} |")
        net = len(newly_solved) - len(regressed)
        L.append(f"| **순증감** | **{'+' if net>=0 else ''}{net}** |")
    if has_orig:
        L.append(f"| rango.json(published) 성공 | {len(orig_succ)}/{n} |")
        L.append(f"| rango.json 대비 신규 해결 | {len(vs_orig_new)}개: {vs_orig_new} |")
        L.append(f"| rango.json 대비 회귀 | {len(vs_orig_reg)}개: {vs_orig_reg} |")
    L.append("")
    verdict = "미정"
    if common:
        net = len(newly_solved) - len(regressed)
        verdict = ("✅ baseline 대비 개선" if net > 0 else
                   "➖ baseline과 동률" if net == 0 else
                   "❌ baseline 대비 하락")
    L.append(f"**판정**: {verdict}")
    L.append("")

    L.append("## 2. 서브모듈별")
    L.append("")
    L.append("| 서브모듈 | ✅ | ❌ | 성공률 |")
    L.append("|---------|-----|-----|--------|")
    for s in sorted(subs):
        a, b = subs[s]
        L.append(f"| `{s}` | {a} | {b} | {100*a/(a+b):.0f}% |")
    L.append("")

    L.append("## 3. 실패 유형 (간이 분류)")
    L.append("")
    if fails:
        L.append("| 유형 | 개수 | idx |")
        L.append("|------|------|-----|")
        for c in sorted(cats, key=lambda k: -len(cats[k])):
            L.append(f"| {c} | {len(cats[c])} | {cats[c]} |")
    else:
        L.append("실패 없음.")
    L.append("")

    L.append("## 4. 케이스별")
    L.append("")
    L.append("| idx | 파일 | 결과 | 시간(s) | baseline | rango.json | 비고 |")
    L.append("|-----|------|------|--------|----------|-----------|------|")
    for i in idxs:
        r = res[i]
        ok = "✅" if r["success"] else "❌"
        b = ("✅" if base.get(i) else "❌") if i in base else "—"
        o = r.get("original_success")
        ostr = "✅" if o is True else ("❌" if o is False else "—")
        note = ""
        if i in newly_solved:
            note = "🎉 신규해결"
        elif i in regressed:
            note = "⚠️ 회귀"
        elif not r["success"]:
            note = categorize(fail_feat[i]).split("(")[0]
        L.append(f"| {i} | {sub_of[i]} | {ok} | {r.get('elapsed_sec','?')} | {b} | {ostr} | {note} |")
    L.append("")

    out = run_dir / "analysis.md"
    out.write_text("\n".join(L))
    print(f"wrote {out}  ({nsucc}/{n} success; 신규 {len(newly_solved)} 회귀 {len(regressed)})")


if __name__ == "__main__":
    main()
