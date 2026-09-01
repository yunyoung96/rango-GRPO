#!/usr/bin/env python3
"""★ [④ 학습] 5블록 SFT 학습기 — 사전 물질화된 (prompt, target) jsonl 을 그대로 학습한다.

왜 새로 쓰나: rango 의 train_decoder 는 dp+포매터 즉석 생성(또는 ExampleDB) 경로라 우리 물질화
jsonl(③ v2 산출) 을 직접 못 먹는다. 학습 규칙은 v10 과 같게 맞춘다:
  · loss 는 **target 토큰에서만** (prompt 는 -100) · target 끝에 EOS 부착 (멈춤 학습)
  · hard_seq_len 초과 행은 **제외**(앞 절단 금지 — 앞쪽이 우리 프리미스 블록이라 gold 를 잃는다)
  · 동적 패딩 · bf16 · gradient checkpointing · cosine + warmup · save/eval 주기
  · 파일 순서 = 물질화 단계의 지점 셔플본을 그대로 (Trainer 의 셔플도 켬)
assert: 마스크가 프롬프트 전부를 가리고 target 을 안 가림 · 라벨 개수 > 0 · loss 유한 · 첫 배치 형태.

사용: python3 scripts/sft_train.py <conf.yaml> [--smoke N]     (--smoke: N 스텝만, 저장 없음)
"""
import json, math, os, random, sys, time
import torch, yaml
from torch.utils.data import Dataset
from transformers import (AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments,
                          TrainerCallback)

CONF = yaml.safe_load(open(sys.argv[1]))
SMOKE = int(sys.argv[sys.argv.index("--smoke") + 1]) if "--smoke" in sys.argv else 0
HARD = int(CONF["hard_seq_len"])
random.seed(CONF.get("seed", 23)); torch.manual_seed(CONF.get("seed", 23))


class PairDataset(Dataset):
    """(prompt, target) → input_ids/labels. 프롬프트 -100, target+EOS 학습."""
    def __init__(self, path, tok, hard, limit=None):
        self.items = []; self.dropped = 0; self.tok = tok
        eos = tok.eos_token_id; assert eos is not None, "EOS 없음"
        for i, l in enumerate(open(path)):
            if limit and len(self.items) >= limit: break
            r = json.loads(l)
            p = tok(r["prompt"], add_special_tokens=False).input_ids
            t = tok(r["target"], add_special_tokens=False).input_ids + [eos]
            if len(p) + len(t) > hard: self.dropped += 1; continue
            self.items.append((p, t))
        assert self.items, f"학습 행 0 ({path})"
        # 첫 행 검증: 프롬프트가 [TACTIC]\n 로 끝나고 target 이 있다
        p0, t0 = self.items[0]
        assert tok.decode(p0).endswith("[TACTIC]\n"), "프롬프트 끝 형식"
        assert len(t0) >= 2, "target 비어 있음"
    def __len__(self): return len(self.items)
    def __getitem__(self, i):
        p, t = self.items[i]
        return {"input_ids": p + t, "labels": [-100] * len(p) + t}


def collate(batch, pad_id):
    m = max(len(b["input_ids"]) for b in batch)
    ids = torch.full((len(batch), m), pad_id, dtype=torch.long)
    lab = torch.full((len(batch), m), -100, dtype=torch.long)
    att = torch.zeros((len(batch), m), dtype=torch.long)
    for i, b in enumerate(batch):
        n = len(b["input_ids"])
        ids[i, :n] = torch.tensor(b["input_ids"]); lab[i, :n] = torch.tensor(b["labels"]); att[i, :n] = 1
    assert (lab != -100).sum().item() > 0, "배치에 학습 토큰 0"
    return {"input_ids": ids, "labels": lab, "attention_mask": att}


class Guard(TrainerCallback):
    """loss 비유한·정체 감시 (주기 모니터링 요구)."""
    def on_log(self, args, state, control, logs=None, **kw):
        if logs and "loss" in logs:
            assert math.isfinite(logs["loss"]), f"loss 비유한 @ {state.global_step}"
            print(f"  [guard] step {state.global_step} loss {logs['loss']:.4f} lr {logs.get('learning_rate', 0):.2e}", flush=True)


def main():
    tok = AutoTokenizer.from_pretrained(CONF["model_name"])
    if tok.pad_token_id is None: tok.pad_token = tok.eos_token
    tr_path = CONF["train_path"]; va_path = CONF.get("val_path")
    if not (va_path and os.path.exists(va_path)):
        # train 뒤 2% 를 검증으로 뗀다 (지점 셔플본이라 임의 표본과 같다)
        rows = open(tr_path).read().splitlines(); k = max(1, len(rows) // 50)
        va_path = tr_path.replace(".jsonl", "_valcut.jsonl"); tr_cut = tr_path.replace(".jsonl", "_traincut.jsonl")
        open(va_path, "w").write("\n".join(rows[-k:]) + "\n"); open(tr_cut, "w").write("\n".join(rows[:-k]) + "\n")
        tr_path = tr_cut
    train = PairDataset(tr_path, tok, HARD, limit=(SMOKE * 8 if SMOKE else None))
    val = PairDataset(va_path, tok, HARD, limit=CONF.get("num_eval_examples"))
    print(f"■ 데이터: train {len(train)} (초과 제외 {train.dropped}) · val {len(val)} (초과 제외 {val.dropped}) · hard {HARD}", flush=True)
    model = AutoModelForCausalLM.from_pretrained(CONF["model_name"], dtype=torch.bfloat16)
    if CONF.get("gradient_checkpointing", True): model.gradient_checkpointing_enable()
    model.config.use_cache = False
    args = TrainingArguments(
        output_dir=CONF["output_dir"] + ("_smoke" if SMOKE else ""),
        per_device_train_batch_size=int(CONF["per_device_train_batch_size"]),
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=int(CONF["gradient_accumulation_steps"]),
        learning_rate=float(CONF["learning_rate"]),
        lr_scheduler_type=CONF.get("lr_scheduler_type", "cosine"),
        warmup_steps=int(CONF.get("warmup_steps", 0)) if not SMOKE else 2,
        max_steps=SMOKE or int(CONF["max_steps"]),
        logging_steps=1 if SMOKE else int(CONF.get("logging_steps", 20)),
        save_steps=int(CONF.get("save_steps", 1000)), save_strategy="no" if SMOKE else "steps",
        eval_strategy="no" if SMOKE else "steps", eval_steps=int(CONF.get("eval_steps", 1000)),
        bf16=bool(CONF.get("bf16", True)), report_to=[], seed=int(CONF.get("seed", 23)),
        dataloader_num_workers=2, remove_unused_columns=False, save_total_limit=3,
    )
    trainer = Trainer(model=model, args=args, train_dataset=train, eval_dataset=val,
                      data_collator=lambda b: collate(b, tok.pad_token_id), callbacks=[Guard()])
    t0 = time.time(); out = trainer.train()
    print(f"■ 학습 종료: {out.global_step} step · {int(time.time()-t0)}s · 최종 loss {out.training_loss:.4f}"
          f" · 피크 메모리 {torch.cuda.max_memory_allocated()/1e9:.1f}GB", flush=True)
    assert math.isfinite(out.training_loss)
    if SMOKE:
        hist = [h["loss"] for h in trainer.state.log_history if "loss" in h]
        assert hist[-1] < hist[0] * 1.05, f"loss 미하강 {hist[0]:.3f}→{hist[-1]:.3f}"
        print(f"■ 스모크 통과: loss {hist[0]:.3f} → {hist[-1]:.3f}")
    else:
        trainer.save_model(CONF["output_dir"] + "/final"); tok.save_pretrained(CONF["output_dir"] + "/final")
    print("SFT_TRAIN_DONE")


if __name__ == "__main__":
    main()
