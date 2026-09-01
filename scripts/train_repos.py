#!/usr/bin/env python3
"""빌드된 TRAIN 저장소 REPOS 문자열 출력 — **VAL/TEST/CUTOFF(CoqStoq) 저장소는 제외** (누출 방지 단일 출처).
2026-09-02 03:5x 실측: 캠페인이 math-classes·fourcolor(TEST)·coqeal(VAL)·coq-ext-lib(TEST)를 TRAIN 으로 빌드해
수집까지 진행됐었다 — raw-data/coqstoq-{val,test,cutoff}/repos 디렉토리명 기준으로 접미사 일치 시 제외한다."""
import json, os, sys
R = "/app/coq-modeling/tmp/tr"
leak = set()
for d in ("raw-data/coqstoq-val/repos", "raw-data/coqstoq-test/repos", "raw-data/coqstoq-cutoff/repos"):
    if os.path.isdir(d): leak |= set(os.listdir(d))
assert {"math-classes", "fourcolor", "coqeal", "ext-lib"} <= leak, f"누출 목록 로드 실패: {sorted(leak)[:5]}"


#: 병리적 저장소 — 성능 테스트용(의도적으로 느린) Coq 파일 모음: 학습 가치 대비 수집 비용이 병적
PATHO = {"JasonGross-slow-coq-examples", "JasonGross-category-coq-experience-tests",
         "Kevin-TD-coq_learning"}   # 생존 3.2% (수집 결함 의심 — train_pool assert 발동, 2026-09-02)


def leaky(proj):
    if proj in PATHO: return True
    p = proj.lower()
    return any(p == n or p.endswith("-" + n) or p.endswith("-coq-" + n) for n in (x.lower() for x in leak))


assert leaky("coq-community-math-classes") and leaky("coq-community-coqeal") and leaky("coq-community-coq-ext-lib") \
    and leaky("coq-community-fourcolor") and not leaky("coq-community-coq-art") and not leaky("zunction-casper-cbc-proofs")

if __name__ == "__main__":
    out = []; dropped = []
    for l in open("all_log/train_build_campaign.jsonl"):
        r = json.loads(l)
        if r.get("vo", 0) <= 0 or not os.path.isdir(f"{R}/{r['proj']}"): continue
        (dropped if leaky(r["proj"]) else out).append(r["proj"])
    print(",".join(f"{p}={R}/{p}" for p in out))
    print(f"제외(VAL/TEST/CUTOFF 누출 방지): {dropped}", file=sys.stderr)
