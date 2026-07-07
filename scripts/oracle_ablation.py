#!/usr/bin/env python3
"""Oracle-prefix teacher-forcing ablation: 병목이 retrieval인가 model capacity인가?

각 target 정리의 gold 증명 P=[t1..tn]에 대해, 모든 prefix 길이 k(0..n-1)에서:
  - oracle prefix(gold t1..tk 강제) 상태 → rango retrieval + tactic generation
  - 생성한 top-k tactic을 gold t(k+1)과 비교(정규화 exact match) + 점수 기록
조건:
  A(normal)     : 표준 rango retrieval
  B(gold-lemma) : gold tactic이 참조한 lemma를 premise로 주입   (--cond B)
  (C 실행/gold-tactic 검증은 후속)
출력: 상세 md (target×prefix마다 입력·retrieval·생성·gold·match) + summary 통계.

사용: python3 scripts/oracle_ablation.py --alias rango --num-files 20 --out all_log/oracle_rango.md
"""
import argparse, os, re, sys, json, time
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))

from coqstoq import Split
from data_management.dataset_file import DatasetFile
from data_management.sentence_db import SentenceDB
from model_deployment.tactic_gen_client import (
    tactic_conf_update_ips,
    tactic_gen_client_from_conf,
)
from model_deployment.conf_utils import (
    wait_for_servers, start_servers, tactic_gen_to_client_conf,
)
from util.util import clear_port_map
import run_thm

DATA_LOC = Path("raw-data/coqstoq-test/data_points")
SENTENCE_DB = Path("raw-data/coq-dataset/sentences.db")


def norm(t: str) -> str:
    """tactic 정규화: 공백 축약, 끝 마침표/불릿 정리."""
    t = t.strip()
    t = re.sub(r"\s+", " ", t)
    return t.rstrip(".").strip()


_TRIVIAL = {"proof", "qed", "defined", "abstract", "admitted"}


def is_trivial(gold: str) -> bool:
    """Proof./Qed./Defined./불릿-only 등 구조적 스텝 — capacity 측정서 제외."""
    n = norm(gold).lower()
    if n in _TRIVIAL or n == "":
        return True
    if all(c in "*-+{} " for c in norm(gold)):  # 불릿만
        return True
    return False


def build_client(alias: str):
    confs = run_thm.get_tactic_confs(alias, Split.TEST)
    clean, all_cmds, nxt = [], [], 0
    for c in confs:
        cc, n, cmds = tactic_gen_to_client_conf(c, nxt)
        all_cmds.extend(cmds); clean.append(cc); nxt = n
    procs = []
    if all_cmds:
        clear_port_map()
        procs = start_servers(all_cmds)
        port_map = wait_for_servers(nxt)
        for cc in clean:
            tactic_conf_update_ips(cc, port_map)
    client = tactic_gen_client_from_conf(clean[0])
    return client, procs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alias", default="rango")
    ap.add_argument("--num-files", type=int, default=20, help="테스트 파일 수")
    ap.add_argument("--max-proofs-per-file", type=int, default=10)
    ap.add_argument("--max-steps-per-proof", type=int, default=40)
    ap.add_argument("--nbest", type=int, default=8, help="생성 후보 수(top-k)")
    ap.add_argument("--detail", action="store_true", help="retrieval/입력을 md에 상세 기록(2배 retrieval)")
    ap.add_argument("--out", default="all_log/oracle_ablation.md")
    args = ap.parse_args()

    sdb = SentenceDB.load(SENTENCE_DB)
    files = sorted(DATA_LOC.glob("*.v"))[: args.num_files]
    client, procs = build_client(args.alias)

    n_steps = n_top1 = n_topk = 0
    by_pos = {}  # prefix 길이 bucket -> [top1_hits, total]
    detail = []  # md 라인

    detail.append(f"# Oracle-prefix teacher-forcing ablation — `{args.alias}`\n")
    detail.append(f"> 각 target×prefix에서 oracle prefix(gold) 상태 → retrieval+생성 → gold와 비교.\n")
    detail.append(f"> exact-match(정규화 문자열)은 **하한**(다른 유효 tactic 미인정). nbest={args.nbest}\n")

    try:
        for fi, fpath in enumerate(files):
            try:
                dp = DatasetFile.load(fpath, sdb)
            except Exception as e:
                detail.append(f"\n## [skip] {fpath.name}: load 실패 {e}\n")
                continue
            for pi, proof in enumerate(dp.proofs[: args.max_proofs_per_file]):
                thm_txt = proof.theorem.term.text.strip().replace("\n", " ")[:150]
                nsteps = min(len(proof.steps), args.max_steps_per_proof)
                if nsteps == 0:
                    continue
                detail.append(f"\n## {fpath.name} · proof#{pi} — `{thm_txt}`  ({len(proof.steps)} steps)\n")
                for k in range(nsteps):
                    step = proof.steps[k]
                    gold = step.step.text
                    if is_trivial(gold) or not step.goals:
                        continue  # 구조적 스텝/무-goal 제외 (capacity 측정 무의미)
                    goal_txt = " / ".join(g.goal for g in step.goals)[:200]
                    try:
                        # retrieval/입력 캡처용 example (get_recs가 내부서 재생성하나, 상세기록 위해)
                        ex = None
                        if args.detail:
                            try:
                                ex = client.formatters[0].example_from_step(k, proof.proof_idx, dp)
                            except Exception:
                                ex = None
                        res = client.get_recs(k, proof, dp, args.nbest, beam=True)
                        cands = list(zip(res.next_tactic_list, res.score_list))
                    except Exception as e:
                        detail.append(f"- step {k}: get_recs 실패 {e}\n")
                        continue
                    n_steps += 1
                    gnorm = norm(gold)
                    top1_hit = bool(cands) and norm(cands[0][0]) == gnorm
                    topk_hit = any(norm(c) == gnorm for c, _s in cands)
                    n_top1 += int(top1_hit); n_topk += int(topk_hit)
                    bucket = min(k, 10)
                    b = by_pos.setdefault(bucket, [0, 0]); b[0] += int(top1_hit); b[1] += 1
                    # 상세 기록
                    mark = "✅top1" if top1_hit else ("🔶topk" if topk_hit else "❌miss")
                    detail.append(f"\n### step {k} — {mark}")
                    detail.append(f"- **goal(입력 상태)**: `{goal_txt}`")
                    if ex is not None:
                        rp = (ex.proofs or [])[:2]
                        rprem = (ex.premises or [])[:3]
                        if rp:
                            detail.append(f"- **retrieval 증명 top{len(rp)}**: " +
                                          " ; ".join(f"`{p.strip()[:90].replace(chr(10),' ')}`" for p in rp))
                        if rprem:
                            detail.append(f"- **retrieval premise top{len(rprem)}**: " +
                                          " ; ".join(f"`{p.strip()[:70].replace(chr(10),' ')}`" for p in rprem))
                    detail.append(f"- **gold**: `{norm(gold)}`")
                    cand_str = " · ".join(f"`{norm(c)}`({s:.2f})" for c, s in cands[:5])
                    detail.append(f"- **생성 top{min(5,len(cands))}**: {cand_str}")
        # summary
        rate1 = n_top1 / max(1, n_steps)
        ratek = n_topk / max(1, n_steps)
        summ = [
            "\n---\n# Summary\n",
            f"- 총 (target,prefix) 스텝: **{n_steps}**",
            f"- **top-1 exact-match**: {n_top1}/{n_steps} = **{rate1:.1%}**",
            f"- **top-{args.nbest} exact-match**: {n_topk}/{n_steps} = **{ratek:.1%}**",
            "\n## prefix 위치별 top-1 (0..9, 10=10+)\n",
            "| pos | top1 | n | rate |", "|---|---|---|---|",
        ]
        for pos in sorted(by_pos):
            h, t = by_pos[pos]
            summ.append(f"| {pos} | {h} | {t} | {h/max(1,t):.1%} |")
        header = "\n".join(summ) + "\n"
        with open(args.out, "w") as f:
            f.write("\n".join(detail[:3]) + "\n" + header + "\n".join(detail[3:]) + "\n")
        print(f"[oracle] steps={n_steps} top1={rate1:.1%} top{args.nbest}={ratek:.1%} → {args.out}")
    finally:
        for p in procs:
            try: p.kill()
            except Exception: pass


if __name__ == "__main__":
    main()
