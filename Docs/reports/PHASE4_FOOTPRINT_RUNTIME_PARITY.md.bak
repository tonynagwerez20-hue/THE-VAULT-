# PHASE 4 FOOTPRINT RUNTIME PARITY REPORT
**AlgoMind / ASAP Retail Order-Flow System**
**Date:** September 23, 2026

---

## 1. Sequence-Level Parity Comparison
Deterministic tick sequences were processed through Python `orderflow_lab` and native MQL5 `AM_*.mqh` includes:

```text
Tick Index | Price   | Vol | Py Delta | MQL Delta | Diff | Py Pressure | MQL Pressure | Diff | Py CD | MQL CD | Diff
------------------------------------------------------------------------------------------------------------------
0          | 2000.10 | 2.0 | +2.00000 | +2.00000  | 0.0  | +1.000000   | +1.000000    | 0.0  | +2.0  | +2.0   | 0.0
1          | 2000.20 | 5.0 | +5.00000 | +5.00000  | 0.0  | +1.000000   | +1.000000    | 0.0  | +7.0  | +7.0   | 0.0
2          | 2000.15 | 3.0 | -3.00000 | -3.00000  | 0.0  | +0.400000   | +0.400000    | 0.0  | +4.0  | +4.0   | 0.0
3          | 2000.30 | 10.0| +10.00000| +10.00000 | 0.0  | +0.700000   | +0.700000    | 0.0  | +14.0 | +14.0  | 0.0
```

---

## 2. Parity Test Execution Summary
- **Calculations Evaluated**: Proxy VWAP, Footprint Pressure, POC, VAH, VAL, Cumulative Delta.
- **Max Error Bound**: $< 10^{-5}$
- **Pytest Result**: 9/9 PASSED
- **MQL5 Compilation**: 0 errors via `metaeditor64.exe`
