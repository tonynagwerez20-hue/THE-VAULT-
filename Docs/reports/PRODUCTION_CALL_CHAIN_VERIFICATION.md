# AMIGO — Production Call Chain Verification

## 1. End-to-End Architectural Trace

The production lifecycle call chain for trading horizon spans analytical detection, intent generation, validation, execution, registration, and active management:

```
[MQL5 Runtime OnClosedBar()]
   │
   ├─► EvaluateTopDownContext(g_symbol, m5_atr) ────────► td (TopDownContext)
   │
   ├─► ScoreStrategies(g_feat, g_ext, g_cfg) ──────────► s (StrategyScores)
   │
   ├─► Decide(s, rs, g_ext, g_cfg, dq) ─────────────────► dr (DecisionResult)
   │     Action: ACTION_TRADE
   │     Direction: dr.direction (+1 / -1)
   │
   ├─► [Analytical Horizon Selection] (AMIGO.mq5:581-585)
   │     selected_horizon = HORIZON_INTRADAY;
   │     if (tf_exec == PERIOD_M1) -> HORIZON_SCALPING
   │     else if (tf_exec == PERIOD_H1 || tf_exec == PERIOD_H4) -> HORIZON_SWING
   │     else if (td.aligned && (td.h4_dir == dr.direction || td.h1_dir == dr.direction)) -> HORIZON_INTRADAY
   │
   ├─► TradeIntent Assembly (ti.horizon = selected_horizon) (Contracts header.mqh:207)
   │
   ├─► ValidateIntent(ti, g_cfg, vreason) ─────────────► PASS (Execution Engine.mqh)
   │
   ├─► ExecuteIntent(ti, lots, g_cfg) ─────────────────► er (ExecutionResult)
   │     If shadow_only = true: Synthetic interception (NO broker order sent)
   │     If shadow_only = false: CTrade OrderSend
   │
   ├─► Position Registration (AMIGO.mq5:616 & 622)
   │     PositionManagerRegister(pid, entry, sl, tp, dir, atr, g_cfg, selected_horizon)
   │
   ├─► Storage in Array (Position Manager.mqh:86)
   │     g_positions[n].horizon = horiz;
   │     g_positions[n].be_trigger_price = entry +/- (tp_dist * be_ratio)
   │
   └─► Periodic Cycle OnTimer() -> PositionManagerTick(g_cfg) (Position Manager.mqh:121)
         Scalp: 3600s holding expiry (Line 205)
         Intraday: session_end_hour liquidation (Line 217)
         Swing: multi-session holding & structural trailing (Line 226)
         Dynamic Trailing: 15% (Scalp), 25% (Intraday), 35% (Swing) (Line 319)
```

## 2. Transition Point Verification Matrix

| Transition Step | Component / Location | Data Transferred | Horizon Survived? | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **1. Analytical Selection** | `AMIGO.mq5:581-584` | `tf_exec` & `td.aligned` -> `selected_horizon` | Yes (Enum explicitly assigned) | **SOURCE-VERIFIED** |
| **2. DecisionResult Handoff** | `AMIGO.mq5:585` | `selected_horizon` -> `ti.horizon` | Yes (`TradeIntent.horizon` assigned) | **SOURCE-VERIFIED** |
| **3. Intent Validation** | `Execution Engine.mqh:52` | `ti` passed to `ValidateIntent()` | Yes (Read-only validation, no mutation) | **SOURCE-VERIFIED** |
| **4. Execution Handoff** | `Execution Engine.mqh:87` | `ti` passed to `ExecuteIntent()` | Yes (Read-only execution dispatch) | **SOURCE-VERIFIED** |
| **5. Position Registration (Live)** | `AMIGO.mq5:616-617` | `PositionManagerRegister(..., selected_horizon)` | Yes (Parameter 8 passed cleanly) | **SOURCE-VERIFIED** |
| **6. Position Registration (Shadow)**| `AMIGO.mq5:622-623` | `PositionManagerRegister(..., selected_horizon)` | Yes (Parameter 8 passed cleanly) | **SOURCE-VERIFIED** |
| **7. PositionState Storage** | `Position Manager.mqh:86` | `g_positions[n].horizon = horiz;` | Yes (Stored in persistent in-memory struct) | **SOURCE-VERIFIED** |
| **8. Periodic Evaluation** | `Position Manager.mqh:139`| `ENUM_HORIZON horiz = g_positions[i].horizon` | Yes (Retrieved every OnTimer tick) | **SOURCE-VERIFIED** |
| **9. Terminal Restart Recovery** | `Position Manager.mqh` | `PositionsTotal()` reconstruction | **NO** (Original horizon lost on restart) | **DEFECTIVE / UNVERIFIED** |

## 3. Vulnerability & Leak Assessment

1. **Implicit Enum Conversions**: None. Strict typing `ENUM_HORIZON` is preserved across all headers.
2. **Silent Fallback to Intraday**:
   - In `AMIGO.mq5:581`, default initialization is `HORIZON_INTRADAY`. If `tf_exec` is M5/M15 and top-down alignment fails, the trade defaults to `HORIZON_INTRADAY`.
3. **Netting / Terminal Restart Leak**:
   - `PositionManagerRegister` stores position states in dynamic memory `g_positions[]`. If the MetaTrader 5 terminal restarts or reloads the EA, `g_positions[]` is wiped.
   - Live reconciliation currently re-reads open positions via `PositionSelectByTicket`, but **does not restore the original `ENUM_HORIZON`** from an external persistent database or deal comments.
