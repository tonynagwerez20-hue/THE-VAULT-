# PHASE 5 — STRUCTURED LOG AUDIT

**Document Status**: Authoritative Engineering Audit  
**Date**: 24 September 2026  
**System**: AlgoMind / ASAP Retail Order-Flow System  

---

## 1. Structured Telemetry Overview

Phase 5 introduced a clean separation of telemetry tags in `AMIGO.mq5` and `Logger.mqh`:

1. **`[AlgoMind][DECISION]`**: Logged on every M5 closed bar when `Decide()` evaluates. Contains `id`, `sym`, `act`, `reg`, `hyp`, `score`, and `reason`.
2. **`[AlgoMind][DIAG]`**: Logged on every M5 closed bar. Contains technical feature vector diagnostics (`fus`, `flip_u`, `flip_d`, `surge`, `swp`, hypothesis scores, threshold margins).
3. **`[AlgoMind][FLOW_DIAG]`** (*New in Phase 5*): Logged on every M5 closed bar. Contains native MQL5 order-flow diagnostics: `vwap`, `dev`, `poc`, `vah`, `val`, `cd` (cumulative delta), `fp_press`, `state` (pressure state), and `shadow` flag.
4. **`[AlgoMind][EXEC_SHADOW]`** (*New in Phase 5*): Logged inside `Execution Engine.mqh` whenever an order attempt reaches execution while `g_cfg.shadow_only == true`. Intercepts `OrderSend()` and logs order parameters without submitting orders.

---

## 2. Field Audit & Provenance Mapping

| Field | Source Module | Provenance Tag | Logged in `20260924.log`? |
| :--- | :--- | :--- | :--- |
| `ts` | `TimeCurrent()` | MT5 Broker Clock | YES |
| `sym` | `g_symbol` | MT5 Market Watch | YES |
| `tf` | `InpTFExec` | MT5 Chart Period | YES |
| `act` | `DecisionResult.action` | MQL5 Strategy Engine | YES |
| `reg` | `RegimeState.regime` | MQL5 Regime Engine | YES |
| `score` | `DecisionResult.best_score` | MQL5 Strategy Engine | YES |
| `reason` | `DecisionResult.reason` | MQL5 Decision Gate | YES |
| `vwap` | `CAM_ProxyVWAP` | PROXY (MQL5 tick-weighted price) | PENDING EA RELOAD |
| `dev` | `CAM_ProxyVWAP` | PROXY (ATR-normalized deviation) | PENDING EA RELOAD |
| `poc` | `CAM_ActivityProfile` | PROXY (Point of Control price) | PENDING EA RELOAD |
| `vah` / `val` | `CAM_ActivityProfile` | PROXY (70% Value Area High / Low) | PENDING EA RELOAD |
| `cd` | `CAM_Footprint` | PROXY (Cumulative Delta) | PENDING EA RELOAD |
| `fp_press` | `CAM_Footprint` | PROXY (Footprint Pressure) | PENDING EA RELOAD |
| `shadow` | `g_cfg.shadow_only` | MQL5 Configuration Gate | PENDING EA RELOAD |

---

## 3. Sample Observed Log Entries from `20260924.log`

### Active Legacy Logs (Observed at 07:30:00 UTC)
```
07:30:00.903 [AlgoMind][DECISION] id=1790224201063 sym=XAUUSD act=4 reg=7 hyp=0 score=0.4000 reason=REGIME_NO_TRADE
07:30:00.903 [AlgoMind][DIAG] ts=2026.09.24 04:30 sym=XAUUSD tf=5 reg=7 dir=1 fus=0.236 flip_u=0 flip_d=0 surge=0 swp=0 cntL=0.332 cntS=0.032 mrL=0.000 mrS=0.400 sL=0.332 sS=0.400 best=0.400 mrg=0.068 th=0.35 mrg_th=0.05 act=4 rsn=REGIME_NO_TRADE
```

### Expected New Telemetry Log Format (Target for EA Reload)
```
07:35:00.120 [AlgoMind][INFO][FLOW_DIAG] ts=2026.09.24 04:35 vwap=2650.12345 dev=-0.35 poc=2651.00000 vah=2653.20000 val=2648.50000 cd=+45.50 fp_press=+0.1245 state=0 shadow=TRUE
```
