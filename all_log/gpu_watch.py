#!/usr/bin/env python3
"""경량 자원 감시자 — nvidia-smi + /proc 로 **GPU util·mem + CPU util + RAM + 실행옵션**을 md 에 적응형 간격 기록.

적응형 간격:
  - 평소 BASE(기본 10분). 자원 **상승 기미**(GPU util>RISE_UTIL / mem>RISE_MEM / CPU>RISE_CPU)면 **FAST(기본 5분) 가속**.
  - 진정되면 BASE 복귀(히스테리시스로 플랩 방지). 간격 전환 시 타임라인에 마커.
  ★ 보고 전용: 정지 안 시킴. 경량(nvidia-smi + /proc 읽기 + ps + sleep). CPU util 은 기존 3초 샘플 창으로 계산(추가 sleep 없음).

사용: setsid nohup python3 all_log/gpu_watch.py 600 </dev/null >/dev/null 2>&1 & disown
출력: all_log/gpu_monitor.md
"""
import os
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta

OUT = "all_log/gpu_monitor.md"
BASE = int(sys.argv[1]) if len(sys.argv) > 1 else 600
FAST = max(60, BASE // 2)
UTIL_HI, MEM_HI, CPU_HI = 85, 90, 85          # 빡빡(⚠) 임계 (GPU util / GPU mem / CPU util)
RISE_UTIL, RISE_MEM, RISE_CPU = 60, 70, 60    # '올라갈 기미' → FAST 가속
CALM_UTIL, CALM_MEM, CALM_CPU = 45, 55, 45    # 진정 → BASE 복귀 (히스테리시스)
KST = timezone(timedelta(hours=9))


def read_cpu():
    """(/proc/stat 집계 cpu 라인) → (total, idle) jiffies."""
    try:
        with open("/proc/stat") as f:
            v = list(map(int, f.readline().split()[1:]))
        idle = v[3] + (v[4] if len(v) > 4 else 0)   # idle + iowait
        return sum(v), idle
    except Exception:
        return None


def read_mem():
    """RAM (used_kB, total_kB) — MemTotal - MemAvailable."""
    mt = ma = 0
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    mt = int(line.split()[1])
                elif line.startswith("MemAvailable:"):
                    ma = int(line.split()[1])
    except Exception:
        pass
    return (mt - ma, mt)


def sample():
    """util 3회(1s 간격) 평균 + 마지막 mem. + 그 3초 창의 CPU util%. 반환 (gpu_rows, cpu_util)."""
    c0 = read_cpu()
    acc = {}
    for _ in range(3):
        try:
            out = subprocess.run(
                ["nvidia-smi", "--query-gpu=index,utilization.gpu,memory.used,memory.total",
                 "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=15).stdout
        except Exception:
            out = ""
        for line in out.strip().splitlines():
            parts = [x.strip() for x in line.split(",")]
            if len(parts) != 4:
                continue
            try:
                gi, u, mu, mt = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
            except ValueError:
                continue
            a = acc.setdefault(gi, [0, 0, 0, 0])
            a[0] += u; a[1] += 1; a[2] = mu; a[3] = mt
        time.sleep(1)
    c1 = read_cpu()
    cpu = 0
    if c0 and c1:
        dt, di = c1[0] - c0[0], c1[1] - c0[1]
        cpu = int(100 * (dt - di) / dt) if dt > 0 else 0
    rows = [(gi, acc[gi][0] // max(acc[gi][1], 1), acc[gi][2], acc[gi][3]) for gi in sorted(acc)]
    return rows, cpu


def _arg(args, key):
    toks = args.split()
    if key in toks:
        i = toks.index(key)
        if i + 1 < len(toks):
            return toks[i + 1]
    return None


def _proc_env(pid, key):
    try:
        with open(f"/proc/{pid}/environ", "rb") as f:
            for kv in f.read().decode("utf-8", "replace").split("\x00"):
                if kv.startswith(key + "="):
                    return kv[len(key) + 1:]
    except Exception:
        pass
    return None


def current_phase():
    try:
        out = subprocess.run(["ps", "-eo", "pid=,args="], capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return ("-", "실행 없음")
    gtrain = roll = ev = None
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        pid, _, args = line.partition(" ")
        if "tactic_gen.grpo_train" in args and "--save_dir" in args:
            gtrain = (pid, args)
        elif "run_all.py" in args and "grpo-rollout-subgoal" in args and "run_thm" not in args:
            roll = (pid, args)
        elif "run_all.py" in args and "rango-grpo-cascade" in args and "run_thm" not in args:
            ev = (pid, args)
    if gtrain:
        pid, args = gtrain
        sd = _arg(args, "--save_dir") or "?"
        st = sd.replace("models/rango-grpo-", "").split("/")[0]
        return (f"gtrain:{st}", f"학습(gtrain) → {sd} · pid{pid}")
    if roll:
        pid, args = roll
        so = _proc_env(pid, "SUBGOAL_OUT") or ""
        st = os.path.basename(so).replace("rango-grpo-", "").replace(".jsonl", "") if so else "?"
        idxf = _arg(args, "--idx-file") or "?"
        gp, w = _arg(args, "--gpus"), _arg(args, "--workers")
        return (f"roll:{st}", f"롤아웃 {st} (idx={os.path.basename(idxf)}, gpus={gp}×w{w}, G={_proc_env(pid,'SUBGOAL_GS') or '?'}) · pid{pid}")
    if ev:
        pid, args = ev
        idxf = _arg(args, "--idx-file") or ""
        which = "rand200" if "rand200" in idxf else ("1191" if idxf.endswith("test_idx.txt") else os.path.basename(idxf))
        gp, w, to = _arg(args, "--gpus"), _arg(args, "--workers"), _arg(args, "--timeout")
        return (f"eval:{which}", f"평가 {which}@{to}s (gpus={gp}×w{w}) · pid{pid}")
    return ("-", "실행 없음")


def main():
    rows0, _ = sample()
    ngpu = len(rows0)
    gcols = " | ".join(f"GPU{g} util | GPU{g} mem" for g in range(ngpu))
    header = f"| 시각(KST) | CPU | RAM | {gcols} | 판정 | 실행옵션 |\n|---|" + "---|" * (2 * ngpu + 4) + "\n"
    with open(OUT, "w") as f:
        f.write("# 자원 감시(CPU+GPU) + 실행옵션 타임라인 (적응형 간격) — 보고 전용, 자동정지 없음\n\n")
        f.write(f"- GPU {ngpu}개. 간격: 평소 **{BASE//60}분**, 상승 기미(GPU util>{RISE_UTIL}% / mem>{RISE_MEM}% / CPU>{RISE_CPU}%)면 **{FAST//60}분 가속**.\n")
        f.write(f"- 빡빡: GPU util>{UTIL_HI}% 또는 mem>{MEM_HI}% 또는 **CPU>{CPU_HI}%** → ⚠ · 3틱 연속 → 🔴지속.\n")
        f.write("- 단계·간격 전환 시 굵은 마커. 매 행 '실행옵션'에 짧은 태그. CPU=시스템 전체 util%, RAM=used/total.\n")
        f.write(f"- 시작 {datetime.now(KST):%m-%d %H:%M:%S} KST (간격 {BASE//60}분)\n")
        f.flush()

    consec = 0
    last_tag = None
    fast_mode = False
    while True:
        rows, cpu = sample()
        ram_u, ram_t = read_mem()
        ram_pct = int(100 * ram_u / ram_t) if ram_t else 0
        tag, detail = current_phase()
        ts = f"{datetime.now(KST):%H:%M:%S}"
        if tag != last_tag:
            consec = 0   # 단계 전환 시 지속(🔴) 카운터 리셋 — gtrain→eval 이월 헛알람 방지

        cells, tight = [], False
        max_util = max_memp = 0
        for gi, ua, mu, mt in rows:
            memp = (mu * 100 // mt) if mt else 0
            max_util = max(max_util, ua); max_memp = max(max_memp, memp)
            flag = "⚠" if (ua > UTIL_HI or memp > MEM_HI) else ""
            if flag:
                tight = True
            cells.append(f"{ua}%{flag}")
            cells.append(f"{mu // 1024}/{mt // 1024}G ({memp}%)")
        cpu_flag = "⚠" if cpu > CPU_HI else ""
        if cpu_flag:
            tight = True
        consec = consec + 1 if tight else 0
        verdict = "여유"
        if tight:
            verdict = "⚠빡빡"
        if consec >= 3:
            verdict = f"🔴지속({consec}틱)"

        # 적응형 간격 (히스테리시스, CPU 포함)
        prev_fast = fast_mode
        if not fast_mode and (max_util > RISE_UTIL or max_memp > RISE_MEM or cpu > RISE_CPU):
            fast_mode = True
        elif fast_mode and (max_util < CALM_UTIL and max_memp < CALM_MEM and cpu < CALM_CPU):
            fast_mode = False
        interval = FAST if fast_mode else BASE

        markers = []
        if tag != last_tag:
            markers.append(f"**[{ts}] ▶ 실행옵션: {detail}**")
            last_tag = tag
        if fast_mode != prev_fast:
            if fast_mode:
                markers.append(f"**[{ts}] ⏱ 상승 기미(CPU={cpu}% GPUutil={max_util}% GPUmem={max_memp}%) → 감시 {FAST//60}분 가속**")
            else:
                markers.append(f"**[{ts}] ⏱ 진정 → 감시 {BASE//60}분 복귀**")
        cpu_cell = f"{cpu}%{cpu_flag}"
        ram_cell = f"{ram_u//1024//1024}/{ram_t//1024//1024}G ({ram_pct}%)"
        with open(OUT, "a") as f:
            if markers:
                f.write("\n" + "\n\n".join(markers) + "\n\n")
                f.write(header)
            f.write(f"| {ts} | {cpu_cell} | {ram_cell} | " + " | ".join(cells) + f" | {verdict} | {tag} |\n")
            f.flush()
        time.sleep(interval)


if __name__ == "__main__":
    main()
