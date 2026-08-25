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
OUT.parent.mkdir(parents=True, exist_ok=True)

CONF = yaml.safe_load(open("all_log/ft_qwen3b_v9_conf.yaml"))
td = TacticDataConf.from_yaml(CONF["tactic_data"])
# ★★ CoqStoq TEST 정리는 **평가용 데이터셋**에 있다 — 학습용 /tmp/coq-dataset 이 아니다.
#   데이터포인트 이름 규칙부터 다르다: 평가용은 `compcert-…`, 학습용은 `AbsInt-CompCert-…`.
#   (run_thm.py get_data_loc/get_sentence_db_loc 가 쓰는 것과 **같은 경로**를 써야
#    프롬프트가 평가 파이프라인과 일치한다.)
DATA_LOC = Path("raw-data/coqstoq-test")
SDB_LOC = Path("raw-data/coqstoq-test/coqstoq-test-sentences.db")
sdb = SentenceDB.load(SDB_LOC)
formatter = formatter_from_conf(td.formatter_conf)
# ★ 래퍼가 체크포인트의 training_conf 를 이 프로세스에 전파한다(HARD_SEQ_LEN·OUT_TOKENS·
#   normalize_inference). 여기서 env 로 못박지 않는다 — 학습과 어긋나면 _L# 이 밀린다.
wrapper = DecoderLocalWrapper.from_checkpoint(Path(CKPT), normalize_inference=True)
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
            gold = ex.next_steps[0]
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
