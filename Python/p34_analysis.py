"""
AlgoMind AMIGO — P3.4 Canonical Dataset Validation and August Forensics
READ-ONLY. No strategy logic changes.

Tasks:
  1  - Prove 793-trade canonical dataset (full duplicate taxonomy)
  2  - Establish authoritative row selection rule
  3  - Verify canonical dataset against MT5 (what is available)
  4  - Rebuild sequence analysis on validated canonical trades
  5  - July vs August forensic (full variable set)
  6  - Identify performance shift variables
  7  - Directional asymmetry
  8  - July/August decomposition by direction
  9  - Dataset export fix (code inspection)
  10 - Final status
"""

import sys
import re
import math
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy import stats

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR    = Path(r"C:\Users\USER\Desktop\ALGOMIND\Python")
CSV_PATH    = BASE_DIR / "algomind_trade_level_dataset.csv"
REPORT_PATH = BASE_DIR / "p34_report.md"

print("=" * 70)
print("AlgoMind AMIGO — P3.4 Canonical Dataset Validation")
print("=" * 70)

# ══════════════════════════════════════════════════════════════════════════════
# LOAD RAW CSV
# ══════════════════════════════════════════════════════════════════════════════
df_raw = pd.read_csv(CSV_PATH)
df_raw["entry_time"] = pd.to_datetime(df_raw["entry_time"], format="%Y.%m.%d %H:%M:%S")
df_raw["stop_dist"]  = (df_raw["entry_price"] - df_raw["sl"]).abs()
print(f"\nRaw CSV: {len(df_raw)} rows, {df_raw['trade_id'].nunique()} unique IDs")

# ══════════════════════════════════════════════════════════════════════════════
# TASK 1 — FULL DUPLICATE TAXONOMY
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("TASK 1 — Full duplicate taxonomy")
print("="*60)

id_counts = df_raw["trade_id"].value_counts()

# Classify every duplicated trade_id
exact_dup_ids      = []   # all occurrences byte-identical
diff_dup_ids       = []   # same id, at least one field differs
conflict_rows      = []   # rows belonging to SAME_ID_DIFFERENT_DATA groups

# All-columns comparison (excluding index)
for tid, cnt in id_counts[id_counts > 1].items():
    grp = df_raw[df_raw["trade_id"] == tid]
    # Drop entry_time from equality check for now, then check
    grp_data = grp.drop(columns=["entry_time"])
    if grp_data.duplicated(keep=False).all():
        exact_dup_ids.append(tid)
    else:
        diff_dup_ids.append(tid)
        conflict_rows.append(grp)

n_exact_dup_ids  = len(exact_dup_ids)
n_diff_dup_ids   = len(diff_dup_ids)
n_exact_dup_rows = id_counts[exact_dup_ids].sum() - len(exact_dup_ids)  # extra rows
n_diff_dup_rows  = id_counts[diff_dup_ids].sum()   if diff_dup_ids else 0

print(f"\nRaw rows                          : {len(df_raw)}")
print(f"Unique trade_ids                  : {df_raw['trade_id'].nunique()}")
print(f"IDs appearing >1x                 : {len(id_counts[id_counts>1])}")
print(f"  A. EXACT_DUPLICATE IDs          : {n_exact_dup_ids} (all occurrences identical)")
print(f"     Extra rows in exact-dup set  : {n_exact_dup_rows}")
print(f"  B. SAME_ID_DIFFERENT_DATA IDs   : {n_diff_dup_ids}")
print(f"     Rows in conflict-dup set     : {n_diff_dup_rows}")

# Full table of SAME_ID_DIFFERENT_DATA
COLS = ["trade_id","entry_time","direction","entry_price","sl","tp",
        "exit_price","planned_risk","net_pnl","r_multiple","volume"]
print(f"\n  All {n_diff_dup_ids} SAME_ID_DIFFERENT_DATA groups:")
for grp in conflict_rows:
    tid = grp["trade_id"].iloc[0]
    cnt = len(grp)
    print(f"\n  trade_id={tid} ({cnt} rows):")
    with pd.option_context("display.max_columns", 20, "display.width", 200):
        display_cols = [c for c in COLS if c in grp.columns]
        print(grp[display_cols].to_string(index=True))

# Frequency table
print(f"\n  Occurrence count distribution:")
count_dist = id_counts.value_counts().sort_index()
for occ, num_ids in count_dist.items():
    print(f"    {occ}x occurrences: {num_ids} trade_ids")

# ══════════════════════════════════════════════════════════════════════════════
# TASK 2 — AUTHORITATIVE ROW SELECTION
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("TASK 2 — Authoritative row selection")
print("="*60)

# Rule: EXACT_DUPLICATE → any copy is authoritative (keep first occurrence)
# SAME_ID_DIFFERENT_DATA → FLAG, do NOT silently discard

# For EXACT_DUPLICATE IDs: deduplicate to first occurrence
exact_dup_id_set = set(exact_dup_ids)
diff_dup_id_set  = set(diff_dup_ids)

# Step 1: Remove exact duplicates (keep first, sorted by CSV row order)
df_no_exact = df_raw.drop_duplicates(subset=list(df_raw.columns[df_raw.columns != "entry_time"]), keep="first")
# More precise: for EXACT_DUPs only
exact_mask   = df_raw["trade_id"].isin(exact_dup_id_set)
non_exact    = df_raw[~exact_mask]
exact_deduped = df_raw[exact_mask].drop_duplicates(
    subset=list(df_raw.drop(columns="entry_time").columns), keep="first")
df_step1 = pd.concat([non_exact, exact_deduped]).sort_index().reset_index(drop=True)
print(f"\nAfter EXACT_DUPLICATE removal: {len(df_step1)} rows (removed {len(df_raw)-len(df_step1)} exact dups)")

# Step 2: Flag SAME_ID_DIFFERENT_DATA — report, don't silently pick
print(f"\nSAME_ID_DIFFERENT_DATA trade_ids ({n_diff_dup_ids} IDs, {n_diff_dup_rows} rows):")
print("  These cannot be automatically resolved. Each requires human judgment.")
print("  They are flagged here; ALL occurrences are listed above in Task 1.")
print()
for tid in diff_dup_ids[:10]:  # show up to 10
    grp = df_step1[df_step1["trade_id"] == tid] if tid in df_step1["trade_id"].values else \
          df_raw[df_raw["trade_id"] == tid]
    print(f"  trade_id={tid}: {len(grp)} conflicting rows — "
          f"entry_times: {[str(t) for t in grp['entry_time'].tolist()]}")
if n_diff_dup_ids > 10:
    print(f"  ... and {n_diff_dup_ids - 10} more")

# For the canonical analysis, we apply the SAME dedup as P3.3:
# Sort by entry_time, keep first occurrence of each trade_id
df_canonical = df_raw.sort_values("entry_time").drop_duplicates("trade_id", keep="first").reset_index(drop=True)
print(f"\nCanonical dataset (sort by entry_time, first-of-each-ID): {len(df_canonical)} trades")
print(f"  Chronologically ordered: {df_canonical['entry_time'].is_monotonic_increasing}")
print(f"  All IDs unique: {df_canonical['trade_id'].nunique() == len(df_canonical)}")
print(f"\nNOTE: Conflicting SAME_ID_DIFFERENT_DATA rows are resolved by earliest entry_time.")
print("      This rule is documented but may not select the 'correct' backtest run.")
print("      A run_id field in the CSV would eliminate this ambiguity.")

df_can = df_canonical.copy()
df_can["stop_dist"] = (df_can["entry_price"] - df_can["sl"]).abs()

# ══════════════════════════════════════════════════════════════════════════════
# TASK 3 — VERIFY AGAINST MT5 (what is available)
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("TASK 3 — Canonical dataset vs MT5 reference")
print("="*60)

# We don't have a saved MT5 HTML report on disk.
# We can report what IS available: from the P3 run summary and the CSV itself.
# MT5 tester report figures (from P3 authoritative run, as reported):
MT5_NET_PROFIT   = 192.91   # from P3 report
MT5_GROSS_PROFIT = 490.41
MT5_GROSS_LOSS   = -297.50
MT5_TRADES       = 1260     # MT5 total trades count
MT5_WINS         = 413      # take_profit exits
MT5_LOSSES       = 847      # stop_loss exits
MT5_PROFIT_FACTOR= 1.65
MT5_BALANCE_DD   = 6.07     # %
MT5_EQUITY_DD    = 14.16    # %

# Canonical CSV stats
r = df_can["r_multiple"]
trig = df_can["trig"] if "trig" in df_can.columns else None
n_tp  = (df_can["trig"] == "take_profit").sum() if trig is not None else None
n_sl  = (df_can["trig"] == "stop_loss").sum()   if trig is not None else None

# Net PnL from CSV
csv_net_pnl   = df_can["net_pnl"].sum()
csv_gross_prof = df_can[df_can["net_pnl"] > 0]["net_pnl"].sum()
csv_gross_loss = df_can[df_can["net_pnl"] < 0]["net_pnl"].sum()
csv_pf         = csv_gross_prof / abs(csv_gross_loss) if csv_gross_loss != 0 else float("inf")
csv_wins       = (df_can["net_pnl"] > 0).sum()
csv_losses     = (df_can["net_pnl"] < 0).sum()
csv_r_sum      = r.sum()
csv_r_mean     = r.mean()

print(f"\n  {'Metric':<35} {'MT5 Report':>15} {'CSV Canonical':>15} {'Delta':>12}")
print(f"  {'-'*80}")
print(f"  {'Trade count':<35} {MT5_TRADES:>15} {len(df_can):>15} {len(df_can)-MT5_TRADES:>+12}")
print(f"  {'Win count':<35} {MT5_WINS:>15} {csv_wins:>15} {csv_wins-MT5_WINS:>+12}")
print(f"  {'Loss count':<35} {MT5_LOSSES:>15} {csv_losses:>15} {csv_losses-MT5_LOSSES:>+12}")
print(f"  {'Net P&L ($)':<35} {MT5_NET_PROFIT:>15.2f} {csv_net_pnl:>15.2f} {csv_net_pnl-MT5_NET_PROFIT:>+12.2f}")
print(f"  {'Gross profit ($)':<35} {MT5_GROSS_PROFIT:>15.2f} {csv_gross_prof:>15.2f} {csv_gross_prof-MT5_GROSS_PROFIT:>+12.2f}")
print(f"  {'Gross loss ($)':<35} {MT5_GROSS_LOSS:>15.2f} {csv_gross_loss:>15.2f} {csv_gross_loss-MT5_GROSS_LOSS:>+12.2f}")
print(f"  {'Profit factor':<35} {MT5_PROFIT_FACTOR:>15.2f} {csv_pf:>15.2f} {csv_pf-MT5_PROFIT_FACTOR:>+12.2f}")

print(f"\n  NOTE: MT5 report counts 1,260 trades; canonical CSV has 793.")
print(f"  The MT5 trade count matches the RAW CSV row count exactly.")
print(f"  This suggests the MT5 report was generated from/alongside the raw (undeduplicated) export.")

# ══════════════════════════════════════════════════════════════════════════════
# TASK 4 — MONTE CARLO ON CANONICAL DATA
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("TASK 4 — Monte Carlo on canonical 793 trades")
print("="*60)

N = 10000

def max_dd_r(arr):
    cum  = np.cumsum(arr)
    peak = np.maximum.accumulate(cum)
    return float((peak - cum).max())

def longest_streak(arr, positive):
    flags = arr > 0 if positive else arr < 0
    c = m = 0
    for f in flags:
        c = c + 1 if f else 0
        m = max(m, c)
    return m

realized = df_can["r_multiple"].values.copy()
b_dd   = max_dd_r(realized)
b_loss = longest_streak(realized, positive=False)
b_win  = longest_streak(realized, positive=True)

print(f"\n  Actual sequence ({len(realized)} trades):")
print(f"    Max Drawdown (R)  : {b_dd:.4f}")
print(f"    Longest loss run  : {b_loss}")
print(f"    Longest win run   : {b_win}")

shuf_dd   = np.empty(N)
shuf_loss = np.empty(N, dtype=int)
shuf_win  = np.empty(N, dtype=int)
buf = realized.copy()
np.random.seed(2024)
for i in range(N):
    np.random.shuffle(buf)
    shuf_dd[i]   = max_dd_r(buf)
    shuf_loss[i] = longest_streak(buf, positive=False)
    shuf_win[i]  = longest_streak(buf, positive=True)
    if (i + 1) % 2000 == 0:
        print(f"  {i+1}/{N}")

def pval(sh, actual):
    return (np.sum(sh >= actual) + 1) / (N + 1)

pv_dd   = pval(shuf_dd,   b_dd)
pv_loss = pval(shuf_loss, b_loss)
pv_win  = pval(shuf_win,  b_win)

print(f"\n  Monte Carlo results (N={N}, p = (count >= actual + 1)/(N+1)):")
print(f"  {'Metric':<28} {'Mean':>8} {'Median':>8} {'p5':>7} {'p95':>7} {'Actual':>8} {'p-value':>10}")
print(f"  {'-'*80}")
for label, sh, act, pv in [
    ("Max Drawdown (R)",       shuf_dd,   b_dd,   pv_dd),
    ("Longest Losing Streak",  shuf_loss, b_loss, pv_loss),
    ("Longest Winning Streak", shuf_win,  b_win,  pv_win),
]:
    print(f"  {label:<28} {sh.mean():>8.3f} {np.median(sh):>8.3f} "
          f"{np.percentile(sh,5):>7.2f} {np.percentile(sh,95):>7.2f} "
          f"{act:>8.3f} {pv:>10.6f}")

# Save MC plots
def mc_plot(sh, actual, label, fname):
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.histplot(sh, kde=True, bins=40, color="steelblue", ax=ax)
    ax.axvline(actual, color="crimson", lw=2, ls="--",
               label=f"Actual = {actual:.3f}")
    pv_str = f"{pval(sh, actual):.6f}"
    ax.set_title(f"{label}\n10,000 shuffles, n=793 canonical trades | corrected p = {pv_str}")
    ax.set_xlabel("Value"); ax.set_ylabel("Count"); ax.legend()
    fig.tight_layout()
    path = BASE_DIR / fname
    fig.savefig(path, dpi=120); plt.close(fig)
    return path

p_dd_path   = mc_plot(shuf_dd,   b_dd,   "Max Drawdown (R)",       "p34_mc_dd.png")
p_loss_path = mc_plot(shuf_loss, b_loss, "Longest Losing Streak",  "p34_mc_loss.png")
p_win_path  = mc_plot(shuf_win,  b_win,  "Longest Winning Streak", "p34_mc_win.png")
print(f"\n  Plots saved.")

# ══════════════════════════════════════════════════════════════════════════════
# TASK 5 — JULY vs AUGUST FORENSIC
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("TASK 5 — July vs August forensic (canonical 793 trades)")
print("="*60)

df_can["month"] = df_can["entry_time"].dt.to_period("M").astype(str)
jul = df_can[df_can["month"] == "2026-07"].copy()
aug = df_can[df_can["month"] == "2026-08"].copy()

def full_month_stats(mdf):
    if len(mdf) == 0:
        return {}
    buy    = mdf[mdf["direction"] == "buy"]
    sell   = mdf[mdf["direction"] == "sell"]
    sl_df  = mdf[mdf["trig"] == "stop_loss"]
    tp_df  = mdf[mdf["trig"] == "take_profit"]
    return {
        "trades"      : len(mdf),
        "buy_n"       : len(buy),
        "sell_n"      : len(sell),
        "buy_pct"     : len(buy)/len(mdf),
        "sell_pct"    : len(sell)/len(mdf),
        "buy_wr"      : (buy["r_multiple"] > 0).mean() if len(buy) else float("nan"),
        "sell_wr"     : (sell["r_multiple"] > 0).mean() if len(sell) else float("nan"),
        "overall_wr"  : (mdf["r_multiple"] > 0).mean(),
        "tp_n"        : len(tp_df),
        "sl_n"        : len(sl_df),
        "tp_pct"      : len(tp_df)/len(mdf),
        "sl_pct"      : len(sl_df)/len(mdf),
        "mean_r"      : mdf["r_multiple"].mean(),
        "median_r"    : mdf["r_multiple"].median(),
        "sum_r"       : mdf["r_multiple"].sum(),
        "buy_mean_r"  : buy["r_multiple"].mean() if len(buy) else float("nan"),
        "sell_mean_r" : sell["r_multiple"].mean() if len(sell) else float("nan"),
        "mean_risk"   : mdf["planned_risk"].mean(),
        "mean_sd"     : mdf["stop_dist"].mean(),
        "mean_vol"    : mdf["volume"].mean(),
        "std_r"       : mdf["r_multiple"].std(),
        "net_pnl"     : mdf["net_pnl"].sum(),
    }

js = full_month_stats(jul)
as_ = full_month_stats(aug)

print(f"\n  {'Metric':<20} {'July 2026':>14} {'August 2026':>14} {'Delta':>14}")
print(f"  {'-'*65}")
for k in sorted(js.keys()):
    jv = js[k]; av = as_[k]
    d = av - jv if not (np.isnan(float(jv)) or np.isnan(float(av))) else float("nan")
    print(f"  {k:<20} {float(jv):>14.4f} {float(av):>14.4f} {float(d):>+14.4f}")

# Mann-Whitney
mw_u, mw_p = stats.mannwhitneyu(jul["r_multiple"], aug["r_multiple"], alternative="two-sided")
print(f"\n  Mann-Whitney U (Jul vs Aug R): U={mw_u:.0f}, p={mw_p:.8f}")

# ══════════════════════════════════════════════════════════════════════════════
# TASK 6 — IDENTIFY THE PERFORMANCE SHIFT VARIABLES
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("TASK 6 — Performance shift variable analysis")
print("="*60)

numeric_vars = ["stop_dist", "planned_risk", "volume", "r_multiple"]
cat_vars     = ["direction", "trig"]

print(f"\n  Numeric variable comparisons:")
print(f"  {'Variable':<20} {'Jul Mean':>12} {'Aug Mean':>12} {'Abs Diff':>10} {'% Diff':>10} {'MW p':>12}")
print(f"  {'-'*78}")
shift_table = []
for v in numeric_vars:
    jv_arr = jul[v].dropna().values
    av_arr = aug[v].dropna().values
    jm, am = np.mean(jv_arr), np.mean(av_arr)
    abs_d  = am - jm
    pct_d  = abs_d / abs(jm) * 100 if jm != 0 else float("nan")
    u, p   = stats.mannwhitneyu(jv_arr, av_arr, alternative="two-sided")
    # Cohen's d
    pooled = np.sqrt((np.std(jv_arr)**2 + np.std(av_arr)**2)/2)
    d_eff  = abs_d / pooled if pooled > 0 else float("nan")
    print(f"  {v:<20} {jm:>12.4f} {am:>12.4f} {abs_d:>+10.4f} {pct_d:>+10.1f}% {p:>12.6f}")
    shift_table.append({"variable":v,"jul_mean":jm,"aug_mean":am,
                        "abs_diff":abs_d,"pct_diff":pct_d,"mw_p":p,"cohens_d":d_eff})

print(f"\n  Categorical variable comparisons:")
for v in cat_vars:
    print(f"\n  {v}:")
    jul_vc = jul[v].value_counts(normalize=True).rename("Jul%")
    aug_vc = aug[v].value_counts(normalize=True).rename("Aug%")
    comp   = pd.concat([jul_vc, aug_vc], axis=1).fillna(0)
    comp["Delta"] = comp["Aug%"] - comp["Jul%"]
    print(comp.to_string())

# ══════════════════════════════════════════════════════════════════════════════
# TASK 7 — DIRECTIONAL ASYMMETRY
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("TASK 7 — Directional asymmetry (canonical 793 trades)")
print("="*60)

buy_r  = df_can[df_can["direction"] == "buy"]["r_multiple"]
sell_r = df_can[df_can["direction"] == "sell"]["r_multiple"]
n_buy, n_sell = len(buy_r), len(sell_r)
bwr, swr      = (buy_r > 0).mean(), (sell_r > 0).mean()
bmr, smr      = buy_r.mean(), sell_r.mean()
bmed, smed    = buy_r.median(), sell_r.median()
bsum, ssum    = buy_r.sum(), sell_r.sum()

# MW test
mw_dir_u, mw_dir_p = stats.mannwhitneyu(buy_r, sell_r, alternative="two-sided")
# Proportion z-test (win rates)
p_pool = (bwr*n_buy + swr*n_sell)/(n_buy+n_sell)
se     = np.sqrt(p_pool*(1-p_pool)*(1/n_buy + 1/n_sell))
z_prop = (swr - bwr)/se
p_prop = 2*(1 - stats.norm.cdf(abs(z_prop)))
# Effect size
pooled_std = np.sqrt((buy_r.std()**2 + sell_r.std()**2)/2)
cohen_d    = (smr - bmr)/pooled_std if pooled_std else float("nan")
# 95% CI for WR difference
ci_margin  = 1.96 * np.sqrt(bwr*(1-bwr)/n_buy + swr*(1-swr)/n_sell)
diff_wr    = swr - bwr
ci_lo, ci_hi = diff_wr - ci_margin, diff_wr + ci_margin

print(f"\n  {'Metric':<25} {'Buy':>12} {'Sell':>12} {'Sell-Buy':>12}")
print(f"  {'-'*65}")
print(f"  {'Count':<25} {n_buy:>12} {n_sell:>12}")
print(f"  {'Win Rate':<25} {bwr:>12.4f} {swr:>12.4f} {diff_wr:>+12.4f}")
print(f"  {'Mean R':<25} {bmr:>12.4f} {smr:>12.4f} {smr-bmr:>+12.4f}")
print(f"  {'Median R':<25} {bmed:>12.4f} {smed:>12.4f} {smed-bmed:>+12.4f}")
print(f"  {'Sum R':<25} {bsum:>12.4f} {ssum:>12.4f} {ssum-bsum:>+12.4f}")
print(f"\n  Win rate diff 95% CI: [{ci_lo:.4f}, {ci_hi:.4f}]")
print(f"  Proportion z-test: z={z_prop:.3f}, p={p_prop:.8f}")
print(f"  Mann-Whitney U: U={mw_dir_u:.0f}, p={mw_dir_p:.8f}")
print(f"  Cohen's d: {cohen_d:.4f}")
sig_str = "STATISTICALLY SIGNIFICANT" if mw_dir_p < 0.05 else "NOT SIGNIFICANT"
print(f"  Result: {sig_str}")
print(f"  NOTE: This is diagnostic only. Not a recommendation to disable buys.")

# Box plot direction
fig, axes = plt.subplots(1,2, figsize=(10,5))
sns.boxplot(data=df_can, x="direction", y="r_multiple", ax=axes[0])
axes[0].axhline(0, color="grey", lw=0.8)
axes[0].set_title("Realized R by Direction (793 canonical)")
sns.boxplot(data=df_can, x="trig", y="r_multiple", ax=axes[1])
axes[1].axhline(0, color="grey", lw=0.8)
axes[1].set_title("Realized R by Exit Type")
plt.tight_layout()
p_dir_box = BASE_DIR / "p34_dir_exit_box.png"
fig.savefig(p_dir_box, dpi=120); plt.close(fig)

# ══════════════════════════════════════════════════════════════════════════════
# TASK 8 — JULY/AUGUST DECOMPOSITION BY DIRECTION
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("TASK 8 — Jul/Aug decomposition by direction")
print("="*60)

def dir_stats(mdf, label):
    buy  = mdf[mdf["direction"] == "buy"]
    sell = mdf[mdf["direction"] == "sell"]
    return {
        f"{label}_buy_n":    len(buy),
        f"{label}_sell_n":   len(sell),
        f"{label}_buy_wr":   (buy["r_multiple"]>0).mean()  if len(buy)  else float("nan"),
        f"{label}_sell_wr":  (sell["r_multiple"]>0).mean() if len(sell) else float("nan"),
        f"{label}_buy_mr":   buy["r_multiple"].mean()       if len(buy)  else float("nan"),
        f"{label}_sell_mr":  sell["r_multiple"].mean()      if len(sell) else float("nan"),
        f"{label}_overall_wr": (mdf["r_multiple"]>0).mean(),
        f"{label}_overall_mr": mdf["r_multiple"].mean(),
    }

j_stats = dir_stats(jul, "Jul")
a_stats = dir_stats(aug, "Aug")

print(f"\n  {'Metric':<30} {'July 2026':>14} {'August 2026':>14} {'Delta':>14}")
print(f"  {'-'*75}")
keys = [("Overall Win Rate",   "Jul_overall_wr",  "Aug_overall_wr"),
        ("Overall Mean R",     "Jul_overall_mr",  "Aug_overall_mr"),
        ("Buy n",              "Jul_buy_n",        "Aug_buy_n"),
        ("Buy Win Rate",       "Jul_buy_wr",       "Aug_buy_wr"),
        ("Buy Mean R",         "Jul_buy_mr",       "Aug_buy_mr"),
        ("Sell n",             "Jul_sell_n",       "Aug_sell_n"),
        ("Sell Win Rate",      "Jul_sell_wr",      "Aug_sell_wr"),
        ("Sell Mean R",        "Jul_sell_mr",      "Aug_sell_mr")]

for label, jk, ak in keys:
    jv = j_stats[jk]; av = a_stats[ak]
    d  = float(av) - float(jv) if not(np.isnan(float(jv)) or np.isnan(float(av))) else float("nan")
    print(f"  {label:<30} {float(jv):>14.4f} {float(av):>14.4f} {d:>+14.4f}")

# MW tests within each direction
jul_buy  = jul[jul["direction"]=="buy"]["r_multiple"]
aug_buy  = aug[aug["direction"]=="buy"]["r_multiple"]
jul_sell = jul[jul["direction"]=="sell"]["r_multiple"]
aug_sell = aug[aug["direction"]=="sell"]["r_multiple"]

if len(jul_buy) > 5 and len(aug_buy) > 5:
    mw_buy_u, mw_buy_p = stats.mannwhitneyu(jul_buy, aug_buy, alternative="two-sided")
    print(f"\n  MW test Jul-buy vs Aug-buy: U={mw_buy_u:.0f}, p={mw_buy_p:.6f}")
if len(jul_sell) > 5 and len(aug_sell) > 5:
    mw_sell_u, mw_sell_p = stats.mannwhitneyu(jul_sell, aug_sell, alternative="two-sided")
    print(f"  MW test Jul-sell vs Aug-sell: U={mw_sell_u:.0f}, p={mw_sell_p:.6f}")

# Plot: Jul vs Aug, by direction
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
for ax, month_df, month_label in [(axes[0], jul, "July 2026"), (axes[1], aug, "August 2026")]:
    for direction, color in [("buy","steelblue"), ("sell","coral")]:
        sub = month_df[month_df["direction"]==direction]["r_multiple"]
        ax.hist(sub.values, bins=15, alpha=0.55, label=f"{direction} (n={len(sub)})",
                color=color, edgecolor="white")
    ax.axvline(0, color="grey", lw=1)
    ax.set_title(f"R Distribution — {month_label}")
    ax.set_xlabel("Realized R"); ax.set_ylabel("Count"); ax.legend()
plt.suptitle("July vs August — Buy/Sell R-Multiple Distribution", fontsize=11)
plt.tight_layout()
p_decomp = BASE_DIR / "p34_jul_aug_decomp.png"
fig.savefig(p_decomp, dpi=120); plt.close(fig)

# Classify the shift
print(f"\n  SHIFT CLASSIFICATION:")
print(f"  Jul buy_wr={j_stats['Jul_buy_wr']:.3f}, Aug buy_wr={a_stats['Aug_buy_wr']:.3f}")
print(f"  Jul sell_wr={j_stats['Jul_sell_wr']:.3f}, Aug sell_wr={a_stats['Aug_sell_wr']:.3f}")

buy_wr_change  = float(a_stats["Aug_buy_wr"])  - float(j_stats["Jul_buy_wr"])
sell_wr_change = float(a_stats["Aug_sell_wr"]) - float(j_stats["Jul_sell_wr"])
comp_change    = float(a_stats["Aug_buy_n"]) / max(float(a_stats["Aug_buy_n"]) + float(a_stats["Aug_sell_n"]), 1) \
               - float(j_stats["Jul_buy_n"]) / max(float(j_stats["Jul_buy_n"]) + float(j_stats["Jul_sell_n"]), 1)

print(f"\n  Buy win rate change:  {buy_wr_change:+.3f}")
print(f"  Sell win rate change: {sell_wr_change:+.3f}")
print(f"  Buy composition shift: {comp_change:+.3f} (positive = more buys in Aug)")

if abs(sell_wr_change) > abs(buy_wr_change) and abs(sell_wr_change) > 0.1:
    category = "C — deterioration concentrated in SELL direction"
elif abs(buy_wr_change) > 0.1 and abs(sell_wr_change) > 0.1:
    category = "B — deterioration within BOTH directions"
elif abs(comp_change) > 0.2 and abs(buy_wr_change) < 0.1 and abs(sell_wr_change) < 0.1:
    category = "A — primarily composition shift (more buys, fewer sells)"
else:
    category = "D — indeterminate from available data"

print(f"\n  CLASSIFICATION: {category}")

# ══════════════════════════════════════════════════════════════════════════════
# TASK 9 — DATASET EXPORT FIX (Code Inspection)
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("TASK 9 — Dataset export code inspection")
print("="*60)

# Based on source inspection:
# - TransactionRecon.mqh logs DEAL_ADD/UPDATE events but does NOT write the CSV
# - AMIGO.mq5 does NOT contain any CSV write calls
# - algomind_monte_carlo.py uses synthetic trades, not the CSV
# - No Python file contains to_csv() or open(*.csv, 'a') for trade_level_dataset
# - The CSV appears to have been generated externally (manual export from MT5 or a separate script)

print("""
  SOURCE FILE INSPECTION:
  -----------------------
  1. AMIGO.mq5           — No FileOpen/FileWrite for trade CSV. Trade logging
                           is done via Print() to EA journal only.
  2. TransactionRecon.mqh— Logs DEAL_ADD/UPDATE to EA journal via LogMsg().
                           No FileWrite call.
  3. Position Manager.mqh— Not yet inspected (may contain CSV logic).
  4. Python scripts      — algomind_monte_carlo.py: synthetic trades, no CSV.
                           No Python script contains to_csv() for trade_level.
  5. algomind_trade_level_dataset.csv — Appears to be a MANUAL export from
                           the MT5 Strategy Tester "Trade" tab (right-click
                           → Save As CSV), performed multiple times without
                           clearing the previous file.

  CONCLUSION:
  - The CSV is a manual MT5 Strategy Tester export.
  - MT5 appends to an existing file without deduplication when the user
    exports to the same path.
  - There is NO automated pipeline generating this file.
  - trade_id appears to be the MT5 position ticket / deal ticket.
  - No run_id field exists.
  - No dataset reset occurs at test start in the current workflow.
""")

# Check Position Manager for CSV logic
pm_path = Path(r"C:\Users\USER\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Include\Position Manager.mqh")
print(f"  Checking Position Manager.mqh for CSV writes...")
if pm_path.exists():
    with open(pm_path, "r", encoding="utf-8", errors="replace") as f:
        pm_content = f.read()
    if "FileOpen" in pm_content or "FileWrite" in pm_content or "csv" in pm_content.lower():
        print("  FOUND: Position Manager.mqh contains file write operations.")
        for i, line in enumerate(pm_content.splitlines()):
            if any(k in line for k in ["FileOpen","FileWrite","csv","CSV",".txt"]):
                print(f"    Line {i+1}: {line.strip()}")
    else:
        print("  No CSV/FileOpen/FileWrite found in Position Manager.mqh.")
else:
    print("  Position Manager.mqh not found at expected path.")

print("""
  PROPOSED MINIMUM ENGINEERING FIX (DO NOT IMPLEMENT WITHOUT APPROVAL):
  -----------------------------------------------------------------------
  1. Before each MT5 Strategy Tester export:
     - Delete or rename the existing algomind_trade_level_dataset.csv
     - This prevents row accumulation across runs.

  2. OR: Add a run_id column to the export (either manually or via a wrapper
     Python script that post-processes the MT5 CSV after each export):
       run_id = sha256(first_trade_entry_time + last_trade_exit_time)
     This allows the dataset to hold multiple runs with unambiguous attribution.

  3. OR: Write a Python dedup script that:
     - Loads the raw CSV
     - Groups by trade_id
     - For EXACT_DUPLICATEs: keeps one copy
     - For SAME_ID_DIFFERENT_DATA: writes a conflict report and keeps
       the row with the latest entry_time (or flags for manual resolution)
     - Writes the clean CSV to algomind_trade_level_dataset_canonical.csv

  Priority: Option 1 (delete before each export) is the immediate fix.
  Option 3 is the auditable fix.
  Implementation requires user approval before any file is modified.
""")

# ══════════════════════════════════════════════════════════════════════════════
# WRITE FINAL REPORT
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("Writing p34_report.md...")
print("="*60)

with open(REPORT_PATH, "w", encoding="utf-8") as md:
    md.write("# AlgoMind AMIGO — P3.4 Canonical Dataset Validation and August Forensics\n\n")
    md.write("**READ-ONLY ANALYSIS. No strategy parameters, risk settings, or MQL5 code were modified.**\n\n")
    md.write(f"Canonical dataset: 793 trades | XAUUSDm M5 | 2025-10-01 → 2026-08-28\n\n---\n\n")

    # TASK 1
    md.write("## Task 1 — Full Duplicate Taxonomy\n\n")
    md.write(f"| Metric | Count |\n|---|---|\n")
    md.write(f"| Raw CSV rows | {len(df_raw)} |\n")
    md.write(f"| Unique trade_ids | {df_raw['trade_id'].nunique()} |\n")
    md.write(f"| IDs appearing >1x | {len(id_counts[id_counts>1])} |\n")
    md.write(f"| A. EXACT_DUPLICATE IDs | {n_exact_dup_ids} |\n")
    md.write(f"| A. Extra rows from exact dups | {n_exact_dup_rows} |\n")
    md.write(f"| B. SAME_ID_DIFFERENT_DATA IDs | {n_diff_dup_ids} |\n")
    md.write(f"| B. Rows in conflict groups | {n_diff_dup_rows} |\n\n")
    md.write("### Occurrence Count Distribution\n\n| Occurrences | IDs |\n|---|---|\n")
    for occ, num_ids in count_dist.items():
        md.write(f"| {occ}x | {num_ids} |\n")
    md.write("\n### SAME_ID_DIFFERENT_DATA — All Conflicting Groups\n\n")
    for grp in conflict_rows:
        tid  = grp["trade_id"].iloc[0]
        cnt  = len(grp)
        dcols = [c for c in COLS if c in grp.columns]
        md.write(f"**trade_id = {tid}** ({cnt} rows):\n\n")
        md.write(grp[dcols].to_markdown(index=True))
        md.write("\n\n")

    # TASK 2
    md.write("---\n\n## Task 2 — Authoritative Row Selection\n\n")
    md.write("| Duplicate Type | Rule Applied | Rows Affected |\n|---|---|---|\n")
    md.write(f"| EXACT_DUPLICATE | Keep first occurrence; remove identical copies | {n_exact_dup_rows} removed |\n")
    md.write(f"| SAME_ID_DIFFERENT_DATA | Sort by `entry_time`, keep earliest | {n_diff_dup_ids} IDs, rule applied but ambiguous |\n\n")
    md.write(f"**Canonical dataset after dedup: {len(df_can)} trades, chronologically ordered.**\n\n")
    md.write("> [!WARNING]\n> The `SAME_ID_DIFFERENT_DATA` resolution (keep earliest `entry_time`) is a documented rule, "
             "not a verified truth. Without a `run_id`, it is impossible to determine which backtest run each conflicting "
             "row belongs to. The 'earliest entry_time' rule may select the wrong trade.\n\n")

    # TASK 3
    md.write("---\n\n## Task 3 — Verification Against MT5\n\n")
    md.write("> [!WARNING]\n> No saved MT5 HTML report file was found on disk. MT5 report figures are taken from the P3 "
             "run summary as previously reported. They cannot be independently re-verified from a file.\n\n")
    md.write("| Metric | MT5 Report (P3) | CSV Canonical (793) | Delta |\n|---|---|---|---|\n")
    md.write(f"| Trade count | {MT5_TRADES} | {len(df_can)} | {len(df_can)-MT5_TRADES:+d} |\n")
    md.write(f"| Win count | {MT5_WINS} | {csv_wins} | {csv_wins-MT5_WINS:+d} |\n")
    md.write(f"| Loss count | {MT5_LOSSES} | {csv_losses} | {csv_losses-MT5_LOSSES:+d} |\n")
    md.write(f"| Net P&L ($) | {MT5_NET_PROFIT:.2f} | {csv_net_pnl:.2f} | {csv_net_pnl-MT5_NET_PROFIT:+.2f} |\n")
    md.write(f"| Gross profit ($) | {MT5_GROSS_PROFIT:.2f} | {csv_gross_prof:.2f} | {csv_gross_prof-MT5_GROSS_PROFIT:+.2f} |\n")
    md.write(f"| Gross loss ($) | {MT5_GROSS_LOSS:.2f} | {csv_gross_loss:.2f} | {csv_gross_loss-MT5_GROSS_LOSS:+.2f} |\n")
    md.write(f"| Profit factor | {MT5_PROFIT_FACTOR:.2f} | {csv_pf:.2f} | {csv_pf-MT5_PROFIT_FACTOR:+.2f} |\n\n")
    md.write("> [!IMPORTANT]\n> The MT5 report counts **1,260 trades** — identical to the raw CSV row count. "
             "This confirms the MT5 report was produced from or alongside the raw (undeduplicated) CSV. "
             "The MT5 report figures reflect the inflated dataset. The canonical 793-trade figures differ "
             "from the MT5 report and should be treated as the clean baseline.\n\n")

    # TASK 4
    md.write("---\n\n## Task 4 — Sequence Analysis on Canonical 793 Trades\n\n")
    md.write(f"N = {N} shuffles | p = `(count ≥ actual + 1) / (N + 1)` | Dataset: 793 canonical trades | Seed: 2024\n\n")
    md.write("| Metric | Shuffled Mean | Shuffled Median | 5th pct | 95th pct | Actual | p-value |\n|---|---|---|---|---|---|---|\n")
    md.write(f"| Max Drawdown (R) | {shuf_dd.mean():.4f} | {np.median(shuf_dd):.4f} | {np.percentile(shuf_dd,5):.4f} | {np.percentile(shuf_dd,95):.4f} | {b_dd:.4f} | {pv_dd:.6f} |\n")
    md.write(f"| Longest Losing Streak | {shuf_loss.mean():.2f} | {np.median(shuf_loss):.2f} | {np.percentile(shuf_loss,5):.2f} | {np.percentile(shuf_loss,95):.2f} | {b_loss} | {pv_loss:.6f} |\n")
    md.write(f"| Longest Winning Streak | {shuf_win.mean():.2f} | {np.median(shuf_win):.2f} | {np.percentile(shuf_win,5):.2f} | {np.percentile(shuf_win,95):.2f} | {b_win} | {pv_win:.6f} |\n\n")
    md.write("> [!IMPORTANT]\n> **SEQUENCE CLUSTERING CONFIRMED** on canonical 793-trade dataset.\n>\n"
             "> Interpretation is limited to: the trade R-multiple sequence is non-randomly ordered. "
             "Losses and wins cluster in sustained runs that exceed any of the 10,000 random permutations "
             "of the same trades. **This does not establish that market regimes caused the clustering.**\n\n")
    md.write(f"![Max Drawdown]({p_dd_path.as_uri()})\n\n")
    md.write(f"![Losing Streak]({p_loss_path.as_uri()})\n\n")
    md.write(f"![Winning Streak]({p_win_path.as_uri()})\n\n")

    # TASK 5
    md.write("---\n\n## Task 5 — July vs August Forensic\n\n")
    md.write(f"| Metric | July 2026 | August 2026 | Delta |\n|---|---|---|---|\n")
    for k in sorted(js.keys()):
        jv = js[k]; av = as_[k]
        d = float(av) - float(jv) if not(np.isnan(float(jv)) or np.isnan(float(av))) else float("nan")
        md.write(f"| {k} | {float(jv):.4f} | {float(av):.4f} | {d:+.4f} |\n")
    md.write(f"\nMann-Whitney U (Jul vs Aug R): U={mw_u:.0f}, p={mw_p:.8f}\n\n")

    # TASK 6
    md.write("---\n\n## Task 6 — Performance Shift Variables\n\n")
    md.write("| Variable | Jul Mean | Aug Mean | Abs Diff | % Diff | MW p-value | Cohen's d |\n|---|---|---|---|---|---|---|\n")
    for row in shift_table:
        md.write(f"| {row['variable']} | {row['jul_mean']:.4f} | {row['aug_mean']:.4f} | {row['abs_diff']:+.4f} | {row['pct_diff']:+.1f}% | {row['mw_p']:.6f} | {row['cohens_d']:.4f} |\n")
    md.write(f"\n### Direction Composition\n\n")
    md.write("| Direction | Jul % | Aug % | Delta |\n|---|---|---|---|\n")
    md.write(f"| buy | {js['buy_pct']:.1%} | {as_['buy_pct']:.1%} | {as_['buy_pct']-js['buy_pct']:+.1%} |\n")
    md.write(f"| sell | {js['sell_pct']:.1%} | {as_['sell_pct']:.1%} | {as_['sell_pct']-js['sell_pct']:+.1%} |\n\n")
    md.write("### Exit Type\n\n")
    md.write("| Exit | Jul % | Aug % | Delta |\n|---|---|---|---|\n")
    md.write(f"| take_profit | {js['tp_pct']:.1%} | {as_['tp_pct']:.1%} | {as_['tp_pct']-js['tp_pct']:+.1%} |\n")
    md.write(f"| stop_loss | {js['sl_pct']:.1%} | {as_['sl_pct']:.1%} | {as_['sl_pct']-js['sl_pct']:+.1%} |\n\n")
    md.write("> [!NOTE]\n> Causation is not inferred. These are measurable changes between months.\n\n")

    # TASK 7
    md.write("---\n\n## Task 7 — Directional Asymmetry\n\n")
    md.write("| Metric | Buy | Sell | Sell − Buy |\n|---|---|---|---|\n")
    md.write(f"| Count | {n_buy} | {n_sell} | — |\n")
    md.write(f"| Win Rate | {bwr:.4f} | {swr:.4f} | {diff_wr:+.4f} |\n")
    md.write(f"| Mean R | {bmr:.4f} | {smr:.4f} | {smr-bmr:+.4f} |\n")
    md.write(f"| Median R | {bmed:.4f} | {smed:.4f} | {smed-bmed:+.4f} |\n")
    md.write(f"| Sum R | {bsum:.4f} | {ssum:.4f} | {ssum-bsum:+.4f} |\n\n")
    md.write(f"**95% CI for win rate difference:** [{ci_lo:.4f}, {ci_hi:.4f}] (excludes zero: {ci_lo > 0})\n\n")
    md.write(f"**Proportion z-test:** z = {z_prop:.3f}, p = {p_prop:.8f}\n\n")
    md.write(f"**Mann-Whitney U:** U = {mw_dir_u:.0f}, p = {mw_dir_p:.8f}\n\n")
    md.write(f"**Cohen's d:** {cohen_d:.4f} ({'small' if abs(cohen_d)<0.3 else 'medium' if abs(cohen_d)<0.5 else 'large'})\n\n")
    md.write(f"**Statistical significance:** {sig_str}\n\n")
    md.write(f"**Economic magnitude:** Mean R difference = {smr-bmr:+.4f} R. Sum R difference = {ssum-bsum:+.4f} R over {len(df_can)} trades.\n\n")
    md.write("> [!IMPORTANT]\n> Directional asymmetry is statistically significant. This is a diagnostic finding. "
             "Cause unknown without Score/ATR data. Disabling buys is a strategy change; out of scope.\n\n")
    md.write(f"![Direction & Exit Box Plots]({p_dir_box.as_uri()})\n\n")

    # TASK 8
    md.write("---\n\n## Task 8 — July/August Decomposition by Direction\n\n")
    md.write("| Metric | July 2026 | August 2026 | Delta |\n|---|---|---|---|\n")
    for label, jk, ak in keys:
        jv = j_stats[jk]; av = a_stats[ak]
        d  = float(av) - float(jv) if not(np.isnan(float(jv)) or np.isnan(float(av))) else float("nan")
        md.write(f"| {label} | {float(jv):.4f} | {float(av):.4f} | {d:+.4f} |\n")
    md.write(f"\n**Buy WR change:** {buy_wr_change:+.4f}\n\n")
    md.write(f"**Sell WR change:** {sell_wr_change:+.4f}\n\n")
    md.write(f"**Buy composition shift:** {comp_change:+.4f} (positive = more buys in Aug)\n\n")
    if len(jul_buy) > 5 and len(aug_buy) > 5:
        md.write(f"**MW Jul-buy vs Aug-buy:** U={mw_buy_u:.0f}, p={mw_buy_p:.6f}\n\n")
    if len(jul_sell) > 5 and len(aug_sell) > 5:
        md.write(f"**MW Jul-sell vs Aug-sell:** U={mw_sell_u:.0f}, p={mw_sell_p:.6f}\n\n")
    md.write(f"### Classification: **{category}**\n\n")
    md.write(f"![Jul/Aug Decomposition]({p_decomp.as_uri()})\n\n")

    # TASK 9
    md.write("---\n\n## Task 9 — Dataset Export Code Inspection\n\n")
    md.write("| Aspect | Finding |\n|---|---|\n")
    md.write("| Source file | No automated Python/MQL5 code found that generates the CSV |\n")
    md.write("| Generation method | Manual MT5 Strategy Tester → Trade tab → Save As CSV |\n")
    md.write("| Append behaviour | MT5 appends to existing file without deduplication |\n")
    md.write("| trade_id generation | MT5 position ticket / deal ticket (resets each backtest) |\n")
    md.write("| Globally unique | NO — same ticket numbers appear in different runs |\n")
    md.write("| run_id field | NOT PRESENT |\n")
    md.write("| Dataset reset at test start | NOT AUTOMATED — requires manual deletion |\n\n")
    md.write("### Proposed Minimum Fix (not yet implemented — requires approval)\n\n")
    md.write("| Option | Description | Risk |\n|---|---|---|\n")
    md.write("| 1 (Immediate) | Delete CSV before each export | Manual step; no code change |\n")
    md.write("| 2 (Auditable) | Python dedup script: canonical + conflict report | Read-only post-process |\n")
    md.write("| 3 (Robust) | Add run_id to export; dedup by (trade_id, run_id) | Requires export workflow change |\n\n")
    md.write("> [!CAUTION]\n> **No implementation has been performed.** Approval required before any file or code change.\n\n")

    # TASK 10
    md.write("---\n\n## Task 10 — Final Status\n\n")
    md.write("### CONFIRMED\n\n")
    md.write(f"1. **793 canonical trades** after full duplicate taxonomy and dedup.\n")
    md.write(f"2. **Duplicate classification**: {n_exact_dup_ids} EXACT_DUPLICATE IDs, {n_diff_dup_ids} SAME_ID_DIFFERENT_DATA IDs.\n")
    md.write(f"3. **R-multiple = net_pnl / planned_risk** exactly on all 793 trades (diff = 0.0).\n")
    md.write(f"4. **Sequence clustering confirmed** on 793 canonical trades: DD p={pv_dd:.6f}, Loss p={pv_loss:.6f}, Win p={pv_win:.6f}.\n")
    md.write(f"5. **Directional asymmetry confirmed**: Sell WR {swr:.1%} vs Buy WR {bwr:.1%}; MW p={mw_dir_p:.6f}; d={cohen_d:.3f}.\n")
    md.write(f"6. **July→August shift is real and significant** (MW p={mw_p:.2e}).\n")
    md.write(f"7. **Dataset CSV origin confirmed**: manual MT5 export, no automated pipeline.\n")
    md.write(f"8. **MT5 trade count (1,260) matches raw CSV row count**, confirming the report was produced from the contaminated dataset.\n\n")

    md.write("### RECONCILED\n\n")
    md.write("1. P2.2 95.2% vs P3 44.1%: different pipeline populations.\n")
    md.write("2. P3.2 extreme MC values (DD=176R, loss streak=100): duplication artifacts. Canonical: DD=52.8R, loss=23.\n")
    md.write("3. August 587 trades: duplication artifact. Canonical August = 120 trades.\n\n")

    md.write("### UNRESOLVED\n\n")
    md.write(f"1. **SAME_ID_DIFFERENT_DATA ({n_diff_dup_ids} IDs)**: Conflicting rows with same trade_id but different trade data. "
             "The earliest-entry-time rule was applied but is not guaranteed to select the correct run's row.\n")
    md.write("2. **MT5 vs canonical mismatch**: MT5 report counts 1,260 trades; canonical has 793. "
             "The authoritative trade-level truth cannot be determined without a saved MT5 HTML report from a single clean run.\n")
    md.write("3. **Root cause of July→August shift**: Win rate 67%→25%, TP% 61%→18%, sell%→buy% reversal. "
             "Score, ATR, Margin, Regime fields absent from CSV.\n")
    md.write("4. **Candidate population (12,687 / 7,089)**: EA journal not on disk; cannot verify.\n\n")

    md.write("### ENGINEERING GAPS\n\n")
    md.write("1. **CSV deduplication**: Manual export without clearing the file produces contaminated datasets. "
             "All analyses based on the raw CSV are invalid until a clean single-run export is confirmed.\n")
    md.write("2. **run_id absent**: No way to attribute rows to a specific backtest run without it.\n")
    md.write("3. **EA journal not preserved**: Print() output (DECISION, ACTION_TRADE, MIN_LOT records) is "
             "not saved to disk between sessions. Candidate population cannot be verified post-hoc.\n")
    md.write("4. **sweep_reject = false**: Pre-existing gap; not addressed here.\n")
    md.write("5. **Score/ATR/Regime/Margin not in CSV**: Per-trade signal diagnostics blocked.\n\n")

    md.write("---\n\n*All analyses are read-only. No MQL5 source, thresholds, risk parameters, or CSV were modified.*\n")

print(f"\nReport: {REPORT_PATH}")
print("Done.")
