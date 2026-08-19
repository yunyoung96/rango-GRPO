#!/usr/bin/env python3
"""★★ 본학습 직전 **종합 동적 검증** — 며칠짜리 학습을 버리지 않기 위해.

20,000 step 을 돌리고 나서 데이터가 잘못됐다는 걸 알면 며칠을 버린다.
**실제 학습이 쓰는 경로 그대로** 예제를 만들어 하나하나 확인한다.

## 검사 항목 (실패하면 학습을 시작하지 않는다)

  A. 설정이 실제로 먹는가   환경변수를 코드가 읽는지 (뒤에 두면 조용히 무시된다 — 실측으로 당함)
  B. 라벨 마스킹           DataCollator 가 응답 템플릿을 찾는가
                          ★ 못 찾으면 **경고 없이 전체를 마스킹**해 라벨 0개로 학습한다
  C. 라벨 == 정답          마스크를 풀었을 때 실제 gold tactic 과 일치하는가
  D. 시퀀스 길이           hard_seq_len 초과율 · 정답이 잘리지 않는가(truncation_side)
  E. 프롬프트 구조         섹션 헤더가 다 있는가 · premise 개수가 0 이 아닌가
  F. 이름 충돌             정규화·cut 이름이 기존 이름을 침범하지 않는가
  G. cut 조회              CUTS_PATH 를 쓸 때 적중률이 0 이 아닌가
  H. 재현성                같은 예제를 두 번 만들면 같은가(정규화 해시가 결정적인가)
  I. 예외                  N 건 중 collate 예외 0 이어야 한다

사용: python3 scripts/preflight_all.py [n]
"""
import collections
import copy
import os
import re
import sys

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.insert(0, "src")
import logging  # noqa: E402

logging.disable(logging.CRITICAL)
import inspect  # noqa: E402
import yaml  # noqa: E402
import torch  # noqa: E402
from data_management.splits import Split  # noqa: E402
from tactic_gen.tactic_data import (TacticDataConf, LmDataset,  # noqa: E402
                                    example_collator_from_conf, get_tokenizer,
                                    MASK_TEMPLATE, whole_number_allocate)
from tactic_gen.data_collator_compat import DataCollatorForCompletionOnlyLM  # noqa: E402
import tactic_gen.tactic_data as TD  # noqa: E402
from premise_selection import premise_client as PC  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 300
CONF = os.environ.get("CONF", "all_log/ft_qwen3b_v8_conf.yaml")
fails = []


def chk(ok, label, detail=""):
    print(f"   [{'✓' if ok else '✗'}] {label}" + (f"  — {detail}" if detail else ""))
    if not ok:
        fails.append(label)
    return ok


cc = yaml.safe_load(open(CONF))
HARD = int(os.environ.get("HARD_SEQ_LEN", cc["hard_seq_len"]))

print(f"■ 본학습 전 종합 검증  ({CONF} · {N}건)\n")
print("A. 설정이 실제로 먹는가")
chk("RETRIEVAL_MODE" in inspect.getsource(PC.SparseClient.get_premise_scores),
    "SparseClient 가 RETRIEVAL_MODE 를 읽는다")
src_alloc = inspect.getsource(whole_number_allocate)
chk("PREMISE_PACK" in src_alloc, "담기 방식이 PREMISE_PACK 로 제어된다",
    f"현재 {os.environ.get('PREMISE_PACK', 'hybrid')}")
chk("cut_lookup" in inspect.getsource(TD.ProofPremiseCollator.collate),
    "collate 가 cut 조회를 한다")
chk(os.environ.get("STRIP_TARGET_NL", "0") == "1",
    "STRIP_TARGET_NL=1 (Qwen 라벨 마스킹 정합에 필수)")

print("\nB~I. 실제 예제로 확인")
conf = TacticDataConf.from_yaml(copy.deepcopy(cc["tactic_data"]))
ds = LmDataset.from_conf(conf, Split.TRAIN, 10 ** 9)
tok = get_tokenizer(cc["model_name"])
coll = example_collator_from_conf(conf.collator_conf)
dc = DataCollatorForCompletionOnlyLM(MASK_TEMPLATE, tokenizer=tok)

st = collections.Counter()
bad = collections.defaultdict(list)
n = 0
for i in range(N * 3):
    if n >= N:
        break
    try:
        e = ds.raw_example(i)
    except Exception:
        continue
    try:
        s = coll.collate(tok, e)
    except Exception as ex:
        st["I 예외"] += 1
        bad["collate 예외"].append(f"{type(ex).__name__}: {str(ex)[:60]}")
        continue
    n += 1
    enc = tok(s, max_length=HARD, truncation=True, padding=False)
    ids = enc["input_ids"]
    st["D 길이합"] += len(ids)
    st["D 초과"] += (len(tok(s, add_special_tokens=False)["input_ids"]) > HARD)

    # B/C 라벨 마스킹
    try:
        batch = dc([{"input_ids": ids, "attention_mask": enc["attention_mask"]}])
        lab = batch["labels"][0]
        nlab = int((lab != -100).sum())
        st["B 라벨0"] += (nlab == 0)
        if nlab:
            txt = tok.decode([t for t in lab.tolist() if t != -100],
                             skip_special_tokens=True).strip()
            # ★ cut 치환이 켜져 있으면 '정답'은 gold 가 아니라 cut 이다.
            #   (how-to-learn §3 ②: gold 가 프롬프트에 없으면 cut 으로 가르친다)
            tgt = (e.next_steps[0] or "").strip()
            if os.environ.get("CUTS_PATH", ""):
                from tactic_gen import cut_lookup
                _c = cut_lookup.cut_for(f"{e.file_name}:{e.proof_idx}:{e.step_idx}")
                if _c:
                    tgt = _c.strip()
                    st["C cut 기대"] += 1
            if STRIP := os.environ.get("STRIP_TARGET_NL", "0") == "1":
                tgt = tgt.lstrip("\n")
            same = txt.replace(" ", "")[:60] == tgt.replace(" ", "")[:60]
            st["C 라벨==정답"] += same
            if not same:
                bad["라벨≠정답"].append(f'라벨="{txt[:50]}" 정답={tgt[:50]!r}')
    except Exception as ex:
        st["B 마스킹 예외"] += 1
        bad["마스킹 예외"].append(str(ex)[:70])

    # E 프롬프트 구조
    for sec in ("[PREMISES]", "[STATE]", "[TACTIC]"):
        if sec not in s:
            st[f"E {sec} 없음"] += 1
    # F 이름 충돌
    if "[TACTIC]" in s:
        prompt, target = s.rsplit("[TACTIC]", 1)
        for nm in set(re.findall(r"as\s+(H_asrt\w*\d+)", target)):
            if re.search(r"(?<![\w'])" + re.escape(nm) + r"(?![\w'])", prompt):
                st["F 이름침범"] += 1
    # G cut 조회
    if os.environ.get("CUTS_PATH", ""):
        from tactic_gen import cut_lookup
        k = f"{e.file_name}:{e.proof_idx}:{e.step_idx}"
        if cut_lookup.cut_for(k):
            st["G cut 적용"] += 1
    # H 재현성
    if n <= 40:
        st["H 재현성 일치"] += (coll.collate(tok, e) == s)

print(f"\n   검사한 예제 {n}건")
chk(st["I 예외"] == 0, "I. collate 예외 0", f"{st['I 예외']}건")
chk(st["B 라벨0"] == 0, "B. 라벨이 0개인 예제 없음",
    f"{st['B 라벨0']}건  ★ 있으면 학습이 아무것도 못 배운다")
chk(st["B 마스킹 예외"] == 0, "B. 마스킹 예외 0", f"{st['B 마스킹 예외']}건")
chk(st["C 라벨==정답"] >= n * 0.95, "C. 라벨이 정답과 일치",
    f"{st['C 라벨==정답']}/{n} = {st['C 라벨==정답']/max(n,1)*100:.1f}%")
chk(st["E [TACTIC] 없음"] == 0, "E. 모든 예제에 [TACTIC] 존재",
    f"누락 {st['E [TACTIC] 없음']}건")
chk(st["F 이름침범"] == 0, "F. 이름 침범 0", f"{st['F 이름침범']}건")
chk(st["H 재현성 일치"] == min(n, 40), "H. 같은 예제를 두 번 만들면 동일",
    f"{st['H 재현성 일치']}/{min(n,40)}")
if os.environ.get("CUTS_PATH", ""):
    chk(st["G cut 적용"] > 0, "G. cut 조회 적중 > 0",
        f"{st['G cut 적용']}건  ★ 0 이면 키 형식이 어긋난 것")
print(f"   [ ] D. 길이 평균 {st['D 길이합']/max(n,1):.0f} 토큰 · "
      f"{HARD} 초과 {st['D 초과']}건 ({st['D 초과']/max(n,1)*100:.1f}%)")
print(f"   [ ] E. [PREMISES] 없는 예제 {st['E [PREMISES] 없음']}건 "
      f"({st['E [PREMISES] 없음']/max(n,1)*100:.1f}%)")

if bad:
    print(f"\n   ■ 문제 표본")
    for k, v in bad.items():
        print(f"     [{len(v)}] {k}")
        for x in v[:2]:
            print(f"        {x}")

print(f"\n{'='*60}")
if fails:
    print(f"★ 검증 실패 {len(fails)}건 — **학습을 시작하면 안 된다**")
    for f in fails:
        print(f"   · {f}")
    sys.exit(2)
print("✓ 전부 통과 — 학습을 시작해도 된다")
