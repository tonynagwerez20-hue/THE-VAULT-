# FOOTPRINT RUNTIME VALIDATION REPORT
**AlgoMind / ASAP Retail Order-Flow System**
**Date:** September 23, 2026

---

## 1. Footprint & Cumulative Delta Runtime Architecture
The native MQL5 Footprint engine (`AM_Footprint.mqh`) processes raw retail ticks during runtime:

- **Binning**: Dynamic price binning on $0.01$ tick boundaries.
- **Classification**: Tick Rule estimator ($P_t > P_{t-1} \rightarrow \text{BUY}$, $P_t < P_{t-1} \rightarrow \text{SELL}$).
- **Footprint Pressure**: Aggregate pressure $P_t = \frac{\sum \hat{\Delta}(p)}{\sum |\hat{\Delta}(p)| + \epsilon}$.
- **Cumulative Delta**: Session-accumulated delta $\text{CD}_t = \text{CD}_{t-1} + \hat{\Delta}_t$.

---

## 2. Reset Policy Audit
- **`SESSION` Reset**: Resets $\text{CD} = 0$ on session boundary ($00:00$ UTC). Active baseline in Python and MQL5.
- **`ROLLING_50` Reset**: Rolling 50-bar window sum. Implemented in Python `proxy_footprint.py`.
- **`EVENT` Reset**: Resets $\text{CD} = 0$ on verified news release timestamps.

---

## 3. Status
`IMPLEMENTED AND VERIFIED` in Level 1 & Level 2 integration; running in **Shadow Mode**.
