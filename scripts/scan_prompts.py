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
import rango_defaults as _D
logging.disable(logging.CRITICAL)
# ★ 설정의 출처는 `all_log/v9_env.sh` **하나**다. 여기에 값을 다시 적으면 반드시
#   어긋나고, 어긋나도 오류가 안 난다 — 조용히 다른 실험을 재게 된다(실제로 겪었다:
#   옛 CUTS_PATH 로 U1 을 재고, structural 로 "학습과 같은 설정" 감사를 돌렸다).
sys.path.insert(0, "scripts")
from _env_from_v9 import apply_v9_env  # noqa: E402
apply_v9_env(verbose=True)
# ★ stdlib 은 **모델이 안다고 가정**한다 (2026-08-22 결정).
#   근거: rango 의 PremiseFilter 가 lib/coq/theories 를 풀에서 통째로 빼므로 검색으로
#   도달 불가인데, 파일 하나에 stdlib premise 가 11,196개씩 딸려 와 전부 보여 줄 수도
#   없다(모듈 목록만 넣어도 758토큰 — premise 예산 896을 거의 다 먹는다).
#   Coq 실측으로 접근성 자체는 문제가 아님도 확인했다: 이미 로드돼 있으면
#   `Coq.Lists.List.app_nil_r` 같은 정규화 이름이 그대로 통한다. 문제는 **이름을
#   아느냐**이고, 그건 프롬프트로 못 준다. → 환각 집계에서 분리한다.
try:
    _STDLIB = set(_json.load(open("data/stdlib_names.json")))
except Exception:
    _STDLIB = set()
# ★ L6 분류용 사전 — 이름이 lemma 인가 함수인가 Ltac 인가
import json as _json  # noqa: E402
try:
    # ★ 2단 구조다: {"kind": {이름: 종류}, "ctor": {...}}
    _dk = _json.load(open("data/decl_kinds.json"))
    _KINDS = _dk.get("kind", _dk) if isinstance(_dk, dict) else {}
except Exception:
    _KINDS = {}
try:
    _FD = _json.load(open(os.environ.get("FUNC_DEFS_PATH", "data/func_defs_v3.json")))
except Exception:
    _FD = {}
from _coq_vocab import is_core  # noqa: E402
# ★ `True` · `BoolSpec` 같은 Coq **기본 어휘**를 프로젝트 이름으로 세면
#   "프롬프트에 없다 → 환각" 이라고 신고해 학습을 막는다(실측 오탐).
# ★ 표본 측정은 **요청된 예제만** 만든다. 캐시는 파일(페이지) 단위라 미스 한 번이
#   그 파일의 모든 proof×step 을 짓는데, 표본은 파일당 한두 건만 쓰므로 순 낭비다.
#   실측: 페이지 빌드 경로 7분에 27건 → 요청 예제만 만들면 56초에 50건.
#   (학습은 한 파일을 여러 번 쓰므로 페이지 빌드가 이득이다 — 거기선 바꾸지 않는다.)
os.environ.setdefault("CACHE_MAX_PAGE", "0")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")


def _strip_comments(t: str) -> str:
    """Coq 주석 `(* … *)` 를 지운다 — 주석 안 낱말은 **이름이 아니다**.

    실측 오탐: `(* Caso Indutivo *)` 의 Indutivo,
    `(* move both quantifiers into the context: *)` 의 quantifiers,
    `(* We choose a preimage by [grp_quotient_map]. *)` 의 preimage·merely
    를 전부 "프롬프트에 없는 이름" 으로 신고했다. 중첩 주석까지 처리한다.
    """
    out, depth, i = [], 0, 0
    while i < len(t):
        if t.startswith("(*", i):
            depth += 1; i += 2; continue
        if t.startswith("*)", i) and depth:
            depth -= 1; i += 2; continue
        if not depth:
            out.append(t[i])
        i += 1
    return "".join(out)

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
HARD = _D.num("HARD_SEQ_LEN")

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
# ★★ "정규화 이름이 **문자열 안**에 새어 들어갔나" 를 볼 때, 이름을 **요구하는**
#   정규식으로 문자열을 찾으면 안 된다 — 그러면 이름을 포함하도록 따옴표 짝이
#   **어긋나게** 잡힌다. 실측 오탐:
#       (ELit (C0 "io" )) (ELit (C0 "fwrite" ))
#   여기서 `" )) (ELit (C0 "` 가 문자열 하나로 매칭된다. C0 는 문자열 **밖**이다.
#   → 리터럴을 **먼저 왼쪽부터 순서대로 짝지어** 찾고, 그 다음 내용만 본다.
#   (이 패턴 계열의 오탐은 이번이 여섯 번째다.)
STR_LIT = re.compile(r'"(?:[^"\n]|"")*"')        # Coq 문자열: "" 이 이스케이프
CMT_LIT = re.compile(r"\(\*.*?\*\)", re.S)        # 주석 (중첩은 무시 — 보수적)
NORM_IN = re.compile(r"(?<![\w'])[TfCLG]\d+(?![\w'])")


# 우리 정규화가 만든 이름은 프롬프트 어딘가에 **선언**으로 나타난다
#   premise → `Lemma L3 …` · 타입 → `Inductive T0 :=` · 함수 → `Definition f2 …`
_OUR_DECL = re.compile(
    r"^\s*(?:Lemma|Theorem|Definition|Corollary|Remark|Fact|Fixpoint|Instance|"
    r"Axiom|Proposition|Example|Let|Inductive|Record|Class|Variant)\s+"
    r"([TfCLG]\d+)(?![\w'])", re.M)


def norm_in_literals(text, pat):
    """`pat` 이 잡는 리터럴들 **안에서만** 정규화 이름을 찾는다. 첫 건을 돌려준다.

    ★★ 그 이름이 **우리가 만든 것인지** 확인한다. `[TfCLG]\d+` 꼴은 실제 Coq 코드에
      흔하다 — 실측 오탐: `Lemma … forall T1 T2, eqb_ty T1 T2 = true -> T1 = T2` 의
      주석 `(* T1=Bool *)`. 여기서 T1 은 **저자의 변수명**이다.
      우리 정규화가 만든 이름은 프롬프트 어딘가에 **선언**(`Lemma L3 …`)으로 나타나므로
      그걸 표지로 쓴다. (이 계열 오탐은 이번이 여덟 번째다.)
    """
    ours = set(_OUR_DECL.findall(text or ""))
    if not ours:
        return None
    for m in pat.finditer(text or ""):
        for nm in NORM_IN.findall(m.group(0)):
            if nm in ours:
                return m.group(0)
    return None
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
    for w in set(re.findall(r"(?<![\w'])([A-Za-z_][\w']{3,})(?![\w'])",
                            _strip_comments(target))):
        if w in TACWORDS or NORM.fullmatch(w) or w in _skip_names or is_core(w):
            continue
        _pw = re.compile(r"(?<![\w'])" + re.escape(w) + r"(?![\w'])")
        if _pw.search(prompt):
            if not _pw.search(vis_p):
                note("L3 ★ 정답이 쓰는 이름이 절단 후 안 보인다", f"idx={i} {w}")
        else:
            # ★★ **검사기의 구멍이었다.** 옛 코드는 "프롬프트에 있는데 절단으로 사라진"
            #   경우만 신고했다. 애초에 **어디에도 없는** 이름은 조용히 넘어갔는데,
            #   그게 가장 나쁜 경우다 — 모델이 순수하게 지어내야 한다.
            # ★ **무엇인지 분류**해야 대응이 정해진다.
            #   lemma  → cut 으로 assert 할 수 있다
            #   함수/타입 → 명제가 아니라 assert 불가. [DEFINITIONS] 주입 대상
            #   Ltac   → 주입도 불가. hopeless 로 빼야 한다
            if w in _STDLIB or w.split(".")[-1] in _STDLIB:
                st["L6b stdlib (안다고 가정 — 환각 아님)"] += 1
                continue
            _kind = "미상"
            try:
                _k = _KINDS.get(w) or _KINDS.get(w.split(".")[-1])
                if _k:
                    _kind = _k
                elif w in _FD:
                    _kind = "정의(func_defs)"
            except Exception:
                pass
            st[f"L6-분류 {_kind}"] += 1
            note("L6 ★ 정답이 쓰는 이름이 프롬프트에 **아예 없다**",
                 f"idx={i} {w} [{_kind}] ← {target[:55]}")
    # ★★ 위험한 것은 "같은 이름이 두 번" 이 아니라 **"같은 이름 · 다른 명제"** 다.
    #   같은 lemma 가 모듈마다 재수출되면 명제가 **똑같은** 선언이 여러 줄 온다
    #   (실측: `Lemma L6 m x e \`{!Ok m} : find x (add x e m) = Some e.` 가 3줄).
    #   그건 `apply L6` 이 어느 것으로 읽혀도 맞으므로 해롭지 않다.
    #   명제가 **다르면** 모델이 뜻이 다른 둘을 한 이름으로 배운다 — 그게 진짜 N2 다.
    #   (이름만 다른 선언은 `premise_names` 가 이미 매핑에서 뺀다. 뚫리는 것은
    #    `add_spec1` 과 `add_spec1'` 처럼 **이름이 실제로 다른** 경우다.)
    _prem_body = body.get("PREMISES", "")
    _by_name = collections.defaultdict(set)
    for _ln in _prem_body.split("\n"):
        _m = DECL.match(_ln.strip())
        if not _m or not NORM.fullmatch(_m.group(1)):
            continue
        # 명제 = `:` 뒤. 다만 **바인더 블록을 먼저 지운다** — `{Hm:Ok m}` 안에도
        # 콜론이 있어서, 먼저 split 하면 `Ok m}: …` 이 명제가 되어 같은 명제를
        # 서로 다르다고 신고한다(실측: L9 두 줄이 그 형태였다).
        _st = re.sub(r"[{`(\[][^{}()\[\]]*[}\)\]]", "", _ln)
        _st = _st.split(":", 1)[-1]
        _by_name[_m.group(1)].add(re.sub(r"\s+", "", _st))
    for nm, sts in _by_name.items():
        if len(sts) > 1:
            note("N2 ★ 같은 정규화 이름이 **서로 다른 명제** 둘에 붙었다",
                 f"idx={i} {nm}  ({len(sts)}종)")
        elif len(DECL.findall(_prem_body)) and \
                collections.Counter(DECL.findall(_prem_body))[nm] > 1:
            st["N2b 같은 이름·같은 명제가 여러 줄 (무해)"] += 1
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
    _sl = norm_in_literals(prompt, STR_LIT)
    if _sl:
        note("N5 ★ 문자열 안 정규화", f"idx={i} {_sl[:60]}")
    _cl = norm_in_literals(prompt, CMT_LIT)
    if _cl:
        note("N5 ★ 주석 안 정규화", f"idx={i} {_cl[:60]}")

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
