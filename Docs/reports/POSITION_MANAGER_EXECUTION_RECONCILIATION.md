# AMIGO — Position Manager Execution Reconciliation Report

**Document Date:** 2026-11-02  
**Target Code:** `MQL5/Include/Position Manager.mqh` (Lines 1–430)  
**Evaluator:** Antigravity Execution Risk Specialist  

---

## 1. Decoupled Lifecycle Architecture

The position manager state loop in `PositionManagerTick()` evaluates positions on each timer pulse (5 seconds). The execution order has been explicitly restructured:

```
[Entry in PositionManagerTick]
       │
       ▼
1. Live vs Shadow Mode State Synchronization (Lines 144-197)
       │
       ▼
2. Horizon Lifecycle Checks (Lines 200-227)
   ├─ SCALPING: Expiry after 3600s if BE not yet active (Line 205)
   ├─ INTRADAY: Forced liquidation at session end hour (Line 217)
   └─ SWING: Multi-session persistence exempt from intraday timers
       │
       ▼
3. Partial Profit Taking (Lines 234-275)
   ├─ Scalping: 1.5R target | Intraday/Swing: 2.0R target
   └─ Gated on verified broker partial volume close (Lines 256-260)
       │
       ▼
4. BREAK-EVEN EVALUATION (Lines 282-329)  <-- FULLY DECOUPLED
   ├─ Evaluated for ALL positions regardless of trailing settings
   ├─ Horizon BE triggers: Scalp 33% | Intraday 50% | Swing 60%
   └─ Gated strictly on PositionModify() confirmation
       │
       ▼
5. Trailing Mode Filter Check (Line 332)
   └─ if(g_positions[i].trailing_mode == TRAIL_OFF) continue;
       │
       ▼
6. Trailing Stop Execution (Lines 334-427)
   ├─ Mode 1: TRAIL_DYNAMIC_25_PERCENT (Lines 337-382)
   └─ Mode 2: TRAIL_ATR (Lines 383-427)
```

---

## 2. Broker Confirmation Gating Audit

Every order modification in `Position Manager.mqh` has been audited against premature state advancement:

### A. Break-Even Modification (Lines 301–321)
```mql5
bool modify_success = true;
if(!cfg.shadow_only)
{
   modify_success = g_trade.PositionModify(pid, proposed_be_sl, cur_tp);
   if(!modify_success)
   {
      LogMsg(LOG_WARN, "BE_FAILED", StringFormat("ticket=%I64u retcode=%u", pid, g_trade.ResultRetcode()));
   }
}

if(modify_success)
{
   g_positions[i].be_activated      = true;
   g_positions[i].current_stop      = proposed_be_sl;
   g_positions[i].last_applied_stop = proposed_be_sl;
   cur_sl                           = proposed_be_sl;
   LogMsg(LOG_INFO, "BE_ACTIVATED", ...);
}
```
**Audit Finding:** `be_activated = true` is only assigned if `modify_success` is true. On failure, state is preserved, and the system attempts modification again on subsequent ticks if conditions remain valid.

### B. Dynamic Trailing (Lines 363–378)
```mql5
bool mod_ok = true;
if(!cfg.shadow_only)
{
   mod_ok = g_trade.PositionModify(pid, proposed_sl, cur_tp);
   if(!mod_ok)
   {
      LogMsg(LOG_WARN, "TRAIL_BLOCKED", StringFormat("reason=MODIFY_FAILED retcode=%u", g_trade.ResultRetcode()));
   }
}
if(mod_ok)
{
   g_positions[i].current_stop      = proposed_sl;
   g_positions[i].last_applied_stop = proposed_sl;
   LogMsg(LOG_INFO, "TRAIL_UPDATE", ...);
}
```
**Audit Finding:** Stop levels are only advanced upon broker confirmation.

### C. ATR Trailing (Lines 408–424)
Standardized to identical verification structure as dynamic trailing, removing prior unverified cache writes.

---

## 3. Horizon Parameter Calibration Table

| Lifecycle Parameter | SCALPING | INTRADAY (Baseline) | SWING |
| :--- | :--- | :--- | :--- |
| **Partial Target** | 1.5R | 2.0R (`cfg.partial_rr`) | 2.0R (`cfg.partial_rr`) |
| **Partial Volume** | 50% (`cfg.partial_fraction`) | 50% (`cfg.partial_fraction`) | 50% (`cfg.partial_fraction`) |
| **Break-Even Trigger** | 33% to TP | 50% to TP | 60% to TP |
| **Dynamic Trail Ratchet**| 15% profit distance | 25% profit distance | 35% profit distance |
| **ATR Trailing Mult** | 1.0 $\times$ ATR | 1.5 $\times$ ATR | 2.5 $\times$ ATR |
| **Holding Expiry** | 3600 seconds (if no BE) | None | None |
| **Session End Action** | Liquidation (if configured)| Liquidation at `session_end_hour` | Exempt (Carries overnight) |

- **Status:** **VERIFIED COMPLETE AND PRODUCTION INTEGRATED.**
