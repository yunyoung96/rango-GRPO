#!/usr/bin/env python3
"""v5 학습 로그의 **이상 징후**를 한 번에 점검. 감독 스크립트가 주기적으로 호출한다.

보는 것:
  H1 발산      : 최근 loss 가 초기 최저의 2배를 넘고 유지되는가
  H2 정체      : 최근 200스텝 loss 개선이 사실상 0인가(학습 신호 소실 의심)
  H3 grad 폭발 : grad_norm 스파이크가 잦은가
  H4 NaN/Inf   : loss 나 grad 에 nan/inf 가 찍혔는가
  H5 예외      : Traceback / OOM / CUDA error 가 있는가
  H6 진행정지  : 스텝이 최근에 전혀 안 늘었는가
종료코드 0=정상, 7=치명(중단 필요), 1=경고
"""
import re, sys, os, time, json

LOG = sys.argv[1] if len(sys.argv) > 1 else "all_log/ft_qwen3b_v5.log"
if not os.path.exists(LOG):
    print("로그 없음"); sys.exit(1)
txt = open(LOG, errors="ignore").read()
# ★ **현재 run 만** 본다. 로그는 append 라 이전 시도의 OOM/Traceback 이 남아 있고,
#   그대로 세면 매번 경고가 떠서 진짜 이상을 가린다(실제로 21:17 4-GPU OOM 흔적이
#   21:53 재개분의 건강검진을 오염시켰다).
_m = txt.rfind("===== v5 학습 시작")
if _m >= 0:
    txt = txt[_m:]

loss = [float(x) for x in re.findall(r"'loss': '([0-9.]+)'", txt)]
gn = [float(x) for x in re.findall(r"'grad_norm': '([0-9.eE+-]+)'", txt)]
steps = re.findall(r"(\d+)/60000 \[", txt)
cur = int(steps[-1]) if steps else 0

bad, warn = [], []
if re.search(r"nan|inf", " ".join(re.findall(r"'loss': '([^']+)'", txt)), re.I):
    bad.append("H4 loss 에 nan/inf")
for pat, name in ((r"Traceback", "H5 예외"), (r"out of memory", "H5 OOM"),
                  (r"CUDA error", "H5 CUDA error")):
    n = len(re.findall(pat, txt, re.I))
    if n: warn.append(f"{name} {n}회")

if len(loss) >= 40:
    best = min(loss[:20]); recent = loss[-10:]
    if all(v > best * 2 for v in recent):
        bad.append(f"H1 발산(초기최저 {best:.3f} → 최근 {sum(recent)/len(recent):.3f})")
    if len(loss) >= 80:
        a = sum(loss[-80:-40]) / 40; b = sum(loss[-40:]) / 40
        if b > a * 0.999 and b > 1.5:
            warn.append(f"H2 정체(직전 {a:.3f} → 최근 {b:.3f})")
if gn:
    spike = sum(1 for v in gn[-100:] if v > 5)
    if spike > 10: warn.append(f"H3 grad 스파이크 {spike}/100")

# ★ eval 은 **전체 이력**으로 본다 — 로그 파일이 교체되면 현재 파일의 최저값만 보게 되어
#   과적합(이전 파일의 진짜 최저 대비 상승)을 놓친다. 실제로 10000(0.9689)이 최저인데
#   교체된 파일에는 12000·14000 만 남아 감시가 울리지 않았다.
_full = open(LOG, errors="ignore").read()
for _p in ("all_log/ft_qwen3b_v5_oomdebug.log",):
    try: _full = open(_p, errors="ignore").read() + _full
    except OSError: pass
ev = [float(x) for x in re.findall(r"'eval_loss': '?([0-9.]+)'?", _full)]
# 과적합 감시: train 이 내려가는데 eval 이 올라가면 경고
if len(ev) >= 3 and ev[-1] > min(ev) * 1.05 and ev[-1] > ev[-2]:
    warn.append(f"H7 eval_loss 상승(최저 {min(ev):.3f} → 최근 {ev[-1]:.3f})")
print(f"step {cur}  loss {loss[-1] if loss else '-'}  "
      f"grad {gn[-1] if gn else '-'}  eval {ev[-1] if ev else '-'}  기록 {len(loss)}개")
if bad:
    for b_ in bad: print("  ★ 치명:", b_)
    sys.exit(7)
if warn:
    for w in warn: print("  ⚠ 경고:", w)
    sys.exit(1)
print("  ✅ 이상 없음")
