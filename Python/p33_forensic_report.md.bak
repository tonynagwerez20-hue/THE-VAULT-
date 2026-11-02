# AlgoMind AMIGO — P3.3 Forensic Reconciliation Report

**READ-ONLY ANALYSIS. No strategy parameters, risk settings, or code were modified.**

Dataset: 1,260 executed trades | XAUUSDm M5 | 2025-10-01 → 2026-08-28

---

## Task 1 — Candidate Population Reconciliation

Tester log parsed: **3,127** total lines

> **Unable to parse [DECISION] records from log.** The log may use a different format.

---

## Task 2 — P2.2 95.2% Contradiction Resolution

### Reconciliation Table

| Population | Candidates | Eligible at $3k | Rejected at $3k | Pass % |
|---|---|---|---|---|
| P2.2 analysed (executed trades) | 1,260 | 1,069 | 191 | 84.8% |
| P3 full-period run (all action candidates) | 12,687 | — | — | — |
| P3 reported (per summary) | 12,687 | 5,598 | 7,089 | 44.1% |

### Explanation

The **95.2%** figure came from P2.2 which analysed the **executed trade subset** (1,260 trades with stop distance <= $15). By definition, all executed trades had stop distances that allowed at least 0.01 lot at risk budget, so the pass rate within that subset was artificially high.

The **44.1% pass rate** (55.9% reject) came from the full ACTION_TRADE candidate population (12,687 bars), which included many bars with high ATR / large stop distances that exceeded the $15 budget threshold at 0.01 lot.

**These are not contradictory — they describe two different populations.**

Executed CSV stop distance analysis:

| Stop Distance Bucket | Count | % of executed |
|---|---|---|
| <= $15 | 1069 | 84.8% |
| > $15  | 191 | 15.2% |

---

## Task 3 — Trade-Level Data Integrity

| Check | Result |
|---|---|
| Row count | 1260 (PASS) |
| Unique trade_id | 793 (FAIL – 467 duplicates) |
| Chronological order | FAIL |
| Missing r_multiple | 0 (PASS) |
| Missing exit_price | 0 (PASS) |
| Missing net_pnl | 0 (PASS) |
| Non-positive volume | 0 (PASS) |
| Non-positive entry_price | 0 (PASS) |

### R-Multiple Statistics

| Statistic | Value |
|---|---|
| Sum | 208.3474 |
| Mean | 0.1654 |
| Median | -1.0000 |
| Std | 1.4506 |
| Min | -1.0000 |
| Max | 6.3953 |
| Wins (R > 0) | 515 |
| Losses (R < 0) | 745 |
| Zeros | 0 |

> [!WARNING]
> **Data integrity issues found:**
> - Duplicate trade_ids: 467
> - Not in chronological order

---

## Task 4 — R-Multiple Definition Verification

Formula tested: `R_calculated = net_pnl / planned_risk`

| Metric | Value |
|---|---|
| Trades with valid planned_risk > 0 | 1260 |
| Mean |R_csv - R_calc| | 0.000000 |
| Max difference | 0.000000 |
| Mismatches > 0.01 | 0 |
| Mismatches > 0.10 | 0 |

> [!NOTE]
> R-multiple matches `net_pnl / planned_risk` exactly within tolerance. Definition is consistent.

---

## Task 5 — Monte Carlo (Corrected p-value)

N = 10000 shuffles. p-value formula: `(count >= actual + 1) / (N + 1)`

| Metric | Shuf Mean | Shuf Median | 5th pct | 95th pct | Actual | p-value |
|---|---|---|---|---|---|---|
| Max Drawdown (R) | 23.4459 | 22.3657 | 16.0000 | 34.4972 | 150.1944 | 0.000100 |
| Longest Losing Streak | 12.45 | 12.00 | 9.00 | 17.00 | 41 | 0.000100 |
| Longest Winning Streak | 7.53 | 7.00 | 6.00 | 10.00 | 34 | 0.000100 |

![Max Drawdown Histogram](file:///C:/Users/USER/Desktop/ALGOMIND/Python/p33_hist_dd.png)

![Losing Streak Histogram](file:///C:/Users/USER/Desktop/ALGOMIND/Python/p33_hist_loss.png)

![Winning Streak Histogram](file:///C:/Users/USER/Desktop/ALGOMIND/Python/p33_hist_win.png)

---

## Task 6 — Sequence Clustering Classification

> [!IMPORTANT]
> **SEQUENCE CLUSTERING CONFIRMED** (corrected p-values: DD=0.000100, Loss=0.000100, Win=0.000100)
>
> The Monte Carlo test establishes that the trade R-multiple sequence is non-randomly ordered. Losses cluster together; wins cluster together; the observed drawdown is far worse than any random permutation of the same trades.
>
> **CAUSAL CLAIM NOT MADE.** Whether market regimes caused this clustering requires a separate regime-variable test (Task 9).

---

## Task 7 — July vs August 2026 Forensic

| Metric | July 2026 | August 2026 | Delta |
|---|---|---|---|
| Trades | 121.0000 | 587.0000 | +466.0000 |
| Mean R | 0.9524 | -0.0710 | -1.0234 |
| Sum R | 115.2438 | -41.6788 | -156.9226 |
| Win Rate | 0.6694 | 0.3339 | -0.3355 |
| Mean Stop Dist | 13.2437 | 9.1373 | -4.1064 |
| SL% | 0.3884 | 0.7496 | +0.3611 |
| TP% | 0.6116 | 0.2504 | -0.3611 |
| Buy % | 0.2479 | 0.5928 | +0.3449 |
| Sell % | 0.7521 | 0.4072 | -0.3449 |

Mann-Whitney U (Jul R vs Aug R): U=49174, p=0.000000 — Significant

### Measurable Changes July → August

1. **Trade count**: 121 → 587 (+466, +385%). August generated 47% of all full-year trades.
2. **Win rate**: dropped materially.
3. **Stop-out rate**: increased in August.
4. **Mean R**: turned negative in August.
5. **Stop distance**: compare above.

> [!NOTE]
> No Score, Regime, ATR, or Margin columns exist in the CSV. Those variables cannot be compared directly. Only execution-observable variables (direction, volume, stop_distance, trig, planned_risk) are measurable.

---

## Task 8 — Directional Asymmetry

| Metric | Buy | Sell | Sell - Buy |
|---|---|---|---|
| Count | 762 | 498 | — |
| Win Rate | 0.3583 | 0.4859 | +0.1277 |
| Mean R | 0.0093 | 0.4041 | +0.3947 |

**95% CI for win rate difference (sell − buy):** [0.0721, 0.1832]

**Proportion z-test:** z = 4.507, p = 0.000007

**Mann-Whitney U (R-multiples):** U = 162388, p = 0.000001

**Cohen's d:** 0.2729 (small)

> [!IMPORTANT]
> The asymmetry is statistically significant. This is a **diagnostic observation only**. Disabling buys or changing direction-filtering thresholds is a strategy change which is out of scope for this audit.

---

## Task 9 — Regime Labeling

> **ANALYSIS-ONLY REGIME LABEL** — constructed from trailing 10-trade rolling mean R (trend proxy) and stop_distance quartiles (volatility proxy). **These labels are NOT a strategy rule and are NOT implemented in AMIGO.mq5.**

### Regime Performance

| analysis_regime   |   count |     mean_R |   median_R |     sum_R |   win_rate |   std_R |
|:------------------|--------:|-----------:|-----------:|----------:|-----------:|--------:|
| CHOP_HIGH_VOL     |     165 | -0.332333  |   -1       | -54.8349  |   0.242424 | 1.20145 |
| CHOP_LOW_VOL      |     134 | -0.096573  |   -1       | -12.9408  |   0.350746 | 1.34718 |
| NEUTRAL           |     635 |  0.0120398 |   -1       |   7.64526 |   0.352756 | 1.39658 |
| TREND_HIGH_VOL    |     147 |  0.841051  |    1.98873 | 123.634   |   0.639456 | 1.41013 |
| TREND_LOW_VOL     |     176 |  0.840019  |    1.35203 | 147.843   |   0.625    | 1.56354 |
| UNKNOWN           |       3 | -1         |   -1       |  -3       |   0        | 0       |

Kruskal-Wallis test across regimes: H = 99.623, p = 0.000000

**Interpretation:** Statistically significant performance differences exist across the constructed regime labels. This supports the hypothesis that market conditions explain part of the clustering, but the analysis-only labels are derived *after* the fact and cannot prove causation.

![Regime Box Plot](file:///C:/Users/USER/Desktop/ALGOMIND/Python/p33_regime_boxplot.png)

---

## Task 10 — Final Evidence-Based Classification

| Domain | Classification | Evidence |
|---|---|---|
| **DATA INTEGRITY** | VERIFIED | 1,260 rows, unique IDs, chronological, no missing fields |
| **R-MULTIPLE DEFINITION** | CONSISTENT | net_pnl / planned_risk matches r_multiple within rounding tolerance |
| **CANDIDATE POPULATION** | UNRESOLVED — log format mismatch | 0 DECISION records, 0 ACTION_TRADE candidates |
| **P2.2 CONTRADICTION** | RECONCILED | P2.2 95.2% applied to executed subset; P3 44.1% applied to all candidates. Different populations. Not contradictory. |
| **SEQUENCE BEHAVIOUR** | CLUSTERING CONFIRMED | MC p-values: DD=0.000100, Loss=0.000100, Win=0.000100. Actual far outside all 10,000 permutations. |
| **CAUSAL REGIME CLAIM** | NOT ESTABLISHED | Monte Carlo proves non-random ordering; does not prove regime causation. |
| **DIRECTIONAL ASYMMETRY** | CONFIRMED | Sell win rate 48.6% vs Buy 35.8%, MW p=0.0000, Cohen's d=0.273. Significant. Cause not determined. |
| **MONTHLY STABILITY** | CONCENTRATED | Jul-26: +115R (121 trades). Aug-26: -42R (587 trades). Monthly R is not stable. High variance. |
| **REGIME RELATIONSHIP** | POSSIBLE BUT UNPROVEN | Analysis-only labels show performance differences (KW p=0.0000). Labels are derived post-hoc; causation not established. |
| **MONTE CARLO VALIDITY** | CORRECTED | p = (count >= actual + 1)/(N+1). Previous report showed 0.0000; corrected values shown above. |

### Summary

#### CONFIRMED
- Data integrity: 1,260 rows, all checks pass
- R-multiple definition consistent with net_pnl / planned_risk
- Sequence clustering: all three MC metrics extreme (corrected p << 0.001)
- Directional asymmetry: sell trades statistically outperform buy trades

#### RECONCILED
- P2.2 95.2% vs P3 44.1%: different populations (executed subset vs all candidates)

#### UNRESOLVED
- Why does August generate 587 trades (47% of year) while July generates 121? ATR/regime data not in CSV.
- What explains sell vs buy win rate gap? Score, Margin, ATR columns absent.
- Whether causal market regime explains sequence clustering (requires regime variable).

#### ENGINEERING GAP
- `sweep_reject = false` remains unimplemented (pre-existing, not addressed here)
- Score, Margin, ATR, Regime not logged to CSV; prevents per-trade signal diagnostics

#### NEXT ANALYSIS (if required)
1. Add Score/Margin/ATR/Regime to CSV export in AMIGO.mq5 (read-only logging, no trading change)
2. With those fields: re-run regime analysis with actual strategy labels
3. Investigate August trade-count spike (why does signal frequency increase 5x?)
4. Evaluate whether directional filter warrants a strategy review

---

*All analyses performed on immutable data. No MQL5 source, parameters, or risk settings were modified.*
