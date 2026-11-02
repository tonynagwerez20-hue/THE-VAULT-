# AMIGO — Regime-to-Strategy Integration Architecture

## 1. Governance Principles & Invariants

1. **Strategy Family Preservation**:
   - AMIGO defines exactly two strategy families: `CONTINUATION` and `MEAN_REVERSION`. No additional strategy families are introduced.
2. **Strategy Invariance**:
   - $\mathcal{S}(\text{strategy\_input}, \text{market\_state}) = \mathcal{S}(\text{market\_state})$. Strategy scoring is strictly objective and mathematical; it does not change based on account balance, leverage, or broker.
3. **Regime Authority**:
   - The Regime Engine is the single authoritative gatekeeper of strategy eligibility. A strategy cannot bypass an authoritative `REGIME_NO_TRADE` or an unaligned regime condition.

---

## 2. Regime-Strategy Qualification Matrix

| Authoritative Regime | Continuation Eligibility | Mean Reversion Eligibility | Risk Modifier | Operational Behaviour |
| :--- | :--- | :--- | :---: | :--- |
| **`REGIME_TREND_UP`** | **Primary (Long Only)** | Restricted (Extreme Extension Only) | 1.00x | Allows bullish continuation pullbacks; forbids fading trend without confirmed structural sweep. |
| **`REGIME_TREND_DOWN`** | **Primary (Short Only)** | Restricted (Extreme Extension Only) | 1.00x | Allows bearish continuation rallies; forbids fading trend without confirmed structural sweep. |
| **`REGIME_BALANCED`** | Restricted (Breakout Only) | **Primary (Both Directions)** | 0.80x | Fades Value Area boundaries back toward Session VWAP / POC; forbids chasing range boundaries. |
| **`REGIME_EXPANSION`** | **Permitted (High Vol)** | Prohibited (Never fade expansion) | 0.50x | Requires strict momentum confirmation; fading explosive volume expansion is vetoed. |
| **`REGIME_EXHAUSTION`** | Prohibited (Trend End) | **Primary (Reversal Confirmation)** | 0.70x | Seeks reversion entries following confirmed liquidity sweeps at range extremes. |
| **`REGIME_NEWS`** | Prohibited | Prohibited | 0.00x | Hard blackout gate around high-impact macroeconomic releases. |
| **`REGIME_NO_TRADE`** | Prohibited | Prohibited | 0.00x | Fail-closed gate: insufficient data, stale ticks, or extreme spread. |

---

## 3. Integration Mechanics in `Decide()`

In `Strategy Engine.mqh:186-191`, the decision gate evaluates hypothesis compatibility:
```mql5
// Regime/hypothesis compatibility gate
if(rs.preferred != HYP_NONE && rs.preferred != d.hypothesis)
{
   d.action = ACTION_WAIT;
   d.reason = "REGIME_HYP_MISMATCH";
   return d;
}
```

Under the top-down regime engine:
1. When `rs.regime == REGIME_TREND_UP`, `rs.preferred = HYP_CONTINUATION`. Any attempt by the Strategy Engine to generate a short mean-reversion signal is automatically intercepted with `REGIME_HYP_MISMATCH`.
2. When `rs.regime == REGIME_BALANCED`, `rs.preferred = HYP_MEAN_REVERSION`. Any breakout continuation trade is held in `ACTION_WAIT` until range expansion is verified.
3. If an explicit countertrend mean reversion is justified by exhaustion criteria, the Regime Engine temporarily classifies the state as `REGIME_EXHAUSTION`, shifting `rs.preferred` to `HYP_MEAN_REVERSION` with reduced risk modifier (`0.70`).
