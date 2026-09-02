#!/bin/bash
# ★ 심층 구제 (2026-09-02 밤, 사용자 "어떻게든 컴파일" · 위험 감수) — 저장소의 **자기 빌드계**를 존중하는 재빌드.
#   synthetic 교훈: 내 생성 _CoqProject·stale wrong-root .vo 가 자기빌드를 poison 했다. → 원복+청소+자기빌드.
#   경계(불변): Coq/OCaml 버전은 안 바꾼다. opam 설치는 dry-run 이 coq/ocaml/coq-core/coq-stdlib 를 건드리면 거부.
#   전부 비파괴: 시작 전 .vo tar 스냅샷, 끝나서 나빠지면 복원.
cd /app/coq-modeling
say(){ echo "[$(date '+%m-%d %H:%M')] $*"; }
R=/app/coq-modeling/tmp/tr
SNAP=/tmp/rescue_deep_snap
mkdir -p $SNAP

# 의존 설치 (버전 가드) — 계획이 금지 패키지를 바꾸면 스킵
safe_install(){
  local pkg=$1
  local plan=$(opam install "$pkg" --show-actions 2>/dev/null | grep -v WARNING)
  echo "$plan" | grep -qE '(upgrade|downgrade|recompile|remove).*(coq |coq-core|coq-stdlib|ocaml )' && { say "   [opam] $pkg 스킵(코어 변경 계획)"; return 1; }
  echo "$plan" | grep -qE 'install|upgrade' || { say "   [opam] $pkg 이미 있음/불필요"; return 0; }
  # 설치 후에도 coq 버전 불변 확인
  local coq0=$(opam list --installed coq --columns=installed-version 2>/dev/null | tail -1)
  timeout 1800 opam install -y "$pkg" > /tmp/opam_$pkg.log 2>&1
  local coq1=$(opam list --installed coq --columns=installed-version 2>/dev/null | tail -1)
  if [ "$coq0" != "$coq1" ]; then say "   [opam] ★ coq 버전 변동 $coq0→$coq1 — 즉시 롤백"; opam install -y coq.$coq0 >/dev/null 2>&1; return 1; fi
  say "   [opam] $pkg 설치 완료"; return 0
}

for d in "$@"; do
  cd $R/$d 2>/dev/null || continue
  vo0=$(find . -name '*.vo' -not -path './_build/*' | wc -l)
  say "== $d (vo0=$vo0)"
  tar czf $SNAP/$d.tgz $(find . -name '*.vo' -not -path './_build/*') 2>/dev/null

  # ① 내가 남긴 생성 흔적 제거 + 원본 빌드파일 복원
  rm -f _CoqProject.scanbak _CoqProject.rootbak Makefile.rootbak Makefile.scanbak Makefile.conf.rootbak _CoqProject.prev .Makefile.d 2>/dev/null
  git checkout -- _CoqProject Makefile 2>/dev/null
  # stale .vo 전부 청소 (wrong-root poison 제거) — 스냅샷 있으니 안전
  find . \( -name '*.vo' -o -name '*.vos' -o -name '*.vok' -o -name '*.glob' -o -name '*.aux' \) -not -path './_build/*' -delete

  # ② opam 선언 의존 설치 (가드)
  for f in *.opam; do [ -f "$f" ] || continue
    for pkg in $(grep -oE '"coq-[a-z0-9-]+"' "$f" | tr -d '"' | sort -u); do safe_install "$pkg"; done
  done

  # ③ 빌드: 자기 _CoqProject > 자기 Makefile > dune
  built=0
  if [ -f _CoqProject ] && grep -qE '^\s*-[QR]' _CoqProject; then
    coq_makefile -f _CoqProject -o Makefile 2>/dev/null && timeout 1800 make -j3 -k > deep_build.log 2>&1 && built=1
  fi
  if [ "$built" = 0 ] && [ -f Makefile ]; then timeout 1800 make -j3 -k > deep_build.log 2>&1; fi
  vo1=$(find . -name '*.vo' -not -path './_build/*' | wc -l)
  if [ -f dune-project ] && [ "$vo1" -lt 20 ]; then
    timeout 1500 dune build > deep_dune.log 2>&1
    [ -d _build/default ] && (cd _build/default && find . -name '*.vo' | while read f; do mkdir -p "$R/$d/$(dirname ${f#./})"; cp -f "$f" "$R/$d/${f#./}" 2>/dev/null; done)
    vo1=$(find . -name '*.vo' -not -path './_build/*' | wc -l)
  fi

  # ④ 비파괴: 나빠지면 스냅샷 복원
  if [ "$vo1" -lt "$vo0" ]; then say "   나빠짐 $vo0→$vo1 — 스냅샷 복원"; tar xzf $SNAP/$d.tgz 2>/dev/null; vo1=$vo0; fi
  say "   $d: vo $vo0 → $vo1"
  cd /app/coq-modeling
  python3 - "$d" "$vo1" <<'PY'
import json, sys
proj, vo = sys.argv[1], int(sys.argv[2])
rows=[json.loads(l) for l in open("all_log/train_build_campaign.jsonl")]
ch=False
for r in rows:
    if r["proj"]==proj and vo>r.get("vo",0): r["vo"]=vo; r["route"]=r.get("route",[])+["deep구제"]; ch=True
if ch: open("all_log/train_build_campaign.jsonl","w").write("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in rows))
PY
done
say "심층 구제 종료"; echo "RESCUE_DEEP_DONE"
