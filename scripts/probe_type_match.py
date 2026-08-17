#!/usr/bin/env python3
"""타입 추론 능력 프로브 — **match 식**으로 자연스럽게 묻는다(재설계판).

## 앞선 설계가 왜 무효였나

`destruct x as [|||]` 표기로 물었는데, 모델이 원하는 건 `[x | y | z]`(바인더 이름) 였다.
실측: `destruct x as [` 다음 top 은 'x'(-1.2) 'M'(-2.2) 'h'(-2.7) 이고 우리가 비교한
'|'(-4.7) ']'(-13.7) 은 **둘 다 후보가 아니었다**. off-distribution 표기로 물으면
"타입을 아는가"가 아니라 "낯선 표기를 얼마나 싫어하는가"를 재게 된다.

그 밖에 잡은 결함: 평균 NLL 은 긴 후보 편애, 총 NLL 은 짧은 후보 편애,
공백 토큰 경계(" IH" vs "IH"), 유명 타입만 고른 표본 편향(6개 100% → 120개 47.5%).

## 재설계 원칙

  1. **자연스러운 문맥**: match 식은 Coq 코드에 가장 흔하다(= in-distribution)
  2. **길이 통제**: 단일 토큰 결정, 또는 같은 토큰 수 후보
  3. **프레임 검증**: 우리 후보가 모델 top-k 안에 있는지 확인. 없으면 그 예제는 **제외**
     (프레임이 off-distribution 이면 무엇을 재든 무의미하므로 비율을 보고한다)

## 프로브

  M1 생성자 소속 : 정의에 있는 생성자 vs 없는 가짜 — 정의를 읽었나
  M2 남은 분기   : `| A => 0 | B => 1 | <?>` 에서 남은 생성자 vs 이미 쓴 것/가짜
  M3 소진 판단   : 모든 생성자를 다 쓴 뒤 `end` vs `|` — **세었나**
  M4 인자 개수   : `| C <?>` 에서 arity 만큼 바인더가 오나

사용: CUDA_VISIBLE_DEVICES=0 python3 scripts/probe_type_match.py --model <hf> --n 60
"""
import argparse
import json
import logging
import os
import random
import re
import statistics
import sys
from math import comb, exp, lgamma, log

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.insert(0, "src")
logging.disable(logging.CRITICAL)

import torch  # noqa: E402
from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: E402

_SYL = ["Zor", "Quv", "Mek", "Pil", "Nax", "Tib", "Wug", "Vex", "Jom", "Kiv",
        "Fen", "Rud", "Lop", "Hab", "Syl", "Cor"]


class Scorer:
    def __init__(self, name):
        print(f"모델: {name}")
        self.tok = AutoTokenizer.from_pretrained(name)
        # ★ 왼쪽 절단 필수: 프레임(...[TACTIC]\napply )이 프롬프트 **끝**에 있으므로
        #   기본값(right)으로 자르면 조건 자체가 날아가 측정이 무의미해진다.
        self.tok.truncation_side = "left"
        self.dev = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = AutoModelForCausalLM.from_pretrained(
            name, torch_dtype=torch.bfloat16 if self.dev == "cuda" else torch.float32
        ).to(self.dev).eval()

    n_forward = 0

    def choose(self, prompt, good, bad, topk=30):
        Scorer.n_forward += 1
        """같은 프리픽스에서 두 후보의 **첫 토큰** 확률 비교 + 프레임 유효성 판정.

        반환 (정답선호?, Δlogp, 프레임유효?).
        프레임유효 = 두 후보 중 **적어도 하나**가 모델 top-k 안에 있음.
        (둘 다 밖이면 모델이 전혀 다른 걸 쓰려는 상황 = 이 질문 자체가 성립 안 함)
        """
        if prompt.endswith(" "):
            prompt, good, bad = prompt[:-1], " " + good.lstrip(), " " + bad.lstrip()
        ids = self.tok(prompt, return_tensors="pt", truncation=True,
                       max_length=3000)["input_ids"].to(self.dev)
        with torch.no_grad():
            lp = torch.log_softmax(self.model(ids).logits[0, -1].float(), dim=-1)
        ga = self.tok(good, add_special_tokens=False)["input_ids"]
        ba = self.tok(bad, add_special_tokens=False)["input_ids"]
        if not ga or not ba or ga[0] == ba[0]:
            return None, 0.0, False
        top = set(torch.topk(lp, topk).indices.tolist())
        valid = (ga[0] in top) or (ba[0] in top)
        g, b = float(lp[ga[0]]), float(lp[ba[0]])
        return g > b, g - b, valid


def fresh(rnd, used):
    while True:
        n = rnd.choice(_SYL) + rnd.choice(_SYL).lower() + str(rnd.randrange(100))
        if n not in used:
            used.add(n)
            return n


def make_type(rnd, n_ctor, max_arity=2):
    used = set()
    tname = fresh(rnd, used)
    ctors = []
    for _ in range(n_ctor):
        cn = fresh(rnd, used)
        a = rnd.randrange(0, max_arity + 1)
        ctors.append((cn, a))
    body = "\n".join(
        f"  | {c} : {tname}" if a == 0 else f"  | {c} : " + " -> ".join(["nat"] * a + [tname])
        for c, a in ctors)
    return tname, ctors, f"Inductive {tname} : Type :=\n{body}."


def binom_p(k, n, p0=0.5):
    """양측 정확 이항검정.

    ★ comb(n,i) 를 float 와 곱하면 n≳1030 에서 OverflowError 가 난다
      (comb(1592,796)≈10^476 > float 최대 1.8e308). 표본을 200→796 으로 늘리자
      M3 가 1592 시도가 되어 실제로 터졌다(1.3b 가 M1·M2 만 찍고 죽음).
      → **로그공간**으로 계산한다.
    """
    if n == 0:
        return 1.0
    lp0, lq0 = log(p0), log(1 - p0)
    lnf = lgamma(n + 1)
    thr = abs(k - n * p0)
    tot = 0.0
    for i in range(n + 1):
        if abs(i - n * p0) >= thr:
            tot += exp(lnf - lgamma(i + 1) - lgamma(n - i + 1)
                       + i * lp0 + (n - i) * lq0)
    return min(1.0, tot)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--verify", action="store_true",
                    help="런타임 불변식 검사(수정이 실제로 먹었는지 동적 확인)")
    args = ap.parse_args()
    rnd = random.Random(23)
    sc = Scorer(args.model)

    V = {"frames": 0, "boundary_saves": 0, "forwards": 0}
    R = {k: [0, 0, 0, []] for k in
         ("M1", "M2", "M3", "M4", "M5", "M6", "X1", "X2", "X3")}  # 정답, 유효, 총, Δ

    def rec(k, res):
        ok, d, valid = res
        R[k][2] += 1
        if ok is None or not valid:
            return
        R[k][1] += 1
        R[k][0] += int(ok)
        R[k][3].append(d)

    for _ in range(args.n):
        nc = rnd.randrange(3, 6)
        tname, ctors, defn = make_type(rnd, nc)
        names = [c for c, _ in ctors]
        used = set(names) | {tname}
        fake = fresh(rnd, used)
        head = f"{defn}\n\nDefinition f (x : {tname}) : nat :=\n  match x with\n"

        # ── M1 생성자 소속: 첫 분기에 실재 생성자 vs 가짜 ──
        rec("M1", sc.choose(head + "  | ", names[0], fake))

        # ── M2 남은 분기: 앞 두 개를 쓴 뒤 남은 것 vs 이미 쓴 것 ──
        body = "".join(f"  | {names[i]} => {i}\n" for i in range(nc - 1))
        rec("M2", sc.choose(head + body + "  | ", names[-1], names[0]))

        # ── M3 소진 판단: 전부 썼으면 end, 아직이면 | ──
        full = "".join(f"  | {names[i]} => {i}\n" for i in range(nc))
        rec("M3", sc.choose(head + full + "  ", "end", "|"))
        partial = "".join(f"  | {names[i]} => {i}\n" for i in range(nc - 1))
        rec("M3", sc.choose(head + partial + "  ", "|", "end"))

        # ── M4 인자 개수: arity>0 인 생성자 뒤에 바인더가 오나 ──
        tgt = next(((c, a) for c, a in ctors if a > 0), None)
        if tgt:
            c, a = tgt
            rec("M4", sc.choose(head + f"  | {c}", " a", " =>"))
        z = next(((c, a) for c, a in ctors if a == 0), None)
        if z:
            rec("M4", sc.choose(head + f"  | {z[0]}", " =>", " a"))

    # ── M5/M6: rango 의 **실제 병목** — 인자 자리에 실재 이름을 쓰나 ──
    #   rand200 실측: INVALID 7,981건 중 '이름 못 찾음' 3,613(45.3%),
    #   그중 78%가 **코퍼스에 아예 없는 지어낸 이름**(apply ltu_shl 등). 최대 단일 원인이다.
    #   → [PREMISES] 에 실재 lemma 를 주고, apply 인자로 그걸 고르나 가짜를 고르나 본다.
    import json as _json
    from tactic_gen.lm_example import LmExample as _LmEx
    _LN0 = re.compile(r"(?:Lemma|Theorem|Definition|Corollary|Remark|Fact)\s+([A-Za-z_][\w']*)")
    _ID0 = re.compile(r"\b([A-Za-z_][\w']*)\b")

    def _usable(e):
        """gold tactic 이 [PREMISES] 안 lemma 를 실제로 쓴 step 만 — 조합 프로브의 전제."""
        prem = list(getattr(e, "premises", None) or [])[:12]
        if not prem:
            return False
        pn = [m.group(1) for p in prem for m in [_LN0.match(p.strip())] if m]
        return bool(pn) and any(n in pn for n in _ID0.findall(e.next_steps[0]))

    # gold 하나(goldsft_bs2)만 쓰면 premise lemma 를 실제 쓴 step 이 **226개뿐**이라
    # X1/M5 같은 병목 프로브의 표본이 말라죽는다. → 성공(reward=1.0, Coq 가 QED 확인)한
    # 롤아웃 파일들을 함께 긁어 풀을 넓힌다. 같은 정리를 8회 롤아웃하므로 **중복 제거**가 필수.
    SOURCES = [
        "data/grpo_rollouts/goldsft_bs2.jsonl",
        "data/grpo_rollouts/ei-r1.jsonl",
        "data/grpo_rollouts/ei-r2.jsonl",
        "data/grpo_rollouts/rango-grpo-cascade-s0.jsonl",
        "data/grpo_rollouts/rango-grpo-cascade-s0r2.jsonl",
        "data/grpo_rollouts/revcurr.jsonl",
        "data/grpo_rollouts/backward.jsonl",
        "data/grpo_rollouts/bigscale2.jsonl",
    ]
    ex_steps, seen_key = [], set()
    for src in SOURCES:
        if len(ex_steps) >= args.n or not os.path.exists(src):
            continue
        for line in open(src):
            if len(ex_steps) >= args.n:
                break
            try:
                g = _json.loads(line)
            except Exception:
                continue
            for a in g.get("attempts", []):
                if a.get("reward", 0) < 1.0:
                    continue
                for st in a.get("steps", []):
                    if not (st.get("example") and st.get("tactic")):
                        continue
                    e = _LmEx.from_json(st["example"])
                    e.next_steps = [st["tactic"]]
                    k = (e.file_name, (e.proof_state or "")[:120], st["tactic"])
                    if k in seen_key:
                        continue
                    if _usable(e):
                        seen_key.add(k)
                        ex_steps.append(e)
                        if len(ex_steps) >= args.n:
                            break
                if len(ex_steps) >= args.n:
                    break
    print(f"   (조합·환각 프로브 표본: {len(ex_steps)}개, 중복제거 후)")
    _LN = re.compile(r"(?:Lemma|Theorem|Definition|Corollary|Remark|Fact)\s+([A-Za-z_][\w']*)")
    _ID = re.compile(r"\b([A-Za-z_][\w']*)\b")
    for e in ex_steps:
        prem = list(getattr(e, "premises", None) or [])[:12]
        if not prem:
            continue
        pnames = [m.group(1) for p in prem for m in [_LN.match(p.strip())] if m]
        if not pnames:
            continue
        pblock = "\n".join(prem)
        state = e.proof_state or ""
        gold = e.next_steps[0].strip()

        # ── M5/M6: 환각 — **gold 가 실제로 쓴 자리**에서 물어야 프레임이 성립한다 ──
        #   (프롬프트에 'apply ' 를 억지로 붙이면 모델이 쓰려던 수와 어긋나 표본이 전부 무효가 된다)
        used = next((n for n in _ID.findall(gold) if n in pnames), None)
        if used is None:
            continue
        m_pos = re.search(r"\b" + re.escape(used) + r"\b", gold)
        if m_pos is None:
            continue
        head5 = (f"[PREMISES]\n{pblock}\n[STATE]\n{state}\n[TACTIC]\n"
                 + gold[: m_pos.start()])
        # 모델이 실제로 지어낸 환각(예: apply ltu_shl)과 같은 꼴 — 단 **첫 토큰이 달라야** 한다.
        gtok = sc.tok(used, add_special_tokens=False)["input_ids"]
        fakes = ["ltu_" + used, "sub_" + used, "aux_" + used, "Zq_" + used]
        fake = next((f for f in fakes if f not in pnames and
                     sc.tok(f, add_special_tokens=False)["input_ids"][:1] != gtok[:1]),
                    None)
        if fake is None:
            continue
        if args.verify:
            V["frames"] += 1
            # 단어경계 검색이 부분문자열 검색과 다른 위치를 주는 경우 = 예전 버그가 터졌을 지점
            if gold.index(used) != m_pos.start():
                V["boundary_saves"] += 1
            # 프레임 끝이 정확히 gold 의 lemma 직전까지여야 한다
            assert head5.endswith(gold[: m_pos.start()]), "프레임 접미 불일치"
            # good 은 premise 목록에 있고, fake 는 없어야 한다
            assert used in pnames and fake not in pnames, "good/fake 집합 위반"
            assert (sc.tok(fake, add_special_tokens=False)["input_ids"][:1]
                    != sc.tok(used, add_special_tokens=False)["input_ids"][:1]), "첫토큰 동일"
        rec("M5", sc.choose(head5, used, fake))
        rec("M6", sc.choose(head5, used, "Zqfake_thm"))

        # ── X1~X3: **조합** — COMPOSITION_IS_THE_WALL.md 의 실측 축을 그대로 프로브로 ──
        #   X1 lemma 선택 : apply 실패의 90% 가 '잘못된 lemma 선택'. [PREMISES] 안에서
        #                   gold 가 쓴 lemma 를 다른 premise 와 구별하나 (인자오류는 0% 라 논외)
        #   X2 인자 배치  : 재료(가설)는 79% 이미 있음. lemma 에 **어느 가설**을 넣나
        #   X3 oracle 활용: gold lemma 를 힌트로 쥐여줘도 8→10%(+2pp)뿐이었다.
        #                   힌트를 주면 그 lemma 선호가 실제로 올라가나 (paired)
        others = [n for n in pnames if n != used]
        if others:
            ok_a, d_a, v_a = sc.choose(head5, used, others[0])
            rec("X1", (ok_a, d_a, v_a))          # 같은 계산을 재사용(중복 forward 제거)
            hint = f"[HINT] The next tactic should use the lemma {used}.\n"
            ok_b, d_b, v_b = sc.choose(hint + head5, used, others[0])
            if v_a and v_b:
                R["X3"][2] += 1; R["X3"][1] += 1
                R["X3"][0] += int(d_b > d_a); R["X3"][3].append(d_b - d_a)
        # X2: gold 가 `... used a b c` 꼴이면 첫 인자를, 상태의 다른 가설과 비교
        tail = gold[m_pos.end():]
        m_arg = re.match(r"\s+([A-Za-z_][\w']*)", tail)
        if m_arg:
            arg = m_arg.group(1)
            hyps = [h.group(1) for h in
                    re.finditer(r"^\s*([A-Za-z_][\w']*)\s*:", state, re.M)]
            distract = next((h for h in hyps if h != arg), None)
            if distract:
                rec("X2", sc.choose(head5 + used, " " + arg, " " + distract))

    print(f"\n■ 타입 추론 프로브 (match 식)  {args.model.split('/')[-1]}")
    print("   프레임유효 = 후보가 모델 top-30 안 (낮으면 질문 자체가 off-distribution)\n")
    names_k = {"M1": "생성자 소속(정의 읽기)", "M2": "남은 분기 추적",
               "M3": "소진 판단(세기)", "M4": "생성자 인자수",
               "M5": "★실재 premise vs 환각", "M6": "★premise 안 이름 vs 가짜",
               "X1": "◆lemma 선택(오선택90%)", "X2": "◆인자 배치(재료79%)",
               "X3": "◆oracle 힌트 활용(+2pp)"}
    for k in ("M1", "M2", "M3", "M4", "M5", "M6", "X1", "X2", "X3"):
        w, v, t, ds = R[k]
        if v == 0:
            print(f"   · {names_k[k]:22s} 유효표본 0/{t} — 프레임 무효")
            continue
        r = w / v * 100
        p = binom_p(w, v)
        # Bonferroni: 9프로브 × 6모델 = 54검정 → α=0.05/54≈0.00093.
        # 보정 전만 통과하면 △(약한 증거)로 표시해 과대해석을 막는다.
        A_RAW, A_BONF = 0.05, 0.05 / 54
        if p >= A_RAW:
            mark = "·"
        elif p >= A_BONF:
            mark = "△" if r > 50 else "▽"
        else:
            mark = "✅" if r > 50 else "❌"
        print(f"   {mark} {names_k[k]:22s} {w:>3}/{v:<3} = {r:>5.1f}%  p={p:.3f}  "
              f"Δlogp {statistics.mean(ds):+.2f}   (프레임유효 {v}/{t} = {v/t*100:.0f}%)")
    if args.verify:
        _verify_report(V, R, sc)


def _verify_report(V, R, sc):
    print("\n■ 런타임 불변식 검증")
    print(f"   프레임 검사 통과            {V['frames']}건 (assert 위반 0 — 위반 시 즉시 예외)")
    print(f"   단어경계로 위치가 교정된 건  {V['boundary_saves']}건 "
          f"(예전 부분문자열 검색이 틀렸을 지점)")
    print(f"   X1 유효표본={R['X1'][1]}  X3 유효표본={R['X3'][1]}  "
          f"→ {'일치 ✓ (같은 forward 재사용)' if R['X1'][1] == R['X3'][1] else '불일치 ✗'}")
    print(f"   총 forward 호출             {Scorer.n_forward}회")
    # Bonferroni 판정 로직 직접 확인
    for p_, exp in ((0.030, "△"), (0.0005, "✅"), (0.20, "·")):
        A_RAW, A_BONF = 0.05, 0.05 / 54
        m = "·" if p_ >= A_RAW else ("△" if p_ >= A_BONF else "✅")
        print(f"   p={p_:<7} → {m}  ({'기대 ' + exp} {'✓' if m == exp else '✗'})")
    # 왼쪽 절단 확인
    long_p = ("x " * 4000) + "[TACTIC]\napply "
    ids = sc.tok(long_p, return_tensors="pt", truncation=True, max_length=3000)["input_ids"]
    tail = sc.tok.decode(ids[0][-6:])
    print(f"   4000단어 프롬프트 절단 후 끝 = {tail!r}  "
          f"{'✓ 프레임 보존' if 'apply' in tail else '✗ 프레임 소실'}")


if __name__ == "__main__":
    main()
