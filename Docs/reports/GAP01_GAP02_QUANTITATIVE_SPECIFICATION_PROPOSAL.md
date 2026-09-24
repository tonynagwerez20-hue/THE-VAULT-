# AlgoMind / ASAP
# GAP-01 / GAP-02 Quantitative Specification Proposal

**Project:** AlgoMind / ASAP Retail Order-Flow System  
**Symbol / Timeframe:** `XAUUSD` / `M5`  
**Execution Environment:** Windows 10, MetaTrader 5 (PID 7964), Exness Demo (`Exness-MT5Trial`)  
**Operating Mode:** SHADOW MODE (`InpShadowOnly = true`)  
**Report Date:** 2026-09-24  
**Local Execution Time:** 2026-09-24 22:55:00+03:00  

---

## 1. PURPOSE

This document presents mathematically explicit candidate proposals for closing the two HIGH-severity strategy scoring gaps identified in `LEVEL4_POST_RECONCILIATION_PRODUCTION_READINESS_AUDIT.md`:

```text
GAP-01 — Mean-Reversion Delta Divergence (div_score)
GAP-02 — Continuation BOS / Displacement (disp)
```

**CRITICAL GOVERNANCE RULE:** This proposal does **NOT** authorize production implementation. No production code is modified. These specifications are developed for inspection, challenge, modification, or decision by the project owner.

---

## 2. EXISTING EVIDENCE & ARCHITECTURAL CONSTRAINTS

1. **Retail MT5 Data Constraints:** Formulas must use strictly retail-accessible XAUUSD M5 data: OHLC bars, tick volume, ATR14, session VWAP/Value Area, proxy delta (`delta_a`, `delta_b`, `fusion`), and market structure ($k$-swings).
2. **No L2/L3 Dependencies:** Must not require institutional order book depth (L2) or time-and-sales tape (L3).
3. **Decoupled Architecture:** Features must be 100% account-invariant ($5 to $100,000+ accounts yield identical feature values).
4. **No Look-Ahead Bias:** Must use strictly point-in-time closed bar data available at decision timestamp $t$.

---

## 3. GAP-01 CONCEPT DEFINITION (MEAN-REVERSION DELTA DIVERGENCE)

### Conceptual Question:
> Is price extending away from value/structure while directional proxy order-flow evidence fails to confirm that extension?

`div_score` provides evidence for the `MEAN_REVERSION` hypothesis (`MR_Evidence()`). It is **NOT** a standalone buy/sell signal.

---

## 4. GAP-01 CANDIDATE A (SWING-TO-SWING PEAK/TROUGH DIVERGENCE)

### Mathematical Definition:
Compare the two most recent confirmed price swing points ($P_1$ at $t_1$, $P_2$ at $t_2$) against cumulative proxy delta ($D_1$ at $t_1$, $D_2$ at $t_2$).

- **Bullish Divergence (Long MR, dir = +1):** $P_2 < P_1$ (lower low in price) while $D_2 > D_1$ (higher low in cumulative delta).
- **Bearish Divergence (Short MR, dir = -1):** $P_2 > P_1$ (higher high in price) while $D_2 < D_1$ (lower high in cumulative delta).

$$\Delta P_{\text{norm}} = \frac{P_2 - P_1}{\text{ATR}_{14}}$$
$$\Delta D_{\text{norm}} = \frac{D_2 - D_1}{\sigma_D}$$
$$\text{div\_raw} = -\text{dir} \times (\Delta P_{\text{norm}} - \Delta D_{\text{norm}})$$
$$\text{div\_score}_A = \text{Clip01}\left( \frac{\text{div\_raw}}{1.5} \right)$$

---

## 5. GAP-01 CANDIDATE B (PRICE VS CUMULATIVE DELTA SLOPE DIVERGENCE)

### Mathematical Definition:
Calculate the linear regression slopes of closing price ($S_P$) and cumulative proxy delta ($S_D$) over a rolling $L$-bar window ($L = 10$ M5 bars).

$$\hat{S}_P = \frac{\text{Slope}(P, L)}{\text{ATR}_{14}}, \quad \hat{S}_D = \frac{\text{Slope}(D, L)}{\sigma_D}$$
$$\text{div\_raw} = \text{dir} \times (\hat{S}_D - \hat{S}_P)$$
$$\text{div\_score}_B = \text{Clip01}\left( \frac{\text{div\_raw}}{2.0} \right)$$

---

## 6. GAP-01 CANDIDATE C (VALUE EXTENSION VS ORDER-FLOW FUSION CONFIRMATION)

### Mathematical Definition:
Measure price extension from session VWAP in ATR units ($Z_{\text{vwap}} = |P - \text{VWAP}| / \text{ATR}_{14}$) against directional order-flow fusion ($F_{\text{dir}} = \text{dir} \times \text{fusion}$).

$$\text{div\_raw} = Z_{\text{vwap}} \times (1.0 - \text{Clip01}(F_{\text{dir}}))$$
$$\text{div\_score}_C = \text{Clip01}\left( \frac{\text{div\_raw} - 1.0}{1.5} \right)$$

---

## 7. GAP-01 CANDIDATE COMPARISON MATRIX

| Property | Candidate A (Swing-to-Swing) | Candidate B (Slope Divergence) | Candidate C (Extension vs Fusion) |
| :--- | :--- | :--- | :--- |
| **Uses Existing Data** | Yes (Swings + Cumulative Delta) | Yes (Close + Cumulative Delta) | Yes (`dev_vwap_atr` + `fusion`) |
| **Look-Ahead Risk** | None (Uses confirmed swings) | None (Rolling window) | None (Point-in-time bar) |
| **Sensitivity to Noise** | Low (Filtered by $k$-swings) | Medium (Sensitivity to $L$) | Low (Smoothed by ATR/VWAP) |
| **Proxy-Delta Fit** | High | Medium | Very High |
| **Interpretability** | Excellent | Good | Excellent |
| **Implementation Risk** | Medium | Low | Very Low |

---

## 8. GAP-01 NORMALIZATION MAPPING

Mapped to $[0.0, 1.0]$ via standard `Clip01()` function:
$$\text{Clip01}(x) = \text{MathMax}(0.0, \text{MathMin}(1.0, x))$$

---

## 9. GAP-01 DATA QUALITY & FALLBACK HANDLING

| Data Quality State | Policy A (Neutral Fallback) | Policy B (Data Quality Veto) | Policy C (Reduced Confidence) |
| :--- | :--- | :--- | :--- |
| **`DQ_MISSING_TICKS`** | `div_score = 0.0` (Neutral) | Set `DQ_FATAL` $\rightarrow$ `ACTION_NO_TRADE` | Scale confidence by 0.50 |
| **`PROXY` Delta State** | `div_score` active via proxy | `div_score` active via proxy | Scale confidence by 0.85 |

*Recommendation:* Policy A (Neutral 0.0 fallback) to prevent spurious trading halts.

---

## 10. GAP-02 CONCEPT DEFINITION (CONTINUATION DISPLACEMENT)

### Conceptual Question:
> Has price demonstrated sufficiently decisive structural movement to support continuation rather than merely drifting through a level?

`disp` provides evidence for the `CONTINUATION` hypothesis (`ContinuationEvidence()`).

---

## 11. GAP-02 BOS CANDIDATES & STRUCTURE DEFINITIONS

- **BOS High:** Bar close exceeds previous confirmed $k$-swing high ($k=2$).
- **BOS Low:** Bar close falls below previous confirmed $k$-swing low ($k=2$).

---

## 12. GAP-02 DISPLACEMENT CANDIDATE A (ATR-NORMALIZED STRUCTURAL BREAK DISTANCE)

### Mathematical Definition:
Measure how far the closing price extended beyond the broken swing level $P_{\text{BOS}}$, normalized by ATR14.

$$\text{disp\_raw} = \frac{|P_{\text{close}} - P_{\text{BOS}}|}{\text{ATR}_{14}}$$
$$\text{disp\_score}_A = \text{Clip01}\left( \frac{\text{disp\_raw}}{1.5} \right)$$

---

## 13. GAP-02 DISPLACEMENT CANDIDATE B (DIRECTIONAL CANDLE BODY RATIO)

### Mathematical Definition:
Measure the magnitude of the BOS candle's directional body relative to its total range and baseline ATR14.

$$\text{body\_ratio} = \frac{|P_{\text{close}} - P_{\text{open}}|}{P_{\text{high}} - P_{\text{low}} + \epsilon}$$
$$\text{size\_ratio} = \frac{|P_{\text{close}} - P_{\text{open}}|}{\text{ATR}_{14}}$$
$$\text{disp\_score}_B = \text{Clip01}\left( 0.6 \times \text{body\_ratio} + 0.4 \times \text{Clip01}\left( \frac{\text{size\_ratio}}{1.5} \right) \right)$$

---

## 14. GAP-02 DISPLACEMENT CANDIDATE C (MULTI-BAR POST-BOS ACCEPTANCE)

### Mathematical Definition:
Measure cumulative directional progress over $N$ bars ($N=3$) following a BOS event relative to pre-break ATR14.

$$\text{progress} = \text{dir} \times (P_{\text{close}, t} - P_{\text{BOS}})$$
$$\text{disp\_score}_C = \text{Clip01}\left( \frac{\text{progress}}{2.0 \times \text{ATR}_{14}} \right)$$

---

## 15. GAP-02 CANDIDATE COMPARISON MATRIX

| Property | Candidate A (ATR Break Dist) | Candidate B (Body/Range Ratio) | Candidate C (Multi-Bar Acceptance) |
| :--- | :--- | :--- | :--- |
| **Uses Existing Data** | Yes (Structure + ATR14) | Yes (OHLC + ATR14) | Yes (Structure + OHLC) |
| **Look-Ahead Risk** | None | None | 3-bar execution lag |
| **Sensitivity to Noise** | Low | Medium | Very Low |
| **Interpretability** | Excellent | Good | Excellent |
| **Implementation Risk** | Very Low | Low | Medium |

---

## 16. DOUBLE-COUNTING & FEATURE REDUNDANCY AUDIT

- **GAP-01 (Divergence):** Overlaps partially with `sweep_reject` and `fusion`. Using Candidate C minimizes redundancy because it specifically couples VWAP stretch to non-confirming fusion.
- **GAP-02 (Displacement):** Overlaps partially with `range_ratio` and `structure_dir`. Candidate A is strictly additive because it measures post-break extension magnitude.

---

## 17. WEIGHT IMPLICATIONS

The `0.20` score weight in `MR_Evidence()` and `ContinuationEvidence()` is a placeholder. Final score weight allocation requires empirical calibration on historical/OOS datasets (`WEIGHT: REQUIRES CALIBRATION`).

---

## 18. LOOK-AHEAD BIAS AUDIT

All candidate formulas consume strictly closed bar data ($r[1]$, $r[2]$) available at decision timestamp $t$. Swing points require confirmation lag ($k=2$ bars), which is explicitly accounted for in candidate indexing.

---

## 19. PROXY-DELTA LIMITATIONS

AlgoMind uses **PROXY DELTA** derived from tick volume and price direction (`delta_a`, `delta_b`). Divergence must be understood as **PROXY DELTA DIVERGENCE**, not exchange-wide L2/L3 order book divergence.

---

## 20. HISTORICAL / OUT-OF-SAMPLE VALIDATION DESIGN

- **Training/Calibration Period:** 2024-01-01 to 2025-06-30
- **Validation Period:** 2025-07-01 to 2025-12-31
- **Out-of-Sample Period:** 2026-01-01 to 2026-09-24
- **Metrics to Track:** Feature distribution stability, correlation with existing features, false signal reduction rate.

---

## 21. ACCOUNT-INVARIANCE REQUIREMENT

Both divergence and displacement candidate formulas are 100% account-invariant ($5 to $100,000+ accounts yield identical outputs for identical market data).

---

## 22. OWNER DECISION REGISTER

| Decision ID | Decision Item | Candidates / Options | Status |
| :--- | :--- | :--- | :--- |
| **DEC-GAP-01A** | Mean-Reversion Divergence Definition | Candidate A (Swing) / Candidate B (Slope) / Candidate C (VWAP/Fusion) | **PENDING OWNER SELECTION** |
| **DEC-GAP-01B** | Missing Delta Data Policy | Policy A (Neutral 0.0) / Policy B (DQ Veto) / Policy C (Scale Conf) | **PENDING OWNER SELECTION** |
| **DEC-GAP-02A** | Continuation Displacement Definition | Candidate A (ATR Break) / Candidate B (Body Ratio) / Candidate C (Multi-bar) | **PENDING OWNER SELECTION** |
| **DEC-GAP-02B** | Score Weight Allocation | Preserve 0.20 / Calibrate empirically on OOS dataset | **PENDING OWNER SELECTION** |

---

## 23. IMPLEMENTATION READINESS SUMMARY

- **GAP-01:** `SPECIFICATION PROPOSALS GENERATED — IMPLEMENTATION BLOCKED PENDING OWNER DECISION`
- **GAP-02:** `SPECIFICATION PROPOSALS GENERATED — IMPLEMENTATION BLOCKED PENDING OWNER DECISION`

---

## 24. EXPLICIT NON-CLAIMS & GOVERNANCE

```text
GAP-01:
SPECIFICATION PROPOSALS GENERATED — IMPLEMENTATION BLOCKED PENDING OWNER DECISION

GAP-02:
SPECIFICATION PROPOSALS GENERATED — IMPLEMENTATION BLOCKED PENDING OWNER DECISION

PRODUCTION CODE:
UNCHANGED

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
