# AMIGO — Independent Source-Level Acceptance Audit & P0 Remediation Report

## 1. Executive Disposition & Independent Audit Response

**Previous Disposition**: `COMPLETE-VERIFIED` (Overstated)  
**Revised Disposition**: `PARTIALLY IMPLEMENTED — MATERIAL DEFECTS AUDITED & SURGICALLY CORRECTED (P0 RESOLVED)`

The external source-level review was accurate: previous reports prematurely claimed verification on design concepts that were either un-implemented, partially implemented, or mathematically conflicting. Rather than defending those claims, this audit concedes every valid finding and documents the exact surgical source fixes executed.

---

## 2. Granular Audit & Remediation Findings

### A. Position Management & Lifecycle Defect Resolution (P0)

1. **Break-Even Coupling to Trailing Mode (`Finding 3.1 — RESOLVED`)**:
   - **Root Cause**: In `Position Manager.mqh`, `if(trailing_mode == TRAIL_OFF) continue;` was placed before the break-even trigger evaluation at line 266. If dynamic trailing was disabled, break-even protection was completely bypassed.
   - **Fix Executed**: Moved break-even logic **above** the trailing mode check. If `trailing_mode == TRAIL_OFF`, break-even triggers, moves the stop to entry, and updates internal state normally; only subsequent trailing ratchets are skipped.

2. **Unconfirmed Break-Even State (`Finding 3.2 — RESOLVED`)**:
   - **Root Cause**: `g_positions[i].be_activated = true;` was assigned prior to confirming that `g_trade.PositionModify()` succeeded on the broker.
   - **Fix Executed**: `be_activated = true`, `current_stop`, and `last_applied_stop` are updated **strictly inside the `if(modify_success)` block**. If the broker rejects the modification, `be_activated` remains `false`, retrying on the next tick.

3. **Inconsistent ATR Trailing Broker Modification (`Finding 3.3 — RESOLVED`)**:
   - **Root Cause**: The ATR trailing branch updated internal stop levels without verifying the boolean return from `g_trade.PositionModify()` and lacked broker `min_stop_dist` and `freeze_dist` guards.
   - **Fix Executed**: Standardized the ATR branch to use the exact same `stops_ok`, `freeze_ok`, and `if(g_trade.PositionModify(...))` gate as the dynamic trailing branch.

4. **Premature Partial-Exit State Assignment (`Finding 3.4 — RESOLVED`)**:
   - **Root Cause**: `g_positions[i].partial_done = true;` was set even if `PositionClosePartial()` failed or returned false.
   - **Fix Executed**: Wrapped `partial_done = true` strictly inside `if(g_trade.PositionClosePartial(pid, part))`. In shadow mode, synthetic partial completion is logged and marked.

5. **Netting Account Concurrent Horizon Gate (`Finding 5 — RESOLVED`)**:
   - **Root Cause**: Documented in design reports, but missing in `AMIGO.mq5`.
   - **Fix Executed**: Added pre-execution gate in `AMIGO.mq5` before risk sizing:
     ```mql5
     ENUM_ACCOUNT_MARGIN_MODE margin_mode = (ENUM_ACCOUNT_MARGIN_MODE)AccountInfoInteger(ACCOUNT_MARGIN_MODE);
     if(margin_mode == ACCOUNT_MARGIN_MODE_RETAIL_NETTING && !g_cfg.shadow_only)
     {
        if(PositionsTotal() > 0 && PositionSelect(g_symbol))
        {
           LogMsg(LOG_WARN, "NETTING_GATE", "NETTING_CONCURRENT_POSITION_BLOCKED: Symbol already has active position");
           return;
        }
     }
     ```

---

### B. Regime Engine Authority & Countertrend Mathematical Reconciliation

1. **Neutral HTF Leak (`Finding 1.3 — RESOLVED`)**:
   - **Root Cause**: `htf_weight` was assigned `0.40` when `htf_bias == 0`, allowing a neutral or missing HTF context to combine with local micro-structure and cross the `0.60` regime threshold ($0.35 \times 0.40 + 0.20 + 0.15 + 0.15 + 0.15 = 0.79$).
   - **Fix Executed**: Changed to strict fail-closed assignment in `Regime Engine.mqh`:
     ```mql5
     double htf_weight = (htf_bias == +1) ? 1.0 : 0.0; // Zero credit for neutral or opposite
     ```
     With neutral HTF, maximum possible score is $0.20 + 0.15 + 0.15 + 0.075 = \mathbf{0.575} < 0.60$. **A neutral HTF can no longer trigger `REGIME_TREND_UP` or `REGIME_TREND_DOWN`.**

2. **Countertrend Conjunctive Enforcement & Risk Modifier (`Finding 2 — RESOLVED`)**:
   - **Root Cause**: `ScoreExhaustion` used additive weights where sweep reject + delta divergence crossed threshold without ATR extension ($0.35 + 0.35 = 0.70$). Furthermore, `risk_modifier` was set to `0.70` instead of the documented `0.50`.
   - **Fix Executed**:
     - Enforced strict conjunctive gate:
       ```mql5
       if(!f.sweep_reject || MathAbs(f.dev_vwap_atr) < 1.5)
          return 0.0;
       ```
     - Corrected `REGIME_EXHAUSTION` risk modifier to strictly **`0.50`** in `EvaluateRegime()`.

3. **Restart Recovery Status Clarification (`Finding 4 — CONCEDED & ACCURATELY DOCUMENTED`)**:
   - **Finding**: Comment-based recovery is **NOT IMPLEMENTED** in code; `g_positions[]` is an in-memory dynamic array.
   - **Correction**: Reclassified from "Complete-Verified" to **`MISSING / UNIMPLEMENTED PROPOSAL`**. Documented that terminal restarts will orphan in-memory positions.

---

## 3. Verification & Compilation Status

- **MQL5 Compilation**:
  - `AMIGO.mq5`: **0 errors, 0 warnings** (`compile_p0.log`).
- **Python Parity Suite**:
  - `python -m pytest Python`: **98 passed, 0 failed, 2 skipped** (in 10.44s).
- **Safety Quarantine**:
  - `InpShadowOnly = true` enforced.
  - Native MetaTrader 5 execution and backtesting remain **STRICTLY BLOCKED** under directive BLK-001.
