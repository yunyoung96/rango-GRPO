#!/usr/bin/env python3
"""★ **tactic 인자로 실제 쓰인 이름** 전수 수집 — 풀에서 뺄지 말지의 유일한 기준.

## 왜

rango 의 `PROJ_THM_FILTER_CONF` 는 프로젝트 파일에서 `DEFINITION`·`INDUCTIVE`·
`RECORD`·`FIXPOINT` 등을 **검색 풀에서 통째로 뺀다.** 그런데 HoTT 는 정리를
`Definition` 으로 선언한다 — 실측: HoTT 선언의 **83%가 풀에서 빠진다**(3,157/18,557).
그래서 정답이 `srapply isequiv_adjointify` 를 써도 그 이름은 검색으로 못 온다
(결손 이름의 **62%가 이렇게 풀에서 빠지는 종류**다).

"이름만 Definition 인 정리" 를 가르는 규칙을 여럿 시도했지만 다 깨졌다:
    `:=` 없음  → cancelL·inv_pp 는 `:=` 가 있다(증명항으로 쓴 정리)
    타입 모양   → isequiv_adjointify 의 타입은 그냥 `IsEquiv f` 다

**믿을 수 있는 건 사용 사실뿐이다** — 누가 `apply`/`rewrite` 인자로 쓴 적이 있는가.

★ 누출 방지: split 이 **프로젝트 단위**라 TRAIN 전용으로 만들면 VAL/TEST 프로젝트는
   통째로 비어 무용지물이다. 대신 **"서로 다른 파일 2개 이상에서 쓰였을 것"** 을 조건에
   넣는다 — 평가 대상 파일 **자신의 기여만으로는 절대 승격되지 않는다.**

출력 data/used_names.json  {proj: {name: [총횟수, 등장파일수]}}
사용: python3 scripts/build_used_names.py
"""
import collections
import json
import os
import re
import sys
import time

D = "raw-data/coq-dataset/data_points"
OUT = "data/used_names.json"

# 인자가 **이름 참조**인 tactic 들
_HEAD = re.compile(
    r"(?:^|[;\[\]|(){}\s])(apply|eapply|exact|eexact|refine|erefine|rapply|srapply|"
    r"nrapply|snrapply|rewrite|erewrite|setoid_rewrite|unfold|fold|induction|destruct|"
    r"case|elim|specialize|generalize|pose|epose|assert|enough|change|constructor|"
    r"econstructor|transitivity|etransitivity|symmetry|apply_with|eauto|auto|"
    r"typeclasses|by|exact_no_check|now|under|congr|move|rewrite_strat)\b")
_KW = {"in", "at", "as", "with", "using", "by", "into", "eqn", "if", "then", "else",
       "forall", "fun", "let", "match", "end", "return", "Type", "Prop", "Set",
       "left", "right", "goal", "star", "all", "auto", "simpl", "trivial"}
# ★ `by apply foo` 처럼 결합자 뒤에 tactic 이 또 오면 그 tactic 이름을 "쓰인 이름"
#   으로 잘못 셌다(실측: HoTT 에서 `apply×559`). tactic 어휘 자체를 뺀다.
_KW |= set(_HEAD.pattern.split("(", 1)[1].split(")")[0].split("|"))
_KW |= {"try", "repeat", "first", "solve", "progress", "abstract", "once", "idtac",
        "reflexivity", "assumption", "discriminate", "inversion", "subst", "split",
        "intros", "intro", "exists", "lia", "lra", "nia", "ring", "field", "omega",
        "cbn", "cbv", "hnf", "red", "compute", "easy", "done", "contradiction"}


def names_in(step: str):
    """tactic 한 줄에서 **참조로 보이는** 이름들."""
    out = []
    s = re.sub(r"\(\*.*?\*\)", " ", step or "", flags=re.S)
    for m in _HEAD.finditer(s):
        tail = s[m.end():]
        tail = re.split(r"[;.]\s|\bin\b", tail, 1)[0]
        for w in re.findall(r"(?<![\w'.])([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)", tail):
            b = w.split(".")[-1]
            if len(b) >= 3 and b not in _KW:
                out.append(b)
    return out


def main():
    files = sorted(os.listdir(D))
    idx = collections.defaultdict(collections.Counter)
    fidx = collections.defaultdict(lambda: collections.defaultdict(set))
    t0 = time.time()
    nsteps = 0
    for i, fn in enumerate(files):
        try:
            o = json.load(open(os.path.join(D, fn)))
        except Exception:
            continue
        fc = o.get("file_context") or []
        proj = None
        if fc:
            try:
                proj = json.loads(fc[0])["repository"].rstrip("/").split("/")[-1]
            except Exception:
                m = re.search(r"/repos/([^/\"]+)", str(fc[0]))
                proj = m.group(1) if m else None
        if not proj:
            continue
        c = idx[proj]
        fc_ = fidx[proj]
        for pr in o.get("proofs") or []:
            for st in pr.get("steps") or []:
                txt = ((st.get("step") or {}).get("text")) or ""
                nsteps += 1
                for n in names_in(txt):
                    c[n] += 1
                    fc_[n].add(fn)
        if (i + 1) % 1500 == 0:
            print(f"   … {i+1}/{len(files)} ({time.time()-t0:.0f}s) "
                  f"프로젝트 {len(idx)} · 스텝 {nsteps:,}", flush=True)
    out = {p: {n: [k, len(fidx[p][n])] for n, k in c.items()}
           for p, c in idx.items() if c}
    json.dump(out, open(OUT, "w"))
    print(f"■ {OUT}  {os.path.getsize(OUT)/1e6:.1f} MB")
    print(f"   프로젝트 {len(out):,} · 스텝 {nsteps:,} · "
          f"이름 {sum(len(v) for v in out.values()):,}")
    for p in ("HoTT-Coq-HoTT", "AbsInt-CompCert", "coq-community-corn"):
        v = out.get(p, {})
        if v:
            top = sorted(v.items(), key=lambda x: -x[1][0])[:5]
            print(f"   {p:22s} 이름 {len(v):6,}  상위 "
                  f"{[f'{k}×{n[0]}/{n[1]}f' for k, n in top]}")
    for probe, p in (("isequiv_adjointify", "HoTT-Coq-HoTT"), ("cancelL", "HoTT-Coq-HoTT"),
                     ("inv_pp", "HoTT-Coq-HoTT"), ("cs_bin_op_strext", "coq-community-corn"),
                     ("merely", "HoTT-Coq-HoTT")):
        v = out.get(p, {}).get(probe, [0, 0])
        print(f"   {probe:20s} {v[0]:4d}회 · 파일 {v[1]}개")


if __name__ == "__main__":
    main()
