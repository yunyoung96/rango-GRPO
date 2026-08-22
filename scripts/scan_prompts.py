#!/usr/bin/env python3
"""완성 프롬프트를 **대량으로** 훑으며 위험 항목을 전부 센다.

40건 눈으로 보는 것(`gen_prompt_comparison.py`)과 역할이 다르다. 저쪽은 사람이
못 보던 것을 찾는 용도고, 이쪽은 **내가 이름 붙인 위험**이 실제로 몇 %인지 재는 용도다.
둘 다 필요하다 — 이름 붙인 것만 세면 생각 못 한 것을 놓치고, 눈으로만 보면 빈도를 모른다.

검사 항목 (★ = 치명, 하나라도 나오면 학습이 망가진다)

  라벨   L1 ★ 정답이 비었다
         L2 ★ 정답의 정규화 이름이 프롬프트에 없다
         L3 ★ 정답의 이름이 **절단 후** 안 보인다 (환각 학습)
         L4 ★ 정답에 섹션 헤더가 섞였다
         L5   정답이 프롬프트 꼬리와 그대로 겹친다 (복사로 풀린다)

  cut    U1 ★ cut 인데 `exact L` 의 L 이 프롬프트에 없다
         U2 ★ cut 의 괄호가 안 맞는다
         U3 ★ cut 의 H_asrt 이름이 기존 가설과 충돌
         U4 ★ hopeless 가 학습에 들어왔다

  정규화 N1 ★ 정규화 이름이 쓰였는데 **선언이 프롬프트에 없다** (dangling)
         N2 ★ 같은 정규화 이름이 서로 다른 두 선언에 붙었다 (비단사)
         N3   같은 문장이 다른 이름으로 두 번 (반쪽 치환 의심)
         N4 ★ 모듈 접두사가 오염됐다
         N5 ★ 문자열·주석 안이 치환됐다

  섹션   S1 ★ 헤더 중복      S2 ★ 헤더 순서 역전    S3 빈 섹션
         S4 ★ [STATE] 없음   S5 ★ NUL·제어문자

  절단   T1   2048 초과       T2 ★ 절단으로 [TACTIC] 소실

  품질   Q1   [TYPES]/[DEFS] 에 본문 없는 시그니처
         Q2   모듈 별칭 정의  Q3 premise 중복  Q4 goal 이 비었다

  결정성 D1 ★ 같은 인덱스를 두 번 만들면 다르다

사용: PYTHONPATH=src python3 scripts/scan_prompts.py [건수]
"""
import collections
import copy
import logging
import os
import re
import sys

sys.path.insert(0, "src")
logging.disable(logging.CRITICAL)
# ★ 설정의 출처는 `all_log/v9_env.sh` **하나**다. 여기에 값을 다시 적으면 반드시
#   어긋나고, 어긋나도 오류가 안 난다 — 조용히 다른 실험을 재게 된다(실제로 겪었다:
#   옛 CUTS_PATH 로 U1 을 재고, structural 로 "학습과 같은 설정" 감사를 돌렸다).
sys.path.insert(0, "scripts")
from _env_from_v9 import apply_v9_env  # noqa: E402
apply_v9_env(verbose=True)
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")

N = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 1000

import yaml  # noqa: E402
from data_management.splits import Split  # noqa: E402
from tactic_gen.tactic_data import (TacticDataConf, LmDataset,  # noqa: E402
                                    example_collator_from_conf, get_tokenizer)

CONF = os.environ.get("CONF", "all_log/ft_qwen3b_v9_conf.yaml")
cc = yaml.safe_load(open(CONF))
conf = TacticDataConf.from_yaml(copy.deepcopy(cc["tactic_data"]))
tok = get_tokenizer(cc["model_name"])
assert tok.truncation_side == "left"
ds = LmDataset.from_conf(conf, Split.TRAIN, None)
coll = example_collator_from_conf(conf.collator_conf)
TOTAL = ds.shuffled_idx.split_length(Split.TRAIN)
HARD = int(os.environ.get("HARD_SEQ_LEN", "2048"))

SECS = ["PREMISES", "PROOFS", "STATE", "SCRIPT", "TYPES", "DEFINITIONS"]
HDR = re.compile(r"\[(" + "|".join(SECS) + r"|GOAL|TACTIC)\]")
NORM = re.compile(r"(?<![\w'])([TfCLG]\d+)(?![\w'])")
DECL = re.compile(r"(?:Lemma|Theorem|Definition|Corollary|Remark|Fact|Instance|Axiom|"
                  r"Parameter|Inductive|CoInductive|Variant|Record|Class|Fixpoint|"
                  r"CoFixpoint|Notation)\s+([A-Za-z_][\w']*)")
# ★ **생성자도 선언이다.** `Inductive f0 … := C0 : … | C1 : …` 의 C0/C1 은 DECL 이
#   머리 이름(f0)만 잡아서 '선언이 없다' 고 오탐했다(실측 idx=1555508).
CTOR = re.compile(r":=\s*\|?\s*([A-Za-z_][\w']*)|\|\s*([A-Za-z_][\w']*)")


def all_decls(text: str):
    out = set(DECL.findall(text))
    for ln in text.split("\n"):
        if re.search(r"\b(?:Inductive|CoInductive|Variant|Record|Class)\b", ln):
            for a, b in CTOR.findall(ln):
                if a: out.add(a)
                if b: out.add(b)
    return out
ALIAS = re.compile(r"^\s*(?:Definition|Notation)\s+[A-Za-z_][\w']*\s*:=\s*"
                   r"[A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)+\s*\.?\s*$", re.M)
STR_NORM = re.compile(r'"[^"\n]*(?<![\w])[TfCLG]\d+[^"\n]*"')
CMT_NORM = re.compile(r"\(\*[^*]*(?<![\w])[TfCLG]\d+", re.S)
# ★ `List.list` `Datatypes.tt` 는 **진짜 Coq 이름**이다. 오염은 "모듈 접두사 자체가
#   정규화 이름으로 바뀐" 경우이므로 접두사 쪽을 본다.
MODPOLL = re.compile(r"(?<![\w'.])[TfCLG]\d+\.[A-Za-z_]")
TACWORDS = {"intros", "intro", "apply", "eapply", "exact", "rewrite", "erewrite",
            "destruct", "induction", "simpl", "unfold", "reflexivity", "symmetry",
            "assumption", "auto", "eauto", "trivial", "constructor", "split",
            "left", "right", "exists", "lia", "omega", "ring", "congruence",
            "discriminate", "inversion", "injection", "subst", "generalize",
            "specialize", "pose", "assert", "clear", "revert", "replace", "change",
            "now", "try", "repeat", "solve", "idtac", "elim", "refine", "eexists",
            "eassumption", "f_equal", "cbn", "cbv", "compute", "case", "red", "hnf",
            "forall", "exists", "fun", "match", "with", "end", "let", "in", "if"}

st = collections.Counter()
bad = collections.defaultdict(list)


def note(k, s):
    st[k] += 1
    if len(bad[k]) < 3:
        bad[k].append(s[:170])


# ★ 인덱스 구간 지정 — `IDX_LO`/`IDX_HI`.
#   cut 은 청크 단위로 만들어지므로 **뒤쪽 인덱스가 마지막에 채워진다.**
#   앞쪽만 훑으면 "cut 이 없는 구간" 을 영영 못 본다(실제로 그 사고를 겪었다).
LO = int(os.environ.get("IDX_LO", "0"))
HI = int(os.environ.get("IDX_HI", "0")) or TOTAL
SPAN = max(1, HI - LO)
step = max(1, SPAN // (N + 1))
t0 = __import__("time").time()
for c in range(N):
    i = LO + (c + 1) * step
    st["검사"] += 1
    try:
        e = ds.resolved_example(i)
        s = coll.collate(tok, e)
    except Exception as ex:
        note(f"★ 예외 {type(ex).__name__}", f"idx={i} {ex}")
        continue
    if "[TACTIC]" not in s:
        note("L4 ★ [TACTIC] 없음", f"idx={i}")
        continue
    prompt, target = s.rsplit("[TACTIC]", 1)
    target = target.strip()

    # ── 섹션 ──
    order = [m.group(1) for m in HDR.finditer(prompt)]
    for sec in SECS:
        if order.count(sec) > 1:
            note(f"S1 ★ [{sec}] 헤더 중복", f"idx={i}")
    seen_order = [x for x in order if x in SECS]
    want = [x for x in ["PREMISES", "PROOFS", "STATE", "SCRIPT", "TYPES", "DEFINITIONS"]
            if x in seen_order]
    if seen_order != want:
        note("S2 ★ 섹션 순서 역전", f"idx={i} {seen_order}")
    if "[STATE]" not in prompt:
        note("S4 ★ [STATE] 없음", f"idx={i}")
    if "\x00" in s or re.search(r"[\x01-\x08\x0b\x0c\x0e-\x1f]", s):
        note("S5 ★ 제어문자", f"idx={i}")

    pos = [(m.start(), m.group(1)) for m in HDR.finditer(prompt)]
    body = {}
    for k, (a, nm) in enumerate(pos):
        b = pos[k + 1][0] if k + 1 < len(pos) else len(prompt)
        body[nm] = prompt[a:b].split("]", 1)[1].strip()
    for sec in ("TYPES", "DEFINITIONS", "PREMISES"):
        if f"[{sec}]" in prompt and not body.get(sec, "").strip():
            st[f"S3 빈 [{sec}]"] += 1

    # ── 라벨 ──
    if not target:
        note("L1 ★ 정답이 비었다", f"idx={i}")
        continue
    if HDR.search(target):
        note("L4 ★ 정답에 섹션 헤더가 섞였다", f"idx={i} {target[:60]}")
    tail = prompt[-len(target) - 5:] if len(target) > 8 else ""
    if len(target) > 12 and target in tail:
        st["L5 정답이 프롬프트 꼬리와 겹친다"] += 1

    # ★ 도입되는 이름은 참조가 아니다 (`destruct X as [f1 …]` 의 f1)
    try:
        from tactic_gen.normalize_names import introduced_names as _intro
        _skip_names = _intro(target)
    except Exception:
        _skip_names = set()
    # ★★ [STATE] 의 **가설 이름**도 정규화 이름이 아니다 — 원본 파일의 지역 변수다.
    #   `[TfCLG]\d+` 는 우리 정규화 이름을 잡으라고 만든 패턴인데, 실제 Coq 코드에
    #   `f1, f2 : Set` · `C0 : ...` 같은 변수가 흔하다(gaia 계열에서 실측).
    #   그걸 "선언이 프롬프트에 없는 정규화 이름"으로 신고하면 학습이 막힌다 —
    #   이 패턴의 오탐은 이번이 **다섯 번째**다. 이제 지역 이름 출처를 셋 다 본다:
    #     ① 이 tactic 이 도입하는 이름 (introduced_names)
    #     ② [STATE] 의 가설 이름
    #     ③ 정규화가 실제로 만든 이름이면 선언이 프롬프트에 있다 (아래 _alld 검사)
    try:
        _st_body = re.search(r"\[STATE\]\n(.*?)(?=\n\[[A-Z]+\]|\Z)", prompt, re.S)
        if _st_body:
            for _ln in _st_body.group(1).split("\n"):
                _m = re.match(r"^([A-Za-z_][\w', ]*?)\s*:", _ln)
                if _m:
                    for _nm in _m.group(1).split(","):
                        _nm = _nm.strip()
                        if _nm:
                            _skip_names.add(_nm)
    except Exception:
        pass
    enc = tok(s, max_length=HARD, truncation=True)
    vis = tok.decode(enc["input_ids"], skip_special_tokens=True)
    vis_p = vis.rsplit("[TACTIC]", 1)[0] if "[TACTIC]" in vis else vis
    full = len(tok(s, add_special_tokens=False)["input_ids"])
    if full > HARD:
        st["T1 2048 초과"] += 1
        if "[TACTIC]" not in vis:
            note("T2 ★ 절단으로 [TACTIC] 소실", f"idx={i} len={full}")

    # ── 정규화 ──
    decls = collections.Counter(DECL.findall(prompt))
    _alld = all_decls(prompt)
    tnorm = set(NORM.findall(target)) - _skip_names
    for nm in tnorm:
        if not re.search(r"(?<![\w'])" + nm + r"(?![\w'])", prompt):
            note("L2 ★ 정답의 정규화 이름이 프롬프트에 없다", f"idx={i} {nm} ← {target[:60]}")
        elif not re.search(r"(?<![\w'])" + nm + r"(?![\w'])", vis_p):
            note("L3 ★ 정답의 이름이 절단 후 안 보인다", f"idx={i} {nm} ← {target[:60]}")
        elif nm not in _alld:
            note("N1 ★ 정규화 이름의 선언이 프롬프트에 없다", f"idx={i} {nm}")
    for w in set(re.findall(r"(?<![\w'])([A-Za-z_][\w']{3,})(?![\w'])", target)):
        if w in TACWORDS or NORM.fullmatch(w) or w in _skip_names:
            continue
        if re.search(r"(?<![\w'])" + re.escape(w) + r"(?![\w'])", prompt) and \
           not re.search(r"(?<![\w'])" + re.escape(w) + r"(?![\w'])", vis_p):
            note("L3 ★ 정답이 쓰는 이름이 절단 후 안 보인다", f"idx={i} {w}")
    for nm, c in decls.items():
        if NORM.fullmatch(nm) and c > 1:
            # [PREMISES] 안에서만 세야 한다 — [PROOFS] 는 같은 lemma 의 증명을 보여준다
            if len(DECL.findall(body.get("PREMISES", ""))) and \
               collections.Counter(DECL.findall(body.get("PREMISES", "")))[nm] > 1:
                note("N2 ★ 같은 정규화 이름이 두 번 선언됐다", f"idx={i} {nm}")
    stmts = collections.Counter()
    for ln in body.get("PREMISES", "").split("\n"):
        m = DECL.match(ln.strip())
        if m:
            stmts[ln.strip()[m.end() - len(m.group(1)):].split(":", 1)[-1].strip()] += 1
    for k2, v2 in stmts.items():
        if v2 > 1 and len(k2) > 25:
            st["N3 같은 문장이 두 번 (이름만 다름)"] += 1
            break
    if MODPOLL.search(prompt):
        note("N4 ★ 모듈 접두사 오염", f"idx={i} {MODPOLL.search(prompt).group(0)}")
    if STR_NORM.search(prompt):
        note("N5 ★ 문자열 안 정규화", f"idx={i} {STR_NORM.search(prompt).group(0)[:50]}")
    if CMT_NORM.search(prompt):
        note("N5 ★ 주석 안 정규화", f"idx={i}")

    # ── cut ──
    if "H_asrt" in target:
        st["cut 적용"] += 1
        if target.count("(") != target.count(")"):
            note("U2 ★ cut 괄호 불일치", f"idx={i} {target[:80]}")
        for m in re.finditer(r"exact\s+@?([\w'.]+?)\s*[.)]", target):
            nm = m.group(1)
            base = nm.split(".")[-1]
            if not re.search(r"(?<![\w'])" + re.escape(base) + r"(?![\w'])", prompt):
                note("U1 ★ cut 의 exact 대상이 프롬프트에 없다", f"idx={i} {nm}")
        for h in re.findall(r"as\s+(H_asrt\w*)", target):
            if re.search(r"(?<![\w'])" + h + r"\s*:", body.get("STATE", "")):
                note("U3 ★ H_asrt 이름 충돌", f"idx={i} {h}")
    if os.environ.get("CUTS_PATH", ""):
        from tactic_gen import cut_lookup
        k3 = f"{e.file_name}:{e.proof_idx}:{e.step_idx}"
        if cut_lookup.is_hopeless(k3):
            note("U4 ★ hopeless 가 학습에 들어왔다", f"idx={i} {k3}")

    # ── 품질 ──
    for sec in ("TYPES", "DEFINITIONS"):
        b2 = body.get(sec, "")
        if ALIAS.search(b2):
            note(f"Q2 [{sec}] 모듈 별칭 정의", f"idx={i} {ALIAS.search(b2).group(0)[:60]}")
        for ln in b2.split("\n"):
            if ln.strip() and ":=" not in ln and not re.search(r":\s*\S", ln):
                st[f"Q1 [{sec}] 본문 없는 줄"] += 1
    pl = [x.strip() for x in body.get("PREMISES", "").split("\n") if x.strip()]
    if len(pl) != len(set(pl)):
        st["Q3 premise 중복"] += 1
    if not body.get("STATE", "").strip():
        st["Q4 [STATE] 가 비었다"] += 1

    # ── 결정성 (앞 40건) ──
    if c < 40:
        try:
            if coll.collate(tok, ds.resolved_example(i)) != s:
                note("D1 ★ 두 번 만들면 다르다", f"idx={i}")
        except Exception:
            pass
    if (c + 1) % 200 == 0:
        el = __import__("time").time() - t0
        print(f"   {c+1}/{N}  ({el:.0f}s · {el/(c+1):.2f}s/건)", flush=True)

n = max(st["검사"], 1)
print(f"\n■ 결과 (완성 프롬프트 {st['검사']}건)\n")
for k in sorted(st):
    if k == "검사":
        continue
    print(f"   {k:52s} {st[k]:6d}  {st[k]/n*100:6.2f}%")
    for x in bad[k]:
        print(f"        {x}")
fatal = sorted(k for k in st if "★" in k)
print()
if fatal:
    print("★ 치명 항목:")
    for f in fatal:
        print(f"   · {f}  ({st[f]}건)")
    sys.exit(1)
print("✓ 치명 항목 없음")
