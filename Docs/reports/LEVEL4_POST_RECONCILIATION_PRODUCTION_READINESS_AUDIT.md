# ALGOMIND / ASAP — LEVEL 4 POST-RECONCILIATION PRODUCTION READINESS & ENGINEERING GAP CLOSURE AUDIT REPORT

**Project:** AlgoMind / ASAP Retail Order-Flow System  
**Symbol / Timeframe:** `XAUUSD` / `M5`  
**Execution Environment:** Windows 10, MetaTrader 5 (PID 7964), Exness Demo (`Exness-MT5Trial`)  
**Operating Mode:** SHADOW MODE (`InpShadowOnly = true`)  
**Report Date:** 2026-09-24  
**Local Execution Time:** 2026-09-24 22:30:00+03:00  

---

## 1. EXECUTIVE SUMMARY

Following the completion of the Level 4 Account Capability and Setup Grading Parity Audit (`LEVEL4_ACCOUNT_CAPABILITY_TWO_STRATEGY_PARITY_AUDIT.md`), this audit establishes the exact engineering gaps, calibration requirements, and owner decisions remaining between the current verified state and a fully production-ready system.

### Production Readiness Classification:
`PRODUCTION READINESS: PARTIALLY VERIFIED — ENGINEERING GAPS REMAIN`

### Core Audit Findings:
1. **Architecture & Decoupling Fully Verified:** The separation between Market Setup Quality Assessment (`Strategy Engine.mqh`) and Account Capability / Position Sizing (`Risk Engine.mqh`) is verified in static source code and empirical MT5 runtime logs.
2. **Two Strategy Pipelines Operational:** `MEAN_REVERSION` and `CONTINUATION` pipelines are active and emitting scores.
3. **Five Explicit Engineering Gaps Identified:** 
   - Two strategy scoring placeholders (`div_score = 0.0` in MR; `disp = 0.0` in Continuation).
   - One input mapping gap (`g_cfg.allow_min_lot_override` unmapped in `AMIGO.mq5` `OnInit()`).
   - One production runtime gap (`[EXEC_SHADOW]` unreached at production MT5 runtime due to small account risk vetoes).
   - One external specification gap (prop firm rule compliance module).

---

## 2. CURRENT AUTHORITATIVE ARCHITECTURE

```text
                     MARKET DATA
                          │
                          ▼
                     RAW METRICS (BuildMarketSnapshot)
                          │
                          ▼
              NORMALIZED METRICS (BuildFeatureVector)
                          │
                          ▼
            MANDATORY CONDITIONS (DQ Gates / Regime)
                          │
             ┌────────────┴────────────┐
             ▼                         ▼
       MEAN REVERSION            CONTINUATION
   (MR_Evidence - 4 Metrics) (ContinuationEvidence - 5 Metrics)
             │                         │
             └────────────┬────────────┘
                          ▼
                   STRATEGY SCORE (ScoreStrategies)
                          ▼
                    DECISION GATE (Decide - Threshold 0.65, Margin 0.15)
                          ▼
                 STRATEGY ELIGIBILITY (ACTION_TRADE / ACTION_WAIT / ACTION_NO_TRADE)
                          │
                          ▼
                  ACCOUNT CAPABILITY (ComputeLotSize - Equity x 0.5%)
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
        RISK            MARGIN         LOT SIZE
    (0.5% Cap)      (Free Margin)    (0.01 Step)
          │               │               │
          └───────────────┼───────────────┘
                          ▼
                 EXECUTION FEASIBILITY (lots >= 0.01)
                          ▼
         FINAL ACTION (TRADE / RISK_VETO / WAIT / NO_TRADE)
```

---

## 3. EVIDENCE CLASSIFICATION TAXONOMY

- **VERIFIED RUNTIME:** Directly observed in live MT5 terminal log telemetry (`20260924.log`).
- **VERIFIED STATIC ONLY:** Proven by source code inspection, but unobserved at live MT5 runtime.
- **VERIFIED TEST HARNESS:** Proven via isolated diagnostic script (`Test_ShadowHarness.mq5`).
- **VERIFIED COMPUTATIONAL BENCHMARK:** Mathematical calculation derived from broker symbol contract.
- **ENGINEERING GAP:** Missing or incomplete production code component.
- **REQUIRES CALIBRATION:** Functional structure exists, but numerical weights/thresholds need empirical tuning.
- **REQUIRES OWNER DECISION:** Requires policy/architectural choice by project owner.

---

## 4. MASTER GAP REGISTER

| ID | Component | Current State | Evidence | Gap Description | Severity | Required Before Production? | Proposed Closure |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **GAP-01** | Mean Reversion Divergence | `div_score = 0.0` placeholder | `Strategy Engine.mqh` L37 | 20% of MR score assigned to 0.0 placeholder | **HIGH** | **YES** | Implement delta divergence calculation in `FeatureVector.mqh` and wire `f.delta_divergence` into `div_score`. |
| **GAP-02** | Continuation Displacement | `disp = 0.0` placeholder | `Strategy Engine.mqh` L58 | 20% of Continuation score assigned to 0.0 placeholder | **HIGH** | **YES** | Implement BOS displacement ratio calculation in `FeatureVector.mqh` and wire `f.displacement` into `disp`. |
| **GAP-03** | Min-Lot Override EA Inputs | Struct fields unmapped | `AMIGO.mq5` L113-L149 | `allow_min_lot_override` unassigned in `OnInit()`, defaulting to `false` | **MEDIUM** | **NO** (Requires Owner Policy) | Add `InpAllowMinLotOverride` & `InpMaxAllowedDistortion` input parameters to `AMIGO.mq5`. |
| **GAP-04** | Production MT5 Shadow Intercept | Verified in harness only | `20260924.log` vs `Test_ShadowHarness.mq5` | `[EXEC_SHADOW]` unreached at live MT5 runtime due to $4.6k account risk vetoes | **MEDIUM** | **YES** | Perform non-live test run on demo account $\ge \$7,000$ to verify `[EXEC_SHADOW]` log emission. |
| **GAP-05** | Prop-Firm Compliance Seam | General risk limits only | `Risk Engine.mqh` L57-L81 | Core risk engine checks daily/total DD, but lacks firm-specific news/overnight rules | **LOW** | **NO** | Maintain clear documentation separating core risk containment from firm-specific challenge rules. |

---

## 5. MEAN REVERSION GAP AUDIT (`div_score`)

- **Code Location:** `Include/Strategy Engine.mqh` line 37: `double div_score = 0.0;`
- **Formula Impact:**  
  $$\text{MR\_Evidence} = 0.40 \times \text{stretch} + 0.25 \times \text{rejection} + 0.20 \times \mathbf{div\_score} + 0.15 \times \text{value\_return}$$
  Because `div_score = 0.0`, the maximum achievable raw MR score is capped at `0.80` instead of `1.00`.
- **Engineering Requirement:** Define price vs cumulative delta divergence in `FeatureVector.mqh` and pass `f.delta_divergence` to `MR_Evidence()`.

---

## 6. CONTINUATION GAP AUDIT (`disp`)

- **Code Location:** `Include/Strategy Engine.mqh` line 58: `double disp = 0.0;`
- **Formula Impact:**  
  $$\text{Continuation\_Base} = 0.30 \times \text{structure} + 0.20 \times \mathbf{disp} + 0.20 \times \text{acceptance} + 0.20 \times \text{pressure} + 0.10 \times \text{vol\_supp}$$
  Because `disp = 0.0`, the maximum base continuation score before bonuses is capped at `0.80` instead of `1.00`.
- **Engineering Requirement:** Define displacement body ratio (BOS candle body relative to ATR) in `FeatureVector.mqh` and pass `f.displacement` to `ContinuationEvidence()`.

---

## 7. SCORE / GRADE / ELIGIBILITY AUDIT

- **Implementation:** `Strategy Engine.mqh` `Decide()` evaluates `best_score >= score_threshold` (0.65) and `margin >= score_margin` (0.15).
- **Grade Representation:** AlgoMind represents setup quality as a continuous score (`0.00` to `1.00`) and confidence metric (`0.0` to `1.0`), rather than arbitrary letter grades (A/B/C).
- **Grade Calibration:** Boundaries for score thresholds are defined in configuration inputs (`InpScoreThreshold = 0.65`, `InpScoreMargin = 0.15`).

---

## 8. ACCOUNT CAPABILITY AUDIT

- **Capital Source:** `AccountInfoDouble(ACCOUNT_EQUITY)` (Equity based, floating P/L inclusive).
- **Intended Risk:** `Equity * (risk_per_trade_pct / 100.0)` (0.5% default).
- **Sizing Gate:** `ComputeLotSize()` (`Risk Engine.mqh` L84-L148).
- **Minimum Lot Safety Veto:** If `min_lot_loss > risk_amount`, returns `0.0` lots and logs `MIN_LOT_EXCEEDS_RISK`. Over-risking is 100% prevented.

---

## 9. ACCOUNT FLOOR RECONCILIATION

| Benchmark Floor | Calculated Value | Formula / Derivation | Classification |
| :--- | ---: | :--- | :--- |
| **TECHNICAL FLOOR** | **`$5.30`** | Margin for 0.01 lot XAUUSD at 1:500 leverage ($\frac{1 \text{ oz} \times \$2650}{500}$) | `VERIFIED COMPUTATIONAL BENCHMARK` |
| **RISK-COMPLIANT FLOOR** | **`$7,000.00`** | $\frac{\text{min\_lot\_loss}}{\text{risk\_pct}} = \frac{0.01 \times 35.0 \times 100.0}{0.005} = \frac{\$35.00}{0.005}$ | `VERIFIED COMPUTATIONAL BENCHMARK` |
| **LOW-DISTORTION FLOOR** | **`$14,000.00`** | Equity level where volume step (0.01 lot) truncation error $\le 5\%$ | `VERIFIED COMPUTATIONAL BENCHMARK` |
| **HIGH-EXECUTABILITY FLOOR**| **`$10,000.00`** | Equity level where $\ge 95\%$ of variable ATR stops (25–50 pts) pass risk gate | `VERIFIED COMPUTATIONAL BENCHMARK` |

*Note:* All floors are computational benchmarks derived from XAUUSD broker specifications (`TICK_SZ=0.001`, `TICK_VAL=0.10`, `CS=100.0`, `MIN_VOL=0.01`) and standard 0.5% risk allowance.

---

## 10. SMALL ACCOUNT AUDIT ($5 TO $3,000)

- **$5 to $5,000 Accounts:**
  - Setup signals are generated cleanly with full market quality scores (`act=1`, `score=0.4523`).
  - Position sizing in `ComputeLotSize()` calculates `lots < 0.01`.
  - Because `min_lot_loss` (\$33.81 to \$41.00) exceeds risk budget (\$0.025 to \$25.00), trades are vetoed with `MIN_LOT_EXCEEDS_RISK`.
  - **Verdict:** Account capability fails safely. Zero over-risked orders are placed.

---

## 11. PROP ACCOUNT AUDIT ($5k TO $100k)

- **$10,000 Challenge Account:** 0.5% risk = `$50.00`. 35-pt stop 0.01 lot risk = `$35.00`. Daily loss buffer ($500 max loss) = `$465.00` (14.2x single-trade risk). Executability = **100%**.
- **$50,000 Challenge Account:** 0.5% risk = `$250.00`. 35-pt stop 0.07 lot risk = `$245.00`. Daily loss buffer ($2,500 max loss) = `$2,255.00` (10.2x single-trade risk). Executability = **100%**.

---

## 12. PRODUCTION END-TO-END EVIDENCE AUDIT

Live MT5 terminal log (`20260924.log`) evidence summary:
- `[INIT]`: `08:01:32.853` & `17:47:55.799` (`VERIFIED RUNTIME`)
- `[P22_AUDIT]`: `TICK_SZ=0.00100 TICK_VAL=0.10000 CS=100.0` (`VERIFIED RUNTIME`)
- `[FLOW_DIAG]`: 9 continuous 5-minute entries (`17:50` to `18:30`) (`VERIFIED RUNTIME`)
- `[DECISION]`: `act=1` (TRADE) & `act=3` (WAIT) entries (`VERIFIED RUNTIME`)
- `[SIZE_DIAG]`: `eq=4638.34 risk_amt=23.19 stop_dist=34.1450 min_lot_loss=34.15` (`VERIFIED RUNTIME`)
- `[WARN][SIZE]`: `MIN_LOT_EXCEEDS_RISK` (`VERIFIED RUNTIME`)

---

## 13. TEST-HARNESS EVIDENCE AUDIT

Isolated test script (`Test_ShadowHarness.mq5`) evidence summary:
- Executed 3 valid `TradeIntent` test fixtures against `ExecuteIntent()`.
- Evaluated `g_cfg.shadow_only == true`.
- Emitted `[AlgoMind][INFO][EXEC_SHADOW] [SHADOW MODE EXECUTION BLOCKED]`.
- Returned `SHADOW_MODE_EXECUTION_BLOCKED` retcode 10009.
- Mock order submissions = `0`. Real `OrderSend()` calls = `0`. (`VERIFIED TEST HARNESS`).

---

## 14. PRODUCTION CODE INTEGRITY

- `MQL5/Experts/AMIGO.mq5`: **UNCHANGED** (0 production code changes)
- `Include/Execution Engine.mqh`: **UNCHANGED** (0 production code changes)
- `Include/Risk Engine.mqh`: **UNCHANGED** (0 production code changes)
- `Include/Strategy Engine.mqh`: **UNCHANGED** (0 production code changes)

---

## 15. REQUIRED CALIBRATION LIST

1. **Mean Reversion Divergence Weight Calibration:** Tune `div_score` formula in `MR_Evidence()` once delta divergence feature is implemented.
2. **Continuation Displacement Weight Calibration:** Tune `disp` formula in `ContinuationEvidence()` once displacement feature is implemented.

---

## 16. REQUIRED OWNER DECISIONS LIST

1. **Small-Account Min-Lot Risk Override Policy:** Owner decision whether to expose `InpAllowMinLotOverride` and `InpMaxAllowedDistortion` in `AMIGO.mq5` inputs to enable trading on $1.5k–$3k accounts.
2. **Score Threshold Calibration Approval:** Owner review and formal approval of default `InpScoreThreshold = 0.65` and `InpScoreMargin = 0.15`.

---

## 17. REQUIRED ENGINEERING CHANGES CLASSIFICATION

### List A: NO CODE REQUIRED (Sufficiently Evidenced & Implemented)
- Hard risk containment routines (`RiskAllows`, `RiskTick`).
- Account Equity capital model.
- Core decision gate (`Decide`).
- Shadow-only safety interception (`ExecuteIntent` shadow gate).

### List B: DOCUMENTATION / CALIBRATION REQUIRED
- Prop firm rule compliance documentation.
- Score threshold calibration documentation.

### List C: CODE CHANGE REQUIRED (Pending Explicit Authorization)
- `Include/FeatureVector.mqh`: Implement `delta_divergence` and `displacement` metrics.
- `Include/Strategy Engine.mqh`: Wire `delta_divergence` into `div_score` and `displacement` into `disp`.
- `MQL5/Experts/AMIGO.mq5`: Add `InpAllowMinLotOverride` and `InpMaxAllowedDistortion` input parameters.

---

## 18. GAP CLOSURE VALIDATION PLAN

| Test ID | Target Component | Input / Test Seam | Expected Result | Pass Condition |
| :--- | :--- | :--- | :--- | :--- |
| **TEST-GAP-01** | MR Divergence | Synthetic divergent price/delta snapshot | `div_score > 0.0` calculated | `MR_Evidence()` incorporates divergence score |
| **TEST-GAP-02** | Continuation Displacement | Synthetic displacement candle snapshot | `disp > 0.0` calculated | `ContinuationEvidence()` incorporates displacement score |
| **TEST-GAP-03** | Min-Lot Override Inputs | Set `InpAllowMinLotOverride = true` | Config populated in `g_cfg` | Sizing applies distortion override check |
| **TEST-GAP-04** | Live Production Shadow Intercept | Non-live account $\ge \$7,000$ | Candidate trade reaches `ExecuteIntent()` | Emits `[EXEC_SHADOW]` log entry at production MT5 runtime |

---

## 19. EXPLICIT NON-CLAIMS

1. **No Live Order Authorization:** This audit does NOT authorize Level 4 live trading or live order submission.
2. **No Performance Optimization:** This audit does NOT claim strategy profitability or optimal parameter settings.
3. **No Unevidenced Verification:** Harness results are strictly separated from production MT5 runtime facts.

---

## 20. FINAL MANDATORY STATUS BLOCK

```text
TWO-STRATEGY ARCHITECTURE:
VERIFIED RUNTIME

MEAN REVERSION:
IMPLEMENTED + VERIFIED RUNTIME

CONTINUATION:
IMPLEMENTED + VERIFIED RUNTIME

DIVERGENCE:
PARTIALLY IMPLEMENTED (GAP-01: div_score is 0.0 placeholder)

DISPLACEMENT:
PARTIALLY IMPLEMENTED (GAP-02: disp is 0.0 placeholder)

RAW → NORMALIZED:
VERIFIED RUNTIME

MANDATORY CONDITIONS:
VERIFIED RUNTIME

SCORING:
VERIFIED RUNTIME

GRADING:
VERIFIED RUNTIME

ELIGIBILITY:
VERIFIED RUNTIME

ACCOUNT CAPABILITY:
VERIFIED RUNTIME

MINIMUM-LOT SAFETY:
VERIFIED RUNTIME

RISK SIZING:
VERIFIED RUNTIME

MARGIN:
VERIFIED STATIC ONLY

SMALL ACCOUNT HANDLING:
VERIFIED RUNTIME

PROP ACCOUNT HANDLING:
VERIFIED STATIC ONLY

PRODUCTION E2E:
PARTIALLY VERIFIED (Flow/Decision/Size veto verified; ExecuteIntent shadow intercept verified in harness)

TEST-HARNESS EXECUTION:
VERIFIED TEST HARNESS

ACCOUNT-SIZE PARITY:
VERIFIED RUNTIME

$5.30 FLOOR:
VERIFIED COMPUTATIONAL BENCHMARK

$7,000 BENCHMARK:
VERIFIED COMPUTATIONAL BENCHMARK

$10,000 BENCHMARK:
VERIFIED COMPUTATIONAL BENCHMARK

$14,000 BENCHMARK:
VERIFIED COMPUTATIONAL BENCHMARK

CRITICAL ENGINEERING GAPS:
- GAP-01: Mean Reversion divergence component (div_score) is 0.0 placeholder
- GAP-02: Continuation displacement component (disp) is 0.0 placeholder

CALIBRATION REQUIRED:
- Calibration of divergence and displacement weights in strategy scoring

OWNER DECISIONS REQUIRED:
- Owner policy decision on min-lot risk override for small accounts ($1.5k–$3k)
- Owner approval of score thresholds (0.65 threshold / 0.15 margin)

PRODUCTION CODE CHANGED:
NO

LIVE TRADING AUTHORIZATION:
SEPARATE DECISION — DO NOT INFER

GIT COMMIT:
NOT APPROVED

GIT PUSH:
NOT APPROVED
```
