#!/usr/bin/env python3
"""★ 랭커 비교를 **네 지표 전부**로 한 표에 모은다 — 논문용 판단 자료.

    A·R    gold 중 **하나라도** 프롬프트에 들어감   (검색으로 직접)
    A·ALL  gold **전부**                          ← 학습이 실제로 요구하는 것
    C·R    assert 후 재검색에서 하나라도
    C·ALL  전부
    합성   A + (1−A)·C   (R 판 · ALL 판)

전부 **[프롬프트] 기준**(토큰 예산 안에 실제로 담김 · hybrid 담기)이다.
`[순위]` 기준은 별도 열로 붙인다.

★ 실행이 다르면 절대 수치를 비교하지 마라 — 표본·시점 코드가 다르다.
  같은 표(=같은 로그) 안에서만 비교한다. McNemar 도 그 안에서만 계산된다.

사용: PYTHONPATH=src python3 scripts/report_rankers.py [로그...]
"""
import re
import sys
import os


def parse(path):
    try:
        t = open(path, errors="ignore").read().replace("\x00", "")
    except Exception:
        return None
    if "프롬프트 포함(P) 기준" not in t:
        return None
    out = {"path": path, "rank": {}, "A": {}, "C": {}, "P": {}, "mcn": {}, "meta": {}}
    m = re.search(r"■ (\w+) · stage1 ([\d,]+) · (\d+)s", t)
    if m:
        out["meta"]["split"], out["meta"]["stage1"] = m.group(1), m.group(2)
    m = re.search(r"분모: .*?스텝 ([\d,]+)건", t)
    if m:
        out["meta"]["nA"] = m.group(1)
    m = re.search(r"\(그중 lemma 2개 이상 필요 ([\d,]+)건 = ([\d.]+)%\)", t)
    if m:
        out["meta"]["multi"] = m.group(2) + "%"

    def sec(start, end):
        mm = re.search(re.escape(start) + r".*?(?=" + end + r")", t, re.S)
        return mm.group(0) if mm else ""

    for tag, s in (("A", sec("【A】", r"【[BC]】")), ("C", sec("【C】", r"【목표】"))):
        for ln in s.split("\n"):
            mm = re.match(r"\s+(\S+) · (R|ALL)\s", ln)
            if not mm:
                continue
            v = re.findall(r"([0-9.]+)%", ln)
            if len(v) >= 4:
                out[tag].setdefault(mm.group(1), {})[mm.group(2)] = (v[-1], v[-2])  # (프롬프트, @50)
    p = sec("프롬프트 포함(P) 기준", r"【")
    for ln in p.split("\n"):
        mm = re.match(r"\s+(\S+)\s+([0-9.]+)%\s+([0-9.]+)%", ln)
        if mm:
            out["P"][mm.group(1)] = (mm.group(2), mm.group(3))
    mc = sec("쌍 비교", r"【")
    base = re.search(r"기준 `(\S+)`", mc)
    out["meta"]["mcn_base"] = base.group(1) if base else "?"
    for ln in mc.split("\n"):
        mm = re.match(r"\s+(\S+)\s+([0-9.]+)%\s+([+-][0-9.]+)\s+(\d+)\s+(\d+)\s+([0-9.]+)\s+(\S+)", ln)
        if mm:
            out["mcn"][mm.group(1)] = (mm.group(3), mm.group(4), mm.group(5), mm.group(6), mm.group(7))
    return out


LOGS = sys.argv[1:] or [
    "all_log/au_research/hyb_val.log", "all_log/au_research/hyb_test.log",
    "all_log/au_research/hyb_train.log", "all_log/au_research/lex_val.log",
    "all_log/au_research/lex_test.log"]

for path in LOGS:
    r = parse(path)
    if not r:
        print(f"\n■ {path} — 결과 없음 (미완 또는 0건)\n")
        continue
    m = r["meta"]
    print(f"\n{'='*104}")
    print(f"■ {m.get('split','?')}  ({os.path.basename(path)})  "
          f"분모 {m.get('nA','?')} · 다중 lemma {m.get('multi','?')} · stage1 {m.get('stage1','?')}")
    print(f"{'='*104}")
    print(f"  {'랭커':13s} │ {'A·R':>7} {'A·ALL':>7} │ {'C·R':>7} {'C·ALL':>7} │ "
          f"{'합성R':>7} {'합성ALL':>8} │ {'@50 A·ALL':>10} │ McNemar vs " + m.get("mcn_base", "?"))
    print(f"  {'-'*13}─┼─{'-'*15}─┼─{'-'*15}─┼─{'-'*16}─┼─{'-'*10}─┼{'-'*26}")
    order = list(r["P"])
    for k in order:
        a = r["A"].get(k, {}); c = r["C"].get(k, {})
        aR = a.get("R", ("-", "-"))[0]; aA = a.get("ALL", ("-", "-"))[0]
        a50 = a.get("ALL", ("-", "-"))[1]
        cR = c.get("R", ("-", "-"))[0]; cA = c.get("ALL", ("-", "-"))[0]
        pR, pA = r["P"].get(k, ("-", "-"))
        mc = r["mcn"].get(k)
        mcs = (f"{mc[0]:>7}  b={mc[1]:<4} c={mc[2]:<4} {mc[4]}" if mc
               else ("  (기준)" if k == m.get("mcn_base") else ""))
        print(f"  {k:13s} │ {aR:>7} {aA:>7} │ {cR:>7} {cA:>7} │ {pR:>7} {pA:>8} │ {a50:>10} │ {mcs}")
print()
print("※ A·R = gold 중 하나라도 · A·ALL = 전부 (학습이 요구하는 것)")
print("  C = A 가 실패한 스텝에서 assert 후 재검색 · 합성 = A + (1−A)·C")
print("  전부 [프롬프트] 기준(토큰 예산 · hybrid 담기). @50 은 순위 기준.")
print("  ★ 실행이 다르면 절대 수치를 비교하지 마라 — 같은 표 안에서만 비교한다.")
