# AMIGO — P0 Adversarial Test Report

**Document Date:** 2026-11-02  
**Test Suite Reference:** Offline Deterministic Tests & Static Code Invariants  
**Evaluator:** Antigravity Adversarial QA Lead  

---

## 1. Adversarial Invariant Matrix

| ID | Test Vector / Invariant | Method | Expected Result | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **ADV-01** | Neutral HTF Trend Infiltration | Analytical Formula Evaluation | Max score $< 0.60$ | Max score $= 0.500$ | ✅ **PASS** |
| **ADV-02** | Opposing HTF Counter-Trend Leaks | Analytical Formula Evaluation | Max score $< 0.60$ | Max score $= 0.475$ | ✅ **PASS** |
| **ADV-03** | Countertrend Sweep without VWAP Extension | Conjunctive Gate Code Walk | Score $= 0.00$ | Line 89 returns $0.0$ immediately | ✅ **PASS** |
| **ADV-04** | Countertrend VWAP Extension without Sweep | Conjunctive Gate Code Walk | Score $= 0.00$ | Line 89 returns $0.0$ immediately | ✅ **PASS** |
| **ADV-05** | Break-Even when `TRAIL_OFF` Selected | Static Source Execution Trace | BE runs independently | Evaluated at line 284 prior to `TRAIL_OFF` exit at 332 | ✅ **PASS** |
| **ADV-06** | Rejected Broker Modification State Retention| Failure Injection Trace | `be_activated` stays false | State update strictly inside `if(modify_success)` | ✅ **PASS** |
| **ADV-07** | Rejected Partial Close State Retention | Failure Injection Trace | `partial_done` stays false | State update strictly inside `if(PositionClosePartial)` | ✅ **PASS** |
| **ADV-08** | Retail Netting Multiple Position Block | Source Netting Gate Trace | OrderSend blocked | Returns immediately with `NETTING_CONCURRENT_POSITION_BLOCKED` | ✅ **PASS** |
| **ADV-09** | Zero Division on Missing ATR | Null Input Evaluation | Safe abort | `if(atr <= 0.0) return;` at line 484 | ✅ **PASS** |
| **ADV-10** | Terminal Crash State Recovery | Reboot Simulation Trace | Positions recovered | `g_positions[]` wiped; **No recovery logic in `OnInit()`** | ❌ **FAIL (Gapped)** |

---

## 2. Compilation and Static Integrity Verification

1. **Clean MQL5 Targets:**
   - `MQL5/Experts/AMIGO.mq5`: 0 Errors, 0 Warnings.
   - `MQL5/Scripts/Test_ShadowHarness.mq5`: 0 Errors, 0 Warnings.
   - `MQL5/Scripts/Test_HorizonPropagation.mq5`: 0 Errors, 0 Warnings.
   - `MQL5/Scripts/Test_RegimeReachability.mq5`: 0 Errors, 0 Warnings.
2. **Protected Core Invariance:**
   - `FeatureVector.mqh`: SHA256 matches baseline `9E8B6327...`
   - `Strategy Engine.mqh`: SHA256 matches baseline `94BC13B7...`
   - Zero modifications permitted or executed.

- **Status:** **ALL CODE-LEVEL INVARIANTS PASS; RESTART RECOVERY CONFIRMED FAILED BY DESIGN (GAP).**
