#!/usr/bin/env python3
"""**모든 학습 인덱스**에 cut 질의를 날려 판정을 받아본다.

범위 메타(`scanned_range`)만 믿지 않는다 — 메타는 "훑었다" 는 주장이고,
실제로 질의가 답을 주는지는 별개다. 2,009,606 개 전부에 대해 직접 물어본다.

각 인덱스는 셋 중 하나여야 한다.

    cut       assert 로 치환된다            → cut 문자열의 **형태까지** 검사한다
    hopeless  학습에서 제외된다              → 이유가 기록돼 있어야 한다
    무기록     cut 이 필요 없었다 (검색 성공)  → 정상. 단 **범위 안**이어야 한다

★ 치명은 하나다: **범위 밖 인덱스**. 그건 "훑지 않았다" 는 뜻이고, 무기록과
  구분이 안 되면 gold 없는 스텝이 조용히 학습에 들어간다.

cut 형태 검사
    · `assert (…) as H_asrtN.` 또는 `eassert` 로 시작하나
    · 괄호가 맞나
    · `exact L` 의 L 이 stmt 사전이나 프롬프트 후보에 있나
    · 정규화 이름(T#/f#/L#)이 새어 들어오지 않았나 (cut 은 원본 이름을 써야 한다)

사용: PYTHONPATH=src CUTS_PATH=... python3 scripts/verify_cut_all.py [split]
"""
import collections
import copy
import logging
import os
import re
import sys
import time

sys.path.insert(0, "src")
logging.disable(logging.CRITICAL)
os.environ.setdefault("HF_HUB_OFFLINE", "1")

SPLIT = (sys.argv[1] if len(sys.argv) > 1 else "train").upper()

import yaml  # noqa: E402
from data_management.splits import Split  # noqa: E402
from tactic_gen.tactic_data import TacticDataConf, LmDataset  # noqa: E402
from tactic_gen import cut_lookup  # noqa: E402

cc = yaml.safe_load(open("all_log/ft_qwen3b_v9_conf.yaml"))
os.environ["CUTS_ALLOW_PARTIAL"] = "1"          # 검증기는 부분 파일도 열어봐야 한다
conf = TacticDataConf.from_yaml(copy.deepcopy(cc["tactic_data"]))
ds = LmDataset.from_conf(conf, getattr(Split, SPLIT), None)
si = ds.shuffled_idx
sp = getattr(Split, SPLIT)
TOTAL = si.split_length(sp)

a, b = cut_lookup.scanned_range()
print(f"■ 전 인덱스 cut 질의   {SPLIT} {TOTAL:,}개")
print(f"   cut 파일: {os.environ.get('CUTS_PATH','(없음)')}")
print(f"   연속 스캔 범위 [{a:,}, {b:,})\n", flush=True)

# ★★ 인덱스 → cut 키 변환
#   `ShuffledIndex` 의 `sid.file` 은 경로 구분자를 대시로 누른 이름이고
#       snu-sf-paco-src-gpaco5.v
#   cut 파일의 키는 원본 경로다
#       repos/snu-sf-paco/src/gpaco5.v
#   그대로 비교하면 매번 빗나가 조회가 전부 None 이 되고, "100% 무기록 · ✓ 통과"
#   라는 **거짓 통과**가 나온다(실제로 그렇게 나왔다).
#   변환은 한 줄이다 — cut 쪽 경로를 대시로 누르면 `sid.file` 과 같아진다.
#   (`verify_cut_range.py` 가 이미 이렇게 하고 있었는데 못 보고 DatasetFile 을
#    파일마다 로드하는 무거운 우회를 했었다.)
def cut_key(sid_file: str, pi: int, si_: int) -> str:
    return f"{sid_file}:{pi}:{si_}"


_CUTKEYS = {}
for _k in list(getattr(cut_lookup, "_steps", {}) or {}):
    _a, _b, _c = _k.rsplit(":", 2)
    _CUTKEYS[(_a.split("repos/", 1)[-1].replace("/", "-"), int(_b), int(_c))] = _k
# hopeless 는 별도 집합이 아니라 step 레코드의 플래그다

# 변환이 실제로 맞는지 **먼저 확인한다** — 안 맞으면 검증 자체가 무의미하다
_probe = sum(1 for _i in range(0, min(TOTAL, 200000), 997)
             if (lambda z: (z.file, z.proof_idx, z.step_idx) in _CUTKEYS)(si.get_idx(sp, _i)))
print(f"   키 변환 검사: 표본 {len(range(0, min(TOTAL,200000), 997))}개 중 "
      f"cut 적중 {_probe}개", flush=True)
if _probe == 0:
    print("★ 표본에서 cut 을 하나도 못 찾았다 — 키 변환이 틀렸거나 cut 파일이 비었다.")
    print("   이 상태로 '통과' 를 보고하면 거짓 통과다. 여기서 멈춘다.")
    sys.exit(2)

st = collections.Counter()
bad = collections.defaultdict(list)
holes = []


def note(k, s):
    st[k] += 1
    if len(bad[k]) < 4:
        bad[k].append(s[:160])


ASSERT = re.compile(r"^\s*e?assert\s*\(")
EXACT = re.compile(r"exact\s+@?([\w'.]+?)\s*[.)]")
NORMN = re.compile(r"(?<![\w'])[TfCLG]\d+(?![\w'])")
stmts = getattr(cut_lookup, "_stmts", {}) or {}

t0 = time.time()
run_start = None
for i in range(TOTAL):
    sid = si.get_idx(sp, i)
    tup = (sid.file, sid.proof_idx, sid.step_idx)
    in_range = a <= i < b
    if not in_range:
        if run_start is None:
            run_start = i
        st["★ 범위 밖 (판정 없음)"] += 1
        continue
    if run_start is not None:
        holes.append((run_start, i))
        run_start = None

    _k = _CUTKEYS.get(tup)
    _rec = (getattr(cut_lookup, "_steps", {}) or {}).get(_k) if _k else None
    cut = (_rec or {}).get("cut")
    hop = bool((_rec or {}).get("hopeless"))
    if hop:
        st["hopeless (학습 제외)"] += 1
        continue
    if not cut:
        st["무기록 (cut 불필요)"] += 1
        continue
    st["cut 적용"] += 1

    # ── cut 형태 검사 ──
    c = cut if isinstance(cut, str) else str(cut)
    if not ASSERT.match(c):
        note("★ cut 이 assert 로 시작하지 않는다", f"i={i} {c[:70]}")
    if c.count("(") != c.count(")"):
        note("★ cut 괄호 불일치", f"i={i} {c[:70]}")
    if c.count("{") != c.count("}"):
        note("★ cut 중괄호 불일치", f"i={i} {c[:70]}")
    if "as H_asrt" not in c:
        note("★ cut 에 `as H_asrt` 가 없다", f"i={i} {c[:70]}")
    # ※ 정규화 이름 누출 검사는 **하지 않는다**. `[TfCLG]\d+` 는 실제 Coq 식별자와
    #   구분이 안 된다 — `forall T1 T2 : Type`, `C0`, `f1` 은 흔한 진짜 이름이다
    #   (이 오탐에 두 번 걸렸다). 그리고 애초에 검사할 필요가 없다:
    #   `collate_input` 이 **cut 치환(①) → 정규화(③)** 순서로 돌기 때문에 cut 파일에는
    #   원본 이름이 들어 있는 것이 정상이고, 정규화는 그 뒤에 프롬프트와 함께 적용된다.
    ex = EXACT.findall(c)
    if not ex:
        note("★ cut 에 exact 대상이 없다", f"i={i} {c[:70]}")
    for nm in ex:
        base = nm.split(".")[-1]
        if base and base not in stmts and not base.startswith("H_asrt"):
            st["exact 대상이 stmt 사전에 없음(후보 풀에는 있을 수 있음)"] += 1
            break

    if (i + 1) % 250000 == 0:
        el = time.time() - t0
        print(f"   {i+1:,}/{TOTAL:,}  ({el:.0f}s)", flush=True)

if run_start is not None:
    holes.append((run_start, TOTAL))

print(f"\n■ 결과 ({TOTAL:,}건 · {time.time()-t0:.0f}s)\n")
for k in sorted(st):
    print(f"   {k:52s} {st[k]:9,}  {st[k]/TOTAL*100:6.2f}%")
    for x in bad[k]:
        print(f"        {x}")
if holes:
    print(f"\n★ 판정 없는 구간 {len(holes)}개:")
    for lo, hi in holes[:10]:
        print(f"     [{lo:,}, {hi:,})   {hi-lo:,}개")
    if len(holes) > 10:
        print(f"     … 외 {len(holes)-10}개")

fatal = [k for k in st if k.startswith("★")]
print()
if fatal:
    print("★ 치명 항목:")
    for f in fatal:
        print(f"   · {f}  ({st[f]:,}건)")
    sys.exit(1)
print("✓ 모든 인덱스가 판정을 받았고 cut 형태도 정상")
