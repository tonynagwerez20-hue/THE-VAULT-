# AMIGO — Position Recovery Test Report

**Document Date:** 2026-11-02  
**Test Suite Reference:** Offline Deterministic Fixtures & Binary Serialization Verification  
**Evaluator:** Antigravity Adversarial QA Specialist  

---

## 1. Test Matrix: Recovery Scenarios

| Test ID | Scenario | Input State | Expected Outcome | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **REC-01** | Clean Startup | No file exists on disk | Returns 0, empty array, clean log | `PositionReconcileState` returns 0 | ✅ **PASS** |
| **REC-02** | Normal Save & Reload | 3 active positions (Scalp, Intraday, Swing) | All 3 restored with identical horizons | Binary serialization matches bit-for-bit | ✅ **PASS** |
| **REC-03** | Schema Mismatch | Schema version = 99 in file header | Reject entire file, log warning | Rejected; array unchanged | ✅ **PASS** |
| **REC-04** | Magic Number Mismatch | Magic = 999999 in file header | Reject entire file, log warning | Rejected; array unchanged | ✅ **PASS** |
| **REC-05** | Offline Position Closure | Ticket 12345 in file, but closed on broker | Omit ticket 12345 from restored array | Skipped gracefully; remaining restored | ✅ **PASS** |
| **REC-06** | Offline Manual BE Adjustment | SL moved to Entry while offline | Restore with `be_activated = true` | `be_activated` automatically flagged | ✅ **PASS** |
| **REC-07** | Symbol Mismatch | Ticket opened on EURUSD, EA on XAUUSD | Conflict detected; ticket rejected | Omitted from active array | ✅ **PASS** |
| **REC-08** | Corrupted / Truncated File | File truncated mid-record | FileOpen/Read fails gracefully | Fails closed; no invalid array records | ✅ **PASS** |
| **REC-09** | Atomic Replace Under Crash | Crash during file write | Primary file remains uncorrupted | Temp write preserves previous primary | ✅ **PASS** |

---

## 2. Compilation and Invariant Verification

- `MQL5/Include/PositionRecovery.mqh`: Integrated cleanly.
- `MQL5/Experts/AMIGO.mq5`: Compiled with 0 errors, 0 warnings.
- `Test_ShadowHarness.mq5`: Compiled with 0 errors, 0 warnings.
- `Test_HorizonPropagation.mq5`: Compiled with 0 errors, 0 warnings.
- `Test_RegimeReachability.mq5`: Compiled with 0 errors, 0 warnings.

- **Verification Status:** **COMPLETE-VERIFIED (TEST-VERIFIED, DETERMINISTIC-FIXTURES).**
