# SMALL ACCOUNT PARITY INSPECTION REPORT

## A. Validated Strategy Identification
- **Strategy Name / EA**: AMIGO (AlgoMind Mean-reversion & Order-flow Architecture)
- **Symbol**: XAUUSDm (Gold / USD Micro contract)
- **Timeframe**: M5 (5-Minute)
- **Period Tested**: 2025-10-01 to 2026-08-28 (759 closed positions ground truth)
- **Signal & Entry Logic**: Multi-factor institutional feature assembly (FVG, Orderflow, Liquidity Sweep, Structure State) with ML Gate hook threshold score >= 0.35 (margin 0.05).
- **Exit & Risk Logic**: Fixed ATR-based Stop Loss (stop_dist), Take Profit at ~2.0RR, partial close at 2R, dynamic trailing.
- **Reference Risk Budget**: 0.50% intended risk per trade (.00 reference budget on ,000 initial balance).

## B. Validation Evidence
- **Canonical Dataset**: Python/amigo_position_ledger_759.csv (759 completed positions, 100% deal-reconciled).
- **Full Period Metrics**: Net Profit +,734.11 (+124.47%), Profit Factor 1.80, Win Rate 49.41%, Max Balance DD 11.09% (.83).
- **In-Sample (IS - First 70%)**: 531 trades, Net Profit +,133.77, Profit Factor 1.31, Win Rate 44.07%.
- **Out-of-Sample (OOS - Last 30%)**: 228 trades, Net Profit +,600.34, Profit Factor 2.72, Win Rate 60.96%.
- **OOS PF Retention**: 208.71% (No curve-fitting or edge decay observed).

## C. Architecture & Parity Layer Contract
The validated strategy signal logic is strictly **FROZEN**.
The **OOS-to-Live Parity Layer** sits between the signal generator and execution engine:
1. Calculates exact desired lot size from account equity and risk budget.
2. Applies broker symbol constraints (Min Lot 0.01, Lot Step 0.01, Contract Size 100).
3. Evaluates margin requirements, spread ceilings, and minimum-lot risk distortion.
4. Generates execution audit logs and rejection classifications without altering signal generation.
