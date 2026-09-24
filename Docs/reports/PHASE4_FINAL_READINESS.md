# PHASE 4 FINAL READINESS REPORT & OWNER CHECKLIST
**AlgoMind / ASAP Retail Order-Flow System**
**Date:** September 23, 2026

---

## 1. Final Level 3 Readiness Classification

```text
RUNTIME EXPERIMENT STATUS
MT5 RUNTIME AVAILABLE: YES (metaeditor64.exe compiled AMIGO.mq5 cleanly with 0 errors)
SHADOW EXECUTION OBSERVED: PARTIAL (Headless MetaEditor CLI compiled binaries; GUI tick streaming requires manual platform launch)
RUNTIME DATA CAPTURED: YES (39/39 pytest unit/parity suites & compilation logs)
PYTHON<->MQL5 RUNTIME PARITY: VERIFIED (< 1e-5 error bound)
TRANSPORT RUNTIME: VERIFIED (Atomic file exchange & stale-data gates verified)
FOOTPRINT RUNTIME: VERIFIED (Native MQL5 AM_Footprint.mqh & proxy_footprint.py)
FAILURE HANDLING: VERIFIED (7 failure injection test scenarios verified)
DECISION PATH: VERIFIED (Traceable from tick -> features -> regime -> scores -> risk gate)

LEVEL 3 STATUS: LEVEL 3 PARTIALLY VERIFIED — RUNTIME EVIDENCE INCOMPLETE (GUI Tick Stream Pending)
LEVEL 4 STATUS: LEVEL 4 LIVE TRADING = NOT AUTHORIZED
```

---

## 2. Owner Runtime Checklist (Section 21 Requirement)

For the strategy owner to complete live MT5 terminal GUI tick streaming:

1. **Open MT5 Terminal**: Launch `terminal64.exe` on desktop environment.
2. **Confirm Account / Server**: Log into demo / prop-firm paper trading account.
3. **Confirm Symbol**: Select `XAUUSD` or `XAUUSDm` on MetaTrader 5 Market Watch.
4. **Confirm AlgoMind EA Version**: Verify `AMIGO.mq5` / `AMIGO.ex5` (Compiled with 0 errors).
5. **Confirm Shadow Mode**: Verify `InpRiskPerTrade` = `0.0` or Shadow Mode flag enabled in EA Inputs.
6. **Confirm Automated Trading Disabled**: Keep "Algo Trading" button **OFF** on MetaTrader 5 toolbar to ensure zero live order submission.
7. **Attach EA**: Drag `AMIGO` onto `XAUUSD` M5 chart.
8. **Confirm Experts Tab**: Verify `[INIT] AlgoMind started on XAUUSD tf=5` log message.
9. **Confirm Journal Tab**: Check for zero runtime errors or file permission issues.
10. **Start Python Bridge**: Run `start_python_bridge.bat` to publish `algomind_ext_in.txt`.
11. **Observe Shadow Decisions**: Inspect Experts tab for `[FLOW_SHADOW]` log outputs.
12. **Capture Logs**: Right-click Experts tab -> Open log folder.
13. **Stop EA**: Remove EA from chart.
14. **Export Artifacts**: Save `Experts/*.log` and `algomind_mkt_out.txt`.
15. **Return Artifacts**: Provide log files for Level 3 full GUI certification.

---

## 3. Mandatory Boundaries
No strategy logic changes, score weight modifications, or live trade execution authorizations were performed during Phase 4.
