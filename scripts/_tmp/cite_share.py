"""타깃 토큰 중 인용이 차지하는 비율 — loss 가 인용으로 희석되는지 확인."""
import os, sys, json, logging, statistics
os.environ.setdefault("HF_HUB_OFFLINE","1"); os.environ.setdefault("TOKENIZERS_PARALLELISM","false")
os.environ.update(dict(AUGMENT_V2="1", RERANK_PREMISES="1", INJECT_TYPES="1", INJECT_DEFS="1",
    HARD_SEQ_LEN="4096", TYPES_TOKENS="300", DEFS_TOKENS="300",
    FUNC_DEFS_PATH="data/func_defs_v3.json",
    CITE_TARGET="1", NORMALIZE_NAMES="1", NORMALIZE_RATE="0.5", TYPE_FACTS="1", DISTRACTORS="2"))
sys.path.insert(0,'src'); logging.disable(logging.CRITICAL)
import yaml
from transformers import AutoTokenizer
from tactic_gen.lm_example import LmExample
from tactic_gen.tactic_data import example_collator_conf_from_yaml, example_collator_from_conf
cc=yaml.safe_load(open('models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml'))
col=example_collator_from_conf(example_collator_conf_from_yaml(cc['example_collator']))
tok=AutoTokenizer.from_pretrained('deepseek-ai/deepseek-coder-1.3b-instruct')
nt=lambda s: len(tok(s or "", add_special_tokens=False)['input_ids'])
steps=[]
for line in open('data/grpo_rollouts/goldsft_bs2.jsonl'):
    g=json.loads(line)
    for a in g['attempts']:
        if a['reward']<1.0: continue
        for st in a['steps']:
            if st.get('example') and st.get('tactic'):
                e=LmExample.from_json(st['example']); e.next_steps=[st['tactic']]; steps.append(e)
                if len(steps)>=400: break
        if len(steps)>=400: break
    if len(steps)>=400: break
cs=[]; ts=[]; sh=[]
for e in steps:
    p=col.collate(tok,e)
    tail=p.split('[TACTIC]')[-1]
    if '[USES]' not in tail: continue
    i=tail.find('\n', tail.find('[USES]'))
    cite=tail[:i+1]; tac=tail[i+1:]
    c,t=nt(cite),nt(tac)
    if c+t==0: continue
    cs.append(c); ts.append(t); sh.append(c/(c+t))
print(f"■ 타깃 구성 ({len(sh)}개 예제)")
print(f"   인용 토큰   중앙 {statistics.median(cs):.0f}")
print(f"   tactic 토큰 중앙 {statistics.median(ts):.0f}")
print(f"   ★ 인용이 차지하는 비율: 중앙 {statistics.median(sh)*100:.0f}%  평균 {statistics.mean(sh)*100:.0f}%")
print(f"\n   → loss 는 타깃 토큰 평균이므로, 인용이 쉬우면 **tactic 이 나아지지 않아도** 평균이 내려간다.")
print(f"     v2(인용 없음) 와 loss 절대값을 직접 비교하면 안 된다.")
