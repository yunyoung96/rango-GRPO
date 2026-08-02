#!/usr/bin/env python3
"""tst1000tr5091 split 재생성 (다른 서버 재현용). CoqStoq 필요.
CompCert 전체(6091정리) → 앞 1000 test / 나머지 5091 train 의 전역 idx 파일 생성.
사용: python3 scripts/build_tst_split.py [CoqStoq경로]"""
import sys
from pathlib import Path
sys.path.insert(0, 'src')
from coqstoq import get_theorem_list, Split

LOC = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("CoqStoq")

def main():
    lst = get_theorem_list(Split.TEST, LOC)
    cc = [i for i, t in enumerate(lst) if t.project.dir_name == 'compcert']
    test_idx, train_idx = cc[:1000], cc[1000:]
    assert not (set(test_idx) & set(train_idx)), "겹침 버그"
    open('data/compcert_tst1000tr5091_test_idx.txt', 'w').write('\n'.join(map(str, test_idx)) + '\n')
    open('data/compcert_tst1000tr5091_train_idx.txt', 'w').write('\n'.join(map(str, train_idx)) + '\n')
    print(f"CompCert {len(cc)}정리 → test {len(test_idx)} / train {len(train_idx)}")
    print("  data/compcert_tst1000tr5091_{test,train}_idx.txt 저장")
    print("  다음: python3 scripts/build_gold_trajectories.py --project compcert --start 1000 --num 5091 "
          "--out data/curriculum/gold_tst1000tr5091.json")

if __name__ == "__main__":
    main()
