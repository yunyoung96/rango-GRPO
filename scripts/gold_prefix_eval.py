#!/usr/bin/env python3
"""**gold prefix 를 준 뒤 완주하는가** — 표류(drift)를 제거하고 조합 능력만 본다.

문제의식: 실패 정리는 깊이 2~7 에서 gold 궤적을 벗어나고, 백트래킹이 없어 뿌리부터
  46번 다시 시작한다. 그러면 "조합을 못한다"가 아니라 "초반에 길을 잘못 들었을 뿐"일
  수 있다. gold 의 앞 k% 를 **정답으로 채워준 뒤** 나머지를 풀게 하면 두 가설이 갈린다.

    · prefix 를 늘려도 성공률이 거의 안 오른다  → 남은 부분 자체를 조합 못 함
    · prefix 를 늘리면 성공률이 급격히 오른다    → 초반 선택 실패가 주원인(표류)

사용: python3 scripts/gold_prefix_eval.py <체크포인트> <정리수> <prefix비율,...>
환경: GP_TIMEOUT(탐색 초, 기본 300) · GP_GPUS(기본 "0,1") · GP_WORKERS(GPU당, 기본 5)
"""
import os
import queue
import re
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, "src")
from coqstoq import Split, get_theorem  # noqa: E402

CKPT = sys.argv[1]
N = int(sys.argv[2]) if len(sys.argv) > 2 else 40
RATIOS = [float(x) for x in (sys.argv[3].split(",") if len(sys.argv) > 3 else ["0", "0.33", "0.66"])]
LOC = Path("CoqStoq")
TIMEOUT = int(os.environ.get("GP_TIMEOUT", "300"))
GPUS = os.environ.get("GP_GPUS", "0,1").split(",")
WPG = int(os.environ.get("GP_WORKERS", "5"))
OUT = Path(os.environ.get("GP_OUT", "all_log/gold_prefix"))
OUT.mkdir(parents=True, exist_ok=True)


def gold_steps(thm) -> list[str]:
    """gold 증명을 **Coq 문장 단위**로 쪼갠다(Proof./Qed. 제외).

    ★ '.' 마다 자르면 안 된다 — `Int.max_signed` 같은 한정이름이 두 동강 나
      Coq 이 구문오류를 냈다. 문장 끝은 '.' **뒤가 공백/개행/끝**일 때뿐이고,
      괄호 안의 '.' 도 제외해야 한다.
    """
    f = LOC / "test-repos" / thm.project.dir_name / thm.path
    lines = f.read_text(errors="ignore").split("\n")
    body = "\n".join(lines[thm.proof_start_pos.line: thm.proof_end_pos.line + 1])
    body = re.sub(r"^\s*Proof\.\s*", "", body.strip())
    body = re.sub(r"\s*Qed\.\s*$", "", body)
    body = re.sub(r"\(\*.*?\*\)", " ", body, flags=re.S)          # 주석 제거

    out, buf, depth = [], [], 0
    for i, ch in enumerate(body):
        buf.append(ch)
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == "." and depth == 0:
            nxt = body[i + 1] if i + 1 < len(body) else " "
            if nxt in " \t\r\n":
                out.append("".join(buf).strip())
                buf = []
    if "".join(buf).strip():
        out.append("".join(buf).strip())
    # 중괄호·불릿만 있는 조각은 단독으로 유효하지 않으므로 앞 문장에 붙인다
    merged: list[str] = []
    for x in out:
        if merged and re.fullmatch(r"[-+*{}\s]+", x):
            merged[-1] += " " + x
        else:
            merged.append(x)
    return [x for x in merged if x.strip()]


idx = [int(x) for x in Path("data/compcert_bs2_rand200_idx.txt").read_text().split()][:N]
env = dict(os.environ)
env.update(dict(
    EXEC_ADAPTER=CKPT, TACTIC_LEADING_NL="1", AUGMENT_V2="1", RERANK_PREMISES="1",
    INJECT_TYPES="1", INJECT_DEFS="1", HARD_SEQ_LEN="4096", TYPES_TOKENS="300",
    DEFS_TOKENS="300", FUNC_DEFS_PATH="data/func_defs_v3.json", HF_HUB_OFFLINE="1"))

res = {r: [0, 0] for r in RATIOS}          # 비율 → [성공, 시도]
skip = {r: 0 for r in RATIOS}              # prefix 가 Coq 에 안 먹힌 건 분모에서 뺀다
lock = threading.Lock()

jobs = []
for i in idx:
    try:
        thm = get_theorem(Split.TEST, i, LOC)
        steps = gold_steps(thm)
    except Exception:
        continue
    if len(steps) < 3:                     # prefix 를 나눌 수 없는 짧은 증명은 제외
        continue
    for r in RATIOS:
        jobs.append((i, r, steps))


def run_one(job, gpu):
    i, r, steps = job
    k = int(len(steps) * r)
    # ★ check_proof 는 file_prefix 에 그대로 이어붙인다(contents = prefix + partial).
    #   탐색기도 "\n"+tactic 으로 쌓으므로 **개행으로 시작**해야 구문이 성립한다.
    prefix = ("\n" + "\n".join(steps[:k])) if k else ""
    e = dict(env)
    e["GOLD_PREFIX"] = prefix
    e["CUDA_VISIBLE_DEVICES"] = gpu
    try:
        p = subprocess.run(
            ["python3", "scripts/run_thm.py", "run", "rango-grpo", "test", str(i),
             "--timeout", str(TIMEOUT)],
            env=e, capture_output=True, text=True, timeout=TIMEOUT + 900)
        out, err = p.stdout, p.stderr
    except subprocess.TimeoutExpired as t:  # 모델 로딩·파일 컴파일 지연 — 실패로 집계
        raw = t.stdout or ""
        out = raw.decode(errors="ignore") if isinstance(raw, bytes) else raw
        err = "WRAPPER_TIMEOUT"
    (OUT / f"{i}_r{int(r * 100)}.txt").write_text(out[-40000:])
    bad = ("Syntax error" in out) or ("AssertionError" in err)
    with lock:
        if bad:
            skip[r] += 1
        else:
            res[r][0] += ("TacticResult.COMPLETE" in out)
            res[r][1] += 1
        done = sum(v[1] for v in res.values()) + sum(skip.values())
        if done % 5 == 0 or done == len(jobs):
            print(f"[{done}/{len(jobs)}] " + "  ".join(
                f"{int(x * 100)}%: {res[x][0]}/{res[x][1]}" for x in RATIOS), flush=True)


q: queue.Queue = queue.Queue()
for j in jobs:
    q.put(j)


def worker(gpu):
    while True:
        try:
            j = q.get_nowait()
        except queue.Empty:
            return
        try:
            run_one(j, gpu)
        except Exception as ex:
            print("  오류:", ex, flush=True)
        finally:
            q.task_done()


print(f"총 {len(jobs)}건 · GPU {GPUS} × 워커 {WPG} = {len(GPUS) * WPG} 병렬", flush=True)
with ThreadPoolExecutor(max_workers=len(GPUS) * WPG) as pool:
    for g in GPUS:
        for _ in range(WPG):
            pool.submit(worker, g)

print("\n=== 결과 ===")
for r in RATIOS:
    s_, n_ = res[r]
    print(f"  gold prefix {int(r * 100):3d}% → {s_}/{n_} = {s_ / max(n_, 1) * 100:5.1f}%"
          + (f"   (prefix 무효 {skip[r]}개 제외)" if skip[r] else ""))
