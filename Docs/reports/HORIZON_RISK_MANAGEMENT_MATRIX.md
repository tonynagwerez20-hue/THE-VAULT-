# AMIGO — Horizon Risk Management Matrix

## 1. Horizon Differentiation Overview

A trading horizon is not a strategy and not a market regime. It is an **analytical scale and trade lifecycle profile** that governs:
1. The structural timeframe used for stop invalidation.
2. The maximum holding duration and session rollover policy.
3. The break-even progress threshold and trailing ratchet speed.

---

## 2. Complete Horizon Risk & Management Specification

| Management Dimension | SCALPING (`HORIZON_SCALPING`) | INTRADAY (`HORIZON_INTRADAY`) | SWING (`HORIZON_SWING`) |
| :--- | :--- | :--- | :--- |
| **Typical Analytical Timeframe** | M1 / M5 | M5 / M15 / H1 | H1 / H4 / D1 |
| **Stop Invalidation Source** | Local M1/M5 Confirmed Swings | M15/H1 Intermediate Swings | H4/D1 Macro Swing Pivots |
| **Fallback ATR Stop** | $1.0 \times \text{ATR}_{14}$ | $1.5 \times \text{ATR}_{14}$ | $2.5 \times \text{ATR}_{14}$ |
| **Base Monetary Risk %** | Spline-governed (0.50% - 1.00%) | Spline-governed (0.50% - 1.00%) | Spline-governed (0.50% - 1.00%) |
| **Break-Even Progress Target** | **33%** of target distance | **50%** of target distance | **60%** of target distance |
| **Dynamic Trailing Ratchet** | **15%** of favourable profit | **25%** of favourable profit | **35%** of favourable profit |
| **ATR Trailing Multiplier** | $1.0 \times \text{ATR}_{14}$ | $1.5 \times \text{ATR}_{14}$ | $2.5 \times \text{ATR}_{14}$ |
| **Partial Exit Policy** | 1.5R Target (Close 50%) | 2.0R Target (Close 50%) | 2.0R / 3.0R Structural Targets |
| **Holding Duration Limit** | **3600 seconds (1 hour)** | **Intraday Session Boundary** | **Unconstrained (Multi-day)** |
| **Session-End Liquidation** | Exempt (Timer governs) | **Mandatory Close** at `session_end_hour` | **Exempt** (Carried overnight) |
| **Spread Sensitivity Gate** | Max Spread $\le 0.08 \times \text{StopDist}$| Max Spread $\le 0.10 \times \text{StopDist}$| Max Spread $\le 0.15 \times \text{StopDist}$|

---

## 3. Strict Monetary Risk Invariance

> [!IMPORTANT]
> **Equal Monetary Risk Across Disparate Stop Distances**
> A wider swing stop must **never** increase monetary dollar loss.
> Lot sizing is derived by the authoritative `AccountExecutionEvaluate()` formula:
> $$\text{Lots} = \frac{\text{Equity} \times \text{Risk\%}}{\text{StopDistancePoints} \times \text{TickValuePerPoint}}$$
> 
> - If a Scalping trade has a $2.00 Gold stop distance on a $10,000 account risking 0.5% ($50):
>   $$\text{Lots} = \frac{\$50}{200 \text{ pts} \times \$0.10} = 0.25 \text{ lots}$$
> - If a Swing trade has a $10.00 Gold stop distance on the same account risking 0.5% ($50):
>   $$\text{Lots} = \frac{\$50}{1000 \text{ pts} \times \$0.10} = 0.05 \text{ lots}$$
> 
> In both instances, the maximum risk exposure is strictly **$50.00 (0.50%)**.
