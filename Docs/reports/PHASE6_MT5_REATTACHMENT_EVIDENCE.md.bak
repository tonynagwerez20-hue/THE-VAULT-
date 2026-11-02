# PHASE 6 — MT5 REATTACHMENT & INITIALIZATION EVIDENCE REPORT

**Document Status**: Authoritative Engineering Audit  
**Date**: 24 September 2026  
**System**: AlgoMind / ASAP Retail Order-Flow System  
**Repository**: `C:\Users\USER\Desktop\ALGOMIND`  
**Classification**: LEVEL 3 UNVERIFIED — MT5 RUNTIME RE-ATTACHMENT PENDING  
**Live Execution Authority**: LEVEL 4 LIVE TRADING = NOT AUTHORIZED  

---

## 1. Executive Summary

Phase 6 evaluates whether the compiled `AMIGO.ex5` binary (built from `AMIGO.mq5` with wired `AM_*.mqh` headers and `InpShadowOnly = true`) has been initialized inside the running MetaTrader 5 terminal GUI.

Inspection of the active MT5 log (`20260924.log`, 1,478,592 bytes as of 07:36:55 AM) confirms that:
- The MT5 terminal process (`terminal64.exe` PID 7964) is running and processing ticks.
- The active chart instance of `AMIGO (XAUUSD, M5)` was last initialized at `00:05:23.845` on 2026-09-24.
- **The updated `AMIGO.ex5` binary (compiled at 07:27:05 AM) has NOT yet been reloaded or reattached by the owner in the MT5 GUI.**

Per Phase 6 Governance Rule 3 and Section 4 ("Initialization Proof"), compilation alone does not constitute runtime verification. Fresh initialization timestamp proof is **PENDING OWNER RE-ATTACHMENT**.

---

## 2. Reattachment Status Matrix

| Audit Item | Expected Value | Observed Runtime Value | Status |
| :--- | :--- | :--- | :--- |
| **MetaEditor Build Time** | `2026-09-24 07:27:05` | File `AMIGO.ex5` (86,210 bytes) | `COMPILED AND DEPLOYED` |
| **Last EA Initialization** | Post-07:27:05 UTC | `2026-09-24 00:05:23.845` | `RE-ATTACHMENT PENDING` |
| **Symbol Display** | `XAUUSD` | `XAUUSD` | `VERIFIED` |
| **Timeframe** | `PERIOD_M5` | `PERIOD_M5` | `VERIFIED` |
| **Shadow Mode Switch** | `InpShadowOnly = true` | `InpShadowOnly = true` (In Code) | `STATICALLY VERIFIED` |
| **FLOW_DIAG Telemetry** | Active in `20260924.log` | Missing (Awaiting EA Reload) | `UNVERIFIED AT RUNTIME` |

---

## 3. Owner Action Required for Re-attachment

To complete Level 3 Runtime Verification:
1. Open the active MT5 window (`terminal64.exe`).
2. Remove the existing `AMIGO` EA from the `XAUUSD, M5` chart.
3. Drag the updated `AMIGO` EA from the Navigator panel onto the `XAUUSD, M5` chart.
4. Confirm `InpShadowOnly = true` in the inputs window and click OK.
5. Verify that `[AlgoMind][INFO][INIT] AlgoMind started on XAUUSD tf=5 ML=OFF` appears in the Experts log with a timestamp after 07:27:05 UTC.
