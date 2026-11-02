# AMIGO — Timeframe Authority Reconciliation Report

**Document Date:** 2026-11-02  
**Target Code:** `MQL5/Include/Structure Engine.mqh` (Lines 142–243), `Regime Engine.mqh` (Lines 30–67)  
**Evaluator:** Antigravity Architect & Adversarial QA  

---

## 1. Documented Conceptual Model vs Actual Source Implementation

In earlier high-level system specifications (`TIMEFRAME_AUTHORITY_AND_ALIGNMENT_MATRIX.md`), the architecture defined an authoritative tier model:
- **Higher Timeframes (HTF - D1, H4, H1):** 50%
- **Intermediate Timeframes (ITF - M30, M15):** 30%
- **Execution Timeframes (LTF - M5, M1):** 20%

In the production MQL5 source code (`Regime Engine.mqh` lines 46–49), the functional scoring implementation evaluates:

$$S_{\text{trend}} = 0.45 \cdot W_{\text{htf}} + 0.20 \cdot W_{\text{ltf}} + 0.15 \cdot P + 0.10 \cdot A + 0.10 \cdot M_{\text{align}}$$

### Comparison Matrix
| Authority Tier | Documented Target | Actual Functional Implementation | Mechanism |
| :--- | :--- | :--- | :--- |
| **HTF Authority** | 50% | **45% Direct + ~8.5% Indirect ($\approx 53.5\%$)** | $W_{\text{htf}}$ directly checks H4/H1; $M_{\text{align}}$ incorporates HTF agreement. |
| **Intermediate Authority** | 30% | **~5% - 8.5% Indirect** | M30/M15 feed into `td.alignment_score` via `ltf_bias` calculation. |
| **Execution Authority** | 20% | **45% Total Confluence** | 20% Structure + 15% Pressure + 10% Acceptance. |

---

## 2. Seven-Timeframe Information Routing Analysis

`EvaluateTopDownContext()` in `Structure Engine.mqh` samples 7 distinct timeframes using closed bars (`CopyRates(..., 1, 200, ...)`):

```
Timeframe       Engine Function          Where Consumed
---------------------------------------------------------------------------------------------------
PERIOD_D1   --> EvaluateStructure()  --> td.d1_dir (NOT consumed in ScoreTrend or alignment synthesis)
PERIOD_H4   --> EvaluateStructure()  --> td.h4_dir (Direct in ScoreTrendUp/Down, Synthesis bias)
PERIOD_H1   --> EvaluateStructure()  --> td.h1_dir (Direct in ScoreTrendUp/Down, Synthesis bias)
PERIOD_M30  --> EvaluateStructure()  --> td.m30_dir (Indirect via ltf_bias fallback)
PERIOD_M15  --> EvaluateStructure()  --> td.m15_dir (Indirect as primary ltf_bias)
PERIOD_M5   --> EvaluateStructure()  --> td.m5_dir (Indirect via ltf_bias fallback; M5 f.structure_dir is direct)
PERIOD_M1   --> EvaluateStructure()  --> td.m1_dir (NOT consumed in ScoreTrend or alignment synthesis)
```

### Critical Findings Regarding D1 and M1
1. **D1 Structure:** Computed at line 173 (`EvaluateStructure(symbol, PERIOD_D1, m5_atr * 8.0, 0)`), stored in `td.d1_dir`. However, `td.d1_dir` is never referenced in lines 201–239 when deriving `htf_bias`, nor is it referenced in `Regime Engine.mqh`.
2. **M1 Structure:** Computed at line 197 (`EvaluateStructure(symbol, PERIOD_M1, m5_atr * 0.5, 0)`), stored in `td.m1_dir`. Similarly, `td.m1_dir` is not consumed by the regime engine or alignment score.
3. **Operational Assessment:** D1 and M1 calculations are currently informational passengers in the regime classifier. The runtime pays the minor overhead of their `CopyRates()` calls without utilizing their structural direction in `ScoreTrendUp`/`ScoreTrendDown`.

---

## 3. Reconciliation Verdict & Acceptance Status

- **Status:** **PARTIALLY CONGRUENT WITH FUNCTIONAL SAFETY PRESERVED**
- **Safety Objective:** The primary safety objective of the 50/30/20 conceptual model was to ensure higher timeframes hold veto power over lower timeframe noise. With $W_{\text{htf}} = 0.45$ and fail-closed zero-credit, this requirement is **fully achieved** (no trade possible with neutral or opposing HTF).
- **Architectural Debt:** The intermediate timeframes (M30, M15) do not hold the full 30% independent weight specified in conceptual docs, and D1/M1 are structurally idle.
