# AMIGO — Older Version Baseline Audit
**Phase 1 Forensic Investigation Report**
**Target**: AMIGO MQL5 Production Runtime Baseline (`XAUUSDm`)
**Commit**: `61bed6014fbebb0ebd25678d4047ffc56d9074a8` (Mon Nov 2 16:16:55 2026 +0300)
**Branch**: `main` | **Remote**: `https://github.com/tonynagwerez20-hue/THE-VAULT-.git`

---

## 1. Executive Forensic Summary

A forensic audit of the older baseline bot and its actual production call chain reveals two fundamental structural flaws responsible for poor decision quality and unexpected drawdowns:

1. **Top-Down Timeframe Disconnect**:
   - `Structure Engine.mqh` defines `TopDownContext EvaluateTopDownContext(symbol, m5_atr)`, computing directional bias across 7 timeframes (D1, H4, H1, M30, M15, M5, M1) and outputting `aligned`, `conflict`, and `alignment_score`.
   - In `AMIGO.mq5:424-428`, `EvaluateTopDownContext` is executed, logged, and then **completely discarded**.
   - `EvaluateRegime()` in `Regime Engine.mqh:67` accepts only `(const FeatureSnapshot &f, const AmigoConfig &cfg)` which derives structure exclusively from the single execution timeframe `g_cfg.tf_exec` (lines 28, 37).
   - Therefore, **the Regime Engine is completely blind to higher-timeframe trends, exhaustion, and HTF-LTF conflicts**. It classifies market regimes purely on local micro-structure.

2. **Horizon Selection & Risk Disconnect**:
   - In `AMIGO.mq5:581-584`, `selected_horizon` was determined by a simplistic fallback heuristic after risk calculations had already concluded.
   - `AccountExecutionEvaluate()` in `AMIGO.mq5:540` sizes the lot volume using `SelectStop()` before the trading horizon lifecycle is established.
   - `PositionManagerRegister()` now stores the horizon, but if the terminal restarts or the position is modified externally, `g_positions[]` loses the horizon identity because it is maintained only in transient dynamic memory with no persistent backing ledger.

---

## 2. End-to-End Production Call Chain Trace

```
1. Market Data (MT5 Quotes / Closed Bars)
   │
2. [AMIGO.mq5:332] OnClosedBar()
   │
   ├──► [Market Snapshot Builder.mqh:10] BuildMarketSnapshot() ──────► g_snap
   │
   ├──► [FeatureVector.mqh:14] BuildFeatureVector() ──────────────────► g_feat (Uses g_cfg.tf_exec ONLY)
   │
   ├──► [Structure Engine.mqh:157] EvaluateTopDownContext() ────────► td (TopDownContext)
   │      [CRITICAL DEFECT]: td is LOGGED then DISCARDED! Never passed to Regime Engine!
   │
   ├──► [Regime Engine.mqh:67] EvaluateRegime(g_feat, g_cfg) ────────► rs (RegimeState)
   │      [CRITICAL DEFECT]: Evaluates only g_feat (tf_exec structure). HTF bias = ZERO influence!
   │
   ├──► [Strategy Engine.mqh:77] ScoreStrategies(g_feat, g_ext, g_cfg)► ss (StrategyScores)
   │
   ├──► [Strategy Engine.mqh:122] Decide(ss, rs, g_ext, g_cfg, dq) ──► dr (DecisionResult)
   │      Checks rs.preferred == dr.hypothesis. If Regime misclassifies, trade is misqualified!
   │
   ├──► [Risk Engine.mqh:107] SelectStop(dr.direction, entry, structural_invalid, atr)
   │      [DEFECT]: Structural invalidation is evaluated on tf_exec (M5), NOT on the trade horizon!
   │
   ├──► [RiskController.mqh:161] RiskControllerEvaluate() ──────────► risk_auto (Spline Risk %)
   │
   ├──► [Account Execution Engine.mqh:311] AccountExecutionEvaluate() ─► acc_env (Lots Sizing)
   │
   ├──► [AMIGO.mq5:581] Horizon Selection:
   │      selected_horizon assigned to TradeIntent.horizon
   │
   ├──► [Execution Engine.mqh:87] ExecuteIntent(ti, lots, g_cfg) ────► er (ExecutionResult)
   │
   └──► [Position Manager.mqh:53] PositionManagerRegister(pid, ..., selected_horizon)
          Stored in in-memory array g_positions[].
          [DEFECT]: State lost upon terminal reboot. Netting accounts aggregate multiple horizons.
```

---

## 3. Subsystem Classification & Verification Matrix

| Subsystem Component | File & Line | Status | Forensic Evidence |
| :--- | :--- | :--- | :--- |
| **Higher Timeframe Calculation** | `Structure Engine.mqh:157-199` | **IMPLEMENTED BUT DISCONNECTED** | D1, H4, H1, M30, M15 structure states are calculated and synthesized into `TopDownContext td`, but `td` is never fed into `EvaluateRegime()`. |
| **Multi-Timeframe Regime Classification** | `Regime Engine.mqh:26-65, 67` | **DEFECTIVE** | `ScoreTrendUp`, `ScoreTrendDown`, `ScoreBalance` use `f.structure_dir` from the local execution timeframe only. HTF alignment is ignored. |
| **Regime-Strategy Gating** | `Strategy Engine.mqh:186-191` | **IMPLEMENTED AND INTEGRATED** | If `rs.preferred != d.hypothesis`, trade returns `ACTION_WAIT`. However, because `rs` is defective, this gate rejects valid trades and admits countertrend traps. |
| **Horizon Determination** | `AMIGO.mq5:581-585` | **IMPLEMENTED AND INTEGRATED** | `selected_horizon` evaluates `tf_exec` and `td.aligned`, populated into `ti.horizon`. |
| **Stop Placement Timeframe** | `AMIGO.mq5:483-494` | **DEFECTIVE** | `CopyRates(g_symbol, g_cfg.tf_exec, ...)` searches for swing points solely on `tf_exec`, giving swing trades scalp-sized stops or forcing premature invalidation. |
| **Horizon Position Management** | `Position Manager.mqh:199-378` | **IMPLEMENTED AND INTEGRATED** | Distinct 33%/50%/60% BE triggers, 15%/25%/35% dynamic trailing factors, 3600s scalp expiry, and intraday session liquidation. |
| **Position State Persistence** | `Position Manager.mqh:32, 147` | **DEFECTIVE** | Transient in-memory array `g_positions[]`. Terminal reboot or crash obliterates horizon mapping. |
| **Authoritative Monetary Sizing** | `Account Execution Engine.mqh:311`| **IMPLEMENTED AND INTEGRATED** | Strict monetary risk bounding across equity tiers, respecting broker volume limits and distortion thresholds. |

---

## 4. Root-Cause Analysis of Live Losses in Older Bot

1. **Local Retracement Traps (Buying Local M5 Peaks in H4 Bear Regimes)**:
   - When H4/D1 is in an aggressive downtrend, a minor M5 bullish expansion creates `f.structure_dir = +1` and positive tick delta.
   - `EvaluateRegime()` scores this as `REGIME_TREND_UP` because it has zero visibility into H4.
   - The EA issues a `HYP_CONTINUATION` Buy order into major institutional resistance, resulting in immediate stop-outs.

2. **Inappropriate Local Stop Sizing for Longer Horizons**:
   - When a Swing or Intraday setup is qualified, `SelectStop()` identifies invalidation pivots from 200 bars of `tf_exec` (M5).
   - An M5 swing pivot cannot withstand normal H1/H4 market noise, causing the position to get stopped out prematurely even when the macro thesis was correct.

3. **In-Flight Horizon Amnesia**:
   - If the bot reloaded or restarted while managing trades, all horizon rules were wiped, leaving positions orphaned or defaulted.

---

## 5. Required Implementation Scope (Phases 2–6)

1. **Phase 2 (Regime Engine Upgrade)**:
   - Extend `EvaluateRegime()` to accept `const TopDownContext &td`.
   - Incorporate HTF directional weight into `ScoreTrendUp`, `ScoreTrendDown`, and detect `HTF_LTF_CONFLICT` as `REGIME_BALANCED` or `REGIME_NO_TRADE`.
   - Condition `HYP_MEAN_REVERSION` strictly on confirmed HTF exhaustion or execution-timeframe structural divergence.

2. **Phase 3 (Horizon-Aware Stop Geometry)**:
   - Adapt `SelectStop()` and swing pivot search to query the timeframe corresponding to the trade's horizon:
     - Scalping: M1/M5 structure
     - Intraday: M15/H1 structure
     - Swing: H4/D1 structure
   - Preserve authoritative account-level monetary risk sizing in `AccountExecutionEvaluate()`.

3. **Phase 4 (Horizon Persistence)**:
   - Encode horizon identity directly into the MT5 position comment string or a local persistent ledger to guarantee recovery after restart.
