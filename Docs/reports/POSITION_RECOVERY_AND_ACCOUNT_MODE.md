# AMIGO — Position Recovery and Account Mode Architecture

## 1. Broker Account Mode Analysis: Netting vs Hedging

In MetaTrader 5, broker accounts are configured as either **Hedging** or **Netting**:

### A. Hedging Accounts (`ACCOUNT_MARGIN_MODE_RETAIL_HEDGING`)
- Each trade order results in an independent broker position with a unique ticket `(POSITION_IDENTIFIER)`.
- Multiple trades on the same symbol can coexist simultaneously (e.g. Scalp Long and Swing Long, or Scalp Long and Intraday Short).
- **AMIGO Safety Invariant**: The in-memory array `g_positions[]` maps 1:1 to unique broker position identifiers. Stop loss and take profit modifications target the specific position ticket via `PositionSelectByTicket(pid)`.

### B. Netting Accounts (`ACCOUNT_MARGIN_MODE_RETAIL_NETTING`)
- Only **one** position can exist per symbol at any time.
- Adding a new trade adds volume to the existing position and computes a weighted average entry price. An opposing trade reduces volume or reverses the position.
- **Critical Netting Danger**: If AMIGO attempts to open a Scalp Long while an Intraday Long is active, MT5 will merge the two orders into one position with a single aggregate ticket, wiping out the distinct initial stops, targets, and trailing logic.

### C. Authoritative Policy for Netting Accounts:
> [!IMPORTANT]
> **Single Active Horizon per Symbol on Netting Accounts**
> On Netting accounts, AMIGO enforces a strict **Single Active Horizon Policy**:
> If a position already exists for `g_symbol`, any subsequent signal for a different horizon is rejected with reason `NETTING_ACCOUNT_CONCURRENT_HORIZON_PROHIBITED`.
> This guarantees that multiple horizons never corrupt a shared netted position.

---

## 2. In-Memory State Loss & Restart Recovery Strategy

### The Problem Identified in Phase 1:
When the MetaTrader 5 terminal restarts, reloads an EA, or experiences a power interruption, the dynamic array `PositionState g_positions[]` is wiped. The previous baseline bot had no mechanism to restore the original `ENUM_HORIZON`, break-even state, or trailing milestones.

### Recovery Architecture:
1. **Trade Comment Encoding**:
   When submitting live orders via `CTrade::OrderSend()`, AMIGO embeds the horizon identity and original risk parameters into the order comment string:
   $$\text{Comment} = \text{"AMIGO:"} + \text{HorizonTag} + \text{":"} + \text{DecisionId}$$
   Where `HorizonTag` $\in \{\text{"SCL"}, \text{"INT"}, \text{"SWG"}\}$.
2. **Reconciliation on EA Initialization (`OnInit()`)**:
   During `OnInit()`, the Position Manager scans all open positions where `PositionGetInteger(POSITION_MAGIC) == g_cfg.magic_number`:
   - Inspects `POSITION_COMMENT`.
   - Parses the `HorizonTag` to restore `g_positions[n].horizon`.
   - Reads current stop, price, and target to recalculate `be_trigger_price`.
3. **Fail-Closed Fallback**:
   If a position's comment cannot be parsed or is unrecognised, AMIGO assigns `HORIZON_INTRADAY` with a warning log, or exits the position safely if the stop distance is invalid. Never guess or corrupt existing state.
