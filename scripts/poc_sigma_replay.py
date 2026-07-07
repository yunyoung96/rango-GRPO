#!/usr/bin/env python3
"""
PoC: §5-A "copy-and-rename replay" 검증기.

가설: rango가 실패한 정리(target)의 증명은, retrieval로 찾은 형제 정리(neighbor)의
증명에 치환 σ 를 적용하면 그대로 컴파일된다.

이 스크립트는 각 케이스에 대해 neighbor 증명을 여러 방식으로 변환한 뒤,
그 변환된 증명을 target 정리의 자리에 끼워 넣고 실제 coqc 로 컴파일해
PASS/FAIL 을 보고한다. "σ replay 가 컴파일되는가?"에 대한 실증.

변형(variant) 사다리:
  V0 verbatim      : neighbor 증명을 글자 그대로 복사 (아무 rename 없음)
  V1 naive-rename  : 토큰 단위 무차별 치환 (Int.->Int64. 등)
  V2 stmt-sigma    : 두 정리의 '문장'만 비교해 유도한 σ (증명 전용 심볼은 못 잡음)
  V3 sigma+repair  : σ + 증명 전용 심볼/문맥 보정 (= 방법 A + 국소수리 B)
"""
import subprocess, sys, re, os, tempfile, time

COMPCERT = os.path.join(os.path.dirname(__file__), "..", "CoqStoq", "test-repos", "compcert")
COMPCERT = os.path.abspath(COMPCERT)
FLAGS = ["-R","lib","compcert.lib","-R","common","compcert.common","-R","x86_64","compcert.x86_64",
         "-R","x86","compcert.x86","-R","backend","compcert.backend","-R","cfrontend","compcert.cfrontend",
         "-R","driver","compcert.driver","-R","export","compcert.export","-R","cparser","compcert.cparser",
         "-R","flocq","Flocq","-R","MenhirLib","MenhirLib"]

def read(path):
    with open(os.path.join(COMPCERT, path), encoding="utf-8") as f:
        return f.read().split("\n")

def extract_body(lines, name):
    """(Theorem|Lemma) name ... Proof. <BODY> Qed.  →  (thm_start, proof_idx, qed_idx, body_str)"""
    start = next(i for i,l in enumerate(lines) if re.match(rf"\s*(Theorem|Lemma)\s+{re.escape(name)}\b", l))
    proof = next(i for i in range(start, len(lines)) if lines[i].strip().startswith("Proof"))
    qed   = next(i for i in range(proof, len(lines)) if lines[i].strip().rstrip() in ("Qed.","Defined."))
    body  = "\n".join(lines[proof+1:qed])
    return start, proof, qed, body

def compile_variant(srcfile, target_name, new_body, cut_suffix=""):
    """target_name 의 증명 본문을 new_body 로 교체한 파일(타깃 Qed까지 컷 + cut_suffix)을 coqc."""
    lines = read(srcfile)
    _, proof, qed, _ = extract_body(lines, target_name)
    head = lines[:proof+1]                       # ... Proof.
    new  = head + [new_body] + [lines[qed]]       # + <body> + Qed.
    if cut_suffix:
        new += [cut_suffix]
    text = "\n".join(new) + "\n"
    d = os.path.dirname(os.path.join(COMPCERT, srcfile))
    tmp = os.path.join(d, f"_poc_{target_name}.v")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    try:
        t0 = time.time()
        r = subprocess.run(["coqc"]+FLAGS+[os.path.relpath(tmp, COMPCERT)],
                           cwd=COMPCERT, capture_output=True, text=True, timeout=180)
        dt = time.time()-t0
        ok = r.returncode == 0
        err = ""
        if not ok:
            m = re.search(r"(Error.*?)(?:\n\n|\Z)", r.stdout+r.stderr, re.S)
            err = (m.group(1) if m else (r.stdout+r.stderr)).strip().replace("\n"," ")[:300]
        return ok, dt, err
    finally:
        for ext in ("",".vo",".vok",".vos",".glob"):
            p = os.path.join(d, f"_poc_{target_name}"+(ext if ext else ".v"))
            if os.path.exists(p): os.remove(p)
        for junk in os.listdir(d):
            if junk.startswith(f".{('_poc_'+target_name)}"):
                os.remove(os.path.join(d, junk))

# ---------------------------------------------------------------- σ transforms
def apply_rules(body, rules):
    for a,b in rules:
        body = body.replace(a,b)
    return body

def run_case(title, srcfile, target, neighbor, variants, cut_suffix=""):
    print("="*78)
    print(f"CASE: {title}")
    print(f"  target={target}   neighbor={neighbor}   file={srcfile}")
    nb_body = extract_body(read(srcfile), neighbor)[3]
    print("-"*78)
    for vname, desc, transform in variants:
        cand = transform(nb_body)
        ok, dt, err = compile_variant(srcfile, target, cand, cut_suffix)
        tag = "PASS ✅" if ok else "FAIL ❌"
        print(f"  [{vname}] {desc:<42} {tag}  ({dt:.1f}s)")
        if not ok:
            print(f"        └ {err}")
    print()

# ===================================================================== CASES
def case_divlu():
    # neighbor: divu_mul_shift(32bit)  →  target: divlu_mul_shift(64bit)
    V0 = ("V0","verbatim (형제 증명 그대로 복사)", lambda b: b)
    def v1(b):  # naive: 무차별 토큰 치환
        return apply_rules(b, [("Int.","Int64."),("32","64")])
    def v2(b):  # 문장 anti-unify 로만 유도한 σ (증명 전용 심볼은 못 잡음)
        return apply_rules(b, [
            ("divu_mul_params_sound","divlu_mul_params_sound"),
            ("Int.divu","Int64.divu"), ("Int.mulhu","Int64.mulhu"),
            ("Int.shru","Int64.shru'"),           # 문장의 shru↦shru' — 그러나 증명은 shru_div_two_p 사용
        ])
    def v3(b):  # σ + 증명전용/문맥 보정 (방법 A + 국소수리)
        return apply_rules(b, [
            ("divu_mul_params_sound","divlu_mul_params_sound"),
            ("Int.shru_div_two_p","int64_shru'_div_two_p"),   # 증명 전용 심볼 (naming stem)
            ("unfold Int.divu, Int.mulhu","unfold Int64.divu, Int64.mulhu"),
            ("by apply Int.unsigned_range","by apply Int64.unsigned_range"),  # rewrite C by ...
            ("Int.unsigned_range x","Int64.unsigned_range x"),  # x:int64 관련 (generalize)
            ("(Int.unsigned_repr m)","(Int64.unsigned_repr m)"),
            ("rewrite Int.unsigned_repr. f_equal. ring","rewrite Int64.unsigned_repr. f_equal. ring"),
            ("Int.unsigned x","Int64.unsigned x"),
            ("Int.modulus","Int64.modulus"),
            ("unfold Int.max_unsigned; lia","unfold Int64.max_unsigned; lia"),
            ("assert (32 < Int64.max_unsigned)","assert (64 < Int.max_unsigned)"),  # p-bound 은 Int 유지
            ("assert (32 < Int.max_unsigned)","assert (64 < Int.max_unsigned)"),
        ])
    run_case("idx=538  divlu_mul_shift  (64bit ← 32bit divu_mul_shift)",
             "backend/SelectDivproof.v", "divlu_mul_shift", "divu_mul_shift",
             [V0, ("V1","naive 무차별 rename (Int.→Int64., 32→64)",v1),
              ("V2","statement-σ 만 (증명전용심볼 미보정)",v2),
              ("V3","σ + 증명심볼/문맥 보정 (A+B)",v3)])

def case_shll():
    # neighbor: eval_shrlu  →  target: eval_shll   (Section CMCONSTR 안 → End 로 닫기)
    V0 = ("V0","verbatim (형제 증명 그대로 복사)", lambda b: b)
    v1 = ("V1","stem rename (shrlu→shll) 한 방", lambda b: b.replace("shrlu","shll"))
    run_case("idx=806  eval_shll  (← eval_shrlu)",
             "x86/SelectLongproof.v", "eval_shll", "eval_shrlu",
             [V0, v1], cut_suffix="\nEnd CMCONSTR.")

if __name__ == "__main__":
    case_shll()
    case_divlu()
