#!/usr/bin/env python3
"""★ **검색이 문제인가, 조립이 문제인가** — 오라클로 갈라 본다.

`next_step_eval.py` 가 "도달성 실패 52%"를 냈다. 그런데 그게
  (a) 검색이 그 lemma 를 프롬프트에 안 실어서인지
  (b) 실렸는데도 모델이 못 골라서인지
구분이 안 됐다. 여기서 네 갈래로 가른다.

  [검색] gold lemma 이름이 **프롬프트에 실려 있나**            ← (a)/(b) 를 가른다
  A 자연     평소대로 생성                                   ← 기준선
  B 오라클검색 gold lemma 를 [PREMISES] 맨 앞에 **꽂고** 생성   ← 검색이 완벽하면?
  C 오라클이름 `<head> <lemma>` 까지 **써 주고** 나머지만 생성  ← 순수 조립 능력

사용: PYTHONPATH=src python3 scripts/oracle_lemma_eval.py <ckpt> [정리수]
환경: OL_GPU · OL_SHARD/OL_NSHARD · OL_N(후보, 기본 8) · OL_MAX_PER_THM · OL_OUT
"""
import collections
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")
os.environ["CUDA_VISIBLE_DEVICES"] = os.environ.get("OL_GPU", "0")
sys.path.insert(0, "src")
sys.path.insert(0, "CoqStoq")
import logging  # noqa: E402
logging.disable(logging.CRITICAL)

import yaml  # noqa: E402
from coqstoq import Split as CSSplit, get_theorem  # noqa: E402
from data_management.sentence_db import SentenceDB  # noqa: E402
from evaluation.find_coqstoq_idx import get_thm_desc  # noqa: E402
from tactic_gen.lm_example import formatter_from_conf  # noqa: E402
from tactic_gen.tactic_data import (TacticDataConf, example_collator_from_conf,  # noqa: E402
                                    example_collator_conf_from_yaml, last_inference_mapping)
from tactic_gen.normalize_names import apply_inverse  # noqa: E402
from model_deployment.model_wrapper import DecoderLocalWrapper  # noqa: E402

CKPT = sys.argv[1]
NTHM = int(sys.argv[2]) if len(sys.argv) > 2 else 200
NCAND = int(os.environ.get("OL_N", "8"))
SHARD = int(os.environ.get("OL_SHARD", "0"))
NSHARD = int(os.environ.get("OL_NSHARD", "1"))
MAXPT = int(os.environ.get("OL_MAX_PER_THM", "4"))
OUT = Path(os.environ.get("OL_OUT", "all_log/oracle_lemma.jsonl"))
OUT.parent.mkdir(parents=True, exist_ok=True)

CONF = yaml.safe_load(open("all_log/ft_qwen3b_v9_conf.yaml"))
td = TacticDataConf.from_yaml(CONF["tactic_data"])
DATA_LOC = Path("raw-data/coqstoq-test")
SDB_LOC = Path("raw-data/coqstoq-test/coqstoq-test-sentences.db")
sdb = SentenceDB.load(SDB_LOC)
formatter = formatter_from_conf(td.formatter_conf)
collator = example_collator_from_conf(
    example_collator_conf_from_yaml(CONF["tactic_data"]["collator_conf"]))
wrapper = DecoderLocalWrapper.from_checkpoint(Path(CKPT), normalize_inference=True)
tok = wrapper.tokenizer
print(f"■ {CKPT} · hard={wrapper.hard_seq_len} · 후보 {NCAND}", flush=True)

# ── gold lemma 의 **선언문**을 sentence DB 에서 찾는다 ────────────────────
_con = sqlite3.connect(str(SDB_LOC))
_cache: dict = {}
def decl_text(name: str):
    """`Pregmap.gso` 같은 한정이름의 **선언문**. 못 찾으면 (None, "없음").

    ★ 맨 이름으로 찾으면 안 된다 - `gso` 는 PTree/PMap/IMap/EMap/ITree 에 전부 있다.
      엉뚱한 명제를 꽂으면 오라클 실험 자체가 무효가 된다. 세 단계로 좁힌다:
        (1) 한정자(Pregmap)가 module 컬럼에 있는 것  -> "정확"
        (2) 같은 프로젝트(compcert) 파일 안의 것      -> "프로젝트"
        (3) 아무거나                                 -> "모호"
      (1)이 안 잡히는 대표 사례가 **펑터 인스턴스**다(Pregmap 은 module 컬럼에 없다).
    """
    if name in _cache:
        return _cache[name]
    parts = name.split(".")
    bare = parts[-1]
    qual = parts[-2] if len(parts) > 1 else None
    pats = [f"Lemma {bare}:%", f"Lemma {bare} %", f"Theorem {bare}:%",
            f"Theorem {bare} %", f"Definition {bare}:%", f"Definition {bare} %",
            f"Corollary {bare}:%", f"Corollary {bare} %"]

    def q(extra, args):
        for pat in pats:
            r = _con.execute(
                "SELECT text FROM sentence WHERE text LIKE ?" + extra + " LIMIT 1",
                (pat,) + args).fetchone()
            if r:
                return r[0]
        return None

    got, how = None, "없음"
    if qual:
        got = q(" AND module LIKE ?", ("%" + qual + "%",))
        if got:
            how = "정확"
    if got is None:
        got = q(" AND file_path LIKE ?", ("%compcert%",))
        if got:
            how = "프로젝트"
    if got is None:
        got = q("", ())
        if got:
            how = "모호"
    _cache[name] = (got, how)
    return _cache[name]

NAMED = re.compile(r"\b(?:e?apply|e?rewrite|exact|unfold|specialize|generalize|refine|"
                   r"destruct|induction|pose\s+proof|inversion|case)\s+(?:<-\s*)?\(?\s*"
                   r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
HEAD = re.compile(r"^\s*(?:now\s+|try\s+|repeat\s+)?([A-Za-z_][\w']*)")
_WS = re.compile(r"\s+")
def norm(s): return _WS.sub(" ", (s or "").strip()).rstrip(".").strip()
def lemma_names(s):
    return {m.group(1) for m in NAMED.finditer(s or "")
            if len(m.group(1)) > 2 and not re.fullmatch(r"[A-Z]\d*", m.group(1))}

idx_all = [int(x) for x in Path("data/compcert_bs2_rand200_idx.txt").read_text().split()][:NTHM]
mine = [i for j, i in enumerate(idx_all) if j % NSHARD == SHARD]
print(f"   담당 {len(mine)} 정리", flush=True)

S = collections.Counter()
fout = OUT.open("w")
done = 0
for i in mine:
    try:
        thm = get_theorem(CSSplit.TEST, i, Path("CoqStoq"))
        desc = get_thm_desc(thm, DATA_LOC, sdb)
        if desc is None: continue
        dp, pidx = desc.dp, desc.idx
        steps = dp.proofs[pidx].steps
    except Exception:
        continue
    ks = []
    for kk in range(len(steps)):
        try: t = steps[kk].step.text
        except Exception: continue
        h = HEAD.match(t)
        if h and h.group(1) in ("apply", "eapply", "rewrite", "erewrite") and lemma_names(t):
            ks.append(kk)
    if not ks: continue
    if len(ks) > MAXPT:
        st = len(ks) / MAXPT
        ks = [ks[int(j * st)] for j in range(MAXPT)]

    for k in ks:
        try:
            ex = formatter.example_from_step(k, pidx, dp, training=False)
            gold = ex.next_steps[0]
            gl = lemma_names(gold)
            if not gl: continue
            gname = sorted(gl)[0]
            g = norm(gold)
            ghead = (HEAD.match(gold).group(1) if HEAD.match(gold) else "apply")

            # ── [검색] 그 이름이 프롬프트에 실렸나 (정규화 **전** 텍스트로 본다)
            plain = collator.collate_input(tok, ex, normalize=False)
            in_prompt = re.search(r"(?<![\w'])" + re.escape(gname) + r"(?![\w'])", plain) is not None
            _dt, _how = decl_text(gname)
            has_decl = _dt is not None

            # ── A. 자연
            rA = wrapper.get_recs(ex, NCAND, "", False, None).next_tactic_list
            hitA = bool(gl & set().union(*[lemma_names(c) for c in rA]) if rA else set())
            okA = g in [norm(c) for c in rA]

            # ── B. 오라클 검색: gold lemma 선언문을 premise 맨 앞에 꽂는다
            okB = hitB = None
            rB = []
            dt = _dt
            if dt:
                import copy as _copy
                ex2 = _copy.copy(ex)
                ex2.premises = [dt] + list(ex.premises or [])
                rB = wrapper.get_recs(ex2, NCAND, "", False, None).next_tactic_list
                hitB = bool(gl & set().union(*[lemma_names(c) for c in rB]) if rB else set())
                okB = g in [norm(c) for c in rB]

            # ── C. 오라클 이름: `<head> <lemma>` 까지 써 주고 나머지만 생성
            pr = collator.collate_input(tok, ex, normalize=True)
            m = last_inference_mapping()
            mapped = m.get(gname, gname) if m else gname
            forced = f"{ghead} {mapped}"
            cont = wrapper.generate_raw(pr + forced, NCAND, 64, 1.0)
            fullC = [apply_inverse(forced + c, m) if m else (forced + c) for c in cont]
            okC = g in [norm(x) for x in fullC]

            S["스텝"] += 1
            S["검색: 프롬프트에 있음"] += in_prompt
            S["검색: 선언 자체가 없음"] += (not has_decl)
            S["선언찾기:" + _how] += 1
            S["A 이름맞힘"] += hitA; S["A 완벽"] += okA
            if okB is not None:
                S["B 대상"] += 1; S["B 이름맞힘"] += hitB; S["B 완벽"] += okB
            S["C 완벽"] += okC
            fout.write(json.dumps(dict(idx=i, k=k, gold=gold, gname=gname,
                                       in_prompt=in_prompt, has_decl=has_decl, decl_how=_how,
                                       A=rA[:3], okA=okA, hitA=hitA,
                                       B=rB[:3], okB=okB, hitB=hitB, okC=okC,
                                       C=fullC[:3]), ensure_ascii=False) + "\n")
        except Exception:
            S["오류"] += 1
    done += 1; fout.flush()
    if done % 5 == 0: print(f"   … {done}/{len(mine)} (스텝 {S['스텝']})", flush=True)

n = max(S["스텝"], 1); nb = max(S["B 대상"], 1)
print(f"\n=== 오라클 실험 (스텝 {S['스텝']}) ===")
print(f"[검색] gold lemma 가 프롬프트에 실림   {S['검색: 프롬프트에 있음']:4d} = {S['검색: 프롬프트에 있음']/n*100:5.1f}%")
print("[검색] 선언 조회 품질: " + str({k: v for k, v in S.items() if k.startswith("선언찾기")}))
print(f"[검색] 그 이름의 **선언 자체가 없음**   {S['검색: 선언 자체가 없음']:4d} = {S['검색: 선언 자체가 없음']/n*100:5.1f}%")
print(f"A 자연        이름맞힘 {S['A 이름맞힘']/n*100:5.1f}%  ·  gold 일치 {S['A 완벽']/n*100:5.1f}%")
print(f"B 오라클검색   이름맞힘 {S['B 이름맞힘']/nb*100:5.1f}%  ·  gold 일치 {S['B 완벽']/nb*100:5.1f}%   (대상 {S['B 대상']})")
print(f"C 오라클이름   ── 이름을 써 줬을 때 나머지 조립 성공 {S['C 완벽']/n*100:5.1f}%")
json.dump(dict(S), open(str(OUT) + ".summary.json", "w"), ensure_ascii=False, indent=1)
