# AlgoMind / ASAP
# GAP-01 / GAP-02 Candidate Evaluation & Selection Audit

**Project:** AlgoMind / ASAP Retail Order-Flow System  
**Symbol / Timeframe:** `XAUUSD` / `M5`  
**Execution Environment:** Windows 10, MetaTrader 5 (PID 7964), Exness Demo (`Exness-MT5Trial`)  
**Operating Mode:** SHADOW MODE (`InpShadowOnly = true`)  
**Report Date:** 2026-09-24  
**Local Execution Time:** 2026-09-24 23:15:00+03:00  

---

## 1. EXECUTIVE SUMMARY & GOVERNANCE ASSURANCE

This report presents a rigorous, evidence-gated research audit evaluating the candidate quantitative specifications documented in `GAP01_GAP02_QUANTITATIVE_SPECIFICATION_PROPOSAL.md` for:
- **GAP-01:** Mean-Reversion Delta Divergence (`div_score`)
- **GAP-02:** Continuation BOS / Displacement (`disp`)

### Non-Negotiable Governance Principles:
1. **Audit & Selection Research Only:** No candidate is implemented into production code during this audit.
2. **Production Code Intact:** `FeatureVector.mqh`, `Strategy Engine.mqh`, `Risk Engine.mqh`, `Execution Engine.mqh`, `AMIGO.mq5`, contracts, risk controls, and execution routines remain **100% UNCHANGED**.
3. **No Unilateral Selection:** The audit evaluates trade-offs and highlights candidates suitable for owner review. The final selection remains blocked pending owner authorization (`GIT COMMIT: NOT APPROVED`, `GIT PUSH: NOT APPROVED`).

---

## 2. AUTHORITATIVE DOCUMENT HIERARCHY & FILE AUDIT

### Authoritative Architecture & Production Code:
- `MQL5/Experts/AMIGO.mq5`: Production EA initialization, event routing, decision pipeline execution.
- `Include/Strategy Engine.mqh`: Strategy scoring logic (`MR_Evidence()`, `ContinuationEvidence()`, `ScoreStrategies()`, `Decide()`).
- `Include/Risk Engine.mqh`: Risk containment and position sizing (`RiskAllows()`, `ComputeLotSize()`).
- `Include/Execution Engine.mqh`: Execution safety gate and order submission (`ExecuteIntent()`).
- `Include/Contracts header.mqh`: Data contracts (`FeatureSnapshot`, `MarketSnapshot`, `TradeIntent`).
- `Include/FeatureVector.mqh`: Feature calculation pipeline (`BuildFeatureVector()`).

### Research & Proposal Audit Reports:
- `Docs/reports/GAP01_GAP02_QUANTITATIVE_SPECIFICATION_PROPOSAL.md`: Quantitative Candidate Proposals.
- `Docs/reports/LEVEL4_POST_RECONCILIATION_PRODUCTION_READINESS_AUDIT.md`: Baseline Gap Identification.
- `Docs/reports/LEVEL4_ACCOUNT_CAPABILITY_TWO_STRATEGY_PARITY_AUDIT.md`: Account Capability & Setup Grading Parity.

---

## 3. GAP-01 CANDIDATE EVALUATIONS (MEAN-REVERSION DELTA DIVERGENCE)

### Candidate A — Swing-to-Swing Peak/Trough Divergence
- **Definition:** Compare price swing points ($P_1, P_2$) against cumulative proxy delta ($D_1, D_2$).
- **Data Availability:** `VERIFIED` (Uses $k$-swings from `Structure Engine.mqh` + cumulative proxy delta).
- **Look-Ahead Safety:** `PARTIALLY VERIFIED` (Requires $k=2$ bar confirmation delay for swing highs/lows).
- **M5 Noise Sensitivity:** `UNVERIFIED` (Low structural noise via $k$-swings, but unverified on historical dataset).
- **Proxy Delta Compatibility:** `PARTIALLY VERIFIED` (Cumulative proxy delta drift over multi-bar swing spans introduces distortion).
- **Feature Overlap:** `MODERATE OVERLAP` (Overlaps with `sweep_reject` and `structure_dir`).

### Candidate B — Rolling Slope Divergence
- **Definition:** Compare rolling 10-bar linear regression slope of price ($\hat{S}_P$) vs cumulative proxy delta ($\hat{S}_D$).
- **Data Availability:** `VERIFIED` (OHLC + cumulative proxy delta over 10 bars).
- **Look-Ahead Safety:** `VERIFIED` (Zero confirmation lag beyond bar close).
- **M5 Noise Sensitivity:** `ENGINEERING GAP` (High sensitivity to 5-minute tick volume spikes; unverified on historical dataset).
- **Proxy Delta Compatibility:** `UNVERIFIED` (Short-window slopes on proxy delta are volatile across broker feeds).
- **Feature Overlap:** `HIGH OVERLAP` (Overlaps heavily with `fusion` and `pressure_state`).

### Candidate C — Value Extension vs Order-Flow Fusion Confirmation
- **Definition:** Compare VWAP stretch ($Z_{\text{vwap}} = |P - \text{VWAP}| / \text{ATR}_{14}$) against directional order-flow fusion ($F_{\text{dir}} = \text{dir} \times \text{fusion}$).
- **Data Availability:** `VERIFIED` (Uses existing `dev_vwap_atr` + `fusion`).
- **Look-Ahead Safety:** `VERIFIED` (Causal point-in-time calculation at bar close).
- **M5 Noise Sensitivity:** `VERIFIED STATIC ONLY` (Low noise sensitivity due to ATR/VWAP smoothing).
- **Proxy Delta Compatibility:** `VERIFIED STATIC ONLY` (Designed specifically for AlgoMind's proxy `fusion` metric).
- **Feature Overlap:** `LOW OVERLAP` (Uniquely couples price value stretch with order-flow exhaustion).

---

## 4. GAP-02 CANDIDATE EVALUATIONS (CONTINUATION DISPLACEMENT)

### Candidate A — ATR-Normalized Structural Break Distance
- **Definition:** Measure $|P_{\text{close}} - P_{\text{BOS}}| / \text{ATR}_{14}$ upon a confirmed BOS.
- **Data Availability:** `VERIFIED` (Uses `Structure Engine.mqh` BOS level + ATR14).
- **Look-Ahead Safety:** `VERIFIED` (Point-in-time calculation on bar close).
- **M5 Noise Sensitivity:** `VERIFIED STATIC ONLY` (Normalized by ATR14).
- **Proxy Delta Compatibility:** `VERIFIED` (Independent of delta data).
- **Feature Overlap:** `LOW OVERLAP` (Measures post-break extension magnitude; strictly additive to `structure_dir`).

### Candidate B — Directional Candle Body Ratio
- **Definition:** Combine directional body ratio ($|P_{\text{close}} - P_{\text{open}}| / \text{Range}$) and body size relative to ATR ($|P_{\text{close}} - P_{\text{open}}| / \text{ATR}_{14}$).
- **Data Availability:** `VERIFIED` (OHLC bar data).
- **Look-Ahead Safety:** `VERIFIED` (Immediate on bar close).
- **M5 Noise Sensitivity:** `UNVERIFIED` (Single-candle bodies on M5 are sensitive to brief liquidity wicks).
- **Proxy Delta Compatibility:** `VERIFIED` (Independent of delta).
- **Feature Overlap:** `HIGH OVERLAP` (Measures candle momentum rather than structural displacement; overlaps with `range_ratio` and `surge`).

### Candidate C — Multi-Bar Post-BOS Acceptance
- **Definition:** Measure cumulative directional progress over 3 bars following BOS relative to ATR14.
- **Data Availability:** `VERIFIED` (Requires 3-bar post-BOS history).
- **Look-Ahead Safety:** `PARTIALLY VERIFIED` (Requires 3-bar execution delay after BOS event).
- **M5 Noise Sensitivity:** `VERIFIED STATIC ONLY` (Low noise due to 3-bar accumulation).
- **Proxy Delta Compatibility:** `VERIFIED` (Independent of delta).
- **Feature Overlap:** `MODERATE OVERLAP` (Overlaps with `acceptance_above` / `acceptance_below`).

---

## 5. EVALUATION CRITERIA AUDIT MATRIX

| Candidate | Criterion A: Data Availability | Criterion B: Look-Ahead Safety | Criterion C: M5 Noise Risk | Criterion D: Proxy Delta Fit | Criterion E: Regime Sensitivity |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **GAP-01 Candidate A** | `VERIFIED` | `PARTIALLY VERIFIED` (2-bar lag) | `UNVERIFIED` | `PARTIALLY VERIFIED` | `UNVERIFIED` |
| **GAP-01 Candidate B** | `VERIFIED` | `VERIFIED` (Causal) | `ENGINEERING GAP` | `UNVERIFIED` | `UNVERIFIED` |
| **GAP-01 Candidate C** | `VERIFIED` | `VERIFIED` (Causal) | `VERIFIED STATIC ONLY` | `VERIFIED STATIC ONLY` | `VERIFIED STATIC ONLY` |
| **GAP-02 Candidate A** | `VERIFIED` | `VERIFIED` (Causal) | `VERIFIED STATIC ONLY` | `VERIFIED` | `VERIFIED STATIC ONLY` |
| **GAP-02 Candidate B** | `VERIFIED` | `VERIFIED` (Causal) | `UNVERIFIED` | `VERIFIED` | `UNVERIFIED` |
| **GAP-02 Candidate C** | `VERIFIED` | `PARTIALLY VERIFIED` (3-bar lag) | `VERIFIED STATIC ONLY` | `VERIFIED` | `UNVERIFIED` |

---

## 6. FEATURE REDUNDANCY & DOUBLE-COUNTING AUDIT

| Feature / Candidate | Overlapping System Features | Redundancy Classification | Recommendation |
| :--- | :--- | :--- | :--- |
| **GAP-01 Candidate A** | `sweep_reject`, `structure_dir` | `MODERATE OVERLAP` | Requires empirical correlation test |
| **GAP-01 Candidate B** | `fusion`, `pressure_state` | `HIGH OVERLAP` | High risk of double-counting order flow |
| **GAP-01 Candidate C** | `dev_vwap_atr`, `fusion` | `LOW OVERLAP` | **Recommended for owner review** |
| **GAP-02 Candidate A** | `structure_dir` | `LOW OVERLAP` | **Recommended for owner review** |
| **GAP-02 Candidate B** | `range_ratio`, `surge` | `HIGH OVERLAP` | High risk of double-counting candle momentum |
| **GAP-02 Candidate C** | `acceptance_above/below` | `MODERATE OVERLAP` | Requires confirmation delay |

---

## 7. INCREMENTAL INFORMATION TEST DESIGN

To evaluate whether a candidate feature provides genuinely new information without modifying production strategy logic:
$$\text{Base Score} = \text{Existing Strategy Output}$$
$$\text{Incremental Feature} = f_{\text{candidate}}(\text{Market Snapshot})$$
$$\text{Information Gain} = I(\text{Future M5 Direction}; \text{Incremental Feature} \mid \text{Base Score})$$
- **Pass Condition:** Candidate feature must demonstrate statistically significant information gain ($p < 0.05$) on historical dataset beyond existing strategy features.

---

## 8. LOOK-AHEAD TIMELINE & CONFIRMATION LAG AUDIT

```text
Bar Index:       t-2         t-1         t0 (Decision Point)
Price Event:     Swing High  Candle 1    Bar Close (t0)
                 │           │           │
                 └── 2-Bar Confirmation ─┘
                     (Candidate A Signal Available at t0)
```
- **Candidate A (Swings):** 2-bar confirmation lag inherent to $k=2$ swing identification. Must evaluate signal at $t_0$ using confirmed swing from $t-2$.
- **Candidate B & C (Slope / VWAP Extension):** Point-in-time causal at $t_0$ bar close. Zero confirmation lag.
- **GAP-02 Candidate A (BOS Break Distance):** Point-in-time causal at $t_0$ bar close following a confirmed structural break.

---

## 9. MISSING DATA POLICY EVALUATION

| Policy Option | Semantics | Strategy Impact | Recommendation |
| :--- | :--- | :--- | :--- |
| **Policy A (Neutral Fallback)** | Missing data $\rightarrow 0.0$ score | Score unearned; no strategy veto | **Recommended default** |
| **Policy B (DQ Fatal Veto)** | Missing data $\rightarrow$ `DQ_FATAL` | Triggers `ACTION_NO_TRADE` | Too aggressive for tick gaps |
| **Policy C (Confidence Scale)** | Scale confidence by $0.50$ | Reduces position size indirectly | Requires risk engine modifications |

---

## 10. SCORE-WEIGHT & CALIBRATION AUDIT

- **Current Source Allocation:** `0.20` weight allocated to `div_score` in `MR_Evidence()` and `0.20` base weight allocated to `disp` in `ContinuationEvidence()`.
- **Classification:** `SOURCE IMPLEMENTATION` (Not an authoritative mathematical constant).
- **Calibration Requirement:** Final numerical weights must be calibrated on historical dataset post-feature implementation (`WEIGHT: REQUIRES CALIBRATION`).

---

## 11. ACCOUNT-SIZE INVARIANCE VERIFICATION

All six evaluated candidate formulas rely exclusively on market price, ATR, VWAP, and proxy delta. None reference account balance, equity, leverage, or lot size.
$$\text{Candidate Output}(\text{Market Snapshot}, \text{Equity}_1) \equiv \text{Candidate Output}(\text{Market Snapshot}, \text{Equity}_2)$$
**Status:** `ACCOUNT-INVARIANT (VERIFIED STATIC ONLY)`.

---

## 12. HISTORICAL / OUT-OF-SAMPLE TEST DESIGN

- **Training / Calibration Period:** `2024-01-01` to `2025-06-30`
- **Validation Period:** `2025-07-01` to `2025-12-31`
- **Out-of-Sample Period:** `2026-01-01` to `2026-09-24`
- **Status:** `OOS VALIDATION — NOT CURRENTLY EXECUTABLE` (Execution requires owner selection of candidate formulas).

---

## 13. RECOMMENDED CANDIDATES FOR OWNER REVIEW

Based on minimal double-counting overlap, causal look-ahead safety, and proxy delta compatibility:
1. **GAP-01 Recommended for Owner Review:** **Candidate C (Value Extension vs Order-Flow Fusion Confirmation)**.
2. **GAP-02 Recommended for Owner Review:** **Candidate A (ATR-Normalized Structural Break Distance)**.

*Note:* This recommendation is provided for research purposes. The owner may inspect, alter, or select alternative candidates.

---

## 14. UPDATED OWNER DECISION REGISTER

| Decision ID | Decision Question | Status / Options |
| :--- | :--- | :--- |
| **DEC-GAP-01A** | Selection of Mean-Reversion Divergence Definition | Pending Owner Choice: Candidate A / B / C (Rec: C) |
| **DEC-GAP-01B** | Missing Delta Data Fallback Policy | Pending Owner Choice: Policy A (Neutral 0.0) / B / C |
| **DEC-GAP-02A** | Selection of Continuation Displacement Definition | Pending Owner Choice: Candidate A / B / C (Rec: A) |
| **DEC-GAP-02B** | Score Weight Calibration Policy | Pending Owner Choice: Preserve 0.20 / OOS Calibrate |

---

## 15. OWNER DECISION PACKET

### Decision Item 1: GAP-01 Divergence Formula Selection (DEC-GAP-01A)
- **Question:** Which divergence formula should AlgoMind adopt for `div_score`?
- **Options:** Candidate A (Swing-to-Swing), Candidate B (Rolling Slope), Candidate C (VWAP Stretch vs Fusion).
- **Default Action if Undecided:** `IMPLEMENTATION BLOCKED`.

### Decision Item 2: GAP-02 Displacement Formula Selection (DEC-GAP-02A)
- **Question:** Which displacement formula should AlgoMind adopt for `disp`?
- **Options:** Candidate A (ATR Break Distance), Candidate B (Body Ratio), Candidate C (Multi-Bar Acceptance).
- **Default Action if Undecided:** `IMPLEMENTATION BLOCKED`.

---

## 16. PRODUCTION CODE INTEGRITY AUDIT

```text
FeatureVector.mqh        UNCHANGED
Strategy Engine.mqh      UNCHANGED
Risk Engine.mqh          UNCHANGED
Execution Engine.mqh     UNCHANGED
AMIGO.mq5                UNCHANGED
Contracts header.mqh     UNCHANGED
```
- **Production Code Changes:** `0`
- **Git State:** `GIT COMMIT: NOT APPROVED`, `GIT PUSH: NOT APPROVED`

---

## 17. MANDATORY FINAL STATUS BLOCK

```text
GAP-01:
CANDIDATE EVALUATION COMPLETE — OWNER SELECTION REQUIRED

GAP-02:
CANDIDATE EVALUATION COMPLETE — OWNER SELECTION REQUIRED

SPECIFICATION:
NOT FROZEN

IMPLEMENTATION:
BLOCKED

CALIBRATION:
NOT PERFORMED

OOS VALIDATION:
OOS VALIDATION — NOT CURRENTLY EXECUTABLE

PRODUCTION CODE:
UNCHANGED

STRATEGY LOGIC:
UNCHANGED

RISK LOGIC:
UNCHANGED

EXECUTION LOGIC:
UNCHANGED

LIVE TRADING:
NOT AUTHORIZED

GIT COMMIT:
NOT APPROVED

GIT PUSH:
NOT APPROVED
```
