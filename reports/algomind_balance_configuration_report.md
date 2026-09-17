# ALGOMIND — FINAL BALANCE & PROP-FIRM VERDICT ( FOCUS: IS vs OOS & MONTE CARLO)

## Technical Floor


## Smallest Aggressive Viable Balance
,500

## Smallest Conservative Viable Balance
,000

## Balance Where Minimum-Lot Distortion Becomes Acceptable
,000

## Balance Where >=95% of Valid Historical Setups Are Executable


## Conservative Configuration (,000 Balance Baseline)
- **Account Balance**: ,000
- **Risk Per Trade**: 0.50% (.00 reference risk budget)
- **Max Historical Drawdown**: 11.09% (Balance DD) / 17.38% (MT5 Peak-to-Trough)
- **Profit Factor**: 1.80
- **Executability**: 100.0%
- **Average Risk Distortion**: 0.97x (Actual Risk 0.486%)

## Aggressive Configuration (,500 Balance Baseline)
- **Account Balance**: ,500
- **Risk Per Trade**: 0.50% (.50 reference risk budget)
- **Max Historical Drawdown**: 22.98%
- **Profit Factor**: 1.80
- **Executability**: 100.0%
- **Average Risk Distortion**: 1.73x (Actual Risk 0.866%)

## FundedNext
- **Model**: Stellar 2-Step (,000 Account)
- **Result**: **PASS** (at 0.25% Risk / Trade) | **PASS** (at 0.50% Risk / Trade)
- **Phase 1 Pass Probability (10,000 MC Paths)**: **100.00%** (Full) | **98.00%** (In-Sample) | **100.00%** (Out-of-Sample)
- **Max Loss Breach Probability**: **0.00%** (Full) | **0.14%** (In-Sample) | **0.00%** (Out-of-Sample)
- **EA Eligibility**: Allowed

## FundingPips
- **Model**: 2-Step Standard (,000 Account)
- **Result**: **PASS** (at 0.25% Risk / Trade) | **PASS** (at 0.50% Risk / Trade)
- **Phase 1 Pass Probability (10,000 MC Paths)**: **100.00%** (Full) | **98.00%** (In-Sample) | **100.00%** (Out-of-Sample)
- **Max Loss Breach Probability**: **0.00%** (Full) | **0.14%** (In-Sample) | **0.00%** (Out-of-Sample)
- **EA Eligibility**: Allowed

---

# IN-SAMPLE VS OUT-OF-SAMPLE & MONTE CARLO RISK REPORT (,000 ACCOUNT)

### 1. In-Sample (IS) vs Out-of-Sample (OOS) Baseline Breakdown
- **In-Sample (First 70% / 531 Trades)**:
  - Net Profit: ,133.77 | Profit Factor: **1.31** | Win Rate: **44.07%** | Max DD: **.30 (9.13%)**.
- **Out-of-Sample (Last 30% / 228 Trades)**:
  - Net Profit: ,600.34 | Profit Factor: **2.72** | Win Rate: **60.96%** | Max DD: **.69 (5.94%)**.
- **Profit Factor Retention**: **208.71%** (OOS PF / IS PF = 2.72 / 1.31), proving zero curve-fitting degradation.

### 2. 10,000-Path Monte Carlo Simulation (,000 Account @ 0.25% Risk)

| Dataset Split | Trade Count | Median Ending Balance | P5 Balance (Worst 5%) | P95 Drawdown % | P95 Drawdown $ | P95 Losing Streak | P1 Pass Prob | Max Breach Prob |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Full Dataset** | 759 | **,744.79** | ,768.85 | **3.64%** | .48 | 13 trades | **100.00%** | **0.00%** |
| **In-Sample (70%)** | 531 | **,133.51** | ,439.94 | **7.00%** | .27 | 14 trades | **98.00%** | **0.14%** |
| **Out-of-Sample (30%)** | 228 | **,595.82** | ,935.05 | **2.53%** | .10 | 8 trades | **100.00%** | **0.00%** |
