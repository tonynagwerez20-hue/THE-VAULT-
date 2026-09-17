# ALGOMIND OOS-LIVE FORENSIC AUDIT

## What "100% Parity" Actually Means

### Definition Used
The previous report's "100% signal identity" refers to definition **(F)**: identical strategy decisions
**before** account constraints are applied. The AMIGO strategy generates the same 759 qualified trade signals
regardless of account size.

### What It Does NOT Mean

| Property | Same Across Accounts? | Reason |
|:---------|:----------------------|:-------|
| Signal generation | ✅ YES | No account-dependent logic in strategy |
| Signal timestamps | ✅ YES | Same historical data |
| Entry prices | ✅ YES | Same historical fills |
| Lot sizes | ❌ NO | Lot sizing depends on equity |
| Trades executed | ❌ NO | Margin rejections differ |
| Trade outcomes (PnL) | ❌ NO | PnL scales with lot size |
| Drawdown profile | ❌ NO | Equity curves diverge |

### Corrected Statement
> "Strategy signal generation is 100% account-independent. Execution outcomes differ due to margin,
> minimum lot, and equity-dependent position sizing constraints."

## Account-Dependent Logic Audit

### Code Searched
1. `MQL5/Include/Strategy Engine.mqh` — Score calculation: **NO account dependency**
2. `MQL5/Include/Regime Engine.mqh` — Regime detection: **NO account dependency**
3. `MQL5/Include/Risk Engine.mqh` — Position sizing: **Uses equity for sizing only**
4. `Python/run_parity_pipeline.py` — Parity engine: **Balance used only for sizing/margin**
5. `Python/algomind_monte_carlo.py` — MC engine: **Equity scales risk, not signals**

### Finding
No hidden account-dependent logic was found in strategy signal generation, regime detection,
or trade scoring. Account size affects **only**: lot sizing, margin availability, and risk gates.

## Data Leakage Audit

| Check | Result |
|:------|:-------|
| Future price data in signals | NOT FOUND |
| Future bar data | NOT FOUND |
| Future spread/volatility | NOT FOUND |
| OOS results influencing IS parameters | NOT FOUND |
| MC results influencing configuration | NOT FOUND |
| Normalization using future data | NOT FOUND |

**DATA LEAKAGE: NOT FOUND**

## Monte Carlo Methodology Comparison

| Property | algomind_monte_carlo.py | run_parity_pipeline.py MC | Phase 11 Audit MC |
|:---------|:------------------------|:--------------------------|:------------------|
| Data source | Synthetic (assumed win rates) | Historical PnLs (759 trades) | Historical PnLs (759 trades) |
| Sampling | Binomial win/loss | Bootstrap w/ replacement | Bootstrap w/ replacement |
| Lot sizing | Perfect fractional | Static from initial balance | **Dynamic from current equity** |
| Margin check | None | Static initial check | **Dynamic per-trade** |
| Lot rounding | None | Min lot enforcement | **Min lot enforcement** |
| Compounding | Geometric (fractional) | Linear (static lots) | **Geometric (dynamic lots)** |
| Spread/slippage | None | None | None |
| Paths | 10,000 | 10,000 | 10,000 |
| Seed | 42 | 42 | 42 |

> [!IMPORTANT]
> The previous Monte Carlo implementations do **NOT** model small-account execution constraints.
> `algomind_monte_carlo.py` uses synthetic outcomes with no lot constraints.
> `run_parity_pipeline.py` uses static lot sizing computed once from the initial balance.
> Only the Phase 11 audit MC correctly models dynamic equity-based lot sizing with per-trade margin checks.
