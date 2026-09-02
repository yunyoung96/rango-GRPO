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
import json, math, os, random, re, sys, time
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
        return {"input_ids": p + t, "labels": [-100] * len(p) + t, "idx": i}


_CONSUMED = {"f": None, "n": 0}
def collate(batch, pad_id):
    # ★ DPO 창 구성용: 이 rank 가 소비한 예제 id 를 마이크로배치 순서대로 기록 (step = n // grad_accum 은 DPO 쪽에서 환산)
    if _CONSUMED["f"] is not None:
        _CONSUMED["f"].write(json.dumps({"mb": _CONSUMED["n"], "idx": [b["idx"] for b in batch]}) + "\n"); _CONSUMED["f"].flush()
        _CONSUMED["n"] += 1
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
    """loss 비유한·정체 감시 (주기 모니터링 요구) + 로그 jsonl 누적."""
    def __init__(self, log_path): self.log_path = log_path; self.hist = []
    def on_log(self, args, state, control, logs=None, **kw):
        if logs and "loss" in logs:
            assert math.isfinite(logs["loss"]), f"loss 비유한 @ {state.global_step}"
            self.hist.append(logs["loss"])
            # 정체·발산 감시: 최근 200 step 평균이 첫 200 step 평균의 1.5배면 발산
            if len(self.hist) >= 40 and sum(self.hist[-20:]) / 20 > 1.5 * sum(self.hist[:20]) / 20 and state.global_step > 500:
                print(f"  [guard] ★ 발산 의심 @ {state.global_step}: 최근 {sum(self.hist[-20:])/20:.3f} vs 초기 {sum(self.hist[:20])/20:.3f}", flush=True)
            print(f"  [guard] step {state.global_step} loss {logs['loss']:.4f} lr {logs.get('learning_rate', 0):.2e}"
                  f" mem {torch.cuda.max_memory_allocated()/1e9:.0f}GB", flush=True)
        if logs and state.is_world_process_zero:
            with open(self.log_path, "a") as f: f.write(json.dumps({"step": state.global_step, **logs}) + "\n")


NAME_RE = re.compile(r"\b(?:e?apply|e?rewrite|exact|refine)\s+(?:<-\s*)?(?:\(\s*)?([A-Za-z_][\w'.]*)")
try:                                    # stdlib 정확 일치는 "기억 사용 정상" — 지표를 두 갈래로 찍는다 (2026-09-02 결정)
    sys.path.insert(0, "src")
    from tactic_gen.normalize_names import is_stdlib_name as _is_std
except Exception:
    _is_std = lambda n: False


class Milestone(TrainerCallback):
    """★ DPO 라운드용 이정표 — milestone_steps(5000) 마다 체크포인트를 models/…/milestone-<step> 로 복사해 보존한다
    (save_total_limit 순환에서 제외). DPO 는 이 이정표에서 lemma 참조 지점만으로 돌리고, 갱신 가중치를 체크포인트에
    덮어쓴 뒤 스케줄을 이어서 재개한다 (design [4] DPO 절)."""
    def __init__(self, every): self.every = every
    def on_save(self, args, state, control, **kw):
        if state.is_world_process_zero and self.every and state.global_step % self.every == 0:
            import shutil
            src = f"{args.output_dir}/checkpoint-{state.global_step}"; dst = f"{args.output_dir}/milestone-{state.global_step}"
            if os.path.isdir(src) and not os.path.isdir(dst):
                shutil.copytree(src, dst); print(f"  [milestone] {dst} 보존", flush=True)


class Sampler(TrainerCallback):
    """★ 학습 중 **프롬프트→출력을 눈으로 보는** 감시 (사용자 요구): 고정 검증 프롬프트 K 개를 sample_steps 마다
    greedy 생성해 gold 와 나란히 jsonl 에 남긴다. 지표: 정확일치(EM) · 출력이 부른 프리미스 이름이 프롬프트 안에 있음(환각 아님)."""
    def __init__(self, tok, val, path, every, k=8, max_new=64):
        self.tok, self.path, self.every, self.max_new = tok, path, every, max_new
        self.items = val.items[:k]
    def _run(self, model, step):
        model.eval(); em = inp = 0; recs = []
        with torch.no_grad():
            for p, t in self.items:
                ids = torch.tensor([p], device=model.device)
                out = model.generate(ids, max_new_tokens=self.max_new, do_sample=False,
                                     eos_token_id=self.tok.eos_token_id, pad_token_id=self.tok.pad_token_id)
                gen = self.tok.decode(out[0, len(p):], skip_special_tokens=True).split("\n")[0].strip()
                gold = self.tok.decode(t, skip_special_tokens=True).strip()
                prompt = self.tok.decode(p, skip_special_tokens=True)
                ok_em = " ".join(gen.split()) == " ".join(gold.split()); em += ok_em
                names = [n.rstrip(".") for n in NAME_RE.findall(gen)]
                def _inp(ns): return all(re.search(r"(?<![\w'])" + re.escape(n.split(".")[-1]) + r"(?![\w'])", prompt) for n in ns) if ns else None
                in_p = _inp(names)                                   # 전체 이름 기준
                in_p2 = _inp([n for n in names if not (_is_std(n) or _is_std(n.split(".")[-1]))])   # stdlib 정확일치 제외
                inp += bool(in_p) if names else 0
                st = prompt[prompt.rfind("[STATE]"):prompt.rfind("[SCRIPT]")][:400]
                recs.append({"step": step, "em": ok_em, "names_in_prompt": in_p, "names_in_prompt_exstd": in_p2, "gen": gen, "gold": gold, "state": st})
        model.train()
        with open(self.path, "a") as f:
            for r in recs: f.write(json.dumps(r, ensure_ascii=False) + "\n")
        n_named = sum(1 for r in recs if r["names_in_prompt"] is not None)
        n2 = sum(1 for r in recs if r["names_in_prompt_exstd"] is not None); i2 = sum(bool(r["names_in_prompt_exstd"]) for r in recs if r["names_in_prompt_exstd"] is not None)
        print(f"  [sample] step {step}: EM {em}/{len(recs)} · 이름∈프롬프트 {inp}/{n_named} (stdlib제외 {i2}/{n2}) · 예) gold={recs[0]['gold'][:50]!r} gen={recs[0]['gen'][:50]!r}", flush=True)
    def on_step_end(self, args, state, control, model=None, **kw):
        if state.is_world_process_zero and self.every and state.global_step % self.every == 0:
            try: self._run(model, state.global_step)
            except Exception as e: print(f"  [sample] 실패 @ {state.global_step}: {type(e).__name__}: {str(e)[:120]}", flush=True)
    def on_train_end(self, args, state, control, model=None, **kw):
        if state.is_world_process_zero:
            try: self._run(model, state.global_step)
            except Exception as e: print(f"  [sample] 실패(종료) {e}", flush=True)


def main():
    tok = AutoTokenizer.from_pretrained(CONF["model_name"])
    if tok.pad_token_id is None: tok.pad_token = tok.eos_token
    tr_path = CONF["train_path"]; va_path = CONF.get("val_path")
    rank = int(os.environ.get("RANK", os.environ.get("LOCAL_RANK", "0")))
    if not (va_path and os.path.exists(va_path)):
        # train 뒤 2% 를 검증으로 뗀다 (지점 셔플본이라 임의 표본과 같다). DDP: rank0 만 파일을 쓰고 나머지는 기다린다.
        va_path = tr_path.replace(".jsonl", "_valcut.jsonl"); tr_cut = tr_path.replace(".jsonl", "_traincut.jsonl")
        # ★ 원본이 컷 파일보다 새로우면 다시 뗀다 — 스모크가 남긴 옛 컷(24행)으로 본학습이 도는 사고 방지
        stale = (os.path.exists(tr_cut) and os.path.getmtime(tr_cut) < os.path.getmtime(tr_path))
        if rank == 0 and (stale or not (os.path.exists(va_path) and os.path.exists(tr_cut))):
            rows = open(tr_path).read().splitlines(); k = max(1, len(rows) // 50)
            open(va_path + ".tmp", "w").write("\n".join(rows[-k:]) + "\n"); open(tr_cut + ".tmp", "w").write("\n".join(rows[:-k]) + "\n")
            os.replace(va_path + ".tmp", va_path); os.replace(tr_cut + ".tmp", tr_cut)
        while not (os.path.exists(va_path) and os.path.exists(tr_cut)) or os.path.getmtime(tr_cut) < os.path.getmtime(tr_path): time.sleep(2)
        tr_path = tr_cut
        if rank == 0:
            n_tr = sum(1 for _ in open(tr_cut)); n_src = sum(1 for _ in open(CONF["train_path"]))
            assert n_tr >= n_src * 0.97, f"컷 파일 행 {n_tr} vs 원본 {n_src} — 옛 컷 의심"
    train = PairDataset(tr_path, tok, HARD, limit=(SMOKE * 8 if SMOKE else None))
    val = PairDataset(va_path, tok, HARD, limit=CONF.get("num_eval_examples"))
    if rank == 0: print(f"■ 데이터: train {len(train)} (초과 제외 {train.dropped}) · val {len(val)} (초과 제외 {val.dropped}) · hard {HARD} · world {os.environ.get('WORLD_SIZE', '1')}", flush=True)
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
        ddp_find_unused_parameters=False, logging_first_step=True,
    )
    odir = args.output_dir; os.makedirs(odir, exist_ok=True)
    if not SMOKE: _CONSUMED["f"] = open(f"{odir}/consumed_rank{rank}.jsonl", "a")   # 재개 시 append (mb 카운터는 파일 길이로 복원)
    if _CONSUMED["f"] is not None:
        try: _CONSUMED["n"] = sum(1 for _ in open(f"{odir}/consumed_rank{rank}.jsonl"))
        except Exception: _CONSUMED["n"] = 0
    sampler = Sampler(tok, val, f"{odir}/samples.jsonl", every=(2 if SMOKE else int(CONF.get("sample_steps", 500))),
                      k=int(CONF.get("sample_k", 8)))
    trainer = Trainer(model=model, args=args, train_dataset=train, eval_dataset=val,
                      data_collator=lambda b: collate(b, tok.pad_token_id), callbacks=[Guard(f"{odir}/trainlog.jsonl"), sampler, Milestone(int(CONF.get("milestone_steps", 5000)))])
    # 재개: output_dir 에 checkpoint-* 가 있으면 거기서 이어간다 (감시자가 죽은 학습을 되살릴 때)
    resume = (not SMOKE) and "--resume" in sys.argv and any(d.startswith("checkpoint-") for d in os.listdir(odir))
    if resume and rank == 0: print("■ 체크포인트에서 재개", flush=True)
    t0 = time.time(); out = trainer.train(resume_from_checkpoint=resume or None)
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
