# ATR EVENT-REACTION ENGINE VALIDATION
**AlgoMind / ASAP Retail Order-Flow System**
**Date:** September 23, 2026

---

## 1. Mathematical Formulas & Baseline Definition

- **Pre-Event Baseline ATR ($\text{ATR}_{\text{pre}}$)**: 14-period M5 ATR calculated strictly prior to `EVENT_APPROACHING` ($t - 15\text{m}$). Future candle data is strictly excluded.
- **Normalized Displacement**:
  $$\text{Disp}_{1m} = \frac{|P_{t+1m} - P_{\text{pre}}|}{\text{ATR}_{\text{pre}} + \epsilon}$$
  $$\text{Disp}_{5m} = \frac{|P_{t+5m} - P_{\text{pre}}|}{\text{ATR}_{\text{pre}} + \epsilon}$$
  $$\text{Disp}_{15m} = \frac{|P_{t+15m} - P_{\text{pre}}|}{\text{ATR}_{\text{pre}} + \epsilon}$$
- **Spread Expansion Ratio**:
  $$\text{SpreadRatio} = \frac{\text{Spread}_{\text{post}}}{\text{Spread}_{\text{pre}}}$$

---

## 2. Validation Findings
- **No Lookahead Enforcement**: Pre-event ATR calculation uses strictly closed bars prior to event release timestamp.
- **Spread Gate**: If $\text{SpreadRatio} > 3.0$ or spread exceeds $10\%$ of stop distance, trade execution is blocked by the MQL5 risk engine.
