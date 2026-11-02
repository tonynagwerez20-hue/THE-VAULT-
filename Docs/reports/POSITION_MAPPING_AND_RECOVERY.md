# AMIGO — Position Mapping, Ticket Invalidation & Restart Recovery

## 1. Ticket Association Architecture
AMIGO operates dual execution modes:
1. **Live Execution Mode (`shadow_only = false`)**:
   - Positions are registered using the broker's authoritative ticket: `(ulong)PositionGetInteger(POSITION_IDENTIFIER)`.
   - On each tick, `PositionSelectByTicket(pid)` revalidates broker existence.
   - If a position is closed externally (SL/TP hit or manual intervention), AMIGO cleans up internal tracking via `PositionManagerRemove()`.
2. **Shadow Execution Mode (`shadow_only = true`)**:
   - Synthetic positions are registered using the deterministic decision ID: `(ulong)decision_id`.
   - Synthetic positions track live quotes directly, evaluating simulated SL, TP, BE triggers, and trailing adjustments without submitting broker orders.

## 2. Invalidation & External Deal Reconciliation
- `OnTradeTransaction()` dispatches all events to `TransactionReconHandle()`.
- Reconciliation handles `TRADE_TRANSACTION_DEAL_ADD`, `TRADE_TRANSACTION_POSITION`, and `TRADE_TRANSACTION_HISTORY_ADD`.
- Internal state mutation is strictly decoupled from asynchronous deal arrival to prevent race conditions during rapid market moves.

## 3. Terminal Restart Recovery Architecture
- When the EA is re-initialized (e.g. after terminal restart or crash):
  - In Live Mode, open positions matching the EA's magic number and symbol are detected via `PositionsTotal()`.
  - Open positions are re-mapped using their ticket ID and current stop levels.
  - In Shadow Mode, positions are re-initialized cleanly, avoiding stale state carryover.
