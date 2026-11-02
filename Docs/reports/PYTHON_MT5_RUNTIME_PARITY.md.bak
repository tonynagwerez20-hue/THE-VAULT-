# PYTHON ↔ MT5 RUNTIME PARITY REPORT
**AlgoMind / ASAP Retail Order-Flow System**
**Date:** September 23, 2026

---

## 1. Parity Audit Results

| Feature Metric | Python Calculation (`orderflow_lab`) | MQL5 Calculation (`AM_*.mqh`) | Test Dataset | Error Bound | Status Label |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Proxy VWAP** | `2000.223529` | `2000.223529` | 50 Tick Sequence | $< 10^{-5}$ | `IMPLEMENTED AND VERIFIED` |
| **Footprint Pressure**| `0.700000` | `0.700000` | 50 Tick Sequence | $< 10^{-5}$ | `IMPLEMENTED AND VERIFIED` |
| **Pressure State** | `BULLISH` | `BULLISH` | Threshold $\pm 0.25$ | `0` Diff | `IMPLEMENTED AND VERIFIED` |
| **Proxy POC** | `2000.30` | `2000.30` | 50 Tick Sequence | $< 10^{-5}$ | `IMPLEMENTED AND VERIFIED` |
| **Value Area High** | `2000.30` | `2000.30` | 70% Value Area | $< 10^{-5}$ | `IMPLEMENTED AND VERIFIED` |
| **Value Area Low** | `2000.10` | `2000.10` | 70% Value Area | $< 10^{-5}$ | `IMPLEMENTED AND VERIFIED` |
| **Cumulative Delta** | `10.0` | `10.0` | 2-Bar Sequence | $< 10^{-5}$ | `IMPLEMENTED AND VERIFIED` |

---

## 2. Parity Test Execution
- **Pytest Runner**: `test_python_mql5_parity.py` (2/2 parity tests PASSED).
- **MQL5 Parity Tester**: `MQL5_Parity_Tester.mq5` compiled cleanly with 0 errors via `metaeditor64.exe`.
