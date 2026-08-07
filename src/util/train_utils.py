from typing import Any, Optional

import time
import sys, os
import shutil
import subprocess
from pathlib import Path
from enum import Enum

from yaml import load, Loader
from transformers import TrainingArguments, PreTrainedTokenizer


from util.constants import (
    DATA_CONF_NAME,
    GOAL_DATA_CONF_NAME,
    PREMISE_DATA_CONF_NAME,
    RERANK_DATA_CONF_NAME,
    REQS_NAME,
    GIT_NAME,
    TRAINING_CONF_NAME,
    TMP_LOC,
)
from util.util import get_basic_logger

_logger = get_basic_logger(__name__)


class TrainType(Enum):
    TACTIC = 1
    SELECT = 2
    RERANK = 3


def allocate_tokens(
    tokenizer: PreTrainedTokenizer, s: str, allowance: int, truncate_front: bool = True
) -> tuple[str, int]:
    tokens = tokenizer.encode(s)
    if truncate_front:
        to_add = tokens[(-1 * allowance) :]
    else:
        to_add = tokens[:allowance]
    return tokenizer.decode(to_add, skip_special_tokens=True), len(to_add)


def load_config(path: str) -> dict[str, Any]:
    with open(path, "r") as fin:
        conf = load(fin, Loader=Loader)
    assert type(conf) == dict
    assert all([type(s) == str for s in conf.keys()])
    return conf


def copy_configs(conf_path: Path, conf: dict[str, Any], train_type: TrainType) -> None:
    output_dir = Path(get_required_arg("output_dir", conf))
    match train_type:
        case TrainType.TACTIC:
            if "data_path" in conf:
                data_path = Path(conf["data_path"])
                data_conf_loc = data_path / "conf.yaml"
                shutil.copy(data_conf_loc, output_dir / DATA_CONF_NAME)
        case TrainType.SELECT:
            data_path = Path(get_required_arg("data_path", conf))
            data_conf_loc = data_path / "conf.yaml"
            shutil.copy(data_conf_loc, output_dir / PREMISE_DATA_CONF_NAME)
        case TrainType.RERANK:
            data_path = Path(get_required_arg("data_path", conf))
            data_conf_loc = data_path / "conf.yaml"
            shutil.copy(data_conf_loc, output_dir / RERANK_DATA_CONF_NAME)

    shutil.copy(conf_path, output_dir / TRAINING_CONF_NAME)
    reqs = subprocess.check_output([sys.executable, "-m", "pip", "freeze"])
    with open(os.path.join(output_dir, REQS_NAME), "wb") as fout:
        fout.write(reqs)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"])
    with open(os.path.join(output_dir, GIT_NAME), "wb") as fout:
        fout.write(commit)


def make_output_dir(conf: dict[str, Any]) -> None:
    """출력 디렉토리 준비. **기존 학습 결과 덮어쓰기 방지**가 목적이다.

    ★ 판정 기준을 '생성시각 30분'에서 '체크포인트 존재'로 바꿨다. 이유:
      · DDP 다중 랭크가 동시에 이 함수를 부르면 한 랭크가 만든 디렉토리를 다른 랭크가 보고 죽는다.
      · NFS 는 ctime 이 캐시돼 방금 만든 디렉토리도 오래된 것으로 보일 수 있다(실측).
      · 정작 지키려는 것은 "이미 학습된 체크포인트"이지 빈 디렉토리가 아니다.
    """
    output_dir = get_required_arg("output_dir", conf)
    if os.path.exists(output_dir):
        ckpts = [d for d in os.listdir(output_dir) if d.startswith("checkpoint-")]
        if ckpts:
            print(f"{output_dir} already has checkpoints {sorted(ckpts)[:3]}... "
                  f"(덮어쓰기 방지 — 이어서 학습하려면 conf 의 checkpoint_name 을 쓰세요)")
            exit(1)
    else:
        os.makedirs(output_dir, exist_ok=True)


def get_required_arg(key: str, conf: dict[str, Any]) -> Any:
    if key not in conf:
        print(f"{key} is a required field in the configuration file.")
        exit(1)
    return conf[key]


def get_optional_arg(key: str, conf: dict[str, Any], default: Any) -> Any:
    if key not in conf:
        print(f"{key} not found in configuration. Defaulting to {default}")
        return default
    return conf[key]


def get_train_val_path(data_path: Path) -> tuple[Path, Path]:
    tmp_path = Path("/tmp") / data_path.name
    if tmp_path.exists():
        train_path = tmp_path / "train.db"
        val_path = tmp_path / "val.db"
        _logger.info(f"Using tmp data at {tmp_path}")
        return train_path, val_path
    else:
        train_path = data_path / "train.db"
        val_path = data_path / "val.db"
        _logger.info(f"Using data at {data_path}")
        return train_path, val_path


def get_training_args(
    conf: dict[str, Any], local_rank: Optional[int]
) -> TrainingArguments:
    # transformers 5.x 에서 evaluation_strategy → eval_strategy 로 개명. 설치 버전에 맞춰 키 선택.
    import inspect

    _params = inspect.signature(TrainingArguments.__init__).parameters
    _eval_key = "eval_strategy" if "eval_strategy" in _params else "evaluation_strategy"
    _extra: dict[str, Any] = {_eval_key: "steps"}
    return TrainingArguments(
        output_dir=get_required_arg("output_dir", conf),
        per_device_train_batch_size=get_required_arg(
            "per_device_train_batch_size", conf
        ),
        gradient_accumulation_steps=get_optional_arg(
            "gradient_accumulation_steps", conf, 2
        ),
        # optim="paged_adamw_8bit", # causes problems retraining ?
        learning_rate=get_required_arg("learning_rate", conf),
        logging_steps=get_required_arg("logging_steps", conf),
        num_train_epochs=get_required_arg("num_train_epochs", conf),
        max_steps=get_optional_arg("max_steps", conf, -1),
        save_strategy="steps",
        save_steps=get_required_arg("save_steps", conf),
        save_total_limit=get_required_arg("save_total_limit", conf),
        **_extra,
        eval_steps=get_required_arg("eval_steps", conf),
        per_device_eval_batch_size=get_required_arg("per_device_eval_batch_size", conf),
        eval_accumulation_steps=get_optional_arg("eval_accumulation_steps", conf, 1),
        # ★ load_best_model_at_end: 기본 True(기존 동작). eval_loss 가 NaN 이거나
        #   save_total_limit=null + 마일스톤 회전을 쓸 땐 conf 에서 false 로 끈다.
        load_best_model_at_end=get_optional_arg("load_best_model_at_end", conf, True),
        # ── 처리량(GPU 굶기지 않기): dataloader 워커/프리페치, bf16, gradient checkpointing ──
        bf16=get_optional_arg("bf16", conf, False),
        gradient_checkpointing=get_optional_arg("gradient_checkpointing", conf, False),
        dataloader_num_workers=get_optional_arg("dataloader_num_workers", conf, 0),
        dataloader_persistent_workers=get_optional_arg(
            "dataloader_persistent_workers", conf, False
        ),
        dataloader_prefetch_factor=get_optional_arg("dataloader_prefetch_factor", conf, None),
        # deepspeed=__get_required_arg("deepspeed", conf),
        local_rank=(local_rank if local_rank else -1),
        ddp_find_unused_parameters=False,
    )
