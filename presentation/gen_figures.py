#!/usr/bin/env python3
"""발표용 그림 생성 (matplotlib). 라벨은 폰트 안전상 영문. → presentation/figures/*.png
겹침 방지: 박스 간격 넓게, 화살표 라벨은 짧게+빈 공간에 배치."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = os.path.join(os.path.dirname(__file__), "figures")
os.makedirs(OUT, exist_ok=True)
BLUE, GREEN, RED, GRAY, ORANGE, PURPLE = "#1565c0", "#2e7d32", "#c62828", "#616161", "#ef6c00", "#6a1b9a"

def box(ax, x, y, w, h, text, fc="#e3f2fd", ec=BLUE, fs=11, tc="#0d1b2a"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.01,rounding_size=0.06",
                                fc=fc, ec=ec, lw=1.6, zorder=3))
    ax.text(x + w/2, y + h/2, text, ha="center", va="center", fontsize=fs, color=tc, zorder=5)

def arrow(ax, p0, p1, text="", color="#37474f", fs=9, rad=0.0, tpos=0.5, tdx=0.0, tdy=0.16, tha="center"):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=15, color=color,
                                 lw=1.6, connectionstyle=f"arc3,rad={rad}", zorder=1))
    if text:
        lx = p0[0] + (p1[0]-p0[0])*tpos + tdx
        ly = p0[1] + (p1[1]-p0[1])*tpos + tdy
        ax.text(lx, ly, text, ha=tha, va="center", fontsize=fs, color=color, style="italic", zorder=6)

def save(fig, name):
    fig.savefig(os.path.join(OUT, name), dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig); print("  ✓", name)

# ── 1. MDP episode (or_comm) — 넓은 간격, 짧은 라벨 ──────────────────────
fig, ax = plt.subplots(figsize=(12.5, 3.8)); ax.set_xlim(0, 12.5); ax.set_ylim(0, 3.8); ax.axis("off")
ax.set_title("Proof as an MDP episode   (theorem:  (A or B) -> (B or A))", fontsize=13, weight="bold")
box(ax, 0.1, 1.35, 2.2, 0.9, "s0\n(A or B) -> (B or A)")
box(ax, 3.2, 1.35, 2.2, 0.9, "s1\nH: A or B  |-  B or A")
box(ax, 6.5, 2.45, 2.1, 0.8, "case A: |- B or A", fc="#e8f5e9", ec=GREEN, fs=10)
box(ax, 6.5, 0.30, 2.1, 0.8, "case B: |- B or A", fc="#e8f5e9", ec=GREEN, fs=10)
box(ax, 9.4, 2.45, 1.3, 0.8, "closed", fc="#fff3e0", ec=ORANGE)
box(ax, 9.4, 0.30, 1.3, 0.8, "closed", fc="#fff3e0", ec=ORANGE)
box(ax, 11.0, 1.35, 1.4, 0.9, "QED\nr = 1", fc="#fff3e0", ec=ORANGE)
arrow(ax, (2.3, 1.8), (3.2, 1.8), "intro", tdy=0.18)                 # gap 0.9
arrow(ax, (5.4, 1.95), (6.5, 2.6), "destruct H", tpos=0.45, tdy=0.22)
arrow(ax, (5.4, 1.65), (6.5, 0.75), "")
arrow(ax, (8.6, 2.85), (9.4, 2.85), "right", tdy=0.18)               # gap 0.8
arrow(ax, (8.6, 0.70), (9.4, 0.70), "left", tdy=0.18)
arrow(ax, (10.7, 2.7), (11.0, 2.05), "")
arrow(ax, (10.7, 0.75), (11.0, 1.55), "")
ax.text(6.25, 3.5, "Reward is sparse & terminal:  0 everywhere,  1 only at QED",
        ha="center", fontsize=10, color=RED)
save(fig, "fig_mdp.png")

# ── 2. Rango architecture — 루프를 하단으로 깔끔히 ───────────────────────
fig, ax = plt.subplots(figsize=(12, 4.2)); ax.set_xlim(0, 12); ax.set_ylim(0, 4.2); ax.axis("off")
ax.set_title("Rango:  retrieval-augmented tactic generation", fontsize=13, weight="bold")
box(ax, 0.2, 3.05, 2.5, 0.7, "similar proofs (BM25)", fc="#f3e5f5", ec=PURPLE, fs=10)
box(ax, 0.2, 1.95, 2.5, 0.8, "current goal state")
box(ax, 0.2, 0.85, 2.5, 0.7, "relevant lemmas (TF-IDF)", fc="#f3e5f5", ec=PURPLE, fs=10)
box(ax, 3.5, 2.05, 1.6, 1.0, "prompt", fc="#eceff1", ec=GRAY)
box(ax, 5.7, 1.9, 2.6, 1.3, "DeepSeek-Coder 1.3B\n(fine-tuned)\n= policy pi_theta", fc="#e3f2fd", ec=BLUE, fs=10)
box(ax, 8.9, 2.05, 2.6, 1.0, "next-tactic\ndistribution")
box(ax, 8.9, 0.55, 2.6, 0.75, "proof search (best-first)", fc="#e8f5e9", ec=GREEN, fs=10)
for py in [3.4, 2.35, 1.2]:
    arrow(ax, (2.7, py), (3.5, 2.55), "")
arrow(ax, (5.1, 2.55), (5.7, 2.55), "")
arrow(ax, (8.3, 2.55), (8.9, 2.55), "")
arrow(ax, (10.2, 2.05), (10.2, 1.3), "apply in Coq", tdx=0.9, tdy=0.0, tha="left")
# loop: proof search -> goal, 아래로 크게 우회(빈 공간)
arrow(ax, (8.9, 0.75), (2.7, 1.95), "new goal  (loop back)", color=GREEN, rad=-0.28,
      tpos=0.5, tdx=0.0, tdy=-0.55)
save(fig, "fig_rango_arch.png")

# ── 3. subgoal tree (or_comm) ───────────────────────────────────────────
fig, ax = plt.subplots(figsize=(8.5, 3.8)); ax.set_xlim(0, 8.5); ax.set_ylim(0, 3.8); ax.axis("off")
ax.set_title("A proof = closing a tree of subgoals", fontsize=13, weight="bold")
box(ax, 2.55, 2.9, 3.4, 0.7, "goal:  (A or B) -> (B or A)")
box(ax, 0.4, 1.5, 2.8, 0.7, "case A:  |- B or A", fc="#e8f5e9", ec=GREEN)
box(ax, 5.3, 1.5, 2.8, 0.7, "case B:  |- B or A", fc="#e8f5e9", ec=GREEN)
box(ax, 0.45, 0.35, 2.7, 0.6, "right; exact HA", fc="#fff3e0", ec=ORANGE, fs=9)
box(ax, 5.35, 0.35, 2.7, 0.6, "left; exact HB", fc="#fff3e0", ec=ORANGE, fs=9)
arrow(ax, (3.5, 2.9), (1.8, 2.2), "destruct H", tpos=0.4, tdx=-0.7, tdy=0.1)
arrow(ax, (4.7, 2.9), (6.7, 2.2), "destruct H", tpos=0.4, tdx=0.7, tdy=0.1)
arrow(ax, (1.8, 1.5), (1.8, 0.95), "")
arrow(ax, (6.7, 1.5), (6.7, 0.95), "")
ax.text(4.25, 0.08, "all subgoals closed  =>  QED", ha="center", fontsize=11, color=ORANGE, weight="bold")
save(fig, "fig_subgoal_tree.png")

# ── 4. dead / mixed / all-solved ────────────────────────────────────────
fig, ax = plt.subplots(figsize=(9, 3.0))
cats = ["dead\n(8/8 fail)", "mixed\n(some pass)", "all-solved\n(8/8 pass)"]
vals = [64, 31, 5]; cols = [GRAY, GREEN, BLUE]
bars = ax.bar(cats, vals, color=cols, width=0.6)
for b, v in zip(bars, vals): ax.text(b.get_x()+b.get_width()/2, v+1.5, f"{v}%", ha="center", fontsize=13, weight="bold")
ax.set_ylabel("% of rollout groups"); ax.set_ylim(0, 78)
ax.set_title("Only 'mixed' gives a learning signal   (dead + all = zero gradient)", fontsize=12, weight="bold")
ax.text(0, 40, "no signal\n(adv = 0)", ha="center", color=RED, fontsize=10)
ax.text(2, 18, "no signal\n(adv = 0)", ha="center", color=RED, fontsize=10)
save(fig, "fig_deadmixed.png")

# ── 5. overfitting (Set 2) ──────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(7.5, 4.2))
x = [1, 2, 3]
ax.plot(x, [36, 38, 43], "-o", color=GREEN, lw=2.5, ms=9, label="train coverage")
ax.plot(x, [37.5, 37.5, 28], "-s", color=RED, lw=2.5, ms=9, label="held-out (rand200)")
ax.axhline(37.5, ls="--", color=GRAY, lw=1, label="SFT->GRPO baseline 37.5%")
ax.set_xticks(x); ax.set_xticklabels(["round 1", "round 2", "round 3"]); ax.set_ylabel("success rate (%)")
ax.set_xlim(0.7, 3.5); ax.set_ylim(20, 50); ax.legend(fontsize=10, loc="center left")
ax.set_title("Set 2: repeating SFT->GRPO  ->  train up, held-out flat/down", fontsize=11, weight="bold")
ax.annotate("train improves", (3, 43), (2.05, 47), color=GREEN, fontsize=10,
            arrowprops=dict(arrowstyle="->", color=GREEN))
ax.annotate("test drops = overfitting", (3, 28), (1.75, 23.5), color=RED, fontsize=10,
            arrowprops=dict(arrowstyle="->", color=RED))
save(fig, "fig_overfitting.png")

# ── 6. Set 1 results ────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(7, 4.2))
names = ["SFT\n(base Rango)", "SFT -> GRPO", "safe-EI\n(running)"]
vals = [33.5, 37.5, 0]; cols = [GRAY, BLUE, "#cccccc"]
bars = ax.bar(names, vals, color=cols, width=0.6)
bars[2].set_hatch("//")
for b, v, t in zip(bars, vals, ["33.5%", "37.5%", "TBD"]):
    ax.text(b.get_x()+b.get_width()/2, (v if v else 2)+1.2, t, ha="center", fontsize=13, weight="bold")
ax.axhline(37.5, ls="--", color=BLUE, lw=1)
ax.set_ylabel("rand200 success rate (%)"); ax.set_ylim(0, 50)
ax.set_title("CompCert held-out:  best = SFT->GRPO 37.5% (gain is small)", fontsize=11, weight="bold")
save(fig, "fig_results.png")

# ── 7. domain gap ───────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(7.5, 3.2))
labels = ["pure math\n(miniF2F, Lean)", "systems verif.\n(CompCert, Coq)"]
vals = [88.9, 32.5]
b = ax.barh(labels, vals, color=[GREEN, RED], height=0.55)
notes = ["88.9%  (DeepSeek-Prover-V2)", "32.5%  (Rango, best)"]
for bar, v, t in zip(b, vals, notes):
    ax.text(v+2, bar.get_y()+bar.get_height()/2, t, va="center", fontsize=11, weight="bold")
ax.set_xlim(0, 100); ax.set_xlabel("automated proving success rate (%)")
ax.set_title("LLMs solve math well, but CompCert stays hard (<40%)", fontsize=11, weight="bold")
save(fig, "fig_domain_gap.png")

# ── 8. Expert Iteration loop — 간격 넓게, 라벨 분리 ─────────────────────
fig, ax = plt.subplots(figsize=(10.5, 4.4)); ax.set_xlim(0, 10.5); ax.set_ylim(0, 4.4); ax.axis("off")
ax.set_title("Expert Iteration (with overfitting safeguards)", fontsize=13, weight="bold")
box(ax, 0.2, 1.9, 1.9, 0.85, "policy pi_k", fc="#e3f2fd", ec=BLUE)
box(ax, 2.9, 2.9, 2.5, 0.85, "rollout 300 thms\ncollect successes", fc="#e8f5e9", ec=GREEN, fs=9)
box(ax, 6.0, 2.9, 2.4, 0.85, "RFT + GRPO\n(KL -> pi_0)", fc="#eceff1", ec=GRAY, fs=9)
box(ax, 6.05, 1.35, 2.3, 0.8, "held-out val\n(early-stop)", fc="#fff3e0", ec=ORANGE, fs=9)
box(ax, 2.95, 0.35, 2.4, 0.75, "best -> rand200", fc="#fce4ec", ec=RED, fs=10)
arrow(ax, (2.1, 2.5), (2.9, 3.15), "", tpos=0.5)
arrow(ax, (5.4, 3.32), (6.0, 3.32), "+gold +accum", tdy=0.2)
arrow(ax, (7.2, 2.9), (7.2, 2.15), "pi_k+1", tdx=0.6, tdy=0.0, tha="left")
arrow(ax, (6.05, 1.75), (2.1, 2.35), "improve? loop", color=BLUE, rad=0.22, tpos=0.55, tdy=0.28)
arrow(ax, (6.05, 1.5), (5.35, 0.75), "plateau -> stop", color=RED, tpos=0.5, tdx=-0.2, tdy=0.25)
ax.text(9.9, 2.3, "safeguards:\n- KL -> pi_0\n- gold + accum mix\n- low lr, 1 epoch\n- val early-stop",
        ha="left", va="center", fontsize=9, color="#0d1b2a",
        bbox=dict(boxstyle="round", fc="#f9fbe7", ec="#9e9d24"))
save(fig, "fig_ei_loop.png")

print("done ->", OUT)
