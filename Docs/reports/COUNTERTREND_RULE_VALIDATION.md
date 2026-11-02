# AMIGO — Countertrend Rule Validation & Microstructure Proof

## 1. Technical Audit of the Countertrend Criteria

The upgraded regime and strategy specifications require three conditions for countertrend mean-reversion eligibility:
1. **Liquidity Sweep Rejection (`sweep_reject`)**
2. **Orderflow Delta Divergence (`delta_divergence`)**
3. **Volatility Extension ($\ge 1.5 \text{ ATR}_{14}$)**

---

## 2. In-Depth Calculation & Provenance Trace

### A. Liquidity Sweep Rejection (`sweep_reject`)
- **Location**: `Structure Engine.mqh:111-125` & `FeatureVector.mqh:108`.
- **Mathematical Formula**:
  - `bull_sweep = (low < last_swing_low) && (close > last_swing_low)`
  - `bear_sweep = (high > last_swing_high) && (close < last_swing_high)`
  - `sweep_reject = bull_sweep || bear_sweep`
- **Microstructure Basis**: Captures the classic "turtle soup" / stop-run pattern where aggressive market orders break a key swing level to trigger stops, but liquidity providers absorb the volume, forcing price to close back inside the prior trading range.
- **Data Source**: Derived directly from closed OHLC bars (`MqlRates`).

### B. Orderflow Delta Divergence (`delta_divergence`)
- **Location**: `FeatureVector.mqh:112-150`.
- **Mathematical Formula**:
  - Identifies two consecutive confirmed swing highs ($p_1, p_2$) or swing lows ($p_1, p_2$) within 20 bars.
  - Compares price change against tick-volume proxy CVD ($d_1, d_2$ from `OrderFlow.mqh` tick-delta accumulator):
    $$\text{div\_bear} = \text{Clip01}\left(\frac{(p_2 - p_1)/\text{ATR} + (d_1 - d_2)}{2.0}\right) \quad \text{when } p_2 > p_1 \text{ and } d_2 < d_1$$
    $$\text{div\_bull} = \text{Clip01}\left(\frac{(p_1 - p_2)/\text{ATR} + (d_2 - d_1)}{2.0}\right) \quad \text{when } p_2 < p_1 \text{ and } d_2 > d_1$$
- **Proxy Provenance Warning**:
  - In MetaTrader 5 retail forex/CFD feeds, **exchange order flow depth (DOM) is unavailable**.
  - `histA` is accumulated from MT5 tick volume updates (`Volume / Tick Count`) using the tick rule (uptick = buy volume, downtick = sell volume).
  - **Verdict**: This is a **Proxy-CVD (Cumulative Volume Delta) Indicator**, not an exchange-cleared CME order-flow feed. It is properly labelled as a proxy in code, preventing false claims of institutional DOM insight.

### C. Volatility Extension ($\ge 1.5 \text{ ATR}_{14}$)
- **Location**: `Regime Engine.mqh:81` (`ext = (MathAbs(f.dev_vwap_atr) >= 1.5) ? 1.0 : 0.0`).
- **Mathematical Meaning**: Price must be displaced from Session VWAP by at least $1.5 \times \text{ATR}_{14}$.
- **Adversarial Assessment**:
  - Is 1.5 ATR arbitrary? **Yes**. In standard statistical finance, mean reversion is typically parameterized by a Z-score ($\ge 2.0$ standard deviations) rather than an arbitrary 1.5 ATR scalar.
  - While $1.5 \text{ ATR}$ provides a reasonable heuristic filter against fading narrow consolidations, its profitability has **not been optimized or validated on out-of-sample Gold tick history**.
  - **Classification**: **HEURISTIC-ONLY (UNVERIFIED EMPIRICAL EDGE)**.
