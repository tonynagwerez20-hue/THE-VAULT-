# analysis_sequence_signal.py
"""
AlgoMind AMIGO P3.2 Analysis Script
Task 8: Sequence dependence analysis (max drawdown, streaks) vs 10,000 shuffled baselines
Task 9: Signal quality diagnostics (correlations of available features with realized R)

Generates PNG plots and walkthrough.md in the same folder.
No strategy parameters are changed. Read-only analysis of the trade-level dataset.
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "algomind_trade_level_dataset.csv"
WALKTHROUGH_PATH = BASE_DIR / "walkthrough.md"

# ── Load dataset ──────────────────────────────────────────────────────────────
print("Loading dataset...")
df = pd.read_csv(CSV_PATH)
df["entry_time"] = pd.to_datetime(df["entry_time"], format="%Y.%m.%d %H:%M:%S")
df = df.sort_values("entry_time").reset_index(drop=True)

# Derived columns
df["stop_distance"] = (df["entry_price"] - df["sl"]).abs()
df["RealizedR"] = df["r_multiple"]

n_trades = len(df)
print(f"Loaded {n_trades} trades.")

# ── Helper functions ──────────────────────────────────────────────────────────

def max_drawdown_r(series):
    """Maximum drawdown of cumulative RealizedR series."""
    cum = np.array(series).cumsum()
    peak = np.maximum.accumulate(cum)
    drawdown = peak - cum
    return float(drawdown.max())

def longest_streak(arr, positive):
    """Longest consecutive run of wins (positive=True) or losses (positive=False)."""
    count = max_run = 0
    for v in arr:
        if (positive and v > 0) or (not positive and v < 0):
            count += 1
            max_run = max(max_run, count)
        else:
            count = 0
    return max_run

# ── Task 8: Sequence Dependence ───────────────────────────────────────────────
print("Computing baseline metrics...")
realized = df["RealizedR"].values.copy()

baseline_max_dd      = max_drawdown_r(realized)
baseline_loss_streak = longest_streak(realized, positive=False)
baseline_win_streak  = longest_streak(realized, positive=True)

print(f"  Max Drawdown (R):      {baseline_max_dd:.4f}")
print(f"  Longest losing streak: {baseline_loss_streak}")
print(f"  Longest winning streak:{baseline_win_streak}")

N_SHUFFLES = 10000
print(f"Running {N_SHUFFLES} Monte Carlo shuffles...")
shuf_dd   = np.empty(N_SHUFFLES)
shuf_loss = np.empty(N_SHUFFLES, dtype=int)
shuf_win  = np.empty(N_SHUFFLES, dtype=int)
buf = realized.copy()
for i in range(N_SHUFFLES):
    np.random.shuffle(buf)
    shuf_dd[i]   = max_drawdown_r(buf)
    shuf_loss[i] = longest_streak(buf, positive=False)
    shuf_win[i]  = longest_streak(buf, positive=True)
    if (i + 1) % 1000 == 0:
        print(f"  {i+1}/{N_SHUFFLES}")

def dist_stats(arr, actual):
    return {
        "mean":    arr.mean(),
        "median":  float(np.median(arr)),
        "p5":      float(np.percentile(arr, 5)),
        "p95":     float(np.percentile(arr, 95)),
        "actual":  actual,
        "p_value": float((arr >= actual).mean()),
    }

stats_dd   = dist_stats(shuf_dd,   baseline_max_dd)
stats_loss = dist_stats(shuf_loss, baseline_loss_streak)
stats_win  = dist_stats(shuf_win,  baseline_win_streak)

# ── Histogram plots ───────────────────────────────────────────────────────────
def save_hist(data, actual, title, filename):
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.histplot(data, kde=True, bins=40, color="steelblue", ax=ax)
    ax.axvline(actual, color="crimson", linewidth=2, linestyle="--", label=f"Actual = {actual:.3f}")
    ax.set_title(title)
    ax.set_xlabel("Value")
    ax.set_ylabel("Frequency")
    ax.legend()
    fig.tight_layout()
    path = BASE_DIR / filename
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path

print("Saving histogram plots...")
plot_dd   = save_hist(shuf_dd,   baseline_max_dd,      "Max Drawdown (R) – Shuffled vs Actual",       "hist_max_drawdown.png")
plot_loss = save_hist(shuf_loss, baseline_loss_streak, "Longest Losing Streak – Shuffled vs Actual",  "hist_longest_loss.png")
plot_win  = save_hist(shuf_win,  baseline_win_streak,  "Longest Winning Streak – Shuffled vs Actual", "hist_longest_win.png")

# ── Task 9: Signal Quality Diagnostics ───────────────────────────────────────
print("Computing signal quality diagnostics...")

# Numeric feature correlations with RealizedR
numeric_features = ["stop_distance", "volume", "planned_risk"]
corr_rows = []
for feat in numeric_features:
    p = df[feat].corr(df["RealizedR"], method="pearson")
    s = df[feat].corr(df["RealizedR"], method="spearman")
    corr_rows.append({"Feature": feat, "Pearson r": round(p, 4), "Spearman rho": round(s, 4)})
corr_df = pd.DataFrame(corr_rows)

# Direction performance
dir_group = df.groupby("direction")["RealizedR"].agg(
    count="count", mean_R="mean", std_R="std", win_rate=lambda x: (x > 0).mean()
).reset_index()

# Exit type performance
trig_group = df.groupby("trig")["RealizedR"].agg(
    count="count", mean_R="mean", std_R="std", win_rate=lambda x: (x > 0).mean()
).reset_index()

# Monthly performance
df["month"] = df["entry_time"].dt.to_period("M").astype(str)
monthly = df.groupby("month")["RealizedR"].agg(
    count="count", mean_R="mean", cumulative_R="sum"
).reset_index()

# Scatter: stop_distance vs RealizedR coloured by direction
fig, ax = plt.subplots(figsize=(8, 5))
for d, grp in df.groupby("direction"):
    ax.scatter(grp["stop_distance"], grp["RealizedR"], label=d, alpha=0.5, s=20)
ax.axhline(0, color="grey", linewidth=0.8)
ax.set_xlabel("Stop Distance (price pts)")
ax.set_ylabel("Realized R")
ax.set_title("Stop Distance vs Realized R")
ax.legend()
fig.tight_layout()
plot_scatter_sd = BASE_DIR / "scatter_stop_distance.png"
fig.savefig(plot_scatter_sd, dpi=120)
plt.close(fig)

# Box plot: RealizedR by direction
fig, axes = plt.subplots(1, 2, figsize=(10, 5))
sns.boxplot(data=df, x="direction", y="RealizedR", ax=axes[0])
axes[0].set_title("Realized R by Direction")
sns.boxplot(data=df, x="trig", y="RealizedR", ax=axes[1])
axes[1].set_title("Realized R by Exit Type")
fig.tight_layout()
plot_box = BASE_DIR / "box_realizedR.png"
fig.savefig(plot_box, dpi=120)
plt.close(fig)

# Monthly cumulative R chart
fig, ax = plt.subplots(figsize=(10, 4))
ax.bar(monthly["month"], monthly["cumulative_R"], color="steelblue")
ax.axhline(0, color="grey", linewidth=0.8)
ax.set_xlabel("Month")
ax.set_ylabel("Sum Realized R")
ax.set_title("Monthly Realized R")
plt.xticks(rotation=45, ha="right")
fig.tight_layout()
plot_monthly = BASE_DIR / "monthly_realizedR.png"
fig.savefig(plot_monthly, dpi=120)
plt.close(fig)

# ── Walkthrough markdown ──────────────────────────────────────────────────────
print("Writing walkthrough.md ...")
with open(WALKTHROUGH_PATH, "w", encoding="utf-8") as md:
    md.write("# AlgoMind AMIGO - P3.2 Analysis Walkthrough\n\n")
    md.write(f"Dataset: {n_trades} executed trades | XAUUSDm M5 | 2025-10-01 to 2026-08-28\n\n")

    # ── Task 8 ────────────────────────────────────────────────────────────────
    md.write("---\n\n## Task 8 — Sequence Dependence Analysis\n\n")
    md.write("Monte Carlo test: 10,000 shuffles of the R-multiple sequence.\n")
    md.write("p-value = fraction of shuffled populations >= actual (one-sided).\n\n")

    md.write("### Baseline Metrics\n\n")
    md.write(f"| Metric | Actual |\n")
    md.write(f"|---|---|\n")
    md.write(f"| Max Drawdown (R) | {baseline_max_dd:.4f} |\n")
    md.write(f"| Longest Losing Streak | {baseline_loss_streak} |\n")
    md.write(f"| Longest Winning Streak | {baseline_win_streak} |\n\n")

    md.write("### Monte Carlo Summary\n\n")
    md.write("| Metric | Shuffled Mean | Shuffled Median | 5th pct | 95th pct | Actual | p-value |\n")
    md.write("|---|---|---|---|---|---|---|\n")
    md.write(
        f"| Max Drawdown (R) | {stats_dd['mean']:.4f} | {stats_dd['median']:.4f} | "
        f"{stats_dd['p5']:.4f} | {stats_dd['p95']:.4f} | {stats_dd['actual']:.4f} | {stats_dd['p_value']:.4f} |\n"
    )
    md.write(
        f"| Longest Losing Streak | {stats_loss['mean']:.2f} | {stats_loss['median']:.2f} | "
        f"{stats_loss['p5']:.2f} | {stats_loss['p95']:.2f} | {stats_loss['actual']} | {stats_loss['p_value']:.4f} |\n"
    )
    md.write(
        f"| Longest Winning Streak | {stats_win['mean']:.2f} | {stats_win['median']:.2f} | "
        f"{stats_win['p5']:.2f} | {stats_win['p95']:.2f} | {stats_win['actual']} | {stats_win['p_value']:.4f} |\n"
    )
    md.write("\n")

    # Interpretation
    dd_sig   = "SIGNIFICANT (p < 0.05)" if stats_dd['p_value']   < 0.05 else "NOT significant (p >= 0.05)"
    loss_sig = "SIGNIFICANT (p < 0.05)" if stats_loss['p_value'] < 0.05 else "NOT significant (p >= 0.05)"
    win_sig  = "SIGNIFICANT (p < 0.05)" if stats_win['p_value']  < 0.05 else "NOT significant (p >= 0.05)"

    md.write("### Interpretation\n\n")
    md.write(f"- Max Drawdown: **{dd_sig}** — ")
    md.write("actual drawdown is worse than random order.\n" if stats_dd['p_value'] < 0.05 else "losses are not clustered worse than random.\n")
    md.write(f"- Losing Streak: **{loss_sig}** — ")
    md.write("actual losing streaks are longer than random order.\n" if stats_loss['p_value'] < 0.05 else "losing streaks are consistent with random ordering.\n")
    md.write(f"- Winning Streak: **{win_sig}** — ")
    md.write("actual winning streaks are longer than random order.\n\n" if stats_win['p_value'] < 0.05 else "winning streaks are consistent with random ordering.\n\n")

    md.write("### Histogram Plots\n\n")
    md.write(f"![]({plot_dd.as_uri()})\n\n")
    md.write(f"![]({plot_loss.as_uri()})\n\n")
    md.write(f"![]({plot_win.as_uri()})\n\n")

    # ── Task 9 ────────────────────────────────────────────────────────────────
    md.write("---\n\n## Task 9 — Signal Quality Diagnostics\n\n")

    md.write("### Numeric Feature Correlations with Realized R\n\n")
    md.write(corr_df.to_markdown(index=False))
    md.write("\n\n")

    md.write("### Performance by Direction\n\n")
    md.write(dir_group.to_markdown(index=False))
    md.write("\n\n")

    md.write("### Performance by Exit Type\n\n")
    md.write(trig_group.to_markdown(index=False))
    md.write("\n\n")

    md.write("### Monthly Performance\n\n")
    md.write(monthly.to_markdown(index=False))
    md.write("\n\n")

    md.write("### Scatter Plot: Stop Distance vs Realized R\n\n")
    md.write(f"![]({plot_scatter_sd.as_uri()})\n\n")

    md.write("### Box Plots: Realized R by Direction and Exit Type\n\n")
    md.write(f"![]({plot_box.as_uri()})\n\n")

    md.write("### Monthly Realized R Bar Chart\n\n")
    md.write(f"![]({plot_monthly.as_uri()})\n\n")

    md.write("---\n\n")
    md.write("*All analyses are read-only. No strategy parameters, risk settings, or code were modified.*\n")

print("Done. Output files:")
print(f"  walkthrough.md       -> {WALKTHROUGH_PATH}")
print(f"  hist_max_drawdown.png-> {plot_dd}")
print(f"  hist_longest_loss.png-> {plot_loss}")
print(f"  hist_longest_win.png -> {plot_win}")
print(f"  scatter_stop_distance-> {plot_scatter_sd}")
print(f"  box_realizedR.png    -> {plot_box}")
print(f"  monthly_realizedR.png-> {plot_monthly}")
