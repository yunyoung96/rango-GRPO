#!/usr/bin/env python3
"""★ **next-step 예측** — gold prefix 를 오라클로 주고 **다음 한 수**만 맞히는가.

완주율(`gold_prefix_eval.py`)과 다른 질문이다. 거기서는 남은 증명 전부를 300초·
수백 회 재시도로 닫아야 했다. 여기서는 **그 자리에서 한 수**만 본다.

`[STATE]`·`[SCRIPT]` 는 gold 의 k번째 지점 그대로다(오라클). 즉 표류가 완전히
제거된 조건이고, 남는 것은 **"이 상태에서 옳은 수를 떠올리는가"** 하나다.

세 갈래로 나눠 센다 — 이게 이 실험의 목적이다.
    gold 가 lemma 이름을 쓰는 스텝에서
      · 이름을 맞히고 형태도 맞음   → 완벽
      · **이름은 맞혔는데 형태가 다름** → 조립 실패
      · **이름조차 안 나옴**          → 도달성 실패

사용: PYTHONPATH=src python3 scripts/next_step_eval.py <ckpt> [정리수] [비율,…]
환경: NS_GPU(기본 0) · NS_SHARD/NS_NSHARD(분할) · NS_N(후보 수, 기본 8) · NS_OUT
"""
import collections
import json
import os
import re
import sys
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")
os.environ["CUDA_VISIBLE_DEVICES"] = os.environ.get("NS_GPU", "0")
sys.path.insert(0, "src")
sys.path.insert(0, "CoqStoq")
import logging  # noqa: E402
logging.disable(logging.CRITICAL)

import yaml  # noqa: E402
from coqstoq import Split as CSSplit, get_theorem  # noqa: E402
from data_management.sentence_db import SentenceDB  # noqa: E402
from evaluation.find_coqstoq_idx import get_thm_desc  # noqa: E402
from tactic_gen.lm_example import formatter_from_conf  # noqa: E402
from tactic_gen.tactic_data import TacticDataConf  # noqa: E402
from model_deployment.model_wrapper import DecoderLocalWrapper  # noqa: E402

CKPT = sys.argv[1]
NTHM = int(sys.argv[2]) if len(sys.argv) > 2 else 200
RATIOS = [float(x) for x in (sys.argv[3].split(",") if len(sys.argv) > 3
                             else ["0", "0.2", "0.4", "0.6", "0.8", "0.9"])]
NCAND = int(os.environ.get("NS_N", "8"))
SHARD = int(os.environ.get("NS_SHARD", "0"))
NSHARD = int(os.environ.get("NS_NSHARD", "1"))
MODE = os.environ.get("NS_MODE", "ratio")   # ratio | named
MAXPT = int(os.environ.get("NS_MAX_PER_THM", "8"))
# ★ named 모드에서 볼 tactic 머리. 기본 = apply/rewrite 계열(인자 조립이 걸리는 곳).
_hs = os.environ.get("NS_HEADS", "apply,eapply,rewrite,erewrite")
_HEADS = set() if _hs.strip() == "all" else {x.strip() for x in _hs.split(",") if x.strip()}
OUT = Path(os.environ.get("NS_OUT", "all_log/next_step.jsonl"))

# ── ★ 필터 풀 주입 (파이썬 변수 — 환경변수 아님) ────────────────────────────
#   OCaml 플러그인(`ocaml/applic`)이 커널 단일화로 걸러 낸 후보를 프롬프트에 태운다.
#   비워 두면 현행 그대로다(동작이 안 바뀐다).
#     "union"  현행 풀 ∪ 필터 결과 → 같은 tf-idf 로 재랭킹
#     "only"   필터 결과만
POOL_FILE = "all_log/dn_pool_snapshot.jsonl"
POOL_MODE = "union"   # 현행 ∪ 필터결과 → 같은 tf-idf 로 재랭킹

# ── ★★ gold lemma 강제 주입 (오라클) ─────────────────────────────────────
#   검색을 **완전히 배제**하고 조립 능력만 잰다.
#     gold prefix state + **정답 lemma 를 프롬프트 맨 앞에 억지로 삽입**
#     → 모델이 gold tactic 을 조립해 내는가
#   랭킹은 상관없다. 정답이 프롬프트에 실려 있기만 하면 된다.
#   이렇게 하면 "도달성 실패" 가 0 이 되고 남는 것은 **조립 실패** 뿐이다.
INJECT_GOLD = False
INJECT_VERIFY = True    # 실제로 프롬프트에 실렸는지 확인해서 따로 센다
OUT.parent.mkdir(parents=True, exist_ok=True)

CONF = yaml.safe_load(open("all_log/ft_qwen3b_v9_conf.yaml"))
# ★ conf 의 sentence_db 는 **학습용**(`/tmp/coq-dataset`)을 가리킨다. 그 경로는
#   tmpfs 초기화로 사라졌고, 애초에 평가에는 CoqStoq TEST 를 써야 한다.
#   포매터를 만들기 **전에** 덮어써야 한다 — 안 그러면 로드에서 죽는다.
_T = "raw-data/coqstoq-test/coqstoq-test-sentences.db"
_D = "raw-data/coqstoq-test"
CONF["tactic_data"]["sentence_db_loc"] = _T
CONF["tactic_data"]["data_loc"] = _D
for _k in ("premise", "proof_ret"):
    _c = CONF["tactic_data"]["formatter_conf"].get(_k)
    if isinstance(_c, dict):
        if "sentence_db_loc" in _c: _c["sentence_db_loc"] = _T
        if "data_loc" in _c: _c["data_loc"] = _D
td = TacticDataConf.from_yaml(CONF["tactic_data"])
# ★★ CoqStoq TEST 정리는 **평가용 데이터셋**에 있다 — 학습용 /tmp/coq-dataset 이 아니다.
#   데이터포인트 이름 규칙부터 다르다: 평가용은 `compcert-…`, 학습용은 `AbsInt-CompCert-…`.
#   (run_thm.py get_data_loc/get_sentence_db_loc 가 쓰는 것과 **같은 경로**를 써야
#    프롬프트가 평가 파이프라인과 일치한다.)
DATA_LOC = Path("raw-data/coqstoq-test")
SDB_LOC = Path("raw-data/coqstoq-test/coqstoq-test-sentences.db")
sdb = SentenceDB.load(SDB_LOC)
formatter = formatter_from_conf(td.formatter_conf)
_pc = formatter.premise_client
from tactic_gen.tactic_data import (example_collator_from_conf,  # noqa: E402
                                    example_collator_conf_from_yaml, get_tokenizer)
_col = example_collator_from_conf(
    example_collator_conf_from_yaml(CONF["tactic_data"]["collator_conf"]))
_tok = get_tokenizer(td.model_name)
# 래퍼와 **같은** 정규화 설정을 쓴다 — 어긋나면 검증이 헛것을 본다
_NORM = True

POOL = {}
if POOL_FILE and os.path.exists(POOL_FILE):
    from premise_selection import coq_search_pool as _CSP
    for _ln in open(POOL_FILE):
        _ln = _ln.strip()
        if not _ln:
            continue
        _d = json.loads(_ln)
        _st = _d.get("stmts") or {}
        POOL[(_d["idx"], _d["k"])] = [f"Lemma {a} : {b}." for a, b in _st.items() if b]
    print(f"■ 필터 풀 {len(POOL):,} 지점 · 모드 {POOL_MODE}", flush=True)


_DECLRE = re.compile(r"^\s*(?:Local\s+|Global\s+|Program\s+)?"
                    r"(?:Lemma|Theorem|Corollary|Remark|Definition|Fixpoint|Inductive|"
                    r"Proposition|Instance|Record|Axiom|Fact|Property)\s+([A-Za-z_][\w'.]*)")


def _find_decl(name, pool):
    """풀에서 그 이름의 선언문을 찾는다. 없으면 None."""
    nb = name.split(".")[-1]
    for p in pool:
        t = getattr(p, "text", "") or ""
        m = _DECLRE.match(t)
        if m and (m.group(1) == name or m.group(1).split(".")[-1] == nb):
            return t
    return None


_DBCON = None
_DECLKW = ("Lemma", "Theorem", "Corollary", "Remark", "Proposition",
           "Fact", "Property", "Definition", "Axiom", "Instance")


def _decl_from_db(name):
    """문장 DB 에서 선언문을 찾는다 (stdlib 폴백).

    현행 풀은 프로젝트 선언만 담으므로 stdlib gold 은 주입 자체가 불가능했다.
    DB 에는 53,387 문장이 있고 stdlib 도 들어 있다."""
    global _DBCON
    import sqlite3
    if _DBCON is None:
        _DBCON = sqlite3.connect(str(SDB_LOC), check_same_thread=False)
    nb = name.split(".")[-1]
    cur = _DBCON.cursor()
    for kw in _DECLKW:
        cur.execute("SELECT text FROM sentence WHERE text LIKE ? LIMIT 1",
                    (f"{kw} {nb} %",))
        r = cur.fetchone()
        if r:
            t = " ".join((r[0] or "").split())
            if not t.endswith("."): t += "."
            return t
    for kw in _DECLKW:
        cur.execute("SELECT text FROM sentence WHERE text LIKE ? LIMIT 1",
                    (f"{kw} {nb}:%",))
        r = cur.fetchone()
        if r:
            t = " ".join((r[0] or "").split())
            if not t.endswith("."): t += "."
            return t
    return None


def _inject_gold(ex, gold, dp, pidx, k):
    """★ 정답 lemma 를 프롬프트 **맨 앞**에 억지로 넣는다.

    반환: (예제, 상태)   상태 ∈ {"넣음", "이미있음", "선언문없음"}
    맨 앞에 두는 이유는 토큰 예산 절단에서 살아남게 하려는 것이지
    랭킹 실험이 아니다 — 실려 있기만 하면 된다."""
    prem = list(ex.premises or [])
    nb = gold.split(".")[-1]
    for t in prem:
        m = _DECLRE.match(t or "")
        if m and (m.group(1) == gold or m.group(1).split(".")[-1] == nb):
            # 이미 있으면 맨 앞으로만 올린다
            prem.remove(t); ex.premises = [t] + prem
            return ex, "이미있음"
    try:
        proof = dp.proofs[pidx]
        base = list(_pc.premise_filter.get_pos_and_avail_premises(
            proof.steps[k], proof, dp).avail_premises)
    except Exception:
        base = []
    d = _find_decl(gold, base)
    if d is None:
        # ★ 현행 풀(`avail_premises`)은 **프로젝트 것만** 담는다 — stdlib 이 없다.
        #   실측: 주입 실패 180건 중 `Rle_trans`·`Z.gt_lt`·`eq_IZR`·`opp_IZR` 처럼
        #   stdlib 이 큰 덩어리였다. 문장 DB 에는 다 있으므로 거기서 찾는다.
        d = _decl_from_db(gold)
    if d is None:
        return ex, "선언문없음"
    ex.premises = [d] + prem
    return ex, "넣음"


def _in_prompt(ex, gold):
    """[PREMISES] 구간에 실제로 실렸나.

    ★ **익명화를 반드시 같이 켜야 한다.** 모델이 보는 프롬프트는
      `normalize=True` 로 만들어져 `PTree.gso` 가 `_L3` 로 바뀌어 있다.
      `normalize=False` 로 확인하면 실제와 다른 문자열을 보게 된다.
      정규화 매핑에서 gold 이 무엇으로 바뀌었는지 찾아 **그 이름**을 센다.

    ★ 프롬프트 전체가 아니라 `[PREMISES]` 구간만 본다 — 전체를 보면
      `[STATE]` 에 우연히 같은 이름이 있어 과대 계상된다(실측 83% 로 부풀었다).
    """
    from tactic_gen.tactic_data import last_inference_mapping
    try:
        s2 = _col.collate_input(_tok, ex, normalize=_NORM)
    except TypeError:
        s2 = _col.collate_input(_tok, ex)
    except Exception:
        return None
    nb = gold.split(".")[-1]
    target = nb
    if _NORM:
        m = last_inference_mapping() or {}
        # 매핑은 {원래이름: 익명이름} 이다. gold 이 익명화됐으면 그 이름을 찾는다.
        for k0, v0 in m.items():
            if k0 == gold or k0.split(".")[-1] == nb:
                target = v0
                break
    seg = s2.split("[PROOFS]")[0] if "[PROOFS]" in s2 else s2
    seg = seg.split("[PREMISES]")[-1]
    return bool(re.search(r"(?<![\w'])" + re.escape(target) + r"(?![\w'])", seg))


def _inject(ex, i, k, dp, pidx):
    """필터 결과를 풀에 넣고 **같은 랭커**로 다시 순위를 매긴다."""
    texts = POOL.get((i, k))
    if not texts:
        return ex
    from premise_selection import coq_search_pool as CSP
    try:
        proof = dp.proofs[pidx]
        step = proof.steps[k]
        extra = CSP.as_sentences(texts)
        if POOL_MODE == "only":
            pool = extra
        else:
            base = list(_pc.premise_filter.get_pos_and_avail_premises(
                step, proof, dp).avail_premises)
            pool = base + extra
        ranked = _pc.get_ranked_premises(k, proof, dp, pool, False)
        ex.premises = [getattr(p, "text", "") for p in ranked]
    except Exception:
        pass
    return ex
# ★ 래퍼가 체크포인트의 training_conf 를 이 프로세스에 전파한다(HARD_SEQ_LEN·OUT_TOKENS·
#   normalize_inference). 여기서 env 로 못박지 않는다 — 학습과 어긋나면 _L# 이 밀린다.
wrapper = DecoderLocalWrapper.from_checkpoint(Path(CKPT), normalize_inference=True)
_NORM = bool(wrapper.normalize_inference)
print(f"■ {CKPT}\n   hard_seq_len={wrapper.hard_seq_len} · normalize={wrapper.normalize_inference}"
      f" · 후보 {NCAND}개 · 비율 {RATIOS}", flush=True)

# gold 가 lemma 를 인자로 부르는 형태
NAMED = re.compile(r"\b(?:e?apply|e?rewrite|exact|unfold|specialize|generalize|refine|"
                   r"destruct|induction|pose\s+proof|inversion|case)\s+(?:<-\s*)?\(?\s*"
                   r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
_WS = re.compile(r"\s+")


def norm(s: str) -> str:
    return _WS.sub(" ", (s or "").strip()).rstrip(".").strip()


def lemma_names(s: str) -> set:
    """gold 스텝이 부르는 이름들. 한 글자·가설이름(H0 등)은 뺀다 — 정보가 없다."""
    out = set()
    for m in NAMED.finditer(s or ""):
        n = m.group(1)
        if len(n) > 2 and not re.fullmatch(r"[A-Z]\d*", n):
            out.add(n)
    return out


idx_all = [int(x) for x in Path("data/compcert_bs2_rand200_idx.txt").read_text().split()]
idx_all = idx_all[:NTHM]
mine = [i for j, i in enumerate(idx_all) if j % NSHARD == SHARD]
print(f"   담당 정리 {len(mine)}/{len(idx_all)} (shard {SHARD}/{NSHARD})", flush=True)

S = collections.defaultdict(collections.Counter)
fout = OUT.open("w")
done = 0
for i in mine:
    try:
        thm = get_theorem(CSSplit.TEST, i, Path("CoqStoq"))
        desc = get_thm_desc(thm, DATA_LOC, sdb)
        if desc is None:
            continue
        dp, pidx = desc.dp, desc.idx
        nsteps = len(dp.proofs[pidx].steps)
    except Exception:
        continue
    if nsteps < 3:
        continue
    # ★★ 어떤 스텝을 물어볼지 — 이게 실험의 성격을 정한다.
    #   ratio: gold 의 r 지점. 그런데 그 자리가 `intros.`·`auto.` 같은 일반 tactic 이면
    #          조립 능력이 안 드러난다(실측: 0% 지점의 90%가 intros).
    #   named: **gold 가 lemma 이름을 인자로 부르는 스텝만** 고른다.
    #          `apply L` · `rewrite L` · `unfold f` 처럼 인자를 조립해야 하는 자리다.
    #          한 정리가 표본을 독식하지 않게 고르게 MAXPT 개만 뽑는다.
    if MODE == "named":
        cand_k = []
        for kk in range(nsteps):
            try:
                t = dp.proofs[pidx].steps[kk].step.text
            except Exception:
                continue
            # ★ 기본은 apply/rewrite 계열만 — **인자 조립**이 걸리는 자리다.
            #   NS_HEADS 로 넓힐 수 있다(예: "all" 이면 이름 쓰는 스텝 전부).
            if not lemma_names(t):
                continue
            _h = re.match(r"\s*(?:now\s+|try\s+|repeat\s+)?([A-Za-z_][\w']*)", t)
            _h = _h.group(1) if _h else ""
            if _HEADS and _h not in _HEADS:
                continue
            cand_k.append(kk)
        if not cand_k:
            continue
        if len(cand_k) > MAXPT:
            step = len(cand_k) / MAXPT
            cand_k = [cand_k[int(j * step)] for j in range(MAXPT)]
        targets = [(kk / max(nsteps - 1, 1), kk) for kk in cand_k]
    else:
        targets = [(r, int(nsteps * r)) for r in RATIOS]

    for r, k in targets:
        if k >= nsteps:
            continue
        try:
            ex = formatter.example_from_step(k, pidx, dp, training=False)
            if POOL:
                ex = _inject(ex, i, k, dp, pidx)
            gold = ex.next_steps[0]
            _instate = None; _injst = None
            if INJECT_GOLD:
                _gn = sorted(lemma_names(gold))
                if _gn:
                    ex, _st = _inject_gold(ex, _gn[0], dp, pidx, k)
                    S[r][f"주입:{_st}"] += 1
                    _injst = _st
                    if INJECT_VERIFY:
                        _instate = _in_prompt(ex, _gn[0])
                        S[r]["프롬프트에 실림" if _instate else "프롬프트에 없음"] += 1
            res = wrapper.get_recs(ex, NCAND, "", False, None)
            cands = list(res.next_tactic_list)
        except Exception as e:
            S[r]["오류"] += 1
            continue
        g = norm(gold)
        cn = [norm(c) for c in cands]
        gl = lemma_names(gold)
        cl = set().union(*[lemma_names(c) for c in cands]) if cands else set()

        S[r]["스텝"] += 1
        S[r]["top1 일치"] += (bool(cn) and cn[0] == g)
        S[r][f"top{NCAND} 일치"] += (g in cn)
        if gl:
            S[r]["gold 가 이름 사용"] += 1
            hit = bool(gl & cl)
            S[r]["└ 이름 맞힘"] += hit
            if hit and g in cn:
                S[r]["  └ 이름+형태 완벽"] += 1
            elif hit:
                S[r]["  └ ★조립 실패(이름만)"] += 1
            else:
                S[r]["  └ ★도달성 실패(이름없음)"] += 1
        else:
            S[r]["gold 가 일반 tactic"] += 1
            S[r]["└ 일반 top1 일치"] += (bool(cn) and cn[0] == g)
        fout.write(json.dumps(dict(idx=i, r=r, k=k, nsteps=nsteps, gold=gold,
                                   inprompt=_instate, inject=_injst,
                                   cands=cands[:NCAND], gold_names=sorted(gl),
                                   cand_names=sorted(cl)), ensure_ascii=False) + "\n")
    done += 1
    fout.flush()
    if done % 5 == 0:
        print(f"   … {done}/{len(mine)}", flush=True)

print("\n=== next-step 결과 ===", flush=True)
for r in (RATIOS if MODE != "named" else sorted(S)):
    c = S[r]
    n = max(c["스텝"], 1)
    print(f"\n■ prefix {int(r*100):2d}%   스텝 {c['스텝']}")
    print(f"   top1  gold 일치      {c['top1 일치']:4d} = {c['top1 일치']/n*100:5.1f}%")
    print(f"   top{NCAND}  gold 일치      {c[f'top{NCAND} 일치']:4d} = {c[f'top{NCAND} 일치']/n*100:5.1f}%")
    gu = max(c["gold 가 이름 사용"], 1)
    print(f"   gold 가 lemma 이름을 쓰는 스텝 {c['gold 가 이름 사용']} ({c['gold 가 이름 사용']/n*100:.0f}%)")
    print(f"     이름 맞힘            {c['└ 이름 맞힘']:4d} = {c['└ 이름 맞힘']/gu*100:5.1f}%")
    print(f"       이름+형태 완벽      {c['  └ 이름+형태 완벽']:4d} = {c['  └ 이름+형태 완벽']/gu*100:5.1f}%")
    print(f"       ★조립 실패         {c['  └ ★조립 실패(이름만)']:4d} = {c['  └ ★조립 실패(이름만)']/gu*100:5.1f}%")
    print(f"       ★도달성 실패       {c['  └ ★도달성 실패(이름없음)']:4d} = {c['  └ ★도달성 실패(이름없음)']/gu*100:5.1f}%")
json.dump({str(r): dict(S[r]) for r in S}, open(str(OUT) + ".summary.json", "w"),
          ensure_ascii=False, indent=1)
print(f"\n→ {OUT}", flush=True)
