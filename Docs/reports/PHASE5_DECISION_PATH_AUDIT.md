# PHASE 5 — DECISION PATH AUDIT & INFLUENCE MATRIX

**Document Status**: Authoritative Engineering Audit  
**Date**: 24 September 2026  
**System**: AlgoMind / ASAP Retail Order-Flow System  

---

## 1. Decision-Path Architecture & Influence Matrix

This document maps every component in the system to determine whether it is actively connected to the authoritative MQL5 trade decision path (`Decide()`) or operates strictly as shadow/observational telemetry.

| Component | Produced in Runtime? | Logged in Runtime? | Consumed by Decision Path? | Influences Regime? | Influences Strategy Score? | Influences Risk Gate? | Influences Final Action? | Classification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **MT5 Price Ticks / Bar Rates** | YES | YES | YES | YES | YES | YES | YES | `IMPLEMENTED AND VERIFIED` |
| **Legacy Delta A & B (`OrderFlow.mqh`)** | YES | YES | YES | YES (`fusion`) | YES (`pressure`) | NO | YES | `IMPLEMENTED AND VERIFIED` |
| **Structure Engine (BOS/ChoCh/Swings)** | YES | YES | YES | YES | YES | YES (`sl`) | YES | `IMPLEMENTED AND VERIFIED` |
| **External Context (`algomind_ext_in.txt`)**| YES | YES | YES | NO | YES (`cftc`/`options`) | YES (`DQ_STALE`) | YES | `IMPLEMENTED AND VERIFIED` |
| **Proxy Footprint (`CAM_Footprint`)** | YES (In Code) | PENDING | NO | NO | NO | NO | NO | `IMPLEMENTED BUT NOT CONNECTED` |
| **Cumulative Delta (`GetCumulativeDelta`)**| YES (In Code) | PENDING | NO | NO | NO | NO | NO | `IMPLEMENTED BUT NOT CONNECTED` |
| **Proxy VWAP (`CAM_ProxyVWAP`)** | YES (In Code) | PENDING | NO | NO | NO | NO | NO | `IMPLEMENTED BUT NOT CONNECTED` |
| **Activity Profile (`CAM_ActivityProfile`)**| YES (In Code) | PENDING | NO | NO | NO | NO | NO | `IMPLEMENTED BUT NOT CONNECTED` |
| **Flow Pressure (`CAM_FlowPressure`)** | YES (In Code) | PENDING | NO | NO | NO | NO | NO | `IMPLEMENTED BUT NOT CONNECTED` |
| **Flow Events (`CAM_FlowEvents`)** | YES (In Code) | PENDING | NO | NO | NO | NO | NO | `IMPLEMENTED BUT NOT CONNECTED` |
| **News Reconciliation Engine** | YES (Python) | NO (MT5) | NO | NO | NO | NO | NO | `IMPLEMENTED BUT NOT CONNECTED` |
| **ATR Event Reaction Engine** | YES (Python) | NO (MT5) | NO | NO | NO | NO | NO | `IMPLEMENTED BUT NOT CONNECTED` |
| **Shadow Execution Gate (`InpShadowOnly`)**| YES | PENDING | YES | NO | NO | YES (Execution) | YES (Blocks `OrderSend`) | `IMPLEMENTED AND VERIFIED` |

---

## 2. Key Architecture Findings

1. **New Order-Flow Engines are SHADOW ONLY**: `AM_Footprint`, `AM_ProxyVWAP`, `AM_ActivityProfile`, `AM_FlowPressure`, and `AM_FlowEvents` execute calculations and publish `[FLOW_DIAG]` logs, but their outputs do **NOT** enter `FeatureSnapshot` or modify `ScoreStrategies()` or `EvaluateRegime()`.
2. **Legacy Delta Retains Live Scoring Authority**: Strategy scoring (`MR_Evidence` and `ContinuationEvidence`) is driven strictly by `f.fusion`, `f.dev_vwap_atr`, `f.structure_dir`, `f.bull_flip`, `f.bear_flip`, and `f.surge`, which are populated by `BuildFeatureVector()` using `OrderFlow.mqh`.
3. **Fail-Closed Safety**: Any disconnect, staleness, or missing file in the external context immediately triggers `DQ_STALE_EXTERNAL` or `DQ_FATAL`, causing `Decide()` to return `ACTION_NO_TRADE` or `ACTION_WAIT`.
