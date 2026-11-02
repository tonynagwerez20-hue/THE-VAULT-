# AMIGO — Production Call-Chain Reverification

## 1. Complete Call-Chain Audit Trace

This table traces the complete production path through the upgraded MQL5 codebase, identifying the exact file, function, line numbers, and consumers:

| Sequence | Function / Stage | File & Lines | Exact Input | Output Produced | Downstream Consumer | Status |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | `OnTick()` | `AMIGO.mq5:263-329` | Broker Tick Stream | Bar transition check | `OnClosedBar()` | **SOURCE-VERIFIED** |
| **2** | `OnClosedBar()` | `AMIGO.mq5:332-625` | Closed Bar Event | Session verification | Pipeline triggers | **SOURCE-VERIFIED** |
| **3** | `BuildMarketSnapshot()` | `Market Snapshot Builder.mqh:10` | `g_symbol` | `g_snap` (MarketSnapshot) | Feature vector & logs | **SOURCE-VERIFIED** |
| **4** | `BuildFeatureVector()` | `FeatureVector.mqh:14` | `g_symbol, g_cfg` | `g_feat` (FeatureSnapshot) | `ScoreStrategies, EvaluateRegime` | **SOURCE-VERIFIED** |
| **5** | `EvaluateTopDownContext()` | `Structure Engine.mqh:157` | `g_symbol, atr14` | `td` (TopDownContext) | `EvaluateRegime, Entry Geometry` | **SOURCE-VERIFIED** |
| **6** | `EvaluateRegime()` | `Regime Engine.mqh:90` | `g_feat, td, g_cfg` | `rs` (RegimeState) | `Decide()` (Strategy Gate) | **SOURCE-VERIFIED** |
| **7** | `ScoreStrategies()` | `Strategy Engine.mqh:77` | `g_feat, g_ext, g_cfg` | `ss` (StrategyScores) | `Decide()` | **SOURCE-VERIFIED** |
| **8** | `Decide()` | `Strategy Engine.mqh:122`| `ss, rs, g_ext, g_cfg` | `dr` (DecisionResult) | `AMIGO.mq5:464` (Action Gate) | **SOURCE-VERIFIED** |
| **9** | **Horizon Determination** | `AMIGO.mq5:475-478` | `g_cfg.tf_exec, td` | `selected_horizon` | Stop TF, `ti.horizon`, `PosMgr` | **SOURCE-VERIFIED** |
| **10** | **Structural Invalidation** | `AMIGO.mq5:485-502` | `stop_tf, dr.direction` | `structural_invalid` | `SelectStop()` | **SOURCE-VERIFIED** |
| **11** | `SelectStop()` | `Risk Engine.mqh:107` | `entry, structural_invalid`| `original_sl` | `EvaluateAdaptiveStop` | **SOURCE-VERIFIED** |
| **12** | `RiskControllerEvaluate()` | `RiskController.mqh:161`| `entry, original_sl, dd` | `risk_auto` (Risk %) | `AccountExecutionEvaluate` | **SOURCE-VERIFIED** |
| **13** | `EvaluateAdaptiveStop()` | `Risk Engine.mqh:145` | `entry, original_sl, tp` | `adapt_res` (Adaptive SL)| `acc_env` | **SOURCE-VERIFIED** |
| **14** | `AccountExecutionEvaluate()` | `Account Execution Engine.mqh:311`| `entry, sl, tp, risk_%` | `acc_env` (Volume Lots) | `ExecuteIntent()` | **SOURCE-VERIFIED** |
| **15** | `TradeIntent Assembly` | `AMIGO.mq5:574-596` | `dr, rs, selected_horizon`| `ti` (TradeIntent) | `ValidateIntent, ExecuteIntent` | **SOURCE-VERIFIED** |
| **16** | `ValidateIntent()` | `Execution Engine.mqh:52`| `ti, g_cfg` | `bool (vreason)` | Execution Gate | **SOURCE-VERIFIED** |
| **17** | `ExecuteIntent()` | `Execution Engine.mqh:87`| `ti, lots, g_cfg` | `er` (ExecutionResult) | Shadow intercept / OrderSend | **SOURCE-VERIFIED** |
| **18** | `PositionManagerRegister()`| `Position Manager.mqh:53`| `pid, entry, sl, tp, horiz`| `g_positions[n]` | `PositionManagerTick()` | **SOURCE-VERIFIED** |
| **19** | `PositionManagerTick()` | `Position Manager.mqh:121`| `g_cfg, quotes` | Stops / Exits / Trailing | `CTrade PositionModify / Close`| **SOURCE-VERIFIED** |

---

## 2. Identified Disconnects & Anomalies

1. **`opened_bar_count` (Dead Struct Member)**:
   - In `Position Manager.mqh:29`, `opened_bar_count` is declared in `PositionState` and initialized to `0` at line 88.
   - It is **never incremented** in `PositionManagerTick()`. Scalping expiry relies solely on wall-clock elapsed seconds (`now_t - opened >= 3600`).
2. **Comment-Based Recovery Omission**:
   - As documented in `POSITION_RECOVERY_ADVERSARIAL_AUDIT.md`, `AMIGO.mq5:OnInit()` does not parse or reconstruct open position states on reboot.
