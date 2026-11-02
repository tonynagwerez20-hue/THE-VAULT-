# AMIGO — Regime × Strategy × Horizon Interaction Matrix

## 1. Six-Way Operational Topology

The combination of 3 Horizons (Scalp, Intraday, Swing) and 2 Strategy Families (Continuation, Mean Reversion) yields six distinct operational profiles:

```
                  +----------------------------------------------+
                  |         AUTHORITATIVE REGIME STATE           |
                  +----------------------+-----------------------+
                                         |
                     +-------------------+-------------------+
                     |                                       |
           [HYP_CONTINUATION]                       [HYP_MEAN_REVERSION]
                     |                                       |
         +-----------+-----------+               +-----------+-----------+
         |           |           |               |           |           |
       SCALP     INTRADAY      SWING           SCALP     INTRADAY      SWING
        (1)         (2)         (3)             (4)         (5)         (6)
```

---

## 2. Comprehensive Interaction Specifications

### 1. Scalping + Continuation
- **Eligible Regimes**: `REGIME_TREND_UP` (Long), `REGIME_TREND_DOWN` (Short).
- **HTF Context**: D1/H4 directional bias aligned with trade direction.
- **LTF Condition**: Local M1/M5 momentum breakout with positive orderflow pressure.
- **Stop Invalidation**: Beyond immediate M1 swing pivot or $1.0 \times \text{ATR}_{14}$.
- **Lifecycle Management**: 33% BE trigger, 15% dynamic trailing ratchet, strict 60-minute holding limit.

### 2. Scalping + Mean Reversion
- **Eligible Regimes**: `REGIME_BALANCED`, `REGIME_EXHAUSTION`.
- **HTF Context**: Price extended $\ge 1.5 \times \text{ATR}_{14}$ from Session VWAP.
- **LTF Condition**: Local M1 liquidity sweep and immediate reversal rejection (`sweep_reject = true`).
- **Stop Invalidation**: Beyond the swept swing high/low.
- **Lifecycle Management**: 33% BE trigger, 1.5R partial exit, strict 60-minute holding limit.

### 3. Intraday + Continuation (Baseline Profile)
- **Eligible Regimes**: `REGIME_TREND_UP` (Long), `REGIME_TREND_DOWN` (Short).
- **HTF Context**: H4 and H1 aligned in trade direction.
- **LTF Condition**: M15 structure continuation on pullback into Value Area High/Low.
- **Stop Invalidation**: Beyond confirmed M15 swing pivot.
- **Lifecycle Management**: 50% BE trigger, 25% dynamic trailing ratchet, 2.0R partial exit, mandatory liquidation at `session_end_hour`.

### 4. Intraday + Mean Reversion
- **Eligible Regimes**: `REGIME_BALANCED`, `REGIME_EXHAUSTION`.
- **HTF Context**: D1/H4 consolidating inside intermediate range or macro exhaustion.
- **LTF Condition**: Rejection of Value Area extreme with delta divergence.
- **Stop Invalidation**: Beyond daily/session extreme.
- **Lifecycle Management**: 50% BE trigger, 2.0R partial exit, mandatory liquidation at `session_end_hour`.

### 5. Swing + Continuation
- **Eligible Regimes**: `REGIME_TREND_UP` (Long), `REGIME_TREND_DOWN` (Short).
- **HTF Context**: D1 and H4 confirmed BOS in trade direction; weekly macro alignment.
- **LTF Condition**: H1 pullback completion.
- **Stop Invalidation**: Beyond confirmed H4 swing low/high.
- **Lifecycle Management**: 60% BE trigger, 35% dynamic trailing ratchet or 2.5x ATR trail, multi-day holding, exempt from session closes.

### 6. Swing + Mean Reversion
- **Eligible Regimes**: `REGIME_EXHAUSTION` (High-tier macro exhaustion only).
- **HTF Context**: Multi-week extreme deviation from 20-day VWAP with severe CFTC positioning extreme ($\ge 90$ or $\le 10$ percentile).
- **LTF Condition**: H4 structural CHoCH against prevailing trend.
- **Stop Invalidation**: Beyond macro multi-week swing extreme.
- **Lifecycle Management**: 60% BE trigger, wider trailing, multi-week persistence, exempt from intraday session close.
