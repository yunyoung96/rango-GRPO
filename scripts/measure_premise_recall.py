#!/usr/bin/env python3
"""검색 recall 측정 — gold tactic 이 쓰는 lemma 가 프롬프트의 [PREMISES] 안에 있나?

왜: 학습 loss 가 원본 rango 보다 +0.21 높고 하강도 느린데, 원인 후보가
    (a) on-the-fly 검색 품질 (b) 증강 프롬프트 두 가지다.
    gold lemma 가 애초 검색되지 않으면 그 예제는 **아무리 학습해도 loss 가 안 내려간다**
    → recall 이 낮으면 (a) 가 주범이라는 강한 신호.

측정: gold tactic(next_steps[0])에서 참조하는 lemma 이름을 뽑아, example.premises 의
      선언 이름들과 대조한다. lemma 를 참조하지 않는 tactic(intros/simpl 등)은 분모에서 제외.

사용: PYTHONPATH=src python3 scripts/measure_premise_recall.py [N]
"""
import json
import logging
import os
import re
import sys

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.insert(0, "src")
logging.disable(logging.CRITICAL)

import yaml  # noqa: E402

# lemma 를 인자로 받는 tactic 들
_TAC = re.compile(r"\b(?:apply|rewrite|erewrite|exact|refine|eapply|destruct|induction|"
                  r"specialize|pose proof|generalize|unfold|case|elim|inversion|"
                  r"rewrite <-|apply <-)\s+([^;.,\)]+)")
_ID = re.compile(r"[A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*")
_DECL = re.compile(r"^\s*(?:Lemma|Theorem|Definition|Corollary|Remark|Fact|Fixpoint|"
                   r"Inductive|Instance|Axiom|Proposition|Property)\s+([A-Za-z_][\w']*)")
_KW = {"in", "with", "as", "at", "by", "using", "eqn", "auto", "simpl", "intros", "intro",
       "H", "IH", "goal", "type", "Type", "Prop", "left", "right", "all", "try"}


def gold_lemmas(tactic: str) -> set:
    """gold tactic 이 참조하는 lemma 후보 이름(로컬 가설·키워드 제외)."""
    out = set()
    for m in _TAC.finditer(tactic or ""):
        for t in _ID.findall(m.group(1)):
            s = t.split(".")[-1]
            if s in _KW or len(s) < 3 or re.fullmatch(r"H\d*|IH\w*", s):
                continue
            out.add(s)
    return out


def premise_names(premises) -> set:
    out = set()
    for p in premises or []:
        m = _DECL.match(p.strip())
        if m:
            out.add(m.group(1).split(".")[-1])
    return out


def report(name, pairs):
    """pairs: [(gold_tactic, premises)]"""
    n_ref = hit = 0
    n_prem = []
    for tac, prem in pairs:
        n_prem.append(len(prem or []))
        g = gold_lemmas(tac)
        if not g:
            continue                      # lemma 참조 없는 tactic → 분모 제외
        n_ref += 1
        if g & premise_names(prem):
            hit += 1
    import statistics
    print(f"\n■ {name}")
    print(f"   예제 {len(pairs)}개, premise 개수 중앙 {statistics.median(n_prem):.0f}")
    print(f"   lemma 참조 tactic: {n_ref}개")
    print(f"   그중 gold lemma 가 premises 안에 있음: {hit} = **{hit/max(n_ref,1)*100:.1f}%**")
    return hit / max(n_ref, 1)


def main():
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    # (1) 우리 학습 파이프라인(on-the-fly 검색)
    from tactic_gen.tactic_data import TacticDataConf, LmDataset
    from data_management.splits import Split
    conf = yaml.safe_load(open("all_log/ft_rango_augmented_conf.yaml"))
    ds = LmDataset.from_conf(TacticDataConf.from_yaml(conf["tactic_data"]), Split.TRAIN)
    pairs = []
    for i in range(N):
        try:
            ex = ds.raw_example(i)
        except Exception:
            continue
        pairs.append(((ex.next_steps or [""])[0], ex.premises))
    r1 = report(f"우리 학습 파이프라인 (on-the-fly, {N}개 샘플)", pairs)

    # (2) 롤아웃 데이터(과거 서버가 검색해 둔 premise) — CompCert
    pairs2 = []
    for line in open("data/grpo_rollouts/goldsft_bs2.jsonl"):
        g = json.loads(line)
        for a in g["attempts"]:
            if a["reward"] < 1.0:
                continue
            for st in a["steps"]:
                ex = st.get("example")
                if ex:
                    pairs2.append((st.get("tactic", ""), ex.get("premises")))
        if len(pairs2) >= N:
            break
    r2 = report(f"롤아웃 데이터 goldsft_bs2 (CompCert, {len(pairs2)}개)", pairs2)

    print(f"\n판정: 우리 {r1*100:.1f}% vs 롤아웃 {r2*100:.1f}%")
    print("  · 우리가 크게 낮으면 → 학습 파이프라인 검색이 gold lemma 를 못 찾고 있다(= loss 격차의 주범 후보)")
    print("  · 비슷하면 → 검색은 정상. loss 격차는 다른 요인(증강/데이터 분포)")


if __name__ == "__main__":
    main()
