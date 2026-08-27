#!/usr/bin/env python3
"""★ **elaborate 된 lemma 타입**으로 필터를 다시 만든다 — 앞선 음성 결과의 재시도.

## 앞선 실패의 원인 (applicability-filter.md §2 를 **정정**한다)

떨어뜨린 gold 21건을 분류하니 **90%가 필터 구현 버그**였다:
    ① 결론 머리가 **전칭 변수**인데 경직 상수로 봤다   47.6%
    ② 중위 notation (`dm!id = Some gd` 의 진짜 머리는 `eq`)  42.9%
    ④ 진짜 elaboration 불일치                          9.5%

`Set Printing All` 은 ②를 펼쳐 주고, 바인더를 명시해 ①을 판정 가능하게 한다:
    dm!id = Some gd  →  @eq (option globdef) (@Maps.PTree.get _ id dm) (@Some _ gd)
    f (shl x n) …    →  forall (f : forall (_:Int.int)(_:Int.int), Int.int) …, @eq …

## 이 필터가 하는 일

  1. elaborate 타입에서 **바인더 이름**을 모은다 → 전칭 변수(와일드카드)
  2. 결론의 **머리기호**를 뽑는다. 그게 바인더면 → **무조건 통과**(어떤 것과도 매칭)
  3. 경직 상수면 goal 에 그 이름이 (맨이름 기준) 나오는지 본다. 없으면 쳐낸다

★ goal 은 여전히 **출력 형태**다(라이브 Coq 세션에서 오므로). 그래서 판정을
  머리기호 **맨이름 포함 여부**라는 느슨한 조건으로 둔다 — 건전성을 우선한다.

사용: EF_SPLIT=TEST EF_N=200 EF_SHARD/EF_NSHARD python3 scripts/elab_filter_eval.py
"""
import collections, json, os, re, sys, yaml, logging
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")
os.environ["CUDA_VISIBLE_DEVICES"] = ""
sys.path.insert(0, "src"); sys.path.insert(0, "CoqStoq")
logging.disable(logging.CRITICAL)
from pathlib import Path
from data_management.sentence_db import SentenceDB
from tactic_gen.lm_example import formatter_from_conf
from tactic_gen.tactic_data import TacticDataConf

N = int(os.environ.get("EF_N", "200"))
SHARD = int(os.environ.get("EF_SHARD", "0"))
NSHARD = int(os.environ.get("EF_NSHARD", "1"))
MAXPT = int(os.environ.get("EF_MAX_PER_THM", "4"))
ELAB = os.environ.get("EF_ELAB", "data/elab_compcert.jsonl")
OUT = Path(os.environ.get("EF_OUT", "all_log/elab_filter.jsonl"))

CONF = yaml.safe_load(open("all_log/ft_qwen3b_v10_conf.yaml"))
td = TacticDataConf.from_yaml(CONF["tactic_data"])
fm = formatter_from_conf(td.formatter_conf)
pc = fm.premise_client

# ── elaborate 색인 로드 ──────────────────────────────────────────────────────
ELABT = {}
for ln in open(ELAB):
    d = json.loads(ln)
    ELABT.setdefault(d["name"].split(".")[-1], d["type"])
print(f"■ elaborate 색인 {len(ELABT):,} 이름 ({ELAB})", flush=True)

ID = re.compile(r"@?([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
BIND = re.compile(r"[\(\[\{]\s*([^:\)\]\}]+?)\s*:")

def split_top(c):
    """괄호 깊이 0 에서 공백으로 쪼갠다 — `@eq T lhs rhs` 의 인자를 얻으려고."""
    out, buf, d = [], "", 0
    for ch in c:
        if ch in "([{":
            d += 1
        elif ch in ")]}":
            d -= 1
        if ch.isspace() and d == 0:
            if buf:
                out.append(buf); buf = ""
        else:
            buf += ch
    if buf:
        out.append(buf)
    return out

def head_of(term, binders):
    """항의 머리기호. 전칭 변수면 None(=와일드카드)."""
    t = term.strip()
    while t.startswith("(") and t.endswith(")"):
        t = t[1:-1].strip()
    m = ID.match(t)
    if not m:
        return None
    h = m.group(1)
    return None if (h in binders or h.split(".")[-1] in binders) else h.split(".")[-1]

def match_keys(ty, tac):
    """이 lemma 를 `tac` 으로 쓸 때 goal 에 **반드시 있어야 하는** 경직 머리들.

    빈 집합이면 = 판정 불가 → **통과**시킨다(건전성).

      apply    결론 머리 하나
      rewrite  결론이 `@eq T L R` / `iff A B` 면 **좌·우변의 머리** — `eq` 자체가 아니다.
               `rewrite L` 은 goal 의 부분항이 L 의 좌변과 매칭돼야 하지
               goal 머리가 `eq` 일 필요가 없다. (이걸 빠뜨려 iff 계열을 전부 떨궜다.)
    """
    binders = set()
    c = ty
    for _ in range(40):
        s = c.strip()
        if not s.startswith("forall"):
            break
        i = s.find(",")
        if i < 0:
            break
        for m in BIND.finditer(s[:i]):
            binders |= set(re.findall(r"[A-Za-z_][\w']*", m.group(1)))
        binders |= set(re.findall(r"[A-Za-z_][\w']*",
                                  re.sub(r"[\(\[\{][^)\]\}]*[\)\]\}]", " ", s[6:i])))
        c = s[i + 1:]
    c = c.strip()
    h = head_of(c, binders)
    if h is None:
        return set()                      # 전칭 변수 머리 → 무엇과도 매칭
    if tac in ("apply", "eapply"):
        return {h}
    # rewrite 계열 — 등식/동치의 **변** 을 본다
    if h in ("eq", "iff"):
        cc = c
        while cc.startswith("(") and cc.endswith(")"):
            cc = cc[1:-1].strip()
        parts = split_top(cc.lstrip("@"))
        sides = parts[2:] if h == "eq" and len(parts) >= 4 else parts[1:]
        ks = {head_of(x, binders) for x in sides}
        ks.discard(None)
        return ks if ks else set()        # 양변 다 변수면 통과
    return {h}

DECL = re.compile(r"^\s*(?:Local\s+|Global\s+|Program\s+)?"
                  r"(?:Lemma|Theorem|Definition|Corollary|Fixpoint|Inductive|Remark|"
                  r"Proposition|Instance|Record|Axiom|Fact|Property)\s+([A-Za-z_][\w']*)")
NAMED = re.compile(r"\b(?:e?apply|e?rewrite)\s+(?:<-\s*)?\(?\s*"
                   r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
HEADT = re.compile(r"^\s*(?:now\s+|try\s+|repeat\s+)?([A-Za-z_][\w']*)")
# ★ notation → 상수. `<=` 하나가 스코프에 따라 Rle·Z.le·le·Int.ltu … 로 갈린다.
#   goal 은 **출력 형태**라 스코프를 모르므로, 기호가 보이면 그 후보를 **전부** 넣는다
#   (건전성 우선 — 좁히려다 gold 를 떨어뜨리면 안 된다).
SYM2C = {"=": {"eq"}, "<->": {"iff"}, "/\\": {"and"}, "\\/": {"or"}, "~": {"not"},
         "<=": {"Rle", "Z.le", "le", "N.le", "Nat.le", "Pos.le"},
         "<": {"Rlt", "Z.lt", "lt", "N.lt", "Nat.lt", "Pos.lt"},
         ">=": {"Rge", "Z.ge", "ge"}, ">": {"Rgt", "Z.gt", "gt"},
         "+": {"Rplus", "Z.add", "plus", "Nat.add", "N.add"},
         "*": {"Rmult", "Z.mul", "mult", "Nat.mul", "N.mul"},
         "-": {"Rminus", "Z.sub", "minus", "Nat.sub"},
         "<>": {"not", "eq"}, "::": {"cons"}, "++": {"app"}}
EQV = {"eq": {"eq", "="}, "iff": {"iff", "<->"}, "and": {"and", "/\\"},
       "or": {"or", "\\/"}, "not": {"not", "~", "<>"}, "List.In": {"In"},
       "ex": {"exists"}, "sig": {"exists", "{"}, "sigT": {"exists", "{"}}

def goal_names(g):
    s = "\n".join(g.hyps) + "\n" + g.goal
    o = set()
    for m in re.finditer(r"@?([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)", s):
        o.add(m.group(1)); o.add(m.group(1).split(".")[-1])
    for sym, names in SYM2C.items():
        if sym in s:
            o |= names
    return o

def decl(t):
    m = DECL.match(t or "")
    return m.group(1) if m else None

print(f"■ TEST · 정리 {N} · 샤드 {SHARD}/{NSHARD}", flush=True)
from coqstoq import Split as CSSplit, get_theorem
from evaluation.find_coqstoq_idx import get_thm_desc
sdb = SentenceDB.load(Path("raw-data/coqstoq-test/coqstoq-test-sentences.db"))
ids = [int(x) for x in Path("data/compcert_bs2_rand200_idx.txt").read_text().split()][:N]
S = collections.Counter(); drop = []
fout = OUT.open("w")
for j, i in enumerate(ids):
    if j % NSHARD != SHARD:
        continue
    try:
        d = get_thm_desc(get_theorem(CSSplit.TEST, i, Path("CoqStoq")),
                         Path("raw-data/coqstoq-test"), sdb)
        if d is None:
            continue
        proof = d.dp.proofs[d.idx]
    except Exception:
        continue
    ks = [k for k, st in enumerate(proof.steps)
          if HEADT.match(st.step.text or "")
          and HEADT.match(st.step.text).group(1) in ("apply", "eapply", "rewrite", "erewrite")
          and NAMED.search(st.step.text or "")]
    if not ks:
        continue
    if len(ks) > MAXPT:
        stp = len(ks) / MAXPT
        ks = [ks[int(x * stp)] for x in range(MAXPT)]
    for k in ks:
        try:
            step = proof.steps[k]
            if not step.goals:
                continue
            gold = NAMED.search(step.step.text).group(1); gb = gold.split(".")[-1]
            pool = list(pc.premise_filter.get_pos_and_avail_premises(step, proof, d.dp).avail_premises)
            texts = [getattr(p, "text", "") or "" for p in pool]
            gi = next((x for x, t in enumerate(texts) if (decl(t) or "") in (gold, gb)), None)
            if gi is None:
                continue
            gn = goal_names(step.goals[0])
            _raw = step.step.text
            tacn = HEADT.match(_raw).group(1)
            tacn = "rewrite" if tacn.endswith("rewrite") else "apply"
            # ★ `apply L in H` / `rewrite L in H` 는 **전방추론**이다 — lemma 의 결론이
            #   goal 과 맞을 이유가 없다(H 를 바꾼다). 이 형태는 판정하지 않고 통과시킨다.
            _fwd = re.search(r"\bin\s+[A-Za-z_][\w']*", _raw) is not None
            keep, no_elab = [], 0
            for x, t in enumerate(texts):
                nm = decl(t)
                ty = ELABT.get((nm or "").split(".")[-1]) if nm else None
                if ty is None:
                    keep.append(x); no_elab += 1      # 색인에 없으면 통과(보수적)
                    continue
                ks = set() if _fwd else match_keys(ty, tacn)
                if (not ks) or any(kk in gn or (EQV.get(kk, set()) & gn) for kk in ks):
                    keep.append(x)
            S["스텝"] += 1; S["풀"] += len(texts); S["통과"] += len(keep)
            S["색인없음"] += no_elab
            S["gold생존"] += (gi in keep)
            S["gold색인있음"] += ((decl(texts[gi]) or "").split(".")[-1] in ELABT)
            if gi not in keep:
                ty = ELABT.get(gb, "")
                drop.append((gold, tacn, match_keys(ty, tacn) if ty else "색인없음"))
            fout.write(json.dumps(dict(idx=i, k=k, gold=gold, pool=len(texts),
                                       keep=len(keep), kept=(gi in keep)),
                                  ensure_ascii=False) + "\n")
        except Exception:
            S["오류"] += 1
    fout.flush()
n = max(S["스텝"], 1)
print(f"\n■ 스텝 {S['스텝']} (오류 {S['오류']})")
print(f"   ① gold 생존   {S['gold생존']}/{n} = {S['gold생존']/n*100:.1f}%")
print(f"   ② 축소율      {S['풀']/n:,.0f} → {S['통과']/n:,.0f}"
      f"  ({S['통과']/max(S['풀'],1)*100:.1f}% 남음, {S['풀']/max(S['통과'],1):.1f}배)")
print(f"   · 후보 중 elaborate 색인에 있던 것 {(S['풀']-S['색인없음'])/max(S['풀'],1)*100:.1f}%"
      f" · gold 이 색인에 있던 비율 {S['gold색인있음']/n*100:.1f}%")
for g, h, eh in drop[:10]:
    print(f"     떨굼 {g:32s} {h:8s} 요구키={eh}")
