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
from tactic_gen.assert_split import transform  # noqa: E402

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

    def check_types(names):
        """★ `Check L.` 로 **Coq 이 보는 실제 타입**을 얻는다.

        sentences.db 의 텍스트는 **Section 안의 원문**이라 Section 변수(`insT`, `A` …)가
        그대로 들어 있다. Section 밖에서는 그것들이 인자로 바뀌므로 원문을 그대로 assert
        하면 `The variable insT was not found` 로 깨진다(실측 최다 유형).
        Coq 에게 물어보면 정확한 타입을 준다.
        """
        f = vf.parent / f"_hc_{os.getpid()}.v"
        tmp_files.append(f)
        out = {}
        try:
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
        return out

    def try_proof(body: str, tag: str):
        f = vf.parent / f"_ha_{tag}_{os.getpid()}.v"
        tmp_files.append(f)
        try:
            f.write_text(src[:at] + body + "\n")
            cf = CoqFile(str(f), timeout=180, workspace=ws)
            cf.run()
            out = [getattr(d, "message", "") for d in cf.errors]
            cf.close()
            return out
        except Exception as ex:
            return [f"예외: {ex}"]
        finally:
            f.unlink(missing_ok=True)

    e0 = try_proof(script + "\n" + tac, "o")
    if e0:
        stat["원본이 이미 오류(스킵)"] += 1
        continue

    # Coq 이 보는 실제 타입으로 assert 한다 (Section 변수·암묵인자가 정리된 형태)
    types = check_types([n for n, _ in pick])
    pick2 = []
    for nm, ptext in pick:
        ty = types.get(nm.split(".")[-1])
        if ty:
            pick2.append((nm, f"Lemma {nm.split('.')[-1]} : {ty}."))
        else:
            pick2.append((nm, ptext))
    stat["Check 로 타입 획득"] += sum(
        1 for nm, _ in pick if types.get(nm.split(".")[-1]))
    tr = transform(tac, pick2, proof_script=script, state=st)
    if tr is None:
        stat["변환 불가(정의/치환실패)"] += 1
        continue
    e1 = try_proof(script + "\n" + tr, "t")
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
print(f"\n   변환 성공률: {stat['✓ 변환 성공']}/{n} = {stat['✓ 변환 성공']/n*100:.1f}%")
if errs:
    print(f"\n   ■ 실패 유형 (많은 순)")
    for k, v in errs.most_common(12):
        print(f"   [{v:3d}회] {k}")
        for tac, head, msg in samples[k][:1]:
            print(f"          원래: {tac}")
            print(f"          변환: {head}")
            print(f"          오류: {msg}")
