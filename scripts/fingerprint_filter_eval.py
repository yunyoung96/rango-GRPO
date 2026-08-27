"""**건전한(sound)** 지문 필터 — 확실히 불가능할 때만 쳐낸다.

usable_thmflags 는 "매칭 못 하겠다"를 False 로 돌려줘서 gold 를 떨어뜨렸다.
지문색인(Schulz 2012)의 핵심은 **soundness** 다 — 불일치가 비유니피케이션의
**필요조건**일 때만 쳐낸다. 여기서는 그 최소판을 만든다:

  apply   : goal 결론의 **머리기호**와 lemma 결론의 머리기호가 **둘 다 경직(rigid)** 이고
            다를 때만 쳐낸다. 한쪽이 변수·evar·미지이면 통과.
  rewrite : lemma 좌변(또는 우변) 머리기호가 goal의 **어떤 부분항 머리**에도 없을 때만 쳐낸다.
"""
import os,re,sys,yaml,logging,json,collections
os.environ.setdefault("HF_HUB_OFFLINE","1"); os.environ.setdefault("CUTS_ALLOW_PARTIAL","1")
os.environ["CUDA_VISIBLE_DEVICES"]=""
sys.path.insert(0,"src"); sys.path.insert(0,"CoqStoq"); logging.disable(logging.CRITICAL)
from pathlib import Path
from coqstoq import Split as CSSplit, get_theorem
from data_management.sentence_db import SentenceDB
from evaluation.find_coqstoq_idx import get_thm_desc
from tactic_gen.lm_example import formatter_from_conf
from tactic_gen.tactic_data import TacticDataConf
NTHM=int(os.environ.get("FP_N","60")); SH=int(os.environ.get("FP_SHARD","0")); NS=int(os.environ.get("FP_NSHARD","1"))
CONF=yaml.safe_load(open("all_log/ft_qwen3b_v10_conf.yaml"))
td=TacticDataConf.from_yaml(CONF["tactic_data"])
sdb=SentenceDB.load(Path("raw-data/coqstoq-test/coqstoq-test-sentences.db"))
fm=formatter_from_conf(td.formatter_conf); pc=fm.premise_client
DECL=re.compile(r"^\s*(?:Local\s+|Global\s+|Program\s+)?(?:Lemma|Theorem|Definition|Corollary|Fixpoint|Inductive|Remark|Proposition|Instance|Record|Axiom)\s+([A-Za-z_][\w']*)")
NAMED=re.compile(r"\b(?:e?apply|e?rewrite)\s+(?:<-\s*)?\(?\s*([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
HEADT=re.compile(r"^\s*(?:now\s+|try\s+|repeat\s+)?([A-Za-z_][\w']*)")
ID=re.compile(r"@?([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
def heads(t):
    """항 문자열에서 **적용 머리**로 보이는 식별자 집합 (괄호 바로 뒤·문두)."""
    out=set()
    for m in re.finditer(r"(?:^|[(\[{,;]|\s)\s*@?([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)", t):
        n=m.group(1)
        out.add(n); out.add(n.split(".")[-1])
    return out
KW={"forall","exists","fun","let","in","match","with","end","if","then","else","Prop","Type","Set","True","False"}
def concl_head(stmt):
    """lemma 선언문의 **결론 머리기호**. 못 정하면 None(=통과)."""
    s=re.sub(r"^\s*\w+\s+[\w']+\s*","",stmt.strip(),count=1)
    s=s.split(":",1)[-1] if ":" in s else s
    parts=re.split(r"->|→",s)
    c=parts[-1].strip().rstrip(".")
    c=re.sub(r"^\(|\)$","",c).strip()
    m=ID.match(c)
    if not m: return None
    n=m.group(1)
    return None if n in KW else n.split(".")[-1]
def goal_heads(g):
    c=g.goal
    parts=re.split(r"->|→",c); tail=parts[-1]
    m=ID.match(tail.strip())
    top=(m.group(1).split(".")[-1] if m and m.group(1) not in KW else None)
    return top, heads(c)
idx_all=[int(x) for x in Path("data/compcert_bs2_rand200_idx.txt").read_text().split()][:NTHM]
mine=[i for j,i in enumerate(idx_all) if j%NS==SH]
S=collections.Counter(); out=[]
for i in mine:
    try:
        thm=get_theorem(CSSplit.TEST,i,Path("CoqStoq")); d=get_thm_desc(thm,Path("raw-data/coqstoq-test"),sdb)
        if d is None: continue
        proof=d.dp.proofs[d.idx]
    except Exception: continue
    ks=[k for k,st in enumerate(proof.steps)
        if HEADT.match(st.step.text or "") and HEADT.match(st.step.text).group(1) in ("apply","eapply","rewrite","erewrite") and NAMED.search(st.step.text or "")]
    if len(ks)>4: stp=len(ks)/4; ks=[ks[int(j*stp)] for j in range(4)]
    for k in ks:
        try:
            step=proof.steps[k]
            gold=NAMED.search(step.step.text).group(1); gb=gold.split(".")[-1]
            head=HEADT.match(step.step.text).group(1)
            fr=pc.premise_filter.get_pos_and_avail_premises(step,proof,d.dp)
            av=list(fr.avail_premises)
            if not av or not step.goals: continue
            ranked=pc.get_ranked_premises(k,proof,d.dp,av,False)
            texts=[getattr(p,"text","") or "" for p in ranked]
            names=[(DECL.match(t).group(1) if DECL.match(t) else None) for t in texts]
            try: rb=next(j for j,n in enumerate(names) if n and n in (gold,gb))
            except StopIteration: continue
            gtop,ghs=goal_heads(step.goals[0])
            keep=[]
            for j,t in enumerate(texts):
                ch=concl_head(t)
                if head in ("apply","eapply"):
                    ok = (ch is None) or (gtop is None) or (ch==gtop)
                else:
                    ok = (ch is None) or (ch in ghs)
                if ok: keep.append(j)
            gk = rb in keep
            ra = keep.index(rb) if gk else None
            S["스텝"]+=1; S["풀"]+=len(texts); S["통과"]+=len(keep); S["살아남음"]+=gk
            S["b100"]+= (rb<100); S["a100"]+= (ra is not None and ra<100)
            S["오름"]+= (ra is not None and ra<rb)
            if not gk: out.append((gold,rb,gtop,concl_head(texts[rb])))
        except Exception: S["오류"]+=1
n=max(S["스텝"],1)
print(f"■ 건전 지문 필터 · 스텝 {S['스텝']} (오류 {S['오류']})")
print(f"   ① 재현율  {S['살아남음']}/{n} = {S['살아남음']/n*100:.1f}%")
print(f"   ② 축소율  {S['풀']/n:,.0f} → {S['통과']/n:,.0f}  ({S['통과']/max(S['풀'],1)*100:.1f}%, {S['풀']/max(S['통과'],1):.1f}배)")
print(f"   ③ top-100 {S['b100']/n*100:.1f}% → {S['a100']/n*100:.1f}%  ({(S['a100']-S['b100'])/n*100:+.1f}pp) · 순위오름 {S['오름']}")
for g,rb,gt,ch in out[:8]: print(f"      떨굼 {g:30s} {rb:4d}위  goal머리={gt} lemma결론머리={ch}")
