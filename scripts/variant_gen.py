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
SHARD = None
if "--shard" in sys.argv:
    _a, _b = sys.argv[sys.argv.index("--shard") + 1].split("/"); SHARD = (int(_a), int(_b))
    OUT = OUT + f".s{SHARD[0]}"
DONE = OUT + ".done3"   # 규칙표 v3 — 전 정리 재방문  # (규칙표 v2: constructor 계열 추가 → 새 사이드카) 처리 완료 정리 (proj\tthm\tthmi) — 이어쓰기(resume)용, 전부기각 정리도 기록
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


#: v2 회차에서 이미 전 정리에 생성·채택 완료된 규칙 — 재생성 금지 (사용자 2026-09-02; 보관 sft_variants_v2rules.jsonl 와 병합)
OLD_RULES = {"ap→eapply", "eapply→ap", "rw→erw", "rw→rw<-", "rw<-→rw",
             "ctor→ector", "ector→ctor", "split→ctor", "left→ctor1", "right→ctor2",
             "applyC→ctor", "applyC→ector"}


def variants_of(step, hyps=()):
    """스텝 텍스트 → [(rule, 변형텍스트)]. 원문 구조(; 이후, in 절)는 유지. v3: 새 규칙만 낸다."""
    t = step
    cv = ctor_variants(t) + misc_variants(t, hyps) + at_variants(t)
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
    out = [c for c in out if c[0] not in OLD_RULES]
    assert all(v != step for _, v in out), "변형이 원문과 동일"
    return out



# ═══ 규칙표 v3 (2026-09-02 사용자 지시: "한번 하는김에 제대로") ═══════════════════
#  구문 8종 + rewrite … at n + apply …/eapply … 의 with/exact 명시화(Show Proof 프로브).
#  채택 판정은 전부 기존과 동일: 그 스텝을 갈아끼우고 남은 proof 를 Qed 까지 재실행.

_TAIL_AUTO = re.compile(r"(;\s*)auto(\s*\.\s*)$")
_REFL = re.compile(r"^(\s*)reflexivity(\s*)([.;].*)$", re.S)
_NOW = re.compile(r"^(\s*)now\s+(.+?)\s*\.\s*$", re.S)
_ASSUM = re.compile(r"^(\s*)assumption\s*\.\s*$")
_DCASE = re.compile(r"^(\s*)(destruct|case|induction|elim)\s+([A-Za-z_][\w']*)\s*([.;].*)$", re.S)
_EXISTS = re.compile(r"^(\s*)exists\s+([^;.]+?)\s*([.;].*)$", re.S)
_INTROS = re.compile(r"^(\s*)intros((?:\s+[A-Za-z_][\w']*)+)\s*\.\s*$")
_EXACT1 = re.compile(r"^(\s*)exact\s+([A-Za-z_][\w'.]*)\s*([.;].*)$", re.S)
_APPLY1 = re.compile(r"^(\s*)apply\s+([A-Za-z_][\w'.]*)\s*([.;].*)$", re.S)
_RW_AT = re.compile(r"^(\s*)((?:now\s+|try\s+)?e?rewrite)\s+(<-\s*)?([A-Za-z_][\w'.]*)"
                    r"(\s+in\s+[A-Za-z_][\w']*)?\s*(?=[;.])")


def misc_variants(step, hyps=()):
    """구문 8종. hyps = 그 지점 STATE 의 가설 이름들 (assumption→exact H 용)."""
    t = step; out = []
    m = _EXACT1.match(t)
    if m: out.append(("exact→apply", f"{m.group(1)}apply {m.group(2)}{m.group(3)}"))
    m = _APPLY1.match(t)
    if m: out.append(("apply→exact", f"{m.group(1)}exact {m.group(2)}{m.group(3)}"))
    m = _TAIL_AUTO.search(t)
    if m: out.append(("auto→eauto", _TAIL_AUTO.sub(lambda mm: mm.group(1) + "eauto" + mm.group(2), t)))
    m = _REFL.match(t)
    if m: out.append(("refl→exact", f"{m.group(1)}exact eq_refl{m.group(2)}{m.group(3)}"))
    m = _NOW.match(t)
    if m: out.append(("now→easy", f"{m.group(1)}{m.group(2)}; easy."))
    m = _ASSUM.match(t)
    if m:
        for h in list(hyps)[-3:][::-1]:
            out.append(("assum→exact", f"{m.group(1)}exact {h}."))
    m = _DCASE.match(t)
    if m:
        swap = {"destruct": "case", "case": "destruct", "induction": "elim", "elim": "induction"}[m.group(2)]
        out.append((f"{m.group(2)}→{swap}", f"{m.group(1)}{swap} {m.group(3)}{m.group(4)}"))
    m = _EXISTS.match(t)
    if m: out.append(("exists→eexists", f"{m.group(1)}eexists{m.group(3)}"))
    m = _INTROS.match(t)
    if m:
        names = m.group(2).split()
        if 2 <= len(names) <= 5:
            out.append(("intros→chain", m.group(1) + " ".join(f"intro {n};" for n in names).rstrip(";") + "."))
    return out


def at_variants(step):
    """rewrite/erewrite … at 1|2 — 출현 지정 (in 절은 두 어순 다 시도, 문법 틀린 쪽은 Qed 가 거름)."""
    m = _RW_AT.match(step)
    if not m: return []
    pre = step[:m.end(4)]; inc = m.group(5) or ""; rest = step[m.end(5) if m.group(5) else m.end(4):]
    out = []
    for n in ("1", "2"):
        if inc:
            out.append((f"rw→at{n}", f"{pre}{inc} at {n}{rest}"))
            out.append((f"rw→at{n}b", f"{pre} at {n}{inc}{rest}"))
        else:
            out.append((f"rw→at{n}", f"{pre} at {n}{rest}"))
    return out


# ── with/exact 명시화 프로브 — 정리당 1회 재생하며 대상 스텝 뒤에서 Show Proof·Check ──
_WP_T = re.compile(r"^(\s*)(e?apply)\s+([A-Za-z_][\w'.]*)\s*(?:in\s+([A-Za-z_][\w']*)\s*)?(?=[;.])")
_HOLE = re.compile(r"^\?[\w']+$")


def _paren_tree(txt):
    """괄호 트리 파싱: 문자열 → 중첩 리스트(원자=str)."""
    toks = re.findall(r"[()]|[^\s()]+", txt)
    stack = [[]]
    for tk in toks:
        if tk == "(": stack.append([])
        elif tk == ")":
            if len(stack) > 1: c = stack.pop(); stack[-1].append(c)
        else: stack[-1].append(tk)
    return stack[0]


def _render(node):
    return node if isinstance(node, str) else "(" + " ".join(_render(x) for x in node) + ")"


def extract_args(term_txt, base):
    """Show Proof 항에서 base 가 머리인 최대 적용 노드의 인자 목록."""
    best = None
    def walk(node):
        nonlocal best
        if isinstance(node, str): return
        if node and isinstance(node[0], str) and (node[0] == base or node[0].endswith("." + base)):
            if best is None or len(node) > len(best): best = node
        for x in node: walk(x)
    tree = _paren_tree(term_txt)
    walk(tree)
    # 최상위(괄호 없는) 적용도 본다: [.. base a1 a2 ..]
    for i, x in enumerate(tree):
        if isinstance(x, str) and (x == base or x.endswith("." + base)):
            cand = [x] + tree[i + 1:]
            if best is None or len(cand) > len(best): best = cand
            break
    if not best: return []
    return [_render(a) for a in best[1:]]


def binder_names(type_txt):
    """`forall (a b : A) (c : B), …` / `forall a b : A, …` → 선행 명시적 바인더 이름들(순서)."""
    t = " ".join(type_txt.split())
    names = []
    while True:
        m = re.match(r"\s*forall\s+(.*)$", t)
        if not m: break
        rest = m.group(1); i = 0; depth = 0
        # 콤마(depth 0)까지가 바인더 구간
        for i, ch in enumerate(rest):
            if ch == "(": depth += 1
            elif ch == ")": depth -= 1
            elif ch == "," and depth == 0: break
        seg, t = rest[:i], rest[i + 1:]
        for g in re.findall(r"\(([^():]+):[^()]*\)|([A-Za-z_][\w']*(?:\s+[A-Za-z_][\w']*)*)\s*:", seg + " "):
            blob = (g[0] or g[1]).strip()
            for nm in blob.split():
                if re.fullmatch(r"[A-Za-z_][\w']*", nm): names.append(nm)
        if not seg.strip(): break
    return names


def with_candidates_for(term_txt, check_txt, head_tac, name, in_h, tail):
    """프로브 산출(항, Check 타입) → with/exact 변형 후보."""
    base = name.split(".")[-1]
    args = extract_args(term_txt, base)
    if not args: return []
    m = re.search(re.escape(base) + r"\s*\n?\s*:\s*(.*)", check_txt, re.S)
    binders = binder_names(m.group(1)) if m else []
    pairs = [(b, a) for b, a in zip(binders, args)
             if not _HOLE.match(a) and a != "_" and len(a) <= 35 and b != a]
    out = []
    inc = f" in {in_h}" if in_h else ""
    if pairs:
        b, a = pairs[-1]                                  # 뒤쪽 바인더가 eapply 가 남기는 자리에 가깝다
        out.append(("ap→with", f"apply {name} with ({b} := {a}){inc}{tail}"))
        if len(pairs) >= 2:
            (b1, a1), (b2, a2) = pairs[-2], pairs[-1]
            out.append(("ap→with2", f"apply {name} with ({b1} := {a1}) ({b2} := {a2}){inc}{tail}"))
    if args and not in_h and all(not _HOLE.match(a) and a != "_" for a in args) \
            and sum(map(len, args)) <= 90:                      # 완전적용 = 추출된 **전체** 인자 (바인더 수로 자르면 증명 인자가 빠진다)
        out.append(("ap→exact(", f"exact ({name} " + " ".join(args) + f"){tail}"))
    return out


def with_probe(pdir, path, head, stmt, steps):
    """정리 1회 재생 + 대상 스텝 뒤 Show Proof/Check → {k: [(rule, variant)]}."""
    targets = {}
    for k, st in enumerate(steps):
        m = _WP_T.match((st or "").lstrip("\n"))
        if m and "with" not in (st or ""): targets[k] = m
    if not targets or len(steps) > 60: return {}
    body = ["Require Import Applic.", head, "Abort All.", rename_stmt(stmt, "__wp"),
            "Set Printing Depth 100000."]
    for k, st in enumerate(steps):
        body.append(st)
        if k in targets:
            body += [f'idtac "@@WP{k}".', "Show Proof.", f"Check {targets[k].group(3)}.", f'idtac "@@WE{k}".']
    env = dict(os.environ)
    env["OCAMLPATH"] = os.path.join(R.PLUG, "findlib") + ":" + env.get("OCAMLPATH", "")
    with tempfile.NamedTemporaryFile("w", suffix=".v", dir=os.path.dirname(path), delete=False) as f:
        f.write("\n".join(body) + "\n"); tmp = f.name
    try:
        out = R._coqtop(["coqtop", "-q"] + R.proj_args(pdir), stdin=open(tmp), env=env, timeout=900)
    except Exception:
        return {}
    finally:
        for e in (".v", ".vo", ".vok", ".vos", ".glob"):
            try: os.unlink(os.path.splitext(tmp)[0] + e)
            except OSError: pass
    o = out if isinstance(out, str) else out[0]
    res = {}
    for k, m in targets.items():
        mm = re.search(rf"@@WP{k}\n(.*?)@@WE{k}", o, re.S)
        if not mm: continue
        seg = mm.group(1)
        base = m.group(3).split(".")[-1]
        cm = re.search(rf"(?m)^{re.escape(base)}\s*$|(?m)^{re.escape(base)}\b", seg)
        term_txt, check_txt = (seg[:cm.start()], seg[cm.start():]) if cm else (seg, "")
        st = steps[k].lstrip("\n"); tail = st[_WP_T.match(st).end():] or "."
        cands = with_candidates_for(term_txt, check_txt, m.group(2), m.group(3), m.group(4), tail)
        if cands: res[k] = cands
    return res


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
    _fidx = -1
    for proj, pdir in REPOS.items():
        for dpf in TP.dp_files(proj):
            _fidx += 1
            if SHARD and _fidx % SHARD[1] != SHARD[0]: continue
            if done_thm >= N_THM: break
            try: dp = DatasetFile.load(Path(dpf), sdb)
            except Exception: continue
            rel = TP.rel_of(dp, proj)
            if not rel: continue
            _ps = TP.PATH_SKIP.get(proj)
            if _ps and _ps.search("/" + rel): continue   # 병리 경로 (Core-Erlang Tests/ 등)
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
                try:
                    wp = with_probe(pdir, path, head, tt, steps)
                except Exception:
                    wp = {}
                pts = []
                for k, st in enumerate(steps):
                    hyps_k = []
                    try:
                        for hstr in (proof.steps[k].goals[0].hyps or []):
                            hyps_k += [x.strip() for x in str(hstr).split(":")[0].split(",") if x.strip()]
                    except Exception: pass
                    vs = wp.get(k, []) + variants_of(st or "", hyps_k)
                    if vs: pts.append((k, vs[:4]))
                if not pts: continue
                pts = pts[:6]
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
