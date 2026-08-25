#!/usr/bin/env python3
"""next_step_eval 의 샤드 jsonl 을 합쳐 보고한다.

두 갈래로 본다.
  · 위치별(prefix 비율) — 표류를 얼마나 제거하면 얼마나 맞히나
  · **tactic 종류별** — apply/rewrite 처럼 인자를 조립해야 하는 것에서 어떻게 무너지나
"""
import collections
import json
import re
import sys

NAMED = re.compile(r"\b(?:e?apply|e?rewrite|exact|unfold|specialize|generalize|refine|"
                   r"destruct|induction|pose\s+proof|inversion|case)\s+(?:<-\s*)?\(?\s*"
                   r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
HEAD = re.compile(r"^\s*(?:now\s+|try\s+|repeat\s+)?([A-Za-z_][\w']*)")
_WS = re.compile(r"\s+")


def norm(s):
    return _WS.sub(" ", (s or "").strip()).rstrip(".").strip()


def bucket(gold):
    """조립 난이도별 분류 — 무엇을 얼마나 채워야 하는가."""
    g = gold or ""
    m = HEAD.match(g)
    h = m.group(1) if m else "?"
    if h in ("apply", "eapply"):
        if " with " in g:
            return "apply … with"
        if re.search(r"\bin\s+[A-Za-z_]", g):
            return "apply … in H"
        return "apply/eapply"
    if h in ("rewrite", "erewrite"):
        if re.search(r"rewrite\s*\(", g):
            return "rewrite (L …)"
        if "<-" in g:
            return "rewrite <-"
        return "rewrite"
    if h == "unfold":
        return "unfold"
    if h in ("destruct", "case"):
        return "destruct/case"
    if h == "induction":
        return "induction"
    if h in ("exact", "refine", "specialize", "generalize", "inversion", "pose"):
        return h
    return "기타"


def row(c, gu_key="이름스텝"):
    n = max(c["스텝"], 1)
    gu = max(c[gu_key], 1)
    return (c["스텝"], c["top1"] / n * 100, c["top8"] / n * 100,
            c[gu_key], c["이름맞힘"] / gu * 100, c["완벽"] / gu * 100,
            c["조립실패"] / gu * 100, c["도달실패"] / gu * 100)


BY_R = collections.defaultdict(collections.Counter)
BY_B = collections.defaultdict(collections.Counter)
ALL = collections.Counter()
for path in sys.argv[1:]:
    try:
        fh = open(path, errors="ignore")
    except FileNotFoundError:
        continue
    for line in fh:
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        g = norm(d["gold"])
        cn = [norm(c) for c in d["cands"]]
        gl, cl = set(d["gold_names"]), set(d["cand_names"])
        rb = round(d["r"] * 5) / 5          # 0.2 단위 버킷
        for c in (BY_R[rb], BY_B[bucket(d["gold"])], ALL):
            c["스텝"] += 1
            c["top1"] += (bool(cn) and cn[0] == g)
            c["top8"] += (g in cn)
            if gl:
                c["이름스텝"] += 1
                hit = bool(gl & cl)
                c["이름맞힘"] += hit
                if hit and g in cn:
                    c["완벽"] += 1
                elif hit:
                    c["조립실패"] += 1
                else:
                    c["도달실패"] += 1
            else:
                c["일반스텝"] += 1

HDR = (f"{'':>16}{'스텝':>7}{'top1':>8}{'top8':>8}  │{'이름스텝':>8}"
       f"{'이름맞힘':>9}{'완벽':>7}{'조립실패':>9}{'도달실패':>9}")
def emit(label, c):
    n, t1, t8, gu, hit, perf, asm, reach = row(c)
    print(f"{label:>16}{n:7d}{t1:7.1f}%{t8:7.1f}%  │{gu:8d}{hit:8.1f}%{perf:6.1f}%{asm:8.1f}%{reach:8.1f}%")

print("\n■ 위치별 (prefix 비율)")
print(HDR)
for r in sorted(BY_R):
    emit(f"{int(r*100)}%", BY_R[r])

print("\n■ tactic 종류별 — 인자를 조립해야 하는 것들")
print(HDR)
for b, c in sorted(BY_B.items(), key=lambda kv: -kv[1]["스텝"]):
    if c["스텝"] >= 5:
        emit(b, c)

print("\n■ 전체")
print(HDR)
emit("ALL", ALL)
