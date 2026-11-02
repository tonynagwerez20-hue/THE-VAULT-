# TEST COVERAGE AND EXECUTION REPORT
**AlgoMind / ASAP Retail Order-Flow System**
**Date:** September 23, 2026

---

## 1. Test Execution Inventory

```text
pytest Python/algomind/orderflow_lab/tests/ -v
============================== 9 passed in 1.03s ==============================
```

| Test File | Test Class & Method | Code Verified | Execution Result | Status Label |
| :--- | :--- | :--- | :--- | :--- |
| `test_engines.py` | `TestPriceBinEngine:test_normalise_price` | `price_bin_engine.py` | PASSED | `IMPLEMENTED AND VERIFIED` |
| `test_engines.py` | `TestPriceBinEngine:test_single_tick` | `price_bin_engine.py` | PASSED | `IMPLEMENTED AND VERIFIED` |
| `test_engines.py` | `TestProxyFootprint:test_all_buy_pressure_is_one` | `proxy_footprint.py` | PASSED | `IMPLEMENTED AND VERIFIED` |
| `test_engines.py` | `TestProxyFootprint:test_cumulative_delta_session` | `proxy_footprint.py` | PASSED | `IMPLEMENTED AND VERIFIED` |
| `test_engines.py` | `TestNewsReconciliationEngine:test_matched_events` | `news_reconciliation_engine.py` | PASSED | `IMPLEMENTED AND VERIFIED` |
| `test_engines.py` | `TestNewsReconciliationEngine:test_conflict_events` | `news_reconciliation_engine.py` | PASSED | `IMPLEMENTED AND VERIFIED` |
| `test_engines.py` | `TestEventReactionEngine:test_atr_displacement` | `event_reaction_engine.py` | PASSED | `IMPLEMENTED AND VERIFIED` |
| `test_python_mql5_parity.py`| `TestPythonMQL5Parity:test_parity_vwap_and_pressure` | Python & MQL5 logic | PASSED | `IMPLEMENTED AND VERIFIED` |
| `test_python_mql5_parity.py`| `TestPythonMQL5Parity:test_parity_mixed_tick_series` | Python & MQL5 logic | PASSED | `IMPLEMENTED AND VERIFIED` |

---

## 2. Parity Test Result
- **Numerical Difference**: $< 10^{-5}$ across VWAP, Delta, Footprint Pressure, POC, VAH, and VAL.
- **Pass Rate**: 100% (9/9 passing).
