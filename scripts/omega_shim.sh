#!/bin/bash
# ★ Omega 드리프트 소스 패치(위험 감수·비파괴 git) — Require ...Omega → Lia, omega. → lia.
#   Coq 8.18 에서 Omega 는 제거됨. Lia 가 상위호환이라 대개 통과. git 트리라 언제든 checkout 복원.
cd /app/coq-modeling/tmp/tr
for d in */; do d=${d%/}; [ -d "$d/.git" ] || continue
  grep -rlZ --include='*.v' -e 'Omega' -e '\bomega\b' "$d" 2>/dev/null | while IFS= read -r -d '' f; do
    sed -i -E 's/Require Import Omega/Require Import Lia/g; s/Require Export Omega/Require Export Lia/g; s/(From Coq Require Import )Omega/\1Lia/g; s/(^|[^A-Za-z_])omega\./\1lia./g' "$f"
  done
done
echo "OMEGA_SHIM_DONE"
