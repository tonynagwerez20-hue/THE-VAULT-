# AMIGO — Position Manager Behaviour Matrix

## 1. Feature Implementation Matrix Across Horizons

| Lifecycle Feature | Scalping (`HORIZON_SCALPING`) | Intraday (`HORIZON_INTRADAY`) | Swing (`HORIZON_SWING`) | Production Location | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Break-Even Trigger** | 33% Progress to TP | 50% Progress to TP | 60% Progress to TP | `Position Manager.mqh:66-71` | **SOURCE-VERIFIED** |
| **Dynamic Trailing Ratchet**| 15% Favourable Profit | 25% Favourable Profit | 35% Favourable Profit | `Position Manager.mqh:319-322` | **SOURCE-VERIFIED** |
| **ATR Trailing Multiplier** | 1.0x ATR | 1.5x ATR (`cfg.trail_atr_mult`) | 2.5x ATR | `Position Manager.mqh:361-364` | **SOURCE-VERIFIED** |
| **Partial Exit Target** | 1.5R | 2.0R (`cfg.partial_rr`) | 2.0R (`cfg.partial_rr`) | `Position Manager.mqh:234` | **SOURCE-VERIFIED** |
| **Holding Time Limit** | 3600 seconds (1 hour) | Session Close Hour | Unconstrained (Multi-session) | `Position Manager.mqh:205-224` | **SOURCE-VERIFIED** |
| **Session-End Liquidation** | Exempt (Timer-governed) | Active (`dt.hour >= cfg.session_end_hour`) | Exempt (Multi-session) | `Position Manager.mqh:217-224` | **SOURCE-VERIFIED** |
| **Max Holding Bars** | Unenforced (Uses elapsed time) | Session Boundary | None | `Position Manager.mqh:207` | **PARTIAL** |
| **Local Invalidation** | Relies on Stop Loss | Relies on Stop Loss | Relies on Stop Loss | `Position Manager.mqh:173, 187` | **SOURCE-VERIFIED** |
| **Structural Invalidation** | N/A | N/A | Evaluated Pre-Entry Only | `Risk Engine.mqh:107` | **MODEL-ONLY** |

## 2. In-Depth Operational Analysis

### A. Scalping Lifecycle
1. **Hold Limit & Expiry**:
   - `Position Manager.mqh:205-213`: Checks `elapsed_sec = (int)(now_t - g_positions[i].opened)`.
   - If `elapsed_sec >= 3600` AND `!g_positions[i].be_activated`, calls `PositionManagerRemove(i, "SCALP_TIME_EXPIRED", cur_price, cfg)`.
   - **Behavioral impact**: Protects against momentum decay in failed micro-setups.
2. **Break-Even**:
   - `be_ratio = 0.33` moves stop to entry at one-third progress to target.
3. **Trailing Stop**:
   - Ratchets at 15% distance, locking profits aggressively.

### B. Intraday Lifecycle
1. **Session Enforcement**:
   - `Position Manager.mqh:217-224`: Evaluates `dt.hour >= cfg.session_end_hour`.
   - If reached, calls `PositionManagerRemove(i, "INTRADAY_SESSION_CLOSE", cur_price, cfg)`.
   - **Behavioral impact**: Eliminates overnight gap risk, swap costs, and off-session spread expansion.
2. **Break-Even & Trailing**:
   - Preserves baseline 50% BE trigger and 25% dynamic trailing ratchet.

### C. Swing Lifecycle
1. **Multi-Session Independence**:
   - Explicitly bypassed in the holding limit and session liquidation checks.
2. **Break-Even & Trailing**:
   - Break-even delayed to 60% progress to allow multi-day swings to breathe.
   - Dynamic trailing set to 35% ratchet or 2.5x ATR to avoid shakeouts.

## 3. Gaps & Residual Discrepancies
- **`opened_bar_count`**: Field added to `PositionState`, but is not incremented on closed bars in `PositionManagerTick()`. Holding limits rely solely on wall-clock elapsed seconds (`now_t - opened`).
- **Dynamic Structural Pivot Invalidation**: Swing trades do not update trailing stops based on newly forming intermediate swing pivots while in-flight; they rely on the ATR or dynamic percentage ratchet.
