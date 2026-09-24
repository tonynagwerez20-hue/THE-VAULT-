# AlgoMind / ASAP — GAP-01 Implementation Report: Classical Price ↔ Proxy-CVD Divergence

## Executive Summary
This report documents the implementation and verification of **GAP-01 (Classical Price ↔ Proxy-CVD Swing Divergence)** within the AlgoMind production codebase (`MQL5/Include/`). GAP-01 completes the Mean-Reversion strategy evidence calculation by replacing the previous `0.0` placeholder with a mathematically rigorous, normalized divergence score ($0.0 \to 1.0$).

---

## 1. Implementation Details

### 1.1 Structural Features (`Contracts header.mqh` & `FeatureVector.mqh`)
In `Contracts header.mqh`, `FeatureSnapshot` was extended with:
```mql5
double delta_divergence; // GAP-01: Classical price vs proxy CVD divergence score [0,1]
```

In `FeatureVector.mqh`, the divergence calculation engine was implemented via `ComputeDeltaDivergence()`:
* **Inputs**: Confirmed swing highs and lows from `Structure Engine.mqh` ($k=2$ bar confirmation) and cumulative proxy volume delta (`histA` array).
* **Bearish Divergence** (Price Higher High $P_2 > P_1$, CVD Lower High $\text{CVD}_2 < \text{CVD}_1$):
  $$\text{div\_score} = \text{Clip01}\left(\frac{\frac{P_2 - P_1}{\text{ATR}} + \frac{\text{CVD}_1 - \text{CVD}_2}{\text{ATR}_{\text{CVD}}}}{2.0}\right)$$
* **Bullish Divergence** (Price Lower Low $P_2 < P_1$, CVD Higher Low $\text{CVD}_2 > \text{CVD}_1$):
  $$\text{div\_score} = \text{Clip01}\left(\frac{\frac{P_1 - P_2}{\text{ATR}} + \frac{\text{CVD}_2 - \text{CVD}_1}{\text{ATR}_{\text{CVD}}}}{2.0}\right)$$
* **Missing Data / Fallback**: Returns `0.0` if swing points or CVD history are insufficient.

### 1.2 Evidence Integration (`Strategy Engine.mqh`)
In `MR_Evidence()` within `Strategy Engine.mqh`:
```mql5
// Line 37 in Strategy Engine.mqh
double div_score = f.delta_divergence;
```
The score is weighted at $20\%$ of the overall `MR_Evidence()` formula:
$$\text{MR\_Evidence} = 0.40 \cdot \text{stretch\_score} + 0.25 \cdot \text{rej\_score} + 0.20 \cdot \text{div\_score} + 0.15 \cdot \text{ret\_val}$$

---

## 2. Verification & Safety Controls

1. **Compilation Verification**: Compiled via `MetaEditor64.exe` into `AMIGO.ex5`. Resulted in **0 errors**, **13 audit warnings**.
2. **Account Invariance**: The divergence score is computed strictly from market price action and proxy order-flow data before any risk sizing or account check. It produces identical values across all account sizes ($5 to $100,000+).
3. **Safety / Shadow Mode**: Execution gates remain strictly governed by `InpShadowOnly = true`. No real trades are executed.
