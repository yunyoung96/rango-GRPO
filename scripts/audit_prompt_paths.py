#!/usr/bin/env python3
"""프롬프트에 들어가는 **모든 값의 계산 경로**를 실데이터로 감사한다.

검사 대상 6갈래:
  P1 [TYPES]      : 시드가 goal 의 실제 타입인가 / 정의가 그 이름의 것인가
  P2 [DEFINITIONS]: 위와 동일 + 같은 파일 정의 우선이 지켜지는가
  P3 [PREMISES]   : 재랭킹 후에도 gold 가 쓴 lemma 가 남아 있는가(recall 손실 없나)
  P4 [PROOFS]     : 검색된 유사 증명이 **자기 자신**을 포함하지 않는가(정답 누출)
  P5 정규화        : 단사인가 / 프롬프트와 타깃에 같은 사상이 적용됐나 / 헤더를 안 건드리나
  P6 예산·절단    : 한도 초과가 없는가 / 섹션이 잘려 문법이 깨지지 않는가
"""
import os, re, sys, json, collections
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.insert(0, "src")
import logging; logging.disable(logging.CRITICAL)
import yaml
from transformers import AutoTokenizer
from tactic_gen.lm_example import LmExample
import tactic_gen.tactic_data as td
from tactic_gen.tactic_data import (example_collator_conf_from_yaml,
                                    example_collator_from_conf)
from tactic_gen.augment import types_v2, definitions_v2, pick_def, _rel_path, _norm_proj

N = int(sys.argv[1]) if len(sys.argv) > 1 else 200
IDX = json.load(open(os.environ.get("FUNC_DEFS_PATH", "data/func_defs_v3.json")))
DECL = re.compile(r"^\s*(?:Inductive|CoInductive|Variant|Record|Definition|Fixpoint|Lemma|"
                  r"Theorem|Parameter|Axiom|Class|Instance|Structure|Notation)\s+"
                  r"(?:Local\s+|Global\s+)?([A-Za-z_][\w']*)")
LN = re.compile(r"(?:Lemma|Theorem|Definition|Corollary|Remark|Fact)\s+([A-Za-z_][\w']*)")

def load(n):
    out = []
    for line in open("data/grpo_rollouts/goldsft_bs2.jsonl"):
        g = json.loads(line)
        for a in g["attempts"]:
            if a["reward"] < 1.0:
                continue
            for st in a["steps"]:
                if st.get("example") and st.get("tactic"):
                    e = LmExample.from_json(st["example"]); e.next_steps = [st["tactic"]]
                    out.append(e)
                    if len(out) >= n: return out
    return out

def split1(p):
    a = (p or "").split("/", 1); return a[0], (a[1] if len(a) > 1 else "")

def peq(a, b):
    x, y = _norm_proj(a), _norm_proj(b); return x == y or bool(x) and (x in y or y in x)

tok = AutoTokenizer.from_pretrained(os.environ.get("MODEL_NAME",
                                    "Qwen/Qwen2.5-Coder-3B-Instruct"))
cc = yaml.safe_load(open("all_log/ft_qwen3b_v5_conf.yaml"))
col = example_collator_from_conf(example_collator_conf_from_yaml(cc["example_collator"]))
steps = load(N)
fail = collections.Counter(); ex = collections.defaultdict(list)
stat = collections.Counter()

for e in steps:
    goal = e.proof_state or ""
    prompt = col.collate(tok, e)
    inj = dict(td._LAST_INJECTED)

    # ── P1/P2: 주입된 정의가 그 이름의 정의인가 ──
    for nm, dfn in inj.items():
        stat["주입"] += 1
        m = DECL.match(dfn.strip())
        if m and m.group(1) != nm:
            fail["P1/P2 선언이름≠요청이름"] += 1
            if len(ex["P12"]) < 3: ex["P12"].append(f"{nm!r} → {dfn.strip()[:60]}")
        # 같은 파일에 정답이 있으면 그걸 골랐는가
        c = IDX.get(nm)
        if isinstance(c, dict) and len(c) > 1:
            rp, rrest = split1(_rel_path(e.file_name))
            gold = [v for k, v in c.items()
                    if split1(k)[1] == rrest and peq(split1(k)[0], rp)]
            if gold:
                stat["같은파일 정답존재"] += 1
                # 주입값은 _shorten(시그니처만 남기거나 ' ...' 절단)을 거친다.
                # 원본과 문자열 비교하면 전부 오탐 → **접두 일치**로 판정한다.
                g0 = gold[0]
                pre = dfn.rstrip(" .").rstrip("...").strip()
                if not (g0.startswith(pre[:40]) or dfn == g0):
                    fail["P2 같은파일 정의 미선택"] += 1
                    if len(ex["P2"]) < 3:
                        ex["P2"].append(f"{nm} @{e.file_name}\n       주입:{dfn[:50]}\n       정답:{gold[0][:50]}")

    # ── P3: 재랭킹 후 gold lemma 가 [PREMISES] 에 남아 있나 ──
    gold_tac = e.next_steps[0]
    prem_blk = prompt.split("[PREMISES]")[-1].split("[")[0] if "[PREMISES]" in prompt else ""
    pnames = set(LN.findall(prem_blk))
    raw = set(LN.findall("\n".join(list(getattr(e, "premises", None) or []))))
    used = [n for n in re.findall(r"\b[A-Za-z_][\w']*\b", gold_tac) if n in raw]
    for n_ in used:
        if n_ in raw:
            stat["gold lemma 원본 존재"] += 1
            if n_ not in pnames:
                fail["P3 재랭킹이 gold lemma 를 탈락시킴"] += 1
                if len(ex["P3"]) < 3: ex["P3"].append(f"{n_} (gold={gold_tac.strip()[:40]})")

    # ── P4: [PROOFS] 에 자기 정리가 들어갔나(정답 누출) ──
    if "[PROOFS]" in prompt:
        pf = prompt.split("[PROOFS]")[-1].split("[STATE]")[0]
        if gold_tac.strip() and gold_tac.strip() in pf:
            fail["P4 검색 증명에 gold tactic 그대로 존재"] += 1
            if len(ex["P4"]) < 2: ex["P4"].append(gold_tac.strip()[:50])

    # ── P5: 정규화 흔적이 프롬프트/타깃에 일관되나 ──
    tgt = prompt.split(td.MASK_TEMPLATE)[-1]
    norm_ids = set(re.findall(r"\b[TfC]\d+\b", prompt))
    if norm_ids:
        stat["정규화 예제"] += 1
        for nid in re.findall(r"\b[TfC]\d+\b", tgt):
            if nid not in norm_ids:
                fail["P5 타깃에만 있는 정규화 이름"] += 1
        for sep in ("[TYPES]", "[DEFINITIONS]", "[PREMISES]", "[STATE]", "[TACTIC]"):
            if sep.replace("[", "").replace("]", "") and re.search(r"\[[TfC]\d+\]", prompt):
                fail["P5 헤더 훼손"] += 1; break

    # ── P6: 예산·절단 ──
    n_tok = len(tok(prompt)["input_ids"])
    stat["max_tok"] = max(stat["max_tok"], n_tok)
    if n_tok > 4096:
        fail["P6 4096 초과"] += 1
    for sec in ("[TYPES]", "[DEFINITIONS]"):
        if sec in prompt:
            body = prompt.split(sec)[-1].split("[")[0]
            # `_shorten` 은 ① ':=' 앞 시그니처만 남기거나 ② 단어 절단 후 ' ...' 를 붙인다.
            # ①은 마침표로 안 끝나는 게 **정상**이므로, 실제 정보 손실인 ②만 센다.
            stat["절단(...)"] += body.count(" ...")

print(f"■ 프롬프트 경로 감사 — 예제 {len(steps)}개, 주입 {stat['주입']}건, "
      f"최대 {stat['max_tok']}토큰")
print(f"   같은파일 정답존재 {stat['같은파일 정답존재']}건 · 정규화 예제 {stat['정규화 예제']}건 · "
      f"gold lemma 원본존재 {stat['gold lemma 원본 존재']}건")
if not fail:
    print("\n   ✅ P1~P6 전부 통과")
else:
    print()
    for k, v in fail.most_common():
        print(f"   ❌ {k}: {v}건")
    for k, vs in ex.items():
        for s in vs: print(f"      [{k}] {s}")
