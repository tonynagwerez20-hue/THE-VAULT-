# AMIGO — Economic Validation Report

## 1. Governance & Anti-Deception Statement

> [!CAUTION]
> **Zero Theoretical Assumptions / Zero Overfitting Claims**
> It is an ethical and engineering violation to claim profitability, positive expectancy, or increased Sharpe ratio without executing a statistically valid, multi-regime historical backtest on clean broker tick data.
> Because native MetaTrader 5 backtesting is currently blocked by the safety isolation mandate (**BLK-001**), **all economic performance figures remain formally UNVERIFIED**.

---

## 2. Comparative Structural Hypotheses

While empirical profitability cannot be claimed without live tick backtesting, the structural improvements address the mathematical causes of past losses:

| Parameter | Older Baseline Bot | Upgraded Multi-Timeframe Bot | Economic Impact Hypothesis |
| :--- | :--- | :--- | :--- |
| **False Trend Entries** | Frequently bought M5 peaks inside H4 downtrends | Blocked by HTF directional weight & alignment score | Eliminates low-probability countertrend traps |
| **Scalp Holding Risk** | Scalp trades held indefinitely, turning into losers | 3600-second maximum hold time | Cuts decaying trades; frees account margin |
| **Intraday Overnight Risk**| Carried intraday trades across rollover spread spike | Mandatory liquidation at `session_end_hour` | Eliminates swap fees and rollover slippage |
| **Swing Premature Stop-Out**| Swing trades stopped out by local M5 market noise | Stop anchored to H4 structural swings | Prevents premature liquidation on normal noise |
| **Monetary Risk Consistency**| Uncontrolled stop-distance distortion | Scaled by `AccountExecutionEvaluate()` | Constant risk percentage across all horizons |

---

## 3. Validation Roadmap Once Terminal Isolation is Resolved

Once operating system firewall isolation is verified and authorized:
1. **In-Sample Period**: 2026.01.01 to 2026.04.01 (`XAUUSDm` M5, Every Tick).
2. **Out-of-Sample Period**: 2026.04.01 to 2026.06.01.
3. **Statistical Metrics to Compute**:
   - Deflated Sharpe Ratio (DSR)
   - Probability of Backtest Overfitting (PBO)
   - Maximum Adverse Excursion (MAE) vs Maximum Favourable Excursion (MFE)
   - Performance attribution broken down by Regime, Strategy, and Horizon.

**Current Disposition**: **ECONOMIC VALIDATION UNVERIFIED (PENDING AUTHORIZED OFFLINE BACKTEST)**.
