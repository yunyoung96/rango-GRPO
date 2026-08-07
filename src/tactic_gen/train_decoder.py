from typing import Optional, Iterable, Generator, Any
import sys, os
import shutil
import re
import time
import argparse
import functools
import subprocess
from pathlib import Path

from yaml import load, Loader
import jsonlines

from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
import transformers
import transformers.modeling_utils as _tmu

# transformers 5.x: caching_allocator_warmup crashes with bitsandbytes quantized adapters
# It is a perf-only optimization so disabling it is safe.
def _noop_caching_allocator_warmup(model, expanded_device_map, hf_quantizer):
    pass

_tmu.caching_allocator_warmup = _noop_caching_allocator_warmup

from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    PreTrainedModel,
    PreTrainedTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
    CodeLlamaTokenizer,
    Trainer,
    TrainerCallback,
)
import torch
from torch.utils.data import Dataset
from trl import SFTTrainer
from tactic_gen.data_collator_compat import DataCollatorForCompletionOnlyLM

# from datasets import Dataset
import numpy as np

from util.train_utils import (
    get_optional_arg,
    get_required_arg,
    get_training_args,
    load_config,
    make_output_dir,
    copy_configs,
    get_train_val_path,
    TrainType,
    TRAINING_CONF_NAME,
    REQS_NAME,
    GIT_NAME,
)
from util.util import set_rango_logger
from util.constants import RANGO_LOGGER
from data_management.splits import Split
from tactic_gen.tactic_data import (
    LmDataset,
    LmProcessedDataset,
    TacticDataConf,
    example_collator_conf_from_yaml,
    example_collator_from_conf,
    get_tokenizer,
)

import logging

_logger = logging.getLogger(RANGO_LOGGER)


# This doc details how to finetune codellama:
# https://github.com/huggingface/trl/blob/main/examples/scripts/sft_trainer.py

# More ideas for arguments here:
# https://huggingface.co/docs/transformers/main_classes/trainer#transformers.TrainingArguments


class CheckpointRotationCallback(TrainerCallback):
    """중간 체크포인트 회전 — save_steps(예 1000) 마다 저장하되 **keep_every(예 5000) 배수만 영구 보존**.

    마일스톤(배수) step 에 도달하면 그보다 이전의 비-배수 중간본을 지운다. 진행중 구간의 1000 단위는
    남아 있어 GPU 가 끊겨도 최대 save_steps 만 잃는다(= save_total_limit 로는 불가능한 정책:
    Trainer 의 limit 은 오래된 것부터 지워 마일스톤까지 날림 → 그래서 save_total_limit: null 과 함께 쓴다).
    """

    CKPT_RE = re.compile(r"^checkpoint-(\d+)$")

    def __init__(self, keep_every: int, output_dir: str) -> None:
        self.keep_every = keep_every
        self.output_dir = Path(output_dir)

    def on_save(self, args, state, control, **kwargs):
        if not state.is_world_process_zero or self.keep_every <= 0:
            return control
        cur = int(state.global_step)
        if cur % self.keep_every:
            return control                      # 마일스톤 아님 → 아직 정리 안 함
        removed = []
        for d in self.output_dir.glob("checkpoint-*"):
            m = self.CKPT_RE.match(d.name)
            if not m:
                continue
            s = int(m.group(1))
            if s < cur and s % self.keep_every:  # 마일스톤 아닌 이전 중간본만 삭제
                shutil.rmtree(d, ignore_errors=True)
                removed.append(s)
        if removed:
            print(f"[ckpt-rotate] 마일스톤 {cur} 도달 → 중간 체크포인트 삭제: {sorted(removed)}",
                  flush=True)
        return control


def get_lora_conf(conf: dict[str, Any]) -> LoraConfig:
    peft_config = LoraConfig(
        lora_alpha=16,
        lora_dropout=0.1,
        r=64,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules="all-linear",
    )
    return peft_config


def get_model(model_name: str, load_in_4bit: bool = True) -> PreTrainedModel:
    # ★ load_in_4bit: false → bf16 풀 베이스. 96GB GPU 에서는 4bit dequant 오버헤드가 없어
    #   step 이 크게 빨라진다(7B FULL 학습서 실측). 1.3B 는 bf16 이 기본적으로 유리.
    if not load_in_4bit:
        return AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.bfloat16)

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_storage=torch.bfloat16,
    )

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        torch_dtype=torch.bfloat16,
    )

    # https://huggingface.co/docs/bitsandbytes/main/en/fsdp_qlora
    # model = prepare_model_for_kbit_training(model)
    # https://github.com/microsoft/DeepSpeed/blob/master/deepspeed/inference/quantization/quantization.py
    # https://github.com/microsoft/DeepSpeedExamples/tree/master/inference/huggingface/zero_inference
    return model


def get_datasets(
    conf: dict[str, Any],
) -> tuple[LmDataset | LmProcessedDataset, LmDataset | LmProcessedDataset]:
    if "data_path" in conf:
        example_collator_yaml_conf = get_required_arg("example_collator", conf)
        data_path = Path(get_required_arg("data_path", conf))
        num_eval_examples = get_optional_arg("num_eval_examples", conf, None)
        hard_seq_len = get_required_arg("hard_seq_len", conf)
        train_path, val_path = get_train_val_path(data_path)

        example_collator_conf = example_collator_conf_from_yaml(
            example_collator_yaml_conf
        )
        example_collator = example_collator_from_conf(example_collator_conf)
        print("EXAMPLE COLLATOR", example_collator)
        tokenizer = get_tokenizer(get_required_arg("model_name", conf))
        train_dataset = LmProcessedDataset(
            train_path, tokenizer, example_collator, hard_seq_len
        )
        val_dataset = LmProcessedDataset(
            val_path,
            tokenizer,
            example_collator,
            hard_seq_len,
            num_eval_examples,
        )
        return train_dataset, val_dataset
    else:
        assert "tactic_data" in conf
        dataset_conf = TacticDataConf.from_yaml(conf["tactic_data"])
        train_dataset = LmDataset.from_conf(dataset_conf, Split.TRAIN)
        val_dataset = LmDataset.from_conf(
            dataset_conf, Split.VAL, conf.get("num_eval_examples", None)
        )
        return train_dataset, val_dataset


# def formatting_func(examples: list[str]) -> list[str]:
#     # Formatting is done upon dataset creation
#     return examples


def get_trainer(
    conf: dict[str, Any], local_rank: Optional[int], checkpoint_name: Optional[str]
) -> Trainer:
    print("\n\nBuilding Training Config...")
    training_args = get_training_args(conf, local_rank)

    print("\n\nRetrieving Model...")
    model_name = get_required_arg("model_name", conf)
    raw_model = get_model(model_name, get_optional_arg("load_in_4bit", conf, True))
    lora_config = get_lora_conf(conf)
    model = get_peft_model(raw_model, lora_config)

    print("\n\nConstructing Dataset...")
    train_dataset, val_dataset = get_datasets(conf)

    print(train_dataset.tokenizer.decode(train_dataset[0].input_ids))

    print("\n\nBuilding Trainer...")
    # trainer = SFTTrainer(
    #     model=model,
    #     tokenizer=tokenizer,
    #     args=training_args,
    #     data_collator=train_dataset.collator,
    #     train_dataset=train_dataset,
    #     eval_dataset=val_dataset,
    #     max_seq_length=hard_seq_len,
    # )

    # transformers 5.x: Trainer(tokenizer=...) → processing_class=... 로 개명. 설치 버전에 맞춰 선택.
    import inspect as _inspect

    _tk = ("processing_class"
           if "processing_class" in _inspect.signature(Trainer.__init__).parameters
           else "tokenizer")
    trainer = Trainer(
        model=model,
        args=training_args,
        data_collator=train_dataset.collator,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        **{_tk: train_dataset.tokenizer},
        # max_seq_length=hard_seq_len,
    )
    keep_every = get_optional_arg("keep_every", conf, 0)
    if keep_every:      # save_steps 마다 저장 + keep_every 배수만 영구 보존(중단복구 정책)
        trainer.add_callback(
            CheckpointRotationCallback(keep_every, get_required_arg("output_dir", conf))
        )
        print(f"[ckpt-rotate] save_steps={training_args.save_steps} 저장, "
              f"{keep_every} 배수만 영구 보존")
    return trainer


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Train code llama by providing a .yaml config file. As an example, see src/tactic_gen/confs/basic_train.yaml"
    )
    print(f"<ARGV>{sys.argv}</ARGV")
    parser.add_argument(
        "--local_rank",
        type=int,
        default=-1,
        help="local rank passed from distributed launcher",
    )
    parser.add_argument("yaml_config", help="yaml config file to use for training.")
    args = parser.parse_args(sys.argv[1:])
    # ★ 기본 INFO. DEBUG 는 예제마다 goal/쿼리를 전부 찍어 2M 예제 학습에서 로그가 수 GB 로 불어난다
    #   (NFS 부하 + 느려짐). 디버깅이 필요하면 RANGO_LOG_LEVEL=DEBUG 로 켠다.
    _lvl = getattr(logging, os.environ.get("RANGO_LOG_LEVEL", "INFO").upper(), logging.INFO)
    set_rango_logger(__file__, _lvl)
    conf = load_config(args.yaml_config)
    train_from_checkpoint = (
        conf["checkpoint_name"] if "checkpoint_name" in conf else None
    )
    trainer = get_trainer(conf, args.local_rank, train_from_checkpoint)
    if train_from_checkpoint:
        checkpoint_name = conf["checkpoint_name"]
        print(f"Training from checkpoint {checkpoint_name}")
        transformers.logging.set_verbosity_info()
        trainer.train(checkpoint_name)
    else:
        # ★ DDP: 디렉토리 생성/설정복사는 rank0 만(다중 랭크 동시 생성 경쟁 방지).
        _rank = int(os.environ.get("RANK", os.environ.get("LOCAL_RANK", "0")))
        if _rank == 0:
            make_output_dir(conf)
            copy_configs(args.yaml_config, conf, TrainType.TACTIC)
        else:
            os.makedirs(get_required_arg("output_dir", conf), exist_ok=True)
        print("Training from scratch")
        trainer.train()
