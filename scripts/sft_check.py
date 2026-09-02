#!/usr/bin/env python3
"""★ SFT 물질화 산출(jsonl) 사후 검사기 — 학습 전에 반드시 통과해야 하는 불변식들 (requirements [B.5]).
   design_from_requirements.txt [8. 검사 목록] 과 1:1 대응.

  C1  정답의 익명 이름(_L#/_T#/_f#/_G#)은 **전부 프롬프트에 존재** (없으면 모델이 환각을 배운다)
  C2  익명화된 실명이 프롬프트·정답 어디에도 **새지 않는다** (PROOFS/SCRIPT/DEFINITIONS 포함)
      — "Lemma _L3 : 진술" 의 진술을 풀과 대조해 실명을 복원, 프롬프트 전역 검색
  C3  변형 정답(+var)도 C1 만족 + 같은 지점의 행들은 같은 익명 lemma 집합을 참조
  C4  블록 줄 수 ≤ 상한(10/10/10/20/10) · 절단으로 잘린 줄("Lemma X : ." 빈 진술) 없음
  C5  섹션 순서 고정: 5블록 → PROOFS → STATE → SCRIPT → (TYPES/DEFINITIONS/LTAC/NOTATION) → ErrorFeedback → [TACTIC]
  C6  프롬프트+정답 토큰 ≤ hard_seq_len · 정답 비어있지 않음
  C7  같은 지점의 행들은 프롬프트 동일(변형은 정답만 다름) · 원본 행 정확히 1 · 인접 행은 다른 지점(셔플)
  C8  정답의 실명 lemma 는 stdlib · 동명이인(선언 2회+) · 지역 가설 중 하나 (그 밖이면 "검토" 표시)
  C9  [STATE] 비어있지 않음 · [ErrorFeedback] 본문 = none (SFT 단계)
  C10 case B 주입 위치가 한 곳에 몰리지 않음 (블록 내 gold 줄 위치의 최빈 비율 < 60%, 표본 ≥ 20)
  C11 채널 정확성: 정답 form(apply/apply-in/rewrite/rewrite-in)의 gold 가 **그 form 의 블록**에 있다
  C12 토큰 경계: tok(prompt)+tok(target) 길이 = tok(prompt+target) — "[TACTIC]\\n" 경계에서 BPE 병합이 없어
      학습 마스크 경계가 정확하다
  C13 변형 행의 rule 과 정답 머리 일치 (ap→eapply ⇒ eapply …, rw→rw<- ⇒ rewrite <- …)
  C14 익명 이름 충돌 없음: 프롬프트 안에서 같은 `_L#` 로 시작하는 선언 줄이 2개 이상이면 실패
  C15 [Others] 에 채널 블록과 같은 이름 없음 (중복 배제)

사용: python3 scripts/sft_check.py <pairs.jsonl> [hard_seq_len=5120] [풀 jsonl...(실명 대조용)]
"""
import collections, json, re, sys, glob
sys.path.insert(0, "src")
from transformers import AutoTokenizer
from tactic_gen.normalize_names import is_stdlib_name

PATH = sys.argv[1]; HARD = int(sys.argv[2]) if len(sys.argv) > 2 else 5120
rows = [json.loads(l) for l in open(PATH)]
assert rows, "빈 파일"
tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-4B-Base")
ANON = re.compile(r"(?<![\w'])(_[LTfG]\d+)(?![\w'])")
ORDER = ["PremisesForApply", "PremisesForApplyIn", "PremisesForRewrite", "PremisesForRewriteIn", "Others",
         "PROOFS", "STATE", "SCRIPT", "TYPES", "DEFINITIONS", "LTAC", "NOTATION", "ErrorFeedback", "TACTIC"]
BLK = {"PremisesForApply": 10, "PremisesForApplyIn": 10, "PremisesForRewrite": 10, "PremisesForRewriteIn": 20, "Others": 10}
FORM_BLK = {"apply": "PremisesForApply", "exact": "PremisesForApply", "eexact": "PremisesForApply",
            "apply-in": "PremisesForApplyIn", "rewrite": "PremisesForRewrite", "rewrite-in": "PremisesForRewriteIn"}
RULE_HEAD = {"ap→eapply": "eapply", "eapply→ap": "apply", "rw→erw": "erewrite", "rw→rw<-": "rewrite <-", "rw<-→rw": "rewrite",
             "exact→apply": "apply", "apply→exact": "exact", "refl→exact": "exact eq_refl", "assum→exact": "exact",
             "destruct→case": "case", "case→destruct": "destruct", "induction→elim": "elim", "elim→induction": "induction",
             "exists→eexists": "eexists", "intros→chain": "intro", "ap→with": "apply", "ap→with2": "apply", "ap→exact(": "exact ("}
ALIAS = {}
try:
    ALIAS = json.load(open("all_log/r11_alias_map.json"))
except Exception: pass
def alias_set(b):
    out = {b}
    a = ALIAS.get(b)
    if a: out |= {a, a.split(".")[-1]}
    for k, v in ALIAS.items():
        if v == b or v.split(".")[-1] == b: out |= {k, k.split(".")[-1]}
    return out
_KW = r"(?:#\[[^\]]*\]\s+)?(?:Local\s+|Global\s+|Program\s+)?(?:Lemma|Theorem|Definition|Fixpoint|CoFixpoint|Instance|Axiom|Parameter|Hypothesis|Corollary|Remark|Fact|Proposition|Let)"
DECL = re.compile(r"^" + _KW + r"\s+([A-Za-z_][\w'.]*)", re.M)   # `이름:` (콜론 밀착, DB 원문) 도 이름만; Axiom 류 포함 (실측 오탐 83건)


def sections(p):
    """프롬프트 → [(헤더, 본문줄들)] — 헤더 줄은 `[Name]` 단독 줄."""
    out = []; cur = None; body = []
    for ln in p.split("\n"):
        m = re.fullmatch(r"\[([A-Za-z]+)\]", ln)
        if m and m.group(1) in ORDER:
            if cur: out.append((cur, body))
            cur, body = m.group(1), []
        else:
            body.append(ln)
    if cur: out.append((cur, body))
    return out


# 실명 대조용: 풀의 진술문 → 이름 (C2)
stmt2name = {}
for pf in (sys.argv[3:] or glob.glob("all_log/r11_pool_train*.jsonl")):
    try:
        for l in open(pf):
            r = json.loads(l)
            for n, st in (r.get("stmts") or {}).items():
                s = " ".join((st or "").split())
                if s.startswith("(") and s.endswith(")"): s = s[1:-1].strip()
                stmt2name.setdefault(s[:180], n.split(".")[-1])
    except Exception: pass
print(f"■ 검사 대상 {len(rows)}행 · 실명 대조 진술 {len(stmt2name)}")

C = collections.Counter(); fails = collections.defaultdict(list); inj_pos = []
def fail(code, i, msg): fails[code].append((i, msg)); C["FAIL " + code] += 1

by_pt = collections.defaultdict(list)
for i, r in enumerate(rows):
    p, t = r["prompt"], r["target"]; case = r["case"]
    key = (r["proj"], r["thm"], r["thmi"], r["k"]); by_pt[key].append(i)
    secs = sections(p); heads = [h for h, _ in secs]; S = {h: b for h, b in secs}
    # C5 순서·유일성·종료
    idx = [ORDER.index(h) for h in heads]
    if idx != sorted(idx) or len(set(heads)) != len(heads) or not p.endswith("[TACTIC]\n") \
            or any(h not in heads for h in list(BLK) + ["PROOFS", "STATE", "SCRIPT", "ErrorFeedback", "TACTIC"]):
        fail("C5", i, f"헤더 {heads}")
    # C4 블록 줄 수·빈 진술
    blk_names = collections.defaultdict(set)
    for h, cap in BLK.items():
        body = [l for l in S.get(h, []) if l.strip() and l.strip() != "none"]
        if len(body) > cap: fail("C4", i, f"{h} {len(body)}>{cap}")
        if any(re.match(r"^Lemma \S+ : \.?$", l.strip()) for l in body): fail("C4", i, f"{h} 빈 진술")
        C[f"블록 {h} 꽉참"] += (len(body) >= cap)
        for l in body:
            m = DECL.match(l)
            if m: blk_names[h].add(m.group(1).split(".")[-1])
    # C15 Others 중복 배제
    chan = set().union(*(blk_names[h] for h in BLK if h != "Others"))
    if blk_names["Others"] & chan: fail("C15", i, f"Others 중복 {sorted(blk_names['Others'] & chan)[:3]}")
    # C14 익명 선언 충돌
    anon_stmts = collections.defaultdict(set)
    for h_ in BLK:                        # 5블록 안만 — [PROOFS] 의 같은 lemma 는 인쇄(스코프·바인더)가 달라도 정상
        for ln_ in S.get(h_, []):
            m_ = re.match(_KW + r"\s+(_L\d+)\s*:\s*(.*)$", ln_)
            if m_: anon_stmts[m_.group(1)].add(re.sub(r"\s+", "", m_.group(2)))
    clash = [k for k, v in anon_stmts.items() if len(v) > 1]        # 같은 lemma 의 다채널 반복은 정상, 진술이 다르면 충돌
    if clash: fail("C14", i, f"{clash[:3]}")
    # C9 STATE·ErrorFeedback
    if not any(l.strip() for l in S.get("STATE", [])): fail("C9", i, "STATE 비어있음")
    if [l.strip() for l in S.get("ErrorFeedback", []) if l.strip()] != ["none"]: fail("C9", i, "ErrorFeedback≠none")
    # C6 길이·정답
    n_p = len(tok(p, add_special_tokens=False).input_ids); n_t = len(tok(t, add_special_tokens=False).input_ids)
    n_pt = len(tok(p + t, add_special_tokens=False).input_ids)
    if n_pt > HARD: fail("C6", i, f"{n_pt} 토큰")
    if not t.strip(): fail("C6", i, "정답 비어있음")
    # C12 토큰 경계
    if n_p + n_t != n_pt: fail("C12", i, f"경계 병합 {n_p}+{n_t}≠{n_pt}")
    # C1/C3 정답 익명 이름 ⊂ 프롬프트
    for nm in set(ANON.findall(t)):
        if not re.search(r"(?<![\w'])" + re.escape(nm) + r"(?![\w'])", p):
            fail("C3" if "+var" in case else "C1", i, f"{nm} 프롬프트에 없음")
    # C2 실명 누출
    blocks_txt = "\n".join("\n".join(S.get(h_, [])) for h_ in BLK)
    for anon_nm, st in re.findall(r"^" + _KW + r"\s+(_L\d+)\s*:\s*(.*)$", blocks_txt, re.M):
        st_n = " ".join(st.rstrip(".").split())
        if len(st_n) >= 170: continue        # 진술 절단(180자) 근처 — 다른 lemma 의 잘린 진술과 충돌 (오탐원)
        real = stmt2name.get(st_n[:180])
        if not real or is_stdlib_name(real): continue
        if re.search(r"(?<![\w'])" + re.escape(real) + r"(?![\w'])", p + "\n" + t):
            dup_decl = re.search(r"^" + _KW + r"\s+\S*(?<![\w'])" + re.escape(real) + r"(?![\w'])\s*:", blocks_txt, re.M)
            if dup_decl: fail("C2", i, f"{real}→{anon_nm} 블록 내 실명·익명 중복 선언")
            else: C["C2 검토(블록 밖 실명 등장 — 동일 진술 딴 lemma 또는 PROOFS 본문)"] += 1
    # C11 채널 정확성 + C10 주입 위치
    if case.startswith(("A", "B")) and "+var" not in case and r.get("form") in FORM_BLK:
        h = FORM_BLK[r["form"]]; body = [l for l in S.get(h, []) if l.strip() and l.strip() != "none"]
        gold_names = set(re.findall(r"\b(?:e?apply|e?rewrite|exact)\s+(?:<-\s*)?(?:\(\s*)?([A-Za-z_][\w'.]*)", t))
        gold_names |= {g for g in (r.get("gold") or [])}          # `rewrite X, Y` 쉼표 목록은 풀 gold 필드가 정확하다
        gb = set().union(*(alias_set(g.rstrip(".").split(".")[-1]) for g in gold_names)) if gold_names else set()
        pos = [j for j, l in enumerate(body) if (m := DECL.match(l)) and m.group(1).split(".")[-1] in gb]
        if not pos: fail("C11", i, f"{r['form']} gold {sorted(gb)[:2]} 가 {h} 에 없음")
        elif case.startswith("B") and "+var" not in case and body: inj_pos.append(pos[0] / max(len(body), 1))
    # C8 실명 정답 분류
    for nm in re.findall(r"\b(?:e?apply|e?rewrite|exact)\s+(?:<-\s*)?(?:\(\s*)?([A-Za-z_][\w'.]*)", t):
        b = nm.rstrip(".").split(".")[-1]
        if b.startswith("_") or is_stdlib_name(b) or is_stdlib_name(nm.rstrip(".")): continue
        decl = len(re.findall(r"^(?:Lemma|Theorem|Definition|Fixpoint|Instance)\s+\S*" + re.escape(b) + r"\b", p, re.M))
        hyp = any(re.match(r"^[^:]*(?<![\w'])" + re.escape(b) + r"(?![\w'])[^:]*:", l) for l in S.get("STATE", []))
        if decl < 2 and not hyp: C["C8 검토(실명·비stdlib·단일선언)"] += 1; fails["C8?"].append((i, nm))
    # C13 변형 rule
    if "+var" in case and r.get("rule") in RULE_HEAD:
        if not t.strip().startswith(RULE_HEAD[r["rule"]]): fail("C13", i, f"{r['rule']} vs {t.strip()[:30]!r}")
# C7 지점 구조·셔플
for key, ids in by_pt.items():
    if len({rows[i]["prompt"] for i in ids}) != 1: fail("C7", ids[0], "같은 지점 프롬프트 불일치")
    if len([i for i in ids if "+var" not in rows[i]["case"]]) != 1: fail("C7", ids[0], "원본 행 ≠ 1")
    base_i = [i for i in ids if "+var" not in rows[i]["case"]]
    if base_i:
        base_set = set(ANON.findall(rows[base_i[0]]["target"]))
        for i in ids:
            if not set(ANON.findall(rows[i]["target"])) <= base_set:
                fail("C3", i, f"변형이 원본에 없는 익명 이름 사용"); break
for i in range(1, len(rows)):
    a, b = rows[i - 1], rows[i]
    if len(by_pt) > 1 and (a["proj"], a["thm"], a["thmi"], a["k"]) == (b["proj"], b["thm"], b["thmi"], b["k"]):
        fail("C7", i, "인접 행이 같은 지점"); break
# C10 주입 위치 분포
if len(inj_pos) >= 20:
    hist = collections.Counter(int(x * 4) for x in inj_pos)     # 4분위
    if max(hist.values()) / len(inj_pos) >= 0.6: fail("C10", -1, f"주입 위치 편중 {dict(hist)}")
    C["C10 주입 4분위"] = str(dict(sorted(hist.items())))
else:
    C["C10 표본부족"] = len(inj_pos)

# C16 TRAIN 데이터에 VAL/TEST/CUTOFF 저장소가 없어야 한다 (누출 방지 — 2026-09-02 적발 후 상설 검사)
import sys as _sys; _sys.path.insert(0, "scripts")
from train_repos import leaky as _leaky
for i, r in enumerate(rows):
    if _leaky(r.get("proj") or ""): fail("C16", i, r["proj"])

print("■ 결과:", {k: v for k, v in sorted(C.items())})
for code, lst in fails.items():
    print(f"  {code}: {len(lst)}건  예) {lst[:3]}")
hard_fail = [c for c in fails if c != "C8?"]
if "--drop-out" in sys.argv:
    # 잔여 실패 행의 인덱스를 기록 — 상위 단계가 **지점 단위**로 제거한다 (C11 류는 환각을 가르치는 행)
    of = sys.argv[sys.argv.index("--drop-out") + 1]
    bad_rows = sorted({i for c in hard_fail for i, _ in fails[c] if isinstance(i, int) and i >= 0})
    open(of, "w").write("\n".join(map(str, bad_rows)) + ("\n" if bad_rows else ""))
    print(f"드롭 후보 {len(bad_rows)}행 → {of}")
assert not hard_fail, f"검사 실패: {hard_fail}"
print("SFT_CHECK_OK")
