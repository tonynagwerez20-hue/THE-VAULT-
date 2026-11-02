# PHASE 5 — CUMULATIVE DELTA VALIDATION REPORT

**Document Status**: Authoritative Engineering Audit  
**Date**: 24 September 2026  
**System**: AlgoMind / ASAP Retail Order-Flow System  

---

## 1. Cumulative Delta Implementation

Cumulative Delta tracks the accumulated net difference between estimated buy volume and estimated sell volume over time:

$$\text{CD}_t = \text{CD}_{t-1} + (\text{Vol}_{\text{buy}} - \text{Vol}_{\text{sell}})$$

In MQL5, Cumulative Delta is calculated incrementally inside `CAM_Footprint::AddTick()` (`AM_Footprint.mqh` lines 103 & 108) and exposed via `GetCumulativeDelta()`.

---

## 2. Reset Scope & Disconnection Verification

Per strict project governance:

1. **Current Reset Scope**: `SESSION` (Resets at session start or via `ResetCumulativeDelta()`).
2. **Strategy Connection Status**: `DISCONNECTED FROM AUTHORITATIVE STRATEGY SCORING`.
3. **Verification**:
   - Inspection of `Strategy Engine.mqh` confirms that `MR_Evidence()` and `ContinuationEvidence()` do **not** reference Cumulative Delta.
   - Strategy scoring uses `f.fusion` (derived from `OrderFlow.mqh` short-window z-scores).
   - Cumulative Delta is logged strictly inside `[FLOW_DIAG]` for shadow observation.

---

## 3. Findings & Owner Decisions Required

| Feature Question | Current State | Required Action | Status |
| :--- | :--- | :--- | :--- |
| Is Cumulative Delta calculated? | YES (`CAM_Footprint`) | Log in `[FLOW_DIAG]` | `IMPLEMENTED AND VERIFIED` |
| Does Cumulative Delta reset? | YES (`ResetCumulativeDelta`) | Confirm reset trigger | `IMPLEMENTED BUT UNVERIFIED AT RUNTIME` |
| Is Cumulative Delta in scoring? | NO | **Do NOT connect without owner sign-off** | `REQUIRES OWNER DECISION (DEC-005)` |
| Which reset scope to standardise?| `SESSION` | Select `SESSION` vs `ROLLING_50` vs `EVENT` | `REQUIRES OWNER DECISION (DEC-002)` |
