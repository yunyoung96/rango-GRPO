#!/usr/bin/env python3
"""GRPO rollout 수집기 — 정책 π_old로 정리마다 G개 증명 시도 생성 + Coq 검증 → 그룹 jsonl.

각 시도(attempt): 현재 상태에서 next-tactic 1개 샘플(temperature) → check_proof 적용,
COMPLETE(보상1)/INVALID·max_steps(보상0)까지 반복. step마다 (LmExample, tactic) 기록
(서버가 하던 collation을 학습 때 동일 재현하려 example_json 저장).

출력 jsonl(줄=그룹):
  {"theorem": <idx>, "attempts": [{"steps":[{"example":<json>,"tactic":str}], "reward":0/1}, ...]}

rollout은 서버(retrieval)+Coq이 필요 → 평가/실행 단계에서 구동. grpo_train.py가 소비.
★OCaml 무관.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from model_deployment.proof_manager import ProofManager, TacticResult
from model_deployment.tactic_gen_client import TacticGenClient
from model_deployment.straight_line_searcher import (
    StraightLineSuccess,
    StraightLineFailure,
)


# ── multi-turn 에러 피드백 A/B 프로브 (MT_PROBE=1) ─────────────────────────────
#   질문: 1.3B(rango)가 coq-lsp 에러를 받으면 INVALID를 더 잘 고치나?
#   INVALID state에서 같은 예산(n샘플)으로 A0/A1 비교(설계 A = MULTITURN_DESIGN.md, 주석 in-format):
#     A0(대조): [STATE]만으로 재샘플 n개 → valid 있나
#     A1(처리): [STATE] + (* Failed: <tactic> ==> <error> *) 주석을 SCRIPT에 얹어 재샘플 n개 → valid 있나
#   A1 valid율 > A0면 에러 활용 능력 있음 → multi-turn GRPO로. rollout 흐름은 안 건드리고 관찰·기록만.
from model_deployment.model_result import ModelResult as _MTModelResult


def _mt_errtype(e: str) -> str:
    el = (e or "").lower()
    if "unify" in el or "unification" in el:
        return "unify"
    if "not found" in el or "unbound" in el or "no such" in el or "not exist" in el:
        return "not_found"
    if "syntax error" in el or "illegal" in el or "unexpected" in el or "parse error" in el:
        return "syntax"
    if not el.strip():
        return "empty"
    return "other"


def _mt_gen_and_check(tactic_client, proof_manager, proof, theorem, prefix, ex_json, n):
    """example(json) 프롬프트로 n개 후보 생성 → 각 coq-lsp 검증. (fixed:bool, valid_tac, tried:list)."""
    req = {
        "method": "get_recs",
        "params": [ex_json, n, proof.proof_text_to_string(include_theorem=False), False, None],
        "jsonrpc": "2.0", "id": 1,
    }
    url = getattr(tactic_client, "urls", [None])[0]
    resp = tactic_client.session.post(url, json=req).json()
    cands = _MTModelResult.from_json(resp["result"]).next_tactic_list
    tried, seen = [], set()
    for c in cands:
        if c in seen:
            continue
        seen.add(c); tried.append(c)
        r = proof_manager.check_proof(prefix + c, theorem)
        if r.tactic_result in (TacticResult.VALID, TacticResult.COMPLETE):
            return True, c, tried
    return False, None, tried


def _mt_probe(tactic_client, proof_manager, proof, example, prefix,
              failed_tactic, error, theorem, meta):
    """한 INVALID state에서 A0(에러없이)/A1(에러주석)로 각각 재생성·검증하고 JSONL 기록. 절대 rollout을 안 깨뜨림."""
    try:
        out_path = os.environ.get("MT_PROBE_OUT", "/tmp/mt_probe.jsonl")
        cap = int(os.environ.get("MT_PROBE_MAX", "120"))   # 전역 기록 상한(폭주·비용 방지)
        try:
            if sum(1 for _ in open(out_path)) >= cap:
                return
        except FileNotFoundError:
            pass
        n = int(os.environ.get("MT_PROBE_N", "8"))
        lines = [x for x in (error or "").strip().splitlines() if x.strip()]
        err1 = lines[0][:180] if lines else "(no message)"
        comment = ("\n(* Failed here — do NOT repeat this, pick a DIFFERENT tactic:\n"
                   f"   {failed_tactic.strip()}   ==>   {err1} *)")
        ex0 = example.to_json()
        ex1 = dict(ex0)
        ex1["proof_script"] = (ex0.get("proof_script") or "") + comment
        a0, t0, tr0 = _mt_gen_and_check(tactic_client, proof_manager, proof, theorem, prefix, ex0, n)
        a1, t1, tr1 = _mt_gen_and_check(tactic_client, proof_manager, proof, theorem, prefix, ex1, n)
        rec = {
            **(meta or {}),
            "failed_tactic": failed_tactic.strip()[:120],
            "error": err1,
            "error_type": _mt_errtype(error),
            "a0_fixed": a0, "a0_tactic": t0,
            "a1_fixed": a1, "a1_tactic": t1,
            "n": n,
        }
        with open(out_path, "a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


def rollout_attempt(
    tactic_client: TacticGenClient,
    proof_manager: ProofManager,
    theorem: Any,
    initial_proof: str,
    max_steps: int,
    temperature_seed: Optional[int] = None,
    value_fn=None,           # (E2 dense reward) goals:list[str]->float ∈(0,1). None=binary.
    shaping_coef: float = 0.3,
    max_retries: int = 0,    # INVALID 시 같은 state 에서 재샘플링할 횟수. 0=기존(첫 실수에 즉사)
    subgoal_reward: bool = False,  # leaf-first subgoal 단위: focused subgoal 닫히면(goal수↓) reward=1(Qed 불필요)
) -> dict:
    """한 증명 시도. 반환 {"steps":[{example,tactic,result,state_key}], "reward":float}.
    binary: COMPLETE=1 else 0. dense(value_fn): 미완이면 마지막 valid 상태의 QED value×coef.

    ★ max_retries (GRPO_ROLLOUT_ANALYSIS.md §7 P1 처방):
      기존 롤아웃은 tactic 하나가 INVALID 나면 **그 시도를 통째로 버렸다**. 실측 결과 실패의 100%가
      이 경로였고, per-step 에러율 18~21% × 증명 길이 14 → 완주율 5.8% → dead group 73%.
      INVALID 는 **state 를 바꾸지 않는다**(Coq이 거부했으니까). 그러니 같은 state 에서 다시 뽑으면 된다.
      유효 통과확률이 p → 1−(1−p)^(1+k) 로 오른다.

    ★ on-policy 성질은 유지된다(중요): 재샘플링해도 **모든 tactic 은 그 state 에서 π 로부터 샘플된 것**이고,
      INVALID 였던 tactic도 (state, tactic, result=INVALID) 로 **전부 기록**한다. flatten_group 이
      (state,tactic) 쌍 단위로 학습하므로 액션 수준에서 on-policy 다. 바뀌는 것은 방문하는 state 분포뿐인데,
      그건 기존 GRPO도 보정하지 않는다.
      → 게다가 INVALID 기록은 PRM(process reward)의 **음수 신호 그 자체**라 버리면 안 되는 데이터다."""
    if temperature_seed is not None and hasattr(tactic_client, "set_seed"):
        tactic_client.set_seed(temperature_seed)
    steps: list[dict] = []
    _mt_done = False   # MT_PROBE: 정리당 첫 INVALID에서 한 번만 A/B 프로브
    check = proof_manager.check_proof(initial_proof, theorem)
    if check.tactic_result == TacticResult.COMPLETE:
        return {"steps": [], "reward": 1.0}   # ★ invauto: initial_proof(=invertible+auto)가 통째로 닫음(순수-Coq, 모델 불필요)
    if check.tactic_result != TacticResult.VALID or check.new_proof is None:
        return {"steps": [], "reward": 0.0}
    script = initial_proof
    reward = 0.0
    last_valid_goals = _goals_str(check)  # dense reward용 마지막 valid 상태 goal들
    seed_level = len(last_valid_goals)    # subgoal_reward: seed 시점 열린 goal 수. 이 아래로 떨어지면 focused subgoal 닫힘
    # ★ planner-first(train dead group 축소 실험): 32B가 opening 분해를 열고, 이후는 rango가 이어감.
    #   PLANNER_FIRST_URL env로 켬. 최초 상태(initial_proof 없음)에서만.
    _pf_url = os.environ.get("PLANNER_FIRST_URL")
    #  hedge: 짝수 seed만 opener, 홀수는 순수 rango → rango가 풀던 것 보존(regress 방지)
    _hedge = os.environ.get("PLANNER_HEDGE", "0") == "1"
    _use_opener = _pf_url and not initial_proof and (not _hedge or (temperature_seed or 0) % 2 == 0)
    _opener_stopped = False   # tac_mode opener가 NMD("No More Decomposition")를 내면 True → 이후 opener 호출 중단
    #  PLANNER_PRELOOP=1: opener-once(with compound) — opener가 '전체 opening'을 첫 한 번에(NMD까지) 다 하고 rango.
    if _use_opener and os.environ.get("PLANNER_PRELOOP", "0") == "1":
        script, check, _done = _apply_planner_opening_iter(
            _pf_url, proof_manager, theorem, tactic_client, script, check, steps)
        _opener_stopped = True   # pre-loop 끝 → 이후는 rango만
        if _done:
            return {"steps": steps, "reward": 1.0}
        if check is None or check.new_proof is None:
            return {"steps": steps, "reward": 0.0}
        last_valid_goals = _goals_str(check)
        seed_level = len(last_valid_goals)
    #  PLANNER_EVERY=1 이면 pre-loop opening 대신 매 스텝(모든 분해 지점) opener 사용(아래 루프).
    elif _use_opener and os.environ.get("PLANNER_EVERY", "0") != "1":
        script, check, _done = _apply_planner_opening(_pf_url, proof_manager, theorem, script, check, steps)
        if _done:
            return {"steps": steps, "reward": 1.0}
        if check is None or check.new_proof is None:
            return {"steps": steps, "reward": 0.0}
        last_valid_goals = _goals_str(check)
        seed_level = len(last_valid_goals)
    for _ in range(max_steps):
        new_proof = check.new_proof
        if new_proof is None:
            break
        dset = proof_manager.build_dset_file(new_proof)
        proof = dset.proofs[-1]
        # 서버가 만들 example 재현: 현재 step 기준 formatter example.
        fmt = tactic_client.formatters[0]
        example = fmt.example_from_step(len(proof.steps) - 1, proof.proof_idx, dset)
        prefix = proof.proof_prefix_to_string(proof.steps[-1], include_theorem=False)
        # ★ RECORD_TOPK=1: rango 후보 top-k(+score)를 step에 기록(랭킹 분석용). 기본 n=1(기존 동작).
        _topk = int(os.environ.get("RECORD_TOPK", "0") or "0")
        recs = tactic_client.get_recs(
            len(proof.steps) - 1, proof, dset, max(_topk, 1),
            beam=False, file_prefix=proof_manager.file_prefix,
        )
        if not recs.next_tactic_list:
            break
        _rango_topk = None
        if _topk:
            _sc = getattr(recs, "score_list", None) or getattr(recs, "scores", None) or []
            _rango_topk = [{"tactic": t, "score": (float(_sc[i]) if i < len(_sc) else None)}
                           for i, t in enumerate(recs.next_tactic_list[:_topk])]
        # state_key = 이 tactic 을 적용하기 **전** 상태(Math-Shepherd MC 추정용; state 공유 시에만 유효).
        # result = coq-lsp 판정(process reward, 2606.20068). 이게 없으면 per-tactic credit 계산 불가.
        state_key = "\n===\n".join(_goals_str(check))
        cur_check = check
        seen: dict[str, Any] = {}   # 같은 state 에서 이미 판정난 tactic → Coq 호출 절약
        advanced = False

        # ★ 하이브리드: [모델 tactic] + [targeted-invertible 후보들(destruct/induction/inversion on vars)] 을 순차 시도(검색).
        _hyb = os.environ.get("SUBGOAL_HYBRID", "0") == "1"
        _tc = _targeted_cands(_goals_str(check)) if _hyb else []
        # ★ opener-every(PLANNER_EVERY=1): 매 스텝(=이 분해 지점) opener에게 물어 후보 최우선 시도.
        #   opener 롤아웃만(hedge 홀수 seed 제외). 도달률↑(중첩 subgoal까지 opener가 유도). 캐시는 서버가.
        _oc = []
        if _use_opener and not _opener_stopped and os.environ.get("PLANNER_EVERY", "0") == "1":
            # tac_mode opener: retrieval(premises/proofs)도 보냄. NMD 반환 시 이후 opener 호출 중단.
            _prem = list(getattr(example, "premises", None) or [])
            _prf = list(getattr(example, "proofs", None) or [])
            _oc = _planner_http_plan(_pf_url, "\n".join(_goals_str(check)), _prem, _prf)
            if _oc == ["__NMD__"]:
                _opener_stopped = True   # opener가 "분해 끝" → 이후 스텝은 executor만
                _oc = []
            else:
                _oc = _oc[:3]
        _extra = _oc + _tc     # opener 후보 먼저, 그다음 hybrid
        _nattempt = 1 + max(max_retries, len(_extra))
        for attempt_i in range(_nattempt):
            if attempt_i < len(_extra):
                tactic = _extra[attempt_i]           # opener/hybrid 후보 우선
            elif attempt_i == len(_extra):
                tactic = recs.next_tactic_list[0]    # rango top
            else:
                # 같은 state 에서 π 로부터 다시 뽑는다(온도 샘플링이라 매번 다른 결과)
                r2 = tactic_client.get_recs(
                    len(proof.steps) - 1, proof, dset, 1,
                    beam=False, file_prefix=proof_manager.file_prefix,
                )
                if not r2.next_tactic_list:
                    break
                tactic = r2.next_tactic_list[0]

            if tactic in seen:
                # 이미 본 tactic(반드시 INVALID — VALID/COMPLETE 는 즉시 break).
                # 재기록하면 같은 음수 예제가 1+k 번 중복돼 학습 가중이 부풀고
                # normalize_process 의 그룹 mean/std 가 왜곡된다 → 재시도만 소모하고 스킵.
                continue
            # ★ 하이브리드(SUBGOAL_HYBRID=1): rango tactic 뒤에 invertible-hyp 포화 + auto-close 를 붙여
            #   각 노드에서 "rango(어려운 스텝) → invertible+auto(쉬운 leaf 무료 닫기)" 재귀. (기본 OFF=기존과 동일)
            applied = tactic
            if os.environ.get("SUBGOAL_HYBRID", "0") == "1":
                applied = tactic + ("\nall: (try (repeat (match goal with"
                                    " | [ H : _ /\\ _ |- _ ] => destruct H"
                                    " | [ H : ex _ |- _ ] => destruct H"
                                    " | [ H : _ /\\ _ |- _ ] => destruct H end));"
                                    " try (solve [ auto | eauto | lia | congruence | intuition | now eauto ])).")
            res = proof_manager.check_proof(prefix + applied, new_proof.theorem)
            seen[tactic] = res
            # INVALID 였던 tactic 도 전부 기록한다 — PRM 의 음수 신호이자, 버리면 안 되는 데이터.
            steps.append({
                "example": example.to_json(),
                "tactic": tactic,
                "state_key": state_key,
                "result": res.tactic_result.name,   # VALID | INVALID | COMPLETE
                "retry": attempt_i,                  # 0=첫 샘플, 1+=재샘플
                "opener_step": (tactic in _oc),      # opener-every가 제안한 tactic(SFT서 제외)
                **({"rango_topk": _rango_topk} if _rango_topk is not None else {}),  # RECORD_TOPK: rango 후보 랭킹
                **({"coq_error": proof_manager.last_error()[:300]}                    # ★ MULTITURN 점검: coq-lsp 에러
                   if os.environ.get("RECORD_ERROR", "0") == "1" and res.tactic_result == TacticResult.INVALID else {}),
            })
            # ★ MT_PROBE: 정리당 첫 (executor) INVALID에서 A0/A1 에러피드백 프로브 1회. 관찰만.
            if (os.environ.get("MT_PROBE", "0") == "1" and not _mt_done
                    and res.tactic_result == TacticResult.INVALID
                    and attempt_i >= len(_extra)):
                _mt_probe(tactic_client, proof_manager, proof, example, prefix,
                          tactic, proof_manager.last_error(), new_proof.theorem,
                          {"proof_idx": getattr(proof, "proof_idx", None)})
                _mt_done = True
            if res.tactic_result == TacticResult.COMPLETE:
                reward = 1.0
                cur_check = res
                advanced = True
                break
            if res.tactic_result == TacticResult.VALID:
                last_valid_goals = _goals_str(res)
                cur_check = res
                script = prefix + tactic
                advanced = True
                # leaf-first subgoal 단위: goal 수가 seed 레벨 아래로 = focused subgoal 닫힘 → reward=1(Qed 불필요)
                if subgoal_reward and len(last_valid_goals) < seed_level:
                    reward = 1.0
                break
            # INVALID → state 는 그대로. 재시도.

        check = cur_check
        if reward >= 1.0:
            break
        if not advanced:
            break  # 재시도를 다 쓰고도 유효 tactic 을 못 찾음 → 시도 종료
    # dense reward: 미완(reward=0)이고 value_fn 있으면 마지막 valid 상태의 QED value로 부분보상.
    if reward == 0.0 and value_fn is not None and steps:
        try:
            reward = float(shaping_coef) * float(value_fn(last_valid_goals))
        except Exception:
            reward = 0.0
    return {"steps": steps, "reward": reward}


_IND_TYPES = {'nat', 'positive', 'Z', 'N', 'bool', 'list', 'option', 'comparison',
              'ident', 'block', 'val', 'memval', 'instruction', 'sumbool', 'prod'}
_EXCL = ('Type', 'Set', 'Prop', 'R', 'Q', 'radix')
# ③ 타입-지향 결정절차 템플릿(CompCert 특화). {a}=단일변수, {b}=동타입 두번째 변수.
_DEC_UN = {'bool', 'val', 'option', 'comparison', 'sumbool'}          # → destruct a
_DEC_CONST = {   # 상수 0 비교
    'Z': ['zeq {a} 0', 'zlt {a} 0', 'zle 0 {a}'],
    'R': ['Rle_or_lt 0 {a}', 'Rlt_le_dec 0 {a}'],
}
_DEC_BIN = {     # 두 동타입 변수쌍
    'Z': ['zeq {a} {b}', 'zlt {a} {b}', 'zle {a} {b}'],
    'R': ['Rle_or_lt {a} {b}', 'Rlt_le_dec {a} {b}'],
    'positive': ['peq {a} {b}'], 'ident': ['peq {a} {b}'],
    'nat': ['Nat.eq_dec {a} {b}', 'le_lt_dec {a} {b}'],
}


def _scrutinees(text: str) -> list[str]:
    """match E with / if E then 의 E 추출(괄호 balanced, ≤80자, 개행X). compound destruct 핵심 소스."""
    out = []
    for pat in (r'\bmatch\s+(.+?)\s+with\b', r'\bif\s+(.+?)\s+then\b'):
        for m in re.finditer(pat, text):
            e = m.group(1).strip()
            if e and '\n' not in e and len(e) <= 80 and e.count('(') == e.count(')'):
                out.append(e)
    return list(dict.fromkeys(out))


def _targeted_cands(goals: list) -> list[str]:
    """4단계 후보 생성(①문맥변수 ②scrutinee ③결정절차 ④inversion) → dedup → 앞 18개.
    유효성은 Coq LSP가 필터(무효 후보 버려짐)."""
    if not goals:
        return []
    text = str(goals[0])
    hyp_txt = text.split('\n\n', 1)[0]   # 첫 빈 줄 = 가설/결론 경계
    dv, pr = [], []
    byty: dict = {}
    for ln in hyp_txt.split('\n'):
        if ln.strip() == '':
            break
        m = re.match(r"^([\w', ]+?)\s*:\s*(.+)$", ln)
        if not m:
            continue
        typ = m.group(2).strip()
        head = typ.split()[0] if typ.split() else typ
        for nm in re.split(r"[,\s]+", m.group(1).strip()):
            if not nm:
                continue
            if '->' not in typ:
                if head in _IND_TYPES or (head[:1].isupper() and head not in _EXCL):
                    dv.append(nm)          # ① 문맥 변수
                byty.setdefault(head, []).append(nm)   # ③ 타입별 그룹
            if ('=' in typ or nm[0] == 'H') and '->' not in typ:
                pr.append(nm)
    out: list[str] = []
    for v in dv[:3]:                       # ① destruct/induction
        out += [f'\ndestruct {v}.', f'\ninduction {v}.']
    for e in _scrutinees(text)[:4]:        # ② scrutinee
        out.append(f'\ndestruct ({e}).')
    for head, vs in byty.items():          # ③ 결정절차
        if head in _DEC_UN:
            out.append(f'\ndestruct {vs[0]}.')
        for tmpl in _DEC_CONST.get(head, []):
            out.append(f'\ndestruct ({tmpl.format(a=vs[0])}).')
        if head in _DEC_BIN and len(vs) >= 2:
            for tmpl in _DEC_BIN[head]:
                out.append(f'\ndestruct ({tmpl.format(a=vs[0], b=vs[1])}).')
    for h in pr[:2]:                       # ④ inversion
        out += [f'\ninversion {h}.']
    # ⑤ forall-bound 변수(intros 전 induction) + generic premise 귀납(CompCert 흔함)
    goal_txt = text.split('\n\n', 1)[1] if '\n\n' in text else text
    fm = re.search(r'\bforall\s+\(?([\w\s\']+?)\)?\s*[:,]', goal_txt)
    if fm:
        for nm in fm.group(1).split()[:2]:
            out += [f'\ninduction {nm}.', f'\ndestruct {nm}.']
    out.append('\ninduction 1.')
    return list(dict.fromkeys(out))[:18]


def _planner_http_plan(url: str, goal_str: str, premises=None, proofs=None) -> list[str]:
    """persistent planner_server에 goal(+retrieval) 보내 분해 후보(tactic 리스트) 받음. 실패=[].
    tac_mode opener면 premises/proofs도 보내고, 응답이 ["__NMD__"]면 '분해 끝' 신호."""
    import urllib.request
    try:
        body = {"goal": goal_str}
        if premises is not None:
            body["premises"] = premises
        if proofs is not None:
            body["proofs"] = proofs
        data = json.dumps(body).encode()
        req = urllib.request.Request(url.rstrip("/") + "/plan", data=data,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return list(json.loads(r.read().decode()).get("plan", []))
    except Exception:
        return []


def _apply_planner_opening(url, proof_manager, theorem, script, check, steps):
    """★ planner-first(train dead group 축소 실험): 32B planner가 제안한 opening 분해를
    순서대로 적용(각 coq-lsp 검증, 첫 INVALID서 중단)한 뒤 상태를 반환 → 이후는 rango 롤아웃.
    반환 (script, check, done). done=True면 opening만으로 COMPLETE(드묾)."""
    goal_str = "\n".join(_goals_str(check))
    plan = _planner_http_plan(url, goal_str)
    for tac in plan:
        new_proof = check.new_proof
        if new_proof is None:
            break
        res = proof_manager.check_proof(script + tac, theorem)
        steps.append({"example": None, "tactic": tac, "state_key": "\n===\n".join(_goals_str(check)),
                      "result": res.tactic_result.name, "retry": 0, "planner_opening": True})
        if res.tactic_result == TacticResult.COMPLETE:
            return script + tac, res, True
        if res.tactic_result == TacticResult.VALID:
            script = script + tac
            check = res
        else:
            break   # INVALID → opening 중단(그 전까지만), 이후 rango가 이어감
    return script, check, False


def _apply_planner_opening_iter(url, proof_manager, theorem, tactic_client, script, check, steps, max_open=10):
    """★ opener-once(with compound, tac_mode): opener가 '전체 opening'을 **첫 한 번에** 다 한다.
    매 iteration마다 현재 state의 retrieval(premises/proofs)을 넣어 opener에게 다음 opening tactic 1개를 받고
    적용(coq-lsp 검증) → NMD("__NMD__")/빈응답/INVALID 나올 때까지 반복 → 그 뒤는 rango가 이어감.
    (PLANNER_EVERY의 매-스텝 interleave와 달리, opening을 연속 블록으로 처리 후 opener 종료.)
    반환 (script, check, done)."""
    # ★ Proof. 는 pre-loop이 직접(opener에게 안 물음) — opener가 'Proof.'만 반복하는 버그 방지.
    #   opener는 post-Proof state부터 intros/destruct/... 를 낸다(그렇게 학습됨).
    if "Proof." not in script:
        res0 = proof_manager.check_proof(script + "\nProof.", theorem)
        steps.append({"example": None, "tactic": "\nProof.", "state_key": "\n===\n".join(_goals_str(check)),
                      "result": res0.tactic_result.name, "retry": 0, "planner_opening": True})
        if res0.tactic_result == TacticResult.COMPLETE:
            return script + "\nProof.", res0, True
        if res0.tactic_result == TacticResult.VALID:
            script = script + "\nProof."
            check = res0
    _prev_goal = "\n".join(_goals_str(check))
    _applied = set()
    for _ in range(max_open):
        new_proof = check.new_proof
        if new_proof is None:
            break
        # 현재 state의 retrieval(example) 재현 — 메인 루프와 동일 방식.
        try:
            dset = proof_manager.build_dset_file(new_proof)
            proof = dset.proofs[-1]
            fmt = tactic_client.formatters[0]
            example = fmt.example_from_step(len(proof.steps) - 1, proof.proof_idx, dset)
            prem = list(getattr(example, "premises", None) or [])
            prf = list(getattr(example, "proofs", None) or [])
        except Exception:
            prem, prf = [], []
        goal_str = "\n".join(_goals_str(check))
        plan = _planner_http_plan(url, goal_str, prem, prf)
        if plan == ["__NMD__"] or not plan:
            break   # opener: 분해 끝 → rango가 이어감
        tac = plan[0]
        # no-progress 가드: 같은 tactic 재발 or Proof. 재시도면 중단(무한반복 방지)
        if tac.strip().lstrip("\n") == "Proof." or tac in _applied:
            break
        _applied.add(tac)
        res = proof_manager.check_proof(script + tac, theorem)
        steps.append({"example": None, "tactic": tac, "state_key": "\n===\n".join(_goals_str(check)),
                      "result": res.tactic_result.name, "retry": 0, "planner_opening": True})
        if res.tactic_result == TacticResult.COMPLETE:
            return script + tac, res, True
        if res.tactic_result == TacticResult.VALID:
            script = script + tac
            check = res
            new_goal = "\n".join(_goals_str(check))
            if new_goal == _prev_goal:   # goal 안 바뀜(no-op) → 중단
                break
            _prev_goal = new_goal
        else:
            break   # INVALID → opening 중단, 이후 rango
    return script, check, False


def _goals_str(check) -> list[str]:
    """ProofCheckResult.current_goals → goal 문자열 리스트(QED value 입력)."""
    gs = getattr(check, "current_goals", None)
    if not gs:
        return []
    out = []
    for g in gs:
        try:
            out.append(repr(g))
        except Exception:
            pass
    return out


def rollout_gold(
    tactic_client: TacticGenClient,
    proof_manager: ProofManager,
    theorem: Any,
    initial_proof: str,
    gold_tactics: list[str],
    max_steps: int = 40,
) -> dict:
    """LUFFY(2504.14945): 인간 gold 증명을 환경에서 **재생**한 off-policy 시도.

    각 step 은 rollout_attempt 와 동일 포맷(example/tactic/result/state_key)에 off_policy=True.
    gold tactic 은 샘플링하지 않고 순서대로 강제 적용한다(get_recs 호출 없음 — 모델 질의 안 함).
    example 은 fmt.example_from_step 로 서버와 동일하게 재현(학습 collate_fn 이 이걸 복원).

    반환 {"steps":[...], "reward": 1.0 if COMPLETE else 0.0, "off_policy": True}.
    gold 가 (포맷 불일치 등으로) 중간에 깨지면 그때까지의 valid step 만 남기고 reward=0."""
    steps: list[dict] = []
    check = proof_manager.check_proof(initial_proof, theorem)
    if check.tactic_result != TacticResult.VALID or check.new_proof is None:
        return {"steps": [], "reward": 0.0, "off_policy": True}
    reward = 0.0
    for gtac in gold_tactics[:max_steps]:
        new_proof = check.new_proof
        if new_proof is None:
            break
        dset = proof_manager.build_dset_file(new_proof)
        proof = dset.proofs[-1]
        fmt = tactic_client.formatters[0]
        example = fmt.example_from_step(len(proof.steps) - 1, proof.proof_idx, dset)
        prefix = proof.proof_prefix_to_string(proof.steps[-1], include_theorem=False)
        state_key = "\n===\n".join(_goals_str(check))
        res = proof_manager.check_proof(prefix + gtac, new_proof.theorem)
        steps.append({
            "example": example.to_json(),
            "tactic": gtac,
            "state_key": state_key,
            "result": res.tactic_result.name,
            "retry": 0,
            "off_policy": True,   # ★ LUFFY: clip 없이 shaping 으로 학습(luffy_batch_loss)
        })
        if res.tactic_result == TacticResult.COMPLETE:
            reward = 1.0
            break
        if res.tactic_result == TacticResult.VALID:
            check = res
            continue
        break  # INVALID → gold 재생 깨짐(원문 tactic 이 이 prefix 에 안 붙음). 중단.
    return {"steps": steps, "reward": reward, "off_policy": True}


def mc_value(
    tactic_client: TacticGenClient,
    proof_manager: ProofManager,
    theorem: Any,
    prefix: str,
    k: int,
    max_depth: int,
    seed_base: int,
    max_retries: int = 0,
) -> float:
    """VinePPO(2410.01679) MC value 추정: state(=prefix)에서 k개 롤아웃 → 완결 성공률 = V(s).

    ★ Tree 분기: prefix 를 공유한 채 k개의 서로 다른 continuation 을 뽑는다(온도샘플링).
      기존 retry 처럼 '전체 궤적 재실행'이 아니라 **이 state 에서만 분기**하므로 탐색이 효율적이다.
    """
    if max_depth <= 0:
        return 0.0
    succ = 0
    for i in range(k):
        att = rollout_attempt(
            tactic_client, proof_manager, theorem, prefix, max_depth,
            temperature_seed=seed_base + i + 1, max_retries=max_retries,
        )
        if att["reward"] >= 1.0:
            succ += 1
    return succ / max(k, 1)


def rollout_vine(
    tactic_client: TacticGenClient,
    proof_manager: ProofManager,
    theorem: Any,
    initial_proof: str,
    k_mc: int,
    max_steps: int,
    seed: int,
) -> dict:
    """VinePPO(2410.01679): 한 backbone 궤적 + **각 on-policy state 에서 MC value 추정** →
    step 별 advantage A_t = V(s_{t+1}) − V(s_t).

    핵심(우리 실패진단과의 연결): backward/LUFFY 는 **gold state** 신호라 self-state 로 전이가 안 됐다.
    VinePPO 는 **모델이 실제로 도달한 state** 에서만 V 를 추정하므로 분포 불일치가 없다.
    또 sparse binary 를 **step 별 dense credit** 로 바꾼다(어느 tactic 이 value 를 올렸나).

    각 step: {example, tactic, state_key, result, adv_vine}. adv_vine 을 학습에서 그 예제의 advantage 로.
    V 재사용: V(s_{t+1}) 은 다음 step 의 V(s_t) 로 이월(중복 추정 방지).
    INVALID: 상태 진전 없음 → V_next=0 → A=−V(s_t)(가진 value 를 날린 행동에 벌점)."""
    if seed is not None and hasattr(tactic_client, "set_seed"):
        tactic_client.set_seed(seed)
    check = proof_manager.check_proof(initial_proof, theorem)
    if check.tactic_result != TacticResult.VALID or check.new_proof is None:
        return {"steps": [], "reward": 0.0}
    steps: list[dict] = []
    reward = 0.0
    V_cur = mc_value(tactic_client, proof_manager, theorem, initial_proof,
                     k_mc, max_steps, seed * 1000)
    for t in range(max_steps):
        new_proof = check.new_proof
        if new_proof is None:
            break
        dset = proof_manager.build_dset_file(new_proof)
        proof = dset.proofs[-1]
        fmt = tactic_client.formatters[0]
        example = fmt.example_from_step(len(proof.steps) - 1, proof.proof_idx, dset)
        cur_prefix = proof.proof_prefix_to_string(proof.steps[-1], include_theorem=False)
        state_key = "\n===\n".join(_goals_str(check))
        recs = tactic_client.get_recs(
            len(proof.steps) - 1, proof, dset, 1,
            beam=False, file_prefix=proof_manager.file_prefix,
        )
        if not recs.next_tactic_list:
            break
        tactic = recs.next_tactic_list[0]
        res = proof_manager.check_proof(cur_prefix + tactic, new_proof.theorem)
        if res.tactic_result == TacticResult.COMPLETE:
            V_next = 1.0
        elif res.tactic_result == TacticResult.VALID:
            remaining = max_steps - t - 1
            if remaining <= 0:
                # ★ budget 소진(terminal 실패 아님). value 추정 불가 → V=0 로 −V_cur 벌점을
                #   주면 정상적인 open state 를 dead-end 로 오학습. 이 step 은 학습에서 제외(중단).
                break
            V_next = mc_value(tactic_client, proof_manager, theorem, cur_prefix + tactic,
                              k_mc, remaining, seed * 1000 + (t + 1) * 17)
        else:
            V_next = 0.0  # INVALID: 상태 진전 없음, 이 행동은 dead-end
        steps.append({
            "example": example.to_json(),
            "tactic": tactic,
            "state_key": state_key,
            "result": res.tactic_result.name,
            "adv_vine": float(V_next - V_cur),
        })
        if res.tactic_result == TacticResult.COMPLETE:
            reward = 1.0
            break
        if res.tactic_result == TacticResult.VALID:
            check = res
            V_cur = V_next
            continue
        break  # INVALID → backbone 종료
    return {"steps": steps, "reward": reward}


def rollout_bread(
    tactic_client: TacticGenClient,
    proof_manager: ProofManager,
    theorem: Any,
    initial_proof: str,
    gold_tactics: list[str],
    max_steps: int,
    seed: int,
    max_retries: int = 2,
) -> dict:
    """BREAD(Branched Rollouts from Expert Anchors): 모델 궤적을 진행하되 **막히면(INVALID) 그 depth 의
    gold tactic 을 '다리'로 splice** 하고 이어간다. LUFFY(전체 gold 주입)와 달리 **on-policy 궤적 위**에서
    최소한의 gold 만 쓴다 → self-state 에 더 가깝다(우리 전이문제 완화 기대).

    step: 채택된 것만 기록(VALID model 또는 gold bridge). bridge 는 off_policy=True → --luffy 로 shaping.
    on-policy VALID step 은 off_policy=False → 표준 GRPO. reward=COMPLETE 도달 시 1.
    실패한 INVALID 시도는 기록하지 않는다(성공 궤적을 positive 로 배우는 게 목적, 음수신호는 다른 기법이 담당)."""
    if seed is not None and hasattr(tactic_client, "set_seed"):
        tactic_client.set_seed(seed)
    check = proof_manager.check_proof(initial_proof, theorem)
    if check.tactic_result != TacticResult.VALID or check.new_proof is None:
        return {"steps": [], "reward": 0.0}
    steps: list[dict] = []
    reward = 0.0
    depth = 0
    aligned = True   # 모델이 아직 gold 경로 위에 있는가. 벗어나면 gold_tactics[depth] 가 현재 state 와
                     # 불일치 → 다리 인덱싱이 틀림. 벗어난 뒤로는 gold 다리를 놓지 않는다.
    for _ in range(max_steps):
        new_proof = check.new_proof
        if new_proof is None:
            break
        dset = proof_manager.build_dset_file(new_proof)
        proof = dset.proofs[-1]
        fmt = tactic_client.formatters[0]
        example = fmt.example_from_step(len(proof.steps) - 1, proof.proof_idx, dset)
        cur_prefix = proof.proof_prefix_to_string(proof.steps[-1], include_theorem=False)
        state_key = "\n===\n".join(_goals_str(check))
        chosen = None
        for _i in range(1 + max_retries):  # 모델 시도(+재샘플)
            recs = tactic_client.get_recs(
                len(proof.steps) - 1, proof, dset, 1,
                beam=False, file_prefix=proof_manager.file_prefix,
            )
            if not recs.next_tactic_list:
                break
            tac = recs.next_tactic_list[0]
            res = proof_manager.check_proof(cur_prefix + tac, new_proof.theorem)
            if res.tactic_result in (TacticResult.VALID, TacticResult.COMPLETE):
                chosen = (tac, res, False)
                break
        if chosen is None and aligned and depth < len(gold_tactics):  # 막힘 → gold 다리(정렬돼 있을 때만)
            gtac = gold_tactics[depth]
            gres = proof_manager.check_proof(cur_prefix + gtac, new_proof.theorem)
            if gres.tactic_result in (TacticResult.VALID, TacticResult.COMPLETE):
                chosen = (gtac, gres, True)
        if chosen is None:
            break  # 모델도 gold 도 실패(또는 정렬 이탈) → 종료
        tac, res, is_bridge = chosen
        # 모델이 gold 와 다른 tactic 을 두면 이후 gold 인덱싱을 신뢰할 수 없음 → 정렬 해제.
        if not is_bridge and depth < len(gold_tactics) and tac.strip() != gold_tactics[depth].strip():
            aligned = False
        steps.append({
            "example": example.to_json(), "tactic": tac, "state_key": state_key,
            "result": res.tactic_result.name, "off_policy": is_bridge,
        })
        depth += 1
        if res.tactic_result == TacticResult.COMPLETE:
            reward = 1.0
            break
        check = res
    return {"steps": steps, "reward": reward}


def collect_group(
    tactic_client: TacticGenClient,
    proof_manager: ProofManager,
    theorem: Any,
    theorem_id: int,
    group_size: int,
    max_steps: int,
    initial_proof: str = "",
    value_fn=None,
    shaping_coef: float = 0.3,
    max_retries: int = 0,
    start_label: str = "s0",       # 이 그룹의 시작점 표식("s0" | "curriculum")
    seed_base: int = 0,            # 시드 오프셋. dynamic sampling 재샘플에서 try 마다 달라져야 함(no-op 방지)
    subgoal_reward: bool = False,  # leaf-first subgoal 단위 보상(rollout_attempt 로 전달)
) -> dict:
    """정리 하나 + **하나의 시작 상태**에 대해 G개 시도 → 그룹 하나.

    ⚠️ 한 그룹 안에 서로 다른 시작 상태를 섞으면 안 된다 (GRPO 수학 위배):
      advantage A_i = (r_i − mean)/std 에서 **그룹 평균이 V(s)의 근사 baseline** 역할을 한다.
      이는 그룹 구성원이 **같은 상태 s 에서 출발했을 때만** 성립한다. 쉬운 시작점(중간상태)과
      어려운 시작점(처음)을 한 그룹에 섞으면, advantage 가 "이 궤적이 좋았다"와 "이 시작점이 쉬웠다"를
      뒤섞어 baseline 의 분산감소 논리가 깨진다.
      → backward curriculum 은 **별도 그룹**으로 만든다(searcher 가 collect_group 을 두 번 호출)."""
    attempts = []
    for g in range(group_size):
        att = rollout_attempt(
            tactic_client, proof_manager, theorem, initial_proof or "", max_steps,
            temperature_seed=seed_base + g + 1, value_fn=value_fn, shaping_coef=shaping_coef,
            max_retries=max_retries, subgoal_reward=subgoal_reward,
        )
        attempts.append(att)
    n_solved = sum(1 for a in attempts if a["reward"] >= 1.0)
    print(f"  [rollout] thm {theorem_id} ({start_label}): 완결 {n_solved}/{group_size}, "
          f"보상 {[round(a['reward'],2) for a in attempts]}")
    return {"theorem": theorem_id, "start": start_label, "attempts": attempts}


def append_group(out_path: Path, group: dict) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # ★ 버그수정: workers≥2 면 여러 프로세스가 같은 jsonl 에 동시 append 한다. 레코드가 4KB(PIPE_BUF)
    #   초과하면 O_APPEND 도 원자적이지 않아 줄이 interleave→손상. flock(LOCK_EX)로 직렬화.
    import fcntl
    with out_path.open("a") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            f.write(json.dumps(group, ensure_ascii=False) + "\n")
            f.flush()
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


@dataclass
class GRPORolloutSearchConf:
    """run_thm 인프라 재사용을 위한 '탐색기' 형태의 rollout 수집기 설정.
    .search()가 정리에 G개 시도를 생성·검증해 그룹 jsonl에 append."""
    timeout: int
    group_size: int = 8
    max_steps: int = 20
    out: str = "data/grpo_rollouts/rollouts.jsonl"
    initial_proof: Optional[str] = None
    print_proofs: bool = True
    qed_ckpt: Optional[str] = None      # (E2) dense reward용 QED value 체크포인트. None=binary.
    shaping_coef: float = 0.3
    max_retries: int = 0                # INVALID 시 같은 state 재샘플링 횟수. 0=기존(첫 실수에 즉사)
    curriculum_file: Optional[str] = None   # backward curriculum json (build_backward_curriculum.py)
    curriculum_frac: float = 0.5            # 시도 중 중간상태에서 시작할 비율. 나머지는 s_0
    gold_file: Optional[str] = None         # LUFFY gold 궤적 json (build_gold_trajectories.py)
    vine_k: int = 0                         # VinePPO: state 당 MC value 추정 롤아웃 수(0=off)
    adapt_prefix: bool = False              # 적응형 prefix: curriculum starts 를 정답률로 선택
    probe_k: int = 3                        # adapt_prefix 각 후보 prefix 탐침 롤아웃 수
    dyn_resample: int = 0                   # dynamic sampling: dead s0 그룹 재샘플 최대횟수(0=off)
    bread: bool = False                     # BREAD: INVALID 지점에 gold 한 스텝 다리(gold_file 필요)
    gold_only: bool = False                 # gold 궤적만 replay 기록(SFT 데이터용). on-policy 안 함(gold_file 필요)
    skip_s0: bool = False                    # s0 그룹 생략(subgoal 방법: s0는 항상 dead=gradient 0=낭비). curriculum 그룹만.
    subgoal_reward: bool = False             # leaf-first subgoal 단위: focused subgoal 닫히면 reward=1(Qed 불필요)
    ALIAS = "grpo_rollout"

    @classmethod
    def from_yaml(cls, yaml_data: Any) -> "GRPORolloutSearchConf":
        return cls(
            yaml_data["timeout"],
            yaml_data.get("group_size", 8),
            yaml_data.get("max_steps", 20),
            yaml_data.get("out", "data/grpo_rollouts/rollouts.jsonl"),
            yaml_data.get("initial_proof", None),
            yaml_data.get("print_proofs", True),
            yaml_data.get("qed_ckpt", None),
            yaml_data.get("shaping_coef", 0.3),
            yaml_data.get("max_retries", 0),
            yaml_data.get("curriculum_file", None),
            yaml_data.get("curriculum_frac", 0.5),
            yaml_data.get("gold_file", None),
            yaml_data.get("vine_k", 0),
            yaml_data.get("adapt_prefix", False),
            yaml_data.get("probe_k", 3),
            yaml_data.get("dyn_resample", 0),
            yaml_data.get("bread", False),
        )


class GRPORolloutSearcher:
    def __init__(self, tactic_clients, proof_manager, conf: GRPORolloutSearchConf):
        self.tactic_clients = tactic_clients
        self.proof_manager = proof_manager
        self.conf = conf
        self.total_model_time = 0.0
        init_dset = proof_manager.get_initial_context()
        if init_dset is None:
            raise ValueError("Could not get initial datasetfile")
        self.theorem = init_dset.proofs[-1].theorem
        # (E2) dense reward: QED value 모델 로드 → value_fn(goals)->float
        # backward curriculum: {정규화된 정리 statement: {initial_proof, remaining, ...}}
        #   theorem_id 는 hash() 기반이라 프로세스마다 달라진다 → **정리 텍스트**로 조회한다.
        self.curriculum = None
        if getattr(conf, "curriculum_file", None):
            import json as _json
            self.curriculum = _json.load(open(conf.curriculum_file))
            print(f"[GRPO-ROLLOUT] backward curriculum 로드: {len(self.curriculum)}개")

        # LUFFY gold 궤적: {정규화된 정리 statement: {"tactics":[...], ...}}.
        #   theorem_id 는 hash 기반이라 프로세스마다 달라진다 → 정리 텍스트로 조회(backward 와 동일).
        self.gold = None
        if getattr(conf, "gold_file", None):
            import json as _json
            self.gold = _json.load(open(conf.gold_file))
            print(f"[GRPO-ROLLOUT] LUFFY gold 궤적 로드: {len(self.gold)}개")

        self.value_fn = None
        if getattr(conf, "qed_ckpt", None):
            from model_deployment.qed_cartographer import QEDValuePredictor
            vp = QEDValuePredictor(conf.qed_ckpt)
            self.value_fn = lambda goals: vp.value_state(goals) if goals else 0.0

    @classmethod
    def from_conf(cls, conf, tactic_clients, proof_manager):
        return cls(tactic_clients, proof_manager, conf)

    def search(self, **kwargs):
        import time
        import re as _re
        start = time.time()
        thm_text = self.theorem.term.text if hasattr(self.theorem, "term") else str(self.theorem)
        thm_id = abs(hash(thm_text)) % (10 ** 12)

        # ★ VinePPO 모드: backbone G개 + 각 state MC value → step별 advantage. 조기 반환.
        vine_k = getattr(self.conf, "vine_k", 0)
        if vine_k > 0:
            attempts = []
            for gi in range(self.conf.group_size):
                att = rollout_vine(
                    self.tactic_clients[0], self.proof_manager, self.theorem,
                    self.conf.initial_proof or "", vine_k, self.conf.max_steps, seed=gi + 1,
                )
                attempts.append(att)
            n_solved = sum(1 for a in attempts if a["reward"] >= 1.0)
            n_steps = sum(len(a["steps"]) for a in attempts)
            group = {"theorem": thm_id, "start": "vine", "attempts": attempts}
            append_group(Path(self.conf.out), group)
            elapsed = time.time() - start
            print(f"[GRPO-ROLLOUT] VINE thm={thm_id} backbone {self.conf.group_size}개 "
                  f"완결 {n_solved} step {n_steps} (k_mc={vine_k}) → {self.conf.out} ({elapsed:.1f}s)")
            return StraightLineFailure(elapsed, self.total_model_time, [])

        # ★ BREAD 모드: on-policy 궤적 + INVALID 지점 gold 다리. gold_file 필요. 조기 반환.
        if getattr(self.conf, "bread", False) and self.gold is not None:
            gkey = _re.sub(r"\s+", " ", thm_text).strip()
            gent = self.gold.get(gkey)
            gtacs = gent["tactics"] if gent else []
            attempts = []
            for gi in range(self.conf.group_size):
                att = rollout_bread(
                    self.tactic_clients[0], self.proof_manager, self.theorem,
                    self.conf.initial_proof or "", gtacs, self.conf.max_steps, seed=gi + 1,
                    max_retries=getattr(self.conf, "max_retries", 2),
                )
                attempts.append(att)
            n_solved = sum(1 for a in attempts if a["reward"] >= 1.0)
            n_bridge = sum(1 for a in attempts for s in a["steps"] if s.get("off_policy"))
            group = {"theorem": thm_id, "start": "bread", "attempts": attempts}
            append_group(Path(self.conf.out), group)
            elapsed = time.time() - start
            print(f"[GRPO-ROLLOUT] BREAD thm={thm_id} 완결 {n_solved}/{self.conf.group_size} "
                  f"gold다리 {n_bridge}개 → {self.conf.out} ({elapsed:.1f}s)")
            return StraightLineFailure(elapsed, self.total_model_time, [])

        # ★ Adaptive prefix 모드: curriculum starts 중 정답률~0.5 인 prefix 선택 후 그 그룹 수집(+s0). 조기 반환.
        if getattr(self.conf, "adapt_prefix", False) and self.curriculum is not None:
            gkey = _re.sub(r"\s+", " ", thm_text).strip()
            ent = self.curriculum.get(gkey)
            best = None
            if ent and "starts" in ent:
                pk = getattr(self.conf, "probe_k", 3)
                best_gap = 2.0
                for si, st in enumerate(ent["starts"]):
                    p = mc_value(self.tactic_clients[0], self.proof_manager, self.theorem,
                                 st["initial_proof"], pk, self.conf.max_steps, seed_base=1000 + si * 7,
                                 max_retries=getattr(self.conf, "max_retries", 0))
                    gap = abs(p - 0.5)
                    if 0.0 < p < 1.0 and gap < best_gap:
                        best_gap, best = gap, st
                print(f"[GRPO-ROLLOUT] adapt_prefix: 후보 {len(ent['starts'])} → 선택 "
                      f"remaining={best['remaining'] if best else '없음(전부 0/1)'}")
            adapt_starts = [("s0", self.conf.initial_proof or "")]
            if best is not None:
                adapt_starts.append((f"adapt_r{best['remaining']}", best["initial_proof"]))
            n_total = 0
            for label, init in adapt_starts:
                grp = collect_group(
                    self.tactic_clients[0], self.proof_manager, self.theorem, thm_id,
                    self.conf.group_size, self.conf.max_steps, init,
                    max_retries=getattr(self.conf, "max_retries", 0), start_label=label,
                )
                append_group(Path(self.conf.out), grp)
                n_total += sum(1 for a in grp["attempts"] if a["reward"] >= 1.0)
            elapsed = time.time() - start
            print(f"[GRPO-ROLLOUT] ADAPT thm={thm_id} 그룹 {len(adapt_starts)}개 → {self.conf.out} ({elapsed:.1f}s)")
            return StraightLineFailure(elapsed, self.total_model_time, [])

        # ★ Dynamic sampling 모드: dead s0 그룹을 mixed 될 때까지 재샘플(최대 M). on-policy. 조기 반환.
        if getattr(self.conf, "dyn_resample", 0) > 0:
            M = self.conf.dyn_resample
            chosen = None
            for tries in range(1 + M):
                grp = collect_group(
                    self.tactic_clients[0], self.proof_manager, self.theorem, thm_id,
                    self.conf.group_size, self.conf.max_steps, self.conf.initial_proof or "",
                    max_retries=getattr(self.conf, "max_retries", 0),
                    start_label=f"s0_try{tries}",
                    seed_base=tries * 1000,  # ★ try 마다 시드 대역 분리 → 재샘플이 실제로 새 궤적을 뽑음
                )
                rs = [a["reward"] for a in grp["attempts"]]
                su = sum(1 for r in rs if r >= 1.0)
                chosen = grp
                if 0 < su < len(rs):  # mixed → 신호 있음, 채택
                    break
            append_group(Path(self.conf.out), chosen)
            elapsed = time.time() - start
            su = sum(1 for a in chosen["attempts"] if a["reward"] >= 1.0)
            print(f"[GRPO-ROLLOUT] DYN thm={thm_id} {tries+1}회 샘플 → 완결 {su}/{self.conf.group_size} "
                  f"→ {self.conf.out} ({elapsed:.1f}s)")
            return StraightLineFailure(elapsed, self.total_model_time, [])

        # 커리큘럼 시작점(들). backward=단일("initial_proof"), revcurr=다중("starts" 리스트).
        curr_starts: list[tuple[str, str]] = []
        if self.curriculum is not None:
            key = _re.sub(r"\s+", " ", thm_text).strip()
            ent = self.curriculum.get(key)
            if ent is None:
                print(f"[GRPO-ROLLOUT] ⚠️ 커리큘럼에 없는 정리 → s_0 에서만 롤아웃")
            elif "starts" in ent:
                # reverse curriculum(전체 역행): gold 의 여러 중간상태에서 각각 그룹.
                for st in ent["starts"]:
                    curr_starts.append((f"curr_r{st['remaining']}", st["initial_proof"]))
                print(f"[GRPO-ROLLOUT] reverse curriculum: {len(curr_starts)} 시작점 "
                      f"(remaining {[s['remaining'] for s in ent['starts']]})")
            else:
                # backward: gold 중간 한 점.
                curr_starts.append(("curriculum", ent["initial_proof"]))
                print(f"[GRPO-ROLLOUT] backward: gold {ent['total']} tactic 중 "
                      f"앞 {ent['total']-ent['remaining']}개 제공 → 남은 {ent['remaining']}개를 생성")

        # ★ 시작점마다 **별도 그룹**을 만든다. 한 그룹에 섞으면 baseline 이 오염된다(collect_group 주석 참조).
        #   skip_s0: subgoal 방법은 s0 그룹이 항상 dead(전부 실패, GRPO advantage=0=gradient 0=순수 낭비)라
        #   생략 → 시도 16→8, timeout 해결. curriculum 그룹만 수집.
        s0_starts = [] if getattr(self.conf, "skip_s0", False) else [("s0", self.conf.initial_proof or "")]
        starts = s0_starts + curr_starts

        # LUFFY: s_0 그룹에 넣을 gold(off-policy) 시도를 미리 재생해둔다.
        gold_att = None
        if self.gold is not None:
            gkey = _re.sub(r"\s+", " ", thm_text).strip()
            gent = self.gold.get(gkey)
            if gent is None:
                print(f"[GRPO-ROLLOUT] ⚠️ gold 궤적에 없는 정리 → LUFFY 주입 없음")
            else:
                gold_att = rollout_gold(
                    self.tactic_clients[0], self.proof_manager, self.theorem,
                    self.conf.initial_proof or "", gent["tactics"],
                    max_steps=max(self.conf.max_steps, len(gent["tactics"])),
                )
                ok = gold_att["reward"] >= 1.0 and gold_att["steps"]
                print(f"[GRPO-ROLLOUT] LUFFY gold 재생: {len(gold_att['steps'])} step, "
                      f"COMPLETE={'✓' if ok else '✗'} (reward={gold_att['reward']})")
                if not ok:
                    gold_att = None  # 재생 실패(reward<1)면 주입하지 않는다(오염 방지)

        # ★ gold_only(SFT 데이터): gold 궤적만 기록하고 on-policy 롤아웃은 생략. 조기 반환.
        if getattr(self.conf, "gold_only", False):
            if gold_att is not None:
                append_group(Path(self.conf.out), {"theorem": thm_id, "start": "gold",
                                                    "attempts": [gold_att]})
            elapsed = time.time() - start
            print(f"[GRPO-ROLLOUT] GOLD-SFT thm={thm_id} "
                  f"{'gold '+str(len(gold_att['steps']))+'step 기록' if gold_att else 'gold 재생실패 스킵'} "
                  f"({elapsed:.1f}s)")
            return StraightLineFailure(elapsed, self.total_model_time, [])

        n_total = 0
        for label, init in starts:
            group = collect_group(
                self.tactic_clients[0], self.proof_manager, self.theorem, thm_id,
                self.conf.group_size, self.conf.max_steps, init,
                value_fn=self.value_fn, shaping_coef=getattr(self.conf, "shaping_coef", 0.3),
                max_retries=getattr(self.conf, "max_retries", 0),
                start_label=label,
                subgoal_reward=getattr(self.conf, "subgoal_reward", False),
            )
            # ★ gold 는 s_0 그룹에만 주입한다(같은 시작상태 s_0 에서 나온 궤적이라야 baseline 이 성립).
            if label == "s0" and gold_att is not None:
                group["attempts"].append(gold_att)
            append_group(Path(self.conf.out), group)
            n_total += sum(1 for a in group["attempts"] if a["reward"] >= 1.0)

        elapsed = time.time() - start
        # rollout은 데이터 수집이 목적 → 항상 Failure 반환(run_all 성공집계 무의미).
        print(f"[GRPO-ROLLOUT] thm={thm_id} 그룹 {len(starts)}개 "
              f"완결 {n_total}/{self.conf.group_size*len(starts)} → {self.conf.out} ({elapsed:.1f}s)")
        return StraightLineFailure(elapsed, self.total_model_time, [])


def main():
    ap = argparse.ArgumentParser(description="GRPO rollout 수집(run_thm 인프라 필요)")
    ap.add_argument("--group_size", type=int, default=8)
    ap.add_argument("--max_steps", type=int, default=20)
    ap.add_argument("--out", default="data/grpo_rollouts/rollouts.jsonl")
    ap.add_argument("--num", type=int, default=40, help="정리 수(train split)")
    ap.add_argument("--start", type=int, default=200, help="eval셋과 분리 오프셋")
    args = ap.parse_args()
    # 실제 구동은 run_thm의 서버/proof_manager 셋업을 재사용하는 드라이버에서 호출.
    # (여기서는 단독 실행 대신 collect_group을 라이브러리로 호출하는 것을 권장.)
    print("grpo_rollout: collect_group()을 run_thm 셋업과 함께 호출하세요.")
    print(f"  설정: group={args.group_size} max_steps={args.max_steps} out={args.out}")


if __name__ == "__main__":
    main()
