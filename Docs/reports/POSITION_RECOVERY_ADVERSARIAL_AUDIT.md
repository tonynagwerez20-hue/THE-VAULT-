# AMIGO — Position Recovery Adversarial Audit

## 1. Forensic Audit of Previous Claims

> [!CAUTION]
> **Adversarial Critique of Previous Claim**
> Previous documentation (`POSITION_RECOVERY_AND_ACCOUNT_MODE.md`) asserted that:
> *"AMIGO embeds the horizon identity into the order comment string (e.g. `AMIGO:SCL:9001`) and reconciles it on `OnInit()` via `PositionGetInteger(POSITION_MAGIC)`."*

### Source Code Inspection Results:
1. **Search for `POSITION_COMMENT`**:
   - Running `Select-String -Pattern "POSITION_COMMENT"` across the entire `MQL5/` directory returned **ZERO hits**.
2. **Inspection of `OnInit()` in `AMIGO.mq5`**:
   - Lines 120–253 contain account validation, configuration loading, risk initialization, and diagnostic prints.
   - **There is ZERO position reconciliation code in `OnInit()`**.
3. **Inspection of `Position Manager.mqh`**:
   - `g_positions[]` is an in-memory dynamic array.
   - There is no file serialization, no SQLite database storage, no GlobalVariable backup, and no comment parsing logic.

### Unvarnished Truth:
- **The "comment-based position recovery" described in previous reports was a DESIGN PROPOSAL, NOT AN IMPLEMENTED PRODUCTION FEATURE**.
- If the terminal restarts, reloads the EA, or loses power, **all in-memory horizon tracking in `g_positions[]` is permanently lost**.
- Upon restart, open positions will be detected by MetaTrader 5, but AMIGO will treat them as unmanaged or register them with defaults.
- **Classification**: **DEFECTIVE / UNIMPLEMENTED CLAIM RECLASSIFIED**.

---

## 2. Netting Account Operational Hazard

On Netting accounts:
1. Opening a 0.10 lot Scalp Long at $2000.00 followed by a 0.10 lot Swing Long at $2005.00 results in **ONE position of 0.20 lots at $2002.50**.
2. If `g_positions[]` maintains two separate tickets or synthetic records, both records attempt to modify the stop loss of the single underlying netting position using conflicting rules:
   - The Scalp logic will attempt to tighten the stop to $2001.00 (33% BE).
   - The Swing logic will attempt to hold the stop at $1980.00 (H4 structural pivot).
   - A race condition ensues where `PositionModify()` alternates stop levels on every timer tick until broker freeze limits are hit.
3. **Enforced Safety Requirement**:
   - On Netting accounts, AMIGO **must enforce a Single Active Horizon Rule per symbol**.
   - If an open position exists on `g_symbol`, all new trade intents for that symbol must be rejected with `ACTION_NO_TRADE` (`NETTING_CONCURRENT_POSITION_BLOCKED`).
