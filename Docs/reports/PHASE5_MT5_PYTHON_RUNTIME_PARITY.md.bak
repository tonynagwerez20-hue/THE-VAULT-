# PHASE 5 — MT5 ↔ PYTHON RUNTIME PARITY REPORT

**Document Status**: Authoritative Engineering Audit  
**Date**: 24 September 2026  
**System**: AlgoMind / ASAP Retail Order-Flow System  

---

## 1. Parity Evaluation Standard

Per Phase 5 Governance Rule 8, runtime parity between Python (`algomind/orderflow_lab`) and MQL5 (`AM_*.mqh`) cannot be verified using pure Python unit tests or mock simulators alone. Verification requires:
1. Capturing a shared sequence of live market ticks simultaneously in MT5 and Python.
2. Comparing tick classification, price binning, footprint pressure, VWAP, and cumulative delta step-by-step.
3. Quantifying mathematical divergence against strict tolerances ($< 10^{-5}$).

---

## 2. Current Parity Verification Status

```
===================================================================
PYTHON <-> MQL5 RUNTIME PARITY: UNVERIFIED (Awaiting Shared Live Trace)
===================================================================
```

### Analytical Breakdown

| Metric / Engine | Python Engine | MQL5 Class | Theoretical Parity | Shared Runtime Verification |
| :--- | :--- | :--- | :--- | :--- |
| **Tick Rule Classifier** | `proxy_footprint.py` | `CAM_Footprint::AddTick` | Identical Math | `UNVERIFIED` |
| **Footprint Pressure** | `proxy_footprint.py` | `CAM_Footprint::CalculateFootprintPressure` | Identical Math | `UNVERIFIED` |
| **Cumulative Delta** | `proxy_footprint.py` | `CAM_Footprint::GetCumulativeDelta` | Identical Math | `UNVERIFIED` |
| **Incremental VWAP** | `proxy_vwap.py` | `CAM_ProxyVWAP::GetVWAP` | Identical Math | `UNVERIFIED` |
| **Profile POC / VAH / VAL**| `activity_profile.py` | `CAM_ActivityProfile::Compute` | Identical 70% VA | `UNVERIFIED` |

---

## 3. Recommended Action for Empirical Verification

To establish Level 3 verified runtime parity:
1. Run `start_python_bridge.bat` while MT5 is running with the updated `AMIGO.ex5`.
2. Allow both systems to record 100 consecutive M5 ticks on `XAUUSD`.
3. Compare the generated `python_features.jsonl` log against the `[FLOW_DIAG]` entries from the MT5 Experts log using a dedicated script `compare_runtime_parity.py`.
