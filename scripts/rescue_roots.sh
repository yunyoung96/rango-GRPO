#!/bin/bash
# ★ 루트명 자동수정 재빌드 — 실패 저장소의 에러("bound to logical path R.x")에서 기대 루트 R 을 읽어
#   `-R <디렉토리|.> R` 로 _CoqProject 를 다시 쓰고 재빌드한다. 성공 시 campaign jsonl 갱신은 별도 스크립트.
cd /app/coq-modeling/tmp/tr
for d in "$@"; do
  [ -d "$d" ] || continue
  echo "== $d"
  roots=$(cd $d && timeout 60 make -k 2>&1 | grep -o 'bound to logical path [A-Za-z][A-Za-z0-9_]*' | awk '{print $NF}' | sort | uniq -c | sort -rn | awk '$1>=1 {print $2}' | head -3)
  [ -n "$roots" ] || { echo "  기대 루트 없음 — 건너뜀"; continue; }
  cd $d
  for f in Makefile Makefile.conf .Makefile.d _CoqProject; do [ -f $f ] && mv $f $f.rootbak; done
  find . \( -name '*.vo' -o -name '*.vos' -o -name '*.vok' -o -name '*.glob' -o -name '*.aux' \) -delete
  { for r in $roots; do if [ -d "$r" ]; then echo "-R $r $r"; else echo "-R . $r"; fi; done
    find . -name '*.v' -not -path './.git/*' | sed 's|^\./||' | sort; } > _CoqProject
  head -3 _CoqProject | tr '\n' ' '; echo
  coq_makefile -f _CoqProject -o Makefile 2>/dev/null && timeout 1500 make -j3 -k > build_root.log 2>&1
  echo "  결과 vo=$(find . -name '*.vo' | wc -l) / v=$(find . -name '*.v' -not -path './.git/*' | wc -l)"
  cd /app/coq-modeling/tmp/tr
done
echo "RESCUE_ROOTS_DONE"
