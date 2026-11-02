# AMIGO — Restart Recovery Gap & Architecture Design

**Document Date:** 2026-11-02  
**Target Code:** `MQL5/Include/Position Manager.mqh` (Lines 12–33, 50–94), `AMIGO.mq5` (`OnInit()`)  
**Evaluator:** Antigravity Systems Architect & Resilience Engineer  

---

## 1. Defect Classification: Missing Feature

### Current Implementation Fact:
Active trade state is maintained exclusively in an in-memory dynamic array:
```mql5
PositionState g_positions[];
```

`PositionState` records:
- Initial entry, stop, and target.
- Initial ATR and risk-per-unit.
- `be_activated`, `be_trigger_price`, and `last_applied_stop`.
- `partial_done`.
- `horizon` (`HORIZON_SCALPING`, `HORIZON_INTRADAY`, `HORIZON_SWING`).

### The Terminal Restart Failure Mode:
When the MetaTrader 5 terminal restarts, reboots, crashes, or when the EA re-initializes (e.g. chart timeframe change or parameter update):
1. `g_positions[]` is wiped and re-allocated as empty.
2. `OnInit()` contains zero logic to scan open terminal positions (`PositionsTotal()`).
3. **All active positions are orphaned**:
   - The broker retains the open position and broker-side SL/TP.
   - AMIGO ceases tracking the ticket.
   - Break-even monitoring stops.
   - Dynamic and ATR trailing halts.
   - Partial profit targets are ignored.
   - Scalping 3600-second holding expiry and intraday session-close liquidations never trigger.

---

## 2. Proposed Production Recovery Architecture (Design Only)

To resolve this operational gap without risking state corruption, a hardened recovery subsystem is specified:

### A. Trade Comment State Serialization (On Entry)
MT5 allows up to 31 characters in `MqlTradeRequest.comment`. A 24-character compact serialization format can encode core identity:
```
AMG:<H>:<ATR_PTS>:<BE_RATIO>
Example: "AMG:S:125:33"
(Amigo, Scalp Horizon, ATR=12.5 pts, BE at 33% progress)
```

### B. Startup Reconciliation in `OnInit()`
During `OnInit()`, AMIGO must execute a reconciliation loop:
1. Iterate `PositionsTotal()`.
2. Select each position and verify:
   - `PositionGetString(POSITION_SYMBOL) == g_symbol`
   - `PositionGetInteger(POSITION_MAGIC) == g_cfg.magic_number`
3. Parse the comment prefix `"AMG:"`.
4. Reconstruct `PositionState`:
   - Extract horizon and ATR.
   - Read active ticket, volume, entry price, open time, current SL/TP.
   - If current SL is at or beyond entry price, reconstruct `be_activated = true`.
   - Inspect account deal history for the ticket to ascertain whether `partial_done = true`.
5. Populate `g_positions[]` with recovered state.

---

## 3. Governance & Risk Recommendation

- **Do Not Implement Speculatively:** A flawed position recovery engine can spuriously liquidate or mismanage live capital upon startup.
- **Current Status:** **MISSING — HIGH OPERATIONAL LIFECYCLE GAP.**
- **Interim Operational Constraint:** Until formal implementation and testing, any terminal reboot while holding positions requires immediate manual operator supervision or position closure.
