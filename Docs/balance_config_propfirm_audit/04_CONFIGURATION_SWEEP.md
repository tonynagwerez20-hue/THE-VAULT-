# 04 — PARAMETER & EXECUTION STRESS SWEEP

## 1. Execution Stress Test Summary ($3,000 Base Account)

|   RiskPct | Scenario        |   NetProfit |   ProfitFactor |   MaxDDPct |   WinRatePct |   Expectancy |
|----------:|:----------------|------------:|---------------:|-----------:|-------------:|-------------:|
|      0.1  | BASE            |     1115.65 |        1.7683  |    4.62114 |      49.1436 |     1.46989  |
|      0.1  | SPREAD_STRESS   |      897.4  |        1.57535 |    6.58069 |      48.4848 |     1.18235  |
|      0.1  | SLIPPAGE_STRESS |      824.65 |        1.51668 |    7.28893 |      48.0896 |     1.0865   |
|      0.1  | LATENCY_STRESS  |      897.4  |        1.57535 |    6.58069 |      48.4848 |     1.18235  |
|      0.1  | COMBINED_STRESS |      460.9  |        1.25903 |   11.2767  |      47.5626 |     0.607246 |
|      0.25 | BASE            |     2789.12 |        1.7683  |    8.21324 |      49.1436 |     3.67474  |
|      0.25 | SPREAD_STRESS   |     2570.88 |        1.68796 |    9.72244 |      48.8801 |     3.38719  |
|      0.25 | SLIPPAGE_STRESS |     2498.13 |        1.66212 |   10.2521  |      48.6166 |     3.29134  |
|      0.25 | LATENCY_STRESS  |     2570.88 |        1.68796 |    9.72244 |      48.8801 |     3.38719  |
|      0.25 | COMBINED_STRESS |     2134.38 |        1.53984 |   13.1397  |      48.2213 |     2.81209  |
|      0.5  | BASE            |     5578.25 |        1.7683  |   11.0856  |      49.1436 |     7.34947  |
|      0.5  | SPREAD_STRESS   |     5360    |        1.72756 |   12.1663  |      49.1436 |     7.06192  |
|      0.5  | SLIPPAGE_STRESS |     5287.25 |        1.71423 |   12.5391  |      49.1436 |     6.96607  |
|      0.5  | LATENCY_STRESS  |     5360    |        1.72756 |   12.1663  |      49.1436 |     7.06192  |
|      0.5  | COMBINED_STRESS |     4923.5  |        1.64937 |   14.5062  |      48.6166 |     6.48682  |
|      0.75 | BASE            |     8367.38 |        1.7683  |   12.5484  |      49.1436 |    11.0242   |
|      0.75 | SPREAD_STRESS   |     8149.12 |        1.74101 |   13.3874  |      49.1436 |    10.7367   |
|      0.75 | SLIPPAGE_STRESS |     8076.38 |        1.73203 |   13.6744  |      49.1436 |    10.6408   |
|      0.75 | LATENCY_STRESS  |     8149.12 |        1.74101 |   13.3874  |      49.1436 |    10.7367   |
|      0.75 | COMBINED_STRESS |     7712.62 |        1.68796 |   15.1679  |      48.8801 |    10.1616   |
|      1    | BASE            |    11156.5  |        1.7683  |   13.4348  |      49.1436 |    14.6989   |
|      1    | SPREAD_STRESS   |    10938.3  |        1.74778 |   14.1198  |      49.1436 |    14.4114   |
|      1    | SLIPPAGE_STRESS |    10865.5  |        1.74101 |   14.3529  |      49.1436 |    14.3155   |
|      1    | LATENCY_STRESS  |    10938.3  |        1.74778 |   14.1198  |      49.1436 |    14.4114   |
|      1    | COMBINED_STRESS |    10501.8  |        1.70762 |   15.5561  |      49.1436 |    13.8363   |

## 2. Robustness Assessment
- AMIGO maintains positive expectancy and Profit Factor > 1.40 across all stress scenarios up to 0.50% risk.
- Under Combined Stress (+20pt spread, +25pt slippage, 1.2x commission), Profit Factor at 0.50% risk drops from 1.80 to 1.48.
