#!/usr/bin/env python3
"""**기존 rango 프롬프트**와 **v9 프롬프트**를 같은 스텝에서 나란히 뽑아 .md 로 남긴다.

## 왜

우리가 바꾼 것이 워낙 많다(구조 재랭킹 · [TYPES]/[DEFINITIONS] 주입 · 이름 정규화 ·
cut · 예산 변경). 자동 검사는 "내가 생각한 위험" 만 잡는다 — **생각 못 한 위험**은
사람이 눈으로 봐야 나온다. 그래서 원문 그대로 나란히 남긴다.

## 같은 스텝인가

둘 다 같은 `shuffled_index`(ft6.7b-shuffled-index.json)를 쓰므로 인덱스 i 는 같은
StepID 를 가리킨다. 토크나이저도 같은 것(Qwen)을 쓴다 — 예산 차이만 남기고 나머지
변수를 없애야 비교가 의미 있다.

## 무엇이 다른가

    설정            rango 원본        v9
    premise_tokens  512              896
    proof_tokens    1024             256
    hard_seq_len    4096             2048
    num_premises    50               100
    num_proofs      20               12
    검색            tfidf 만          tfidf + 구조 재랭킹(structural)
    [TYPES]/[DEFS]  없음              주입
    이름 정규화      없음              전부(NORMALIZE_RATE=1.0)
    cut             없음              gold 가 프롬프트에 없으면 assert 로 치환

사용: PYTHONPATH=src python3 scripts/gen_prompt_comparison.py [개수] [출력디렉토리]
"""
import collections
import copy
import logging
import os
import re
import sys

sys.path.insert(0, "src")
logging.disable(logging.CRITICAL)
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")

N = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 40
OUT = sys.argv[2] if len(sys.argv) > 2 else "prompt_examples_comparison/v9_vs_rango"
# ★ CUT_ONLY=1 이면 **cut 이 걸린 인덱스만** 고른다. 무작위로 뽑으면 cut 예제가
#   거의 안 나와서(현재 커버리지가 낮다) 정작 보고 싶은 것을 못 본다.
CUT_ONLY = os.environ.get("CUT_ONLY", "0") == "1"
CUTS = os.environ.get("CUTS_PATH", "")
os.makedirs(OUT, exist_ok=True)

import yaml  # noqa: E402
from data_management.splits import Split  # noqa: E402
from tactic_gen.tactic_data import (TacticDataConf, LmDataset,  # noqa: E402
                                    example_collator_from_conf, get_tokenizer)

# ── 두 설정 ──────────────────────────────────────────────────────────────
V9_ENV = dict(CUTS_PATH=CUTS, AUGMENT_V2="1", RERANK_PREMISES="1", INJECT_TYPES="1", INJECT_DEFS="1",
              TYPES_TOKENS="300", DEFS_TOKENS="300", AUG_OUT_TOKENS="128",
              FUNC_DEFS_PATH="data/func_defs_v3.json", NORMALIZE_NAMES="1",
              NORMALIZE_RATE="1.0", NORMALIZE_PREMISES="1", NORMALIZE_THEOREM="1",
              NORMALIZE_SKIP_STDLIB="1", INJECT_SKIP_STDLIB="1",
              RETRIEVAL_MODE="structural", RETRIEVAL_STAGE1="5000",
              PREMISE_PACK="hybrid", PREMISE_PACK_TOPK="4", STRIP_TARGET_NL="1",
              HARD_SEQ_LEN="2048")
# ★ rango 원본 = 증강 3종·정규화·cut 을 **전부 끈다**. 끄는 것을 빠뜨리면 비교가 거짓이 된다.
RANGO_ENV = dict(AUGMENT_V2="0", RERANK_PREMISES="0", INJECT_TYPES="0", INJECT_DEFS="0",
                 NORMALIZE_NAMES="0", NORMALIZE_RATE="0.0", NORMALIZE_PREMISES="0",
                 NORMALIZE_THEOREM="0", RETRIEVAL_MODE="tfidf", PREMISE_PACK="rank",
                 CUTS_PATH="", HARD_SEQ_LEN="4096")


def setenv(d, base):
    for k in set(V9_ENV) | set(RANGO_ENV) | {"CUTS_PATH"}:
        os.environ.pop(k, None)
    for k, v in base.items():
        os.environ[k] = v
    for k, v in d.items():
        os.environ[k] = v


BASE = {k: v for k, v in os.environ.items() if k.startswith(("NORMALIZE", "INJECT"))}

cc9 = yaml.safe_load(open("all_log/ft_qwen3b_v9_conf.yaml"))
conf9 = TacticDataConf.from_yaml(copy.deepcopy(cc9["tactic_data"]))
tok = get_tokenizer(cc9["model_name"])

ccr = yaml.safe_load(open("all_log/ft_rango_control_conf.yaml"))
tdr = copy.deepcopy(ccr["tactic_data"])
tdr["model_name"] = cc9["model_name"]              # 토크나이저는 같게 — 변수 하나만 남긴다
tdr["cache_loc"] = "/tmp/prompt-cmp-rango-cache"
confr = TacticDataConf.from_yaml(tdr)

print("데이터셋 로딩…", flush=True)
setenv(V9_ENV, {})
ds9 = LmDataset.from_conf(conf9, Split.TRAIN, None)
coll9 = example_collator_from_conf(conf9.collator_conf)
setenv(RANGO_ENV, {})
dsr = LmDataset.from_conf(confr, Split.TRAIN, None)
collr = example_collator_from_conf(confr.collator_conf)
TOTAL = ds9.shuffled_idx.split_length(Split.TRAIN)
print(f"TRAIN {TOTAL:,}", flush=True)

SECS = ["PREMISES", "PROOFS", "SCRIPT", "STATE", "TYPES", "DEFINITIONS"]
HDR = re.compile(r"\[(" + "|".join(SECS) + r")\]")
NORM = re.compile(r"(?<![\w'])([TfCLG]\d+)(?![\w'])")
ALIAS = re.compile(r"^\s*Definition\s+[A-Za-z_][\w']*\s*:=\s*"
                   r"[A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)+\s*\.?\s*$", re.M)


def sections(prompt):
    pos = [(m.start(), m.group(1)) for m in HDR.finditer(prompt)]
    out = {}
    for k, (st, name) in enumerate(pos):
        end = pos[k + 1][0] if k + 1 < len(pos) else len(prompt)
        body = prompt[st:end].split("]", 1)[1].strip()
        out[name] = body
    return out


def ntok(t):
    return len(tok(t, add_special_tokens=False)["input_ids"]) if t else 0


def build(ds, coll, env, i, hard):
    setenv(env, {})
    e = ds.resolved_example(i)
    s = coll.collate(tok, e)
    prompt, target = (s.rsplit("[TACTIC]", 1) + [""])[:2]
    enc = tok(s, add_special_tokens=False)
    full = len(enc["input_ids"])
    trunc = tok.decode(tok(s, max_length=hard, truncation=True)["input_ids"],
                       skip_special_tokens=True)
    return dict(s=s, prompt=prompt, target=target.strip(), full=full,
                trunc=trunc, sec=sections(prompt), e=e)


CUTKEYS = set()
if CUT_ONLY:
    import json as _json
    with open(CUTS) as _f:
        for _ln in _f:
            try:
                _d = _json.loads(_ln)
            except Exception:
                continue
            if _d.get("kind") == "step" and _d.get("cut"):
                _sid = _d.get("sid", "")
                _pp = _sid.rsplit(":", 2)
                if len(_pp) == 3:
                    CUTKEYS.add((os.path.basename(_pp[0]), int(_pp[1]), int(_pp[2])))
    print(f"cut 이 걸린 스텝 {len(CUTKEYS):,}개", flush=True)

ISSUES = collections.Counter()
rows = []
# ★ 인덱스 구간 지정 — `IDX_LO`/`IDX_HI`.
#   cut 은 청크 단위로 만들어지므로 **뒤쪽 인덱스가 마지막에 채워진다.**
#   앞쪽만 훑으면 "cut 이 없는 구간" 을 영영 못 본다(실제로 그 사고를 겪었다).
LO = int(os.environ.get("IDX_LO", "0"))
HI = int(os.environ.get("IDX_HI", "0")) or TOTAL
SPAN = max(1, HI - LO)
step = max(1, SPAN // (N + 1))
made = 0
i = 0
scan = 0
while made < N and scan < TOTAL:
    if CUT_ONLY:
        # ★ cut 파일의 키는 `repos/a-b/src/f.v:p:s` 인데 ShuffledIndex 의 `sid.file` 은
        #   `a-b-src-f.v` 다 — 경로 구분자가 대시로 눌려 있어 **문자열로는 못 맞춘다**.
        #   (basename, proof_idx, step_idx) 로 후보를 좁히고, 실제로 cut 이 적용됐는지는
        #   만들어진 정답에 `H_asrt` 가 있는지로 확정한다.
        found = None
        while scan < TOTAL:
            sid = ds9.shuffled_idx.get_idx(Split.TRAIN, scan)
            scan += 1
            if (os.path.basename(sid.file), sid.proof_idx, sid.step_idx) in CUTKEYS:
                found = scan - 1
                break
        if found is None:
            break
        idx = found
    else:
        idx = LO + (made + 1) * step
        scan += step
    i += 1
    try:
        v9 = build(ds9, coll9, V9_ENV, idx, 2048)
        rg = build(dsr, collr, RANGO_ENV, idx, 4096)
    except Exception as ex:
        ISSUES[f"생성 예외 {type(ex).__name__}"] += 1
        made += 1
        continue

    # ── 자동 점검 ────────────────────────────────────────────────────────
    bad = []
    for nm in NORM.findall(v9["target"]):
        if not re.search(r"(?<![\w'])" + nm + r"(?![\w'])", v9["prompt"]):
            bad.append(f"★★ 정답의 정규화 이름 `{nm}` 이 프롬프트에 없다")
    for sec in SECS:
        if v9["prompt"].count(f"[{sec}]") > 1:
            bad.append(f"★ [{sec}] 헤더 중복")
    for sec in ("TYPES", "DEFINITIONS"):
        if f"[{sec}]" in v9["prompt"] and not v9["sec"].get(sec, "").strip():
            bad.append(f"★ [{sec}] 가 비어 있다")
    for m in ALIAS.finditer(v9["sec"].get("DEFINITIONS", "")):
        bad.append(f"★ 모듈 별칭 정의가 남았다: {m.group(0).strip()[:50]}")
    if re.search(r'"[^"\n]*[TfCLG]\d+[^"\n]*"', v9["prompt"]):
        bad.append("★ 문자열 안에 정규화 이름이 보인다")
    if re.search(r"(?<![\w'.])[A-Za-z_][\w']*\.(?:tt|nat|list)\.", v9["prompt"]):
        bad.append("★ 모듈 접두사가 stdlib 이름으로 바뀐 흔적")
    if v9["full"] > 2048 and "[PREMISES]" not in v9["trunc"]:
        bad.append(f"★★ 2048 절단으로 [PREMISES] 헤더 소실 (전체 {v9['full']}토큰)")
    if not v9["target"]:
        bad.append("★★ 정답이 비어 있다")
    if "\x00" in v9["s"]:
        bad.append("★★ NUL 문자")
    is_cut = "H_asrt" in v9["target"]
    if CUT_ONLY and not is_cut:
        continue                       # 후보였지만 실제로는 cut 이 안 걸렸다
    for b in bad:
        ISSUES[b.split(":")[0]] += 1

    n9 = {k: (len([x for x in v.split("\n") if x.strip()]), ntok(v))
          for k, v in v9["sec"].items()}
    nr = {k: (len([x for x in v.split("\n") if x.strip()]), ntok(v))
          for k, v in rg["sec"].items()}

    made += 1
    fn = f"{OUT}/ex_{made:03d}.md"
    with open(fn, "w") as f:
        f.write(f"# 예제 {made:03d} — TRAIN 인덱스 {idx:,}\n\n")
        f.write(f"`{v9['e'].file_name}` · proof {v9['e'].proof_idx} · "
                f"step {v9['e'].step_idx}\n\n")
        f.write("## 한눈에\n\n")
        f.write("| | rango 원본 | v9 |\n|---|---|---|\n")
        f.write(f"| 전체 토큰 | {rg['full']} (한계 4096) | {v9['full']} (한계 2048) |\n")
        for sec in SECS:
            a = nr.get(sec)
            b = n9.get(sec)
            f.write(f"| [{sec}] | {'—' if not a else f'{a[0]}개 · {a[1]}tok'} "
                    f"| {'—' if not b else f'{b[0]}개 · {b[1]}tok'} |\n")
        f.write(f"| cut(assert) 적용 | — | {'✅' if is_cut else '—'} |\n")
        f.write(f"| 이름 정규화 | — | {'✅ ' + str(len(set(NORM.findall(v9['prompt'])))) + '개' if NORM.search(v9['prompt']) else '—'} |\n\n")
        f.write("## 자동 점검\n\n")
        f.write(("\n".join(f"- {b}" for b in bad) if bad else "- 이상 없음") + "\n\n")
        f.write("## 정답 tactic\n\n")
        f.write(f"**rango**\n```coq\n{rg['target']}\n```\n\n")
        f.write(f"**v9**\n```coq\n{v9['target']}\n```\n\n")
        f.write("## rango 원본 프롬프트\n\n```\n" + rg["prompt"].strip() + "\n```\n\n")
        f.write("## v9 프롬프트\n\n```\n" + v9["prompt"].strip() + "\n```\n")
    rows.append((made, idx, rg["full"], v9["full"], is_cut, len(bad),
                 bool(n9.get("TYPES")), bool(n9.get("DEFINITIONS"))))
    if made % 5 == 0:
        print(f"  {made}/{N}", flush=True)

with open(f"{OUT}/README.md", "w") as f:
    f.write("# v9 프롬프트 vs 기존 rango 프롬프트\n\n")
    f.write(f"같은 스텝({len(rows)}개)에서 두 파이프라인이 만드는 프롬프트를 "
            "그대로 나란히 뽑았다.\n\n")
    f.write("## 무엇이 다른가\n\n")
    f.write("| 설정 | rango 원본 | v9 |\n|---|---|---|\n")
    for a, b, c in [("premise_tokens", "512", "896"), ("proof_tokens", "1024", "256"),
                    ("hard_seq_len", "4096", "2048"), ("num_premises", "50", "100"),
                    ("num_proofs", "20", "12"),
                    ("검색", "tfidf 만", "tfidf + 구조 재랭킹"),
                    ("[TYPES]/[DEFINITIONS]", "없음", "주입"),
                    ("이름 정규화", "없음", "전부(rate 1.0)"),
                    ("cut", "없음", "gold 가 없으면 assert 치환")]:
        f.write(f"| {a} | {b} | {c} |\n")
    f.write("\n토크나이저는 **둘 다 Qwen** 으로 맞췄다 — 예산 차이만 남기고 나머지 "
            "변수를 없애야 비교가 의미 있다.\n\n")
    f.write("## 자동 점검 요약\n\n")
    if ISSUES:
        for k, v in ISSUES.most_common():
            f.write(f"- **{v}건** {k}\n")
    else:
        f.write("- 이상 없음\n")
    f.write("\n## 예제 목록\n\n")
    f.write("| # | 인덱스 | rango tok | v9 tok | cut | TYPES | DEFS | 점검 |\n")
    f.write("|---|---|---|---|---|---|---|---|\n")
    for m, idx, rf, vf, cut, nb, ht, hd in rows:
        f.write(f"| [{m:03d}](ex_{m:03d}.md) | {idx:,} | {rf} | {vf} | "
                f"{'✅' if cut else ''} | {'✅' if ht else ''} | {'✅' if hd else ''} | "
                f"{'⚠️ ' + str(nb) if nb else ''} |\n")

print(f"\n■ 자동 점검 요약")
for k, v in ISSUES.most_common():
    print(f"   [{v:4d}] {k}")
if not ISSUES:
    print("   이상 없음")
print(f"\n→ {OUT}/README.md")
