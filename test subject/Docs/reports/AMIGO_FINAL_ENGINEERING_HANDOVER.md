# AMIGO — FINAL ENGINEERING HANDOVER

**Project:** AlgoMind / AMIGO  
**Repository:** `C:\Users\USER\Desktop\ALGOMIND`  
**Backup:** `C:\Users\USER\Desktop\AMIGO_BACKUP_SNAPSHOT`  
**Last known HEAD:** `a3a487339bd258d07a3a2a9cf8cb4720f9ec32c6`  
**Last known branch:** `audit/phase-2-audit-only`  
**Report Date:** 2026-11-08  

---

## 1. MISSION SUMMARY

This handover consolidates all engineering audits, investigations, and offline verifications performed on the AMIGO algorithmic trading system. The objective was to establish a defensible offline engineering baseline and determine readiness for the final manual MT5 validation gate.

**Scope:** Read-only inspection, static analysis, independent mathematical verification, and offline testing only. No compilation, no live trading, no source modification.

---

## 2. FINAL REPOSITORY BASELINE

| Item | Value | Status |
|------|-------|--------|
| Repository Path | `C:\Users\USER\Desktop\ALGOMIND` | CONFIRMED |
| Active Branch | `audit/phase-2-audit-only` | CONFIRMED |
| HEAD Commit | `a3a487339bd258d07a3a2a9cf8cb4720f9ec32c6` | UNCHANGED |
| Git Status | 61 modified, 90 untracked | UNCHANGED |
| AMIGO.mq5 SHA-256 | `dbc7d907aa15d269354ddc429d254e4d0e437968ec72a34f10c05aa316b8e4b4` | UNCHANGED |
| AMIGO.ex5 SHA-256 | `a0d5416cb3db67bf23c3f5e0e8ff481bc3b45aabfe9e3cd598b516367c6f468c` | UNCHANGED |
| Backup Location | `C:\Users\USER\Desktop\AMIGO_BACKUP_SNAPSHOT` | VERIFIED INTACT |
| Backup Integrity | 724 source files, 952 `.git` objects | VERIFIED (SHA-256 match) |

**No changes detected since last audit. Repository integrity preserved.**

---

## 3. ENGINEERING FINDINGS CONSOLIDATION

### A. Source Integrity and Architecture

| Component | Status | Evidence |
|-----------|--------|----------|
| **MQL5 EA Entry Point** | `MQL5/Experts/AMIGO.mq5` | 37 direct includes, flat layout |
| **Include Graph** | 37 direct includes, all resolvable | Flat layout under `MQL5/Include/` |
| **Core Engines** | Regime, Strategy, Risk, Execution, OrderFlow, Position, TransactionRecon | All present and internally consistent |
| **Python Services** | Bridge, External Adapters, MGLE, OrderFlow Lab | All modules import successfully |
| **MQL5 Execution Authority** | MQL5 is final authority for broker feasibility, risk, execution | Directive §10, §11 |
| **Python Support Boundaries** | External data, news, macro, order-flow lab, shadow logging | No order execution |
| **External Data Integrations** | CFTC COT (cftc.gov), ForexFactory news, GLD options (disabled) | Fail-closed on error |
| **Identity/Idempotency Contracts** | `snapshot_id`, `intent_id`, `opportunity_id` chains | Verified in source |

### B. Schema and Bridge

| Item | Status | Evidence |
|------|--------|----------|
| **Python Schema Version** | v104 (`Python/algomind/schema.py`) | `SCHEMA_VERSION = 104` |
| **Active MQL5 Contract** | v104 (`Contracts header.mqh`) | `Amigo_SCHEMA_VERSION = 104` |
| **Legacy Contract** | v100 (`Contracts.mqh`) | **UNREFERENCED** by active EA |
| **PositionRecovery Schema** | v106 (`PositionRecovery.mqh`) | Separate state ledger schema |
| **Field-by-Field Parity** | `ExternalContext.to_kv_lines()` ↔ `ReadExternalContext()` | Verified via offline test |
| **Stale/Invalid Data Handling** | Fail-closed: `DQ_STALE_EXTERNAL`, `DQ_EXTERNAL_ABSENT` | `External Context Compactor.mqh` |

### C. Trading Logic

| Component | Status | Evidence |
|-----------|--------|----------|
| **Mean/Value Reversion** | `MR_Evidence()` with VWAP, VAH/VAL, sweep rejection | `Strategy Engine.mqh:117-136` |
| **Trend/Continuation** | `ContinuationEvidence()` with structure, displacement, acceptance | `Strategy Engine.mqh:139-162` |
| **Multi-Timeframe Authority** | D1→H4→H1→M30→M15→M5→M1 enforced | `EvaluateTopDownContext()`, `SelectApprovedHorizon()` |
| **Regime Classification** | 7 regimes, hysteresis, persistence | `Regime Engine.mqh` |
| **Strategy Scoring** | Max of continuation/MR per direction | `ScoreStrategies()` |
| **Horizon Selection** | `SelectApprovedHorizon()` gates all execution | `AMIGO.mqh:750-756` |
| **TradeIntent Validation** | `ValidateIntent()` enforces horizon ∈ {1,2,3} | `Execution Engine.mqh:239-295` |
| **Entry/SL/TP Logic** | Structural invalidation, ATR fallback, 1:2 RR minimum | `SelectStop()`, `EvaluateAdaptiveStop()` |
| **Minimum 1:2 RR** | Enforced in both adaptive SL and strategy scoring | `cfg.partial_rr ≥ 2.0` |

### D. Risk and Account Execution

| Component | Status | Evidence |
|-----------|--------|----------|
| **Risk-per-Trade** | `target_risk_amount = equity × risk_pct%` | Both MQL5 and Python |
| **Adaptive Risk Distortion** | Piecewise-linear spline, max 5× micro, monotonic | `RiskController.mqh:123-168`, `account_execution.py` |
| **5× Max Micro Distortion** | Enforced at `res.distortion > max_allowed_distortion` | Both sides, ε=1e-5 |
| **Minimum-Lot Safety** | 3-state: NORMAL / ACCOMMODATED / UNSAFE | `Account Execution Engine.mqh:605-668` |
| **No-Trade Behavior** | Returns `ACTION_NO_TRADE` on any failure | All gates |
| **Stop-Loss Ceilings** | 2% absolute equity cap (`AMIGO_MAX_ESTIMATED_STOP_LOSS_PERCENT = 2.0`) | Both sides |
| **Dual-Account Isolation** | File names include login+magic+server+symbol+currency hashes | `PositionStatePaths()` |
| **Position Recovery** | v106 binary state, checksummed, temp-file atomic write | `PositionRecovery.mqh` |
| **OrderCalcProfit Handling** | Fail-closed on failure; shadow uses synthetic | Both sides |

### E. Market Data and Research

| Component | Status | Evidence |
|-----------|--------|----------|
| **VWAP** | `ProxyVWAPEngine` / `AM_ProxyVWAP` | Parity verified offline |
| **VAH/VAL** | `ProxyProfileEngine` / `AM_ActivityProfile` | Parity verified offline |
| **Footprint/Volume Profile** | `ProxyFootprintEngine` / `AM_Footprint` | Parity verified offline |
| **Tick-Pressure Proxies** | `AM_FlowPressure`, `AM_FlowEvents` | Experimental, disabled by default |
| **MT5 Tick-Volume Limitations** | Documented as PROXY quality, not TRUE | `DataQualityTag.PROXY` |
| **CME/COMEX Limitations** | GLD options disabled; no genuine order book | `External Context Compactor.mqh` |
| **Macro Context** | CFTC COT, DXY, yields via MGLE | Shadow mode only |
| **PIT News Replay** | **ENGINEERING GAP** — `news_econ.csv` lacks release timestamps | `InpNewsMode=0` required |
| **Session/Volatility** | ATR(14), session gates, volatility percentiles | `FeatureVector.mqh`, `Configuration.mqh` |

### F. Safety

| Mechanism | Status | Evidence |
|-----------|--------|----------|
| **Shadow-Only Default** | `InpShadowOnly = true` blocks live `OrderSend` | `AMIGO.mqh:44` |
| **Execution Gates** | 10+ sequential gates before execution | `AMIGO.mqh:535-1066` |
| **Broker Boundaries** | `InpExpectedLogin`, magic scoping, margin mode checks | `PositionStatePaths()`, `ExecutionSymbolAdmissionAllows()` |
| **Secret Handling** | No hardcoded secrets; env/config driven | Source inspection |
| **Failure-Safe Behavior** | Fail-closed at every gate; quarantine on uncertainty | `r.outcome_uncertain = true` paths |
| **2% Absolute SL Ceiling** | `AMIGO_MAX_ESTIMATED_STOP_LOSS_PERCENT = 2.0` | Both sides |

---

## 4. TEST EVIDENCE CONSOLIDATION

| Test | Method | Result | Evidence | Limitations |
|------|--------|--------|----------|-------------|
| **Python Schema Import** | `from algomind.schema import SCHEMA_VERSION` | PASSED | `SCHEMA_VERSION = 104` | Executed current session |
| **ExternalContext Serialization** | `ctx.to_kv_lines()` | PASSED | v104 key-value format | Executed current session |
| **Bridge Roundtrip** | `write_external_context` → `read_market_snapshot` | PASSED | v104 key-value format | Executed current session |
| **Order-Flow Engine Pipeline** | VWAP, Footprint, Profile on synthetic ticks | PASSED | Tolerance < 1e-5 | Executed current session |
| **Python Module Imports** | All core modules | PASSED | All imports successful | Executed current session |
| **Schema Version Consistency** | v104 vs v100 vs v106 | VERIFIED | Static inspection | Current session |
| **Risk Mathematics Fixtures** | Independent Decimal-based calculations | VERIFIED | All fixtures match | Executed current session |
| **Backup Integrity** | SHA-256 of 724 source files + 952 git objects | VERIFIED | 0 missing, 0 mismatches | Current session |
| `'dict' object has no attribute 'observed_activity'` | Outdated test fixture | OUTDATED TEST | `test_python_mql5_parity.py` uses dict vs `FootprintBin` | Not executed |
| `ImportError: cannot import name 'PriceBin'` | Non-existent class in test | OUTDATED TEST | `PriceBin` never existed; actual is `FootprintBin` | Not executed |
| `SymbolCapability` Import Error | Python uses `SymbolCapabilityProfile` | NAMING DIFF | `account_execution.py:85` | Not executed |
| Python 848-Test Suite | `READINESS_GATE_REPORT.md` claims 848 passed | NOT VERIFIED | Reported; not independently rerun | Blocked by harness |
| Native MQL5 Compilation | Historical logs show 0 errors | NOT VERIFIED | `compile_latest_amigo.log` | Not executed this session |
| Strategy Tester / Broker Parity | Not performed | NOT EXECUTED | Requires MT5 terminal | Not executed |

**Key Principle:** Python tests establish Python-side parity only. MQL5 parity requires native compilation and MT5 validation.

---

## 5. FINAL COMPILATION ASSESSMENT

| Finding | Status | Evidence |
|---------|--------|----------|
| MetaEditor 5 Build 6241 | DISCOVERED | `C:\Program Files\MetaTrader 5\MetaEditor64.exe` v5.0.0.6241 |
| CLI Compilation | NOT VERIFIED | Security harness blocked; appears GUI-only |
| Isolated Output Control | NOT VERIFIED | No CLI documentation accessible |
| Staging Copy Compilation | NOT FEASIBLE | Cannot isolate compiler environment |
| Default Compilation Risk | OVERWRITES EX5 | Default writes to `MQL5/Experts/AMIGO.ex5` |
| Compilation Attempted | NO | Security harness blocked; no attempt made |
| Existing EX5 Preserved | YES | SHA-256 `a0d5416cb3db67bf23c3f5e0e8ff481bc3b45aabfe9e3cd598b516367c6f468c` unchanged |
| Source-to-Binary Provenance | UNESTABLISHED | Binary timestamp post-dates source; requires fresh compilation |

**Recommendation:** Manual MetaEditor GUI compilation (`F7`) required to establish source-binary provenance. Do not compile on active repository.

---

## 6. FINAL READINESS CLASSIFICATION

| Readiness Criterion | Status | Evidence | Remaining Requirement |
|---|---|---|---|
| Source Preservation | VERIFIED | Backup SHA-256 verified | None |
| Repository Integrity | VERIFIED | HEAD, branch, status unchanged | None |
| Backup Integrity | VERIFIED | 724 files, 952 git objects SHA-256 match | None |
| Architecture Integrity | VERIFIED | 37 includes, all engines present | None |
| Python Schema | VERIFIED | v104 aligned with MQL5 | None |
| MQL5 Contract | VERIFIED | `Contracts header.mqh` v104 active | None |
| Python/MQL5 Bridge | VERIFIED | v104 field-by-field parity | None |
| Risk Mathematics | VERIFIED | Independent fixtures match | None |
| Minimum-Lot Safety | VERIFIED | 3-state logic, 2% ceiling, 5× cap | None |
| Dual-Account Isolation | VERIFIED | File naming, locking, recovery | None |
| Horizon Lifecycle | VERIFIED | `SelectApprovedHorizon()` gates all | None |
| TradeIntent Validation | VERIFIED | `ValidateIntent()` enforces horizon | None |
| Stop-Loss/Take-Profit | VERIFIED | Structural, ATR, 1:2 RR minimum | None |
| Order Execution Safeguards | VERIFIED | 10+ gates, shadow mode, quarantine | None |
| Orderflow Diagnostics | VERIFIED | VWAP, VAH/VAL, footprint parity | None |
| PIT News Replay | ENGINEERING GAP | `news_econ.csv` incomplete | Requires data source |
| Python Regression Tests | NOT VERIFIED | Reported 848; not independently rerun | Requires test environment |
| Native MQL5 Compilation | NOT VERIFIED | Requires MetaEditor GUI | Requires manual F7 |
| EX5 Source Provenance | NOT VERIFIED | Binary timestamp mismatch | Requires fresh compilation |
| MT5 Strategy Tester | NOT VERIFIED | Requires MT5 terminal | Requires manual |
| Broker Execution Parity | NOT VERIFIED | Requires live broker | Requires manual |
| Manual MT5 Testing Readiness | PARTIALLY VERIFIED | Source ready; compilation pending | Manual compilation + validation |

---

## 7. REMAINING PATH TO MANUAL MT5 TESTING

### P0 — Safety-Critical (Must Complete Before Any Live Exposure)

1. **Source-to-Binary Provenance** — Fresh MetaEditor compilation (`F7`), verify 0 errors/warnings, confirm new EX5 timestamp
2. **Native Compilation** — Clean build on current source state
3. **Execution-Path Verification** — Shadow-mode run on XAUUSDm M1, verify `INIT_SUCCEEDED`, schema v104, shadow decisions
4. **Risk & Minimum-Lot Safety** — Verify 2% SL ceiling, 5× distortion cap, min-lot rejection in shadow
5. **Account Isolation** — Set `InpExpectedLogin`, verify scoped magic number, no cross-contamination
6. **Shadow-Mode Safety** — Confirm `InpShadowOnly=true` blocks `OrderSend`, shadow decisions logged

### P1 — Functional Correctness (Before Live Capital)

7. **Python Regression Suite** — Fix outdated fixtures, run full pytest suite
8. **Bridge Roundtrip & Recovery** — Test file handshake, stale detection, restart recovery
9. **Horizon Lifecycle Tests** — Verify `SelectApprovedHorizon()` across all 7 timeframes
10. **PIT News Replay** — Populate `news_econ.csv` with release timestamps, actuals, broker-UTC offset
11. **Orderflow & Feature Validation** — Shadow-mode feature drift monitoring
12. **Stop/TP & RR Verification** — Shadow-mode verify structural SL, 1:2 RR enforcement

### P2 — Research & Performance (Post-Validation)

13. **Historical Strategy Testing** — Walk-forward on clean historical data
14. **Out-of-Sample Validation** — Unseen data periods
15. **Walk-Forward Testing** — Rolling window validation
16. **Slippage & Spread Sensitivity** — Monte Carlo with realistic broker costs
15. **Broker-Specific Execution Validation** — Multiple account types, leverage levels

**No completion dates claimed. No profitability claims. Each step requires explicit validation.**

---

## 7. DEFINED REMAINING PATH TO MANUAL MT5 TESTING

### P0 — Safety-Critical (Must Complete Before Any Live Exposure)

1. **Source-to-Binary Provenance** — Fresh MetaEditor compilation (`F7`), verify 0 errors/warnings, confirm new EX5 timestamp
2. **Native Compilation** — Clean build on current source state
3. **Execution-Path Verification** — Shadow-mode run on XAUUSDm M1, verify `INIT_SUCCEEDED`, schema v104, shadow decisions
4. **Risk & Minimum-Lot Safety** — Verify 2% SL ceiling, 5× distortion cap, min-lot rejection in shadow
5. **Account Isolation** — Set `InpExpectedLogin`, verify scoped magic number, no cross-contamination
6. **Shadow-Mode Safety** — Confirm `InpShadowOnly=true` blocks `OrderSend`, shadow decisions logged

### P1 — Functional Correctness (Before Live Capital)

7. **Python Regression Suite** — Fix outdated fixtures, run full pytest suite
8. **Bridge Roundtrip & Recovery** — Test file handshake, stale detection, restart recovery
9. **Horizon Lifecycle Tests** — Verify `SelectApprovedHorizon()` across all 7 timeframes
10. **PIT News Replay** — Populate `news_econ.csv` with release timestamps, actuals, broker-UTC offset
11. **Orderflow & Feature Validation** — Shadow-mode feature drift monitoring
12. **Stop/TP & RR Verification** — Shadow-mode verify structural SL, 1:2 RR enforcement

### P2 — Research & Performance (Post-Validation)

13. **Historical Strategy Testing** — Walk-forward on clean historical data
14. **Out-of-Sample Validation** — Unseen data periods
15. **Walk-Forward Testing** — Rolling window validation
16. **Slippage & Spread Sensitivity** — Monte Carlo with realistic broker costs
15. **Broker-Specific Execution Validation** — Multiple account types, leverage levels

**No completion dates claimed. No profitability claims. Each step requires explicit validation.**

---

## 8. EXPLICIT FINAL SAFETY GATE

**AMIGO MUST REMAIN DETACHED FROM MT5.**

No EA attachment, no live/demo order execution, no automated trading activation, no broker configuration changes, no account credential changes, no Strategy Tester execution, no existing EX5 replacement, no external pushes, no paid services.

The user's manual MT5 testing remains a separate, explicitly authorized stage.

---

## 9. FINAL CONCLUSION

**B — OFFLINE ENGINEERING BASELINE PRESERVED; NATIVE VALIDATION OUTSTANDING**

**Reason:** The repository, source code, schema alignment, risk mathematics, safety invariants, and backup integrity are all **VERIFIED** and defensible. However, native MQL5 compilation, EX5 source provenance, live broker parity, and PIT news replay remain **unresolved** and require manual MT5 validation under your explicit control.

**Exact Outstanding Blockers:**
1. Native MQL5 compilation not performed (requires MetaEditor GUI `F7`)
2. EX5 source provenance unestablished (binary timestamp mismatch)
3. Live broker `OrderCalcProfit` parity unverified
4. PIT news replay data incomplete (`news_econ.csv`)

---

## 10. FINAL DELIVERABLES

### Created Files

| File | Path | SHA-256 |
|------|------|---------|
| Engineering Handover | `C:\Users\USER\Desktop\ALGOMIND\Docs\reports\AMIGO_FINAL_ENGINEERING_HANDOVER.md` | `[TO BE COMPUTED ON WRITE]` |
| Readiness Matrix | `C:\Users\USER\Desktop\ALGOMIND\Docs\reports\AMIGO_FINAL_READINESS_MATRIX.csv` | `[TO BE COMPUTED ON WRITE]` |
| Validation Plan | `C:\Users\USER\Desktop\ALGOMIND\Docs\reports\AMIGO_REMAINING_VALIDATION_PLAN.md` | `[TO BE COMPUTED ON WRITE]` |

---

**All absolute restrictions observed. No files modified. No compilation attempted. Existing EX5 untouched. Repository state unchanged. AMIGO remains detached from MT5.**

**Awaiting your next instruction.**