# ALGOMIND MINIMUM VIABLE BALANCE FORENSIC AUDIT

## Section 1: Broker Specification

| Property | Value | Source | Verification |
|:---------|:------|:-------|:-------------|
| Symbol | XAUUSDm | Hardcoded in Python scripts | BROKER SPECIFICATION NOT VERIFIED |
| Contract Size | 100 troy oz / lot | Hardcoded (L29-32 run_audit_pipeline.py) | Consistent with MQL5 standard |
| Tick Size | 0.01 | Hardcoded | Consistent with MQL5 standard |
| Tick Value | $1.00 / lot / tick | Hardcoded | Consistent with MQL5 standard |
| Point Size | 0.01 | Assumed same as tick_size | NOT INDEPENDENTLY VERIFIED |
| Min Volume | 0.01 lot | Hardcoded | Typical for micro-lot brokers |
| Volume Step | 0.01 lot | Hardcoded | Typical for micro-lot brokers |
| Max Volume | Not specified | N/A | NOT TESTED |
| Leverage | 1:100 | Hardcoded | Varies by broker/jurisdiction |
| Spread | Not modeled | N/A | SIMULATION LIMITATION |
| Commission | Not modeled | Embedded in historical PnL | PARTIALLY CAPTURED |
| Swap | Not modeled | N/A | SIMULATION LIMITATION |
| Stop Level | Unknown | N/A | NOT TESTED |
| Freeze Level | Unknown | N/A | NOT TESTED |

> [!WARNING]
> All symbol specifications are hardcoded in Python simulation scripts. The MQL5 EA (`Risk Engine.mqh` L92-96) queries broker specs dynamically via `SymbolInfoDouble()`. The Python simulations use assumed values that have **NOT been independently verified** against the actual live broker.

## Section 2: Position Sizing Mathematics

### Equations

```
loss_per_lot = (stop_distance / tick_size) * tick_value
             = stop_distance * contract_size    (for XAUUSD)

ideal_volume = risk_amount / loss_per_lot
             = (equity * risk_pct) / (stop_distance * contract_size)

actual_volume = max(min_lot, floor(ideal_volume / lot_step) * lot_step)

actual_risk = actual_volume * stop_distance * contract_size

risk_distortion = actual_risk_pct / intended_risk_pct
```

### Verification Against MQL5 Source
- `Risk Engine.mqh` L111: `loss_per_lot = (stop_distance / tick_size) * tick_value` ✅
- `Risk Engine.mqh` L118-119: `raw = risk_amount / loss_per_lot; lots = floor(raw / vol_step) * vol_step` ✅
- Python formula algebraically identical ✅

### Verification Against Dataset
- `planned_risk_dollars = volume * stop_dist * contract_size` — **759/759 exact matches** ✅

## Section 3: Minimum-Lot Risk Table

For the minimum lot (0.01), the fixed monetary risk per trade is:

```
min_lot_risk = 0.01 * stop_distance * 100 = stop_distance (in USD)
```

| Stop Distance Statistic | Price Points | Min Lot Risk ($) |
|:------------------------|:-------------|:-----------------|
| Minimum | 2.877 | $2.88 |
| Mean | 12.902 | $12.90 |
| Median | 11.083 | $11.08 |
| Maximum | 34.477 | $34.48 |

## Section 4: Risk Distortion Curve

| Balance | Mean Distortion | Max Distortion | % Trades Distorted | Mean Actual Risk % | Margin Pass % |
|--------:|:----------------|:---------------|:-------------------|:-------------------|:--------------|
| $5 | 516.0783x | 1379.0800x | 100.0% | 258.04% | 0.0% |
| $10 | 258.0391x | 689.5400x | 100.0% | 129.02% | 0.0% |
| $25 | 103.2157x | 275.8160x | 100.0% | 51.61% | 0.0% |
| $50 | 51.6078x | 137.9080x | 100.0% | 25.80% | 88.7% |
| $100 | 25.8039x | 68.9540x | 100.0% | 12.90% | 100.0% |
| $250 | 10.3216x | 27.5816x | 100.0% | 5.16% | 100.0% |
| $500 | 5.1608x | 13.7908x | 100.0% | 2.58% | 100.0% |
| $1,000 | 2.5804x | 6.8954x | 93.4% | 1.29% | 100.0% |
| $1,500 | 1.7317x | 4.5969x | 77.2% | 0.87% | 100.0% |
| $2,000 | 1.3200x | 3.4477x | 56.4% | 0.66% | 100.0% |
| $2,500 | 1.0930x | 2.7582x | 42.2% | 0.55% | 100.0% |
| $3,000 | 0.9714x | 2.2985x | 32.1% | 0.49% | 100.0% |
| $5,000 | 0.8235x | 1.3791x | 5.7% | 0.41% | 100.0% |

## Section 5: Minimum Viable Balances

### By Maximum Actual Risk Threshold

| Max Permitted Risk % | Min Balance (Mean Stop) | Min Balance (Worst Stop) | Distortion vs 0.50% |
|:---------------------|:------------------------|:-------------------------|:---------------------|
| 0.25% | $5,161 | $13,791 | 2.00x |
| 0.50% | $2,580 | $6,895 | 1.00x |
| 0.75% | $1,720 | $4,597 | 0.67x |
| 1.00% | $1,290 | $3,448 | 0.50x |
| 1.25% | $1,032 | $2,758 | 0.40x |
| 1.50% | $860 | $2,298 | 0.33x |
| 2.00% | $645 | $1,724 | 0.25x |
| 2.50% | $516 | $1,379 | 0.20x |
| 5.00% | $258 | $690 | 0.10x |

### Distortion Breakpoints

- Mean distortion <= 1.0x: **$2,900**
- Mean distortion <= 1.1x: **$2,500**
- Mean distortion <= 1.2x: **$2,200**
- Mean distortion <= 1.5x: **$1,800**
- Mean distortion <= 2.0x: **$1,300**

## Section 6: Small-Account Replay Results

|   Balance |   TradeCount |   ExecutedTrades |   RejectedTrades |   RejectedMargin |   RejectedEquityDepleted |   MinLotConstrained |   StartingEquity |   EndingEquity |   NetReturnPct |   MaxDDPct |   MaxLosingStreak |   AvgActualRiskPct |   MaxActualRiskPct |   MeanRiskDistortion |   MarginFailures | FailureType                    |
|----------:|-------------:|-----------------:|-----------------:|-----------------:|-------------------------:|--------------------:|-----------------:|---------------:|---------------:|-----------:|------------------:|-------------------:|-------------------:|---------------------:|-----------------:|:-------------------------------|
|         5 |          759 |                0 |              759 |              759 |                        0 |                   0 |                5 |           5    |           0    |       0    |                 0 |             0      |             0      |               0      |              759 | NON-EXECUTABLE (MARGIN)        |
|        10 |          759 |                0 |              759 |              759 |                        0 |                   0 |               10 |          10    |           0    |       0    |                 0 |             0      |             0      |               0      |              759 | NON-EXECUTABLE (MARGIN)        |
|        25 |          759 |                0 |              759 |              759 |                        0 |                   0 |               25 |          25    |           0    |       0    |                 0 |             0      |             0      |               0      |              759 | NON-EXECUTABLE (MARGIN)        |
|        50 |          759 |                1 |              758 |              758 |                        0 |                   1 |               50 |          37.92 |         -24.16 |      24.16 |                 1 |            24.922  |            24.922  |              49.844  |              758 | EXECUTABLE_SEVERE_DISTORTION   |
|       100 |          759 |                6 |              753 |              753 |                        0 |                   6 |              100 |          30.29 |         -69.71 |      69.71 |                 6 |            17.6071 |            28.5862 |              35.2143 |              753 | EXECUTABLE_SEVERE_DISTORTION   |
|       250 |          759 |              759 |                0 |                0 |                        0 |                 614 |              250 |        3820.91 |        1428.37 |      18.27 |                23 |             1.3042 |             9.0068 |               2.6084 |                0 | EXECUTABLE_HIGH_DISTORTION     |
|       500 |          759 |              759 |                0 |                0 |                        0 |                 564 |              500 |        4106.79 |         721.36 |      17    |                23 |             0.9339 |             3.2988 |               1.8679 |                0 | EXECUTABLE_MODERATE_DISTORTION |
|      1000 |          759 |              759 |                0 |                0 |                        0 |                 449 |             1000 |        4734.89 |         373.49 |      15.55 |                23 |             0.6536 |             1.4692 |               1.3072 |                0 | EXECUTABLE_MODERATE_DISTORTION |
|      1500 |          759 |              759 |                0 |                0 |                        0 |                 348 |             1500 |        5616.66 |         274.44 |      13.2  |                23 |             0.5212 |             0.9998 |               1.0424 |                0 | EXECUTABLE_MINOR_DISTORTION    |
|      2000 |          759 |              759 |                0 |                0 |                        0 |                 203 |             2000 |        6819.02 |         240.95 |      11.86 |                23 |             0.4467 |             0.7577 |               0.8934 |                0 | EXECUTABLE_FAITHFUL            |
|      2500 |          759 |              759 |                0 |                0 |                        0 |                  65 |             2500 |        8091.52 |         223.66 |      11.03 |                23 |             0.4126 |             0.6036 |               0.8251 |                0 | EXECUTABLE_FAITHFUL            |
|      3000 |          759 |              759 |                0 |                0 |                        0 |                   3 |             3000 |        8849.33 |         194.98 |      11.29 |                23 |             0.3948 |             0.5177 |               0.7895 |                0 | EXECUTABLE_FAITHFUL            |
|      5000 |          759 |              759 |                0 |                0 |                        0 |                   0 |             5000 |       17124.6  |         242.49 |      11.46 |                23 |             0.4243 |             0.4997 |               0.8485 |                0 | EXECUTABLE_FAITHFUL            |

## Section 7: Monte Carlo Results (10,000 Paths, Dynamic Lot Sizing)

|   Balance |   RiskPct |   SimCount |   MedianFinalEquity |   P5FinalEquity |   P25FinalEquity |   P50FinalEquity |   P75FinalEquity |   P95FinalEquity |   MedianMaxDDPct |   P95MaxDDPct |   WorstObservedDDPct |   MaxLosingStreakP95 |   ProbHalvingPct |   ProbSevereDDPct |   ProbRuinPct |   ProbDoublingPct |   FailedPaths |   TotalPaths |
|----------:|----------:|-----------:|--------------------:|----------------:|-----------------:|-----------------:|-----------------:|-----------------:|-----------------:|--------------:|---------------------:|---------------------:|-----------------:|------------------:|--------------:|------------------:|--------------:|-------------:|
|         5 |      0.25 |      10000 |                5    |            5    |             5    |             5    |             5    |             5    |             0    |          0    |                 0    |                    0 |             0    |              0    |          0    |              0    |             0 |        10000 |
|        10 |      0.25 |      10000 |               10    |           10    |            10    |            10    |            10    |            10    |             0    |          0    |                 0    |                    0 |             0    |              0    |          0    |              0    |             0 |        10000 |
|        25 |      0.25 |      10000 |               25    |           25    |            25    |            25    |            25    |            25    |             0    |          0    |                 0    |                    0 |             0    |              0    |          0    |              0    |             0 |        10000 |
|        50 |      0.25 |      10000 |               35.87 |           20.73 |            29.12 |            35.87 |          3334.56 |          4273.51 |            32.65 |         76.79 |               126.71 |                   11 |             9.13 |             24.67 |          0.39 |             37.39 |            39 |        10000 |
|       100 |      0.25 |      10000 |             3422.93 |           27.46 |          2663.95 |          3422.93 |          3900.48 |          4559.54 |             5.84 |         80.1  |               112.1  |                   12 |            27.01 |             20.8  |          0.06 |             79.2  |             6 |        10000 |
|       500 |      0.25 |      10000 |             4012.88 |         3059.73 |          3619.39 |          4012.88 |          4416.2  |          5022.82 |             4.71 |          8.7  |                24.06 |                   13 |             0.19 |              0    |          0    |            100    |             0 |        10000 |
|      1000 |      0.25 |      10000 |             4529.02 |         3545.49 |          4119.41 |          4529.02 |          4938.69 |          5548.12 |             4.18 |          7.51 |                19.97 |                   13 |             0    |              0    |          0    |            100    |             0 |        10000 |
|      3000 |      0.25 |      10000 |             6812.92 |         5655.04 |          6309.77 |          6812.92 |          7302.49 |          8047.92 |             2.81 |          4.78 |                12.96 |                   13 |             0    |              0    |          0    |             86.93 |             0 |        10000 |
|      5000 |      0.25 |      10000 |             9629.83 |         8248.82 |          9018.6  |          9629.83 |         10254.3  |         11155.1  |             2.2  |          3.66 |                 7.79 |                   13 |             0    |              0    |          0    |             34.49 |             0 |        10000 |
|         5 |      0.5  |      10000 |                5    |            5    |             5    |             5    |             5    |             5    |             0    |          0    |                 0    |                    0 |             0    |              0    |          0    |              0    |             0 |        10000 |
|        10 |      0.5  |      10000 |               10    |           10    |            10    |            10    |            10    |            10    |             0    |          0    |                 0    |                    0 |             0    |              0    |          0    |              0    |             0 |        10000 |
|        25 |      0.5  |      10000 |               25    |           25    |            25    |            25    |            25    |            25    |             0    |          0    |                 0    |                    0 |             0    |              0    |          0    |              0    |             0 |        10000 |
|        50 |      0.5  |      10000 |               35.87 |           20.73 |            29.19 |            35.87 |          3522.46 |          4763.45 |            32.28 |         75.68 |               127.25 |                   11 |             9.21 |             24.81 |          0.38 |             36.88 |            38 |        10000 |
|       100 |      0.5  |      10000 |             3656.02 |           26.97 |          2751.78 |          3656.02 |          4286.95 |          5241.93 |             5.59 |         80.14 |               112.11 |                   12 |            26.77 |             20.78 |          0.11 |             79.22 |            11 |        10000 |
|       500 |      0.5  |      10000 |             4427.92 |         3168.62 |          3889.77 |          4427.92 |          5045.53 |          6033.59 |             4.51 |          8.31 |                22.76 |                   13 |             0.19 |              0    |          0    |            100    |             0 |        10000 |
|      1000 |      0.5  |      10000 |             5282.73 |         3815.75 |          4621.53 |          5282.73 |          6004.08 |          7169.11 |             4.03 |          7.19 |                17.02 |                   13 |             0    |              0    |          0    |             99.98 |             0 |        10000 |
|      3000 |      0.5  |      10000 |            10236.5  |         7693.39 |          9118.52 |         10236.5  |         11582.4  |         13869.5  |             3.65 |          6.24 |                13.22 |                   13 |             0    |              0    |          0    |             99.85 |             0 |        10000 |
|      5000 |      0.5  |      10000 |            17012.4  |        12536.6  |         14988.2  |         17012.4  |         19427.5  |         23430.9  |             3.82 |          6.6  |                14.97 |                   13 |             0    |              0    |          0    |             99.83 |             0 |        10000 |

## Section 8: Interpretation

### Three Failure Categories

1. **NON-EXECUTABLE**: Account cannot open minimum position due to margin requirements.
   - Margin for 0.01 lot ranges $38.56 to $53.31
   - Accounts below ~$39 are always non-executable

2. **EXECUTABLE BUT RISK-DISTORTED**: Trade executes but minimum lot forces actual risk >> intended risk.
   - At $100: mean actual risk 12.9% vs intended 0.50%
   - At $500: mean actual risk 2.58%
   - At $3,000: mean actual risk 0.486%

3. **STRATEGY FAILURE**: Strategy underperforms despite correct execution. NOT observed in audit — strategy shows positive edge when risk is faithfully expressed.

### Transition Breakpoints

| Transition | Balance | Criterion |
|:-----------|--------:|:----------|
| Non-executable -> Executable | ~$39-53 | Margin for 0.01 lot (varies with gold price) |
| Severe distortion -> High distortion | ~$250 | Mean distortion drops below 5x |
| High distortion -> Moderate | ~$1,000 | Mean distortion drops below 2x |
| Moderate -> Minor | ~$2,600 | Mean distortion drops below 1.25x |
| Minor -> Faithful | ~$3,100 | Mean distortion drops below 1.0x |

## Section 9: Limitations

1. **BROKER SPECIFICATION NOT VERIFIED** — All symbol specs are hardcoded assumptions, not queried from live broker.
2. **Spread/Slippage Not Modeled** — Simulations use historical PnL which embeds actual spread/commission at the time of trading, but does not dynamically model varying spreads.
3. **Static Gold Price Assumption** — Margin calculations correctly use per-trade entry prices, but future gold prices (and thus future margins) are unknown.
4. **Monte Carlo Bootstrap** — Resampling with replacement assumes trade independence (no serial correlation). Real markets exhibit autocorrelation.
5. **Single Risk Configuration** — Audit tests 0.25% and 0.50% risk only. Other risk levels may behave differently.
6. **Leverage Assumption** — 1:100 is used throughout. Different brokers offer different leverage for gold, significantly affecting margin requirements and minimum viable balance.

## Section 10: Evidence-Based Conclusions

### Previous Claim vs Audit Result

| Claim | Previous Report | Audit Finding | Status |
|:------|:----------------|:--------------|:-------|
| $5-$25 non-executable | 0 trades executed | 0 trades (confirmed) | **CONFIRMED** |
| $50 = 1 executed | 1 trade executed | Differs (dynamic equity sizing) | **REQUIRES REVIEW** |
| $100 = 6 executed | 6 trades executed | Differs (dynamic equity sizing) | **REQUIRES REVIEW** |
| $3,000 conservative floor | 0.97x distortion | 0.97x mean, but 2.30x max, 32% trades >1.0x | **PARTIALLY CONFIRMED** |
| $50 margin = $38.70 | Fixed | Dynamic: $38.56-$53.31 | **DISCREPANCY** |
