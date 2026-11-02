# AlgoMind / ASAP
# GAP-01 / GAP-02 Formal Specification Freeze Proposal

**Project:** AlgoMind / ASAP Retail Order-Flow System  
**Symbol / Timeframe:** `XAUUSD` / `M5`  
**Execution Environment:** Windows 10, MetaTrader 5 (PID 7964), Exness Demo (`Exness-MT5Trial`)  
**Operating Mode:** SHADOW MODE (`InpShadowOnly = true`)  
**Report Date:** 2026-09-24  
**Local Execution Time:** 2026-09-24 23:18:00+03:00  

---

## 1. EXECUTIVE SUMMARY

This document converts the candidate evaluation results from `GAP01_GAP02_CANDIDATE_EVALUATION_SELECTION_AUDIT.md` into an explicit, mathematically complete specification freeze proposal for owner approval:

```text
GAP-01 Specification Basis: Candidate C — Value Extension vs Order-Flow Fusion Confirmation
GAP-02 Specification Basis: Candidate A — ATR-Normalized Structural Break Distance
```

**CRITICAL GOVERNANCE RULE:** This document is a **SPECIFICATION FREEZE PROPOSAL ONLY**. It does NOT authorize production implementation, weight calibration, or live trading. Zero production code is modified (`PRODUCTION CODE: UNCHANGED`, `GIT COMMIT: NOT APPROVED`, `GIT PUSH: NOT APPROVED`).

---

## 2. CURRENT CANDIDATE BASIS & REFERENCES

- **Evaluation Audit:** `Docs/reports/GAP01_GAP02_CANDIDATE_EVALUATION_SELECTION_AUDIT.md`
- **Specification Proposal:** `Docs/reports/GAP01_GAP02_QUANTITATIVE_SPECIFICATION_PROPOSAL.md`
- **Baseline Readiness Report:** `Docs/reports/LEVEL4_POST_RECONCILIATION_PRODUCTION_READINESS_AUDIT.md`
- **Authoritative Code Contracts:** `Include/Contracts header.mqh`, `Include/FeatureVector.mqh`, `Include/Strategy Engine.mqh`.

---

## 3. AUTHORITATIVE DOCUMENT HIERARCHY & NORMATIVE CONVENTIONS

1. **Existing Conventions Preserved:** Mapped strictly to existing project infrastructure: `Clip01()` normalization, `FeatureSnapshot` contracts, `dev_vwap_atr`, `fusion`, `structure_dir`, `atr14`.
2. **Account Decoupling Maintained:** All formulas are 100% market-derived and account-invariant ($5 to $100,000+ accounts yield identical outputs).
3. **No Speculative Extensions:** Unspecified parameters are marked `NOT SPECIFIED — REQUIRES OWNER DECISION`.

---

## 4. GAP-01 FORMAL SPECIFICATION (VALUE EXTENSION / FUSION CONFIRMATION)

### 4.1 Value Reference & Extension Formula
- **Value Reference:** Session VWAP (`fs.vwap` computed via `ComputeSessionVWAP()`).
- **Normalized VWAP Stretch ($Z_{\text{vwap}}$):**
  $$Z_{\text{vwap}} = \text{fs.dev\_vwap\_atr} = \frac{P_{\text{close}} - \text{VWAP}}{\text{ATR}_{14}}$$
  $$\text{stretch} = |Z_{\text{vwap}}|$$
- **Stretch Score Component ($S_{\text{stretch}}$):**
  $$S_{\text{stretch}} = \text{Clip01}\left( \frac{\text{stretch} - 1.0}{1.5} \right)$$

### 4.2 Order-Flow Confirmation / Fusion
- **Order-Flow Fusion Metric:** `fs.fusion` ($\in [-1.0, +1.0]$ computed via `ComputeFusion()`).
- **Directional Fusion Alignment ($F_{\text{dir}}$):**
  $$F_{\text{dir}}(\text{dir}) = \text{dir} \times \text{fs.fusion} \quad (\text{dir} \in \{+1, -1\})$$
- **Flow Failure Component ($S_{\text{flow\_fail}}$):**
  $$S_{\text{flow\_fail}}(\text{dir}) = \text{Clip01}\left( 1.0 - \max(0.0, F_{\text{dir}}(\text{dir})) \right)$$

### 4.3 Directional Divergence Semantics
- **Bearish Divergence (Short MR, $\text{dir} = -1$):** Price extended above VWAP ($Z_{\text{vwap}} > 1.0$) while order flow fails to confirm upside ($F_{\text{dir}} < 0.25$).
- **Bullish Divergence (Long MR, $\text{dir} = +1$):** Price extended below VWAP ($Z_{\text{vwap}} < -1.0$) while order flow fails to confirm downside ($F_{\text{dir}} < 0.25$).

### 4.4 Normalization & Score Integration
- **Raw Divergence Score Equation:**
  $$\text{div\_raw}(\text{dir}) = S_{\text{stretch}} \times S_{\text{flow\_fail}}(\text{dir})$$
- **Normalized Divergence Score ($\text{div\_score}$):**
  $$\text{div\_score}(\text{dir}) = \text{Clip01}(\text{div\_raw}(\text{dir}))$$
- **Integration in `MR_Evidence()` (`Strategy Engine.mqh` L47):**
  $$\text{MR\_Evidence}(\text{dir}) = 0.40 \times S_{\text{stretch}} + 0.25 \times \text{rej\_score} + 0.20 \times \mathbf{div\_score}(\text{dir}) + 0.15 \times \text{ret\_val}$$

### 4.5 Missing-Data Policy & DQ Fallbacks
- **Policy A (Neutral Fallback):** If tick delta or fusion is missing/stale (`DQ_MISSING_TICKS`), `div_score = 0.0`. Score contribution is unearned, but execution is NOT halted by a hard data-quality veto.
- **Fallback Behavior:** `div_score = 0.0` when `atr14 <= 0.0` or `vwap <= 0.0`.

### 4.6 Timing & Causality
- **Point-in-Time Calculation:** Calculated strictly at M5 bar close ($t_0$) using closed bar $r[1]$. Zero future bar dependencies.

### 4.7 Double-Counting Audit
- Couples price value stretch with order-flow exhaustion. Strictly distinct from `sweep_reject` (liquidity sweep) and `pressure_state` (raw flow direction).

---

## 5. GAP-02 FORMAL SPECIFICATION (ATR-NORMALIZED STRUCTURAL BREAK DISTANCE)

### 5.1 BOS Definition & Structure Reference
- **Structure Engine:** `EvaluateStructure()` using $k=2$ swing points.
- **BOS Level ($P_{\text{BOS}}$):** Most recent confirmed swing high ($P_{\text{swing\_high}}$ for bullish BOS, $\text{dir} = +1$) or swing low ($P_{\text{swing\_low}}$ for bearish BOS, $\text{dir} = -1$).

### 5.2 Displacement Distance Formula
- **Directional Break Distance ($\text{dist\_raw}$):**
  $$\text{dist\_raw}(\text{dir}) = \text{dir} \times (P_{\text{close}} - P_{\text{BOS}})$$
- **ATR-Normalized Break Ratio ($\text{disp\_ratio}$):**
  $$\text{disp\_ratio}(\text{dir}) = \frac{\text{dist\_raw}(\text{dir})}{\text{ATR}_{14}}$$

### 5.3 Normalization & Score Integration
- **Linear Saturation Formula ($\kappa_{\text{disp}} = 1.5$):**
  $$\text{disp}(\text{dir}) = \text{Clip01}\left( \frac{\max(0.0, \text{disp\_ratio}(\text{dir}))}{1.5} \right)$$
- **Integration in `ContinuationEvidence()` (`Strategy Engine.mqh` L72):**
  $$\text{Continuation\_Base}(\text{dir}) = 0.30 \times \text{structure} + 0.20 \times \mathbf{disp}(\text{dir}) + 0.20 \times \text{accept} + 0.20 \times \text{pressure} + 0.10 \times \text{vol\_supp}$$

### 5.4 Timing & Causality
- **Causal Calculation:** Computed at M5 bar close ($t_0$) following a confirmed BOS event. Zero future bar dependencies.

### 5.5 Regime & News Interaction
- Account-size invariant. Operates downstream under existing regime gates (`REGIME_NO_TRADE` block).

---

## 6. SCORE WEIGHT & CALIBRATION POLICY

- **Initial Implementation Weight:** `PROVISIONAL — REQUIRES CALIBRATION`
- The `0.20` weight in `MR_Evidence()` and `ContinuationEvidence()` is preserved as a provisional source placeholder. Empirical tuning on historical/OOS datasets is required post-implementation (`WEIGHTS: NOT FROZEN`).

---

## 7. ACCEPTANCE TEST CASES (DETERMINISTIC SPECIFICATION TESTS)

### GAP-01 Specification Tests:
1. **Case 1 (Strong Stretch + Zero Flow Confirmation):** $Z_{\text{vwap}} = +2.5$, $F_{\text{dir}} = -0.50 \implies S_{\text{stretch}} = 1.0, S_{\text{flow\_fail}} = 1.0 \implies \text{div\_score} = 1.0$.
2. **Case 2 (Strong Stretch + Strong Flow Confirmation):** $Z_{\text{vwap}} = +2.5$, $F_{\text{dir}} = +0.80 \implies S_{\text{stretch}} = 1.0, S_{\text{flow\_fail}} = 0.20 \implies \text{div\_score} = 0.20$.
3. **Case 3 (No Stretch):** $Z_{\text{vwap}} = +0.5 \implies S_{\text{stretch}} = 0.0 \implies \text{div\_score} = 0.0$.
4. **Case 4 (Missing Delta):** Delta missing $\implies \text{div\_score} = 0.0$ (Neutral fallback).

### GAP-02 Specification Tests:
1. **Case 1 (Bullish BOS + 1.5 ATR Break):** $P_{\text{close}} - P_{\text{BOS}} = 1.5 \times \text{ATR}_{14} \implies \text{disp} = 1.0$.
2. **Case 2 (Bullish BOS + 0.75 ATR Break):** $P_{\text{close}} - P_{\text{BOS}} = 0.75 \times \text{ATR}_{14} \implies \text{disp} = 0.50$.
3. **Case 3 (No BOS / Failed Break):** $P_{\text{close}} < P_{\text{BOS}} \implies \text{disp} = 0.0$.

---

## 8. ACCOUNT-SIZE INVARIANCE VERIFICATION

All input variables ($P_{\text{close}}$, $\text{VWAP}$, $\text{ATR}_{14}$, $\text{fusion}$, $P_{\text{BOS}}$) are strictly market-derived. Account equity/balance is zero-indexed in both formulas:
$$\text{div\_score}(\text{Snapshot}, \text{Equity}_1) \equiv \text{div\_score}(\text{Snapshot}, \text{Equity}_2)$$
$$\text{disp}(\text{Snapshot}, \text{Equity}_1) \equiv \text{disp}(\text{Snapshot}, \text{Equity}_2)$$

---

## 9. FINAL OWNER DECISION REGISTER

| Decision ID | Decision Item | Proposed Specification | Status |
| :--- | :--- | :--- | :--- |
| **DEC-GAP-01A** | GAP-01 Mathematical Definition | Candidate C (Value Extension vs Order-Flow Fusion) | `SPECIFICATION READY FOR OWNER REVIEW` |
| **DEC-GAP-01B** | Missing-Data Fallback Policy | Policy A (Neutral 0.0 Fallback) | `SPECIFICATION READY FOR OWNER REVIEW` |
| **DEC-GAP-01C** | GAP-01 Normalization Convention | `Clip01` mapping equation | `SPECIFICATION READY FOR OWNER REVIEW` |
| **DEC-GAP-02A** | GAP-02 Mathematical Definition | Candidate A (ATR-Normalized Break Distance) | `SPECIFICATION READY FOR OWNER REVIEW` |
| **DEC-GAP-02B** | BOS Confirmation Definition | $k=2$ Swing High/Low Break from `Structure Engine` | `SPECIFICATION READY FOR OWNER REVIEW` |
| **DEC-GAP-02C** | GAP-02 Normalization Convention | `Clip01(disp_ratio / 1.5)` | `SPECIFICATION READY FOR OWNER REVIEW` |
| **DEC-GAP-02D** | Weight / Calibration Policy | Provisional 0.20; Empirical OOS calibration required | `PROVISIONAL — REQUIRES CALIBRATION` |

---

## 10. SPECIFICATION FREEZE GATE CLASSIFICATION

- **GAP-01 Mathematical Formula:** `SPECIFICATION READY FOR OWNER REVIEW`
- **GAP-01 Missing-Data Policy:** `SPECIFICATION READY FOR OWNER REVIEW`
- **GAP-01 Normalization:** `SPECIFICATION READY FOR OWNER REVIEW`
- **GAP-02 Mathematical Formula:** `SPECIFICATION READY FOR OWNER REVIEW`
- **GAP-02 BOS Definition:** `SPECIFICATION READY FOR OWNER REVIEW`
- **GAP-02 Normalization:** `SPECIFICATION READY FOR OWNER REVIEW`
- **Score Weights:** `PROVISIONAL — REQUIRES CALIBRATION`

---

## 11. PRODUCTION CODE INTEGRITY AUDIT

```text
PRODUCTION CODE:
UNCHANGED (0 production code modifications made)

STRATEGY LOGIC:
UNCHANGED

RISK LOGIC:
UNCHANGED

EXECUTION LOGIC:
UNCHANGED

CALIBRATION:
NOT PERFORMED

OOS VALIDATION:
NOT PERFORMED

LIVE TRADING:
NOT AUTHORIZED

GIT COMMIT:
NOT APPROVED

GIT PUSH:
NOT APPROVED
```

---

## 12. FINAL MANDATORY STATUS BLOCK

```text
GAP-01 DIVERGENCE:
SPECIFICATION READY FOR OWNER REVIEW

GAP-02 DISPLACEMENT:
SPECIFICATION READY FOR OWNER REVIEW

DIVERGENCE FORMULA:
PROPOSED (Candidate C: Value Extension vs Fusion)

DISPLACEMENT FORMULA:
PROPOSED (Candidate A: ATR-Normalized Break Distance)

NORMALIZATION:
Clip01 MAPPING DEFINED

DATA QUALITY HANDLING:
POLICY A (Neutral 0.0 Fallback Proposed)

SCORE WEIGHTS:
PROVISIONAL 0.20 (REQUIRES CALIBRATION)

GRADE BOUNDARIES:
INVARIANT CONTINUOUS SCORE

CALIBRATION:
NOT PERFORMED

OWNER DECISIONS:
- DEC-GAP-01A: GAP-01 Mathematical Definition approval
- DEC-GAP-01B: Missing-data policy approval
- DEC-GAP-02A: GAP-02 Mathematical Definition approval
- DEC-GAP-02D: Weight calibration policy approval

PRODUCTION CODE CHANGED:
NO

STRATEGY LOGIC CHANGED:
NO

RISK LOGIC CHANGED:
NO

EXECUTION LOGIC CHANGED:
NO

GIT COMMIT:
NOT APPROVED

GIT PUSH:
NOT APPROVED
```
