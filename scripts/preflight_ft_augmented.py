#!/usr/bin/env python3
"""rango-augmented 완전 재학습 **사전점검**(60k step 태우기 전 필수).

확인 항목:
  1. 코퍼스 존재(data_path 모드의 train.db/val.db/conf.yaml 또는 tactic_data 모드의 data_loc/sentence_db)
  2. 프롬프트가 실제로 증강되는가([TYPES] 섹션, premise 재랭킹) — env RERANK_PREMISES/INJECT_TYPES 반영
  3. **학습 타깃이 gold tactic 인가** — 롤아웃 유래 데이터는 next_steps 가 '\\nAdmitted.' 플레이스홀더라
     그대로 학습하면 loss 가 1e-4 로 떨어지며 아무것도 안 배운다(실제로 겪은 함정).
  4. 프롬프트 토큰 길이가 hard_seq_len 안에 들어오는가

사용: RERANK_PREMISES=1 INJECT_TYPES=1 python3 scripts/preflight_ft_augmented.py all_log/ft_rango_augmented_conf.yaml
"""
import os
import sys
import statistics
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.insert(0, "src")

import yaml   # noqa: E402

N_SAMPLE = int(os.environ.get("N_SAMPLE", "30"))
# ★ 진짜 위험한 것은 "모든 타깃이 같은 플레이스홀더"인 경우(롤아웃 유래 데이터의 '\nAdmitted.').
#   실제 코퍼스에서 `Qed.`/`Admitted.`는 **정당한 gold step**(증명 종료)이라 소수 존재가 정상.
#   → 비율로 판정한다(BAD_RATIO 초과 시에만 NO-GO).
BAD_TARGETS = {"\nAdmitted.", "Admitted.", ""}
BAD_RATIO = 0.5


def fail(msg):
    print(f"  ✗ {msg}")
    return False


def main():
    conf_path = sys.argv[1] if len(sys.argv) > 1 else "all_log/ft_rango_augmented_conf.yaml"
    conf = yaml.safe_load(open(conf_path))
    print(f"■ conf: {conf_path}")
    print(f"  증강 env: RERANK_PREMISES={os.environ.get('RERANK_PREMISES', '0')} "
          f"INJECT_TYPES={os.environ.get('INJECT_TYPES', '0')}")
    ok = True

    # 1) 코퍼스 존재
    if "data_path" in conf:
        dp = Path(conf["data_path"])
        for f in ("train.db", "val.db", "conf.yaml"):
            if not (dp / f).exists():
                ok = fail(f"코퍼스 파일 없음: {dp / f}")
        mode = "data_path(전처리 DB)"
    else:
        td = conf["tactic_data"]
        for key in ("data_loc", "sentence_db_loc", "shuffled_index_loc"):
            if not Path(td[key]).exists():
                ok = fail(f"코퍼스 경로 없음: {key}={td[key]}")
        mode = "tactic_data(on-the-fly 검색)"
    print(f"  모드: {mode}")
    if not ok:
        print("\n★ NO-GO — 코퍼스부터 복원하세요.")
        return 1

    # 2~4) 실제 데이터셋을 열어 프롬프트/타깃 검사
    from tactic_gen.tactic_data import (      # noqa: E402
        LmProcessedDataset, LmDataset, TacticDataConf,
        example_collator_conf_from_yaml, example_collator_from_conf, get_tokenizer,
    )
    from data_management.splits import Split  # noqa: E402

    tok = get_tokenizer(conf["model_name"])
    if "data_path" in conf:
        col = example_collator_from_conf(example_collator_conf_from_yaml(conf["example_collator"]))
        ds = LmProcessedDataset(Path(conf["data_path"]) / "train.db", tok, col,
                                conf["hard_seq_len"])
        hard_seq_len = conf["hard_seq_len"]

        def raw_example(i):
            import json
            from tactic_gen.lm_example import LmExample
            return LmExample.from_json(json.loads(ds.edb.retrieve(ds.edb_map[i] + 1)))
    else:
        dsconf = TacticDataConf.from_yaml(conf["tactic_data"])
        ds = LmDataset.from_conf(dsconf, Split.TRAIN)
        col = ds.example_collator
        hard_seq_len = conf["tactic_data"]["hard_seq_len"]

        def raw_example(i):
            return ds.raw_example(i)

    print(f"  train 예제 수: {len(ds)}")

    n_types, n_defs, n_proj, n_bad_target, plens, tlens = 0, 0, 0, 0, [], []
    for i in range(min(N_SAMPLE, len(ds))):
        ex = raw_example(i)
        if ex is None:
            continue
        prompt = col.collate_input(tok, ex)
        target = (ex.next_steps or [""])[0]
        if "[TYPES]" in prompt:
            n_types += 1
        if "[DEFINITIONS]" in prompt:
            n_defs += 1
        if getattr(ex, "file_name", None):
            n_proj += 1
        if target in BAD_TARGETS:
            n_bad_target += 1
        plens.append(len(tok(prompt, add_special_tokens=False)["input_ids"]))
        tlens.append(len(tok(target, add_special_tokens=False)["input_ids"]))

    if plens:
        print(f"  프롬프트 토큰: 중앙 {statistics.median(plens):.0f} 최대 {max(plens)} "
              f"(hard_seq_len {hard_seq_len}, 초과 {sum(1 for x in plens if x > hard_seq_len)}건)")
        print(f"  [TYPES] 주입률: {n_types}/{len(plens)}")
        print(f"  [DEFINITIONS] 주입률: {n_defs}/{len(plens)}")
        print(f"  file_name(프로젝트 판별) 있는 예제: {n_proj}/{len(plens)}")
        print(f"  타깃 토큰: 중앙 {statistics.median(tlens):.0f}")
    if plens and n_bad_target / len(plens) > BAD_RATIO:
        ok = fail(f"학습 타깃이 플레이스홀더인 예제 {n_bad_target}/{len(plens)}건 "
                  f"(next_steps='Admitted.' 류). 이 데이터로 학습하면 loss 만 0 으로 떨어지고 학습 안 됨.")
    else:
        print(f"  ✓ 타깃 정상(플레이스홀더 {n_bad_target}/{len(plens)}건 — 소수는 정상)")
    if os.environ.get("INJECT_TYPES") == "1" and n_types == 0:
        ok = fail("INJECT_TYPES=1 인데 [TYPES] 섹션이 하나도 없음 — 인덱스(IND_INDEX_PATH) 확인")

    print("\n" + ("★ GO — 학습 시작 가능: bash all_log/ft_rango_augmented.sh" if ok else "★ NO-GO"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
