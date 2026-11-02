# AMIGO — Multi-Timeframe Regime Architecture & Mathematical Design

## 1. Contextual Architecture

Market regimes are inherently multi-scale. A market is rarely in a single uniform state across all horizons simultaneously. The AMIGO Regime Engine is designed around a three-tier hierarchy:

1. **Macro / Directional Layer (D1, H4)**:
   - Primary role: Establishes structural dominance and macro supply/demand boundaries.
   - Prevents trading into structural walls.
2. **Intermediate Structural Layer (H1, M30)**:
   - Primary role: Gauges continuation health, trend maturity, and value migration.
   - Confirms whether intermediate auction participants support macro directional flow.
3. **Execution Micro-Structure Layer (M15, M5, M1)**:
   - Primary role: Measures local momentum, order-flow pressure, value-area rotation, and local invalidation.

```
+--------------------------------------------------------------------------+
|  MACRO CONTEXT (D1 / H4): Major Trend & Structural Anchors               |
|  - Directional Dominance (d1_dir, h4_dir)                                |
+------------------------------------+-------------------------------------+
                                     |
                                     v
+------------------------------------+-------------------------------------+
|  INTERMEDIATE CONTEXT (H1 / M30): Trend Health & Development             |
|  - Value migration, intermediate swing confirmation (h1_dir, m30_dir)     |
+------------------------------------+-------------------------------------+
                                     |
                                     v
+------------------------------------+-------------------------------------+
|  EXECUTION HORIZON (M15 / M5 / M1): Micro Geometry & Local Signals       |
|  - Local swing pivots, footprint pressure proxies, value-area rotation   |
+------------------------------------+-------------------------------------+
                                     |
                                     v
+------------------------------------+-------------------------------------+
|  SYNTHESIS ENGINE (Regime Engine): Authoritative Contextual Regime       |
|  - Evaluates HTF Dominance, Conflict Rejection, Countertrend Eligibility |
+--------------------------------------------------------------------------+
```

---

## 2. Mathematical Multi-Timeframe Regime Scoring Formulation

Let:
- $S_{HTF} \in \{-1, 0, +1\}$ be the synthesized higher-timeframe directional bias:
  $$S_{HTF} = \begin{cases}
    h4\_dir & \text{if } h4\_dir == h1\_dir \text{ and } h4\_dir \neq 0 \\
    h1\_dir & \text{if } h1\_dir \neq 0 \\
    h4\_dir & \text{otherwise}
  \end{cases}$$
- $S_{LTF} \in \{-1, 0, +1\}$ be the execution/intermediate directional bias from M15/M5.
- $A_{score} \in [0.0, 1.0]$ be the TopDownContext alignment score.
- $P_{local} \in [-1, +1]$ be the normalized orderflow pressure proxy.
- $V_{state} \in \{-1, 0, +1\}$ be the value-area relation (Above VAH, Inside VA, Below VAL).

### A. Multi-Timeframe Trend Up Score ($Score_{TrendUp}$)
In the baseline version, trend scoring relied 35% on local structure and 25% on local pressure. Under the top-down model:
$$Score_{TrendUp} = 0.35 \cdot \mathbf{1}_{\{S_{HTF} = +1\}} + 0.20 \cdot \mathbf{1}_{\{S_{LTF} = +1\}} + 0.15 \cdot \mathbf{1}_{\{P_{local} > 0\}} + 0.15 \cdot \mathbf{1}_{\{f.acceptance\_above\}} + 0.15 \cdot A_{score}$$

**Key Property**: If $S_{HTF} = -1$ (HTF is Bearish), $Score_{TrendUp}$ loses the 0.35 HTF component and receives an alignment penalty ($A_{score} \le 0.25$), mathematically preventing the regime score from crossing the `regime_threshold` ($0.60$). **This permanently prevents buying local M5 rallies inside macro bear trends.**

### B. Multi-Timeframe Trend Down Score ($Score_{TrendDown}$)
$$Score_{TrendDown} = 0.35 \cdot \mathbf{1}_{\{S_{HTF} = -1\}} + 0.20 \cdot \mathbf{1}_{\{S_{LTF} = -1\}} + 0.15 \cdot \mathbf{1}_{\{P_{local} < 0\}} + 0.15 \cdot \mathbf{1}_{\{f.acceptance\_below\}} + 0.15 \cdot A_{score}$$

### C. Balanced / Conflict Score ($Score_{Balanced}$)
When HTF and LTF directly oppose each other, or price is consolidating within intermediate value areas:
$$Score_{Balanced} = 0.40 \cdot \mathbf{1}_{\{td.conflict\}} + 0.30 \cdot \mathbf{1}_{\{V_{state} = 0\}} + 0.30 \cdot \mathbf{1}_{\{|\Delta VWAP| < 0.5 \cdot ATR\}}$$

**Key Property**: When an HTF-LTF conflict occurs, $Score_{Balanced}$ is elevated, shifting the regime to `REGIME_BALANCED` and restricting `HYP_CONTINUATION` entries.

### D. Exhaustion Score ($Score_{Exhaustion}$)
Detects when a prevailing higher-timeframe trend has overextended into liquidity sweep zones:
$$Score_{Exhaustion} = 0.40 \cdot \mathbf{1}_{\{f.sweep\_reject\}} + 0.30 \cdot \mathbf{1}_{\{f.delta\_divergence > 0.5\}} + 0.30 \cdot \mathbf{1}_{\{|\Delta VWAP| > 2.0 \cdot ATR\}}$$

---

## 3. TopDownContext Integration into `EvaluateRegime`

The signature of `EvaluateRegime` in `Regime Engine.mqh` is extended:
```mql5
RegimeState EvaluateRegime(const FeatureSnapshot &f, const TopDownContext &td, const AmigoConfig &cfg);
```

### Transition State Machine:
1. **`REGIME_NO_TRADE`**: Enforced if `td.summary == "BALANCED_OR_INSUFFICIENT_HTF_DATA"` or missing bar history.
2. **`REGIME_TREND_UP`**: Enforced when HTF is bullish and LTF confirms or completes a minor pullback into support.
3. **`REGIME_TREND_DOWN`**: Enforced when HTF is bearish and LTF confirms or completes a minor pullback into resistance.
4. **`REGIME_BALANCED`**: Enforced during structural conflict or rotation inside the session value area.
5. **`REGIME_EXHAUSTION`**: Enforced upon high-volume liquidity sweep and immediate structural rejection.
