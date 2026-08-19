#!/usr/bin/env python3
"""★ 익명화로 **gold tactic 생성에 필요한 정보가 빠졌는지** 검사한다.

## 용어

  · **익명화(정규화)**  프롬프트의 lemma·정의 이름을 `L0` `T0` `f0` `C0` `G0` 로 바꾸는 것.
    이름 암기로 tactic 을 찍는 습관을 끊으려는 것이다. 프롬프트와 정답에 **같은 매핑**을
    적용하므로, 프롬프트에 있는 것을 정답이 가리키면 이름이 같이 바뀌어 연결이 유지된다.
  · **환각(hallucination)**  정답 tactic 이 프롬프트 어디에도 없는 이름을 쓰는 것.
    모델은 그 이름을 **지어낼 수밖에 없다** — 배울 수 없는 예제다.

## 무엇을 재나

collate 를 실제로 돌려 (프롬프트, 정답)을 얻고, **정답에 나오는 식별자마다** 그것이
어디서 온 것인지 분류한다.

    ⓐ 프롬프트에 있다        → 읽고 쓸 수 있다 (정상)
    ⓑ tactic 키워드          → intros, apply, auto … (배워야 할 대상, 정상)
    ⓒ Coq 기본어휘          → nat, list, eq, S, O … (사전지식, 정상)
    ⓓ **어디에도 없다**      → ★ 환각. 지어내야 한다

ⓓ 가 이 실험의 대상이다. 익명화 전/후를 비교해 **익명화가 ⓓ 를 늘리는지**를 본다.

사용: python3 scripts/check_anon_loss.py [n] [train|val|test]
"""
import collections
import copy
import os
import re
import sys

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.insert(0, "src")
import logging  # noqa: E402

logging.disable(logging.CRITICAL)
import yaml  # noqa: E402
from transformers import AutoTokenizer  # noqa: E402
from data_management.splits import Split  # noqa: E402
from tactic_gen.tactic_data import TacticDataConf, LmDataset  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 500
SPLIT = (sys.argv[2] if len(sys.argv) > 2 else "train").upper()

# ⓑ tactic 키워드 · 결합자
_TAC = set("""intros intro apply exact refine rewrite erewrite reflexivity symmetry
transitivity assumption auto eauto trivial simpl unfold fold destruct induction case
elim inversion injection discriminate constructor split left right exists
econstructor esplit specialize generalize revert clear subst omega lia nia ring field
congruence tauto firstorder intuition now by move case elim have suff wlog pose set
remember replace change cbn cbv compute vm_compute native_compute
assert eassert cut enough refine idtac fail try repeat first solve do progress
unshelve abstract instantiate admit Admitted Qed Defined Proof
in as with using at into after before else then end
""".split())
# ⓒ Coq 기본 어휘 (극히 흔한 것만 — 넓게 잡으면 환각을 놓친다)
_BUILTIN = set("""nat bool Prop Type Set list option prod sum unit True False
eq eq_refl eq_sym eq_trans f_equal S O Z N R Q le lt ge gt plus minus mult
cons nil app length rev map filter fold_left fold_right In
andb orb negb true false tt I conj or_introl or_intror ex_intro
forall exists fun match let fix cofix if is return of
""".split())
_ID = re.compile(r"[A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*")

cc = yaml.safe_load(open("all_log/ft_qwen3b_v8_conf.yaml"))
tdc = copy.deepcopy(cc["tactic_data"])
conf = TacticDataConf.from_yaml(tdc)
ds = LmDataset.from_conf(conf, getattr(Split, SPLIT), 10 ** 9)
tok = AutoTokenizer.from_pretrained(cc["model_name"])
from tactic_gen.tactic_data import example_collator_from_conf  # noqa: E402
coll = example_collator_from_conf(conf.collator_conf)


def classify(prompt: str, target: str):
    """정답의 식별자를 ⓐ~ⓓ 로 분류."""
    pset = set(_ID.findall(prompt))
    out = collections.Counter()
    unknown = []
    for w in _ID.findall(target):
        base = w.split(".")[-1]
        if w in pset or base in pset:
            out["ⓐ 프롬프트에 있음"] += 1
        elif base in _TAC:
            out["ⓑ tactic 키워드"] += 1
        elif base in _BUILTIN:
            out["ⓒ Coq 기본어휘"] += 1
        elif base.isdigit() or len(base) <= 1:
            out["ⓒ Coq 기본어휘"] += 1
        else:
            out["ⓓ ★ 어디에도 없음"] += 1
            unknown.append(w)
    return out, unknown


res = {}
for mode, envs in (("익명화 OFF", {"NORMALIZE_NAMES": "0"}),
                   ("익명화 ON", {"NORMALIZE_NAMES": "1", "NORMALIZE_RATE": "1.0",
                                  "NORMALIZE_PREMISES": "1", "NORMALIZE_THEOREM": "1"})):
    for k, v in envs.items():
        os.environ[k] = v
    os.environ["AUGMENT_V2"] = "1"
    os.environ["RERANK_PREMISES"] = "1"
    os.environ["INJECT_TYPES"] = "1"
    os.environ["INJECT_DEFS"] = "1"
    cnt = collections.Counter()
    bad_steps = 0
    n = 0
    samples = []
    for i in range(N):
        try:
            e = ds.raw_example(i)
        except Exception:
            continue
        try:
            s = coll.collate(tok, e)
        except Exception:
            continue
        # 정답은 마지막 [TACTIC] 뒤
        if "[TACTIC]" not in s:
            continue
        prompt, target = s.rsplit("[TACTIC]", 1)
        n += 1
        c, unk = classify(prompt, target)
        cnt.update(c)
        if unk:
            bad_steps += 1
            if len(samples) < 6:
                samples.append((sorted(set(unk))[:5], target.strip()[:80]))
    tot = max(sum(cnt.values()), 1)
    res[mode] = (cnt, n, bad_steps, tot, samples)

print(f"\n■ {SPLIT} — 익명화 정보 손실 검사")
print(f"   정답 tactic 의 식별자가 프롬프트에서 읽을 수 있는가\n")
print(f"   {'':22s} {'익명화 OFF':>14s} {'익명화 ON':>14s}")
keys = ["ⓐ 프롬프트에 있음", "ⓑ tactic 키워드", "ⓒ Coq 기본어휘", "ⓓ ★ 어디에도 없음"]
for k in keys:
    a = res["익명화 OFF"][0][k] / res["익명화 OFF"][3] * 100
    b = res["익명화 ON"][0][k] / res["익명화 ON"][3] * 100
    print(f"   {k:22s} {a:13.1f}% {b:13.1f}%")
for mode in ("익명화 OFF", "익명화 ON"):
    cnt, n, bad, tot, _ = res[mode]
    print(f"\n   {mode}: 예제 {n}건 중 **{bad}건({bad/max(n,1)*100:.1f}%)** 이 "
          f"프롬프트에 없는 이름을 쓴다")
print(f"\n   ■ 익명화 ON 에서 지어내야 하는 이름 (표본)")
for unk, t in res["익명화 ON"][4]:
    print(f"     {unk}")
    print(f"       ← {t}")
