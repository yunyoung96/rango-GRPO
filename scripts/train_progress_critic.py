"""LeanProgress(2502.17925) progress critic 학습 — 남은 tactic 수 회귀.

백본: deepseek-coder-1.3b-instruct + LoRA(rango adapter 로 초기화 → 이미 Coq 증명상태를 이해).
      ⚠️ base 가 아니라 instruct 다 — rango adapter_config 의 base_model_name_or_path 가 instruct 이고,
      추론 서버도 그걸 로드한다. base 를 쓰면 학습·배포 정책이 갈린다(GRPO_ROLLOUT_ANALYSIS.md §9).
헤드: 마지막 토큰 은닉상태 → softplus 스칼라(남은 스텝 수).
손실: Huber(예측, 라벨). 라벨은 N_MAX 로 clip — 꼬리가 길어서(21+ 가 절반) 그대로 두면
      회귀가 꼬리에 끌려간다. 탐색에서 필요한 건 "가까운가"의 해상도이지 100 vs 200 구분이 아니다.

논문의 short-proof skew 보정: proof_len 버킷(1-5/6-10/11-20/21+)별 균형 샘플링.

사용:
  python3 scripts/train_progress_critic.py \
      --data data/progress/train.jsonl \
      --model_name deepseek-ai/deepseek-coder-1.3b-instruct \
      --init_adapter models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500 \
      --save_dir models/progress_critic --max_samples 200000 --epochs 1
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import torch  # noqa: E402
from torch.utils.data import DataLoader, Dataset  # noqa: E402

from tactic_gen.progress_critic import (  # noqa: E402
    N_MAX,
    ProgressHead,
    last_token_hidden,
)


def bucket(proof_len: int) -> str:
    if proof_len <= 5:
        return "1-5"
    if proof_len <= 10:
        return "6-10"
    if proof_len <= 20:
        return "11-20"
    return "21+"


class ProgressData(Dataset):
    def __init__(self, rows: list[dict], tok, max_len: int):
        self.rows = rows
        self.tok = tok
        self.max_len = max_len

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, i: int):
        r = self.rows[i]
        return r["state"], min(float(r["remaining"]), N_MAX)


def make_collate(tok, max_len: int):
    def collate(batch):
        states = [b[0] for b in batch]
        ys = torch.tensor([b[1] for b in batch], dtype=torch.float32)
        enc = tok(
            states,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=max_len,
        )
        return enc["input_ids"], enc["attention_mask"], ys

    return collate


def load_balanced(path: Path, max_samples: int, seed: int) -> list[dict]:
    """버킷 균형 샘플링 — 논문의 short-proof skew 보정."""
    by_bucket: dict[str, list[dict]] = defaultdict(list)
    with path.open() as f:
        for line in f:
            r = json.loads(line)
            by_bucket[bucket(r["proof_len"])].append(r)
    print("  원본 버킷:", {k: len(v) for k, v in by_bucket.items()})

    rng = random.Random(seed)
    per = max_samples // len(by_bucket)
    rows: list[dict] = []
    for k, v in by_bucket.items():
        take = min(per, len(v))
        rows.extend(rng.sample(v, take))
    rng.shuffle(rows)
    print("  균형 후 버킷:", {k: sum(1 for r in rows if bucket(r["proof_len"]) == k) for k in by_bucket})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/progress/train.jsonl")
    ap.add_argument("--model_name", default="deepseek-ai/deepseek-coder-1.3b-instruct")
    ap.add_argument(
        "--init_adapter",
        default="models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500",
        help="rango LoRA(Coq 증명상태 이해). 없으면 새 LoRA.",
    )
    ap.add_argument("--save_dir", default="models/progress_critic")
    ap.add_argument("--max_samples", type=int, default=200_000)
    ap.add_argument("--val_frac", type=float, default=0.02)
    ap.add_argument("--max_len", type=int, default=1024)
    ap.add_argument("--bsz", type=int, default=8)
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    from peft import LoraConfig, PeftModel, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[critic] device={device}")

    print("[critic] 데이터 로드")
    rows = load_balanced(Path(args.data), args.max_samples, args.seed)
    n_val = max(1, int(len(rows) * args.val_frac))
    val_rows, train_rows = rows[:n_val], rows[n_val:]
    print(f"  train {len(train_rows):,} · val {len(val_rows):,}")

    tok = AutoTokenizer.from_pretrained(args.model_name)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "right"  # last_token_hidden 이 attention_mask.sum()-1 로 마지막 토큰을 찾는다

    base = AutoModelForCausalLM.from_pretrained(
        args.model_name, torch_dtype=torch.bfloat16
    )
    if args.init_adapter:
        lm = PeftModel.from_pretrained(base, args.init_adapter, is_trainable=True)
        print(f"  LoRA 초기화 ← {args.init_adapter}")
    else:
        lora = LoraConfig(
            r=32, lora_alpha=16, lora_dropout=0.1, bias="none",
            task_type="CAUSAL_LM", target_modules="all-linear",
        )
        lm = get_peft_model(base, lora)
    lm = lm.to(device)

    hidden = lm.config.hidden_size if hasattr(lm, "config") else base.config.hidden_size
    head = ProgressHead(hidden).to(device).to(torch.bfloat16)

    collate = make_collate(tok, args.max_len)
    dl = DataLoader(
        ProgressData(train_rows, tok, args.max_len),
        batch_size=args.bsz, shuffle=True, collate_fn=collate, num_workers=2,
    )
    vdl = DataLoader(
        ProgressData(val_rows, tok, args.max_len),
        batch_size=args.bsz, shuffle=False, collate_fn=collate, num_workers=2,
    )

    params = [p for p in lm.parameters() if p.requires_grad] + list(head.parameters())
    n_train = sum(p.numel() for p in params)
    print(f"  학습 파라미터 {n_train/1e6:.1f}M")
    opt = torch.optim.AdamW(params, lr=args.lr)
    lossf = torch.nn.HuberLoss(delta=2.0)

    def evaluate() -> tuple[float, float]:
        lm.eval(); head.eval()
        se = ae = n = 0.0
        with torch.no_grad():
            for ids, attn, ys in vdl:
                ids, attn, ys = ids.to(device), attn.to(device), ys.to(device)
                h = last_token_hidden(lm, ids, attn)
                pred = head(h.to(torch.bfloat16)).float()
                se += float(((pred - ys) ** 2).sum())
                ae += float((pred - ys).abs().sum())
                n += ys.numel()
        lm.train(); head.train()
        return (se / n) ** 0.5, ae / n

    # 학습 전 기준선: 항상 평균을 예측하는 모델의 MAE 와 비교해야 의미가 있다
    ys_all = torch.tensor([min(float(r["remaining"]), N_MAX) for r in val_rows])
    base_mae = float((ys_all - ys_all.mean()).abs().mean())
    print(f"  [기준선] 평균 예측 MAE = {base_mae:.3f}  (critic 이 이걸 못 이기면 무의미)")

    lm.train(); head.train()
    for ep in range(args.epochs):
        tot = n = 0.0
        for i, (ids, attn, ys) in enumerate(dl):
            ids, attn, ys = ids.to(device), attn.to(device), ys.to(device)
            h = last_token_hidden(lm, ids, attn)
            pred = head(h.to(torch.bfloat16)).float()
            loss = lossf(pred, ys)
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            opt.step()
            tot += float(loss); n += 1
            if (i + 1) % 200 == 0:
                print(f"  ep{ep} step {i+1}/{len(dl)} loss={tot/n:.4f}")
        rmse, mae = evaluate()
        print(f"[critic] epoch {ep}: train_loss={tot/max(n,1):.4f} | val RMSE={rmse:.3f} MAE={mae:.3f} "
              f"(기준선 MAE {base_mae:.3f} → {'개선' if mae < base_mae else '★실패: 기준선 미달'})")

    out = Path(args.save_dir)
    out.mkdir(parents=True, exist_ok=True)
    lm.save_pretrained(str(out / "adapter"))
    torch.save({"state_dict": head.state_dict(), "hidden": hidden}, out / "head.pt")
    print(f"[critic] 저장 → {out}/adapter , {out}/head.pt")


if __name__ == "__main__":
    main()
