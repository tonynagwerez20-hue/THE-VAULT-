# AlgoMind AMIGO - P3.2 Analysis Walkthrough

Dataset: 1260 executed trades | XAUUSDm M5 | 2025-10-01 to 2026-08-28

---

## Task 8 — Sequence Dependence Analysis

Monte Carlo test: 10,000 shuffles of the R-multiple sequence.
p-value = fraction of shuffled populations >= actual (one-sided).

### Baseline Metrics

| Metric | Actual |
|---|---|
| Max Drawdown (R) | 176.8842 |
| Longest Losing Streak | 100 |
| Longest Winning Streak | 45 |

### Monte Carlo Summary

| Metric | Shuffled Mean | Shuffled Median | 5th pct | 95th pct | Actual | p-value |
|---|---|---|---|---|---|---|
| Max Drawdown (R) | 23.5465 | 22.4953 | 16.0010 | 34.6115 | 176.8842 | 0.0000 |
| Longest Losing Streak | 12.49 | 12.00 | 9.00 | 17.00 | 100 | 0.0000 |
| Longest Winning Streak | 7.53 | 7.00 | 6.00 | 10.00 | 45 | 0.0000 |

### Interpretation

- Max Drawdown: **SIGNIFICANT (p < 0.05)** — actual drawdown is worse than random order.
- Losing Streak: **SIGNIFICANT (p < 0.05)** — actual losing streaks are longer than random order.
- Winning Streak: **SIGNIFICANT (p < 0.05)** — actual winning streaks are longer than random order.

### Histogram Plots

![](file:///C:/Users/USER/Desktop/ALGOMIND/Python/hist_max_drawdown.png)

![](file:///C:/Users/USER/Desktop/ALGOMIND/Python/hist_longest_loss.png)

![](file:///C:/Users/USER/Desktop/ALGOMIND/Python/hist_longest_win.png)

---

## Task 9 — Signal Quality Diagnostics

### Numeric Feature Correlations with Realized R

| Feature       |   Pearson r |   Spearman rho |
|:--------------|------------:|---------------:|
| stop_distance |     -0.0774 |        -0.077  |
| volume        |      0.1595 |         0.1195 |
| planned_risk  |      0.0348 |         0.072  |

### Performance by Direction

| direction   |   count |     mean_R |   std_R |   win_rate |
|:------------|--------:|-----------:|--------:|-----------:|
| buy         |     762 | 0.00933945 | 1.40727 |   0.358268 |
| sell        |     498 | 0.404078   | 1.48438 |   0.485944 |

### Performance by Exit Type

| trig        |   count |   mean_R |    std_R |   win_rate |
|:------------|--------:|---------:|---------:|-----------:|
| stop_loss   |     847 | -0.75915 | 0.6513   |   0.120425 |
| take_profit |     413 |  2.06137 | 0.445069 |   1        |

### Monthly Performance

| month   |   count |     mean_R |   cumulative_R |
|:--------|--------:|-----------:|---------------:|
| 2025-10 |      65 |  0.231716  |       15.0615  |
| 2025-11 |      53 |  0.331129  |       17.5499  |
| 2025-12 |     126 |  0.533051  |       67.1644  |
| 2026-01 |      20 |  1.53842   |       30.7683  |
| 2026-02 |      91 |  0.159401  |       14.5055  |
| 2026-03 |      51 | -0.0380038 |       -1.93819 |
| 2026-04 |      38 |  0.345475  |       13.128   |
| 2026-05 |      52 | -0.115609  |       -6.01169 |
| 2026-06 |      56 | -0.27581   |      -15.4454  |
| 2026-07 |     121 |  0.952428  |      115.244   |
| 2026-08 |     587 | -0.0710031 |      -41.6788  |

### Scatter Plot: Stop Distance vs Realized R

![](file:///C:/Users/USER/Desktop/ALGOMIND/Python/scatter_stop_distance.png)

### Box Plots: Realized R by Direction and Exit Type

![](file:///C:/Users/USER/Desktop/ALGOMIND/Python/box_realizedR.png)

### Monthly Realized R Bar Chart

![](file:///C:/Users/USER/Desktop/ALGOMIND/Python/monthly_realizedR.png)

---

*All analyses are read-only. No strategy parameters, risk settings, or code were modified.*
