#!/usr/bin/env python3
"""★★★ **필터 → 랭킹 → 프롬프트** 를 끝까지 잰다.

네 지점을 한 번에 본다:

    ① gold 살리는 비율        필터가 통과시킨 목록에 정답이 있나
    ② 필터링 비율             후보 우주 대비 몇 개가 남나
    ③ 랭킹 후 상위 K          같은 tf-idf 로 순위를 매기면 정답이 top 10/20/50/100 에 드나
    ④ 프롬프트 진입           premise 토큰 예산 + 절단을 거쳐 **실제로 실려 나가나**

현행(rango avail_premises) 과 짝지어 비교한다.

사용: python3 scripts/dn_rank_eval.py
"""
import concurrent.futures as cf
import signal
import collections, json, os, re, subprocess, sys, tempfile, yaml, logging
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")
os.environ["CUDA_VISIBLE_DEVICES"] = ""
sys.path.insert(0, "src"); sys.path.insert(0, "CoqStoq")
logging.disable(logging.CRITICAL)
from pathlib import Path
from coqstoq import Split as CSSplit, get_theorem
from data_management.sentence_db import SentenceDB
from evaluation.find_coqstoq_idx import get_thm_desc
from tactic_gen.lm_example import formatter_from_conf
from tactic_gen.tactic_data import (TacticDataConf, example_collator_from_conf,
                                    example_collator_conf_from_yaml, get_tokenizer)
from premise_selection import coq_search_pool as CSP

# ★ 표본 크기. 80 이면 지점 191(rewrite 30) 로 1건=3.8% 라 흔들린다.
#   전체 rand200 을 쓰면 지점 ~450, rewrite ~75 가 된다.
N       = 200
JOBS    = 2
TIMEOUT = 2400
MAX_PT  = 3
PHASE1  = "all_log/dn_pool.jsonl"      # 1단: 필터 결과 (이름 + 진술문)
OUT     = "all_log/dn_rank.jsonl"
CC      = "CoqStoq/test-repos/compcert"
PLUG    = os.path.abspath("ocaml/applic")

t = open(os.path.join(CC, "_CoqProject")).read().split(); ARGS = []; _i = 0
while _i < len(t):
    if t[_i] in ("-R", "-Q"):
        ARGS += [t[_i], os.path.abspath(os.path.join(CC, t[_i+1])), t[_i+2]]; _i += 3
    else: _i += 1
ARGS += ["-R", PLUG, "Applic", "-I", PLUG]
ENV = dict(os.environ); ENV["OCAMLPATH"] = os.path.join(PLUG, "findlib") + ":" + ENV.get("OCAMLPATH", "")

_T = "raw-data/coqstoq-test/coqstoq-test-sentences.db"
CONF = yaml.safe_load(open("all_log/ft_qwen3b_v10_conf.yaml"))
CONF["tactic_data"]["sentence_db_loc"] = _T
CONF["tactic_data"]["data_loc"] = "raw-data/coqstoq-test"
CONF["tactic_data"]["formatter_conf"]["premise"]["sentence_db_loc"] = _T
CONF["tactic_data"]["formatter_conf"]["proof_ret"]["sentence_db_loc"] = _T
CONF["tactic_data"]["formatter_conf"]["proof_ret"]["data_loc"] = "raw-data/coqstoq-test"
td = TacticDataConf.from_yaml(CONF["tactic_data"])
sdb = SentenceDB.load(Path(_T))
fm = formatter_from_conf(td.formatter_conf)
pc = fm.premise_client
col = example_collator_from_conf(example_collator_conf_from_yaml(CONF["tactic_data"]["collator_conf"]))
tok = get_tokenizer(td.model_name)

# ★ apply/rewrite 밖의 채널도 잰다 — 실측상 외부 이름을 쓰는 스텝의 45.8% 다
#   (destruct 17.1% · unfold 10.2% · induction/case/elim 4.3% · exact 2.3%).
NAMED = re.compile(r"\b(?:e?apply|e?rewrite|unfold|destruct|induction|case|elim"
                   r"|e?exact)\s+(?:<-\s*)?\(?\s*"
                   r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
HEADT = re.compile(r"^\s*(?:now\s+|try\s+|repeat\s+)?([A-Za-z_][\w']*)")
DECL = re.compile(r"^\s*(?:Local\s+|Global\s+|Program\s+)?"
                  r"(?:Lemma|Theorem|Corollary|Remark|Definition|Fixpoint|Inductive|"
                  r"Proposition|Instance|Record|Axiom|Fact|Property)\s+([A-Za-z_][\w'.]*)")
# ★ 채널이 일곱이다. 신호(lgg=/e=/z=/d=/g=)가 이름 뒤에 붙을 수 있다.
#   ★★ `DNRWH`(가설 rewrite)를 **긴 것부터** 적어야 한다 — `DNRW` 를 먼저 두면
#      정규식이 `DNRW` 로 맞춘 뒤 공백을 못 찾아 **줄 전체를 버린다**(실측: 147개
#      가설 rewrite 후보가 조용히 사라졌다). 교대(|)는 앞에서부터 시도한다.
LINE = re.compile(r"(?m)^(APPLICIN|APPLIC|DNRWH|DNRW|UNFOLD|DESTRUCT|DECIDE) ([\w'.]+)"
                  r"((?: \w+=-?\d+)*)(?: :: (.*))?$")
_CH = {"APPLIC": "ap", "APPLICIN": "in", "DNRW": "rw", "DNRWH": "rwh",
       "UNFOLD": "uf", "DESTRUCT": "ds", "DECIDE": "dc"}
# ★ 시동 자가검사 — 태그 순서를 잘못 두면 조용히 0이 된다
for _t, _c in _CH.items():
    _m = LINE.search(f"{_t} PTree.gso lgg=15 g=20")
    assert _m and _CH[_m.group(1)] == _c, f"{_t} 파싱 실패 — 교대 순서를 의심하라"
# ★ 지역 가설 이름. `destruct l` 처럼 **지역 변수를 인자로 쓰는** 스텝은
#   애초에 검색 대상이 아니다 — 분모에서 빼야 "풀에" 가 뜻을 갖는다.
HYPL = re.compile(r"(?m)^HYPS ?(.*)$")
# ★ goal 바인더. `induction l; simpl; intros.` 의 `l` 은 가설이 아니라 아직
#   goal 의 바인더다 — 이것도 지역이므로 검색 대상이 아니다.
GBL = re.compile(r"(?m)^GBIND ?(.*)$")
STAT = re.compile(r"APPLIC_STAT\s+ver=(\S+)\s+cand=(\d+)[\s\S]*?sec=([\d.]+)")

# ── ★ 자식 coqtop 메모리 상한 ────────────────────────────────────────────
#   실측: CompCert `backend/Kildall.v` 의 `reachable_predecessors` 하나가
#   coqtop 을 112GB 까지 키워 기계를 마비시켰다(45정리 중 1건뿐).
#   상한을 걸면 그 정리만 죽고 나머지는 정상 수집된다.
_MEM_CAP_GB = 12


def _memcap():
    import resource
    b = _MEM_CAP_GB * 1024 ** 3
    resource.setrlimit(resource.RLIMIT_AS, (b, b))


def _coqtop(cmd, stdin=None, env=None, timeout=None, **kw):
    """★ coqtop 을 **자기 프로세스 그룹**으로 띄운다.

    예전 판은 `subprocess.run` 을 그냥 썼는데, 파이썬 드라이버를 죽이면
    자식 coqtop 이 **살아남아** 기계를 포화시켰다(실측: 좀비 17개, 일부
    12시간·RSS 116GB). 그룹으로 묶어 timeout 때 그룹째 죽인다."""
    import subprocess as _sp
    # ★ 호출부가 `subprocess.run` 관례로 넘기는 인자는 여기서 걷어낸다.
    #   `Popen` 은 `capture_output` 을 모른다 — 넘기면 TypeError 가 나고
    #   바깥 `except` 에 먹혀 **모든 지점이 조용히 0** 이 된다(실측으로 당했다).
    kw.pop("capture_output", None); kw.pop("text", None)
    p = _sp.Popen(cmd, stdin=stdin, stdout=_sp.PIPE, stderr=_sp.PIPE,
                  text=True, env=env, start_new_session=True, preexec_fn=_memcap, **kw)
    try:
        out, err = p.communicate(timeout=timeout)
    except _sp.TimeoutExpired:
        try: os.killpg(os.getpgid(p.pid), signal.SIGKILL)
        except Exception: pass
        p.wait()
        raise
    return _sp.CompletedProcess(cmd, p.returncode, out, err)

# ── ★ 시동 자가검사 ────────────────────────────────────────────────────────
#   이 세션에서 **조용한 0** 에 세 번 당했다:
#     ① OCaml 문자열 줄바꿈이 공백을 남겨 정규식이 안 맞음 → 전 지점 0
#     ② `capture_output` 을 `Popen` 에 넘겨 TypeError → 바깥 except 가 삼킴
#     ③ head_of_file 이 순진해서 200 중 183 을 버림
#   그래서 **실제 출력 표본**으로 정규식을 시동 시에 검사한다.
_SAMPLE_STAT = ("APPLIC_STAT ver=r9 cand=12652 pat=77060 build=0.593 hyps=1 redex=20 "
                "raw=32371 keypass=4812 apply=227 applyin=432 rewrite=275 sec=0.3114")
_SAMPLE_CHECK = ("CHECK ver=r9 PTree.gso ap=1 in=1 rw=1 dnA=1 dnR=1 indexed=1        "
                 "          nap=227 nin=432 nrw=275 redex=20 raw=32371 "
                 "keypass=4812 sec=0.307")

assert re.search(r"APPLIC_STAT\s+ver=(\S+)\s+cand=(\d+)", _SAMPLE_STAT)


def head_by_pos(orig, thm):
    ln = getattr(getattr(thm, "theorem_start_pos", None), "line", None)
    if not ln: return None
    parts = orig.splitlines(keepends=True)
    return "".join(parts[:ln - 1]) if ln - 1 <= len(parts) else None

def phase1(job):
    i, path, head, thm_text, chunks, ks = job
    body = ["Require Import Applic.", "ApplicPrintTypes 1.", head, thm_text]; prev = 0
    for k in ks:
        body.append(chunks[prev]); body.append(f'idtac "@@@{k}".')
        body.append("try applic_filter."); prev = k
    body.append("Admitted.")
    d = os.path.dirname(os.path.abspath(path))
    with tempfile.NamedTemporaryFile("w", suffix=".v", dir=d, delete=False) as f:
        f.write("\n".join(body) + "\n"); tmp = f.name
    try:
        p = _coqtop(["coqtop", "-q"] + ARGS, stdin=open(tmp), env=ENV,
                           capture_output=True, text=True, timeout=TIMEOUT)
        out = p.stdout or ""
        blocks = re.split(r"@@@(\d+)\s*", out); recs = []
        for a in range(1, len(blocks) - 1, 2):
            k = int(blocks[a]); seg = blocks[a + 1]
            m = STAT.search(seg)
            got, chan, sig = {}, collections.defaultdict(list), {}
            for tag, nm, sg, ty in LINE.findall(seg):
                chan[_CH[tag]].append(nm)
                if ty: got[nm] = ty.strip()
                else: got.setdefault(nm, "")
                if sg.strip():
                    sig[nm] = dict(x.split("=") for x in sg.split())
            hm = HYPL.search(seg); gm = GBL.search(seg)
            assert chan or not seg.strip(), "채널이 하나도 안 잡혔다"
            recs.append({"idx": i, "k": k, "names": sorted(got),
                         "stmts": got, "chan": {k2: sorted(set(v))
                                                for k2, v in chan.items()},
                         "sig": sig,
                         "hyps": ((hm.group(1).split() if hm else [])
                                  + (gm.group(1).split() if gm else [])),
                         "ver": m.group(1) if m else None,
                         "cand": int(m.group(2)) if m else None,
                         "sec": float(m.group(3)) if m else None})
        return i, recs
    except Exception:
        return i, []
    finally:
        b = os.path.splitext(tmp)[0]
        for e in (".v", ".vo", ".vok", ".vos", ".glob"):
            try: os.unlink(b + e)
            except OSError: pass

def rank_of(ranked, gold):
    gb = gold.split(".")[-1]
    for j, p in enumerate(ranked):
        m = DECL.match(getattr(p, "text", "") or "")
        if m and (m.group(1) == gold or m.group(1).split(".")[-1] == gb):
            return j
    return None

def seen(nm, text):
    return re.search(r"(?<![\w'])" + re.escape(nm) + r"(?![\w'])", text) is not None

def prompt_has(ex, gold):
    try: s = col.collate_input(tok, ex, normalize=False)
    except TypeError: s = col.collate_input(tok, ex)
    seg = s.split("[PROOFS]")[0] if "[PROOFS]" in s else s
    seg = seg.split("[PREMISES]")[-1]
    return seen(gold, seg) or seen(gold.split(".")[-1], seg)

if __name__ == "__main__":
    ids = [int(x) for x in Path("data/compcert_bs2_rand200_idx.txt").read_text().split()]
    jobs, info = [], {}
    for i in ids:
        if len(jobs) >= N: break
        try:
            thm = get_theorem(CSSplit.TEST, i, Path("CoqStoq"))
            d = get_thm_desc(thm, Path("raw-data/coqstoq-test"), sdb)
            if d is None: continue
            proof = d.dp.proofs[d.idx]
            path = os.path.join(CC, str(thm.path)); orig = open(path, errors="ignore").read()
            head = head_by_pos(orig, thm)
        except Exception: continue
        if head is None: continue
        ks = [k for k, s in enumerate(proof.steps)
              if HEADT.match(s.step.text or "")
              and HEADT.match(s.step.text).group(1) in (
                  "apply", "eapply", "rewrite", "erewrite",
                  "unfold", "destruct", "induction", "case", "elim",
                  "exact", "eexact")
              and NAMED.search(s.step.text or "") and s.goals]
        if not ks: continue
        if len(ks) > MAX_PT:
            stp = len(ks)/MAX_PT; ks = [ks[int(x*stp)] for x in range(MAX_PT)]
        steps = [s.step.text for s in proof.steps]
        chunks, prev = {}, 0
        for k in ks: chunks[prev] = "".join(steps[prev:k]); prev = k
        info[i] = (d, ks)
        jobs.append((i, path, head, proof.theorem.term.text, chunks, ks))
    jobs.sort(key=lambda j: len(open(j[1], errors="ignore").read()))
    print(f"■ 1단: 정리 {len(jobs)} · 병렬 {JOBS}", flush=True)
    POOL = {}
    with open(PHASE1, "w") as fo, cf.ThreadPoolExecutor(JOBS) as ex:
        for n, (i, recs) in enumerate(ex.map(phase1, jobs)):
            for r in recs:
                POOL[(r["idx"], r["k"])] = r
                fo.write(json.dumps(r, ensure_ascii=False) + "\n")
            if (n+1) % 10 == 0: print(f"   … {n+1}/{len(jobs)} · 지점 {len(POOL)}", flush=True)
            fo.flush()
    assert POOL, "1단이 아무 지점도 못 얻었다 — 플러그인 출력을 확인하라"
    APPLIC_RANK = {}
    print(f"■ 2단: 랭킹·프롬프트 ({len(POOL)} 지점)", flush=True)
    S = collections.Counter(); C = collections.defaultdict(list)
    with open(OUT, "w") as fo:
        for (i, k), r in sorted(POOL.items()):
            d, _ = info[i]; dp, pidx = d.dp, d.idx; proof = dp.proofs[pidx]
            try:
                st = proof.steps[k]
                gold = NAMED.search(st.step.text).group(1)
                base = list(pc.premise_filter.get_pos_and_avail_premises(st, proof, dp).avail_premises)
            except Exception:
                continue
            filt = CSP.as_sentences([f"Lemma {n} : {t}." for n, t in r["stmts"].items() if t])
            S["지점"] += 1
            C["우주"].append(r["cand"] or 0)
            _h = HEADT.match(st.step.text)
            _h = _h.group(1) if _h else ""
            tac = ("rewrite" if _h.endswith("rewrite") else
                   "apply" if _h in ("apply", "eapply") else
                   _h if _h in ("unfold", "destruct", "exact", "induction",
                                "case", "elim") else "기타")
            _loc = gold in set(r.get("hyps") or [])
            row = {"idx": i, "k": k, "gold": gold, "cand": r["cand"], "tac": tac,
                   "local": _loc,
                   "n_filt": len(filt), "n_base": len(base)}
            for _c in ("ap", "in", "rw", "rwh", "uf", "ds", "dc"):
                row[f"n_{_c}"] = len(r.get("chan", {}).get(_c, []))
            if _loc:
                # ★ 지역 변수를 인자로 쓰는 스텝은 검색 대상이 아니다 — 기록만 남긴다
                fo.write(json.dumps(row, ensure_ascii=False) + "\n"); continue
            # ★ 4번째: 필터 결과에 **필터가 만든 신호**로 순위를 매긴다.
            #   ★ 주의: 아래 ④ 표는 **합쳐서 정렬**한다(현행 tf-idf 와 같은 조건 비교용).
    #     채널별 정렬 수치는 `scripts/chan_ranker.py` 가 낸다 —
    #     실측으로 rewrite @10 이 38.6%(합침) vs 75.4%(채널별)로 두 배 차이다.
    #   tf-idf 는 "어휘가 겹치는가" 를 재는데 우리 모집단에는 안 맞는다 —
            #   실측으로 필터후 top10 의 43.3% 가 stdlib, 19.3% 가 보편 lemma 였다.
            APPLIC_RANK[(i, k)] = dict(names=list((r.get("chan") or {}).get("ap", []))
                                       + list((r.get("chan") or {}).get("in", []))
                                       + list((r.get("chan") or {}).get("rw", []))
                                       + list((r.get("chan") or {}).get("rwh", []))
                                       + list((r.get("chan") or {}).get("uf", []))
                                       + list((r.get("chan") or {}).get("ds", []))
                                       + list((r.get("chan") or {}).get("dc", [])),
                                       sig=r.get("sig") or {},
                                       stmts=r.get("stmts") or {})
            for lab, pool in (("현행", base), ("필터후", filt), ("합집합", list(base) + filt)):
                if not pool: continue
                try: ranked = pc.get_ranked_premises(k, proof, dp, pool, False)
                except Exception: continue
                rk = rank_of(ranked, gold)
                S[f"{lab}|n"] += 1; C[f"{lab}|풀"].append(len(pool))
                if rk is not None:
                    S[f"{lab}|풀에"] += 1
                    for K in (10, 20, 50, 100): S[f"{lab}@{K}"] += (rk < K)
                    C[f"{lab}|순위"].append(rk)
                row[f"{lab}_rank"] = rk; row[f"{lab}_n"] = len(pool)
                # 프롬프트 — 실제 formatter 로 만들어 [PREMISES] 구간만 본다
                try:
                    ex2 = fm.example_from_step(k, pidx, dp, training=False)
                    ex2.premises = [getattr(p, "text", "") for p in ranked]
                    inp = prompt_has(ex2, gold)
                    S[f"{lab}|프롬프트"] += inp; row[f"{lab}_prompt"] = inp
                except Exception:
                    pass
            fo.write(json.dumps(row, ensure_ascii=False) + "\n")
    import statistics as stt
    assert S["지점"] > 0, "2단에서 지점이 0"
    def dist(v):
        v = sorted(v)
        if not v: return "—"
        q = lambda p: v[min(len(v)-1, int(p*len(v)))]
        return (f"중앙 {stt.median(v):,.0f} · p25 {q(.25):,.0f} · p75 {q(.75):,.0f} "
                f"· p90 {q(.90):,.0f} · max {max(v):,.0f}")

    def table(rows, title):
        """한 부분집합의 표.

        ▸ @K 는 **랭킹 순위**다 (필터후 풀 안에서 gold 이 K위 안인가).
        ▸ 프롬프트는 **실제 [PREMISES] 구간에 실렸나**다 — 토큰 예산·절단 뒤.
          둘은 다른 것이므로 항상 같이 낸다.
        """
        if not rows: return
        n = len(rows)
        tc = collections.Counter(r.get("tac", "?") for r in rows)
        nloc = sum(1 for r in rows if r.get("local"))
        print(f"\n■ {title}  ({n} 지점)")
        print(f"   ▸ 대상 tactic : " + " · ".join(f"{k} {v}" for k, v in tc.most_common()))
        if nloc:
            print(f"   ▸ 제외 : 지역변수 인자 {nloc}개 (검색 대상 아님)")
        print(f"   ▸ @K = 랭킹 순위 · 프롬프트 = 실제 [PREMISES] 진입")
        print(f"   {'풀':10s}{'개수':>8s}{'풀에':>8s}{'@10':>8s}{'@20':>8s}"
              f"{'@50':>8s}{'@100':>8s}{'순위중앙':>10s}{'프롬프트':>10s}")
        for lab in ("현행", "필터후", "합집합", "적용가능"):
            rk = [r.get(f"{lab}_rank") for r in rows if f"{lab}_rank" in r]
            got = [x for x in rk if x is not None]
            sz = [r.get(f"{lab}_n", 0) for r in rows if f"{lab}_n" in r]
            pr = [r.get(f"{lab}_prompt") for r in rows if f"{lab}_prompt" in r]
            m = max(1, len(rk))
            pct = lambda K: 100*sum(1 for x in got if x < K)/m
            print(f"   {lab:10s}{stt.median(sz) if sz else 0:8,.0f}"
                  f"{100*len(got)/m:7.1f}%{pct(10):7.1f}%{pct(20):7.1f}%"
                  f"{pct(50):7.1f}%{pct(100):7.1f}%"
                  f"{(stt.median(got) if got else 0):10,.0f}"
                  f"{(100*sum(1 for x in pr if x)/max(1,len(pr))):9.1f}%")
        # ★ 목표 미달은 **경고**로 낸다 — assert 로 죽이면 측정을 잃는다.
        rk = [r.get("필터후_rank") for r in rows if "필터후_rank" in r]
        cov = 100*len([x for x in rk if x is not None])/max(1, len(rk))
        if cov < 95.0:
            print(f"   ⚠ 필터 통과분에 gold 이 {cov:.1f}% — 목표 100% 미달. "
                  f"채널 배선/상한을 의심하라")

    # ── ★ 적용가능 랭커 패스 ──
    #   같은 지점·같은 필터 결과에, tf-idf 대신 **비트합** 으로 순위를 매기고
    #   같은 방식으로 프롬프트를 조립해 진입률까지 잰다.
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location("ar", "scripts/applic_rank.py")
    _ar = _ilu.module_from_spec(_spec)
    try:
        _spec.loader.exec_module(_ar)
        _rows_for_idf = [json.loads(l) for l in open(PHASE1)]
        for _r in _rows_for_idf:
            _r["chan"] = _r.get("chan") or {}
        _idf, _, _ = _ar.build_idf(_rows_for_idf)
        _sc = _ar.make_bit_score(_rows_for_idf, _idf)
        _ok = True
    except Exception as _e:
        print(f"   ⚠ 적용가능 랭커 로드 실패: {_e}")
        _ok = False
    if _ok:
        import io as _io
        _tmp = []
        for _l in open(OUT):
            _row = json.loads(_l)
            _key = (_row["idx"], _row["k"])
            _a = APPLIC_RANK.get(_key)
            if _a and not _row.get("local"):
                _names = list(dict.fromkeys(_a["names"]))
                _g = float((list(_a["sig"].values()) or [{}])[0].get("g", 1) or 1)
                _ranked = sorted(_names, key=lambda x: -_sc(x, _a["sig"], _idf, _g))
                _gold = _row["gold"]; _gb = _gold.split(".")[-1]
                _pos = next((j for j, x in enumerate(_ranked)
                             if x == _gold or x.split(".")[-1] == _gb), None)
                _row["적용가능_rank"] = _pos
                _row["적용가능_n"] = len(_ranked)
                # 프롬프트: 같은 formatter 로 조립
                try:
                    _d, _ks = info[_row["idx"]]
                    _dp, _pidx = _d.dp, _d.idx
                    _ex = fm.example_from_step(_row["k"], _pidx, _dp, training=False)
                    _ex.premises = [f"Lemma {x} : {_a['stmts'].get(x, '')}."
                                    for x in _ranked if _a["stmts"].get(x)]
                    _row["적용가능_prompt"] = prompt_has(_ex, _gold)
                except Exception:
                    pass
            _tmp.append(_row)
        with open(OUT, "w") as _f:
            for _row in _tmp:
                _f.write(json.dumps(_row, ensure_ascii=False) + "\n")

    ROWS = [json.loads(l) for l in open(OUT)]
    nn = max(S["지점"], 1)
    med = lambda k: stt.median(C[k]) if C[k] else 0
    assert med('우주') > 0, "후보 우주가 0 — APPLIC_STAT 파싱 실패를 의심하라"
    print(f"\n■ 필터 → 랭킹 → 프롬프트 (CompCert {S['지점']} 지점)")
    print(f"\n── ① gold 살리는 비율 · ② 필터링 비율 ──")
    print(f"   후보 우주 (환경 전체)   {med('우주'):,.0f}개")
    print(f"   필터 통과 (중앙)        {med('필터후|풀'):,.0f}개"
          f"   = {med('필터후|풀')/max(1,med('우주'))*100:.2f}%"
          f"  ({med('우주')/max(1,med('필터후|풀')):,.0f}배 축소)")
    print(f"   ★ gold 생존             {S['필터후|풀에']/max(1,S['필터후|n'])*100:.1f}%")
    print(f"\n── ③ 채널별 후보 수 ──")
    for ch, nm in (("ap", "apply"), ("in", "apply…in"), ("rw", "rewrite"),
                   ("uf", "unfold"), ("ds", "destruct")):
        v = [r.get(f"n_{ch}", 0) for r in ROWS if f"n_{ch}" in r]
        if v: print(f"   {nm:10s} {dist(v)}")
    table(ROWS, "④ 전체")
    for tac, nm in (("apply", "gold = apply"), ("rewrite", "gold = rewrite"),
                    ("unfold", "gold = unfold"), ("destruct", "gold = destruct")):
        table([r for r in ROWS if r.get("tac") == tac], f"④ {nm}")
