# PHASE 6 — FLOW_DIAG TELEMETRY AUDIT REPORT

**Document Status**: Authoritative Engineering Audit  
**Date**: 24 September 2026  
**System**: AlgoMind / ASAP Retail Order-Flow System  

---

## 1. `FLOW_DIAG` Telemetry Code Audit

The `FLOW_DIAG` logging statement in `AMIGO.mq5` (lines 315–319) was audited against all contract specifications:

```cpp
// AMIGO.mq5 lines 315-319
LogMsg(LOG_INFO, "FLOW_DIAG", StringFormat("ts=%s vwap=%.5f dev=%.2f poc=%.5f vah=%.5f val=%.5f cd=%.2f fp_press=%.4f state=%d shadow=%s",
       TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES),
       g_vwap_engine.GetVWAP(), g_vwap_engine.GetDeviation(cur_p, g_feat.atr14),
       g_profile_engine.GetPOC(), g_profile_engine.GetVAH(), g_profile_engine.GetVAL(),
       g_footprint_engine.GetCumulativeDelta(), fp_pressure, (int)p_state, g_cfg.shadow_only ? "TRUE" : "FALSE"));
```

---

## 2. Field Audit & Provenance Verification

| Field | Source Method | Math Specification | Label | Classification |
| :--- | :--- | :--- | :--- | :--- |
| `vwap` | `CAM_ProxyVWAP::GetVWAP()` | $\frac{\Sigma (P \times V)}{\Sigma V}$ | PROXY | `IMPLEMENTED IN CODE` |
| `dev` | `CAM_ProxyVWAP::GetDeviation()` | $\frac{P - \text{VWAP}}{\text{ATR}_{14}}$ | PROXY | `IMPLEMENTED IN CODE` |
| `poc` | `CAM_ActivityProfile::GetPOC()` | Peak activity price bin | PROXY | `IMPLEMENTED IN CODE` |
| `vah` | `CAM_ActivityProfile::GetVAH()` | 70% Value Area High | PROXY | `IMPLEMENTED IN CODE` |
| `val` | `CAM_ActivityProfile::GetVAL()` | 70% Value Area Low | PROXY | `IMPLEMENTED IN CODE` |
| `cd` | `CAM_Footprint::GetCumulativeDelta()` | $\Sigma (\text{Vol}_{\text{buy}} - \text{Vol}_{\text{sell}})$ | PROXY | `IMPLEMENTED IN CODE` |
| `fp_press` | `CAM_Footprint::CalculateFootprintPressure()` | $\frac{\Sigma \delta}{\Sigma |\delta| + \epsilon}$ | PROXY | `IMPLEMENTED IN CODE` |
| `state` | `CAM_FlowPressure::ClassifyState()` | $-1 / 0 / +1$ | PROXY | `IMPLEMENTED IN CODE` |
| `shadow` | `g_cfg.shadow_only` | `true / false` | GATE | `IMPLEMENTED IN CODE` |

---

## 3. Disconnection Guarantee

None of the fields in `FLOW_DIAG` (`vwap`, `poc`, `vah`, `val`, `cd`, `fp_press`) feed into `Strategy Engine.mqh` scoring functions (`MR_Evidence` or `ContinuationEvidence`). They are published purely as shadow telemetry.
