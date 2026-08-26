#!/usr/bin/env python3
"""gold lemma 를 못 쓸 때 모델은 **대신 무엇을 쓰나** — CPU 전용(생성 없음).

오라클 jsonl 에 저장된 A 팔 생성물을 읽고, 같은 스텝의 **검색된 100 premise** 를
재구성해서 생성물 안의 이름이 어디서 왔는지 가른다.

  gold          gold lemma 를 씀
  검색된 다른 것   검색 목록에 있는 **다른** lemma 를 씀
  검색 밖 실재     검색엔 없지만 선언이 실제로 존재하는 이름 (파라메트릭 기억)
  환각           선언이 어디에도 없는 이름
  이름 없음       인자 없는 tactic (auto/lia/unfold/…)

사용: WI_SHARD/WI_NSHARD  WI_OUT  python3 scripts/what_instead.py <jsonl...>
"""
import collections, json, os, re, sqlite3, sys, yaml, logging
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")
os.environ["CUDA_VISIBLE_DEVICES"] = ""
sys.path.insert(0, "src"); sys.path.insert(0, "CoqStoq")
logging.disable(logging.CRITICAL)
from pathlib import Path
from coqstoq import Split as CSSplit, get_theorem
from data_management.sentence_db import SentenceDB
from evaluation.find_coqstoq_idx import get_thm_desc
from tactic_gen.lm_example import formatter_from_conf
from tactic_gen.tactic_data import TacticDataConf

SHARD = int(os.environ.get("WI_SHARD", "0"))
NSHARD = int(os.environ.get("WI_NSHARD", "1"))
OUT = Path(os.environ.get("WI_OUT", "all_log/what_instead.jsonl"))
CONF = yaml.safe_load(open("all_log/ft_qwen3b_v9_conf.yaml"))
td = TacticDataConf.from_yaml(CONF["tactic_data"])
DATA_LOC = Path("raw-data/coqstoq-test")
SDB_LOC = Path("raw-data/coqstoq-test/coqstoq-test-sentences.db")
sdb = SentenceDB.load(SDB_LOC)
formatter = formatter_from_conf(td.formatter_conf)

_con = sqlite3.connect(str(SDB_LOC))
_dcache = {}
def has_decl(bare):
    if bare in _dcache: return _dcache[bare]
    hit = False
    for kw in ("Lemma", "Theorem", "Definition", "Corollary", "Fixpoint",
               "Inductive", "Remark", "Proposition", "Instance", "Record"):
        for pat in (f"{kw} {bare}:%", f"{kw} {bare} %"):
            if _con.execute("SELECT 1 FROM sentence WHERE text LIKE ? LIMIT 1", (pat,)).fetchone():
                hit = True; break
        if hit: break
    _dcache[bare] = hit
    return hit

NAMED = re.compile(r"\b(?:e?apply|e?rewrite|exact|unfold|specialize|generalize|refine|"
                   r"destruct|induction|pose\s+proof|inversion|case)\s+(?:<-\s*)?\(?\s*"
                   r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
HEAD = re.compile(r"^\s*(?:now\s+|try\s+|repeat\s+)?([A-Za-z_][\w']*)")
DECL = re.compile(r"^\s*(?:Local\s+|Global\s+|Program\s+)?"
                  r"(?:Lemma|Theorem|Definition|Corollary|Fixpoint|Inductive|Remark|"
                  r"Proposition|Instance|Record|Axiom|Parameter)\s+([A-Za-z_][\w']*)")
def lemma_names(s):
    return {m.group(1) for m in NAMED.finditer(s or "")
            if len(m.group(1)) > 2 and not re.fullmatch(r"[A-Z]\d*", m.group(1))}
def prem_names(prems):
    out = set()
    for p in prems or []:
        m = DECL.match(p or "")
        if m: out.add(m.group(1))
    return out

recs = []
for f in sys.argv[1:]:
    for ln in Path(f).open():
        ln = ln.strip()
        if ln: recs.append(json.loads(ln))
by_thm = collections.defaultdict(list)
for r in recs: by_thm[r["idx"]].append(r)
thms = sorted(by_thm)
mine = [t for j, t in enumerate(thms) if j % NSHARD == SHARD]
print(f"■ 담당 {len(mine)}/{len(thms)} 정리 · 스텝 {sum(len(by_thm[t]) for t in mine)}", flush=True)

fout = OUT.open("w"); done = 0
for i in mine:
    try:
        thm = get_theorem(CSSplit.TEST, i, Path("CoqStoq"))
        desc = get_thm_desc(thm, DATA_LOC, sdb)
        if desc is None: continue
        dp, pidx = desc.dp, desc.idx
    except Exception:
        continue
    for r in by_thm[i]:
        try:
            ex = formatter.example_from_step(r["k"], pidx, dp, training=False)
            P = prem_names(ex.premises)
            Pbare = {n.split(".")[-1] for n in P}
            gname = r["gname"]; gbare = gname.split(".")[-1]
            outs = []
            for cand in r["A"]:
                nm = lemma_names(cand)
                head = (HEAD.match(cand).group(1) if HEAD.match(cand) else "?")
                cls = []
                for n in sorted(nm):
                    b = n.split(".")[-1]
                    if b == gbare or n == gname: cls.append(("gold", n))
                    elif n in P or b in Pbare:   cls.append(("검색된 다른 것", n))
                    elif has_decl(b):            cls.append(("검색 밖 실재", n))
                    else:                        cls.append(("환각", n))
                outs.append(dict(text=cand, head=head, names=cls))
            fout.write(json.dumps(dict(idx=i, k=r["k"], gold=r["gold"], gname=gname,
                                       in_prompt=r["in_prompt"], decl_how=r["decl_how"],
                                       okA=r["okA"], hitA=r["hitA"], okB=r["okB"],
                                       hitB=r["hitB"], okC=r["okC"],
                                       gold_in_prem=(gname in P or gbare in Pbare),
                                       nprem=len(ex.premises or []), outs=outs),
                                  ensure_ascii=False) + "\n")
        except Exception as e:
            fout.write(json.dumps(dict(idx=i, k=r["k"], err=str(e)[:120]), ensure_ascii=False) + "\n")
    done += 1; fout.flush()
    if done % 5 == 0: print(f"   … {done}/{len(mine)}", flush=True)
print("DONE", flush=True)
