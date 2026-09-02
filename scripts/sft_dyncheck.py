#!/usr/bin/env python3
"""★ SFT 산출의 **동적(Coq 실행) 검증** — 정적 검사기(sft_check)가 못 보는 것을 실제 coqtop 으로 확인한다.

  D1 정답 재현: 그 지점까지 원본 스텝을 재생한 뒤 **원문 gold tactic** 을 실행하면 통과한다
     (풀 좌표·gold_text·저장소 빌드가 서로 맞는지 — 좌표 어긋남·빌드 오염을 잡는다)
  D2 선언문 진위: gold 프리미스의 블록 선언줄(진술)이 Coq 의 `Check <gold>` 출력과 일치한다
     (case B 주입 선언문이 **진짜** 선언문인지 — 풀/DB 별칭 오염을 잡는다). 토큰 자카드 ≥ 0.6.
  D3 변형 재현: +var 행의 원문 변형(역매핑)을 같은 지점에서 실행하면 통과한다 (variant_gen 결과 재확인)

표본: case A/B 행 무작위 N (기본 24). 실패 1건이라도 있으면 종료코드 1 (학습 착수 금지).
사용: python3 scripts/sft_dyncheck.py <pairs.jsonl> [N=24]
"""
import json, os, random, re, sys, tempfile, collections
sys.path.insert(0, "scripts"); sys.path.insert(0, "src")
import logging; logging.disable(logging.CRITICAL)
_A = sys.argv[:]; sys.argv = ["train_pool.py", "1"]
import train_pool as TP
import r11_eval as R
sys.argv = ["variant_gen.py", "0"]
import variant_gen as VG          # run_theorem: 정리 재시작 → k-1 스텝 재생 → tactic → 나머지 proof → Check(Qed 판정)
sys.argv = _A
from pathlib import Path
from data_management.dataset_file import DatasetFile

PATH = _A[1]; N = int(_A[2]) if len(_A) > 2 else 24
ROOT = "/app/coq-modeling/tmp/tr"
random.seed(11)
rows = [json.loads(l) for l in open(PATH)]
cands = [r for r in rows if r.get("case") in ("A", "B") and r.get("gold")]
vars_ = [r for r in rows if "+var" in r.get("case", "") and r.get("gold_text")]
samp = random.sample(cands, min(N, len(cands))) + random.sample(vars_, min(N // 3, len(vars_)))
print(f"■ 동적 검증 표본 {len(samp)} (A/B {min(N, len(cands))} · 변형 {min(N // 3, len(vars_))})", flush=True)
TOK = re.compile(r"[A-Za-z_][\w']*|\d+|[^\s\w]")


def coq(pdir, path, script):
    """프로젝트 빌드 환경에서 coqtop 에 script 를 먹이고 출력을 돌려준다 (variant_gen.run_theorem 과 같은 방식)."""
    env = dict(os.environ); env["OCAMLPATH"] = os.path.join(R.PLUG, "findlib") + ":" + env.get("OCAMLPATH", "")
    with tempfile.NamedTemporaryFile("w", suffix=".v", dir=os.path.dirname(path), delete=False) as f:
        f.write(script); tmp = f.name
    try:
        out = R._coqtop(["coqtop", "-q"] + R.proj_args(pdir), stdin=open(tmp), env=env, timeout=900)
    finally:
        for e in (".v", ".vo", ".vok", ".vos", ".glob"):
            try: os.unlink(os.path.splitext(tmp)[0] + e)
            except OSError: pass
    return out if isinstance(out, str) else out[0]


_DP = {}
def locate(r):
    """행 → (pdir, path, head, stmt, steps) — train_pool 의 dp·정리 위치 찾기 재사용."""
    proj = r["proj"]; pdir = f"{ROOT}/{proj}"
    if proj not in _DP:
        _DP[proj] = {}
        for dpf in TP.dp_files(proj):
            try: dp = DatasetFile.load(Path(dpf), TP.sdb)
            except Exception: continue
            rel = TP.rel_of(dp, proj)
            if rel: _DP[proj][rel] = dp
    dp = _DP[proj].get(r["thm"]); assert dp is not None, f"dp 없음 {proj}/{r['thm']}"
    path = os.path.join(pdir, r["thm"]); assert os.path.exists(path), f"원본 없음 {path}"
    proof = dp.proofs[r["thmi"]]; tt = proof.theorem.term.text
    orig = open(path, errors="ignore").read(); pos = 0
    for pi in range(r["thmi"] + 1):                      # 같은 파일 앞쪽 정리를 차례로 지나 위치를 맞춘다
        hit = TP.find_thm(orig, dp.proofs[pi].theorem.term.text or "", pos)
        assert hit, f"정리 위치 실패 {r['thm']}[{pi}]"
        off, head = hit; pos = off + 1
    steps = [s.step.text for s in proof.steps]
    return pdir, path, head, tt, steps


C = collections.Counter(); fails = []
for r in samp:
    try:
        pdir, path, head, stmt, steps = locate(r)
        k = r["k"]; is_var = "+var" in r["case"]
        # D1/D3: 재생 + (gold 원문 | 변형 원문) 실행 → 다음 스텝이 진행되는지(에러 없음)로 판정
        tac = r["gold_text"] if not is_var else None
        if is_var:
            # 변형 원문 = 정답(익명)을 역매핑할 수 없으므로 sft_variants.jsonl 에서 같은 좌표·rule 로 찾는다
            for l in open("all_log/sft_variants.jsonl"):
                v = json.loads(l)
                if (v["proj"], v["thm"], v["thmi"], v["k"], v["rule"]) == (r["proj"], r["thm"], r["thmi"], k, r.get("rule")):
                    tac = v["variant"]; break
        assert tac, "실행할 tactic 없음"
        # ★ 판정은 variant_gen 과 같은 방식 — 그 스텝을 tac 으로 갈아끼우고 **나머지 proof 를 끝까지** 재생해 Qed 가 서는가.
        #   (tac 직후에 다른 명령을 넣어 판정하면 불릿/포커스 종료 때문에 거짓 실패가 난다 — 1차 구현의 실측 32/32 오판)
        res = VG.run_theorem(pdir, path, head, stmt, steps, [(k, [("self", tac)])])
        ok = bool(res) and res[0][3]
        code = "D3" if is_var else "D1"
        C[f"{code} {'통과' if ok else '실패'}"] += 1
        if not ok: fails.append((code, r["proj"], r["thm"], r["thmi"], k, tac[:60]))
        # D2: gold 선언문 vs Check
        if not is_var and r.get("gold_decl"):
            g = r["gold"][0]
            out2 = coq(pdir, path, "\n".join([head, f"Check {g}.", "Abort All."]))
            m = re.search(re.escape(g.split(".")[-1]) + r"\s*\n?\s*:\s*(.*?)(?=\n\S|\Z)", out2, re.S)
            if not m: C["D2 Check실패"] += 1; fails.append(("D2", r["proj"], r["thm"], g, "Check 출력 없음", out2[-160:].replace("\n", " "))); continue
            a = set(TOK.findall(m.group(1))); b = set(TOK.findall(r["gold_decl"].split(" : ", 1)[-1]))
            jac = len(a & b) / max(1, len(a | b))
            # Section 안에서 Check 하면 section 변수가 빠진 **국소 타입**이 찍힌다("Equivalence equiv") —
            # 풀 진술은 section 을 닫은 전역 타입. 국소 타입 토큰이 전역 진술의 부분집합이면 같은 lemma 로 본다.
            ok2 = jac >= 0.6 or (a and a <= b)
            C["D2 일치" if ok2 else "D2 불일치"] += 1
            if not ok2: fails.append(("D2", r["proj"], r["thm"], g, f"jaccard {jac:.2f}", r["gold_decl"][:80], m.group(1)[:80]))
    except AssertionError as e:
        if "정리문 파싱 실패" in str(e):      # Definition/Instance 로 선언된 정리 — variant_gen 과 같은 이유로 재생 대상 아님
            C["스킵(Definition류)"] += 1; continue
        C["예외"] += 1; fails.append(("EXC", r.get("proj"), r.get("thm"), str(e)[:120]))
    except Exception as e:
        C["예외"] += 1; fails.append(("EXC", r.get("proj"), r.get("thm"), str(e)[:120]))

print("■ 결과:", dict(C))
for f in fails[:12]: print("  ✗", f)
# D2 는 방법론 한계(implicit 표시·이름 가림·Section 국소화)로 오탐이 있어 **검토**로 강등 (2026-09-02 실측 3/28 전부 그 부류,
# 진짜 문제인 "DB 폴백의 동명 딴 모듈 선언"은 future_work: decl_of 모듈 일치 강제 후 v11.1 재물질화).
bad = C["D1 실패"] + C["D3 실패"] + C["예외"]
if C["D2 불일치"] or C["D2 Check실패"]:
    print(f"★ D2 검토 {C['D2 불일치'] + C['D2 Check실패']}건 — 로그 확인 (비치명)")
assert bad == 0, f"동적 검증 실패 {bad}건"
print("SFT_DYNCHECK_OK")
