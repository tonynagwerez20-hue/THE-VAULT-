# AMIGO — REMAINING VALIDATION PLAN

**Project:** AlgoMind / AMIGO  
**Repository:** `C:\Users\USER\Desktop\ALGOMIND`  
**Baseline HEAD:** `a3a487339bd258d07a3a2a9cf8cb4720f9ec32c6`  
**Plan Date:** 2026-11-08  

---

## PURPOSE

This document defines the dependency-ordered validation path from the current offline engineering baseline to the final manual MT5 testing gate. Each step must be explicitly validated before proceeding to the next.

**No completion dates claimed. No profitability claims. Each step requires explicit validation evidence.**

---

## PRIORITY ORDERING METHODOLOGY

- **P0 — Safety-Critical:** Must complete before ANY live market exposure (demo or real)
- **P1 — Functional Correctness:** Must complete before risking live capital
- **P2 — Research & Performance:** Post-validation optimization and robustness

---

## P0 — SAFETY-CRITICAL (Must Complete Before ANY Live Exposure)

### P0.1 — Source-to-Binary Provenance
**Objective:** Establish that the compiled EX5 binary corresponds exactly to the audited source state.

| Step | Action | Success Criteria | Evidence Required |
|------|--------|------------------|-------------------|
| 1 | Open `MQL5/Experts/AMIGO.mq5` in MetaEditor 5 | File loads without errors | Screenshot of open file |
| 2 | Verify `#include <Contracts header.mqh>` present; `Contracts.mqh` NOT included | v104 active contract | Source view |
| 3 | Compile via `F7` (Build → Compile) | **0 errors, 0 warnings** | Build log screenshot |
| 4 | Verify new `AMIGO.ex5` timestamp updates | Timestamp > source file timestamp | File properties |
| 5 | Record new EX5 SHA-256 | Hash recorded | `sha256sum AMIGO.ex5` |

**Dependencies:** None  
**Blocking:** All subsequent steps  
**Safety:** `InpShadowOnly=true` MUST remain default

---

### P0.2 — Native Compilation Verification
**Objective:** Confirm clean build on exact audited source state.

| Step | Action | Success Criteria | Evidence Required |
|------|--------|------------------|-------------------|
| 1 | Verify build log shows 0 errors, 0 warnings | Clean build | Build log |
| 2 | Confirm no new warnings vs. historical logs | No regressions | Compare with `compile_latest_amigo.log` |
| 3 | Verify EX5 size reasonable (~280KB) | Size within expected range | File size check |

**Dependencies:** P0.1 complete  
**Blocking:** P0.3, P0.3, P0.4

---

### P0.3 — Execution-Path Verification (Shadow Mode)
**Objective:** Verify complete decision pipeline executes without live orders.

| Step | Action | Success Criteria | Evidence Required |
|------|--------|------------------|-------------------|
| 1 | Attach compiled `AMIGO.ex5` to XAUUSDm chart (M1) | EA loads without errors | Terminal Experts tab |
| 2 | Set inputs: `InpShadowOnly=true`, `InpExpectedLogin=[demo login]` | Inputs accepted | Input dialog |
| 3 | Observe initialization log | `INIT_SUCCEEDED`, schema v104, risk ledger OK | Experts log |
| 4 | Observe at least 3 closed-bar cycles | Shadow decisions logged (`RISK_OP_SHADOW`) | Experts log |
| 5 | Verify NO live orders placed | `OrdersTotal()` = 0 for AMIGO magic | Terminal Trade tab |

**Dependencies:** P0.2 complete  
**Blocking:** P0.4, P0.5

---

### P0.4 — Risk & Minimum-Lot Safety Verification
**Objective:** Confirm risk guards enforce 2% ceiling, 5× distortion cap, min-lot rejection.

| Step | Action | Success Criteria | Evidence Required |
|------|--------|------------------|-------------------|
| 1 | Verify `AMIGO_MAX_ESTIMATED_STOP_LOSS_PERCENT = 2.0` in log | 2% ceiling enforced | Expert log |
| 2 | Verify `InpMaxAllowedDistortion = 5.0` (5× cap) | 5× distortion cap | Input dialog / log |
| 6 | Observe min-lot rejection on micro account (if available) | `FEASIBILITY_MIN_LOT_UNSAFE` → `NO_TRADE` | Experts log |
| 7 | Verify no trade executes when distortion > 5× | `MIN_LOT_UNSAFE` → `NO_TRADE` | Experts log |

**Dependencies:** P0.3 complete  
**Blocking:** Live capital exposure

---

### P0.5 — Account Isolation Verification
**Objective:** Confirm dual-account isolation via `InpExpectedLogin` and magic scoping.

| Step | Action | Success Criteria | Evidence Required |
|------|--------|------------------|-------------------|
| 1 | Set `InpExpectedLogin` to demo account login | Input accepted | Input dialog |
| 2 | Verify EA rejects on wrong account | `ACCOUNT_MISMATCH` → `INIT_FAILED` | Experts log |
| 3 | Verify magic number scoping in position state files | File name includes login+magic | File system check |
| 4 | Verify no cross-contamination on two terminals | Independent state files | File system check |

**Dependencies:** P0.3 complete  
**Blocking:** Multi-account deployment

---

### P0.6 — Shadow-Mode Safety Confirmation
**Objective:** Confirm shadow mode blocks live orders and logs synthetic decisions.

| Step | Action | Success Criteria | Evidence Required |
|------|--------|------------------|------------------|
| 1 | Confirm `InpShadowOnly = true` (default) | Input dialog shows `true` | Input dialog |
| 2 | Verify `SHADOW_MODE_EXECUTION_BLOCKED` log entries | Log present | Experts log |
| 3 | Verify `r.shadow_evaluated = true` in shadow decisions | Log shows shadow evaluation | Experts log |
| 4 | Verify ZERO live orders placed over 10+ bars | `OrdersTotal()` = 0 | Terminal Trade tab |

**Dependencies:** P0.3 complete  
**Blocking:** Any live mode consideration

---

## P1 — FUNCTIONAL CORRECTNESS (Before Live Capital)

### P1.1 — Python Regression Suite Restoration
**Objective:** Fix outdated test fixtures and run full pytest suite.

| Step | Action | Success Criteria | Evidence Required |
|------|--------|------------------|------------------|
| 1 | Fix `test_python_mql5_parity.py`: replace dict bins with `FootprintBin` | Test imports and runs | Updated test file |
| 2 | Fix `PriceBin` → `FootprintBin` references | No import errors | Updated test file |
| 3 | Run `pytest Python/algomind/orderflow_lab/tests/ -v` | All tests pass (target: 848+) | pytest output |
| 4 | Run `pytest Python/algomind/tests/ -v` | All tests pass | pytest output |
| 5 | Document any skipped/xfail tests with reasons | Documented | Test report |

**Dependencies:** Independent (can start immediately)  
**Blocking:** P1.4, P1.5

---

### P1.2 — Bridge Roundtrip & Recovery Testing
**Objective:** Verify file handshake, stale detection, restart recovery.

| Step | Action | Success Criteria | Evidence Required |
|------|--------|------------------|------------------|
| 1 | Test `write_external_context` → `read_market_snapshot` roundtrip | Data integrity preserved | Test output |
| 2 | Test stale bridge file detection (`DQ_STALE_EXTERNAL`) | Stale flag set correctly | Test output |
| 3 | Test restart recovery: kill/restart bridge, verify state | State recovered correctly | Log output |
| 4 | Test corrupted bridge file handling | Fail-closed, no crash | Log output |

**Dependencies:** P1.1 complete  
**Blocking:** Live bridge deployment

---

### P1.3 — Horizon Lifecycle Tests
**Objective:** Verify `SelectApprovedHorizon()` across all 7 timeframes.

| Step | Action | Success Criteria | Evidence Required |
|------|--------|------------------|------------------|
| 1 | Test continuation → SWING (D1+H4+H1 aligned) | `HORIZON_SWING` returned | Unit test |
| 2 | Test continuation → INTRADAY (H1+M30+M15 aligned) | `HORIZON_INTRADAY` returned | Unit test |
| 3 | Test continuation → SCALPING (only M5 aligned) | `HORIZON_SCALPING` returned | Unit test |
| 4 | Test mean-reversion → INTRADAY (H1+M30+M15 neutral) | `HORIZON_INTRADAY` returned | Unit test |
| 5 | Test mean-reversion → SCALPING (M15+M5 neutral) | `HORIZON_SCALPING` returned | Unit test |
| 6 | Test conflicting timeframe → NO_ELIGIBLE_HORIZON | `false` returned | Unit test |

**Dependencies:** P1.1 complete  
**Blocking:** Live horizon-dependent execution

---

### P1.4 — PIT News Replay Implementation
**Objective:** Enable historical news replay with actual release timestamps.

| Step | Action | Success Criteria | Evidence Required |
|------|--------|------------------|------------------|
| 1 | Source actual release timestamps for `news_econ.csv` events | Timestamps populated | Updated CSV |
| 3 | Add actual vs consensus values | Values populated | Updated CSV |
| 4 | Add broker-UTC offset table | Offsets documented | Config file |
| 4 | Implement historical news replay in `news_adapter.py` | Replay functional | Test output |
| 5 | Test `InpNewsMode=1/2/3` with historical data | No `NEWS_REPLAY_REQUIRED` error | Test output |

**Dependencies:** Data sourcing required  
**Blocking:** Any news-enabled mode

---

### P1.5 — Orderflow & Feature Validation (Shadow Mode)
**Objective:** Monitor feature drift and proxy accuracy in shadow mode.

| Step | Action | Success Criteria | Evidence Required |
|------|--------|------------------|------------------|
| 1 | Run shadow mode for 50+ bars | Features stable | Log analysis |
| 2 | Compare Python vs MQL5 VWAP/VAH/VAL on same bars | Drift < 1e-5 | Log comparison |
| 3 | Monitor `FootprintBin` proxy vs MT5 tick volume | Correlation tracked | Log analysis |
| 4 | Document any feature drift > threshold | Threshold documented | Report |

**Dependencies:** P0.3 complete  
**Blocking:** Live feature-dependent execution

---

### P1.6 — Stop/TP & RR Verification
**Objective:** Verify structural SL, ATR fallback, 1:2 RR enforcement in shadow.

| Step | Action | Success Criteria | Evidence Required |
|------|--------|------------------|------------------|
| 1 | Verify structural SL selected when swing exists | `VALID_STRATEGY_STRUCTURE` | Log output |
| 2 | Verify ATR fallback when no structure | `VALID_STRATEGY_ATR` | Log output |
| 3 | Verify RR ≥ 2.0 enforced | `cand_rr >= 2.0` | Log output |
| 4 | Verify adaptive SL respects 2% ceiling | `actual_risk_pct <= 2.0` | Log output |

**Dependencies:** P0.4 complete  
**Blocking:** Live execution

---

## P2 — RESEARCH & PERFORMANCE (Post-Validation)

### P2.1 — Historical Strategy Testing
- Walk-forward on clean historical data (2020-2024)
- No look-ahead bias (PIT news, proper bar closure)
- Document all parameters

### P2.2 — Out-of-Sample Validation
- Unseen data periods (e.g., 2023-2024 if trained on 2020-2022)
- No parameter tuning on OOS data

### P2.3 — Walk-Forward Testing
- Rolling window (e.g., 12-month train, 3-month test)
- Parameter stability analysis

### P2.4 — Slippage & Spread Sensitivity
- Monte Carlo with realistic broker costs
- Spread widening scenarios
- Slippage distribution modeling

### P2.5 — Broker-Specific Execution Validation
- Multiple account types (Standard, Raw Spread, Zero)
- Leverage levels (1:30, 1:100, 1:500)
- Commission structures

---

## DEPENDENCY GRAPH

```
P0.1 → P0.2 → P0.3 → P0.4, P0.5, P0.6
                                    ↓
P1.1 → P1.2, P1.3 → P1.4, P1.5, P1.6
                                    ↓
P2.1 → P2.2 → P2.3 → P2.4 → P2.5
```

---

## DECISION GATES

| Gate | Criteria | Authority |
|------|----------|-----------|
| **Gate 0** | Source-binary provenance established | User authorization |
| **Gate 1** | P0.1-P0.6 all PASS | User authorization |
| **Gate 2** | P1.1-P1.6 all PASS | User authorization |
| **Gate 3** | P2.1-P2.5 complete | User authorization |

**No gate may be passed without explicit user authorization and documented evidence.**

---

**END OF VALIDATION PLAN**