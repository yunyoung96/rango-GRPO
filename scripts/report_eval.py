#!/usr/bin/env python3
"""평가 결과 리포트 — **아키텍처·워커수·하드웨어를 항상 명시**한다.

왜: "rango" 라고만 쓰면 어떤 체크포인트인지, 몇 워커로 쟀는지 알 수 없다. 실제로 이 저장소에는
    같은 'rango' 이름의 결과가 둘 있고(다른 환경 w2 33.5% / 이 서버 w6 37.0%) 3.5%p 차이가 난다.
    워커 수는 confound(CPU 경합 → 600초 안 탐색량 변화)이므로 조건이 다르면 비교가 성립하지 않는다.

사용: STEP=50000 TOTW=6 TIMEOUT=600 python3 scripts/report_eval.py
"""
import glob
import json
import os
import sys

STEP = os.environ.get("STEP", "50000")
TOTW = os.environ.get("TOTW", "6")
WPG = os.environ.get("WPG", "3")
NGPU = os.environ.get("NGPU", "2")
TAG = os.environ.get("TAG", f"g{NGPU}xw{WPG}_tot{TOTW}")
TIMEOUT = os.environ.get("TIMEOUT", "600")

# 비교 대상 정의: (표시명, 아키텍처/체크포인트, 워커, 하드웨어, summary.json 경로)
BASELINES = [
    ("rango (원본)", "deepseek-1.3b + LoRA, checkpoint-54500", (1, 6, 6),
     "RTX PRO 6000 Blackwell (이 서버)", "all_results/rand200_rango_blackwell_g1w6/summary.json"),
    ("rango (원본)", "deepseek-1.3b + LoRA, checkpoint-54500", (1, 2, 2),
     "미상(다른 환경)", "all_results/rand200_baseline_test600_w2/summary.json"),
]


def load_dir(d):
    """logs/*.txt 에서 {idx: 성공여부}. summary.json 보다 정확(중단분 제외)."""
    out = {}
    for f in glob.glob(os.path.join(d, "logs", "*.txt")):
        try:
            i = int(os.path.basename(f)[:-4])
        except ValueError:
            continue
        t = open(f, errors="ignore").read()
        if "CURRENT RESULT: SUCCESS" in t:
            out[i] = True
        elif "\nfailed" in t:
            out[i] = False
    return out


def load_summary(p):
    if not os.path.exists(p):
        return {}
    return {int(x["idx"]): bool(x["success"])
            for x in json.load(open(p))["results"]}


def wlabel(ngpu, wpg, tot):
    """워커 표기 규칙: g<GPU수>×w<GPU당>=<총합>. 'w6' 만 쓰면 GPU당인지 총합인지 헷갈린다."""
    return f"g{ngpu}×w{wpg}={tot}"


def pct(a, b):
    return f"{a/max(b,1)*100:.1f}%"


def main():
    ours_arch = f"deepseek-1.3b + LoRA, rango-augmented **v2** step {int(STEP):,}"
    ours_hw = "RTX PRO 6000 Blackwell ×2 (이 서버)"
    print(f"\n{'='*78}")
    print(f"■ 평가 결과  (timeout {TIMEOUT}s)")
    print(f"{'='*78}")
    print(f"  측정 대상 : {ours_arch}")
    print(f"  하드웨어  : {ours_hw}")
    print(f"  워커      : {wlabel(NGPU, WPG, TOTW)}   (GPU {NGPU}장 × GPU당 {WPG} = 총 {TOTW})")
    print(f"  프롬프트  : 재랭킹 + [TYPES](정의문+재귀) + [DEFINITIONS](재귀), 맨 뒤 배치")

    # 1) 우리 결과 (rand200 + 전이)
    print(f"\n■ 성적")
    print(f"   {'평가셋':14s} {'성공':>5} {'완료':>5} {'전체':>5} {'성공률':>8}")
    print("   " + "-" * 46)
    for name, pat in [("rand200(CompCert)", f"all_results/rango_v2_step{STEP}_rand200_t{TIMEOUT}_{TAG}"),
                      ("hoare-tut", f"all_results/rango_v2_step{STEP}_hoare-tut_t{TIMEOUT}_{TAG}"),
                      ("dblib", f"all_results/rango_v2_step{STEP}_dblib_t{TIMEOUT}_{TAG}")]:
        if not os.path.isdir(pat):
            continue
        r = load_dir(pat)
        ok = sum(r.values())
        idxf = {"rand200(CompCert)": "data/compcert_bs2_rand200_idx.txt",
                "hoare-tut": "data/hoare-tut_all_idx.txt",
                "dblib": "data/dblib_all_idx.txt"}[name]
        tot = sum(1 for _ in open(idxf)) if os.path.exists(idxf) else len(r)
        print(f"   {name:14s} {ok:>5} {len(r):>5} {tot:>5} {pct(ok,len(r)):>8}")

    # 2) 기준선 대비 (rand200 만 — 기준선이 CompCert 뿐)
    ours = load_dir(f"all_results/rango_v2_step{STEP}_rand200_t{TIMEOUT}_{TAG}")
    if not ours:
        print("\n   (rand200 결과 없음)")
        return
    print(f"\n■ 기준선 대비 (rand200, 같은 정리만)")
    for label, arch, wtup, hw, path in BASELINES:
        bg, bw, btot = wtup
        base = load_summary(path)
        if not base:
            continue
        c = sorted(i for i in ours if i in base)
        if not c:
            continue
        o = sum(1 for i in c if ours[i])
        b = sum(1 for i in c if base[i])
        both = sum(1 for i in c if ours[i] and base[i])
        oo = sum(1 for i in c if ours[i] and not base[i])
        bo = sum(1 for i in c if base[i] and not ours[i])
        u = both + oo + bo
        same_hw = "★ 동일 하드웨어" if "이 서버" in hw else "  다른 환경"
        same_w = ("★ 동일 총워커" if str(btot) == str(TOTW)
                  else f"  총워커 다름(기준선 {btot} vs 우리 {TOTW}) — CPU 경합 차이 가능")
        print(f"\n   ── {label}  [{arch}]")
        print(f"      하드웨어: {hw}   {same_hw}")
        print(f"      워커: {wlabel(bg, bw, btot)}   {same_w}")
        print(f"      전체 성적: {sum(base.values())}/{len(base)} = {pct(sum(base.values()),len(base))}")
        print(f"      같은 정리 {len(c)}개 → 우리 {o} ({pct(o,len(c))})  vs  기준선 {b} ({pct(b,len(c))})"
              f"   차이 {o-b:+d} ({(o-b)/len(c)*100:+.1f}%p)")
        print(f"      우리만 {oo} | 기준선만 {bo} | 둘다 {both} | 합집합 {u} ({pct(u,len(c))}) | Jaccard {pct(both,u)}")
    print(f"\n{'='*78}\n")


if __name__ == "__main__":
    main()
