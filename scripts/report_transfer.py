#!/usr/bin/env python3
"""프로젝트별 전이 평가 리포트 — v2(증강) vs rango(원본)를 같은 정리로 비교.

아키텍처·워커·하드웨어를 항상 명시한다("rango" 만으로는 어떤 체크포인트·조건인지 알 수 없음).
"""
import glob
import os

STEP = os.environ.get("STEP", "60000")
TIMEOUT = os.environ.get("TIMEOUT", "600")
TAG = os.environ.get("TAG", "g2xw6_tot12")

PROJECTS = ["rand200", "hoare-tut", "dblib", "ext-lib", "zorns-lemma", "zfc",
            "huffman", "poltac", "reglang", "buchberger", "math-classes", "fourcolor"]


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


def main():
    print(f"\n{'='*92}")
    print(f"■ 전이 평가  (timeout {TIMEOUT}s, 워커 {TAG}, RTX PRO 6000 Blackwell ×2)")
    print(f"   v2    = deepseek-1.3b + LoRA, rango-augmented v2 step {STEP} "
          f"(재랭킹+[TYPES]+[DEFINITIONS])")
    print(f"   rango = deepseek-1.3b + LoRA, checkpoint-54500 (원본, 증강 없음)")
    print(f"{'='*92}")
    print(f"{'프로젝트':14s} {'정리':>5} │ {'v2 성공':>8} {'v2%':>6} │ {'rango':>7} {'rango%':>7} │ "
          f"{'차이':>6} {'v2만':>5} {'ran만':>5} {'둘다':>5}")
    print("-" * 92)
    T = [0, 0, 0, 0, 0, 0]      # 정리, v2성공, rango성공, v2만, rango만, 둘다
    for p in PROJECTS:
        vd = (f"all_results/v2_step{STEP}_{p}_t{TIMEOUT}_{TAG}" if p != "rand200"
              else f"all_results/v2_step{STEP}_rand200_t{TIMEOUT}_{TAG}")
        rd = f"all_results/rango54500_{p}_t{TIMEOUT}_{TAG}"
        if p == "rand200" and not os.path.isdir(rd):
            rd = "all_results/rand200_rango_blackwell_g1w6"     # 기존 기준선(g1×w6=6)
        v, r = load(vd), load(rd)
        if not v:
            continue
        c = sorted(i for i in v if i in r)
        if not c:
            print(f"{p:14s} {len(v):>5} │ {sum(v.values()):>8} {sum(v.values())/len(v)*100:>5.1f}% │ "
                  f"{'(기준선 없음)':>15} │")
            continue
        o = sum(1 for i in c if v[i]); b = sum(1 for i in c if r[i])
        oo = sum(1 for i in c if v[i] and not r[i])
        bo = sum(1 for i in c if r[i] and not v[i])
        both = sum(1 for i in c if v[i] and r[i])
        mark = "*" if p == "rand200" and rd.endswith("g1w6") else " "
        print(f"{p:14s} {len(c):>5} │ {o:>8} {o/len(c)*100:>5.1f}% │ {b:>7}{mark} {b/len(c)*100:>6.1f}% │ "
              f"{o-b:>+6} {oo:>5} {bo:>5} {both:>5}")
        T = [T[0]+len(c), T[1]+o, T[2]+b, T[3]+oo, T[4]+bo, T[5]+both]
    print("-" * 92)
    if T[0]:
        print(f"{'★ 합계(프로젝트 아님)':14s} {T[0]:>5} │ {T[1]:>8} {T[1]/T[0]*100:>5.1f}% │ "
              f"{T[2]:>7} {T[2]/T[0]*100:>6.1f}% │ {T[1]-T[2]:>+6} {T[3]:>5} {T[4]:>5} {T[5]:>5}")
    print("   * = 기존 기준선(g1×w6=6, 조건 일부 다름)")
    print(f"{'='*92}\n")


if __name__ == "__main__":
    main()
