#!/usr/bin/env python3
"""문서용 코드 참조(파일:라인) 자동 추적. 심볼→현재 라인번호를 grep해 출력.
코드 수정 후 재실행하면 최신 라인으로 갱신됨. 사용: python3 scripts/doc_lineref.py"""
import re, subprocess, json
# (표시이름, 파일, 정규식 앵커)
REFS = [
    ("check_proof",            "src/model_deployment/proof_manager.py",     r"def check_proof\("),
    ("admit 차단",             "src/model_deployment/proof_manager.py",     r'"Admitted\." in partial_proof|admit\. .* in partial_proof|\("admit\.'),
    ("get_recs(client)",       "src/model_deployment/tactic_gen_client.py", r"def get_recs\("),
    ("BFS.search",             "src/model_deployment/bfs_prover_searcher.py",r"def search\(self"),
    ("BFS._score",             "src/model_deployment/bfs_prover_searcher.py",r"def _score\("),
    ("RMaxTS.ducb",            "src/model_deployment/rmaxts_searcher.py",    r"def ducb\("),
    ("RMaxTS._expand",         "src/model_deployment/rmaxts_searcher.py",    r"def _expand\("),
    ("group_advantages",       "src/tactic_gen/grpo.py",                     r"def group_advantages\("),
    ("kl_unbiased",            "src/tactic_gen/grpo.py",                     r"def kl_unbiased\("),
    ("grpo_batch_loss",        "src/tactic_gen/grpo.py",                     r"def grpo_batch_loss\("),
    ("rollout_attempt",        "src/tactic_gen/grpo_rollout.py",            r"def rollout_attempt\("),
    ("collect_group",          "src/tactic_gen/grpo_rollout.py",            r"def collect_group\("),
    ("sequence_token_logprobs","src/tactic_gen/grpo_train.py",              r"def sequence_token_logprobs\("),
    ("flatten_group",          "src/tactic_gen/grpo_train.py",              r"def flatten_group\("),
    ("train(GRPO 루프)",       "src/tactic_gen/grpo_train.py",              r"def train\("),
    ("dpo_loss",               "src/tactic_gen/dpo.py",                     r"def dpo_loss\("),
    ("value_iteration",        "src/model_deployment/qed_value_iter.py",    r"def value_iteration\("),
    ("QEDValue.value_state",   "src/model_deployment/qed_cartographer.py",  r"def value_state\("),
    ("SolveGoal(_solve)",      "src/model_deployment/quarry_searcher.py",   r"def _solve\("),
    ("alias 결합(run_thm)",    "scripts/run_thm.py",                        r'case "rango-grpo-rmaxts"'),
]
def commit():
    try: return subprocess.check_output(["git","rev-parse","--short","HEAD"],text=True).strip()
    except: return "?"
out={}
for name,f,anchor in REFS:
    ln=None
    try:
        for i,line in enumerate(open(f),1):
            if re.search(anchor,line): ln=i; break
    except FileNotFoundError: pass
    out[name]={"file":f,"line":ln}
    print(f"  {name:26s} {f}:{ln}")
json.dump({"commit":commit(),"refs":out}, open("all_log/doc_linerefs.json","w"), indent=2, ensure_ascii=False)
print(f"\n저장 → all_log/doc_linerefs.json (commit {commit()})")
