#!/usr/bin/env python3
"""assert 변환의 **실패 유형을 실제 Coq 실행으로 사냥**한다.

## 왜 동적이어야 하나

`forall {A}` 가 문법 오류인 것도, bullet 이 `Wrong bullet` 으로 거부되는 것도, 암묵인자
lemma 를 `exact L` 로 받으면 타입이 안 맞는 것도 — **전부 실행해 보고서야** 드러났다.
정적 검사로는 알 수 없다.

## 무엇을 하나

실제 gold step 을 가져와 assert 변환하고, 원본 증명과 변환 증명을 **둘 다 Coq 에 넣어**
비교한다. 원본은 되는데 변환이 깨지면 그것이 우리가 찾는 실패 유형이다.

오류 메시지를 정규화해 유형별로 모은다 — 어떤 함정이 얼마나 자주 터지는지 알아야
고칠 순서를 정할 수 있다.

## 대상

★ 정정(2026-08-21): `/tmp/coq-dataset/repos` 에 원본이 **13GB · 2,182 레포** 받아져 있다.
TRAIN 도 대부분 Coq 을 돌릴 수 있다(표본 기준 ~81%, 일부 레포는 아직 안 받아짐).
따라서 TRAIN cut 도 **정적 검사에 그치지 말고 동적으로 검증할 수 있다.**
(옛 주석은 '원본이 없다'고 단정했는데 사실이 아니었다.)

사용: python3 scripts/hunt_assert_errors.py [스텝수] [val|test]
"""
import collections
import copy
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
import yaml  # noqa: E402
from coqpyt.coq.base_file import CoqFile  # noqa: E402
from data_management.splits import Split  # noqa: E402
from data_management.dataset_file import DatasetFile  # noqa: E402
from data_management.sentence_db import SentenceDB  # noqa: E402
from tactic_gen.tactic_data import TacticDataConf, LmDataset  # noqa: E402
from tactic_gen.gold_lemma import gold_lemmas  # noqa: E402
from tactic_gen.search_query import local_names  # noqa: E402
from tactic_gen import assert_split as A  # noqa: E402
from tactic_gen.assert_split import (transform, extract_application,  # noqa: E402
                                     transform_with_types)

NSTEP = int(sys.argv[1]) if len(sys.argv) > 1 else 40
SPLIT = (sys.argv[2] if len(sys.argv) > 2 else "test").upper()
# TRAIN 은 splits/commits.json 으로 복구한 /tmp/coq-dataset/repos 를 쓴다
#   (VAL/TEST 는 CoqStoq 가 빌드해 둔 트리). TRAIN 은 빌드가 없어 의존성이 안 맞으면
#   **원본도 컴파일 실패**하므로 그 케이스는 자동으로 스킵된다 — 비교가 오염되지 않는다.
REPOS = (Path("/tmp/coq-dataset/repos") if SPLIT == "TRAIN"
         else Path(f"CoqStoq/{SPLIT.lower()}-repos"))

_NAME = re.compile(r"^\s*(?:Lemma|Theorem|Definition|Corollary|Remark|Fact|Fixpoint|"
                   r"Instance|Axiom|Proposition|Example|Let|Program\s+\w+)\s+"
                   r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")


def declname(t):
    m = _NAME.match(t or "")
    return m.group(1) if m else None


def find_decl(src: str, decl: str) -> int:
    key = re.sub(r"\\ ", r"\\s+", re.escape(decl.strip()))
    m = re.search(key, src)
    if m:
        return m.start()
    mm = re.match(r"\s*\w+\s+([A-Za-z_][\w']*)", decl)
    if mm:
        m2 = re.search(r"^[ \t]*\w+\s+" + re.escape(mm.group(1)) + r"\b", src, re.M)
        if m2:
            return m2.start()
    return -1


def _clean_ty(t: str) -> str:
    """`Check` 출력에서 **타입만** 남긴다.

    ★ Coq 은 미결정 evar 가 있으면 타입 뒤에 `where ?h : [ …컨텍스트… ]` 를 덧붙인다.
      그걸 타입의 일부로 삼키면 `Syntax error: 'as' or 'in' … after [term level 200]`
      이 난다 — B 실험 실패 37건 중 15건(최다)의 원인이었다(실측).
      `where` 를 잘라내고 `?x` 를 `_` 로 바꿔 `eassert` 로 세우면 통과한다.
    """
    t = " ".join((t or "").split())
    return re.split(r"\s+where\s+\?", t)[0].strip()


def norm_err(msg: str) -> str:
    """오류 메시지를 유형으로 접는다 (구체 이름·항을 지운다)."""
    m = (msg or "").strip().replace("\n", " ")
    m = re.sub(r'"[^"]*"', '"…"', m)
    m = re.sub(r"\b[A-Za-z_][\w'.]{2,}\b", "X", m)
    return m[:90]


cc = yaml.safe_load(open("all_log/ft_qwen3b_v8_conf.yaml"))
tdc = copy.deepcopy(cc["tactic_data"])
tdc["formatter_conf"].pop("proof_ret", None)
tdc["formatter_conf"].pop("num_proofs", None)
conf = TacticDataConf.from_yaml(tdc)
ds = LmDataset.from_conf(conf, getattr(Split, SPLIT), 20000)
sdb = SentenceDB.load(conf.sentence_db_loc)

stat = collections.Counter()
why = collections.Counter()
gate = collections.Counter()
name_bad = []
errs = collections.Counter()
samples = collections.defaultdict(list)
tmp_files = []
t_start = time.time()

for i in range(20000):
    if stat["검증"] >= NSTEP:
        break
    try:
        e = ds.raw_example(i)
    except Exception:
        continue
    st = getattr(e, "proof_state", "") or ""
    tac = (e.next_steps[0] if getattr(e, "next_steps", None) else "").strip()
    golds = gold_lemmas(tac, local_names(st))
    if not golds:
        continue
    prems = [p for p in (getattr(e, "premises", None) or [])]
    ptexts = [p if isinstance(p, str) else getattr(p, "text", str(p)) for p in prems]
    pick = []
    for g in golds:
        for t in ptexts:
            nm = declname(t)
            if nm and nm.split(".")[-1] == g:
                pick.append((nm, t))
                break
    if not pick:
        stat["premise 텍스트 못 찾음"] += 1
        continue

    script = getattr(e, "proof_script", "") or ""

    # ── 실제 파일에서 그 지점을 재현 ──
    sid = ds.shuffled_idx.get_idx(ds.split, i)
    try:
        dp = DatasetFile.load(conf.data_loc / "data_points" / sid.file, sdb)
    except Exception:
        continue
    fc = getattr(dp.file_context, "file", "") or ""
    mm = re.search(r"repos/([^/]+)/(.+)$", fc)
    if not mm:
        stat["경로 파싱 실패"] += 1
        continue
    proj_dir, rel = mm.group(1), mm.group(2)
    if SPLIT == "TRAIN":
        p0 = REPOS / proj_dir / rel
        cands = [p0] if p0.exists() else list(REPOS.glob(f"{proj_dir}/{rel}"))
    else:
        cands = list(REPOS.glob(f"*/{rel}")) or list(REPOS.glob(f"**/{rel}"))
    if not cands:
        stat["소스 파일 없음"] += 1
        continue
    vf = cands[0].resolve()
    try:
        src = vf.read_text(errors="ignore")
    except Exception:
        continue
    decl = script.strip().split("\n")[0].strip()
    at = find_decl(src, decl)
    if at < 0:
        stat["선언 위치 못 찾음"] += 1
        continue

    ws = str((REPOS / cands[0].relative_to(REPOS).parts[0]).resolve())

    # ★ **뒤 증명(suffix)까지 검증**하기 위해 원본에서 전체 증명을 뽑는다.
    #   assert 는 가설 H 를 컨텍스트에 추가하므로 뒤 증명이 영향받을 수 있다:
    #   `assumption`/`auto` 가 H 를 잘못 집거나, 가설 번호(H0·H1)가 밀리거나,
    #   `intros` 패턴 개수가 어긋난다. 스텝만 확인하면 그걸 놓친다.
    _end = -1
    for _kw in ("\nQed.", "\nDefined.", "\nAdmitted.", " Qed.", " Defined."):
        _i = src.find(_kw, at)
        if _i >= 0 and (_end < 0 or _i < _end):
            _end = _i + len(_kw)
    full_proof = src[at:_end] if _end > at else None
    # prefix(=proof_script) 다음이 suffix 다. 공백이 다를 수 있어 정규화해 찾는다
    suffix = None
    if full_proof:
        _norm = lambda x: re.sub(r"\s+", " ", x).strip()
        _np, _nf = _norm(script + " " + tac), _norm(full_proof)
        if _np and _nf.startswith(_np[:min(len(_np), 400)]):
            # 원문에서 prefix+tac 이 끝나는 지점을 문자 단위로 되짚는다
            _cnt, _k = 0, 0
            _target = len(_np)
            _sq = _norm(script + " " + tac)
            # 간단하고 안전한 방법: 원문을 정규화하며 같은 길이에 도달하는 위치를 찾는다
            _acc = []
            for _k, _ch in enumerate(full_proof):
                _acc.append(_ch)
                if len(_norm("".join(_acc))) >= _target:
                    break
            suffix = full_proof[_k + 1:]

    def check_terms_all(terms):
        """★ `Set Printing All` 로 **notation 없는** 타입을 얻는다.

        실패 119건을 분류하니 근본 원인이 하나였다: **Coq 의 출력이 항상 다시 파싱되지
        않는다.** `{fpmodR}` · `'Mor(M,N)` · `- _` 같은 notation 은 출력용 형태라
        assert 에 넣으면 `Unknown interpretation for notation` 이 난다(실패의 67% 가
        SSReflect/mathcomp 계열).

        `Set Printing All` 은 notation 을 전부 펴서 `@eq R (Ropp x) (Rmult …)` 처럼
        만든다 — 검증: 이 형태는 assert 에서 오류 0 으로 파싱된다.

        대가: 항이 길고 사람이 쓰는 형태가 아니다. 그래서 **notation 형태를 먼저 쓰고
        실패할 때만** 이쪽으로 폴백한다.
        """
        f = vf
        bak = vf.parent / (vf.name + ".abak")
        out = {}
        try:
            body = (script + "\nSet Printing All.\n"
                    + "\n".join(f"Check ({t})." for t in terms) + "\n")
            vf.rename(bak)
            pass  # ★ 원본 vf 를 tmp_files 에 넣으면 스크립트 끝에서 삭제된다
            f.write_text(src[:at] + body)
            cf = CoqFile(str(f), timeout=180, workspace=ws)
            cf.run()
            msgs = [getattr(d, "message", "") for d in cf.diagnostics
                    if getattr(d, "severity", 0) == 3]
            cf.close()
            got = []
            for m in msgs:
                mm = re.match(r"\s*(.+?)\s*:\s*(.+)$", m, re.S)
                if mm:
                    got.append(_clean_ty(mm.group(2)))
            for t, ty in zip(terms, got):
                out[t] = ty
        except Exception:
            pass
        finally:
            f.unlink(missing_ok=True)
            if bak.exists():
                bak.rename(vf)
        return out

    def check_terms(terms):
        """★ **증명 지점에서** `Check (항).` 을 실행해 타입을 얻는다.

        `have := L a b` 처럼 인자를 적용하는 형태는 `L` 만 assert 하면 인자 개수가
        어긋난다(H 는 인자가 전부 명시적인데 `L a b` 는 암묵인자가 채워진 상태).
        **항 전체**의 타입을 물으면 인스턴스화·Section 변수·암묵인자가 전부 정리된
        형태가 나와 그 문제가 원천적으로 사라진다.

        지역 변수(`p`, `q`)가 보이려면 반드시 **증명 안에서** 물어야 한다.
        """
        # ★ 임시 파일 이름이 **모듈 경로**가 되어 타입 안에 샌다
        #   (`_hct_2538238.pre_graph was not found` — 실측 최다 실패).
        #   원본과 같은 이름을 써야 한다: 원본을 잠시 옮기고 그 자리에 쓴다.
        f = vf
        bak = vf.parent / (vf.name + ".hbak")
        out = {}
        try:
            body = script + "\n" + "\n".join(f"Check ({t})." for t in terms) + "\n"
            vf.rename(bak)
            pass  # ★ 원본 vf 를 tmp_files 에 넣으면 스크립트 끝에서 삭제된다
            f.write_text(src[:at] + body)
            cf = CoqFile(str(f), timeout=180, workspace=ws)
            cf.run()
            msgs = [getattr(d, "message", "") for d in cf.diagnostics
                    if getattr(d, "severity", 0) == 3]
            cf.close()
            # `Check (t).` 순서대로 답이 온다고 보고 매칭 (': ' 뒤가 타입)
            got = []
            for m in msgs:
                mm = re.match(r"\s*(.+?)\s*:\s*(.+)$", m, re.S)
                if mm:
                    got.append(_clean_ty(mm.group(2)))
            for t, ty in zip(terms, got):
                out[t] = ty
        except Exception:
            pass
        finally:
            f.unlink(missing_ok=True)
            if bak.exists():
                bak.rename(vf)
        return out

    def check_types(names):
        """★ `Check L.` 로 **Coq 이 보는 실제 타입**을 얻는다.

        sentences.db 의 텍스트는 **Section 안의 원문**이라 Section 변수(`insT`, `A` …)가
        그대로 들어 있다. Section 밖에서는 그것들이 인자로 바뀌므로 원문을 그대로 assert
        하면 `The variable insT was not found` 로 깨진다(실측 최다 유형).
        Coq 에게 물어보면 정확한 타입을 준다.
        """
        # ★ 여기도 **원본과 같은 파일 이름**이어야 한다 — 임시 이름을 쓰면 그것이
        #   모듈 경로가 되어 타입에 샌다(`_hc_2569394.pre_graph was not found`).
        f = vf
        bak = vf.parent / (vf.name + ".cbak")
        out = {}
        try:
            vf.rename(bak)
            pass  # ★ 원본 vf 를 tmp_files 에 넣으면 스크립트 끝에서 삭제된다
            f.write_text(src[:at] + "\n".join(f"Check @{n}." for n in names) + "\n")
            cf = CoqFile(str(f), timeout=180, workspace=ws)
            cf.run()
            msgs = [getattr(d, "message", "") for d in cf.diagnostics
                    if getattr(d, "severity", 0) == 3]
            cf.close()
            for m in msgs:
                mm = re.match(r"\s*@?([A-Za-z_][\w'.]*)\s*:\s*(.+)$", m, re.S)
                if mm:
                    out[mm.group(1).split(".")[-1]] = " ".join(mm.group(2).split())
        except Exception:
            pass
        finally:
            f.unlink(missing_ok=True)
            if bak.exists():
                bak.rename(vf)
        return out

    def try_proof(body: str, tag: str):
        # 증명 검증도 **원본과 같은 파일 이름**으로 해야 모듈 경로가 어긋나지 않는다
        bak = vf.parent / (vf.name + f".pbak{tag}")
        try:
            vf.rename(bak)
            pass  # ★ 원본 vf 를 tmp_files 에 넣으면 스크립트 끝에서 삭제된다
            vf.write_text(src[:at] + body + "\n")
            cf = CoqFile(str(vf), timeout=180, workspace=ws)
            cf.run()
            out = [getattr(d, "message", "") for d in cf.errors]
            cf.close()
            return out
        except Exception as ex:
            return [f"예외: {ex}"]
        finally:
            vf.unlink(missing_ok=True)
            if bak.exists():
                bak.rename(vf)

    e0 = try_proof(script + "\n" + tac, "o")
    if e0:
        stat["원본이 이미 오류(스킵)"] += 1
        continue
    # 원본도 suffix 까지 되는지 먼저 확인 — 원본이 안 되면 비교가 무의미하다
    if suffix is not None:
        if try_proof(script + "\n" + tac + "\n" + suffix, "os"):
            stat["원본 suffix 실패(스킵)"] += 1
            suffix = None

    # ── ① 적용 항 전체를 뽑아 그 타입을 Coq 에 묻는다 (인자 개수 문제 원천 제거) ──
    terms = []
    for nm, _pt in pick:
        r = extract_application(tac, nm)
        if r and r[0] not in terms:
            terms.append(r[0])
    A.WHY.clear()
    tr = None
    if terms:
        tt = check_terms(terms)
        apps = [(t, tt.get(t)) for t in terms if tt.get(t)]
        stat["Check(항) 타입 획득"] += len(apps)
        if apps:
            tr = transform_with_types(tac, apps, state=st, proof_script=script,
                                      suffix=(suffix or ""), premises=ptexts)
    # ── ② 실패하면 lemma 이름만으로 (기존 방식) ──
    if tr is None:
        types = check_types([n for n, _ in pick])
        pick2 = [(nm, f"Lemma {nm.split('.')[-1]} : {ty}." if
                  (ty := types.get(nm.split('.')[-1])) else pt) for nm, pt in pick]
        stat["Check(이름) 폴백"] += 1
        tr = transform(tac, pick2, proof_script=script, state=st,
                       suffix=(suffix or ""), premises=ptexts)
    why_snap = list(A.WHY)
    if tr is None:
        stat["변환 포기(위험/불가)"] += 1
        for _w in (A.WHY or ["이유 미기록"]):
            why[_w] += 1
        continue
    e1 = try_proof(script + "\n" + tr, "t")
    # 스텝이 통과하면 **뒤 증명까지 붙여 Qed 에 도달하는지** 본다
    if not e1 and suffix is not None:
        stat["suffix 검증 시도"] += 1
        e1s = try_proof(script + "\n" + tr + "\n" + suffix, "s")
        if e1s:
            stat["✗ suffix 에서 깨짐"] += 1
            e1 = e1s
        else:
            stat["✓ suffix 까지 통과"] += 1
    # ★ notation 형태가 깨지면 **Printing All 형태**로 다시 시도한다.
    #   장황하지만 재파싱이 보장된다 — assert 를 아예 못 만드는 것보다 낫다.
    if e1 and terms:
        ta = check_terms_all(terms)
        apps2 = [(t, ta.get(t)) for t in terms if ta.get(t)]
        if apps2:
            tr2 = transform_with_types(tac, apps2, state=st, proof_script=script,
                                       skip_risk=True, suffix=(suffix or ""),
                                       premises=ptexts)
            if tr2:
                e2 = try_proof(script + "\n" + tr2, "t2")
                if not e2:
                    stat["★ PrintingAll 폴백으로 성공"] += 1
                    tr, e1 = tr2, e2
    # ★ 이름 침범 검사 — 만든 `H_asrt*` 가 state/앞증명/뒤증명/premise 어디에도
    #   원래 있던 이름이 아니어야 한다. 한 건이라도 걸리면 즉시 드러나게 센다.
    for _nm in set(re.findall(r"as\s+(H_asrt\d+)", tr)):
        if not A.name_is_free(_nm, st, script, suffix or "", ptexts):
            stat["★★ 이름 침범!"] += 1
            name_bad.append((_nm, tac[:60]))
    # ── gold premise **없이** assert 만 넣었을 때 뒤 증명이 도는가 ───────────
    #   `{ exact L. }` 를 `{ admit. }` 로 바꾸면 "필요한 명제를 선언만 했을 때"가 된다.
    #   이것이 통과하면 **assert 구문 자체는 안전**하고, 남는 문제는 그 명제를
    #   증명할 lemma 를 찾는 것뿐이라는 뜻이다(= 우리 아이디어의 핵심 가정).
    if not e1 and suffix is not None:
        tr_ad = re.sub(r"\{ exact [^{}]*\. \}", "{ admit. }", tr)
        # ★ `admit` 뒤에 `Qed.` 가 오면 **무조건** 실패한다:
        #   "Attempt to save a proof with given up goals … use Admitted".
        #   suffix 는 원본 증명의 끝이라 `Qed.` 를 포함한다 → 바꿔 줘야 측정이 성립한다.
        suf_ad = re.sub(r"\b(Qed|Defined)\s*\.", "Admitted.", suffix)
        if tr_ad != tr:
            stat["admit 시도"] += 1
            if try_proof(script + "\n" + tr_ad + "\n" + suf_ad, "ad"):
                stat["✗ admit 만으로는 suffix 실패"] += 1
            else:
                stat["✓ admit 만으로 suffix 통과"] += 1
    stat["검증"] += 1
    # ★ 필터를 껐을 때(ASSERT_RISK=0) "걸렸을 텐데 통과시킨" 항목의 실제 결과를 센다.
    #   이것이 곧 필터별 정확도다 — 실패율이 낮으면 그 필터는 과하다.
    for _w in {w[1:] for w in why_snap if w.startswith("~")}:
        gate[(_w, "실패" if e1 else "성공")] += 1
    if not e1:
        stat["✓ 변환 성공"] += 1
    else:
        stat["✗ 변환 실패"] += 1
        k = norm_err(e1[0])
        errs[k] += 1
        if len(samples[k]) < 2:
            samples[k].append((tac[:70], tr.split("\n")[0][:100], e1[0][:150]))
    if stat["검증"] % 5 == 0:
        print(f"  {stat['검증']}건 검증 · 성공 {stat['✓ 변환 성공']} "
              f"({time.time()-t_start:.0f}s)", flush=True)

# ★ 여기서 tmp_files 를 지우면 안 된다 — 한때 원본 .v 경로가 담겨 있어 소스를 삭제했다.
#   각 함수의 finally 가 이미 임시본을 지우고 백업을 복원한다. 남은 백업만 되돌린다.
for _b in list(REPOS.rglob("*.?bak*")) + list(REPOS.rglob("*.v.*bak*")):
    try:
        _t = Path(str(_b).split(".v.")[0] + ".v") if ".v." in str(_b) else None
        if _t and not _t.exists():
            _b.rename(_t)
    except Exception:
        pass

print(f"\n■ {SPLIT} — assert 변환 동적 검증")
for k in sorted(stat, key=lambda x: -stat[x]):
    print(f"   {k:28s} {stat[k]:5d}")
n = max(stat["검증"], 1)
print(f"\n   변환 성공률(시도분): {stat['✓ 변환 성공']}/{n} = {stat['✓ 변환 성공']/n*100:.1f}%")
_att = stat["검증"] + stat["변환 포기(위험/불가)"]
print(f"   적용률(포기 포함)  : {n}/{_att} = {n/max(_att,1)*100:.1f}%"
      f"   — 포기 {stat['변환 포기(위험/불가)']}건")
if name_bad:
    print(f"\n   ■ ★★ 이름 침범 {len(name_bad)}건")
    for _nm, _t in name_bad[:10]:
        print(f"     {_nm}  ← {_t}")
else:
    print(f"\n   ✓ 이름 침범 0건 (state·앞증명·뒤증명·premise 전부 대조)")
if gate:
    print(f"\n   ■ 필터별 정확도 — 필터를 끄고 통과시킨 결과 (ASSERT_RISK=0)")
    _rs = sorted({k[0] for k in gate}, key=lambda r: -(gate[(r, "성공")] + gate[(r, "실패")]))
    print(f"     {'필터':44s} {'통과':>5s} {'실패':>5s} {'실패율':>7s}")
    for _r in _rs:
        _o, _x = gate[(_r, "성공")], gate[(_r, "실패")]
        print(f"     {_r:44s} {_o+_x:5d} {_x:5d} {_x/max(_o+_x,1)*100:6.1f}%")
if why:
    print(f"\n   ■ 포기 이유 (많은 순)")
    for _k, _v in why.most_common(20):
        print(f"     [{_v:4d}] {_k}")
if errs:
    print(f"\n   ■ 실패 유형 (많은 순)")
    for k, v in errs.most_common(12):
        print(f"   [{v:3d}회] {k}")
        for tac, head, msg in samples[k][:1]:
            print(f"          원래: {tac}")
            print(f"          변환: {head}")
            print(f"          오류: {msg}")
