# AMIGO — Horizon Selection & Stop Geometry Report

**Document Date:** 2026-11-02  
**Target Code:** `MQL5/Experts/AMIGO.mq5` (Lines 475–541)  
**Evaluator:** Antigravity Quantitative Trading Systems Engineer  

---

## 1. Horizon Selection Mechanism

In `AMIGO.mq5` lines 475–479, the trading horizon is determined prior to stop-loss geometry:

```mql5
ENUM_HORIZON selected_horizon = HORIZON_INTRADAY;
if(g_cfg.tf_exec == PERIOD_M1) selected_horizon = HORIZON_SCALPING;
else if(g_cfg.tf_exec == PERIOD_H1 || g_cfg.tf_exec == PERIOD_H4) selected_horizon = HORIZON_SWING;
else if(td.aligned && (td.h4_dir == dr.direction || td.h1_dir == dr.direction)) selected_horizon = HORIZON_INTRADAY;
```

### Analysis of Logic:
1. **Primary Determinant:** The input execution timeframe (`g_cfg.tf_exec`).
   - `PERIOD_M1` $\rightarrow$ `HORIZON_SCALPING`
   - `PERIOD_H1` or `PERIOD_H4` $\rightarrow$ `HORIZON_SWING`
   - `PERIOD_M5` (Default) $\rightarrow$ `HORIZON_INTRADAY`
2. **Third Condition Redundancy:** The branch `else if(td.aligned && ...)` assigns `HORIZON_INTRADAY`, which is already the initialized default value. It has zero functional effect on horizon selection.
3. **Static vs Dynamic:** Horizon selection is **statically bound to chart configuration**. It does not dynamically adapt to market volatility, liquidity sweep depth, or regime expansion states.

---

## 2. Horizon-Specific Structural Invalidation Timeframe

Once `selected_horizon` is established, the stop geometry calculation selects the structural reference timeframe (`stop_tf`) at lines 487–491:

```mql5
ENUM_TIMEFRAMES stop_tf = g_cfg.tf_exec;
if(selected_horizon == HORIZON_SCALPING) stop_tf = (g_cfg.tf_exec == PERIOD_M1) ? PERIOD_M1 : PERIOD_M5;
else if(selected_horizon == HORIZON_SWING) stop_tf = (g_cfg.tf_h4 != 0) ? g_cfg.tf_h4 : PERIOD_H4;
else stop_tf = (g_cfg.tf_context != 0) ? g_cfg.tf_context : PERIOD_M15;
```

### Invalidation Structure Mapping:
| Horizon | `stop_tf` Applied | Structural Lookback Source | Invalidation Rationale |
| :--- | :--- | :--- | :--- |
| **SCALPING** | M1 or M5 | Latest M1/M5 confirmed swing high/low | Micro-structural invalidation; tight risk bounds. |
| **INTRADAY** | M15 (`tf_context`)| Latest M15 confirmed swing high/low | Standard session structure; protects against execution noise. |
| **SWING** | H4 (`tf_h4`) | Latest H4 confirmed swing high/low | Macro-trend invalidation; gives multi-day trades room to breathe. |

---

## 3. Propagation Integrity Check

The selected horizon flows through the trade pipeline:
1. `selected_horizon` selected in `AMIGO.mq5` line 475.
2. Directs `stop_tf` selection for `FindLatestConfirmedSwing()` (line 487).
3. Packed into `TradeIntent.horizon = selected_horizon;` (line 603).
4. Passed into `PositionManagerRegister(..., selected_horizon)` (lines 635, 641).
5. Persisted in `g_positions[n].horizon` (line 86).
6. Regulates holding expiry (3600s), session liquidations, partial targets (1.5R vs 2.0R), break-even thresholds (33%, 50%, 60%), and trailing rates (15%, 25%, 35%) throughout the position lifecycle.

- **Status:** **IMPLEMENTED & FULLY INTEGRATED ACROSS RUNTIME.**
