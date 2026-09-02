#!/bin/bash
# ★ 상시 데이터 구제 스캔 (사용자 2026-09-02 밤 지시: "살릴 수 있는지 계속 검사") —
#   캠페인에서 vo<50% 로 남은 저장소를 하나씩: ① 기대루트 × 소스디렉토리(-R src|theories|Code <Root>) 재빌드
#   ② dune-project 면 잔해 청소 후 dune build (산출은 트리에 복사) ③ coqdep 결핍 라이브러리 탐지 →
#   화이트리스트(opam 순수 추가 확인 시)만 설치 후 재빌드. 결과는 저장소별 판정으로 남긴다.
cd /app/coq-modeling
say(){ echo "[$(date '+%m-%d %H:%M')] $*"; }
WHITELIST="coq-paco coq-stdpp coq-mathcomp-ssreflect coq-itauto coq-equations coq-flocq"
R=/app/coq-modeling/tmp/tr

python3 - <<'PY' > /tmp/rescue_targets.txt
import json, os
skip={"snu-sf-paco","DonaldKellett-iron-lambda","uds-psl-coq-synthetic-incompleteness"}   # 판정완료+복원중
for l in open("all_log/train_build_campaign.jsonl"):
    r=json.loads(l)
    if r["proj"] in skip: continue
    if r.get("v",0) and r.get("vo",0) < 0.5*r["v"] and os.path.isdir(f"/app/coq-modeling/tmp/tr/{r['proj']}"):
        print(r["proj"])
PY
say "대상 $(wc -l < /tmp/rescue_targets.txt)개"

while read d; do
  cd $R/$d || continue
  vo0=$(find . -name '*.vo' -not -path './_build/*' | wc -l)
  say "== $d (vo=$vo0)"
  if [ "$vo0" -ge 20 ] && [ ! -f dune-project ]; then say "   $d: 이미 vo≥20 — 건너뜀(파괴/경쟁 방지)"; cd /app/coq-modeling; continue; fi
  # ① 기대 루트 추출 → 소스 디렉토리 매핑 재빌드
  roots=$(timeout 60 make -k 2>&1 | grep -o 'bound to logical path [A-Za-z][A-Za-z0-9_]*' | awk '{print $NF}' | sort -u | head -2)
  if [ -n "$roots" ] && [ "$vo0" -lt 20 ]; then    # 이미 20+ 빌드된 저장소는 건드리지 않는다 (파괴 방지)
    tar czf /tmp/scan_vo_snap.tgz $(find . -name '*.vo' -not -path './_build/*') 2>/dev/null
    for f in Makefile Makefile.conf .Makefile.d _CoqProject; do [ -f $f ] && mv -f $f $f.scanbak; done
    find . \( -name '*.vo' -o -name '*.vos' -o -name '*.vok' -o -name '*.glob' -o -name '*.aux' \) -not -path './_build/*' -delete
    { for r0 in $roots; do
        if [ -d theories ]; then echo "-R theories $r0"; elif [ -d src ]; then echo "-R src $r0";
        elif [ -d Code ]; then echo "-R Code $r0"; elif [ -d "$r0" ]; then echo "-R $r0 $r0"; else echo "-R . $r0"; fi
      done | sort -u
      find . -name '*.v' -not -path './.git/*' -not -path './_build/*' | sed 's|^\./||' | sort; } > _CoqProject
    coq_makefile -f _CoqProject -o Makefile 2>/dev/null && timeout 1500 make -j2 -k > scan_build.log 2>&1
  fi
  vo1=$(find . -name '*.vo' -not -path './_build/*' | wc -l)
  if [ "$vo1" -lt "$vo0" ]; then say "   $d: 재빌드가 나빠짐 ($vo0→$vo1) — 스냅샷 복원"; tar xzf /tmp/scan_vo_snap.tgz 2>/dev/null; vo1=$vo0; fi
  # ② dune 경로
  if [ -f dune-project ] && [ "$vo1" -lt 20 ]; then
    find . \( -name '*.glob' -o -name '*.vo' -o -name '*.vok' -o -name '*.vos' -o -name '*.aux' \) -not -path './_build/*' -delete
    timeout 1200 dune build > scan_dune.log 2>&1
    # 산출을 트리로 복사 (경로 미러)
    if [ -d _build/default ]; then
      (cd _build/default && find . -name '*.vo' | while read f; do cp -f "$f" "$R/$d/${f#./}" 2>/dev/null; done)
    fi
  fi
  vo2=$(find . -name '*.vo' -not -path './_build/*' | wc -l)
  # ③ 결핍 라이브러리 (보고 위주 · 화이트리스트만 설치)
  miss=$(timeout 40 make -k 2>&1 | grep -o 'Unable to locate library [A-Za-z][A-Za-z0-9_.]*' | awk '{print $NF}' | cut -d. -f1 | sort -u | head -3)
  say "   $d: vo $vo0 → $vo2  (결핍: ${miss:-없음})"
  cd /app/coq-modeling
  python3 - "$d" "$vo2" <<'PY'
import json, sys
proj, vo = sys.argv[1], int(sys.argv[2])
rows=[json.loads(l) for l in open("all_log/train_build_campaign.jsonl")]
for r in rows:
    if r["proj"]==proj and vo > r.get("vo",0): r["vo"]=vo; r["route"]=r.get("route",[])+["scan구제"]
open("all_log/train_build_campaign.jsonl","w").write("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in rows))
PY
done < /tmp/rescue_targets.txt
say "스캔 1순회 종료"
echo "RESCUE_SCAN_DONE"
