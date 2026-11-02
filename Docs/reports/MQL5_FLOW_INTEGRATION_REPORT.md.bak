# MQL5 NATIVE FLOW INTEGRATION REPORT
**AlgoMind / ASAP Retail Order-Flow Project**

## 1. Architecture Overview
The MQL5 order-flow feature set is structured as lightweight, modular include headers (`.mqh`) designed to update state incrementally on every tick:

- `AM_FlowQuality.mqh`: Provenance tags and fail-closed quality checks.
- `AM_ProxyVWAP.mqh`: Incremental Proxy VWAP and deviation calculator.
- `AM_ActivityProfile.mqh`: Price-bin histogram maintaining POC, VAH, VAL.
- `AM_Footprint.mqh`: Tick-rule classification and footprint pressure.
- `AM_FlowPressure.mqh`: Pressure state machine, hysteresis, and flips.
- `AM_FlowEvents.mqh`: Multi-bar event detection (Persistence, Divergence).
- `AM_ProxyDOM.mqh`: Activity-at-price ladder & broker depth integration.

## 2. Zero External Runtime Dependency
The MQL5 implementation operates 100% natively inside MetaTrader 5 without requiring Python, DLLs, socket connections, or external API calls during live trading.
