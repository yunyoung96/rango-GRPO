#!/usr/bin/env python3
"""Type-ablation 리포트 — 세 조건을 같은 정리로 비교하고 McNemar 로 유의성까지.

조건: polluted(학습과 동일 오염 인덱스) / fixed(파일단위 수정) / empty(내용 비움).
아키텍처·워커·하드웨어를 항상 명시한다.
"""
import glob
import json
import os
from math import comb

TAG = os.environ.get("TAG", "g2xw3_tot6")
TIMEOUT = os.environ.get("TIMEOUT", "600")
CONDS = [("clean", "올바른 정의(파일단위 수정)"),
         ("wrong", "다른 파일 동명정의 ★학습과 동일"),
         ("corrupt", "생성자 개수·이름 조작"),
         ("empty", "헤더만, 내용 (none)")]


def load(d):
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


def mcnemar(a_only, b_only):
    """양측 이항검정 p (불일치 쌍만 사용)."""
    n = a_only + b_only
    if n == 0:
        return 1.0
    k = min(a_only, b_only)
    p = sum(comb(n, i) for i in range(k + 1)) * 2 / 2 ** n
    return min(p, 1.0)


def main():
    res = {k: load(f"all_results/ablation_v2_{k}_t{TIMEOUT}_{TAG}") for k, _ in CONDS}
    have = [k for k, _ in CONDS if res[k]]
    if not have:
        print("결과 없음")
        return
    print(f"\n{'='*84}")
    print(f"■ Type-ablation  (deepseek-1.3b+LoRA, augmented-v2 step 60000)")
    print(f"   timeout {TIMEOUT}s · 워커 {TAG} · RTX PRO 6000 Blackwell ×2")
    print(f"   같은 모델·같은 정리, 프롬프트 **포맷 고정** — [TYPES]/[DEFINITIONS] 내용만 변경")
    print(f"{'='*84}")
    print(f"   {'조건':10s} {'설명':24s} {'성공':>5} {'완료':>5} {'성공률':>8}")
    print("   " + "-" * 60)
    for k, desc in CONDS:
        r = res[k]
        if not r:
            print(f"   {k:10s} {desc:24s} {'(진행 전)':>19}")
            continue
        print(f"   {k:10s} {desc:24s} {sum(r.values()):>5} {len(r):>5} "
              f"{sum(r.values())/len(r)*100:>7.1f}%")

    # 쌍별 비교(공통 정리만)
    print(f"\n   {'비교':22s} {'정리':>5} {'A':>5} {'B':>5} {'차이':>6} {'A만':>4} {'B만':>4} {'p':>7}")
    print("   " + "-" * 66)
    for i in range(len(have)):
        for j in range(i + 1, len(have)):
            a, b = have[i], have[j]
            c = sorted(set(res[a]) & set(res[b]))
            if not c:
                continue
            na = sum(1 for x in c if res[a][x])
            nb = sum(1 for x in c if res[b][x])
            ao = sum(1 for x in c if res[a][x] and not res[b][x])
            bo = sum(1 for x in c if res[b][x] and not res[a][x])
            print(f"   {a+' vs '+b:22s} {len(c):>5} {na:>5} {nb:>5} {na-nb:>+6} "
                  f"{ao:>4} {bo:>4} {mcnemar(ao,bo):>7.3f}")
    print("\n   해석 (모델은 wrong 으로 학습됨 = train-matched):")
    print("     · 네 조건이 모두 비슷        → 모델이 섹션을 안 읽음(신호 희석). 학습 레시피 문제.")
    print("     · clean > wrong              → 읽고 있고 오염이 손해였음 → 깨끗한 데이터로 재학습 가치.")
    print("     · wrong·clean > corrupt·empty → 내용이 실제로 쓰이고 있음(정보 기여 확인).")
    print(f"{'='*84}\n")


if __name__ == "__main__":
    main()
