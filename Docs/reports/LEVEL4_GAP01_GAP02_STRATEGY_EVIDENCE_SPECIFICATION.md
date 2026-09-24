# AlgoMind / ASAP
# GAP-01 / GAP-02 Strategy Evidence Specification Gate

**Project:** AlgoMind / ASAP Retail Order-Flow System  
**Symbol / Timeframe:** `XAUUSD` / `M5`  
**Execution Environment:** Windows 10, MetaTrader 5 (PID 7964), Exness Demo (`Exness-MT5Trial`)  
**Operating Mode:** SHADOW MODE (`InpShadowOnly = true`)  
**Report Date:** 2026-09-24  
**Local Execution Time:** 2026-09-24 22:45:00+03:00  

---

## 1. OBJECTIVE

The objective of this gate is to conduct a strict specification audit for the two HIGH-severity strategy scoring gaps identified in the Level 4 Post-Reconciliation Production Readiness Audit (`LEVEL4_POST_RECONCILIATION_PRODUCTION_READINESS_AUDIT.md`):

```text
GAP-01 — Mean Reversion Divergence (div_score = 0.0 placeholder)
GAP-02 — Continuation Displacement (disp = 0.0 placeholder)
```

Per governance rules, this gate determines whether authoritative specifications exist to implement these components correctly, or whether implementation is blocked pending owner decisions. **No production code is written or modified during this task.**

---

## 2. AUTHORITATIVE SOURCES

- **MQL5 Source Code:** `MQL5/Experts/AMIGO.mq5`, `Include/Contracts header.mqh`, `Include/FeatureVector.mqh`, `Include/Strategy Engine.mqh`, `Include/Risk Engine.mqh`, `Include/Execution Engine.mqh`.
- **System Documentation:** Math Spec §15, §17, §18, §26; `CURRENT_PROJECT_STATE_RECONCILIATION.md`, `FOOTPRINT_DELTA_INTEGRATION_AUDIT.md`.
- **Audit Baseline:** `LEVEL4_POST_RECONCILIATION_PRODUCTION_READINESS_AUDIT.md`.

---

## 3. GAP-01 MEAN REVERSION DIVERGENCE (`div_score`)

### 3.1 Current Implementation
In `Include/Strategy Engine.mqh` line 37:
```mql5
double div_score = 0.0;
```
`MR_Evidence()` evaluates:
$$\text{MR\_Evidence} = 0.40 \times \text{stretch\_score} + 0.25 \times \text{rej\_score} + 0.20 \times \mathbf{div\_score} + 0.15 \times \text{ret\_val}$$
Because `div_score` is hardcoded to `0.0`, the 20% divergence contribution is unearned, capping maximum achievable raw MR score at `0.80` instead of `1.00`.

### 3.2 Existing Specification
- `Contracts header.mqh`: `FeatureSnapshot` contains **NO field** for `delta_divergence`.
- `FeatureVector.mqh`: `BuildFeatureVector()` calculates `delta_a`, `delta_b`, `fusion`, `pressure_state`, `bull_flip`, `bear_flip`, `surge`, `persistence`, but does **NOT** calculate price vs delta divergence.
- Authoritative documentation notes price/delta divergence conceptually, but does not provide an exact mathematical formula.

### 3.3 Specification Matrix

| Requirement | Specified? | Source | Exact Definition | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Divergence input** | `NO` | None | Unspecified (Cumulative Delta vs Price) | `NOT SPECIFIED — REQUIRES OWNER DECISION` |
| **Price reference** | `NO` | None | Unspecified (Swing High/Low vs Close) | `NOT SPECIFIED — REQUIRES OWNER DECISION` |
| **Delta reference** | `NO` | None | Unspecified (Cumulative Delta vs Fusion) | `NOT SPECIFIED — REQUIRES OWNER DECISION` |
| **Lookback** | `NO` | None | Unspecified (e.g. 5, 10, 20 bars) | `NOT SPECIFIED — REQUIRES OWNER DECISION` |
| **Swing definition** | `NO` | None | Unspecified (Fractal vs K-swing) | `NOT SPECIFIED — REQUIRES OWNER DECISION` |
| **Direction** | `NO` | None | Unspecified (Bullish vs Bearish) | `NOT SPECIFIED — REQUIRES OWNER DECISION` |
| **Normalization** | `NO` | None | Unspecified (Clip01 vs Z-score) | `NOT SPECIFIED — REQUIRES OWNER DECISION` |
| **Range** | `NO` | None | Unspecified (Expected 0.0 to 1.0) | `NOT SPECIFIED — REQUIRES OWNER DECISION` |
| **Missing-data behavior** | `NO` | None | Unspecified (Fail closed vs 0.0) | `NOT SPECIFIED — REQUIRES OWNER DECISION` |
| **Weight** | `YES` | `Strategy Engine.mqh` L47 | `0.20` weight in `MR_Evidence` | `IMPLEMENTED STATIC ONLY` |
| **Score contribution** | `YES` | `Strategy Engine.mqh` L47 | $0.20 \times \text{div\_score}$ | `IMPLEMENTED STATIC ONLY` |
| **Eligibility interaction** | `YES` | `Strategy Engine.mqh` L158 | Feeds `s_long` / `s_short` $\ge 0.65$ | `IMPLEMENTED STATIC ONLY` |
| **Validation method** | `NO` | None | Unspecified (Deterministic test fixture) | `NOT SPECIFIED — REQUIRES OWNER DECISION` |

### 3.4 Evidence Chain
$$\text{Tick / Bar Data} \longrightarrow \text{delta\_a / delta\_b} \longrightarrow \mathbf{\text{[MISSING: delta\_divergence]}} \longrightarrow \mathbf{\text{[MISSING: fs.delta\_divergence]}} \longrightarrow \text{div\_score = 0.0} \longrightarrow \text{MR\_Evidence}$$

### 3.5 Missing Definitions
1. Exact mathematical formula for comparing price peaks/troughs to cumulative delta peaks/troughs.
2. Lookback bar window length for divergence detection.
3. Normalization function to map raw divergence into $[0.0, 1.0]$.
4. Data quality fallback behavior when tick delta history is incomplete.

### 3.6 Implementation Readiness
**Classification:** `BLOCKED — SPECIFICATION GAP`

---

## 4. GAP-02 CONTINUATION DISPLACEMENT (`disp`)

### 4.1 Current Implementation
In `Include/Strategy Engine.mqh` line 58:
```mql5
double disp = 0.0;
```
`ContinuationEvidence()` evaluates:
$$\text{Continuation\_Base} = 0.30 \times \text{structure} + 0.20 \times \mathbf{disp} + 0.20 \times \text{accept} + 0.20 \times \text{pressure} + 0.10 \times \text{vol\_supp}$$
Because `disp` is hardcoded to `0.0`, the 20% displacement contribution is unearned, capping maximum base Continuation score at `0.80` instead of `1.00`.

### 4.2 Existing Specification
- `Contracts header.mqh`: `FeatureSnapshot` contains **NO field** for `displacement`.
- `FeatureVector.mqh`: `BuildFeatureVector()` calculates `structure_dir`, `bull_choch`, `bear_choch`, `bos_age_bars = 0.0`, but does **NOT** calculate a displacement ratio.
- Authoritative documentation mentions post-release ATR displacement in event reaction contexts (`FOMC_MINUTES_REACTION_SPEC.md`), but does not provide an M5 strategy displacement formula.

### 4.3 Specification Matrix

| Requirement | Specified? | Source | Exact Definition | Status |
| :--- | :--- | :--- | :--- | :--- |
| **BOS definition** | `PARTIAL` | `Structure Engine.mqh` | Break of swing high/low | `IMPLEMENTED STATIC ONLY` |
| **Structure definition** | `YES` | `Structure Engine.mqh` | `swing_k = 2` swing points | `IMPLEMENTED STATIC ONLY` |
| **Displacement definition**| `NO` | None | Unspecified (Candle body / ATR ratio) | `NOT SPECIFIED — REQUIRES OWNER DECISION` |
| **Lookback** | `NO` | None | Unspecified (BOS candle lookback) | `NOT SPECIFIED — REQUIRES OWNER DECISION` |
| **Timeframe** | `YES` | `Configuration.mqh` | `tf_exec = PERIOD_M5` | `IMPLEMENTED STATIC ONLY` |
| **Normalization** | `NO` | None | Unspecified (Clip01 vs linear scaling) | `NOT SPECIFIED — REQUIRES OWNER DECISION` |
| **Range** | `NO` | None | Unspecified (Expected 0.0 to 1.0) | `NOT SPECIFIED — REQUIRES OWNER DECISION` |
| **Direction** | `YES` | `Strategy Engine.mqh` L51 | Directional alignment with `dir` | `IMPLEMENTED STATIC ONLY` |
| **Missing-data behavior** | `NO` | None | Unspecified (Fail closed vs 0.0) | `NOT SPECIFIED — REQUIRES OWNER DECISION` |
| **Weight** | `YES` | `Strategy Engine.mqh` L72 | `0.20` weight in base Continuation | `IMPLEMENTED STATIC ONLY` |
| **Score contribution** | `YES` | `Strategy Engine.mqh` L72 | $0.20 \times \text{disp}$ | `IMPLEMENTED STATIC ONLY` |
| **Eligibility interaction** | `YES` | `Strategy Engine.mqh` L158 | Feeds `s_long` / `s_short` $\ge 0.65$ | `IMPLEMENTED STATIC ONLY` |
| **Validation method** | `NO` | None | Unspecified (Deterministic test fixture) | `NOT SPECIFIED — REQUIRES OWNER DECISION` |

### 4.4 Evidence Chain
$$\text{Price Bars} \longrightarrow \text{Structure Engine (BOS)} \longrightarrow \mathbf{\text{[MISSING: displacement]}} \longrightarrow \mathbf{\text{[MISSING: fs.displacement]}} \longrightarrow \text{disp = 0.0} \longrightarrow \text{ContinuationEvidence}$$

### 4.5 Missing Definitions
1. Exact formula for displacement magnitude (e.g., $\text{Body\_Size} / \text{ATR14}$ vs $\text{Close} - \text{BOS\_Level}$).
2. Threshold for minimum displacement to earn $1.0$.
3. Lookback window for evaluating displacement following a BOS event.

### 4.6 Implementation Readiness
**Classification:** `BLOCKED — SPECIFICATION GAP`

---

## 5. FEATURE CONTRACT AUDIT

Neither `delta_divergence` nor `displacement` exists in the `FeatureSnapshot` struct in `Contracts header.mqh`. Before any calculation can be wired:
1. `FeatureSnapshot` must be updated with `double delta_divergence;` and `double displacement;`.
2. `feature_version` must be incremented from `1` to `2`.

---

## 6. DATA QUALITY AUDIT

The system uses `DQ_FATAL`, `DQ_MISSING_TICKS`, and `DQ_BROKER_INVALID` flags.
- Policy for missing divergence/displacement data must be specified:
  - Defaulting to `0.0` acts as a neutral contribution without triggering a hard data-quality veto.
  - Setting a `DQ_` error flag would trigger a hard `ACTION_NO_TRADE` decision.
- **Status:** `NOT SPECIFIED — REQUIRES OWNER DECISION` (Recommending neutral `0.0` fallback without hard DQ veto).

---

## 7. NORMALIZATION AUDIT

Existing normalization infrastructure uses `Clip01(x)`:
$$\text{Clip01}(x) = \text{MathMax}(0.0, \text{MathMin}(1.0, x))$$
Any future formula for `delta_divergence` or `displacement` should output a normalized value in $[0.0, 1.0]$ via `Clip01()`.

---

## 8. SCORE WEIGHT AUDIT

In `Strategy Engine.mqh`:
- `div_score` weight in `MR_Evidence()` is `0.20` (20% of total score).
- `disp` weight in `ContinuationEvidence()` is `0.20` (20% of base score).
- Both weights are verified in static source code, but their numerical values require empirical calibration once feature formulas are established.

---

## 9. CALIBRATION REQUIREMENTS

The following items require empirical calibration using the project's historical/OOS validation dataset:
1. **Divergence Scaling Parameter:** Multiplier/scaling constant for mapping price/delta divergence to $[0.0, 1.0]$.
2. **Displacement ATR Multiple:** Threshold multiple of ATR14 required to achieve a full `1.0` displacement score.

---

## 10. OWNER DECISION REGISTER

| Decision ID | Decision Item | Why It Matters | Status / Action |
| :--- | :--- | :--- | :--- |
| **DEC-GAP-01** | Delta Divergence Mathematical Formula | Required to code `BuildFeatureVector()` divergence calculation | `NOT SPECIFIED — REQUIRES OWNER DECISION` |
| **DEC-GAP-02** | BOS Displacement Ratio Mathematical Formula | Required to code `BuildFeatureVector()` displacement calculation | `NOT SPECIFIED — REQUIRES OWNER DECISION` |
| **DEC-GAP-03** | Missing Data Fallback Policy | Determines if missing divergence/displacement causes neutral 0.0 or DQ veto | `NOT SPECIFIED — REQUIRES OWNER DECISION` |
| **DEC-GAP-04** | Small Account Min-Lot Override Input Parameter | Exposes `InpAllowMinLotOverride` in `AMIGO.mq5` inputs for small accounts | `NOT SPECIFIED — REQUIRES OWNER DECISION` |

---

## 11. IMPLEMENTATION READINESS SUMMARY

- **GAP-01 (Mean Reversion Divergence):** `BLOCKED — SPECIFICATION GAP`
- **GAP-02 (Continuation Displacement):** `BLOCKED — SPECIFICATION GAP`
- **Proposed Closures:** `NOT YET AUTHORITATIVE` (Implementation cannot proceed until owner decisions DEC-GAP-01 and DEC-GAP-02 are specified).

---

## 12. VALIDATION PLAN (FOR POST-SPECIFICATION TESTING)

When authoritative formulas are provided by the owner:
1. **Unit Test:** Verify `ComputeDeltaDivergence()` and `ComputeDisplacement()` formulas against synthetic test data.
2. **Feature Contract Test:** Verify `fs.delta_divergence` and `fs.displacement` populate correctly in `FeatureSnapshot`.
3. **Strategy Engine Test:** Verify `div_score` and `disp` contribute to `MR_Evidence()` and `ContinuationEvidence()`.
4. **Account-Size Parity Test:** Verify `delta_divergence` and `displacement` outputs remain 100% account-invariant.

---

## 13. PRODUCTION-CODE INTEGRITY

```text
PRODUCTION CODE CHANGED: NO (0 production code modifications made)
STRATEGY LOGIC CHANGED: NO
RISK LOGIC CHANGED: NO
EXECUTION LOGIC CHANGED: NO
```

---

## 14. FINAL STATUS

```text
GAP-01 DIVERGENCE:
BLOCKED — SPECIFICATION GAP

GAP-02 DISPLACEMENT:
BLOCKED — SPECIFICATION GAP

DIVERGENCE FORMULA:
NOT SPECIFIED — REQUIRES OWNER DECISION

DISPLACEMENT FORMULA:
NOT SPECIFIED — REQUIRES OWNER DECISION

NORMALIZATION:
Clip01 CONVENTION AVAILABLE (STATIC ONLY)

DATA QUALITY HANDLING:
NOT SPECIFIED — REQUIRES OWNER DECISION

SCORE WEIGHTS:
0.20 IN SOURCE (STATIC ONLY — REQUIRES CALIBRATION)

GRADE BOUNDARIES:
INVARIANT CONTINUOUS SCORE (VERIFIED STATIC ONLY)

CALIBRATION:
REQUIRES HISTORICAL / OOS CALIBRATION POST-SPECIFICATION

OWNER DECISIONS:
- DEC-GAP-01: Delta Divergence mathematical formula
- DEC-GAP-02: BOS Displacement ratio mathematical formula
- DEC-GAP-03: Missing data fallback policy
- DEC-GAP-04: Small-account min-lot override policy

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
