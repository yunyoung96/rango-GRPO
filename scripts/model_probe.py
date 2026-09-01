#!/usr/bin/env python3
"""후보 모델 적재·학습 가능성 검사 — 가중치 다운로드 → bf16 적재 → seq 4096 전방/역방 3스텝(AdamW, grad-ckpt)
→ 피크 메모리·스텝 시간. 사용: python3 scripts/model_probe.py [모델...]  (GPU 1 사용)"""
import sys, time, json, torch, transformers
from transformers import AutoTokenizer, AutoModelForCausalLM
DEV = "cuda:1"; SEQ = 4096
models = sys.argv[1:] or ["Qwen/Qwen3.5-4B-Base", "Qwen/Qwen3-4B-Base"]
rows = [json.loads(l) for l in open("all_log/sft_pairs_val.jsonl")]
for m in models:
    print("==", m, flush=True)
    try:
        t0 = time.time(); tok = AutoTokenizer.from_pretrained(m)
        try:
            model = AutoModelForCausalLM.from_pretrained(m, dtype=torch.bfloat16, device_map={"": DEV})
            kind = "CausalLM"
        except Exception as e:
            print("  AutoModelForCausalLM 실패 →", str(e)[:120])
            from transformers import AutoModelForImageTextToText
            model = AutoModelForImageTextToText.from_pretrained(m, dtype=torch.bfloat16, device_map={"": DEV})
            kind = "ImageTextToText"
        n = sum(p.numel() for p in model.parameters())
        print(f"  적재 {kind} · 파라미터 {n/1e9:.2f}B · {time.time()-t0:.0f}s · 적재 메모리 {torch.cuda.memory_allocated(DEV)/1e9:.1f}GB", flush=True)
        # 실제 프롬프트 토큰을 이어 붙여 SEQ 길이 배치 1개
        ids = []
        for r in rows:
            ids += tok(r["prompt"] + "\n[TACTIC]\n" + r["target"] + "\n", add_special_tokens=False).input_ids
            if len(ids) >= SEQ: break
        ids = torch.tensor([ids[:SEQ]], device=DEV)
        assert ids.shape[1] == SEQ
        model.train(); model.gradient_checkpointing_enable()
        opt = torch.optim.AdamW(model.parameters(), lr=1e-6)
        torch.cuda.reset_peak_memory_stats(DEV); t = time.time(); losses = []
        for step in range(3):
            out = model(input_ids=ids, labels=ids); out.loss.backward(); opt.step(); opt.zero_grad(set_to_none=True)
            torch.cuda.synchronize(DEV); losses.append(round(out.loss.item(), 3))
        print(f"  학습 스텝 seq={SEQ} B=1 AdamW+ckpt: {(time.time()-t)/3:.2f}s/step · 피크 {torch.cuda.max_memory_allocated(DEV)/1e9:.1f}GB · loss {losses}", flush=True)
        assert all(torch.isfinite(torch.tensor(losses))), "loss 비유한"
        del model, opt; torch.cuda.empty_cache()
    except Exception as e:
        import traceback; traceback.print_exc(); print(f"  실패 {m}: {str(e)[:200]}", flush=True)
print("PROBE_DONE")
