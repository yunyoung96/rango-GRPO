#!/usr/bin/env python3
"""정규화(α-치환) 파이프라인 **동적 전수 검증**.

검사하는 불변식:

  A 검색 불변    정규화 ON/OFF 에서 [PREMISES] 의 lemma 이름 집합이 **동일**해야 한다.
                 (정규화가 검색보다 먼저 일어나면 tfidf 질의가 T0/f1 이 되어 검색이 망가진다)
  B 단사성       서로 다른 원래 이름이 같은 새 이름으로 가면 안 된다.
  C 충돌 없음    새로 만든 이름(T0/f1/C2)이 원문에 **이미 있으면 안 된다**.
                 (실측 사고: goal 에 `f, f0: float` 가 있는데 f0 을 새로 만들어 충돌)
  D 일관성       프롬프트와 정답에 **같은 매핑**이 적용돼야 한다.
                 (매핑된 원래 이름이 정답에 그대로 남아 있으면 위반)
  E 보호 대상    섹션 헤더·tactic 이름·stdlib 상식은 안 바뀐다.
                 (실측 사고: [ERROR] → [T7], pattern → f11)
  F 역매핑 왕복  치환 후 역매핑하면 원문이 복원돼야 한다(v7 추론에서 실제 이름 복원에 필요).

사용: python3 scripts/verify_normalize.py [예제수]
"""
import collections
import importlib
import json
import os
import re
import sys

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.insert(0, "src")
import logging  # noqa: E402

logging.disable(logging.CRITICAL)
import yaml  # noqa: E402


def _word(name: str) -> str:
    """치환기와 **같은 식별자 개념**으로 찾는다.

    ★ `\bsz\b` 는 `sz'` 의 앞부분에 매칭된다(작은따옴표가 단어경계로 취급됨).
      그런데 치환기의 _IDENT 는 `[A-Za-z_][\w']*` 라 `sz'` 를 **하나의 다른 식별자**로 본다.
      이 불일치로 "정답에 원래 이름 잔존" 오탐이 났다(실측 1건).
    """
    return r"(?<![\w'])" + re.escape(name) + r"(?![\w'])"
from transformers import AutoTokenizer  # noqa: E402
from tactic_gen.lm_example import LmExample  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 200
CONF = os.environ.get("CONF", "all_log/ft_qwen3b_v6_conf.yaml")
cc = yaml.safe_load(open(CONF))
tok = AutoTokenizer.from_pretrained(cc["model_name"])

_LN = re.compile(r"(?:Lemma|Theorem|Definition|Corollary|Remark|Fact)\s+([A-Za-z_][\w']*)")
_HDR = re.compile(r"\[[A-Z][A-Z_ -]*\]")
_NEW = re.compile(r"\b[TfCLG]\d+\b")
_STDLIB_SAMPLE = {"nat", "list", "bool", "option", "Z", "S", "O", "cons", "nil", "True", "False"}
_TACTICS = {"intros", "destruct", "apply", "rewrite", "auto", "eauto", "simpl", "unfold",
            "induction", "reflexivity", "lia", "exact", "split", "constructor"}

examples = []
for line in open("data/grpo_rollouts/goldsft_bs2.jsonl"):
    g = json.loads(line)
    for a in g["attempts"]:
        if a["reward"] < 1.0:
            continue
        for st in a["steps"]:
            if st.get("example") and st.get("tactic"):
                e = LmExample.from_json(st["example"])
                e.next_steps = [st["tactic"]]
                examples.append(e)
                if len(examples) >= N:
                    break
        if len(examples) >= N:
            break
    if len(examples) >= N:
        break


def build(rate: str):
    """주어진 NORMALIZE_RATE 로 (프롬프트, 정답, 주입이름, **실제 매핑**) 목록을 만든다.

    ★ 매핑을 추론하지 말고 **가로채야** 한다. 원문에 원래 있던 `f0`(예: `f, f0: float`)
      까지 '새로 만든 이름'으로 세면 충돌 오탐이 난다(실제로 61건 오탐).
    """
    os.environ["NORMALIZE_RATE"] = rate
    import tactic_gen.normalize_names as nn
    importlib.reload(nn)
    _orig = nn.build_mapping
    captured = {}
    def _spy(injected, seed_key, avoid_text="", premises=None, proof_script=None):
        m = _orig(injected, seed_key, avoid_text, premises, proof_script)
        captured[seed_key] = (dict(m), avoid_text, nn.LAST_THM_DECL)
        return m
    nn.build_mapping = _spy
    import tactic_gen.tactic_data as td
    importlib.reload(td)
    td.build_mapping = _spy
    col = td.example_collator_from_conf(
        td.example_collator_conf_from_yaml(cc["example_collator"]))
    out = []
    for e in examples:
        full = col.collate(tok, e)
        tail = full.split(td.MASK_TEMPLATE)[-1]
        mp = list(captured.values())[-1] if captured else ({}, "", None)
        out.append((full, tail, dict(td._LAST_INJECTED), mp[0], mp[2]))
        captured.clear()
    return out


off = build("0.0")
on = build("1.0")

fail = collections.Counter()
fail_selfretrieval = [0]
ex = collections.defaultdict(list)
n_norm = 0

for _e_cur, (p0, t0, inj0, _m0, _a0), (p1, t1, inj1, mapping, thm_decl) in zip(
        [(e,) for e in examples], off, on):
    # ── A 검색 불변 ──
    def prem(p):
        return set(_LN.findall(p[p.index("[PREMISES]"):p.index("[PROOFS]")])) \
            if "[PREMISES]" in p and "[PROOFS]" in p else set()
    _inv = {v: k for k, v in (mapping or {}).items()}
    import tactic_gen.normalize_names as _nn0
    # ★ 정리 선언부는 매핑 밖에서 G# 로 따로 치환된다(동명 충돌 시). 역매핑도 그걸 알아야
    #   복원된다 — v8 추론에서 실제 이름으로 되돌릴 때 같은 처리가 필요하다.
    p1_pre = p1
    if thm_decl:
        _g = re.search(r"(?:Lemma|Theorem|Remark|Corollary|Fact|Proposition|Definition)\s+(G\d+)", p1)
        if _g:
            p1_pre = _nn0.substitute_theorem_decl(p1, _g.group(1),
                                                  mapping.get(thm_decl, thm_decl))
    p1_restored = _nn0.apply_mapping(p1_pre, _inv) if _inv else p1_pre
    # ★ 이름이 바뀐 것과 **검색 결과가 바뀐 것**은 다르다. 역매핑으로 되돌린 뒤 비교해야
    #   "정규화가 tfidf 질의를 오염시켰나"를 정확히 잰다.
    if prem(p0) != prem(p1_restored):
        fail["A 검색 결과가 정규화로 바뀜"] += 1
        if len(ex["A"]) < 2:
            ex["A"].append(f"OFF-ON 차이 {sorted(prem(p0) - prem(p1_restored))[:3]}")

    if not mapping:
        continue
    n_norm += 1
    vals = list(mapping.values())

    # ── B 단사성 ──
    if len(vals) != len(set(vals)):
        fail["B 단사성 위반(두 이름이 같은 새 이름으로)"] += 1
        if len(ex["B"]) < 2:
            ex["B"].append(str({k: v for k, v in mapping.items()})[:90])

    # ── C 충돌: **새로 만든** 이름이 정규화 전 원문에 이미 있었나 ──
    pre = set(_NEW.findall(p0))
    clash = set(vals) & pre
    if clash:
        fail["C 새 이름이 원문에 이미 존재"] += 1
        if len(ex["C"]) < 2:
            ex["C"].append(f"충돌 {sorted(clash)[:3]}  매핑 {list(mapping.items())[:3]}")

    # ── D 일관성: 치환된 원래 이름이 정답에 남아 있으면 위반 ──
    for nm in mapping:
        if re.search(_word(nm), t1):
            fail["D 정답에 원래 이름 잔존"] += 1
            if len(ex["D"]) < 2:
                ex["D"].append(f"{nm!r} in {t1[:40]!r}")
            break

    # ── E 보호 대상 ──
    if set(_HDR.findall(p0)) != set(_HDR.findall(p1)):
        fail["E 섹션 헤더 훼손"] += 1
        if len(ex["E"]) < 2:
            ex["E"].append(f"{sorted(set(_HDR.findall(p0)) ^ set(_HDR.findall(p1)))[:3]}")
    for w in _STDLIB_SAMPLE | _TACTICS:
        if re.search(_word(w), p0) and not re.search(_word(w), p1):
            fail["E 보호 이름(stdlib/tactic)이 치환됨"] += 1
            if len(ex["E2"]) < 2:
                ex["E2"].append(w)
            break

    # ── F 역매핑 왕복: inv(apply(text)) == text ──
    import tactic_gen.normalize_names as _nn
    inv = {v: k for k, v in mapping.items()}
    if _nn.apply_mapping(p1_pre, inv) != p0 or _nn.apply_mapping(t1, inv) != t0:
        fail["F 역매핑 왕복 실패"] += 1
        if len(ex["F"]) < 2:
            ex["F"].append(f"매핑 {list(mapping.items())[:2]}")

    # ── G 완전 치환: 매핑된 원래 이름이 프롬프트에 하나도 남지 않아야 ──
    for nm in mapping:
        if re.search(_word(nm), p1):
            fail["G 프롬프트에 원래 이름 잔존(부분 치환)"] += 1
            if len(ex["G"]) < 2:
                ex["G"].append(f"{nm!r} → {mapping[nm]!r} 인데 원문 잔존")
            break

    # ── I (v7) premise lemma 가 실제로 치환됐나 + L 접두사인가 ──
    if os.environ.get("NORMALIZE_PREMISES", "0") == "1":
        import tactic_gen.normalize_names as _nn2
        pset = set(_nn2.premise_names(list(getattr(_e_cur[0], "premises", None) or [])))
        # 주입 정의 이름과 겹치면 T/f/C 매핑이 우선이다(중복 금지) → L 검사에서 제외
        mapped_prem = {k: v for k, v in mapping.items()
                       if k in pset and k not in inj0}
        if pset and not mapped_prem:
            fail["I premise 이름이 하나도 치환 안 됨"] += 1
        for k, v in mapped_prem.items():
            if not v.startswith("L"):
                fail["I premise 가 L 접두사가 아님"] += 1
                if len(ex["I"]) < 2: ex["I"].append(f"{k} → {v}")
                break
        # 치환된 premise 이름이 프롬프트에 남아 있으면 안 된다
        for k in mapped_prem:
            if re.search(_word(k), p1):
                fail["I 치환된 premise 이름 잔존"] += 1
                if len(ex["I2"]) < 2: ex["I2"].append(k)
                break

    # ── J (v8) 증명 중인 정리 이름이 G 로 치환됐나 ──
    if os.environ.get("NORMALIZE_THEOREM", "0") == "1":
        import tactic_gen.normalize_names as _nn4
        tn = _nn4.theorem_name(getattr(_e_cur[0], "proof_script", "") or "")
        if tn and tn in mapping:
            # ★ 정리 이름이 [PREMISES] 에도 있으면(자기 정리가 검색된 경우, 실측 1.7%)
            #   premise 매핑(L#)이 이긴다 — 이름 하나에 매핑 하나여야 하므로 정상이다.
            import tactic_gen.normalize_names as _nn6
            _is_prem = tn in set(_nn6.premise_names(
                list(getattr(_e_cur[0], "premises", None) or [])))
            if _is_prem:
                fail_selfretrieval[0] += 1
            elif not mapping[tn].startswith("G"):
                fail["J 정리 이름이 G 접두사가 아님"] += 1
                if len(ex["J"]) < 2: ex["J"].append(f"{tn} → {mapping[tn]}")
            if re.search(_word(tn), p1):
                fail["J 정리 이름이 프롬프트에 잔존"] += 1
                if len(ex["J2"]) < 2: ex["J2"].append(tn)

    # ── H 대상 범위: 매핑 키는 주입된 정의 이름이나 그 생성자여야 ──
    # ★ build_mapping 과 **똑같이** 뽑아야 한다. 예전엔 `\|\s*(...)` 로만 찾아
    #   `Inductive t := Decimal | Hex` 의 **첫 생성자(Decimal)**를 놓쳐 오탐이 났다.
    allowed = set(inj0)
    for d in inj0.values():
        if ":=" not in d:
            continue
        for part in d.split(":=", 1)[1].split("|"):
            m2 = re.match(r"\s*([A-Za-z_][\w']*)", part)
            if m2:
                allowed.add(m2.group(1))
    if os.environ.get("NORMALIZE_PREMISES", "0") == "1":
        import tactic_gen.normalize_names as _nn3
        allowed |= set(_nn3.premise_names(list(getattr(_e_cur[0], "premises", None) or [])))
    if os.environ.get("NORMALIZE_THEOREM", "0") == "1":
        import tactic_gen.normalize_names as _nn5
        _tn = _nn5.theorem_name(getattr(_e_cur[0], "proof_script", "") or "")
        if _tn: allowed.add(_tn)
    stray = set(mapping) - allowed
    if stray:
        fail["H 주입되지 않은 이름을 치환"] += 1
        if len(ex["H"]) < 2:
            ex["H"].append(f"{sorted(stray)[:4]}")

print(f"■ 정규화 검증 — 예제 {len(examples)}개 (정규화 적용 {n_norm}개)")
if fail_selfretrieval[0]:
    print(f"   ※ 참고: 증명 중인 정리가 [PREMISES] 에도 검색된 경우 {fail_selfretrieval[0]}건 "
          f"({fail_selfretrieval[0]/max(n_norm,1)*100:.1f}%) — 매핑은 정상(L#)이나 검색 누출\n")
else:
    print()
if not fail:
    print("   ✅ A~F 전부 통과")
else:
    for k, v in fail.most_common():
        print(f"   ❌ {k}: {v}건")
    for k, vs in ex.items():
        for s in vs:
            print(f"      [{k}] {s}")
