# AMIGO — Final Independent Acceptance Gate

**Document Date:** 2026-11-02  
**Baseline Git Commit:** `61bed6014fbebb0ebd25678d4047ffc56d9074a8`  
**Consolidated P0 Verification Pass**  
**Role:** Adversarial Senior MQL5 Architect & Principal Quantitative Verification Lead  

---

## 1. Domain-by-Domain Final Acceptance Matrix

| Domain | Source Reference | Deterministic Test / Evidence | Residual Gap / Risk | Final Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **P0.1 Break-Even Decoupling** | `Position Manager.mqh:282-329` | Static control-flow trace; runs prior to `TRAIL_OFF` exit | None. Completely decoupled. | ✅ **ACCEPTED** |
| **P0.2 Broker Confirmation Gating** | `Position Manager.mqh:301-321, 363-378, 408-424` | Modifications gated inside `if(modify_success)` and `if(mod_ok)` | Broker error recovery is tick-retry based; no exponential backoff. | ✅ **ACCEPTED** |
| **P0.3 Partial Exit Gating & Volume Step** | `Position Manager.mqh:246-274` | `RoundVolume()` + dual-min volume check | Shadow mode marks partial complete regardless of lot feasibility. | ✅ **ACCEPTED (Live Mode)** |
| **P0.4 Netting Account Safety** | `AMIGO.mq5:550-559` | Direct `ACCOUNT_MARGIN_MODE_RETAIL_NETTING` check | Does not check magic number (blocks on manual trades). | ✅ **ACCEPTED (Conservative)**|
| **P0.5 Neutral HTF Leak Elimination** | `Regime Engine.mqh:30-67` | Mathematical proof: max neutral score is $0.500 < 0.600$ | None. Zero-credit strictly enforced. | ✅ **ACCEPTED** |
| **P0.6 Conjunctive Countertrend Gate** | `Regime Engine.mqh:85-95` | `if(!sweep_reject \|\| dev < 2.0) return 0.0;` | `rs.risk_modifier = 0.5` is not consumed by downstream sizing. | ⚠️ **PARTIALLY ACCEPTED** |
| **P0.7 Top-Down Integration** | `AMIGO.mq5:434`, `Regime Engine.mqh:100` | `EvaluateRegime(g_feat, td, g_cfg)` actively passed | D1 and M1 structures are computed but idle in scoring. | ✅ **ACCEPTED** |
| **P0.8 Horizon Identity Propagation** | `Contracts header.mqh:207`, `AMIGO.mq5:603, 635` | `TradeIntent.horizon` and `PositionState.horizon` verified | Horizon selection is statically bound to execution timeframe. | ✅ **ACCEPTED** |
| **P0.9 Restart Recovery Engine** | `Position Manager.mqh:32`, `AMIGO.mq5:OnInit` | Static trace: `g_positions[]` is transient in-memory array | **Zero recovery logic exists in `OnInit()`. Positions orphaned on crash.** | ❌ **REJECTED (KNOWN GAP)** |
| **P0.10 Core Protected Files Invariance** | `FeatureVector.mqh`, `Strategy Engine.mqh` | SHA256 hashes match baseline: `9E8B6327...` / `94BC13B7...` | None. Untouched. | ✅ **ACCEPTED** |
| **P0.11 Economic Profitability Proof** | N/A | Offline tests only; no live broker trades executed | **Unverified empirically without clean multi-month OOS backtest.** | ⚠️ **ECONOMICALLY UNVERIFIED** |

---

## 2. Summary of Residual Architectural & Operational Deficiencies

1. **Terminal Restart Recovery (CRITICAL GAP):**
   - Active position states exist solely in transient RAM (`g_positions[]`). A terminal crash or chart reload leaves open broker positions completely unmanaged by the EA. Operator manual intervention is strictly required upon unexpected reboots.
2. **Countertrend Risk Modifier Downstream Disconnect:**
   - Although `rs.risk_modifier = 0.5` is correctly assigned during `REGIME_EXHAUSTION`, `AMIGO.mq5` calculates trade sizing directly via `RiskControllerEvaluate()` without multiplying the returned risk budget by `rs.risk_modifier`.
3. **Timeframe Utilization Imbalance:**
   - D1 and M1 are sampled via `CopyRates` in `EvaluateTopDownContext()`, but neither contributes to trend scoring or alignment synthesis.

---

## 3. Final Overall Acceptance Statement

The critical P0 safety, mathematical consistency, and execution gating remediations are **FUNCTIONALLY VERIFIED AND ACCEPTED FOR CONTINUED CONTROLLED TESTING**. 

All changes compile cleanly (0 errors, 0 warnings across all 4 targets), all 98 Python parity tests pass, and core protected files remain bit-for-bit identical to baseline. Live trading authorization remains subject to resolving the restart recovery mechanism and testing under terminal isolation once BLK-001 is cleared.
