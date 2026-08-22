#!/usr/bin/env python3
"""전체 학습 경로 감사 — 어떤 step 인덱스를 돌려도 문제가 없는가.

학습이 실제로 쓰는 `LmDataset.resolved_example → collate → 라벨 마스킹` 경로를
**인덱스 전 구간과 경계**에서 그대로 태워 보고, 학습을 망칠 수 있는 것만 본다.

  A. 예외·크래시    어떤 인덱스에서든 죽지 않는가
  B. 라벨           비어 있지 않은가 · 정답과 맞는가 (정규화 차이는 구조로 판정)
  C. 잘림           hard_seq_len 초과율 · 잘려서 [TACTIC] 이 사라지지 않는가
  D. 정규화         정답의 정규화 이름(T#/f#/C#/L#/G#)이 프롬프트에서 읽히는가
  E. 위생           섹션 헤더 중복 · NUL · 제어문자
  F. 결정성         같은 인덱스를 두 번 만들면 같은가
  G. cut            cut 적중 · hopeless 가 학습에 새어들어오는가

사용: PYTHONPATH=src python3 scripts/audit_train_path.py [구간당 건수] [--spots a,b,c]
"""
import collections
import copy
import logging
import os
import re
import sys

sys.path.insert(0, "src")
logging.disable(logging.CRITICAL)

N_PER = 60
for a in sys.argv[1:]:
    if a.isdigit():
        N_PER = int(a)

# ★ 설정의 출처는 `all_log/v9_env.sh` **하나**다. 여기에 값을 다시 적으면 반드시
#   어긋나고, 어긋나도 오류가 안 난다 — 조용히 다른 실험을 재게 된다(실제로 겪었다:
#   옛 CUTS_PATH 로 U1 을 재고, structural 로 "학습과 같은 설정" 감사를 돌렸다).
sys.path.insert(0, "scripts")
from _env_from_v9 import apply_v9_env  # noqa: E402
apply_v9_env(verbose=True)
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
# ★ 학습과 **같은 설정**으로 태운다. v9_env.sh 를 source 한 셸에서 부르는 것이 정석이고,
#   빠진 값은 여기서 기본값으로 채운다(감사 스크립트가 조용히 다른 설정을 쓰면 의미가 없다).
for k, v in dict(AUGMENT_V2="1", RERANK_PREMISES="1", INJECT_TYPES="1", INJECT_DEFS="1",
                 TYPES_TOKENS="300", DEFS_TOKENS="300", HARD_SEQ_LEN="2048",
                 AUG_OUT_TOKENS="128", FUNC_DEFS_PATH="data/func_defs_v3.json",
                 NORMALIZE_NAMES="1", NORMALIZE_RATE="1.0", NORMALIZE_PREMISES="1",
                 NORMALIZE_THEOREM="1", NORMALIZE_SKIP_STDLIB="1", INJECT_SKIP_STDLIB="1",
                 RETRIEVAL_MODE="eqx", RETRIEVAL_STAGE1="5000",
                 PREMISE_PACK="hybrid", PREMISE_PACK_TOPK="4",
                 STRIP_TARGET_NL="1", TFIDF_DOC_CACHE="200000",
                 DP_CACHE_SIZE="2048").items():
    os.environ.setdefault(k, v)
# 감사 중에는 cut 파일이 생성 중일 수 있다 — 커버리지 미달로 죽지 않게 한다.
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")

import yaml  # noqa: E402
from data_management.splits import Split  # noqa: E402
from tactic_gen.tactic_data import (TacticDataConf, LmDataset,  # noqa: E402
                                    example_collator_from_conf, MASK_TEMPLATE,
                                    get_tokenizer)
from tactic_gen.data_collator_compat import DataCollatorForCompletionOnlyLM  # noqa: E402

CONF = os.environ.get("CONF", "all_log/ft_qwen3b_v9_conf.yaml")
cc = yaml.safe_load(open(CONF))
conf = TacticDataConf.from_yaml(copy.deepcopy(cc["tactic_data"]))
# ★★ 반드시 `get_tokenizer` 를 쓴다 — 학습이 쓰는 것과 같아야 한다.
#   AutoTokenizer 기본값은 truncation_side="right" 라서 **끝에 있는 [TACTIC] 이 잘린다.**
#   그걸로 재면 "잘림으로 [TACTIC] 소실 8.3%" 같은 **가짜 경보**가 나온다(실제로 겪었다).
#   학습은 truncation_side="left" 로 앞쪽([PREMISES])부터 자르므로 정답은 항상 남는다.
tok = get_tokenizer(cc["model_name"])
assert tok.truncation_side == "left", "학습과 다른 절단 방향으로는 감사할 수 없다"
ds = LmDataset.from_conf(conf, Split.TRAIN, None)
coll = example_collator_from_conf(conf.collator_conf)
dc = DataCollatorForCompletionOnlyLM(MASK_TEMPLATE, tokenizer=tok)

TOTAL = ds.shuffled_idx.split_length(Split.TRAIN)
HARD = int(os.environ["HARD_SEQ_LEN"])
# ★ 전 구간 + **경계**(0, 1, 마지막). 경계는 off-by-one 이 숨는 자리다.
SPOTS = [0, 1, TOTAL // 8, TOTAL // 4, TOTAL // 2,
         TOTAL * 5 // 8, TOTAL * 3 // 4, TOTAL * 7 // 8,
         TOTAL - N_PER - 2]
print(f"■ 학습 경로 감사   TRAIN {TOTAL:,} · 구간 {len(SPOTS)}곳 × {N_PER}건 "
      f"= {len(SPOTS)*N_PER}건\n", flush=True)

NORM = re.compile(r"\b[TfCLG]\d+\b")
st = collections.Counter()
bad = collections.defaultdict(list)


def note(k, s):
    st[k] += 1
    if len(bad[k]) < 3:
        bad[k].append(s[:150])


def skel(x):
    """식별자를 지운 뼈대 — 정규화로 이름만 바뀐 것과 구조가 깨진 것을 가른다."""
    return re.sub(r"[A-Za-z_][\w']*", "□", x).replace(" ", "")


for sp in SPOTS:
    for i in range(sp, min(sp + N_PER, TOTAL)):
        st["검사"] += 1
        try:
            e = ds.resolved_example(i)
            s = coll.collate(tok, e)
        except Exception as ex:
            note(f"A ★ 예외 {type(ex).__name__}", f"idx={i} {ex}")
            continue
        if "[TACTIC]" not in s:
            note("A ★ [TACTIC] 없음", f"idx={i}")
            continue
        prompt, target = s.rsplit("[TACTIC]", 1)

        # ── B. 라벨 ──
        enc = tok(s, max_length=HARD, truncation=True, padding=False)
        try:
            lab = dc([{"input_ids": enc["input_ids"],
                       "attention_mask": enc["attention_mask"]}])["labels"][0]
            nlab = int((lab != -100).sum())
            if nlab == 0:
                note("B ★ 라벨 0개", f"idx={i} tgt={target.strip()[:60]}")
            else:
                txt = tok.decode([t for t in lab.tolist() if t != -100],
                                 skip_special_tokens=True).strip()
                tg = target.strip().lstrip("\n")
                if txt.replace(" ", "")[:50] != tg.replace(" ", "")[:50]:
                    # 정규화로 이름만 다른 것은 정상 — 뼈대가 같은지로 가른다
                    if skel(txt)[:60] == skel(tg)[:60]:
                        st["B 정규화 차이(정상)"] += 1
                    else:
                        note("B ★ 라벨 구조가 정답과 다르다",
                             f"idx={i} lab={txt[:45]} tgt={tg[:45]}")
        except Exception as ex:
            note(f"B ★ 마스킹 예외 {type(ex).__name__}", f"idx={i} {ex}")

        # ── C. 잘림 ──
        full = len(tok(s, add_special_tokens=False)["input_ids"])
        if full > HARD:
            st["C 2048 초과"] += 1
            if "[TACTIC]" not in tok.decode(enc["input_ids"], skip_special_tokens=True):
                note("C ★★ 잘림으로 [TACTIC] 소실", f"idx={i} len={full}")

        # ── D. 정규화 이름이 프롬프트에서 읽히는가 ──
        #   ★★ **잘린 뒤의 프롬프트**로 본다. 섹션 예산 합(3,416)이 hard_seq_len(2,048)을
        #     넘으므로 앞쪽(=하위 premise)이 실제로 잘려 나간다. 자르기 **전**으로 재면
        #     "정답이 읽힌다" 는 결론이 낙관적으로 나온다 — 모델이 보는 것은 잘린 쪽이다.
        try:
            from tactic_gen.normalize_names import introduced_names as _intro
            _skip_names = _intro(target)
        except Exception:
            _skip_names = set()
        vis = tok.decode(enc["input_ids"], skip_special_tokens=True)
        vis_prompt = vis.rsplit("[TACTIC]", 1)[0] if "[TACTIC]" in vis else vis
        for m in NORM.finditer(target):
            nm = m.group(0)
            if nm in _skip_names:
                continue
            if not re.search(r"(?<![\w'])" + nm + r"(?![\w'])", prompt):
                note("D ★ 정답의 정규화이름이 프롬프트에 없음",
                     f"idx={i} {nm} ← {target.strip()[:70]}")
            elif not re.search(r"(?<![\w'])" + nm + r"(?![\w'])", vis_prompt):
                note("D ★★ 정답의 이름이 **잘려서** 안 보임 (환각 학습)",
                     f"idx={i} {nm} ← {target.strip()[:70]}")
        # gold lemma 이름 자체(정규화 안 된 경우 포함)가 잘려 사라졌나
        for w in set(re.findall(r"(?<![\w'])([A-Za-z_][\w']{3,})(?![\w'])", target)):
            if w in ("intros", "apply", "rewrite", "exact", "destruct", "induction",
                     "reflexivity", "assumption", "simpl", "unfold", "auto") \
                    or w in _skip_names:
                continue
            inp = re.search(r"(?<![\w'])" + re.escape(w) + r"(?![\w'])", prompt)
            if inp and not re.search(r"(?<![\w'])" + re.escape(w) + r"(?![\w'])",
                                     vis_prompt):
                note("D ★★ 정답이 쓰는 이름이 **잘려서** 안 보임", f"idx={i} {w}")

        # ── E. 위생 ──
        if "\x00" in s:
            note("E ★ NUL 문자", f"idx={i}")
        for sec in ("PREMISES", "PROOFS", "STATE", "SCRIPT", "TYPES", "DEFINITIONS"):
            if prompt.count(f"[{sec}]") > 1:
                note(f"E ★ [{sec}] 헤더 중복", f"idx={i}")

        # ── G. cut ──
        if os.environ.get("CUTS_PATH", ""):
            from tactic_gen import cut_lookup
            k = f"{e.file_name}:{e.proof_idx}:{e.step_idx}"
            if cut_lookup.cut_for(k):
                st["G cut 적용"] += 1
            if cut_lookup.is_hopeless(k):
                note("G ★★ hopeless 가 학습에 들어왔다", f"idx={i} {k}")

        # ── F. 결정성 (구간마다 앞 3건) ──
        if i - sp < 3:
            try:
                if coll.collate(tok, ds.resolved_example(i)) != s:
                    note("F ★ 두 번 만들면 다르다", f"idx={i}")
            except Exception:
                pass

n = max(st["검사"], 1)
print(f"■ 결과 (검사 {st['검사']}건)\n")
for k in sorted(st):
    if k == "검사":
        continue
    print(f"   {k:44s} {st[k]:5d}  {st[k]/n*100:5.1f}%")
    for x in bad[k]:
        print(f"        {x}")

fatal = sorted(k for k in st if "★" in k)
print()
if fatal:
    print("★ 치명 항목:")
    for f in fatal:
        print(f"   · {f}  ({st[f]}건)")
    sys.exit(1)
print("✓ 치명 항목 없음 — 전 구간에서 학습 경로 정상")
