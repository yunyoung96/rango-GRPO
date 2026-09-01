#!/usr/bin/env python3
"""★ [학습 전 ③] SFT 물질화 v2 — rango 포매터·콜레이터를 그대로 태우고 **[PREMISES] 자리만 5블록**으로 바꾼다.

v1(sft_build.py) 과의 차이 (design_from_requirements [7] "③물질화 v2" 항목 이행)
  · [PROOFS](BM25 유사증명) · [TYPES]/[DEFINITIONS](augment v2) · [STATE] · [SCRIPT] 는 **rango 가 만든다**
    → 추론 시점 프롬프트 빌더와 같은 코드 경로 (형식 불일치 = OOD 를 원천 차단)
  · [Others] = 기존 rango tf-idf(RETRIEVAL_MODE=tfidf) 상위 중 채널 블록에 없는 것 10개 (requirements [4])
  · 익명화 = rango normalize_names.build_mapping (stdlib 제외 · 동명 보호 · 정리이름 _G#) —
    프롬프트·정답·변형이 **한 매핑**을 지난다. 블록 줄은 "Lemma <이름> : <진술>." 꼴이라 rango 가 이름을 뽑는다.
  · case B 주입 선언문은 **실제 선언문**(풀 진술 → 없으면 sentence DB) — 없으면 그 지점은 버리고 센다.
  · seq_len 4096 (HARD_SEQ_LEN 덮어씀) · v10 gold 주입은 끈다(우리 case A/B 가 대신) · 변형 조인 ≤2 · 지점 셔플.

구현 방식: tactic_data.allocate_and_fmt 를 **이 프로세스 안에서만** 감싸, premises 인자가 우리 블록 목록(같은 객체)이면
  미리 만든 5블록 문자열을 돌려준다 → ProofPremiseCollator.collate() 가 예산·TYPES/DEFS·정규화를 전부 처리.

사용: python3 scripts/sft_build_v2.py <split> [상한]      → all_log/sft2_pairs_<split>.jsonl
"""
import collections, json, os, random, re, sys, time
from pathlib import Path
import yaml
sys.path.insert(0, "src"); sys.path.insert(0, "scripts")
import logging; logging.disable(logging.CRITICAL)

import rango_defaults as _D
HARD = 5120                                      # v2 실측(40지점): 4096 이면 7.5% 초과(최대 4,364) → 5120 (0% 초과)
_D.PROD_DEFAULTS["HARD_SEQ_LEN"] = str(HARD)
_D.PROD_DEFAULTS["RETRIEVAL_MODE"] = "tfidf"     # [Others] = 기존 rango tf-idf
_D.PROD_DEFAULTS["CUTS_PATH"] = ""               # cut 계획(hopeless 판정) 경로 차단 — 우리 지점엔 무관
_D.PROD_DEFAULTS["RERANK_PREMISES"] = "0"        # 재랭킹은 새 리스트를 만들어 우리 블록 치환(객체 동일성)을 비껴간다
import tactic_gen.v10_inject as V10
V10.ENABLED = False                              # 우리 case A/B 가 주입을 맡는다
V10.SENTENCE_DB = None   # split 확정 후 아래에서 설정
import tactic_gen.normalize_config as NC
NC.RATE = 1.0                                    # 전부 익명화 (stdlib 제외는 SKIP_STDLIB)
from tactic_gen import tactic_data as TD
from tactic_gen.lm_example import formatter_conf_from_yaml, GeneralFormatter
from tactic_gen.normalize_names import apply_mapping, apply_inverse, _PREM_DECL
import tactic_gen.normalize_names as NN
from data_management.dataset_file import DatasetFile
import sft_build as SB                            # v1 의 랭커·FORM_CH·BLK·VARIANTS·point_shuffle 재사용
from transformers import AutoTokenizer

SPLIT = SB.SPLIT; CAP = SB.CAP
# split 별 데이터 위치 — TRAIN 은 rango 데이터셋, VAL/TEST 는 CoqStoq 분할 (dp·sentence DB 가 각각 다르다)
DATA_DIR, SDB_PATH = {"train": ("raw-data/coq-dataset", "raw-data/coq-dataset/sentences.db"),
                      "val": ("raw-data/coqstoq-val", "raw-data/coqstoq-val/coqstoq-val-sentences.db"),
                      "test": ("raw-data/coqstoq-test", "raw-data/coqstoq-test/coqstoq-test-sentences.db")}[SPLIT]
assert os.path.isdir(DATA_DIR + "/data_points") and os.path.exists(SDB_PATH), (DATA_DIR, SDB_PATH)
OUT = f"all_log/sft2_pairs_{SPLIT}.jsonl"
random.seed(23)
BLK, BLOCK_NAME, FORM_CH = SB.BLK, SB.BLOCK_NAME, SB.FORM_CH
STMT_CHARS = 180                                 # v1 과 동일한 진술 절단
ERR_SLOT = "\n[ErrorFeedback]\nnone"             # design [4]: 고정 슬롯 (추론 빌더도 같은 슬롯을 내야 한다)

# ── rango 포매터/콜레이터 (v10 conf 재사용, 경로만 raw-data 로) ──────────────
CONF = yaml.safe_load(open("all_log/ft_qwen3b_v10_conf.yaml"))["tactic_data"]
def _fix(d):
    if isinstance(d, dict): return {k: _fix(v) for k, v in d.items()}
    if isinstance(d, str) and d.startswith("/tmp/coq-dataset"):
        return SDB_PATH if d.endswith("sentences.db") else d.replace("/tmp/coq-dataset", DATA_DIR)
    return d
FCONF = _fix(CONF["formatter_conf"])
assert FCONF["premise"]["kind"] == "tfidf" and FCONF["proof_ret"]["kind"] == "bm25", FCONF
FMT = GeneralFormatter.from_conf(formatter_conf_from_yaml(FCONF))
COL = TD.ProofPremiseCollator(**vars(TD.ProofPremiseCollatorConf.from_yaml(CONF["collator_conf"])))
COL.PREMISE_SEP = "\n"                           # "[PREMISES]" 헤더 대신 우리 블록 헤더
TOK = AutoTokenizer.from_pretrained(CONF["model_name"])
DPD = DATA_DIR + "/data_points"
V10.SENTENCE_DB = SDB_PATH

# ── allocate_and_fmt 감싸기: 우리 블록 목록이면 미리 만든 문자열 ─────────────
_OVR = {"list": None, "str": None}
_orig_aaf = TD.allocate_and_fmt
def _aaf(tokenizer, ss, allowance, reverse=True):
    if ss is not None and _OVR["list"] is not None and (ss is _OVR["list"] or list(ss) == list(_OVR["list"])):
        _OVR["hit"] = _OVR.get("hit", 0) + 1
        return _OVR["str"]
    return _orig_aaf(tokenizer, ss, allowance, reverse)
TD.allocate_and_fmt = _aaf

# ── dp 파일 찾기: (proj, rel) → DatasetFile (프로젝트당 1회 스캔) ─────────────
_DP_IDX = {}; _DP_CACHE = {}
PROJ_ALIAS = {"tr": "coq-community-coq-art"}    # 옛 풀 행의 저장소 별칭 (scratchpad/tr 시절)
def _dp_for(proj, rel):
    proj = PROJ_ALIAS.get(proj, proj)
    if proj not in _DP_IDX:
        idx = {}
        for f in sorted(os.listdir(DPD)):
            if not f.startswith(proj + "-"): continue
            try: dp = DatasetFile.load(Path(DPD) / f, _SDB)
            except Exception: continue
            fp = dp.file_context.file or ""
            m = re.search(r"/repos/" + re.escape(proj) + r"/(.*)$", fp)
            if m: idx[m.group(1)] = (f, dp)
        _DP_IDX[proj] = idx
        if not idx: print(f"  [dp] {proj}: dp 파일 없음/경로 패턴 불일치", flush=True)
    hit = _DP_IDX[proj].get(rel)
    return hit[1] if hit else None

from data_management.sentence_db import SentenceDB
_SDB = SentenceDB.load(Path(SDB_PATH))

# ── 선언문 ────────────────────────────────────────────────────────────────
def _clean_stmt(s):
    s = " ".join((s or "").split())
    if s.startswith("(") and s.endswith(")"): s = s[1:-1].strip()
    return s[:STMT_CHARS]

def decl_of(name, stmts, rango_texts, shown=None):
    """블록 한 줄의 선언문. 풀 진술 → rango 검색 결과 원문 → sentence DB. 없으면 None.
    `shown` = 프롬프트에 실리는 이름 (동명이인이면 한정자를 남긴다 — `Nat.measure_induction` 와
    `N.measure_induction` 가 같은 `_L#` 로 합쳐지거나 같은 맨 이름으로 보이면 구분 불가. rango 는
    동명 이름을 익명화에서 빼는데, 한정자까지 지우면 그 보호가 무의미해진다)."""
    base = name.split(".")[-1]; shown = shown or base
    st = stmts.get(name) or stmts.get(base)
    if st: return f"Lemma {shown} : {_clean_stmt(st)}."
    for t in rango_texts:                        # rango 후보에 원문이 있으면 이름만 맞춰 쓴다
        m = _PREM_DECL.match((t or "").strip())
        if m and m.group(1) == base: return V10._decl(shown, t)[:STMT_CHARS + 60]
    db = V10._db_decl(name)
    if db: return V10._decl(shown, db)[:STMT_CHARS + 60]
    return None

_QUAL = re.compile(r"(?:[A-Za-z_][\w']*\.)+(_L\d+)(?![\w'])")
def strip_qual(s):
    """`Mod._L3` → `_L3` — 익명화된 이름에 남은 한정자 제거 (블록 줄은 맨 이름이므로 일관되게)."""
    return _QUAL.sub(r"\1", s)

# ── 지점 하나 ─────────────────────────────────────────────────────────────
_REF = re.compile(r"\b(e?apply|e?rewrite|exact|eexact)\b([^;]*)")
def ref_form(text, gold):
    """복합 스텝 `t1; t2; apply L in H` 에서 **L 을 참조하는 하위 tactic** 의 형태 (apply/apply-in/rewrite/rewrite-in/exact).
    수집기의 tac 은 머리(t1)만 보므로 뒷 세그먼트 참조는 채널을 못 잡는다 (실측 0.5%, 사용자 지적 2026-09-01)."""
    gb = gold.split(".")[-1]
    for m in _REF.finditer(text or ""):
        seg = m.group(2)
        if re.search(r"(?<![\w'.])" + re.escape(gb) + r"(?![\w'])", seg):
            h = m.group(1); has_in = bool(re.search(r"\bin\b", seg.split(" by ")[0]))
            if h.endswith("rewrite"): return "rewrite-in" if has_in else "rewrite"
            if h in ("apply", "eapply"): return "apply-in" if has_in else "apply"
            return "exact"
    return None


def build_point(r, stat):
    f = r.get("tac"); form_ch = FORM_CH.get(f)
    golds = SB.PR.golds_of(r); stmts = r.get("stmts") or {}
    if golds and form_ch is None:              # 복합 스텝: 참조 하위 tactic 의 형태로 채널을 잡는다
        rf = ref_form(r.get("gold_text") or "", golds[0])
        if rf and FORM_CH.get(rf): f = rf; form_ch = FORM_CH[rf]; stat["복합스텝→참조형"] += 1
    dp = _dp_for(r["proj"], r["thm"])
    if dp is None: stat["dp없음"] += 1; return []
    thmi, k = r["thmi"], r["k"]
    assert 0 <= thmi < len(dp.proofs) and 0 <= k < len(dp.proofs[thmi].steps), "좌표 범위"
    ex = FMT.example_from_step(k, thmi, dp, training=False)
    gold_step = (ex.next_steps[0] if ex.next_steps else "").strip()
    assert gold_step.split() == (r.get("gold_text") or "").split(), f"gold 불일치: {gold_step[:40]} vs {(r.get('gold_text') or '')[:40]}"
    rango_texts = list(ex.premises or [])
    # 4채널 블록 (r18 랭커)
    blocks = {c: SB.rank_channel(r, c)[:BLK[c]] for c in ("ap", "in", "rw", "rwh")}
    used_base = {n.split(".")[-1] for v in blocks.values() for n in v}
    # case A/B — 채널 정확 주입 (v1 과 동일 규칙)
    case = "-"
    if form_ch and golds:                      # gold 없는 무참조 스텝(intros·simpl…)은 주입 없이 '-'
        bl = blocks[form_ch]
        def hit(names):
            bs = set()
            for g in golds:
                gb = g.split(".")[-1]; bs |= {g, gb}
                a = SB.PR.ALIAS.get(g) or SB.PR.ALIAS.get(gb)
                if a: bs.add(a)
            return [n for n in names if n in bs or n.split(".")[-1] in bs]
        if hit(bl): case = "A"
        else:
            case = "B"
            pool_hit = hit(sorted(set((r.get("chan") or {}).get(form_ch, []))))
            gname = pool_hit[0] if pool_hit else golds[0]
            if decl_of(gname, stmts, rango_texts) is None:
                stat["주입선언문없음"] += 1; return []
            if bl:
                lower = list(range(len(bl) // 2, len(bl))) or [len(bl) - 1]
                bl.pop(random.choice(lower))
            bl.insert(random.randrange(len(bl) + 1), gname)
            assert len(hit(bl)) == 1, "주입 후 gold 가 정확히 1회가 아님"
            used_base.add(gname.split(".")[-1])
    # Others = rango tf-idf 상위 중 채널 밖 이름
    oth = []
    for t in rango_texts:
        m = _PREM_DECL.match((t or "").strip())
        if not m or m.group(1) in used_base: continue
        oth.append(" ".join(t.split())[:STMT_CHARS + 60]);
        if len(oth) >= BLK["oth"]: break
    # 블록 → 선언문 줄
    lines = {}; miss = 0
    # 동명이인 = 맨 이름이 같은 **서로 다른** 전체 이름 (같은 lemma 의 다채널 반복은 아님)
    base_cnt = collections.Counter(n.split(".")[-1] for n in {n for c in ("ap", "in", "rw", "rwh") for n in blocks[c]})
    _decl_cache = {}                                   # 같은 lemma 는 채널이 달라도 같은 선언문(같은 출처)으로
    for c in ("ap", "in", "rw", "rwh"):
        ls = []
        for n in blocks[c]:
            shown = n if base_cnt[n.split(".")[-1]] > 1 and "." in n else None   # 동명이인 → 한정자 유지
            if n not in _decl_cache: _decl_cache[n] = decl_of(n, stmts, rango_texts, shown)
            d = _decl_cache[n]
            if d is None: miss += 1; continue
            ls.append(d)
        lines[c] = ls
    lines["oth"] = oth
    stat["블록선언문누락"] += miss
    flat = [d for c in ("ap", "in", "rw", "rwh", "oth") for d in lines[c]]
    sec = "\n\n".join(f"[{BLOCK_NAME[c]}]\n" + ("\n".join(lines[c]) if lines[c] else "none")
                      for c in ("ap", "in", "rw", "rwh", "oth"))
    # rango 콜레이터: premises 만 우리 것으로 갈아끼운다 (정규화 대상 = flat 의 이름들)
    # ★ 같은 lemma 가 여러 채널 블록에 실리면(적용 가능성이 겹침) rango 의 premise_names 가
    #   "동명 중복"으로 보고 익명화에서 뺀다 → 실명 누출. 매핑용 목록은 중복 제거한다.
    flat = list(dict.fromkeys(flat))
    ex.premises = flat; _OVR["list"] = flat; _OVR["str"] = sec; _OVR["hit"] = 0
    TD._LAST_TRAIN_MAPPING = {}
    # ★ 동명이인(맨 이름이 같은 서로 다른 lemma)은 rango 정책대로 **실명 유지** — 한정자 붙은 줄("Lemma Mod.foo :")은
    #   rango 의 이름 추출이 `Mod` 만 보므로 `foo` 가 유일하다고 오판해 매핑하고, 그러면 `Mod.foo` 도 `Mod._L3` 로
    #   바뀌어 서로 다른 두 lemma 가 같은 `_L3` 를 갖는다(검사기 C14 실측 3/62). 그 이름들을 보호 집합에 넣는다.
    dup_bases = {b for b, c in base_cnt.items() if c > 1}
    _saved = set(NN._PROTECTED); NN._PROTECTED |= dup_bases
    try:
        s = COL.collate(TOK, ex)
    finally:
        NN._PROTECTED.clear(); NN._PROTECTED |= _saved
    assert _OVR["hit"] == 1, f"블록 치환 미적용 (hit={_OVR['hit']})"
    tpl = TD.NEWLINE_RESPONSE_TEMPLATE
    i = s.rfind(tpl); assert i > 0, "[TACTIC] 템플릿 없음"
    prompt, target = s[:i] + ERR_SLOT + tpl, s[i + len(tpl):]
    mapping = dict(getattr(TD, "_LAST_TRAIN_MAPPING", {}) or {})
    prompt, target = strip_qual(prompt), strip_qual(target)
    # ── assert 묶음 ──
    for c in ("ap", "in", "rw", "rwh", "oth"):
        assert prompt.count(f"[{BLOCK_NAME[c]}]") == 1, f"블록 헤더 {c} 개수 이상"
    for h in ("[PROOFS]", "[STATE]", "[SCRIPT]", "[ErrorFeedback]"):
        assert prompt.count(h) == 1, f"섹션 {h} 개수 이상"
    assert prompt.endswith(tpl), "프롬프트 끝이 [TACTIC] 가 아님"
    # 정답 왕복: 역매핑하면 원문 gold 로 돌아와야 한다 (한정자 제거분은 base 비교)
    back = apply_inverse(target, mapping) if mapping else target
    assert [w.split(".")[-1] for w in back.split()] == [w.split(".")[-1] for w in gold_step.split()], "익명화 왕복 실패"
    if form_ch and case in ("A", "B"):
        # gold 프리미스가 (익명이든 실명이든) 프롬프트의 자기 채널 블록 안에 있어야 한다
        blk_txt = re.search(rf"\[{BLOCK_NAME[form_ch]}\]\n(.*?)(?=\n\n\[|$)", prompt, re.S).group(1)
        gb = {g.split(".")[-1] for g in golds} | {SB.PR.ALIAS.get(g.split(".")[-1], "").split(".")[-1] for g in golds}
        names_in = {mapping.get(x, x) for x in gb}
        assert any(re.search(r"(?<![\w'])" + re.escape(nm) + r"(?![\w'])", blk_txt) for nm in names_in if nm), \
            f"gold 가 {form_ch} 블록에 없음 (case {case})"
        stat["익명" if any(v in target for v in mapping.values()) else "실명(stdlib/동명)"] += 1
    gold_decl = None
    if form_ch and case in ("A", "B"):
        gold_decl = next((d for n, d in zip(blocks[form_ch], [decl_of(n, stmts, rango_texts, None) for n in blocks[form_ch]])
                          if d and n.split(".")[-1] in {g.split(".")[-1] for g in golds} | {(SB.PR.ALIAS.get(g.split(".")[-1]) or "").split(".")[-1] for g in golds}), None)
    rows = [{"prompt": prompt, "target": target, "case": case, "form": f,
             "proj": PROJ_ALIAS.get(r["proj"], r["proj"]), "thm": r["thm"], "thmi": thmi, "k": k,
             "gold": golds, "gold_decl": gold_decl, "gold_text": r.get("gold_text")}]
    for v in SB.VARIANTS.get((PROJ_ALIAS.get(r["proj"], r["proj"]), r["thm"], thmi, k), [])[:2]:
        vt = strip_qual(apply_mapping(v["variant"], mapping) if mapping else v["variant"])
        rows.append({**rows[0], "target": vt, "case": case + "+var", "rule": v["rule"]})
    return rows


if __name__ == "__main__":
    POOL = [a for a in sys.argv[3:] if a.endswith(".jsonl")]
    # ★ 샤딩: `--shard i/N` — 실측 1.6 s/지점(BM25 유사증명 검색이 지배)이라 12만 지점은 단일 프로세스로 50h+.
    #   행을 (proj, thm) 순으로 정렬해 연속 구간으로 나누면 샤드 안에서 dp/의존 캐시가 잘 맞는다. 샤드 출력은
    #   OUT.part{i}; 병합·지점 셔플은 scripts/sft_merge_shuffle.py 가 한다.
    SHARD = None
    if "--shard" in sys.argv:
        a_, b_ = sys.argv[sys.argv.index("--shard") + 1].split("/"); SHARD = (int(a_), int(b_))
        OUT = OUT + f".part{SHARD[0]}"
    if POOL:
        # ★ 전 지점 풀: gold 없는 무참조 행도 학습 대상 (load_merge 는 gold 없는 행을 버린다). 좌표 중복은 마지막 행.
        _m = {}
        for _pf in POOL:
            for l in open(_pf):
                r_ = json.loads(l)
                if r_.get("local"): continue
                _m[(r_["proj"], r_["thm"], r_["thmi"], r_["k"])] = r_
        rows = list(_m.values())
    else:
        rows, _ = SB.PR.load_merge(SB.SPLITS[SPLIT.upper()])
    print(f"■ 풀: {POOL or SB.SPLITS[SPLIT.upper()]} · 행 {len(rows)}", flush=True)
    if SHARD:
        rows.sort(key=lambda r: (r["proj"], r["thm"], r["thmi"], r["k"]))
        i_, n_ = SHARD; lo = len(rows) * i_ // n_; hi = len(rows) * (i_ + 1) // n_
        rows = rows[lo:hi]; print(f"■ 샤드 {i_}/{n_}: 행 {lo}..{hi} ({len(rows)})", flush=True)
    else:
        random.shuffle(rows)
    stat = collections.Counter(); n = 0; t0 = time.time(); plen = []
    with open(OUT, "w") as fo:
        for r in rows:
            if n >= CAP: break
            if r.get("tac") == "unfold": continue                 # 프롬프트 내부 해결 계열 제외
            try: prs = build_point(r, stat)
            except AssertionError as e: stat[f"assert:{str(e)[:40]}"] += 1; continue
            if not prs: continue
            # 하드 길이 초과 지점은 버린다 — rango 학습 절단은 앞(=우리 블록)부터 잘라 gold 를 잃을 수 있다
            _n = len(TOK(prs[0]["prompt"], add_special_tokens=False).input_ids)
            if _n > HARD - 64: stat["길이초과제외"] += 1; continue
            for pr in prs:
                fo.write(json.dumps(pr, ensure_ascii=False) + "\n"); stat[pr["case"]] += 1
            plen.append(len(TOK(prs[0]["prompt"], add_special_tokens=False).input_ids))
            n += 1
            if n % 100 == 0: print(f"  {n} 지점 · {int(time.time()-t0)}s · {n/max(1,time.time()-t0):.2f}/s", flush=True)
    assert n == 0 or plen, "길이 통계 없음"
    plen.sort()
    print(f"■ SFT 물질화 v2 {SPLIT}: 지점 {n} · 행 {sum(v for k, v in stat.items() if k[0] in 'AB-')} · {int(time.time()-t0)}s")
    print("   통계:", dict(stat))
    if plen:
        print(f"   프롬프트 토큰: 중앙 {plen[len(plen)//2]} · p90 {plen[int(len(plen)*.9)]} · 최대 {plen[-1]} · >{HARD-64} {sum(1 for x in plen if x > HARD-64)}/{len(plen)}")
    if SHARD:
        print("SFTBUILD2_SHARD_DONE")
    else:
        ns = SB.point_shuffle(OUT)
        print(f"   지점 셔플 완료 ({ns}행 · 인접 assert 통과)")
        print("SFTBUILD2_DONE")
