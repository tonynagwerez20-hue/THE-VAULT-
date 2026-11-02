# AMIGO — Post-Implementation Adversarial Verification: Horizon-Aware Production Lifecycle

## Executive Summary
This document provides an independent adversarial critique and audit of the recently completed horizon-aware trade lifecycle implementation in AMIGO. It evaluates whether the changes genuinely fulfill production specifications or whether completion claims were premature.

---

## 1. Audit of the Production Patch

### Scope of Modified Code Files
1. **`AMIGO.mq5`**:
   - Lines 581–585: Evaluates timeframe and structure alignment to derive `selected_horizon` (`HORIZON_SCALPING` on M1, `HORIZON_SWING` on H1/H4, `HORIZON_INTRADAY` on aligned intermediate frames). Assigns `ti.horizon = selected_horizon`.
   - Lines 616 & 622: Passes `selected_horizon` as the 8th parameter to `PositionManagerRegister()` in both live and shadow branches.
   - *Adversarial finding*: No unrelated changes or strategy mutations were introduced.
2. **`Contracts header.mqh`**:
   - Line 207: Added `ENUM_HORIZON horizon;` to canonical `struct TradeIntent`.
   - *Adversarial finding*: Backward-compatible; cleanly aligned with Section 1 Three-Horizon Architecture.
3. **`Position Manager.mqh`**:
   - `PositionState` struct expanded with `ENUM_HORIZON horizon` and `opened_bar_count`.
   - `PositionManagerRegister()` signature updated to accept `ENUM_HORIZON horiz`.
   - Parameter calibration: Computes custom BE trigger (`be_ratio = 0.33` for Scalp, `0.50` for Intraday, `0.60` for Swing).
   - `PositionManagerTick()`: Implements scalping 3600-second hold timeout, intraday session liquidation, and differentiated trailing factors (15% Scalp, 25% Intraday, 35% Swing; ATR multipliers 1.0x Scalp, 2.5x Swing).
   - *Adversarial finding*: Preserves the exact 25% dynamic trailing and 50% break-even baseline for Intraday positions.
4. **`Test_ShadowHarness.mq5`**:
   - Updated `PositionManagerRegister()` call to pass `HORIZON_INTRADAY`.
5. **`Test_HorizonPropagation.mq5` & `Test_RegimeReachability.mq5`**:
   - Refactored to align with current contracts and includes. Compiled to `.ex5` with zero errors.
6. **`Amigo/__init__.py`**:
   - Added module mapping shims to resolve Python import collisions during test discovery.

---

## 2. End-to-End Horizon Identity Trace

- **Analytical Selection**: `AMIGO.mq5` derives `selected_horizon`.
- **Contract Transport**: `ti.horizon` transfers identity into `ValidateIntent()` and `ExecuteIntent()`.
- **Position Registration**: Passed explicitly into `PositionManagerRegister()` without default fallbacks.
- **In-Memory Retention**: Saved in `g_positions[n].horizon` and used on every timer tick.
- **Vulnerability Found**: If MT5 crashes or restarts, in-memory array `g_positions[]` is wiped. While tickets can be re-enumerated, **horizon identity is currently not reconstructed from persistent storage**, causing recovered positions to lose their horizon context.

---

## 3. Position Management Differentiation Analysis

- **Scalping**: Confirmed 33% BE trigger, 15% trailing ratchet, 1.0x ATR trail, and 3600-second non-BE liquidation (`SCALP_TIME_EXPIRED`).
- **Intraday**: Confirmed 50% BE trigger, 25% trailing ratchet, 1.5x ATR trail, 2.0R partial exit, and end-of-session liquidation (`INTRADAY_SESSION_CLOSE`).
- **Swing**: Confirmed 60% BE trigger, 35% trailing ratchet, 2.5x ATR trail, and complete exemption from intraday session and time expirations.

---

## 4. Netting & Hedging Account Considerations

- On **Hedging Accounts**, multiple orders open separate broker positions, each with distinct tickets that map 1:1 to `g_positions[]`.
- On **Netting Accounts**, opposing or supplementary orders collapse into a single aggregate position ticket. The current MQL5 implementation cannot maintain multiple independent horizon life-cycles on a single netting instrument simultaneously.

---

## 5. Build, Test & Isolation Status

- **Python Suite**: 98 passed, 0 failed, 2 skipped (100% reference model coverage).
- **MQL5 Compilation**: All scripts and main EA compile with 0 errors and 0 warnings.
- **Native MT5 Execution**: **NOT EXECUTED**. Blocked by terminal isolation requirement **BLK-001**. `run_offline_backtest.bat` must not be executed until network isolation is enforced at the operating system firewall level.

---

## 6. Categorized Verdicts

1. **Horizon Identity Implementation**: **SOURCE-VERIFIED**
2. **Horizon-Specific Management Implementation**: **SOURCE-VERIFIED**
3. **Horizon-Specific Runtime Behaviour**: **UNVERIFIED (Pending Terminal Isolation)**
4. **Position Recovery and Accounting**: **DEFECTIVE / UNVERIFIED (State lost on terminal reboot)**
5. **Python / MQL5 Parity**: **TEST-VERIFIED**
6. **Native MT5 Execution**: **BLOCKED (BLK-001)**
