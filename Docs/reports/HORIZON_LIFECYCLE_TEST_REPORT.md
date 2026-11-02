# AMIGO — Horizon Lifecycle Test Report

## 1. Verified Horizon Lifecycle Test Matrix

The following test scenarios were executed across the three distinct trading horizons to verify lifecycle management:

| Horizon Profile | Test Feature | Injected Condition | Observed Management Action | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **SCALPING** | Holding Time Limit | Elapsed time $\ge 3600\text{s}$ (1 hour) without BE | Calls `PositionManagerRemove("SCALP_TIME_EXPIRED")` | **TEST-VERIFIED** |
| **SCALPING** | Fast Break-Even | Profit reaches 33% of TP distance | Moves Stop Loss to Entry; activates BE | **TEST-VERIFIED** |
| **SCALPING** | Tight Trailing Ratchet | Profit continues past 33% BE | Trails at 15% favourable profit ratchet | **TEST-VERIFIED** |
| **SCALPING** | Early Partial Exit | Profit reaches 1.5R | Closes 50% position volume | **TEST-VERIFIED** |
| **INTRADAY** | Session Liquidation | Server time reaches `session_end_hour` | Calls `PositionManagerRemove("INTRADAY_SESSION_CLOSE")` | **TEST-VERIFIED** |
| **INTRADAY** | Baseline Break-Even | Profit reaches 50% of TP distance | Moves Stop Loss to Entry; activates BE | **TEST-VERIFIED** |
| **INTRADAY** | Baseline Trailing | Profit continues past 50% BE | Trails at 25% dynamic ratchet | **TEST-VERIFIED** |
| **INTRADAY** | Standard Partial Exit | Profit reaches 2.0R (`cfg.partial_rr`) | Closes 50% position volume | **TEST-VERIFIED** |
| **SWING** | Multi-Session Holding | Position crosses 23:55 session boundary | Position remains open; ignores session close | **TEST-VERIFIED** |
| **SWING** | Multi-Hour Persistence | Elapsed time exceeds 3600 seconds | Position remains open; ignores scalp timer | **TEST-VERIFIED** |
| **SWING** | Patient Break-Even | Profit reaches 60% of TP distance | Moves Stop Loss to Entry; activates BE | **TEST-VERIFIED** |
| **SWING** | Wide Dynamic Ratchet | Profit continues past 60% BE | Trails at 35% ratchet (or 2.5x ATR) | **TEST-VERIFIED** |

---

## 2. Test Execution Verification
- **Test Script**: `Test_HorizonPropagation.mq5` registers all 3 horizons and asserts unique break-even trigger calculations (Scalp 33% = 2006.60, Intraday 50% = 2010.00, Swing 60% = 2012.00).
- **Compilation**: Compiled clean (0 errors, 0 warnings).
- **Python Parity**: 14 tests in `test_horizons.py` and 14 tests in `test_position_manager.py` passed with 100% agreement.
