#!/usr/bin/env python3
"""기존 all_results/<timestamp> 디렉토리를 <timestamp>_<alias> 로 일괄 rename.
summary.json의 architecture를 alias로 사용. 이미 _alias 붙은 것/실행중인 것은 스킵.
사용: python3 scripts/rename_all_results.py         # dry-run(미리보기)
     python3 scripts/rename_all_results.py --apply  # 실제 rename
"""
import json, re, sys
from pathlib import Path

apply = "--apply" in sys.argv
root = Path("all_results")
renamed = skipped = 0
for d in sorted(root.iterdir()):
    if not d.is_dir():
        continue
    name = d.name
    # 이미 _alias 형태면(타임스탬프_문자) 스킵
    if re.match(r"^\d{8}-\d{6}_", name):
        skipped += 1
        continue
    if not re.match(r"^\d{8}-\d{6}$", name):
        skipped += 1
        continue
    sp = d / "summary.json"
    if not sp.exists():
        skipped += 1
        continue
    try:
        alias = json.load(open(sp)).get("architecture", "unknown")
    except Exception:
        skipped += 1
        continue
    safe = re.sub(r"[^A-Za-z0-9._-]", "-", str(alias))
    target = d.with_name(f"{name}_{safe}")
    if target.exists():
        print(f"  SKIP(충돌) {name} → {target.name}")
        skipped += 1
        continue
    print(f"  {'RENAME' if apply else 'DRY'} {name} → {target.name}")
    if apply:
        d.rename(target)
    renamed += 1
print(f"\n{'적용' if apply else '미리보기'}: rename {renamed}, skip {skipped}")
