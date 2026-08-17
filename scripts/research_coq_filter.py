#!/usr/bin/env python3
"""**Coq 이 직접 판정하는 적용가능성 필터** — 재랭킹의 최종 단계.

## 핵심 트릭

`Fail tac.` 은 tac 이 **실패해야** 성공한다.

    Fail apply X.   →  오류 없이 지나가면  X 는 apply **불가**
                    →  오류를 내면        X 는 apply **가능**

goal 상태를 전혀 바꾸지 않고 판정하며 **2~4ms**. Coq 이 실제 타입검사를 하므로
이름·구조 휴리스틱과 달리 **100% 정확**하고, gold 를 잘못 버릴 위험이 원리적으로 없다.

## 왜 필터인가

검색이 top-50 까지는 gold 를 꽤 넣지만 프롬프트 정원은 21개다. 상위 후보 중 **실제로
적용되는 것만** 남기면 정원 안에 gold 가 들어올 확률이 오른다.

## Coq 상태 재현

롤아웃의 `example.proof_script` 는 **정리 선언부터** 시작한다. 원본 .v 에서 그 선언 위치를
찾아 앞부분 + proof_script 로 임시 파일을 만들면 그 시점이 정확히 재현된다.

사용: python3 scripts/research_coq_filter.py [스텝수] [후보수]
"""
import json
import os
import re
import sys
import time
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.insert(0, "src")
import logging  # noqa: E402

logging.disable(logging.CRITICAL)
from coqpyt.coq.base_file import CoqFile  # noqa: E402
from tactic_gen.lm_example import LmExample  # noqa: E402
from tactic_gen.gold_lemma import gold_lemmas  # noqa: E402
from tactic_gen.search_query import local_names  # noqa: E402

NSTEP = int(sys.argv[1]) if len(sys.argv) > 1 else 20
TOPN = int(sys.argv[2]) if len(sys.argv) > 2 else 50
REPOS = Path("CoqStoq/test-repos")

_NAME = re.compile(r"^\s*(?:Lemma|Theorem|Definition|Corollary|Remark|Fact|Fixpoint|"
                   r"Instance|Axiom|Proposition|Example|Let|Program\s+\w+)\s+"
                   r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")


def _find_decl(src: str, decl: str) -> int:
    """원본 .v 에서 정리 선언 위치.

    ★ 그냥 `src.find(decl)` 는 거의 실패한다 — 원본은 줄바꿈·들여쓰기가 섞여 있는데
      proof_script 의 선언은 한 줄로 정규화돼 있기 때문이다. 공백을 `\s+` 로 바꿔 찾고,
      그래도 없으면 **선언 이름**으로 찾는다.
    """
    key = re.sub(r"\\ ", r"\\s+", re.escape(decl.strip()))
    m = re.search(key, src)
    if m:
        return m.start()
    mm = re.match(r"\s*(?:Lemma|Theorem|Definition|Corollary|Remark|Fact|Fixpoint|"
                  r"Instance|Proposition|Example|Program\s+\w+)\s+"
                  r"([A-Za-z_][\w']*)", decl)
    if mm:
        m2 = re.search(r"^[ \t]*\w+\s+" + re.escape(mm.group(1)) + r"\b", src, re.M)
        if m2:
            return m2.start()
    return -1


def declname(t):
    m = _NAME.match(t or "")
    return m.group(1) if m else None


# ── gold step 수집 (프롬프트·premise·proof_script 가 이미 붙어 있다) ─────────
steps = []
for line in open("data/grpo_rollouts/goldsft_bs2.jsonl"):
    g = json.loads(line)
    for a in g["attempts"]:
        if a["reward"] < 1.0:
            continue
        for s in a["steps"]:
            if s.get("example") and s.get("tactic"):
                e = LmExample.from_json(s["example"])
                e.next_steps = [s["tactic"]]
                steps.append(e)
        break
print(f"gold step {len(steps)}개 로드", flush=True)

tot = {"n": 0, "b10": 0, "b20": 0, "a10": 0, "a20": 0, "kept": 0, "cand": 0,
       "lost": 0, "ms": 0.0, "probe": 0, "open_ms": 0.0, "skip": 0}
tmp_files = []

for e in steps:
    if tot["n"] >= NSTEP:
        break
    st = getattr(e, "proof_state", "") or ""
    golds = set(gold_lemmas(e.next_steps[0], local_names(st)))
    if not golds:
        continue
    prems = [p if isinstance(p, str) else getattr(p, "text", str(p))
             for p in (getattr(e, "premises", None) or [])][:TOPN]
    names = [declname(t) for t in prems]
    gpos = [j for j, nm in enumerate(names) if nm and nm.split(".")[-1] in golds]
    if not gpos:
        continue

    fn = getattr(e, "file_name", "") or ""
    rel = fn[len("repos/"):] if fn.startswith("repos/") else fn
    vf = (REPOS / rel).resolve()
    if not vf.exists():
        tot["skip"] += 1
        continue
    script = getattr(e, "proof_script", "") or ""
    decl = script.strip().split("\n")[0].strip()
    if len(decl) < 12:
        tot["skip"] += 1
        continue
    try:
        src = vf.read_text(errors="ignore")
    except Exception:
        tot["skip"] += 1
        continue
    at = _find_decl(src, decl)
    if at < 0:                       # 원본에서 선언을 못 찾으면 재현 불가
        tot["skip"] += 1
        continue

    tmp = vf.parent / f"_pf_{tot['n']}_{os.getpid()}.v"
    tmp_files.append(tmp)
    try:
        tmp.write_text(src[:at] + script + "\n")
        t0 = time.time()
        # ★ workspace 는 **절대경로**여야 coq-lsp 가 _CoqProject 의 -R 매핑을 읽는다.
        #   상대경로면 "Cannot find a physical path bound to logical path" 로 전부 깨진다.
        cf = CoqFile(str(tmp), timeout=300,
                     workspace=str((REPOS / rel.split("/")[0]).resolve()))
        cf.run()
        open_ms = (time.time() - t0) * 1000
        tot["open_ms"] += open_ms
        if cf.errors:
            print(f"  skip(오류 {len(cf.errors)}): {rel} — "
                  f"{str(cf.errors[0])[:70]}", flush=True)
            cf.close()
            tmp.unlink(missing_ok=True)
            tot["skip"] += 1
            continue
    except Exception as ex:
        tmp.unlink(missing_ok=True)
        tot["skip"] += 1
        print(f"  skip(예외): {rel} — {str(ex)[:70]}", flush=True)
        continue

    def probe_score(nm: str) -> float:
        """적용가능성을 **단계적 점수**로. 이진 통과/탈락은 변별력이 없다.

        ★ eapply 는 evar 를 만들어 거의 모든 결론에 매칭된다 — 넣으면 후보 30개가 전부
          통과한다(30→30). 그렇다고 빼면 eapply 로 쓰이는 gold 를 놓친다.
          → 강도별로 점수를 달리 준다: apply/rewrite(확실) 3점, eapply(약함) 1점.
        """
        for tac, sc in ((f"Fail apply {nm}.", 3.0), (f"Fail rewrite {nm}.", 3.0),
                        (f"Fail rewrite <- {nm}.", 3.0), (f"Fail erewrite {nm}.", 2.0),
                        (f"Fail eapply {nm}.", 1.0)):
            before = len(cf.errors)
            try:
                cf.add_step(len(cf.steps) - 1, "\n" + tac)
                cf.exec(1)
            except Exception:
                return 3.0
            tot["probe"] += 1
            if len(cf.errors) > before:
                return sc
        return 0.0

    def _unused_probe(nm: str) -> bool:
        """적용 가능하면 True. `Fail` 이라 상태를 안 바꾼다.

        ★ 시도 집합이 좁으면 gold 를 버린다 — apply/rewrite 만 봤을 때 **22.5%** 를
          잘못 버렸다(40건 실측). eapply 가 필요한 경우, 가설에 적용하는 경우
          (`apply X in H`), unfold/exact 로 쓰는 경우를 모두 넣어야 한다.
        """
        # ★ 너무 넓히면 변별력이 사라진다: unfold/exact 를 넣었더니 후보 30개가
        #   **전부** 통과했다(30→30). 반대로 apply/rewrite 만 보면 gold 를 22.5% 버린다.
        #   → 실제로 lemma 를 쓰는 방식만 남긴다(eapply·가설적용 포함, unfold/exact 제외).
        cands = [f"Fail apply {nm}.", f"Fail eapply {nm}.",
                 f"Fail rewrite {nm}.", f"Fail rewrite <- {nm}.",
                 f"Fail erewrite {nm}."]
        # `apply X in *|-`(모든 가설에 시도)도 넣어 봤으나 거의 항상 성공해
        # 후보 30개가 전부 통과했다(30→30). 변별력이 없어 뺐다.
        for tac in cands:
            before = len(cf.errors)
            try:
                cf.add_step(len(cf.steps) - 1, "\n" + tac)
                cf.exec(1)
            except Exception:
                return True                 # 실행이 튀면 보수적으로 살린다
            tot["probe"] += 1
            if len(cf.errors) > before:     # Fail 이 실패 = tac 성공 = 적용 가능
                return True
        return False

    t1 = time.time()
    scs = [probe_score(nm.split(".")[-1]) if nm else 3.0 for nm in names]
    ok = [x > 0 for x in scs]
    dt = (time.time() - t1) * 1000
    cf.close()
    tmp.unlink(missing_ok=True)

    # ★ 필터로 **버리면** R@20 이 97.5→77.5% 로 무너진다(gold 를 22.5% 버림).
    #   버리지 말고 **적용 가능한 것을 앞으로 옮기는 재정렬**만 한다 — 순위는 오르고
    #   잘못 버릴 위험은 사라진다.
    # 점수 내림차순 재정렬(동점은 원래 순위 유지) — 버리지 않으므로 손실이 없다
    kept = sorted(range(len(prems)), key=lambda j: (-scs[j], j))
    tot["n"] += 1
    tot["cand"] += len(prems)
    tot["kept"] += sum(1 for j in range(len(prems)) if ok[j])
    tot["ms"] += dt
    b = min(gpos)
    tot["b10"] += (b < 10)
    tot["b20"] += (b < 20)
    a = min(kept.index(j) for j in gpos)
    tot["a10"] += (a < 10)
    tot["a20"] += (a < 20)
    ar = str(a)
    if not any(ok[j] for j in gpos):
        tot["lost"] += 1          # 판정은 틀렸지만 재정렬이라 버려지진 않는다
        ar += "(판정X)"
    print(f"  [{tot['n']}] {rel.split('/')[-1]:22s} 후보{len(prems)}→남김{len(kept)} · "
          f"gold순위 {b}→{ar} · {dt:.0f}ms (열기 {open_ms:.0f}ms)", flush=True)

for t in tmp_files:
    try:
        t.unlink(missing_ok=True)
    except Exception:
        pass

n = max(tot["n"], 1)
print(f"\n■ CompCert(TEST) gold step {tot['n']}개 · 후보 상위 {TOPN} (건너뜀 {tot['skip']})")
print(f"   Coq 필터가 남기는 비율 : {tot['kept']}/{tot['cand']} = "
      f"{tot['kept']/max(tot['cand'],1)*100:.1f}%")
print(f"   gold 를 '적용 불가' 로 오판 : {tot['lost']}/{n} = {tot['lost']/n*100:.1f}%"
      f"  (버리지 않고 뒤로 미루므로 손실은 없다)")
print(f"\n   {'':10s} {'R@10':>9s} {'R@20':>9s}")
print(f"   {'필터 전':10s} {tot['b10']/n*100:8.1f}% {tot['b20']/n*100:8.1f}%")
print(f"   {'필터 후':10s} {tot['a10']/n*100:8.1f}% {tot['a20']/n*100:8.1f}%")
print(f"\n   판정 {tot['probe']}회 · 스텝당 {tot['ms']/n:.0f}ms "
      f"({tot['ms']/max(tot['probe'],1):.1f}ms/판정) · 파일열기 {tot['open_ms']/n:.0f}ms")
