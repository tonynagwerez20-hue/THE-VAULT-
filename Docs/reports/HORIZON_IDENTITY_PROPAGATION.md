# AMIGO — Horizon Identity Propagation & Traceability Audit

## 1. Traceability Map

```
[Timeframe Context] -> EvaluateTopDownContext()
                                |
[Signal Evaluation] -> ScoreStrategies() & Decide()
                                |
[Decision Layer]    -> dr.direction, dr.hypothesis, dr.best_score
                                |
[Horizon Selector]  -> selected_horizon (SCALPING / INTRADAY / SWING)
                                |
                                v
                       TradeIntent.horizon
                                |
                   ValidateIntent(ti, g_cfg)
                                |
                   ExecuteIntent(ti, lots, g_cfg)
                                |
                   PositionManagerRegister(..., selected_horizon)
                                |
                                v
                     g_positions[n].horizon
                                |
                   PositionManagerTick(g_cfg)
                                |
                     [Horizon-Specific Policies]
```

## 2. Component Verification

| Component | File | Evidence / Verification | Status |
| :--- | :--- | :--- | :--- |
| **Contract** | `Contracts header.mqh:207` | `ENUM_HORIZON horizon;` in `TradeIntent` | **VERIFIED** |
| **EA Selection** | `AMIGO.mq5:581-585` | `selected_horizon` set based on `g_cfg.tf_exec` & `td.aligned` | **VERIFIED** |
| **EA Registration** | `AMIGO.mq5:616, 622` | Passed directly into `PositionManagerRegister` | **VERIFIED** |
| **Position State** | `Position Manager.mqh:26` | `g_positions[n].horizon` assigned and retained | **VERIFIED** |
| **Lifecycle Policies** | `Position Manager.mqh:205-227` | Horizon-differentiated expiry, session exit, BE, and trailing | **VERIFIED** |
| **Shadow Harness** | `Test_ShadowHarness.mq5:139` | Horizon explicitly supplied during synthetic registration | **VERIFIED** |
| **Unit Verification** | `Test_HorizonPropagation.mq5` | Verified 3/3 profiles registered with unique BE triggers | **VERIFIED** |
