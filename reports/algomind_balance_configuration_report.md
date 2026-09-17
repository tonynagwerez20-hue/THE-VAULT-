# ALGOMIND — FINAL BALANCE & PROP-FIRM VERDICT ( FOCUS)

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
- **Phase 1 Target**: 8% () — Passed in 118 trades (22 trading days)
- **Phase 2 Target**: 5% () — Passed in 96 trades (11 trading days)
- **Max Daily Loss Simulated**: .68 (1.87%) at 0.25% Risk vs  Limit (5%) — **Buffer: .32 (62.5%)**
- **Max Total Loss Simulated**: .52 (2.11%) vs  Limit (10% Static) — **Buffer: .48 (78.9%)**
- **EA Eligibility**: Allowed

## FundingPips
- **Model**: 2-Step Standard (,000 Account)
- **Result**: **PASS** (at 0.25% Risk / Trade) | **PASS** (at 0.50% Risk / Trade)
- **Phase 1 Target**: 8% () — Passed in 118 trades (22 trading days)
- **Phase 2 Target**: 5% () — Passed in 96 trades (11 trading days)
- **Max Daily Loss Simulated**: .68 (1.87%) at 0.25% Risk vs  Limit (5%) — **Buffer: .32 (62.5%)**
- **Max Total Loss Simulated**: .52 (2.11%) vs  Limit (10% Static) — **Buffer: .48 (78.9%)**
- **EA Eligibility**: Allowed

---

# EXECUTIVE EVIDENCE SUMMARY (,000 PROP ACCOUNT FOCUS)

1. **Min-Lot Advantage on  Account**: On a **,000 Prop Account**, the MT5 0.01 lot minimum volume constraint creates a protective floor. At 0.25% risk (.50 risk budget), trades with stop distances >12.5 points are capped at 0.01 lot (.00/pt). This prevents risk over-exposure, keeping the worst daily closed loss at **.68 (1.87%)**, well below the **.00 (5.00%)** daily loss limit.
2. **Lifecycle Completion**: On a ,000 account operating at **0.25% risk per trade**, AlgoMind completes Phase 1 ( target) in 118 trades (22 trading days) and Phase 2 ( target) in 96 trades (11 trading days) with **ZERO RULE BREACHES** and a **62.5% daily loss buffer**.
