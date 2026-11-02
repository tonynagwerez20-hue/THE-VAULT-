# ADVERSARIAL MULTI-HORIZON TRADE DIFFERENTIATION, LIFECYCLE & EXECUTION AUDIT
**Auditor**: Independent Principal Quantitative Trading Architect & Adversarial Code Auditor  
**Project**: AMIGO Core / AlgoMind MQL5  
**Audit Baseline**: Git commit `61bed60` (Zero Strategy Mutations, Inspection-Only Mode)  
**Date**: 2026-11-02  

---

## 1. Adversarial Verdict & Executive Findings

```
================================================================================
ADVERSARIAL VERDICT           : HORIZONS ARE MOSTLY LABELS (PARTIALLY DIFFERENTIATED)
LIFECYCLE SEPARATION STATUS   : DEFECTIVE AT POSITION MANAGEMENT LEVEL
TRADE IDENTITY SURVIVABILITY  : DEGRADED (Defaults to HORIZON_INTRADAY in MQL5 EA)
BACKTEST & EXECUTION READINESS: CONDITIONALLY-ACCEPTABLE (Offline Simulation Feasible)
================================================================================
```

### The Brutal Truth: What Was Claimed vs. What Was Actually Built
While Python reference schemas (`schema.py`, `test_horizons.py`) and top-down structure engines (`EvaluateTopDownContext`, `level_engine.py`) define distinct multi-horizon parameters, **the actual MQL5 EA runtime (`AMIGO.mq5`) registers every single trade with a hardcoded default horizon (`HORIZON_INTRADAY`) and manages all open positions with identical trailing logic.**

---

## 2. Forensic Code-Level Evidence of Defects

### DEFECT 1: Silent Horizon Defaulting in Main Execution Pipeline
* **File & Lines**: [`AMIGO.mq5`](file:///C:/Users/USER/Desktop/ALGOMIND/MQL5/Experts/AMIGO.mq5#L611-L619)
* **Actual Code**:
  ```mql5
  // Line 611-613 in AMIGO.mq5:
  PositionManagerRegister(er.position_id, entry, sl, tp, dr.direction, atr, g_cfg);
  
  // Signature in Position Manager.mqh line 48-50:
  void PositionManagerRegister(ulong pid, double entry, double stop, double target,
                               int dir, double atr, const AmigoConfig &cfg,
                               ENUM_HORIZON horiz = HORIZON_INTRADAY)
  ```
* **Consequence**: The EA passes no `horiz` parameter. As a result, **100% of all trades (whether identified on M1 scalping or H4 swing context) are assigned `HORIZON_INTRADAY`**. The horizon dimension is completely erased the moment a trade enters position management.
* **Classification**: `SOURCE-VERIFIED` | **Severity**: `CRITICAL`

### DEFECT 2: One Generic Position Management Function for All Trades
* **File & Lines**: [`Position Manager.mqh`](file:///C:/Users/USER/Desktop/ALGOMIND/MQL5/Include/Position Manager.mqh#L80-L345)
* **Actual Code**:
  Inside `PositionManagerTick`, the `horizon` field in `PositionState` is **never queried**.
  Every position, regardless of horizon:
  1. Shares the identical 50% TP progress break-even trigger (`be_trigger = entry ± 0.50 * |tp - entry|`).
  2. Shares the identical dynamic 25% trailing stop ratchet (`trailing_dist = profit_dist * 0.25`).
  3. Shares the identical 2.0R partial exit rule (`target_2r = entry ± 2.0 * r_unit`, closes 50%).
  4. Has **no maximum holding-period expiry** for scalps.
  5. Has **no end-of-session forced exit** for intraday positions.
* **Consequence**: A scalping trade that fails to reach TP will remain open indefinitely overnight, effectively morphing into an uncontrolled swing position. A swing trade experiencing normal intraday noise can be prematurely trailed by a tight 25% profit ratchet.
* **Classification**: `SOURCE-VERIFIED` | **Severity**: `CRITICAL`

### DEFECT 3: TradeIntent Schema Horizon Disconnect
* **File & Lines**: [`AMIGO.mq5`](file:///C:/Users/USER/Desktop/ALGOMIND/MQL5/Experts/AMIGO.mq5#L563-L584)
* **Actual Code**:
  In `OnClosedBar`, when building `TradeIntent ti`:
  ```mql5
  ti.intent_id        = decision_id;
  ti.schema_version   = Amigo_SCHEMA_VERSION;
  ti.strategy_version = 1;
  ti.feature_version  = g_feat.feature_version;
  ti.model_version    = ml.available ? 1 : 0;
  ti.symbol           = g_symbol;
  ti.direction        = dr.direction;
  ti.score            = dr.best_score;
  ti.regime           = rs.regime;
  ti.hypothesis       = dr.hypothesis;
  // NOTE: ti.horizon is NOT even populated!
  ```
* **Consequence**: The authoritative trade contract dispatched to execution contains no record of which horizon generated the trade.
* **Classification**: `SOURCE-VERIFIED` | **Severity**: `HIGH`

---

## 3. Systematic Answers to the 10 Mandatory Questions

1. **Are scalping, intraday, and swing trades genuinely treated differently?**  
   **NO.** In the MQL5 EA, all trades receive identical stop sizing formulas, identical 25% dynamic trailing rules, and identical 2.0R partials.
2. **Does horizon identity survive the entire trade lifecycle?**  
   **NO.** It is omitted when building `TradeIntent` and defaults to `HORIZON_INTRADAY` when registering in `PositionManager`.
3. **Are entry, stop, target, and management rules horizon-aware?**  
   **PARTIALLY.** Multi-timeframe structure (`EvaluateTopDownContext`) calculates swings across timeframes, but the final stop is always the latest M5 swing or $1.5\times ATR$, and TP is always $2.0\times$ stop distance.
4. **Can a trade accidentally change its intended holding period?**  
   **YES.** Because scalping positions lack a time-decay / max-bars expiry condition, stagnant scalps become overnight swing positions by default.
5. **Can different horizons coexist without position-management interference?**  
   **NO.** In netting accounts or single-order execution, multiple horizons on the same symbol will conflict or overwrite stops.
6. **Is risk controlled independently of horizon?**  
   **YES.** The risk controller correctly calculates lot sizing based on account equity and monetary risk budget, capping min-lot risk distortion at $5.0\times$.
7. **Are the two strategy families correctly supported across horizons?**  
   **YES, in Python tests (`test_horizons.py` 6 combinations PASS); NO, in MQL5 production EA.**
8. **Are horizon-specific performance results available?**  
   **NO.** Logging outputs ticket and price, but does not aggregate MAE/MFE or expectancy by horizon.
9. **What is actually implemented vs. missing vs. defective?**  
   * **Implemented**: 6-timeframe top-down structure synthesis, Python 6-combination unit test suite, account-aware risk budgeting.
   * **Defective**: MQL5 position manager never inspects `horizon`; EA omits horizon when calling `PositionManagerRegister`.
   * **Missing**: Time-based expiry for scalping, session close liquidation for intraday, and horizon-specific trailing profiles.
10. **What prevents the system from satisfying the intended design?**  
    A failure to bridge the analytical multi-timeframe outputs down into the trade registration call and position lifecycle manager.

---

## 4. Minimum Technically Sufficient Remediation Plan

To transform the multi-horizon architecture from "labels" into genuinely differentiated execution lifecycles:

1. **Step 1: Populate Horizon in `DecisionResult` and `TradeIntent`**:
   Derive `ENUM_HORIZON` based on entry timeframe (`M1 -> SCALPING`, `M5/M15 -> INTRADAY`, `H1/H4 -> SWING`).
2. **Step 2: Pass Horizon in `PositionManagerRegister`**:
   ```mql5
   PositionManagerRegister(er.position_id, entry, sl, tp, dr.direction, atr, g_cfg, dr.horizon);
   ```
3. **Step 3: Horizon-Aware Position Management Rules**:
   * **`HORIZON_SCALPING`**: Fast break-even at 30% TP progress; tight 15% trailing; max holding time of 12 M5 bars (1 hour). If time expires without momentum, close at market.
   * **`HORIZON_INTRADAY`**: Standard 50% break-even; 25% trailing; hard session-close liquidation before roll.
   * **`HORIZON_SWING`**: Wide structural trailing (trailing behind latest confirmed H1 swing); no time-based exit; immune to intraday noise.

---

### Authoritative Final Verdict
```
VERDICT: HORIZONS ARE MOSTLY LABELS (PARTIALLY DIFFERENTIATED)
RECOMMENDATION: Apply Step 1-3 lifecycle remediation before deploying multi-horizon live execution.
```
