# AMIGO — Regime Scoring Mathematical Verification

**Document Date:** 2026-11-02  
**Target Code:** `MQL5/Include/Regime Engine.mqh` (Lines 30–199)  
**Evaluator:** Antigravity Mathematical & Quantitative Engineering  

---

## 1. Mathematical Formulation

The regime engine uses a multi-factor linear weighting scheme to determine trend scores:

$$S_{\text{trend\_up}} = 0.45 \cdot W_{\text{htf}} + 0.20 \cdot W_{\text{ltf}} + 0.15 \cdot P + 0.10 \cdot A + 0.10 \cdot M_{\text{align}}$$

Where:
- $W_{\text{htf}} \in \{0.0, 1.0\}$: Higher-timeframe directional agreement ($+1$ for Up, $-1$ for Down). Strict zero-credit for neutral or opposing.
- $W_{\text{ltf}} \in \{0.0, 1.0\}$: Local structure direction (`f.structure_dir`).
- $P \in \{0.0, 1.0\}$: Order flow pressure direction (`f.pressure_state`).
- $A \in \{0.0, 1.0\}$: Price acceptance above/below value area (`f.acceptance_above` / `f.acceptance_below`).
- $M_{\text{align}} \in [0.0, 1.0]$: Synthesis alignment score (`td.alignment_score`).

Total weight sum:
$$0.45 + 0.20 + 0.15 + 0.10 + 0.10 = 1.000$$

Regime classification threshold:
$$\text{Threshold} = 0.600$$

---

## 2. Worked Mathematical Scenarios

### Scenario 1: Bullish HTF Aligned (Strongest Agreement)
- Context: H4 = +1, H1 = +1 $\rightarrow$ `htf_bias` = +1, `alignment_score` = 0.85
- Features: `structure_dir` = +1, `pressure_state` = +1, `acceptance_above` = true
- Calculation:
  $$S_{\text{trend\_up}} = 0.45(1.0) + 0.20(1.0) + 0.15(1.0) + 0.10(1.0) + 0.10(0.85)$$
  $$S_{\text{trend\_up}} = 0.45 + 0.20 + 0.15 + 0.10 + 0.085 = \mathbf{0.985}$$
- Verdict: **PASS ($\ge 0.60$)** $\rightarrow$ Triggers `REGIME_TREND_UP` (subject to 2-bar persistence).

### Scenario 2: Bearish HTF Aligned
- Context: H4 = -1, H1 = -1 $\rightarrow$ `htf_bias` = -1, `alignment_score` = 0.85
- Features: `structure_dir` = -1, `pressure_state` = -1, `acceptance_below` = true
- Calculation:
  $$S_{\text{trend\_down}} = 0.45(1.0) + 0.20(1.0) + 0.15(1.0) + 0.10(1.0) + 0.10(0.85) = \mathbf{0.985}$$
- Verdict: **PASS ($\ge 0.60$)** $\rightarrow$ Triggers `REGIME_TREND_DOWN`.

### Scenario 3: Neutral HTF (Safety Invariant Check)
- Context: H4 = 0, H1 = 0 $\rightarrow$ `htf_bias` = 0, `alignment_score` = 0.50
- Features: Maximal bullish confluence locally ($W_{\text{ltf}}=1, P=1, A=1$)
- Calculation:
  $$S_{\text{trend\_up}} = 0.45(0.0) + 0.20(1.0) + 0.15(1.0) + 0.10(1.0) + 0.10(0.50)$$
  $$S_{\text{trend\_up}} = 0.0 + 0.20 + 0.15 + 0.10 + 0.050 = \mathbf{0.500}$$
- Verdict: **REJECT ($0.500 < 0.600$)**
- Conclusion: Under neutral HTF conditions, local confluence cannot breach the regime activation threshold. Trend trading is prevented.

### Scenario 4: Opposing HTF (Counter-Trend Block)
- Context: H4 = -1, H1 = -1 $\rightarrow$ `htf_bias` = -1, `alignment_score` = 0.25 (HTF/LTF conflict)
- Features: Maximal bullish confluence locally attempting to buy into higher timeframe resistance
- Calculation:
  $$S_{\text{trend\_up}} = 0.45(0.0) + 0.20(1.0) + 0.15(1.0) + 0.10(1.0) + 0.10(0.25)$$
  $$S_{\text{trend\_up}} = 0.0 + 0.20 + 0.15 + 0.10 + 0.025 = \mathbf{0.475}$$
- Verdict: **REJECT ($0.475 < 0.600$)**
- Conclusion: Confirmed opposing HTF strictly vetoes counter-directional trend regimes.

### Scenario 5: Conflicted Intermediate HTF (H4 Bullish, H1 Bearish)
- Context: H4 = +1, H1 = -1. Per synthesis rule line 35, H1 takes priority when non-zero $\rightarrow$ `htf_bias` = -1.
- Evaluating Bullish Trend:
  $$S_{\text{trend\_up}} \le 0.45(0.0) + 0.45 + 0.10(0.50) = \mathbf{0.500} < 0.600$$
- Evaluating Bearish Trend:
  $$S_{\text{trend\_down}} \le 0.45(1.0) + 0.45(\text{LTF}) + 0.10(0.25) \approx \mathbf{0.500 - 0.725}$$
  (Requires complete local bearish confluence to qualify).

### Scenario 6: Insufficient / Stale HTF Guard
- Context: `td.summary == "BALANCED_OR_INSUFFICIENT_HTF_DATA"` and `td.alignment_score < 0.40`.
- Code Gate (`Regime Engine.mqh` lines 107–114):
  ```mql5
  rs.regime = REGIME_NO_TRADE;
  rs.confidence = 0.0;
  rs.preferred = HYP_NONE;
  rs.risk_modifier = 0.0;
  return rs;
  ```
- Verdict: Immediate fail-closed bypass; no scoring is executed.

---

## 3. Mathematical Scenario Summary Table

| Scenario | HTF Bias | Align Score | LTF Weight | Max Score | Threshold | Regime Result |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Bullish Aligned** | +1 | 0.85 | 1.00 | **0.985** | 0.60 | `REGIME_TREND_UP` |
| **Bearish Aligned** | -1 | 0.85 | 1.00 | **0.985** | 0.60 | `REGIME_TREND_DOWN` |
| **Neutral HTF** | 0 | 0.50 | 1.00 | **0.500** | 0.60 | Blocked / Ineligible |
| **Opposing HTF** | -1 (vs Up) | 0.25 | 1.00 | **0.475** | 0.60 | Blocked / Ineligible |
| **Split HTF (H4/H1)**| Conflict | $\le 0.50$ | 1.00 | $\le \mathbf{0.500}$ | 0.60 | Blocked / Ineligible |
| **Missing HTF Data** | N/A | < 0.40 | N/A | **0.000** | 0.60 | `REGIME_NO_TRADE` |
