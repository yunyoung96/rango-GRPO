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

TRAIN 프로젝트는 원본 .v 가 없어 Coq 을 못 돌린다. **VAL/TEST 프로젝트**(CoqStoq 에 소스가
있다)에서 검증하고, 거기서 잡은 규칙을 TRAIN 정적 변환에 반영한다.

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
from tactic_gen.assert_split import (transform, extract_application,  # noqa: E402
                                     transform_with_types)

NSTEP = int(sys.argv[1]) if len(sys.argv) > 1 else 40
SPLIT = (sys.argv[2] if len(sys.argv) > 2 else "test").upper()
REPOS = Path(f"CoqStoq/{SPLIT.lower()}-repos")

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
            tmp_files.append(f)
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
                    got.append(" ".join(mm.group(2).split()))
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
            tmp_files.append(f)
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
                    got.append(" ".join(mm.group(2).split()))
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
            tmp_files.append(f)
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
            tmp_files.append(vf)
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

    # ── ① 적용 항 전체를 뽑아 그 타입을 Coq 에 묻는다 (인자 개수 문제 원천 제거) ──
    terms = []
    for nm, _pt in pick:
        r = extract_application(tac, nm)
        if r and r[0] not in terms:
            terms.append(r[0])
    tr = None
    if terms:
        tt = check_terms(terms)
        apps = [(t, tt.get(t)) for t in terms if tt.get(t)]
        stat["Check(항) 타입 획득"] += len(apps)
        if apps:
            tr = transform_with_types(tac, apps, state=st, proof_script=script)
    # ── ② 실패하면 lemma 이름만으로 (기존 방식) ──
    if tr is None:
        types = check_types([n for n, _ in pick])
        pick2 = [(nm, f"Lemma {nm.split('.')[-1]} : {ty}." if
                  (ty := types.get(nm.split('.')[-1])) else pt) for nm, pt in pick]
        stat["Check(이름) 폴백"] += 1
        tr = transform(tac, pick2, proof_script=script, state=st)
    if tr is None:
        stat["변환 포기(위험/불가)"] += 1
        continue
    e1 = try_proof(script + "\n" + tr, "t")
    # ★ notation 형태가 깨지면 **Printing All 형태**로 다시 시도한다.
    #   장황하지만 재파싱이 보장된다 — assert 를 아예 못 만드는 것보다 낫다.
    if e1 and terms:
        ta = check_terms_all(terms)
        apps2 = [(t, ta.get(t)) for t in terms if ta.get(t)]
        if apps2:
            tr2 = transform_with_types(tac, apps2, state=st, proof_script=script,
                                       skip_risk=True)
            if tr2:
                e2 = try_proof(script + "\n" + tr2, "t2")
                if not e2:
                    stat["★ PrintingAll 폴백으로 성공"] += 1
                    tr, e1 = tr2, e2
    stat["검증"] += 1
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

for f in tmp_files:
    try:
        f.unlink(missing_ok=True)
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
if errs:
    print(f"\n   ■ 실패 유형 (많은 순)")
    for k, v in errs.most_common(12):
        print(f"   [{v:3d}회] {k}")
        for tac, head, msg in samples[k][:1]:
            print(f"          원래: {tac}")
            print(f"          변환: {head}")
            print(f"          오류: {msg}")
