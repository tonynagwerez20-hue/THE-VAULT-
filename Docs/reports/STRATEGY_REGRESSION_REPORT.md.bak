# STRATEGY REGRESSION REPORT
**AlgoMind / ASAP Retail Order-Flow System**
**Date:** September 23, 2026

---

## 1. Strategy Preservation Audit
Audit confirms that the core validated strategy logic inside `Strategy Engine.mqh` and `Regime Engine.mqh` remains 100% preserved and un-altered:

- **Mean Reversion Scoring (`MR_Evidence`)**: Evaluates VWAP stretch, sweep rejection, and value state. Unchanged.
- **Continuation Scoring (`ContinuationEvidence`)**: Evaluates structure direction, acceptance, pressure, and volume ratio. Unchanged.
- **Regime Thresholds**: Regime transition threshold ($0.60$), hysteresis ($0.10$), persistence ($2$ bars). Unchanged.
- **Hard Risk Limits**: Trade risk ($0.5\%$), Daily loss ($2.0\%$), Total drawdown ($5.0\%$). Unchanged.

---

## 2. Shadow-Mode Isolation
All new order-flow features (footprint-derived delta, cumulative delta, news reconciliation, event reaction) execute initially in **Shadow Mode**, producing telemetry logs (`[FLOW_SHADOW]`) without modifying live trade intents or score thresholds.
