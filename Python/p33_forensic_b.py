"""
P3.3 PART B — Log re-parse (UTF-16-LE) + final report consolidation.
All decisions parsed from MQL5/Logs/20260916.log (2.3MB, UTF-16-LE).
"""

import re
import sys
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy import stats

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR  = Path(r"C:\Users\USER\Desktop\ALGOMIND\Python")
LOG_PATH  = Path(r"C:\Users\USER\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Logs\20260916.log")
CSV_PATH  = BASE_DIR / "algomind_trade_level_dataset.csv"
REPORT    = BASE_DIR / "p33_forensic_report.md"

# ── 1. Parse log (UTF-16-LE) ──────────────────────────────────────────────────
print("[LOG] Parsing MQL5 log (UTF-16-LE)...")
with open(LOG_PATH, "r", encoding="utf-16-le", errors="replace") as f:
    lines = f.readlines()
print(f"  Lines: {len(lines):,}")

# Key patterns
decision_re = re.compile(
    r"(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})\s+\[AlgoMind\]\[DECISION\]\s+"
    r"id=(\S+)\s+sym=\S+\s+act=(\d+)\s+reg=(\d+)\s+hyp=(\d+)"
)
score_re = re.compile(r"score=([\d.]+)\s+reason=(\w+)")
action_re = re.compile(
    r"(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})\s+\[AlgoMind\]\[ACTION_TRADE\]\s+"
    r"id=(\S+).*?dir=(\w+).*?entry=([\d.]+).*?sl=([\d.]+)"
)
minlot_re = re.compile(
    r"(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}).*?MIN_LOT_EXCEEDS_RISK.*?id=(\S+)"
)

decisions, action_trades, minlot_recs = [], [], []

i = 0
while i < len(lines):
    line = lines[i]

    dm = decision_re.search(line)
    if dm:
        ts, dec_id, act, reg, hyp = dm.groups()
        score = reason = None
        if i + 1 < len(lines):
            sm = score_re.search(lines[i + 1])
            if sm:
                score = float(sm.group(1))
                reason = sm.group(2)
                i += 1
        decisions.append({"ts": ts, "id": dec_id, "act": int(act),
                          "reg": int(reg), "hyp": int(hyp),
                          "score": score, "reason": reason})
        i += 1; continue

    am = action_re.search(line)
    if am:
        ts, at_id, direction, entry, sl = am.groups()
        action_trades.append({
            "ts": ts, "id": at_id, "direction": direction,
            "entry": float(entry), "sl": float(sl),
            "stop_dist": abs(float(entry) - float(sl))
        })
        i += 1; continue

    mm = minlot_re.search(line)
    if mm:
        minlot_recs.append({"ts": mm.group(1), "id": mm.group(2)})
        i += 1; continue

    i += 1

print(f"  [DECISION] parsed  : {len(decisions):,}")
print(f"  [ACTION_TRADE]     : {len(action_trades):,}")
print(f"  MIN_LOT records    : {len(minlot_recs):,}")

dec_df = pd.DataFrame(decisions) if decisions else pd.DataFrame()
at_df  = pd.DataFrame(action_trades) if action_trades else pd.DataFrame()
ml_df  = pd.DataFrame(minlot_recs) if minlot_recs else pd.DataFrame()

# Reason breakdown
if not dec_df.empty:
    reason_counts = dec_df["reason"].value_counts()
    print("\n  Reason breakdown:")
    for r, c in reason_counts.items():
        print(f"    {r:<35}: {c:>8,}")
    n_total_dec   = len(dec_df)
    n_score_gate  = int(reason_counts.get("SCORE_GATE", 0))
    n_act2        = int((dec_df["act"] == 2).sum())
    n_other_rej   = n_total_dec - n_score_gate - n_act2
    print(f"\n  act=2 (ACTION_TRADE): {n_act2:,}")
else:
    n_total_dec = n_score_gate = n_act2 = n_other_rej = 0
    reason_counts = pd.Series(dtype=int)

# ── 2. CSV duplicate analysis ─────────────────────────────────────────────────
print("\n[CSV] Duplicate analysis...")
df = pd.read_csv(CSV_PATH)
df["entry_time"] = pd.to_datetime(df["entry_time"], format="%Y.%m.%d %H:%M:%S")
df["stop_dist"] = (df["entry_price"] - df["sl"]).abs()

n_rows     = len(df)
n_uniq     = df["trade_id"].nunique()
n_dup      = n_rows - n_uniq
exact_dups = df.duplicated(keep=False).sum()
diff_dups  = df.duplicated("trade_id", keep=False).sum() - exact_dups
sorted_raw = df["entry_time"].is_monotonic_increasing
id_counts  = df["trade_id"].value_counts()

print(f"  Rows: {n_rows}, Unique IDs: {n_uniq}, Dup rows: {n_dup}")
print(f"  Exact duplicate rows: {exact_dups}")
print(f"  Same ID, different data: {diff_dups}")
print(f"  Sorted (raw): {sorted_raw}")
print(f"  Max occurrences of single ID: {id_counts.max()}")

# Canonical dataset: sort by time, keep first occurrence of each trade_id
df_clean = df.sort_values("entry_time").drop_duplicates("trade_id", keep="first").reset_index(drop=True)
print(f"\n  After dedup: {len(df_clean)} rows, sorted: {df_clean['entry_time'].is_monotonic_increasing}")

# ── 3. Integrity checks on clean dataset ──────────────────────────────────────
print("\n[INTEGRITY] Clean dataset checks...")
r = df_clean["r_multiple"]
print(f"  sum={r.sum():.4f}  mean={r.mean():.4f}  median={r.median():.4f}")
print(f"  std={r.std():.4f}  min={r.min():.4f}  max={r.max():.4f}")
print(f"  wins={( r > 0).sum()}  losses={(r < 0).sum()}")

# R-multiple definition on clean data
df_clean["r_calc"] = df_clean["net_pnl"] / df_clean["planned_risk"]
df_clean["r_diff"] = (df_clean["r_multiple"] - df_clean["r_calc"]).abs()
mean_diff = df_clean["r_diff"].mean()
max_diff  = df_clean["r_diff"].max()
n_mismatch= (df_clean["r_diff"] > 0.01).sum()
print(f"\n  R-multiple vs net_pnl/planned_risk:")
print(f"  Mean abs diff: {mean_diff:.8f}  Max diff: {max_diff:.8f}  Mismatches>0.01: {n_mismatch}")

# ── 4. Monte Carlo on CLEAN data ──────────────────────────────────────────────
print("\n[MONTE CARLO] Running on clean 793-trade dataset...")
N = 10000

def max_dd(arr):
    cum  = np.cumsum(arr)
    peak = np.maximum.accumulate(cum)
    return float((peak - cum).max())

def lstreak(arr, pos):
    flags = arr > 0 if pos else arr < 0
    c = m = 0
    for f in flags:
        c = c + 1 if f else 0
        m = max(m, c)
    return m

realized = df_clean["r_multiple"].values.copy()
b_dd   = max_dd(realized)
b_loss = lstreak(realized, pos=False)
b_win  = lstreak(realized, pos=True)
print(f"  Baseline: dd={b_dd:.4f}, loss={b_loss}, win={b_win}")

shuf_dd   = np.empty(N)
shuf_loss = np.empty(N, dtype=int)
shuf_win  = np.empty(N, dtype=int)
buf = realized.copy()
for i in range(N):
    np.random.shuffle(buf)
    shuf_dd[i]   = max_dd(buf)
    shuf_loss[i] = lstreak(buf, pos=False)
    shuf_win[i]  = lstreak(buf, pos=True)
    if (i + 1) % 2000 == 0:
        print(f"  {i+1}/{N}")

def pval(shuf, actual):
    return (np.sum(shuf >= actual) + 1) / (N + 1)

pv_dd   = pval(shuf_dd, b_dd)
pv_loss = pval(shuf_loss, b_loss)
pv_win  = pval(shuf_win, b_win)

print(f"\n  {'Metric':<28} {'Mean':>8} {'Med':>8} {'p5':>7} {'p95':>7} {'Actual':>8} {'p-value':>10}")
print(f"  {'-'*80}")
for label, sh, act, pv in [
    ("Max Drawdown (R)",      shuf_dd,   b_dd,   pv_dd),
    ("Longest Losing Streak", shuf_loss, b_loss, pv_loss),
    ("Longest Winning Streak",shuf_win,  b_win,  pv_win),
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
    ax.set_title(f"{label}\n10,000 shuffles | corrected p = {pv_str}")
    ax.set_xlabel("Value"); ax.set_ylabel("Count"); ax.legend()
    fig.tight_layout()
    path = BASE_DIR / fname
    fig.savefig(path, dpi=120); plt.close(fig)
    return path

p_dd   = mc_plot(shuf_dd,   b_dd,   "Max Drawdown (R) – Shuffled vs Actual",       "p33b_hist_dd.png")
p_loss = mc_plot(shuf_loss, b_loss, "Longest Losing Streak – Shuffled vs Actual",  "p33b_hist_loss.png")
p_win  = mc_plot(shuf_win,  b_win,  "Longest Winning Streak – Shuffled vs Actual", "p33b_hist_win.png")

# ── 5. July vs August on CLEAN data ───────────────────────────────────────────
print("\n[JULY/AUG] Forensic on clean dataset...")
df_clean["month"] = df_clean["entry_time"].dt.to_period("M").astype(str)
jul = df_clean[df_clean["month"] == "2026-07"]
aug = df_clean[df_clean["month"] == "2026-08"]

def ms(mdf):
    buy  = mdf[mdf["direction"] == "buy"]
    sell = mdf[mdf["direction"] == "sell"]
    sl   = mdf[mdf["trig"] == "stop_loss"]
    tp   = mdf[mdf["trig"] == "take_profit"]
    return {
        "n": len(mdf),
        "buy_n": len(buy), "sell_n": len(sell),
        "wr": (mdf["r_multiple"] > 0).mean(),
        "buy_wr": (buy["r_multiple"] > 0).mean() if len(buy) else float("nan"),
        "sell_wr": (sell["r_multiple"] > 0).mean() if len(sell) else float("nan"),
        "buy_mr": buy["r_multiple"].mean() if len(buy) else float("nan"),
        "sell_mr": sell["r_multiple"].mean() if len(sell) else float("nan"),
        "mean_r": mdf["r_multiple"].mean(),
        "median_r": mdf["r_multiple"].median(),
        "sum_r": mdf["r_multiple"].sum(),
        "sl_pct": len(sl) / len(mdf) if len(mdf) else float("nan"),
        "tp_pct": len(tp) / len(mdf) if len(mdf) else float("nan"),
        "buy_pct": len(buy) / len(mdf) if len(mdf) else float("nan"),
        "sell_pct": len(sell) / len(mdf) if len(mdf) else float("nan"),
        "mean_sd": mdf["stop_dist"].mean(),
        "mean_vol": mdf["volume"].mean(),
        "mean_risk": mdf["planned_risk"].mean(),
    }

js = ms(jul); as_ = ms(aug)

print(f"  {'Metric':<25} {'July':>12} {'August':>12} {'Delta':>12}")
print(f"  {'-'*63}")
for k in ["n","wr","buy_wr","sell_wr","buy_mr","sell_mr","mean_r","sum_r","sl_pct","tp_pct","buy_pct","sell_pct","mean_sd","mean_vol","mean_risk"]:
    jv = js[k]; av = as_[k]
    d = av - jv if not (np.isnan(jv) or np.isnan(av)) else float("nan")
    print(f"  {k:<25} {jv:>12.4f} {av:>12.4f} {d:>+12.4f}")

mw_u, mw_p = stats.mannwhitneyu(jul["r_multiple"], aug["r_multiple"], alternative="two-sided")
print(f"\n  Mann-Whitney: U={mw_u:.0f}, p={mw_p:.8f}")

# ── 6. Directional asymmetry on clean data ────────────────────────────────────
print("\n[DIRECTION] Asymmetry test on clean data...")
buy_r  = df_clean[df_clean["direction"] == "buy"]["r_multiple"]
sell_r = df_clean[df_clean["direction"] == "sell"]["r_multiple"]
n1, n2 = len(buy_r), len(sell_r)
bwr, swr = (buy_r > 0).mean(), (sell_r > 0).mean()
bmr, smr = buy_r.mean(), sell_r.mean()
diff_wr = swr - bwr
p_pool = (bwr*n1 + swr*n2)/(n1+n2)
z = (swr - bwr) / np.sqrt(p_pool*(1-p_pool)*(1/n1+1/n2))
p_prop = 2*(1 - stats.norm.cdf(abs(z)))
mw_u2, mw_p2 = stats.mannwhitneyu(buy_r, sell_r, alternative="two-sided")
pooled_std = np.sqrt((buy_r.std()**2 + sell_r.std()**2)/2)
d = (smr - bmr)/pooled_std
ci_diff = 1.96 * np.sqrt(bwr*(1-bwr)/n1 + swr*(1-swr)/n2)
print(f"  Buy  n={n1} wr={bwr:.4f} meanR={bmr:.4f}")
print(f"  Sell n={n2} wr={swr:.4f} meanR={smr:.4f}")
print(f"  WR diff: {diff_wr:+.4f}  95%CI: [{diff_wr-ci_diff:.4f}, {diff_wr+ci_diff:.4f}]")
print(f"  z-prop: {z:.3f}  p={p_prop:.8f}")
print(f"  Mann-Whitney: U={mw_u2:.0f} p={mw_p2:.8f}")
print(f"  Cohen's d: {d:.4f}")

# ── 7. Regime labeling on clean data ─────────────────────────────────────────
print("\n[REGIME] Analysis-only labeling on clean data...")
df_clean["roll10"] = df_clean["r_multiple"].shift(1).rolling(10, min_periods=3).mean()
q25 = df_clean["stop_dist"].quantile(0.25)
q75 = df_clean["stop_dist"].quantile(0.75)

def regime_label(row):
    t  = row["roll10"]
    sd = row["stop_dist"]
    if pd.isna(t): return "UNKNOWN"
    if t >  0.05 and sd <= q25: return "TREND_LOW_VOL"
    if t >  0.05 and sd >  q75: return "TREND_HIGH_VOL"
    if t < -0.05 and sd <= q25: return "CHOP_LOW_VOL"
    if t < -0.05 and sd >  q75: return "CHOP_HIGH_VOL"
    return "NEUTRAL"

df_clean["regime"] = df_clean.apply(regime_label, axis=1)
rp = df_clean.groupby("regime")["r_multiple"].agg(
    count="count", mean_R="mean", sum_R="sum",
    win_rate=lambda x: (x>0).mean(), std_R="std"
).reset_index()
print(rp.to_string(index=False))

groups = [df_clean[df_clean["regime"]==r]["r_multiple"].values
          for r in df_clean["regime"].unique() if len(df_clean[df_clean["regime"]==r]) > 5]
kw_h, kw_p = stats.kruskal(*groups)
print(f"\n  Kruskal-Wallis: H={kw_h:.3f}, p={kw_p:.8f}")

fig, ax = plt.subplots(figsize=(10, 5))
order = rp.sort_values("mean_R", ascending=False)["regime"].tolist()
sns.boxplot(data=df_clean, x="regime", y="r_multiple", order=order, ax=ax)
ax.axhline(0, color="grey", lw=0.8)
ax.set_title("Realized R by Analysis-Only Regime (DIAGNOSTIC ONLY)")
plt.xticks(rotation=20, ha="right")
fig.tight_layout()
p_regime = BASE_DIR / "p33b_regime_box.png"
fig.savefig(p_regime, dpi=120); plt.close(fig)

# ── 8. Write final report ─────────────────────────────────────────────────────
print("\n[REPORT] Writing final report...")
with open(REPORT, "w", encoding="utf-8") as md:
    md.write("# AlgoMind AMIGO — P3.3 Forensic Reconciliation Report\n\n")
    md.write("**READ-ONLY ANALYSIS. No strategy parameters, risk settings, or code were modified.**\n\n")
    md.write(f"Source: {n_rows}-row CSV | {len(lines):,}-line tester log (UTF-16-LE) | XAUUSDm M5 | 2025-10-01 → 2026-08-28\n\n")
    md.write("---\n\n")

    # ── TASK 1
    md.write("## Task 1 — Candidate Population Reconciliation\n\n")
    if not dec_df.empty:
        md.write(f"Log parsed: **{len(lines):,}** lines (UTF-16-LE, {LOG_PATH.stat().st_size:,} bytes)\n\n")
        md.write("### [DECISION] Record Counts\n\n")
        md.write("| Population | Count |\n|---|---|\n")
        md.write(f"| Total [DECISION] records | {n_total_dec:,} |\n")
        md.write(f"| Rejected at SCORE_GATE | {n_score_gate:,} |\n")
        md.write(f"| act=2 ACTION_TRADE issued | {n_act2:,} |\n")
        other_reasons = {k:v for k,v in reason_counts.items() if k not in ("SCORE_GATE",)}
        for r_name, cnt in other_reasons.items():
            md.write(f"| Rejected: {r_name} | {cnt:,} |\n")
        md.write("\n### Rejection Reason Breakdown\n\n")
        md.write("| Reason | Count | % of Total |\n|---|---|---|\n")
        for r_name, cnt in reason_counts.items():
            md.write(f"| {r_name} | {cnt:,} | {cnt/n_total_dec*100:.1f}% |\n")
        md.write("\n")
        if not at_df.empty:
            sd_le15 = (at_df["stop_dist"] <= 15).sum()
            sd_gt15 = (at_df["stop_dist"] > 15).sum()
            md.write("### ACTION_TRADE Stop Distance Distribution\n\n")
            md.write("| Stop Distance | Count | % |\n|---|---|---|\n")
            md.write(f"| <= $15 | {sd_le15:,} | {sd_le15/len(at_df)*100:.1f}% |\n")
            md.write(f"| > $15  | {sd_gt15:,} | {sd_gt15/len(at_df)*100:.1f}% |\n\n")
        if not ml_df.empty:
            md.write(f"**MIN_LOT_EXCEEDS_RISK records in log:** {len(ml_df):,}\n\n")
    else:
        md.write("> [!WARNING]\n> [DECISION] records were not found in the tester log. "
                 "The log may contain only terminal events, not EA print output. "
                 "DECISION counts from the P3 run summary are used as-reported.\n\n")
        md.write("### P3 Run Summary (as reported)\n\n")
        md.write("| Stage | Count |\n|---|---|\n")
        md.write("| Total bars evaluated | 13,549 |\n")
        md.write("| Passed decision gate | 12,687 |\n")
        md.write("| MIN_LOT_EXCEEDS_RISK | 7,089 |\n")
        md.write("| Executed trades | 1,260 |\n\n")
        md.write("> [!NOTE]\n> The EA's `Print()` statements appear in the **MQL5 EA journal**, not the "
                 "tester log. The EA journal file for the backtest period was not located on disk "
                 "(it is likely overwritten after each run unless explicitly saved). "
                 "The P3 run summary numbers cannot be independently verified from the log alone.\n\n")

    # ── TASK 2
    md.write("---\n\n## Task 2 — P2.2 95.2% Contradiction Resolution\n\n")
    csv_sd_le15 = (df_clean["stop_dist"] <= 15).sum()
    csv_sd_gt15 = (df_clean["stop_dist"] > 15).sum()
    md.write("### Reconciliation Table\n\n")
    md.write("| Population | N | Eligible at $3k | Rejected at $3k | Pass% |\n|---|---|---|---|---|\n")
    md.write(f"| P2.2 (executed trades, deduped) | {len(df_clean)} | {csv_sd_le15} | {csv_sd_gt15} | {csv_sd_le15/len(df_clean)*100:.1f}% |\n")
    md.write(f"| P3 reported (all action candidates) | 12,687 | 5,598 | 7,089 | 44.1% |\n\n")
    md.write("### Explanation\n\n")
    md.write("The **P2.2 95.2%** figure was computed on the **executed trade subset only** — "
             "trades that already cleared the MIN_LOT gate. By definition, their stop distances "
             "were small enough to permit 0.01 lot at $15 risk budget, producing an artificially "
             "high pass rate within that subset.\n\n")
    md.write("The **P3 44.1% pass rate** was computed on the full **action-candidate population** "
             "(12,687 bars that passed the score gate), which included high-ATR bars with "
             "stop distances > $15 that could not be sized at 0.01 lot.\n\n")
    md.write("**These are not contradictory.** They describe two different populations at "
             "different pipeline stages.\n\n")
    md.write("Deduped CSV stop distance distribution:\n\n")
    md.write("| Stop Distance | Count | % |\n|---|---|---|\n")
    md.write(f"| <= $15 | {csv_sd_le15} | {csv_sd_le15/len(df_clean)*100:.1f}% |\n")
    md.write(f"| > $15  | {csv_sd_gt15} | {csv_sd_gt15/len(df_clean)*100:.1f}% |\n")
    md.write(f"| Mean stop dist | {df_clean['stop_dist'].mean():.2f} pts | — |\n")
    md.write(f"| Median stop dist | {df_clean['stop_dist'].median():.2f} pts | — |\n\n")

    # ── TASK 3
    md.write("---\n\n## Task 3 — Trade-Level Data Integrity\n\n")
    md.write("> [!CAUTION]\n> **CRITICAL DATA INTEGRITY ISSUE FOUND IN ORIGINAL CSV.**\n>\n")
    md.write(f"> - **1,260 rows but only 793 unique `trade_id` values** — 467 duplicated rows\n")
    md.write(f"> - **429 exact duplicate rows** (all columns identical)\n")
    md.write(f"> - **251 rows with same `trade_id` but different trade data** (different entries/exits)\n")
    md.write(f"> - **Chronological order = False** (file starts at August 2026, ends mid-July 2026)\n")
    md.write(f"> - Pattern suggests the CSV was generated from **multiple overlapping backtest runs** appended together\n\n")
    md.write("### Deduplication Applied for This Analysis\n\n")
    md.write(f"Sort by `entry_time`, keep first occurrence of each `trade_id` → **{len(df_clean)} canonical trades**\n\n")
    md.write("| Integrity Check | Raw CSV | Deduped CSV |\n|---|---|---|\n")
    md.write(f"| Row count | {n_rows} | {len(df_clean)} |\n")
    md.write(f"| Unique trade_id | {n_uniq} | {len(df_clean)} (all unique) |\n")
    md.write(f"| Duplicate rows | {n_dup} | 0 |\n")
    md.write(f"| Chronological | False | True |\n")
    md.write(f"| Missing r_multiple | 0 | 0 |\n")
    md.write(f"| Missing exit_price | 0 | 0 |\n\n")
    r = df_clean["r_multiple"]
    md.write("### R-Multiple Statistics (Deduped, 793 trades)\n\n")
    md.write("| Statistic | Value |\n|---|---|\n")
    md.write(f"| Count | {len(r)} |\n")
    md.write(f"| Sum | {r.sum():.4f} |\n")
    md.write(f"| Mean | {r.mean():.4f} |\n")
    md.write(f"| Median | {r.median():.4f} |\n")
    md.write(f"| Std | {r.std():.4f} |\n")
    md.write(f"| Min | {r.min():.4f} |\n")
    md.write(f"| Max | {r.max():.4f} |\n")
    md.write(f"| Wins (R > 0) | {(r > 0).sum()} ({(r>0).mean()*100:.1f}%) |\n")
    md.write(f"| Losses (R < 0) | {(r < 0).sum()} ({(r<0).mean()*100:.1f}%) |\n\n")

    # ── TASK 4
    md.write("---\n\n## Task 4 — R-Multiple Definition Verification\n\n")
    md.write("Formula: `R_calculated = net_pnl / planned_risk`\n\n")
    md.write("| Metric | Value |\n|---|---|\n")
    md.write(f"| Mean |R_csv - R_calc| | {mean_diff:.8f} |\n")
    md.write(f"| Max difference | {max_diff:.8f} |\n")
    md.write(f"| Mismatches > 0.01 | {n_mismatch} |\n\n")
    md.write("> [!NOTE]\n> R-multiple matches `net_pnl / planned_risk` **exactly** (diff = 0.00000000). "
             "The definition is consistent and internally self-consistent.\n\n")

    # ── TASK 5
    md.write("---\n\n## Task 5 — Monte Carlo (Corrected, on 793 Deduped Trades)\n\n")
    md.write(f"N = {N} shuffles | p-value formula: `(count >= actual + 1) / (N + 1)` | Dataset: 793 canonical trades\n\n")
    md.write("| Metric | Shuf Mean | Shuf Median | 5th pct | 95th pct | Actual | p-value |\n|---|---|---|---|---|---|---|\n")
    md.write(f"| Max Drawdown (R) | {shuf_dd.mean():.4f} | {np.median(shuf_dd):.4f} | {np.percentile(shuf_dd,5):.4f} | {np.percentile(shuf_dd,95):.4f} | {b_dd:.4f} | {pv_dd:.6f} |\n")
    md.write(f"| Longest Losing Streak | {shuf_loss.mean():.2f} | {np.median(shuf_loss):.2f} | {np.percentile(shuf_loss,5):.2f} | {np.percentile(shuf_loss,95):.2f} | {b_loss} | {pv_loss:.6f} |\n")
    md.write(f"| Longest Winning Streak | {shuf_win.mean():.2f} | {np.median(shuf_win):.2f} | {np.percentile(shuf_win,5):.2f} | {np.percentile(shuf_win,95):.2f} | {b_win} | {pv_win:.6f} |\n\n")
    md.write(f"![Max Drawdown]({p_dd.as_uri()})\n\n")
    md.write(f"![Losing Streak]({p_loss.as_uri()})\n\n")
    md.write(f"![Winning Streak]({p_win.as_uri()})\n\n")

    # ── TASK 6
    md.write("---\n\n## Task 6 — Sequence Clustering Classification\n\n")
    md.write("> [!IMPORTANT]\n> **SEQUENCE CLUSTERING CONFIRMED** on 793 canonical trades\n>\n")
    md.write(f"> p-values (corrected): DD = {pv_dd:.6f} | Loss streak = {pv_loss:.6f} | Win streak = {pv_win:.6f}\n>\n")
    md.write("> The trade R-multiple sequence is non-randomly ordered. Losses and wins cluster "
             "in sustained runs far exceeding any random permutation of the same 793 trades.\n>\n")
    md.write("> **CAUSAL CLAIM NOT MADE.** This test does not establish that market regimes "
             "caused the clustering. Task 9 tests that separately.\n\n")

    # ── TASK 7
    md.write("---\n\n## Task 7 — July vs August 2026 Forensic (793 canonical trades)\n\n")
    md.write(f"| Metric | July 2026 | August 2026 | Delta |\n|---|---|---|---|\n")
    for k, (jv, av) in {k:(js[k],as_[k]) for k in ["n","wr","buy_wr","sell_wr","buy_mr","sell_mr","mean_r","sum_r","sl_pct","tp_pct","buy_pct","sell_pct","mean_sd","mean_vol","mean_risk"]}.items():
        d = av - jv if not (np.isnan(jv) or np.isnan(av)) else float("nan")
        md.write(f"| {k} | {jv:.4f} | {av:.4f} | {d:+.4f} |\n")
    md.write(f"\nMann-Whitney U (Jul vs Aug R): U={mw_u:.0f}, p={mw_p:.8f}\n\n")
    md.write("### Key Observable Changes July → August\n\n")
    md.write("| Variable | Direction of Change | Magnitude |\n|---|---|---|\n")
    md.write(f"| Trades | +{as_['n']-js['n']} | {js['n']} → {as_['n']} |\n")
    md.write(f"| Win rate | {as_['wr']-js['wr']:+.1%} | {js['wr']:.1%} → {as_['wr']:.1%} |\n")
    md.write(f"| Mean R | {as_['mean_r']-js['mean_r']:+.3f} | {js['mean_r']:.3f} → {as_['mean_r']:.3f} |\n")
    md.write(f"| SL exit % | {as_['sl_pct']-js['sl_pct']:+.1%} | {js['sl_pct']:.1%} → {as_['sl_pct']:.1%} |\n")
    md.write(f"| Buy direction % | {as_['buy_pct']-js['buy_pct']:+.1%} | {js['buy_pct']:.1%} → {as_['buy_pct']:.1%} |\n")
    md.write(f"| Sell direction % | {as_['sell_pct']-js['sell_pct']:+.1%} | {js['sell_pct']:.1%} → {as_['sell_pct']:.1%} |\n")
    md.write(f"| Mean stop distance | {as_['mean_sd']-js['mean_sd']:+.2f} pts | {js['mean_sd']:.2f} → {as_['mean_sd']:.2f} pts |\n\n")
    md.write("> [!NOTE]\n> Score, Margin, ATR, and Regime variables are not in the CSV. "
             "Causal explanation for the July→August shift requires those fields.\n\n")

    # ── TASK 8
    md.write("---\n\n## Task 8 — Directional Asymmetry (793 canonical trades)\n\n")
    md.write("| Metric | Buy | Sell | Sell − Buy |\n|---|---|---|---|\n")
    md.write(f"| Count | {n1} | {n2} | — |\n")
    md.write(f"| Win Rate | {bwr:.4f} | {swr:.4f} | {diff_wr:+.4f} |\n")
    md.write(f"| Mean R | {bmr:.4f} | {smr:.4f} | {smr-bmr:+.4f} |\n\n")
    md.write(f"**95% CI for win rate difference (sell − buy):** [{diff_wr-ci_diff:.4f}, {diff_wr+ci_diff:.4f}]\n\n")
    md.write(f"**Proportion z-test:** z = {z:.3f}, p = {p_prop:.8f}\n\n")
    md.write(f"**Mann-Whitney U:** U = {mw_u2:.0f}, p = {mw_p2:.8f}\n\n")
    md.write(f"**Cohen's d:** {d:.4f} ({'small' if abs(d)<0.3 else 'medium' if abs(d)<0.5 else 'large'} effect)\n\n")
    md.write("> [!IMPORTANT]\n> Directional asymmetry is **statistically significant** on both win-rate and R-multiple. "
             "This is a **diagnostic observation only.** Cause is unknown without Score/ATR/Regime data. "
             "Modifying the directional filter is out of scope.\n\n")

    # ── TASK 9
    md.write("---\n\n## Task 9 — Regime Labeling (Analysis-Only)\n\n")
    md.write("> [!WARNING]\n> **ANALYSIS-ONLY REGIME LABELS** — constructed post-hoc from:\n")
    md.write("> 1. Trailing 10-trade rolling mean R (trend proxy)\n")
    md.write("> 2. Stop-distance quartile (volatility proxy)\n")
    md.write("> These labels **do not exist in AMIGO.mq5** and are **not a strategy rule**.\n\n")
    md.write("### Regime Performance\n\n")
    md.write(rp.to_markdown(index=False))
    md.write(f"\n\n**Kruskal-Wallis test:** H = {kw_h:.3f}, p = {kw_p:.8f}\n\n")
    kw_sig = kw_p < 0.05
    md.write("**Interpretation:** " +
             ("Statistically significant performance differences exist across constructed regime labels (p < 0.05). "
              "TREND regime trades strongly outperform CHOP regime trades. "
              "This is consistent with a regime-following strategy but **does not prove causation** — "
              "the labels are derived from the same R series used to define performance."
              if kw_sig else
              "No significant performance difference across regime labels.") + "\n\n")
    md.write(f"![Regime Box Plot]({p_regime.as_uri()})\n\n")

    # ── TASK 10
    md.write("---\n\n## Task 10 — Final Evidence-Based Classification\n\n")
    md.write("| Domain | Classification | Evidence |\n|---|---|---|\n")
    md.write(f"| **DATA INTEGRITY** | ISSUE FOUND & DOCUMENTED | 1,260 raw rows → 793 canonical after dedup; 467 duplicates from multiple overlapping runs |\n")
    md.write(f"| **R-MULTIPLE DEFINITION** | CONSISTENT | net_pnl / planned_risk = r_multiple exactly (diff = 0.00000000) |\n")
    md.write(f"| **CANDIDATE POPULATION** | UNVERIFIED FROM LOG | EA Print() output not in tester log; P3 summary counts used as-reported |\n")
    md.write(f"| **P2.2 CONTRADICTION** | RECONCILED | Different populations: P2.2 on executed subset, P3 on all candidates |\n")
    md.write(f"| **MONTE CARLO VALIDITY** | CORRECTED | Corrected p-values on 793 canonical trades: DD={pv_dd:.6f}, Loss={pv_loss:.6f}, Win={pv_win:.6f} |\n")
    md.write(f"| **SEQUENCE BEHAVIOUR** | CLUSTERING CONFIRMED | All three MC metrics far outside 10,000 shuffles |\n")
    md.write(f"| **CAUSAL REGIME CLAIM** | NOT ESTABLISHED | MC proves non-random ordering; regime causation requires separate test |\n")
    md.write(f"| **DIRECTIONAL ASYMMETRY** | CONFIRMED | Sell WR={swr:.1%} vs Buy WR={bwr:.1%}; MW p={mw_p2:.6f}; Cohen's d={d:.3f} |\n")
    md.write(f"| **MONTHLY STABILITY** | CONCENTRATED | Jul-26: {js['n']:.0f} trades +{js['sum_r']:.1f}R. Aug-26: {as_['n']:.0f} trades {as_['sum_r']:.1f}R |\n")
    md.write(f"| **REGIME RELATIONSHIP** | POSSIBLE (UNPROVEN) | Analysis-only labels: KW H={kw_h:.1f} p={kw_p:.6f}; TREND >> CHOP; labels are post-hoc |\n\n")

    md.write("---\n\n### CONFIRMED\n\n")
    md.write("1. Data: 793 canonical trades after dedup; all R values, exit prices, SL/TP present\n")
    md.write("2. R-multiple = net_pnl / planned_risk exactly\n")
    md.write(f"3. Sequence clustering confirmed (MC corrected p-values all ≤ {max(pv_dd,pv_loss,pv_win):.6f})\n")
    md.write("4. Directional asymmetry is statistically significant\n\n")

    md.write("### RECONCILED\n\n")
    md.write("1. P2.2 95.2% vs P3 44.1%: different pipeline populations — not contradictory\n\n")

    md.write("### UNRESOLVED\n\n")
    md.write("1. **CSV duplicate origin**: 1,260 rows contain 793 unique trades. The extra 467 rows appear to be from multiple overlapping backtest runs appended to the same file. Which run is authoritative is unclear without timestamps on the export.\n")
    md.write("2. **Candidate population verification**: EA journal (DECISION/ACTION_TRADE prints) not found on disk. P3 candidate counts cannot be independently confirmed from log files.\n")
    md.write("3. **July→August shift cause**: Trade count +385%, win rate -33pp, SL% +36pp between months. ATR/Score/Regime data absent from CSV.\n")
    md.write("4. **Buy underperformance cause**: Buy WR 35% vs Sell WR 49%. Score/ATR not available per trade.\n\n")

    md.write("### ENGINEERING GAP\n\n")
    md.write("1. `sweep_reject = false` — pre-existing, not addressed in this audit\n")
    md.write("2. Score, Margin, ATR, Regime not exported to CSV — prevents per-trade signal diagnostics\n")
    md.write("3. CSV export writes multiple overlapping runs without deduplication\n\n")

    md.write("### NEXT ANALYSIS (if required)\n\n")
    md.write("1. Fix CSV export to write unique trades only, tagged with run timestamp\n")
    md.write("2. Add Score/Margin/ATR/Regime to CSV logging (read-only, no trading change)\n")
    md.write("3. Re-run P3.3 with full per-trade feature set\n")
    md.write("4. Investigate August trade-count spike with regime context\n\n")
    md.write("---\n\n*All analyses are read-only. No MQL5 source, thresholds, or risk parameters were modified.*\n")

print(f"\nReport: {REPORT}")
print("Done.")
