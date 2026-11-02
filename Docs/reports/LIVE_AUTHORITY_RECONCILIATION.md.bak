# LIVE AUTHORITY RECONCILIATION REPORT
**AlgoMind / ASAP Retail Order-Flow System**
**Date:** September 23, 2026

---

## 1. MQL5 Sole Execution Authority Confirmation
Audit of `MQL5/Experts/AMIGO.mq5` and `MQL5/Include/Execution Engine.mqh` confirms:

- **Order Submission**: All trade commands originate exclusively inside MQL5 via `OrderSend()` / `OrderSendAsync()`.
- **Pre-Trade Checks**: Hard pre-trade checks (`OrderCheck`) validate account free margin, leverage, volume step, stop level, freeze level, and maximum allowed drawdown ($5\%$).
- **No Python Execution Authority**: Python publishes external context (`ExternalContext`); Python is strictly incapable of issuing live orders or overriding MQL5 risk gates.

---

## 2. Hard Risk Control Verification

| Risk Control | Threshold | Enforcement Location | Status Label |
| :--- | :--- | :--- | :--- |
| **Max Risk Per Trade** | $0.5\%$ Equity | `Risk Engine.mqh:CheckRiskLimits` | `IMPLEMENTED AND VERIFIED` |
| **Daily Loss Limit** | $2.0\%$ Equity | `Risk Engine.mqh:CheckRiskLimits` | `IMPLEMENTED AND VERIFIED` |
| **Total Drawdown Limit**| $5.0\%$ Hard Lock | `Risk Engine.mqh:CheckRiskLimits` | `IMPLEMENTED AND VERIFIED` |
| **Minimum Stop Level** | Broker `SYMBOL_TRADE_STOPS_LEVEL` | `Risk Engine.mqh:ValidateStopLoss` | `IMPLEMENTED AND VERIFIED` |
| **Spread Gate** | $\le 10\%$ Stop Distance | `Strategy Engine.mqh:Decide` | `IMPLEMENTED AND VERIFIED` |
| **Zero Martingale Policy**| Round-down if lot $< 0.01$; NO trade | `Risk Engine.mqh:CalculateLotSize` | `IMPLEMENTED AND VERIFIED` |
