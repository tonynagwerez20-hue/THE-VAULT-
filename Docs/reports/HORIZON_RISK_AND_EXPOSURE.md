# AMIGO — Horizon Risk Allocation & Multi-Horizon Exposure Guard

## 1. Risk Decoupling Principles
- Strategy scoring and horizon classification operate completely independently of account balance or equity tier.
- Sizing is executed strictly through the 3-State Min-Lot Engine in `Account Execution Engine.mqh`.
- The spline curve dynamically computes base risk percentage (0.50% - 1.50%) and maximum allowable distortion.

## 2. Multi-Horizon Concurrency Control
To prevent concurrent horizon risk stacking (e.g. Scalp + Intraday + Swing entering concurrently on the same instrument):
1. **Daily Loss Lock**:
   - `RiskTick()` tracks cumulative daily drawdown against `g_cfg.daily_loss_pct`.
   - Exceeding the daily limit sets `daily_locked = true`, blocking new entries across all horizons.
2. **Total High-Water Mark Drawdown Lock**:
   - Monitored continuously; exceeding `g_cfg.total_dd_pct` permanently locks new entries until manual intervention.
3. **Symbol Exposure Limits**:
   - By default, AMIGO limits simultaneous open positions to avoid margin over-utilization and correlated stop-out risks.
