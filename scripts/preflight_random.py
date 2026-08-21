#!/usr/bin/env python3
"""**랜덤·큰 인덱스** 사전점검 — 학습은 0부터 순서대로 돌지 않는다.

## 왜 필요한가

`SFTTrainer`(=HF `Trainer`)는 학습에 `RandomSampler` 를 쓴다. 즉 첫 스텝부터
**2,009,606 중 아무 인덱스**나 나온다. 지금까지의 점검은 대부분 앞쪽(0~수십만)에
치우쳐 있었고, 실제로 **큰 인덱스에서만 나는 문제**를 여러 번 겪었다:

  · cut 파일이 720,000 까지만 덮어서 그 뒤가 조용히 죽었다
  · 계획 청크가 뒤쪽부터 채워지므로 앞만 보면 빈 구간을 못 본다

그래서 여기서는 **전 구간에서 무작위로** 뽑아 학습이 실제로 타는 경로
(`resolved_example → collate → 토크나이즈 → 라벨 마스킹`)를 그대로 태운다.

## 보는 것 (하나라도 걸리면 학습을 시작하지 않는다)

  P1 ★ 예외        어떤 인덱스에서든 죽지 않는가
  P2 ★ cut 판정    범위 밖 인덱스가 없는가 (`_uncovered` 가 죽이는지)
  P3 ★ 라벨        비어 있지 않고 정답과 맞는가
  P4 ★ 정답 가시성  정답이 쓰는 이름이 **잘린 뒤에도** 프롬프트에서 읽히는가
  P5 ★ hopeless    학습에 새어 들어오는가
  P6   분포        구간별로 cut 적용률·hopeless 율이 고르게 나오는가
  P7 ★ 결정성      같은 인덱스를 두 번 만들면 같은가

사용: PYTHONPATH=src CUTS_PATH=... python3 scripts/preflight_random.py [건수]
"""
import collections
import copy
import logging
import os
import random
import re
import sys
import time

sys.path.insert(0, "src")
logging.disable(logging.CRITICAL)
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

N = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 400
SEED = int(os.environ.get("PREFLIGHT_SEED", "12345"))

import yaml  # noqa: E402
from data_management.splits import Split  # noqa: E402
from tactic_gen.tactic_data import (TacticDataConf, LmDataset,  # noqa: E402
                                    example_collator_from_conf, get_tokenizer,
                                    MASK_TEMPLATE)
from tactic_gen.data_collator_compat import DataCollatorForCompletionOnlyLM  # noqa: E402

CONF = os.environ.get("CONF", "all_log/ft_qwen3b_v9_conf.yaml")
cc = yaml.safe_load(open(CONF))
conf = TacticDataConf.from_yaml(copy.deepcopy(cc["tactic_data"]))
tok = get_tokenizer(cc["model_name"])
assert tok.truncation_side == "left", "학습과 다른 절단 방향으로는 점검할 수 없다"
ds = LmDataset.from_conf(conf, Split.TRAIN, None)
coll = example_collator_from_conf(conf.collator_conf)
dc = DataCollatorForCompletionOnlyLM(MASK_TEMPLATE, tokenizer=tok)
TOTAL = ds.shuffled_idx.split_length(Split.TRAIN)
HARD = int(os.environ.get("HARD_SEQ_LEN", "2048"))

random.seed(SEED)
# ★ 전 구간 균등 + **끝쪽을 일부러 더** 뽑는다. 큰 인덱스가 늦게 채워지므로.
idxs = [random.randrange(TOTAL) for _ in range(int(N * 0.7))]
idxs += [random.randrange(int(TOTAL * 0.9), TOTAL) for _ in range(N - len(idxs))]
random.shuffle(idxs)
print(f"■ 랜덤 인덱스 사전점검   TRAIN {TOTAL:,} 중 {len(idxs)}건 (seed={SEED})")
print(f"   인덱스 범위 {min(idxs):,} ~ {max(idxs):,} · 중앙 {sorted(idxs)[len(idxs)//2]:,}\n",
      flush=True)

NORM = re.compile(r"(?<![\w'])([TfCLG]\d+)(?![\w'])")
TACW = {"intros", "intro", "apply", "eapply", "exact", "rewrite", "destruct", "induction",
        "simpl", "unfold", "reflexivity", "assumption", "auto", "eauto", "trivial",
        "constructor", "split", "left", "right", "exists", "lia", "omega", "ring",
        "congruence", "discriminate", "inversion", "injection", "subst", "assert",
        "now", "try", "repeat", "solve", "forall", "fun", "match", "with", "end"}
st = collections.Counter()
bad = collections.defaultdict(list)
band = collections.defaultdict(collections.Counter)


def note(k, s_):
    st[k] += 1
    if len(bad[k]) < 3:
        bad[k].append(s_[:150])


t0 = time.time()
for c, i in enumerate(idxs):
    st["검사"] += 1
    b = f"{i * 10 // TOTAL}0%"
    band[b]["n"] += 1
    try:
        e = ds.resolved_example(i)
        s = coll.collate(tok, e)
    except RuntimeError as ex:
        if "cut 판정이 없는" in str(ex):
            note("P2 ★★ cut 판정 없는 인덱스", f"idx={i} {str(ex)[:90]}")
        else:
            note(f"P1 ★ RuntimeError", f"idx={i} {ex}")
        continue
    except Exception as ex:
        note(f"P1 ★ 예외 {type(ex).__name__}", f"idx={i} {ex}")
        continue
    if "[TACTIC]" not in s:
        note("P3 ★ [TACTIC] 없음", f"idx={i}")
        continue
    prompt, target = s.rsplit("[TACTIC]", 1)
    target = target.strip()
    if not target:
        note("P3 ★ 정답이 비었다", f"idx={i}")
        continue
    if "H_asrt" in target:
        st["cut 적용"] += 1
        band[b]["cut"] += 1
    if getattr(e, "cut_substep", None):
        st[f"하위스텝 {e.cut_substep[2]}"] += 1

    enc = tok(s, max_length=HARD, truncation=True, padding=False)
    try:
        lab = dc([{"input_ids": enc["input_ids"],
                   "attention_mask": enc["attention_mask"]}])["labels"][0]
        if int((lab != -100).sum()) == 0:
            note("P3 ★ 라벨 0개", f"idx={i} tgt={target[:60]}")
    except Exception as ex:
        note(f"P3 ★ 마스킹 예외 {type(ex).__name__}", f"idx={i} {ex}")

    # ★ **도입되는 이름은 참조가 아니다** — `destruct X as [f1 …]` 의 `f1` 은
    #   그 자리에서 새로 만드는 이름이라 프롬프트에 없는 것이 정상이다.
    #   구분 안 하면 오탐한다(실측: idx=1815688 의 f1).
    try:
        from tactic_gen.normalize_names import introduced_names as _intro
        _skip_names = _intro(target)
    except Exception:
        _skip_names = set()
    vis = tok.decode(enc["input_ids"], skip_special_tokens=True)
    vp = vis.rsplit("[TACTIC]", 1)[0] if "[TACTIC]" in vis else vis
    for nm in set(NORM.findall(target)) - _skip_names:
        if not re.search(r"(?<![\w'])" + nm + r"(?![\w'])", prompt):
            note("P4 ★★ 정답의 정규화 이름이 프롬프트에 없다", f"idx={i} {nm} ← {target[:60]}")
        elif not re.search(r"(?<![\w'])" + nm + r"(?![\w'])", vp):
            note("P4 ★★ 정답의 이름이 **잘려서** 안 보인다", f"idx={i} {nm}")
    for w in set(re.findall(r"(?<![\w'])([A-Za-z_][\w']{3,})(?![\w'])", target)):
        if w in TACW or NORM.fullmatch(w) or w in _skip_names:
            continue
        if re.search(r"(?<![\w'])" + re.escape(w) + r"(?![\w'])", prompt) and \
           not re.search(r"(?<![\w'])" + re.escape(w) + r"(?![\w'])", vp):
            note("P4 ★★ 정답이 쓰는 이름이 **잘려서** 안 보인다", f"idx={i} {w}")

    if os.environ.get("CUTS_PATH", ""):
        from tactic_gen import cut_lookup
        k = f"{e.file_name}:{e.proof_idx}:{e.step_idx}"
        if cut_lookup.is_hopeless(k):
            note("P5 ★★ hopeless 가 학습에 들어왔다", f"idx={i} {k}")

    if c < 30:
        try:
            if coll.collate(tok, ds.resolved_example(i)) != s:
                note("P7 ★ 두 번 만들면 다르다", f"idx={i}")
        except Exception:
            pass
    if (c + 1) % 100 == 0:
        print(f"   {c+1}/{len(idxs)}  ({time.time()-t0:.0f}s)", flush=True)

n = max(st["검사"], 1)
print(f"\n■ 결과 ({st['검사']}건 · {time.time()-t0:.0f}s)\n")
for k in sorted(st):
    if k == "검사":
        continue
    print(f"   {k:48s} {st[k]:6d}  {st[k]/n*100:6.2f}%")
    for x in bad[k]:
        print(f"        {x}")

print(f"\n■ P6 구간별 분포 (cut 적용률)")
for b in sorted(band, key=lambda x: int(x[:-1])):
    v = band[b]
    print(f"   {b:>5s}  {v['n']:5d}건  cut {v['cut']:4d}  {v['cut']/max(v['n'],1)*100:5.1f}%")

fatal = sorted(k for k in st if "★" in k)
print()
if fatal:
    print("★ 치명 항목:")
    for f in fatal:
        print(f"   · {f}  ({st[f]}건)")
    sys.exit(1)
print("✓ 랜덤·큰 인덱스에서 학습 경로 정상")
