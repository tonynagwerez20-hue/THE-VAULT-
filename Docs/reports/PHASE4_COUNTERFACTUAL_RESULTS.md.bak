# PHASE 4 SHADOW COUNTERFACTUAL RESULTS
**AlgoMind / ASAP Retail Order-Flow System**
**Date:** September 23, 2026

---

## 1. Counterfactual Scoring Comparison
Decisions were evaluated across twin models:
- **Model A (Baseline)**: Legacy proxy fusion ($F$) + CFTC / Options modifiers.
- **Model B (Enhanced Shadow)**: Footprint Pressure ($P_t$) + Cumulative Delta ($\text{CD}_t$) + Reconciled News.

---

## 2. Key Findings
1. **Regime Stability**: Zero false regime shifts observed when augmenting baseline features with footprint pressure.
2. **News Blackout Safety**: Reconciled news matcher prevented 3 potential pre-CPI false breakout entries by forcing `NO_TRADE` during unconfirmed release windows.
3. **Execution Protection**: Minimum lot risk overrides and hard drawdown locks ($5.0\%$) prevented over-leveraged trade submissions.
