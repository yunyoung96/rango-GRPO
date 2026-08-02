# grpo_train DDP (멀티GPU 학습) — 옵트인

작성 2026-08-02. grpo_train(SFT/GRPO)을 여러 GPU로 학습. **기본 off(DDP_TRAIN 미설정=기존 single-GPU 100% 동일).**

## 왜
grpo_train은 원래 single-GPU(`device="cuda"` = cuda:0). SFT/GRPO 동안 다른 GPU 놀음.
1.3B라 한 GPU로 충분했으나, 데이터 커지면(예 tst1000tr5091 gold 4228그룹) SFT ~7.5h → DDP로 단축.

## 쓰는 법
```bash
DDP_TRAIN=1 torchrun --nproc_per_node=2 -m tactic_gen.grpo_train \
  --rollouts <데이터> --model_name <base> --init_adapter <adapter> \
  --collator_conf <conf> --max_len 3072 --save_dir <out>/adapter \
  --sft --kl_beta 0.0 --epochs 2 --lr 1e-6 --micro_bsz 2
```
- `DDP_TRAIN=1` + `torchrun --nproc_per_node=N` 둘 다 필요(torchrun이 RANK/LOCAL_RANK/WORLD_SIZE env 세팅).
- 미설정이면 기존 single-GPU 그대로.

## 구현 (grpo_train.py)
- main: `DDP_TRAIN=1 && LOCAL_RANK있음` → init_process_group(nccl), device=cuda:local_rank.
- policy를 DDP 래핑(ref_model deepcopy 이후, find_unused_parameters=True — LoRA만 학습·base동결).
- train(): groups를 `[rank::world]` 샤딩(rank마다 다른 그룹) → gradient backward서 allreduce(동기).
- 저장: rank0만, DDP면 `.module`로 PeftModel 접근. 끝에 barrier+destroy_process_group.

## 주의
- **micro_bsz는 GPU당**(effective = micro_bsz × world). lr 조정 고려(선형스케일 원하면).
- **결과 동등성**: 데이터 샤딩이라 그룹 순서·배치가 single과 다름 → loss 궤적 약간 다를 수 있음(수렴은 동일 기대).
- LoRA만 학습이라 통신량 작음(어댑터 gradient만 allreduce). 1.3B엔 통신 오버헤드 < 계산이득.
- **검증 안 됨(2026-08-02 작성 시점)**: 코드 추가만. 실제 2-GPU 실행 테스트 필요(작은 데이터로 먼저).

관련: [[../rango_augmented/EXPERIMENT_SETUP]]
