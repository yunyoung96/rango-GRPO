#!/usr/bin/env python3
"""★ [학습 전 ②] gold tactic 변형 사전 대량 생성 — Qed 직접 검증으로 채택.

answer.txt [3] 구현. 정리당 coqtop 1세션:
  head 1회 로드 → 변형마다 { Abort All. → 정리를 __v_i 로 개명 재선언 →
  k 전 스텝 재생 → 변형 → k 후 원본 스텝(Qed 포함) → Check __v_i. }
  성공 판정 = stdout 에 "__v_i :" 타입 출력 (Qed 가 닫혀야만 존재).

v1 규칙표 (순수 텍스트 변형 — evar 인스턴스 필요한 with/exact 는 v2):
  apply N → eapply N          eapply N → apply N
  rewrite N → erewrite N      rewrite N → rewrite <- N
  rewrite <- N → rewrite N
  (… in H 꼴은 머리·화살표만 바꾸고 in 절 유지)

사용: python3 scripts/variant_gen.py <표본정리수> [저장소들]
산출: all_log/sft_variants.jsonl {proj,thm,thmi,k,orig,variant,rule,qed}
"""
import collections, json, os, re, sys, tempfile
os.environ.setdefault("HF_HUB_OFFLINE", "1"); os.environ["CUDA_VISIBLE_DEVICES"] = ""
sys.path.insert(0, "src"); sys.path.insert(0, "scripts"); sys.path.insert(0, "CoqStoq")
import logging; logging.disable(logging.CRITICAL)
from pathlib import Path
_A = sys.argv[:]
sys.argv = ["r11_eval.py", "VAL", "0", "", ""]
import r11_eval as R
sys.argv = _A
from data_management.sentence_db import SentenceDB
from data_management.dataset_file import DatasetFile

N_THM = int(sys.argv[1]) if len(sys.argv) > 1 else 6
_SCR = "/app/coq-modeling/tmp/tr"   # 영속 위치
REPOS = dict(kv.split("=", 1) for kv in
             (sys.argv[2] if len(sys.argv) > 2 else
              f"coq-community-coq-art={_SCR}/coq-community-coq-art").split(","))
OUT = "all_log/sft_variants.jsonl"
DONE = OUT + ".done2"  # (규칙표 v2: constructor 계열 추가 → 새 사이드카) 처리 완료 정리 (proj\tthm\tthmi) — 이어쓰기(resume)용, 전부기각 정리도 기록
sdb = SentenceDB.load(Path("raw-data/coq-dataset/sentences.db"))

DECL = re.compile(r"^(\s*(?:Local\s+|Global\s+)?(?:Theorem|Lemma|Fact|Remark|"
                  r"Corollary|Proposition)\s+)([A-Za-z_][\w']*)")
HEAD_T = re.compile(r"^(\s*)(apply|eapply|rewrite|erewrite)\b(\s*<-)?\s*")


# ★ constructor 계열 (사용자 제안 2026-09-01): 같은 상태에서 동치인 표기를 서로 바꿔 출력 다양성을 학습.
#   채택은 여전히 Qed 재실행이 판정한다 (split→constructor 는 단일 생성자 타입에서만 성립하는 식).
CTOR_T = re.compile(r"^(\s*)(constructor|econstructor|split|left|right)\b(\s*\d+)?(?=\s*[;.]|\s+(?:with|$))")
try:
    _IND = json.load(open("data/ind_constructors_clean.json"))
    CTORS = set()
    for _t, _v in _IND.items():
        _cs = _v.get("constructors") if isinstance(_v, dict) else _v
        if isinstance(_cs, dict): _cs = list(_cs.keys())
        for _c in (_cs or []): CTORS.add(_c if isinstance(_c, str) else str(_c[0]) if isinstance(_c, (list, tuple)) else str(_c))
except Exception:
    CTORS = set()
# stdlib 의 흔한 생성자 (인덱스는 프로젝트 정의만 담는다)
CTORS |= {"le_n", "le_S", "eq_refl", "refl_equal", "or_introl", "or_intror", "conj", "ex_intro", "I", "in_eq", "in_cons",
          "Forall_nil", "Forall_cons", "Exists_cons_hd", "Exists_cons_tl", "inl", "inr", "Some", "None", "pair", "tt",
          "O", "S", "nil", "cons", "true", "false", "Lt", "Gt", "Eq", "Z0", "Zpos", "Zneg", "xH", "xO", "xI",
          "ex_intro2", "exist", "existT", "left", "right", "inleft", "inright", "sig_intro", "Permutation_nil",
          "Permutation_skip", "Permutation_swap", "Permutation_trans", "Acc_intro", "le_pred", "Rle_refl"}
assert len(CTORS) > 1000, f"생성자 인덱스 로드 실패 {len(CTORS)}"
_APPLY_ONE = re.compile(r"^(\s*)(apply|eapply)\s+([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)\s*(?=[;.]|$)")   # 마침표는 이름에 안 붙인다


def ctor_variants(step):
    t = step; lead = t[:len(t) - len(t.lstrip("\n"))]; body = t.lstrip("\n"); out = []
    m = CTOR_T.match(body)
    if m:
        h = m.group(2); num = (m.group(3) or "").strip()
        def rep(new): return lead + body[:m.start(2)] + new + body[m.end(3) if m.group(3) else m.end(2):]
        if h == "constructor" and not num: out.append(("ctor→ector", rep("econstructor")))
        if h == "econstructor" and not num: out.append(("ector→ctor", rep("constructor")))
        if h == "split": out.append(("split→ctor", rep("constructor")))
        if h == "left": out.append(("left→ctor1", rep("constructor 1")))
        if h == "right": out.append(("right→ctor2", rep("constructor 2")))
        return out
    m = _APPLY_ONE.match(body)          # `apply C.` 에서 C 가 생성자면 constructor/econstructor 로
    if m and m.group(3).split(".")[-1] in CTORS:
        rest = body[m.end(3):]
        out.append(("applyC→ctor", lead + body[:m.start(2)] + "constructor" + rest))
        out.append(("applyC→ector", lead + body[:m.start(2)] + "econstructor" + rest))
    return out


def variants_of(step):
    """스텝 텍스트 → [(rule, 변형텍스트)]. 원문 구조(; 이후, in 절)는 유지."""
    t = step
    cv = ctor_variants(t)
    m = HEAD_T.match(t.lstrip("\n"))
    if not m: return cv
    lead_ws = t[:len(t) - len(t.lstrip("\n"))]
    body = t.lstrip("\n")
    out = []
    def sub(new_head, arrow):
        nb = HEAD_T.sub(lambda mm: f"{mm.group(1)}{new_head}{arrow} ", body, count=1)
        return lead_ws + nb
    h, arr = m.group(2), (m.group(3) or "").strip()
    if h == "apply":    out.append(("ap→eapply", sub("eapply", "")))
    if h == "eapply":   out.append(("eapply→ap", sub("apply", "")))
    if h == "rewrite" and not arr:
        out.append(("rw→erw", sub("erewrite", "")))
        out.append(("rw→rw<-", sub("rewrite", " <-")))
    if h == "rewrite" and arr == "<-":
        out.append(("rw<-→rw", sub("rewrite", "")))
    out = out + [c for c in cv if c not in out]
    assert all(v != step for _, v in out), "변형이 원문과 동일"
    return out


def rename_stmt(stmt, newname):
    m = DECL.match(stmt.strip())
    assert m, f"정리문 파싱 실패: {stmt[:60]!r}"
    return DECL.sub(lambda mm: mm.group(1) + newname, stmt.strip(), count=1)


def run_theorem(pdir, path, head, stmt, steps, points):
    """points = [(k, [(rule, variant)])]. 반환 [(k, rule, variant, qed?)]."""
    body = ["Require Import Applic.", head]
    tags = []
    vid = 0
    for k, vs in points:
        for rule, var in vs:
            nm = f"__v_{vid}"; vid += 1
            body += ["Abort All.", rename_stmt(stmt, nm),
                     "".join(steps[:k]), var, "".join(steps[k + 1:]),
                     f"Check {nm}."]
            tags.append((nm, k, rule, var))
    env = dict(os.environ)
    env["OCAMLPATH"] = os.path.join(R.PLUG, "findlib") + ":" + env.get("OCAMLPATH", "")
    with tempfile.NamedTemporaryFile("w", suffix=".v", dir=os.path.dirname(path),
                                     delete=False) as f:
        f.write("\n".join(body) + "\n"); tmp = f.name
    try:
        out = R._coqtop(["coqtop", "-q"] + R.proj_args(pdir), stdin=open(tmp),
                        env=env, timeout=1800)
    finally:
        for e in (".v", ".vo", ".vok", ".vos", ".glob"):
            try: os.unlink(os.path.splitext(tmp)[0] + e)
            except OSError: pass
    res = []
    for nm, k, rule, var in tags:
        ok = bool(re.search(rf"^{nm}\s*$|^{nm}\b\s*:", out, re.M)) or (nm + "\n     :" in out)
        res.append((k, rule, var, ok))
    return res


if __name__ == "__main__":
    import train_pool as TP     # dp 열거·rel 매핑 재사용
    nw = 0; stat = collections.Counter()
    # ── 이어쓰기: 이미 처리한 정리는 건너뛴다 (출력은 append). 채택 행 + done 사이드카 합집합.
    done_keys = set()
    # ★ 이어쓰기 기준은 **사이드카(DONE)만** — 출력(OUT)의 채택 행으로 건너뛰면 규칙표가 바뀌었을 때(v2: constructor 계열)
    #   옛 채택분이 있는 정리가 재방문되지 않는다. 중복 변형은 물질화 로더가 제거한다.
    if os.path.exists(DONE):
        for l in open(DONE):
            a_ = l.rstrip("\n").split("\t")
            if len(a_) == 3: done_keys.add((a_[0], a_[1], int(a_[2])))
    fo = open(OUT, "a"); fd = open(DONE, "a")
    done_thm = 0; skipped = 0
    print(f"■ 이어쓰기: 기처리 정리 {len(done_keys)}", flush=True)
    for proj, pdir in REPOS.items():
        for dpf in TP.dp_files(proj):
            if done_thm >= N_THM: break
            try: dp = DatasetFile.load(Path(dpf), sdb)
            except Exception: continue
            rel = TP.rel_of(dp, proj)
            if not rel: continue
            path = os.path.join(pdir, rel)
            if not (os.path.exists(path)
                    and os.path.exists(os.path.splitext(path)[0] + ".vo")): continue
            orig = open(path, errors="ignore").read(); pos = 0
            for pi, proof in enumerate(dp.proofs):
                if done_thm >= N_THM: break
                tt = proof.theorem.term.text or ""
                if not tt.strip() or not DECL.match(tt.strip()): continue
                hit = TP.find_thm(orig, tt, pos)
                if hit is None: continue
                off, head = hit; pos = off + 1
                if (proj, rel, pi) in done_keys:
                    done_thm += 1; skipped += 1; continue
                steps = [s.step.text for s in proof.steps]
                pts = []
                for k, st in enumerate(steps):
                    vs = variants_of(st or "")
                    if vs: pts.append((k, vs[:3]))
                if not pts: continue
                pts = pts[:4]
                try:
                    res = run_theorem(pdir, path, head, tt, steps, pts)
                except Exception as e:
                    stat["세션실패"] += 1; continue
                done_thm += 1
                fd.write(f"{proj}\t{rel}\t{pi}\n"); fd.flush()
                for k, rule, var, ok in res:
                    stat["qed" if ok else "fail"] += 1
                    if ok:
                        nw += 1
                        fo.write(json.dumps({"proj": proj, "thm": rel, "thmi": pi,
                                             "k": k, "orig": steps[k].strip(),
                                             "variant": var.strip(), "rule": rule,
                                             "qed": True}, ensure_ascii=False) + "\n")
                fo.flush()
                print(f"  {rel.split('/')[-1]}[{pi}]: "
                      + " ".join(f"{r}={'✓' if ok else '✗'}" for _, r, _, ok in res),
                      flush=True)
    fo.close(); fd.close()
    print(f"\n■ 변형 생성: 정리 {done_thm} (건너뜀 {skipped}) · 채택 {nw} · {dict(stat)}")
    assert done_thm == skipped or stat.get("qed", 0) + stat.get("fail", 0) > 0
    print("VARGEN_DONE")
