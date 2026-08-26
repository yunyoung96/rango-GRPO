#!/usr/bin/env python3
"""지정한 (데이터포인트, proof_idx, step_idx) 의 **v9 추론 프롬프트**를 그대로 찍는다.

## 왜 따로 두나

`gen_prompt_comparison.py` 는 TRAIN 인덱스를 훑는다. 그런데 "왜 이 스텝을 못 푸나" 를
볼 때 보고 싶은 것은 **평가 대상(CompCert)의 특정 스텝**이다. 그건 TRAIN 에 없다.
그래서 학습 데이터셋을 거치지 않고 `GeneralFormatter` → `collate_input` 을
**추론과 같은 경로**로 직접 부른다.

## 학습 프롬프트와 다른 점은 하나뿐이다

정규화가 `NORMALIZE_INFERENCE` 경로(`_maybe_normalize_input`)로 걸린다 — 정답이
없으므로 프롬프트만 바꾸고 매핑을 남긴다. 학습(`collate`)은 정답에도 같은 매핑을 건다.

사용:
    PYTHONPATH=src python3 scripts/dump_one_prompt.py \
        /tmp/coq-dataset/data_points/AbsInt-CompCert-backend-Unusedglobproof.v 52 5 [출력디렉토리]
"""
import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, "src")
logging.disable(logging.CRITICAL)
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")

import yaml  # noqa: E402
import rango_defaults as _D  # noqa: E402
from data_management.dataset_file import DatasetFile  # noqa: E402
from data_management.sentence_db import SentenceDB  # noqa: E402
from tactic_gen.lm_example import (formatter_conf_from_yaml,  # noqa: E402
                                   formatter_from_conf)
from tactic_gen.tactic_data import (example_collator_conf_from_yaml,  # noqa: E402
                                    example_collator_from_conf, get_tokenizer,
                                    last_inference_mapping)

DP, PI, SI = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
OUT = Path(sys.argv[4]) if len(sys.argv) > 4 else None
CONF = os.environ.get("CONF", "all_log/ft_qwen3b_v9_conf.yaml")

cc = yaml.safe_load(open(CONF))
td = cc["tactic_data"]
tok = get_tokenizer(cc["model_name"])
sdb = SentenceDB.load(Path(td["sentence_db_loc"]))
dp = DatasetFile.load(Path(DP), sdb)
fmt = formatter_from_conf(formatter_conf_from_yaml(td["formatter_conf"]))
coll = example_collator_from_conf(example_collator_conf_from_yaml(td["collator_conf"]))

ex = fmt.example_from_step(SI, PI, dp, training=False)
norm = coll.collate_input(tok, ex, normalize=True)
mapping = last_inference_mapping()
# ★ 매핑을 먼저 읽고 나서 실명본을 만든다 — `collate_input` 이 전역을 덮어쓴다.
raw = coll.collate_input(tok, ex, normalize=False)

ntok = len(tok(norm, add_special_tokens=False)["input_ids"])
print("=" * 78)
print(f"■ 프롬프트 (토큰 {ntok} / 상한 {_D.num('HARD_SEQ_LEN')})")
print("=" * 78)
print(norm)
print("=" * 78)
print("■ 정규화 매핑 (실명 → 프롬프트 이름)")
print(json.dumps(mapping, ensure_ascii=False, indent=1))
print("■ gold tactic:", repr(dp.proofs[PI].steps[SI].step.text))

if OUT:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "prompt_norm.txt").write_text(norm)
    (OUT / "prompt_raw.txt").write_text(raw)
    (OUT / "mapping.json").write_text(json.dumps(mapping, ensure_ascii=False, indent=1))
    print(f"저장: {OUT}/prompt_norm.txt · prompt_raw.txt · mapping.json")
