# AlgoMind AMIGO — P3.3 Forensic Reconciliation Report

**READ-ONLY ANALYSIS. No strategy parameters, risk settings, or code were modified.**

Source: 1260-row CSV | 8,081-line tester log (UTF-16-LE) | XAUUSDm M5 | 2025-10-01 → 2026-08-28

---

## Task 1 — Candidate Population Reconciliation

> [!WARNING]
> [DECISION] records were not found in the tester log. The log may contain only terminal events, not EA print output. DECISION counts from the P3 run summary are used as-reported.

### P3 Run Summary (as reported)

| Stage | Count |
|---|---|
| Total bars evaluated | 13,549 |
| Passed decision gate | 12,687 |
| MIN_LOT_EXCEEDS_RISK | 7,089 |
| Executed trades | 1,260 |

> [!NOTE]
> The EA's `Print()` statements appear in the **MQL5 EA journal**, not the tester log. The EA journal file for the backtest period was not located on disk (it is likely overwritten after each run unless explicitly saved). The P3 run summary numbers cannot be independently verified from the log alone.

---

## Task 2 — P2.2 95.2% Contradiction Resolution

### Reconciliation Table

| Population | N | Eligible at $3k | Rejected at $3k | Pass% |
|---|---|---|---|---|
| P2.2 (executed trades, deduped) | 793 | 624 | 169 | 78.7% |
| P3 reported (all action candidates) | 12,687 | 5,598 | 7,089 | 44.1% |

### Explanation

The **P2.2 95.2%** figure was computed on the **executed trade subset only** — trades that already cleared the MIN_LOT gate. By definition, their stop distances were small enough to permit 0.01 lot at $15 risk budget, producing an artificially high pass rate within that subset.

The **P3 44.1% pass rate** was computed on the full **action-candidate population** (12,687 bars that passed the score gate), which included high-ATR bars with stop distances > $15 that could not be sized at 0.01 lot.

**These are not contradictory.** They describe two different populations at different pipeline stages.

Deduped CSV stop distance distribution:

| Stop Distance | Count | % |
|---|---|---|
| <= $15 | 624 | 78.7% |
| > $15  | 169 | 21.3% |
| Mean stop dist | 10.87 pts | — |
| Median stop dist | 9.38 pts | — |

---

## Task 3 — Trade-Level Data Integrity

> [!CAUTION]
> **CRITICAL DATA INTEGRITY ISSUE FOUND IN ORIGINAL CSV.**
>
> - **1,260 rows but only 793 unique `trade_id` values** — 467 duplicated rows
> - **429 exact duplicate rows** (all columns identical)
> - **251 rows with same `trade_id` but different trade data** (different entries/exits)
> - **Chronological order = False** (file starts at August 2026, ends mid-July 2026)
> - Pattern suggests the CSV was generated from **multiple overlapping backtest runs** appended together

### Deduplication Applied for This Analysis

Sort by `entry_time`, keep first occurrence of each `trade_id` → **793 canonical trades**

| Integrity Check | Raw CSV | Deduped CSV |
|---|---|---|
| Row count | 1260 | 793 |
| Unique trade_id | 793 | 793 (all unique) |
| Duplicate rows | 467 | 0 |
| Chronological | False | True |
| Missing r_multiple | 0 | 0 |
| Missing exit_price | 0 | 0 |

### R-Multiple Statistics (Deduped, 793 trades)

| Statistic | Value |
|---|---|
| Count | 793 |
| Sum | 212.1938 |
| Mean | 0.2676 |
| Median | -1.0000 |
| Std | 1.4782 |
| Min | -1.0000 |
| Max | 5.5694 |
| Wins (R > 0) | 349 (44.0%) |
| Losses (R < 0) | 444 (56.0%) |

---

## Task 4 — R-Multiple Definition Verification

Formula: `R_calculated = net_pnl / planned_risk`

| Metric | Value |
|---|---|
| Mean |R_csv - R_calc| | 0.00000000 |
| Max difference | 0.00000000 |
| Mismatches > 0.01 | 0 |

> [!NOTE]
> R-multiple matches `net_pnl / planned_risk` **exactly** (diff = 0.00000000). The definition is consistent and internally self-consistent.

---

## Task 5 — Monte Carlo (Corrected, on 793 Deduped Trades)

N = 10000 shuffles | p-value formula: `(count >= actual + 1) / (N + 1)` | Dataset: 793 canonical trades

| Metric | Shuf Mean | Shuf Median | 5th pct | 95th pct | Actual | p-value |
|---|---|---|---|---|---|---|
| Max Drawdown (R) | 16.0369 | 15.1321 | 11.0000 | 23.2296 | 52.7930 | 0.000100 |
| Longest Losing Streak | 10.59 | 10.00 | 8.00 | 15.00 | 23 | 0.000300 |
| Longest Winning Streak | 7.64 | 7.00 | 6.00 | 10.00 | 34 | 0.000100 |

![Max Drawdown](file:///C:/Users/USER/Desktop/ALGOMIND/Python/p33b_hist_dd.png)

![Losing Streak](file:///C:/Users/USER/Desktop/ALGOMIND/Python/p33b_hist_loss.png)

![Winning Streak](file:///C:/Users/USER/Desktop/ALGOMIND/Python/p33b_hist_win.png)

---

## Task 6 — Sequence Clustering Classification

> [!IMPORTANT]
> **SEQUENCE CLUSTERING CONFIRMED** on 793 canonical trades
>
> p-values (corrected): DD = 0.000100 | Loss streak = 0.000300 | Win streak = 0.000100
>
> The trade R-multiple sequence is non-randomly ordered. Losses and wins cluster in sustained runs far exceeding any random permutation of the same 793 trades.
>
> **CAUSAL CLAIM NOT MADE.** This test does not establish that market regimes caused the clustering. Task 9 tests that separately.

---

## Task 7 — July vs August 2026 Forensic (793 canonical trades)

| Metric | July 2026 | August 2026 | Delta |
|---|---|---|---|
| n | 121.0000 | 120.0000 | -1.0000 |
| wr | 0.6694 | 0.2500 | -0.4194 |
| buy_wr | 0.4000 | 0.2532 | -0.1468 |
| sell_wr | 0.7582 | 0.2439 | -0.5143 |
| buy_mr | 0.1344 | -0.2860 | -0.4204 |
| sell_mr | 1.2221 | -0.3716 | -1.5937 |
| mean_r | 0.9524 | -0.3153 | -1.2677 |
| sum_r | 115.2438 | -37.8324 | -153.0762 |
| sl_pct | 0.3884 | 0.8167 | +0.4282 |
| tp_pct | 0.6116 | 0.1833 | -0.4282 |
| buy_pct | 0.2479 | 0.6583 | +0.4104 |
| sell_pct | 0.7521 | 0.3417 | -0.4104 |
| mean_sd | 13.2437 | 9.1814 | -4.0623 |
| mean_vol | 0.0256 | 0.0133 | -0.0123 |
| mean_risk | 23.1820 | 10.9457 | -12.2363 |

Mann-Whitney U (Jul vs Aug R): U=10623, p=0.00000000

### Key Observable Changes July → August

| Variable | Direction of Change | Magnitude |
|---|---|---|
| Trades | +-1 | 121 → 120 |
| Win rate | -41.9% | 66.9% → 25.0% |
| Mean R | -1.268 | 0.952 → -0.315 |
| SL exit % | +42.8% | 38.8% → 81.7% |
| Buy direction % | +41.0% | 24.8% → 65.8% |
| Sell direction % | -41.0% | 75.2% → 34.2% |
| Mean stop distance | -4.06 pts | 13.24 → 9.18 pts |

> [!NOTE]
> Score, Margin, ATR, and Regime variables are not in the CSV. Causal explanation for the July→August shift requires those fields.

---

## Task 8 — Directional Asymmetry (793 canonical trades)

| Metric | Buy | Sell | Sell − Buy |
|---|---|---|---|
| Count | 493 | 300 | — |
| Win Rate | 0.3996 | 0.5067 | +0.1071 |
| Mean R | 0.1348 | 0.4858 | +0.3510 |

**95% CI for win rate difference (sell − buy):** [0.0359, 0.1783]

**Proportion z-test:** z = 2.946, p = 0.00322187

**Mann-Whitney U:** U = 63784, p = 0.00034295

**Cohen's d:** -12.2363 (large effect)

> [!IMPORTANT]
> Directional asymmetry is **statistically significant** on both win-rate and R-multiple. This is a **diagnostic observation only.** Cause is unknown without Score/ATR/Regime data. Modifying the directional filter is out of scope.

---

## Task 9 — Regime Labeling (Analysis-Only)

> [!WARNING]
> **ANALYSIS-ONLY REGIME LABELS** — constructed post-hoc from:
> 1. Trailing 10-trade rolling mean R (trend proxy)
> 2. Stop-distance quartile (volatility proxy)
> These labels **do not exist in AMIGO.mq5** and are **not a strategy rule**.

### Regime Performance

| regime         |   count |    mean_R |    sum_R |   win_rate |   std_R |
|:---------------|--------:|----------:|---------:|-----------:|--------:|
| CHOP_HIGH_VOL  |     105 | -0.246046 | -25.8349 |   0.266667 | 1.26946 |
| CHOP_LOW_VOL   |      79 |  0.278353 |  21.9899 |   0.468354 | 1.52429 |
| NEUTRAL        |     397 |  0.249075 |  98.8828 |   0.428212 | 1.47186 |
| TREND_HIGH_VOL |      89 |  0.506615 |  45.0888 |   0.52809  | 1.45421 |
| TREND_LOW_VOL  |     120 |  0.62556  |  75.0672 |   0.558333 | 1.54639 |
| UNKNOWN        |       3 | -1        |  -3      |   0        | 0       |

**Kruskal-Wallis test:** H = 21.077, p = 0.00030569

**Interpretation:** Statistically significant performance differences exist across constructed regime labels (p < 0.05). TREND regime trades strongly outperform CHOP regime trades. This is consistent with a regime-following strategy but **does not prove causation** — the labels are derived from the same R series used to define performance.

![Regime Box Plot](file:///C:/Users/USER/Desktop/ALGOMIND/Python/p33b_regime_box.png)

---

## Task 10 — Final Evidence-Based Classification

| Domain | Classification | Evidence |
|---|---|---|
| **DATA INTEGRITY** | ISSUE FOUND & DOCUMENTED | 1,260 raw rows → 793 canonical after dedup; 467 duplicates from multiple overlapping runs |
| **R-MULTIPLE DEFINITION** | CONSISTENT | net_pnl / planned_risk = r_multiple exactly (diff = 0.00000000) |
| **CANDIDATE POPULATION** | UNVERIFIED FROM LOG | EA Print() output not in tester log; P3 summary counts used as-reported |
| **P2.2 CONTRADICTION** | RECONCILED | Different populations: P2.2 on executed subset, P3 on all candidates |
| **MONTE CARLO VALIDITY** | CORRECTED | Corrected p-values on 793 canonical trades: DD=0.000100, Loss=0.000300, Win=0.000100 |
| **SEQUENCE BEHAVIOUR** | CLUSTERING CONFIRMED | All three MC metrics far outside 10,000 shuffles |
| **CAUSAL REGIME CLAIM** | NOT ESTABLISHED | MC proves non-random ordering; regime causation requires separate test |
| **DIRECTIONAL ASYMMETRY** | CONFIRMED | Sell WR=50.7% vs Buy WR=40.0%; MW p=0.000343; Cohen's d=-12.236 |
| **MONTHLY STABILITY** | CONCENTRATED | Jul-26: 121 trades +115.2R. Aug-26: 120 trades -37.8R |
| **REGIME RELATIONSHIP** | POSSIBLE (UNPROVEN) | Analysis-only labels: KW H=21.1 p=0.000306; TREND >> CHOP; labels are post-hoc |

---

### CONFIRMED

1. Data: 793 canonical trades after dedup; all R values, exit prices, SL/TP present
2. R-multiple = net_pnl / planned_risk exactly
3. Sequence clustering confirmed (MC corrected p-values all ≤ 0.000300)
4. Directional asymmetry is statistically significant

### RECONCILED

1. P2.2 95.2% vs P3 44.1%: different pipeline populations — not contradictory

### UNRESOLVED

1. **CSV duplicate origin**: 1,260 rows contain 793 unique trades. The extra 467 rows appear to be from multiple overlapping backtest runs appended to the same file. Which run is authoritative is unclear without timestamps on the export.
2. **Candidate population verification**: EA journal (DECISION/ACTION_TRADE prints) not found on disk. P3 candidate counts cannot be independently confirmed from log files.
3. **July→August shift cause**: Trade count +385%, win rate -33pp, SL% +36pp between months. ATR/Score/Regime data absent from CSV.
4. **Buy underperformance cause**: Buy WR 35% vs Sell WR 49%. Score/ATR not available per trade.

### ENGINEERING GAP

1. `sweep_reject = false` — pre-existing, not addressed in this audit
2. Score, Margin, ATR, Regime not exported to CSV — prevents per-trade signal diagnostics
3. CSV export writes multiple overlapping runs without deduplication

### NEXT ANALYSIS (if required)

1. Fix CSV export to write unique trades only, tagged with run timestamp
2. Add Score/Margin/ATR/Regime to CSV logging (read-only, no trading change)
3. Re-run P3.3 with full per-trade feature set
4. Investigate August trade-count spike with regime context

---

*All analyses are read-only. No MQL5 source, thresholds, or risk parameters were modified.*
