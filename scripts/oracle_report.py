#!/usr/bin/env python3
"""oracle_lemma_eval 샤드 합산 보고.

A 자연 · B 오라클검색(gold lemma 를 [PREMISES] 맨 앞에 주입) · C 오라클이름(이름까지 써 줌)
★ B 는 **선언 조회 품질**로 갈라 본다 — "모호"는 같은 맨이름이 여러 모듈에 있어
  엉뚱한 명제를 꽂았을 수 있으므로 그 행은 신뢰도가 낮다.
"""
import collections, json, sys

S = collections.Counter()
BY_P = collections.defaultdict(collections.Counter)   # 프롬프트 실림 여부
BY_H = collections.defaultdict(collections.Counter)   # 선언 조회 품질


def add(c, d):
    c["스텝"] += 1
    c["실림"] += d["in_prompt"]
    c["선언없음"] += (not d["has_decl"])
    c["A이름"] += d["hitA"]; c["A완벽"] += d["okA"]
    if d.get("okB") is not None:
        c["B대상"] += 1; c["B이름"] += d["hitB"]; c["B완벽"] += d["okB"]
    c["C완벽"] += d["okC"]


for p in sys.argv[1:]:
    try:
        fh = open(p, errors="ignore")
    except FileNotFoundError:
        continue
    for line in fh:
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        add(S, d)
        add(BY_P["프롬프트에 있음" if d["in_prompt"] else "프롬프트에 없음"], d)
        add(BY_H[d.get("decl_how", "?")], d)


def emit(lab, c):
    n = max(c["스텝"], 1); nb = max(c["B대상"], 1)
    print(f"  {lab:14s} 스텝{c['스텝']:5d} │ 실림 {c['실림']/n*100:5.1f}%"
          f" 선언없음 {c['선언없음']/n*100:5.1f}% │"
          f" A {c['A이름']/n*100:5.1f}%/{c['A완벽']/n*100:5.1f}% │"
          f" B {c['B이름']/nb*100:5.1f}%/{c['B완벽']/nb*100:5.1f}% │"
          f" C {c['C완벽']/n*100:5.1f}%")


print("  (칸: A 자연 이름맞힘/gold일치 · B 오라클검색 이름맞힘/gold일치 · C 오라클이름 조립성공)")
emit("전체", S)
print("\n  ── gold lemma 가 원래 프롬프트에 실려 있었나")
for k in ("프롬프트에 있음", "프롬프트에 없음"):
    if BY_H and BY_P[k]["스텝"]:
        emit(k, BY_P[k])
print("\n  ── B 의 선언 조회 품질별 (모호 = 같은 맨이름이 여러 모듈, 신뢰도 낮음)")
for k in ("정확", "프로젝트", "모호", "없음"):
    if BY_H[k]["스텝"]:
        emit(k, BY_H[k])
