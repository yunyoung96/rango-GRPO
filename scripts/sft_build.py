#!/usr/bin/env python3
"""★ [학습 전 ③] SFT 데이터 물질화 — answer.txt 설계 구현 v1.

지점마다: 5블록(채널별 r18 랭커 · rwh 만 20개) + 익명화(전역만, stdlib 제외)
 + case A/B(채널 정확 주입·균등 랜덤 위치·하위권 제거) + [ErrorFeedback] none
 + 변형(sft_variants.jsonl 조인, 지점당 ≤3) → sft_pairs.jsonl

주의 (answer.txt [5]·[6] 이행):
  · gold 와 프롬프트가 **같은 익명화 맵 객체**를 지나간다 (단일 함수)
  · 익명화 왕복 assert · 주입 후 "정답이 그 채널 블록에 정확히 1회" assert
  · 통계 출력: case A/B 비율 · 섹션별 토큰 예산 (피드백 ④ 실측)

사용: python3 scripts/sft_build.py <split> [상한]
"""
import collections, json, math, os, random, re, sys
import numpy as np
sys.path.insert(0, "scripts")
import logging; logging.disable(logging.CRITICAL)
_A = sys.argv[:]
sys.argv = ["pretty_rank.py", "x", "--", "y", "--", "z"]
import pretty_rank as PR
import applic_rank as AR
sys.argv = _A
from report_r15 import SPLITS, build_tfidf

SPLIT = (_A[1] if len(_A) > 1 else "train").lower()
CAP = int(_A[2]) if len(_A) > 2 else 10 ** 9
OUT = f"all_log/sft_pairs_{SPLIT}.jsonl"
random.seed(23)
K_RRF = 20
BLK = {"ap": 10, "in": 10, "rw": 10, "rwh": 20, "oth": 10}   # answer.txt [1]
BLOCK_NAME = {"ap": "PremisesForApply", "in": "PremisesForApplyIn",
              "rw": "PremisesForRewrite", "rwh": "PremisesForRewriteIn",
              "oth": "Others"}
FORM_CH = dict(PR.FORM_CH); FORM_CH["exact"] = "ap"; FORM_CH["eexact"] = "ap"
STRUCT = {"ap": "S1", "in": "S1", "rw": "S2", "rwh": "S1"}

tr_rows, _ = PR.load_merge(SPLITS["TRAIN"])
IDF, MAXI = build_tfidf(tr_rows)
VARIANTS = collections.defaultdict(list)
if os.path.exists("all_log/sft_variants.jsonl"):
    for l in open("all_log/sft_variants.jsonl"):
        v = json.loads(l)
        VARIANTS[(v["proj"], v["thm"], v["thmi"], v["k"])].append(v)


def rankdata_avg(v):
    order = np.argsort(-v, kind="mergesort")
    r = np.empty(len(v)); r[order] = np.arange(1, len(v) + 1)
    out = r.copy()
    for val in np.unique(v):
        m = v == val
        if m.sum() > 1: out[m] = r[m].mean()
    return out


def rank_channel(r, c):
    """채널 후보를 r18 랭커로 정렬해 이름 목록 반환."""
    names = sorted(set((r.get("chan") or {}).get(c, [])))
    if not names: return []
    SC = AR.sig_by_chan(r); sig = r.get("sig") or {}
    gsz = float((list(sig.values()) or [{}])[0].get("g", 1) or 1)
    cs = SC.get(c, sig)
    raw = PR.GOALS.get((r["proj"], r["thm"], r["thmi"], r["k"]), "")
    gtc = collections.Counter(AR._TOK.findall(raw)); 
    na = math.sqrt(sum((v * IDF.get(t, MAXI)) ** 2 for t, v in gtc.items()))
    stmts = r.get("stmts") or {}
    ST = []; TF = []
    for n in names:
        x = PR.pfeats(n, cs.get(n) or {}, gsz)
        ST.append((x[0] + x[1] + x[2]) if STRUCT[c] == "S1" else (x[0] + x[2]))
        scc = collections.Counter(AR._TOK.findall(stmts.get(n) or ""))
        num = sum(gtc[t] * scc[t] * IDF.get(t, MAXI) ** 2
                  for t in gtc.keys() & scc.keys())
        nb = math.sqrt(sum((v * IDF.get(t, MAXI)) ** 2 for t, v in scc.items()))
        TF.append(num / (na * nb) if na and nb else 0.0)
    ST = np.array(ST); TF = np.array(TF)
    s = 1.0 / (K_RRF + rankdata_avg(ST)) + 1.0 / (K_RRF + rankdata_avg(TF))
    order = sorted(range(len(names)), key=lambda i: (-s[i], names[i]))
    return [names[i] for i in order]


class Anon:
    """단일 익명화 맵 — 프롬프트·gold·에러가 전부 이 객체 하나를 지난다."""
    def __init__(self):
        self.map = {}; self.rev = {}
    def name(self, n):
        if AR._is_std(n): return n                     # stdlib 는 익명화 제외
        b = n.split(".")[-1]
        if b not in self.map:
            t = f"_L{len(self.map)}"
            self.map[b] = t; self.rev[t] = b
        return self.map[b]
    def text(self, s):
        for b, t in sorted(self.map.items(), key=lambda kv: -len(kv[0])):
            s = re.sub(rf"\b{re.escape(b)}\b", t, s)
        return s
    def rt(self, s):                                    # 왕복 검증용
        for t, b in self.rev.items():
            s = re.sub(rf"\b{re.escape(t)}\b", b, s)
        return s


def build_point(r):
    f = r.get("tac")
    form_ch = FORM_CH.get(f)
    golds = PR.golds_of(r)
    stmts = r.get("stmts") or {}
    blocks = {}
    for c in ("ap", "in", "rw", "rwh"):
        blocks[c] = rank_channel(r, c)[:BLK[c]]
    # Others = 나머지 이름을 tfidf 로 (간이: 채널 밖 이름의 어휘 점수 상위)
    used = set().union(*blocks.values())
    rest = [n for n in stmts if n not in used]
    blocks["oth"] = rest[:BLK["oth"]]
    case = "-"
    if form_ch:
        bl = blocks[form_ch]
        def hit(names): 
            bs = set()
            for g in golds:
                gb = g.split(".")[-1]; bs |= {g, gb}
                a = PR.ALIAS.get(g) or PR.ALIAS.get(gb)
                if a: bs.add(a)
            return [n for n in names if n in bs or n.split(".")[-1] in bs]
        if hit(bl):
            case = "A"
        else:
            case = "B"                                  # 채널 정확 주입
            pool_hit = hit(sorted(set((r.get("chan") or {}).get(form_ch, []))))
            gname = pool_hit[0] if pool_hit else golds[0]
            if bl:
                lower = list(range(len(bl) // 2, len(bl))) or [len(bl) - 1]
                bl.pop(random.choice(lower))
            bl.insert(random.randrange(len(bl) + 1), gname)
            assert len(hit(bl)) >= 1, "주입 후 gold 부재"
    anon = Anon()
    sec = []
    raw_goal = PR.GOALS.get((r["proj"], r["thm"], r["thmi"], r["k"]), "")
    for c in ("ap", "in", "rw", "rwh", "oth"):
        lines = []
        for n in blocks[c]:
            an = anon.name(n)
            st = (stmts.get(n) or "").replace("\n", " ")[:180]
            lines.append(f"{an} : {st}")
        sec.append(f"[{BLOCK_NAME[c]}]\n" + ("\n".join(lines) if lines else "none"))
    # 익명화는 맵 완성 후 일괄 (goal·진술문 본문·gold — 같은 맵)
    goal_a = anon.text(raw_goal)
    secs_a = [anon.text(x) for x in sec]
    gold_a = anon.text(r.get("gold_text") or "")
    assert anon.rt(gold_a).split() == (r.get("gold_text") or "").split(), "익명화 왕복 실패"
    prompt = "\n\n".join(["[STATE]\n" + goal_a] + secs_a
                         + ["[ErrorFeedback]\nnone"])
    rows = [{"prompt": prompt, "target": gold_a, "case": case, "form": f,
             "proj": r["proj"], "thm": r["thm"], "thmi": r["thmi"], "k": r["k"]}]
    for v in VARIANTS.get((r["proj"], r["thm"], r["thmi"], r["k"]), [])[:2]:
        rows.append({**rows[0], "target": anon.text(v["variant"]),
                     "case": case + "+var", "rule": v["rule"]})
    return rows


if __name__ == "__main__":
    rows, _ = PR.load_merge(SPLITS[SPLIT.upper()])
    random.shuffle(rows)
    stat = collections.Counter(); tok = collections.Counter(); n = 0
    with open(OUT, "w") as fo:
        for r in rows:
            if n >= CAP: break
            if r.get("tac") == "unfold": continue
            try: prs = build_point(r)
            except AssertionError as e: stat[f"assert:{e}"] += 1; continue
            for pr in prs:
                fo.write(json.dumps(pr, ensure_ascii=False) + "\n")
                stat[pr["case"]] += 1
            for scn in ("STATE", "PremisesForApply", "PremisesForApplyIn",
                        "PremisesForRewrite", "PremisesForRewriteIn", "Others"):
                m = re.search(rf"\[{scn}\]\n(.*?)(?=\n\n\[|$)", prs[0]["prompt"], re.S)
                if m: tok[scn] += len(m.group(1).split())
            n += 1
    print(f"■ SFT 물질화 {SPLIT}: 지점 {n} · 행 {sum(v for k,v in stat.items() if not k.startswith('assert'))}")
    print("   케이스:", dict(stat))
    print("   섹션별 평균 토큰(공백):",
          {k: v // max(n, 1) for k, v in tok.items()})
    print("SFTBUILD_DONE")
