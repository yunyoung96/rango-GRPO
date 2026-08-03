#!/usr/bin/env python3
"""발표용 그림 생성 (matplotlib). 라벨은 폰트 안전상 영문. → presentation/figures/*.png

크기/가독성은 아래 세 상수로 일괄 조절:
  SZ  : 캔버스 크기 배율(↓ 그림이 작아짐)   FSC : 글씨 배율(↑ 글씨가 커짐)   DPI : 선명도
최종 픽셀폭 ≈ (figsize × SZ) × DPI, 글씨는 pt 단위라 SZ와 무관.
따라서 SZ↓ + FSC↑ = "그림은 작고 글씨는 크게"(발표용 비율).

겹침 방지 규칙: 박스 폭은 가장 긴 줄 기준으로 잡되 긴 라벨은 여러 줄로 쪼갠다.
글자폭 어림값(데이터 단위) ≈ 글자수 × pt × 0.0143  (SZ=0.72, FSC=1.35 기준)
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = os.path.join(os.path.dirname(__file__), "figures")
os.makedirs(OUT, exist_ok=True)
BLUE, GREEN, RED, GRAY, ORANGE, PURPLE = "#1565c0", "#2e7d32", "#c62828", "#616161", "#ef6c00", "#6a1b9a"

SZ, FSC, DPI = 0.72, 1.35, 118

def F(pt):                      # 폰트 크기 스케일
    return round(pt * FSC, 1)

def S(w, h):                    # 캔버스 크기 스케일
    return (w * SZ, h * SZ)

plt.rcParams.update({
    "font.size": F(10), "axes.labelsize": F(11), "axes.labelweight": "bold",
    "xtick.labelsize": F(10.5), "ytick.labelsize": F(10.5), "legend.fontsize": F(9.5),
    "axes.linewidth": 1.2,
})

def box(ax, x, y, w, h, text, fc="#e3f2fd", ec=BLUE, fs=11, tc="#0d1b2a"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.01,rounding_size=0.06",
                                fc=fc, ec=ec, lw=1.6, zorder=3))
    ax.text(x + w/2, y + h/2, text, ha="center", va="center", fontsize=F(fs), color=tc, zorder=5)

def arrow(ax, p0, p1, text="", color="#37474f", fs=9, rad=0.0, tpos=0.5, tdx=0.0, tdy=0.16, tha="center"):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=15, color=color,
                                 lw=1.6, connectionstyle=f"arc3,rad={rad}", zorder=1))
    if text:
        lx = p0[0] + (p1[0]-p0[0])*tpos + tdx
        ly = p0[1] + (p1[1]-p0[1])*tpos + tdy
        ax.text(lx, ly, text, ha=tha, va="center", fontsize=F(fs), color=color, style="italic", zorder=6)

def save(fig, name):
    fig.savefig(os.path.join(OUT, name), dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig); print("  ✓", name)

# ── 1. MDP episode (or_comm) ────────────────────────────────────────────
fig, ax = plt.subplots(figsize=S(12.5, 4.9)); ax.set_xlim(0, 12.5); ax.set_ylim(0, 4.9); ax.axis("off")
ax.set_title("Proof as an MDP episode:   (A or B) -> (B or A)", fontsize=F(12.5), weight="bold")
box(ax, 0.1, 1.60, 2.1, 1.50, "s0\n(A or B)\n-> (B or A)", fs=10.5)
box(ax, 3.2, 1.60, 2.1, 1.50, "s1\nH: A or B\n|-  B or A", fs=10.5)
box(ax, 6.0, 3.20, 2.0, 1.15, "case A\n|- B or A", fc="#e8f5e9", ec=GREEN, fs=10.5)
box(ax, 6.0, 0.35, 2.0, 1.15, "case B\n|- B or A", fc="#e8f5e9", ec=GREEN, fs=10.5)
box(ax, 9.05, 3.35, 1.45, 0.85, "closed", fc="#fff3e0", ec=ORANGE, fs=10.5)
box(ax, 9.05, 0.50, 1.45, 0.85, "closed", fc="#fff3e0", ec=ORANGE, fs=10.5)
box(ax, 11.05, 1.75, 1.35, 1.20, "QED\nr = 1", fc="#fff3e0", ec=ORANGE, fs=10.5)
arrow(ax, (2.2, 2.35), (3.2, 2.35), "intro", tdy=0.26)      # gap 1.0 = 라벨 폭보다 넓게
arrow(ax, (5.3, 2.60), (6.0, 3.60), "")
arrow(ax, (5.3, 2.10), (6.0, 1.10), "")
ax.text(7.0, 2.35, "destruct H", ha="center", va="center", fontsize=F(9.5),
        color="#37474f", style="italic", zorder=6)          # 두 화살표 사이 빈 공간
arrow(ax, (8.0, 3.775), (9.05, 3.775), "right", tdy=0.28)
arrow(ax, (8.0, 0.925), (9.05, 0.925), "left", tdy=0.28)
arrow(ax, (10.5, 3.60), (11.05, 2.95), "")
arrow(ax, (10.5, 0.75), (11.05, 1.75), "")
ax.text(6.25, 4.68, "Reward is sparse & terminal:  0 everywhere,  1 only at QED",
        ha="center", fontsize=F(10.5), color=RED, weight="bold")
save(fig, "fig_mdp.png")

# ── 2. Rango architecture ───────────────────────────────────────────────
fig, ax = plt.subplots(figsize=S(13.2, 4.9)); ax.set_xlim(0, 13.2); ax.set_ylim(0, 4.9); ax.axis("off")
ax.set_title("Rango:  retrieval-augmented tactic generation", fontsize=F(12.5), weight="bold")
box(ax, 0.05, 3.50, 3.35, 0.90, "similar proofs\n(BM25)", fc="#f3e5f5", ec=PURPLE, fs=10.5)
box(ax, 0.05, 2.35, 3.35, 0.90, "current goal\nstate", fs=10.5)
box(ax, 0.05, 1.20, 3.35, 0.90, "relevant lemmas\n(TF-IDF)", fc="#f3e5f5", ec=PURPLE, fs=10.5)
box(ax, 3.95, 2.35, 1.60, 0.90, "prompt", fc="#eceff1", ec=GRAY, fs=11)
box(ax, 6.05, 2.00, 3.75, 1.60, "DeepSeek-Coder\n1.3B (fine-tuned)\n= policy pi_theta",
    fc="#e3f2fd", ec=BLUE, fs=10.5)
box(ax, 10.3, 2.25, 2.75, 1.10, "next-tactic\ndistribution", fs=10.5)
box(ax, 10.3, 0.55, 2.75, 1.00, "proof search\n(rollout)", fc="#e8f5e9", ec=GREEN, fs=10.5)
arrow(ax, (3.40, 3.95), (3.95, 2.95), "")
arrow(ax, (3.40, 2.80), (3.95, 2.80), "")
arrow(ax, (3.40, 1.65), (3.95, 2.65), "")
arrow(ax, (5.55, 2.80), (6.05, 2.80), "")
arrow(ax, (9.80, 2.80), (10.3, 2.80), "")
arrow(ax, (10.8, 2.25), (10.8, 1.55), "apply in Coq", tdx=0.18, tdy=0.0, tha="left")
arrow(ax, (10.3, 0.90), (3.40, 2.35), "", color=GREEN, rad=-0.26)
# 되먹임 라벨은 곡선이 낮게 지나는 오른쪽 구간 위에 둔다(왼쪽은 곡선이 가파르게 올라와 붙음)
ax.text(8.05, 1.45, "new goal  (loop back)", ha="center", va="center",
        fontsize=F(9), color=GREEN, style="italic", zorder=6)
save(fig, "fig_rango_arch.png")

# ── 3. subgoal tree (or_comm) ───────────────────────────────────────────
fig, ax = plt.subplots(figsize=S(10.3, 4.6)); ax.set_xlim(0, 10.3); ax.set_ylim(0, 4.6); ax.axis("off")
ax.set_title("A proof = closing a tree of subgoals", fontsize=F(12.5), weight="bold")
box(ax, 2.95, 3.35, 4.40, 1.00, "goal:\n(A or B) -> (B or A)", fs=10.5)
box(ax, 0.55, 1.70, 2.30, 1.10, "case A\n|- B or A", fc="#e8f5e9", ec=GREEN, fs=10.5)
box(ax, 7.45, 1.70, 2.30, 1.10, "case B\n|- B or A", fc="#e8f5e9", ec=GREEN, fs=10.5)
box(ax, 0.10, 0.50, 3.20, 0.75, "right; exact HA", fc="#fff3e0", ec=ORANGE, fs=10)
box(ax, 7.00, 0.50, 3.20, 0.75, "left; exact HB", fc="#fff3e0", ec=ORANGE, fs=10)
arrow(ax, (4.35, 3.35), (2.10, 2.80), "destruct H", tpos=0.4, tdx=-0.80, tdy=0.16)
arrow(ax, (5.95, 3.35), (8.20, 2.80), "destruct H", tpos=0.4, tdx=0.80, tdy=0.16)
arrow(ax, (1.70, 1.70), (1.70, 1.25), "")
arrow(ax, (8.60, 1.70), (8.60, 1.25), "")
ax.text(5.15, 0.10, "all subgoals closed  =>  QED", ha="center", fontsize=F(11),
        color=ORANGE, weight="bold")
save(fig, "fig_subgoal_tree.png")

# ── 4. dead / mixed / all-solved ────────────────────────────────────────
fig, ax = plt.subplots(figsize=S(8.0, 3.6))
cats = ["dead\n(8/8 fail)", "mixed\n(some pass)", "all-solved\n(8/8 pass)"]
vals = [64, 31, 5]; cols = [GRAY, GREEN, BLUE]
bars = ax.bar(cats, vals, color=cols, width=0.72)
for b, v in zip(bars, vals):
    ax.text(b.get_x()+b.get_width()/2, v+1.8, f"{v}%", ha="center", fontsize=F(13), weight="bold")
ax.set_ylabel("% of rollout groups"); ax.set_ylim(0, 84)
ax.set_title("Only 'mixed' gives a learning signal\n(dead + all-solved = zero gradient)",
             fontsize=F(11), weight="bold")
ax.text(0, 36, "no signal\n(adv = 0)", ha="center", color="white", fontsize=F(9.5), weight="bold")
ax.text(2, 18, "no signal\n(adv = 0)", ha="center", color=RED, fontsize=F(9.5), weight="bold")
save(fig, "fig_deadmixed.png")

# ── 5. overfitting (Set 2) ──────────────────────────────────────────────
fig, ax = plt.subplots(figsize=S(7.4, 4.4))
x = [1, 2, 3]
ax.plot(x, [36, 38, 43], "-o", color=GREEN, lw=2.8, ms=9)
ax.plot(x, [37.5, 37.5, 28], "-s", color=RED, lw=2.8, ms=9)
ax.axhline(37.5, ls="--", color=GRAY, lw=1.2)
ax.set_xticks(x); ax.set_xticklabels(["round 1", "round 2", "round 3"]); ax.set_ylabel("success rate (%)")
ax.set_xlim(0.7, 3.85); ax.set_ylim(14, 58)
ax.set_title("Set 2: repeating SFT->GRPO\ntrain up, held-out flat/down", fontsize=F(11), weight="bold")
# 범례(큰 박스)가 곡선을 덮으므로 선에 직접 라벨 — 발표용 가독성
ax.text(0.78, 48.0, "train coverage", color=GREEN, fontsize=F(10.5), weight="bold")
ax.text(0.78, 40.2, "baseline 37.5%", color=GRAY, fontsize=F(9.5))
ax.text(0.78, 31.0, "held-out (rand200)", color=RED, fontsize=F(10.5), weight="bold")
ax.annotate("train improves", (3.04, 43), (2.15, 51), color=GREEN, fontsize=F(10.5), weight="bold",
            arrowprops=dict(arrowstyle="->", color=GREEN))
ax.annotate("test drops\n= overfitting", (3.04, 28), (2.05, 18), color=RED, fontsize=F(10.5),
            weight="bold", arrowprops=dict(arrowstyle="->", color=RED))
save(fig, "fig_overfitting.png")

# ── 6. Set 1 results ────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=S(6.4, 4.4))
names = ["Rango\n(= SFT baseline)", "SFT -> GRPO"]
vals = [33.5, 37.5]; cols = [GRAY, BLUE]
bars = ax.bar(names, vals, color=cols, width=0.5)
for b, v, t in zip(bars, vals, ["33.5%", "37.5%"]):
    ax.text(b.get_x()+b.get_width()/2, v+1.3, t, ha="center", fontsize=F(14), weight="bold")
ax.axhline(37.5, ls="--", color=BLUE, lw=1.2)
ax.set_ylabel("success rate (%)"); ax.set_ylim(0, 50)
ax.set_title("CompCert held-out (rand200)\nbest = SFT->GRPO (+4.0%p)",
             fontsize=F(11), weight="bold")
save(fig, "fig_results.png")

# ── 7. domain gap ───────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=S(7.6, 3.9))
cats = ["pure math\n(miniF2F, Lean)\nDeepSeek-Prover-V2", "systems verif.\n(CompCert, Coq)\nRango (best)"]
vals = [88.9, 32.5]
bars = ax.bar(cats, vals, color=[GREEN, RED], width=0.5)
for b, v in zip(bars, vals):
    ax.text(b.get_x()+b.get_width()/2, v+2.5, f"{v}%", ha="center", fontsize=F(13.5), weight="bold")
ax.set_ylim(0, 105); ax.set_ylabel("success rate (%)")
ax.set_title("LLMs solve math well, CompCert stays hard (<40%)", fontsize=F(11), weight="bold")
save(fig, "fig_domain_gap.png")

# ── 8. Expert Iteration loop ────────────────────────────────────────────
fig, ax = plt.subplots(figsize=S(11.8, 5.4)); ax.set_xlim(0, 11.8); ax.set_ylim(0, 5.4); ax.axis("off")
ax.set_title("Expert Iteration (with overfitting safeguards)", fontsize=F(12.5), weight="bold")
box(ax, 0.10, 2.55, 2.60, 1.00, "policy pi_k", fc="#e3f2fd", ec=BLUE, fs=11)
box(ax, 3.30, 3.85, 3.60, 1.05, "rollout 300 thms\ncollect successes", fc="#e8f5e9", ec=GREEN, fs=10)
box(ax, 9.10, 3.85, 2.60, 1.05, "RFT + GRPO\n(KL -> pi_0)", fc="#eceff1", ec=GRAY, fs=10)
box(ax, 9.05, 2.10, 2.60, 1.00, "held-out val\n(early-stop)", fc="#fff3e0", ec=ORANGE, fs=10)
box(ax, 3.55, 0.60, 3.35, 0.90, "best -> rand200", fc="#fce4ec", ec=RED, fs=10.5)
arrow(ax, (2.70, 3.30), (3.30, 4.15), "")
arrow(ax, (6.90, 4.375), (9.10, 4.375), "+gold +accum", tdy=0.62)   # 라벨은 두 박스보다 위로
arrow(ax, (10.4, 3.85), (10.4, 3.10), "pi_k+1", tdx=0.18, tdy=0.0, tha="left")
arrow(ax, (9.05, 2.60), (2.70, 3.05), "improve? loop", color=BLUE, rad=0.22, tpos=0.55, tdy=0.45)
arrow(ax, (9.05, 2.30), (6.90, 1.50), "plateau -> stop", color=RED, tpos=0.5, tdx=-0.55, tdy=0.30)
ax.text(0.15, 1.15, "safeguards:\n- KL -> pi_0\n- gold + accum mix\n- low lr, 1 epoch\n- val early-stop",
        ha="left", va="center", fontsize=F(9.5), color="#0d1b2a",
        bbox=dict(boxstyle="round", fc="#f9fbe7", ec="#9e9d24"))
save(fig, "fig_ei_loop.png")

# ── 9. CompCert pipeline (semantic preservation) ────────────────────────
W, H = 17.5, 5.6
fig, ax = plt.subplots(figsize=S(W, H)); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")
ax.set_title("CompCert: every compilation pass is proven to preserve semantics",
             fontsize=F(12.5), weight="bold")
LANGS = ["C source\n(*.c)", "Clight", "Cminor", "RTL", "Asm\n(x86/ARM)"]
PASSES = ["parse+simpl", "stack alloc", "instr select", "optim+regalloc"]
BW, BH, STEP, BX0, BY = 2.60, 0.80, 3.66, 0.10, 4.38   # 언어 박스 행
Y_PROVED, Y_PASS = 5.40, 4.00                           # 박스 위/아래 라벨 행
for i, name in enumerate(LANGS):
    edge, face = (BLUE, "#e3f2fd") if 0 < i < 4 else (GREEN, "#e8f5e9")
    box(ax, BX0 + i*STEP, BY, BW, BH, name, fc=face, ec=edge, fs=10.5)
for i, p in enumerate(PASSES):
    x0, x1 = BX0 + i*STEP + BW, BX0 + (i+1)*STEP
    arrow(ax, (x0, BY + BH/2), (x1, BY + BH/2))
    ax.text((x0+x1)/2, Y_PASS, p, ha="center", va="center", fontsize=F(8.5),
            color="#37474f", style="italic")
    ax.text((x0+x1)/2, Y_PROVED, "proved", ha="center", va="center",
            fontsize=F(8), color=GREEN, weight="bold")
ax.add_patch(FancyBboxPatch((0.10, 2.50), W - 0.20, 0.86,
                            boxstyle="round,pad=0.01,rounding_size=0.06",
                            fc="#f1f8e9", ec=GREEN, lw=1.6, zorder=3))
ax.text(W/2, 3.16, "each pass is proven in Coq  (backward simulation):", ha="center",
        va="center", fontsize=F(9.5), color=GREEN, weight="bold", zorder=5)
ax.text(W/2, 2.72, "every behavior of the output program is a behavior of the input program",
        ha="center", va="center", fontsize=F(9.5), color="#0d1b2a", zorder=5)
arrow(ax, (W/2, 2.50), (W/2, 1.98), color=GREEN)
ax.add_patch(FancyBboxPatch((0.85, 0.62), W - 1.70, 1.36,
                            boxstyle="round,pad=0.01,rounding_size=0.06",
                            fc="#fff3e0", ec=ORANGE, lw=1.8, zorder=3))
ax.text(W/2, 1.62, "compose all passes  =>  CompCert's top-level theorem", ha="center",
        va="center", fontsize=F(9), color=ORANGE, style="italic", zorder=5)
ax.text(W/2, 1.10, "transf_c_program p = OK tp  ->  backward_simulation (Csem p) (Asm tp)",
        ha="center", va="center", fontsize=F(10.5), color="#0d1b2a", weight="bold", zorder=5)
save(fig, "fig_compcert_pipeline.png")

print("done ->", OUT)
