#!/usr/bin/env python3
"""
Iter 10: 발산 지점에서 실제 rango next-tactic 모델 호출.

Iter 5(음성): 일반 자동화 tail(eauto/lia/...) 은 transplant 잔여 site 를 0/22 못 닫음.
→ 남은 건 "정확한 특정 tactic". 그걸 rango 모델이 goal state 를 보고 예측할 수 있나?

이 모듈은 GPU 모델 wrapper 를 lazy 로 1회 로드하고, (proof_state, proof_script) →
상위 n tactic 후보를 돌려준다. transplant 하네스가 발산 site 에서 이걸 호출한다.

양보: 다른 run 이 GPU 를 쓰는 중이면 로드를 미룬다. VRAM 여유(42GB)라 공존 가능하나
util 을 뺏지 않도록 호출을 소수(발산 site 당 1회)로 제한한다.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from pathlib import Path

CKPT = "models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500"
_WRAPPER = None

def load_model():
    global _WRAPPER
    if _WRAPPER is None:
        from model_deployment.model_wrapper import DecoderLocalWrapper
        _WRAPPER = DecoderLocalWrapper.from_checkpoint(Path(os.path.join(os.path.dirname(__file__), "..", CKPT)))
    return _WRAPPER

def suggest(proof_state, proof_script="", n=16, premises=None, proofs=None, beam=True):
    """goal state 텍스트 → [(tactic, score)] 상위 n."""
    from tactic_gen.lm_example import LmExample
    w = load_model()
    ex = LmExample(
        proof_script=proof_script,
        proof_state=proof_state,
        next_steps=[],
        proofs=proofs,
        premises=premises,
    )
    res = w.get_recs(ex, n, proof_script, beam, None)
    return list(zip(res.next_tactic_list, res.score_list))

if __name__=="__main__":
    # SMOKE: 간단한 goal 하나로 모델이 뜨고 답하는지 (GPU 사용 — 양보 확인 후 수동 실행)
    st = "n : nat\n============================\nn + 0 = n"
    for tac, sc in suggest(st, n=8):
        print(f"{sc:8.3f}  {tac}")
