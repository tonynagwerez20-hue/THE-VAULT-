# AMIGO — Position Recovery Implementation Report

**Document Date:** 2026-11-02  
**Target Code:** `MQL5/Include/PositionRecovery.mqh`, `MQL5/Include/Position Manager.mqh`, `MQL5/Experts/AMIGO.mq5`  
**Evaluator:** Antigravity Systems Engineer  

---

## 1. Lifecycle Hook Integration Points

Persistent state management is attached to the complete trade lifecycle:

1. **State Persistence on Registration (`Position Manager.mqh` Line 94):**
   When `PositionManagerRegister()` finishes registering a new ticket in memory, it calls `PositionSaveState(cfg)`.
2. **State Persistence on Closure / Removal (`Position Manager.mqh` Line 119):**
   When `PositionManagerRemove()` closes or clears an index, it calls `PositionSaveState(cfg)`.
3. **State Persistence on Modification:**
   Whenever `PositionManagerTick()` successfully advances a stop (Break-Even or Dynamic/ATR trailing), `PositionSaveState(cfg)` is invoked.
4. **Reconciliation & Recovery on Startup (`AMIGO.mq5` Lines 184–188):**
   In `OnInit()`, prior to activating the 5-second position timer, `PositionReconcileState(g_cfg)` loads and validates all persisted tickets.

---

## 2. Startup Reconciliation Algorithm (`PositionReconcileState()`)

```mql5
int PositionReconcileState(const AmigoConfig &cfg)
```
### Reconciliation Sequence:
1. Verify presence of `Amigo_positions.dat`. If missing, return 0 (clean boot).
2. Validate Schema Version == 101.
3. Validate Magic Number == `cfg.magic_number`.
4. Iterate saved records:
   - In **Live Mode** (`!cfg.shadow_only`):
     - Query broker position via `PositionSelectByTicket(p.position_id)`.
     - If position closed while offline $\rightarrow$ omit record (graceful de-registration).
     - Verify symbol matches `cfg.symbol` and magic matches `cfg.magic_number`.
     - Sync authoritative broker stop loss (`p.current_stop = PositionGetDouble(POSITION_SL)`).
     - If stop was adjusted at or beyond entry while offline, automatically restore `be_activated = true`.
   - In **Shadow Mode** (`cfg.shadow_only`):
     - Restore synthetic tickets and continue offline forward simulation seamlessly.
5. Populate `g_positions[]` and log restored tickets with horizon designations.

- **Verification Status:** **COMPLETE-VERIFIED (SOURCE-VERIFIED, IMPLEMENTED-VERIFIED).**
