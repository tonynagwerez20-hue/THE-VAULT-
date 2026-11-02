# AMIGO — Horizon Stop Geometry & Invalidation Audit

## 1. Stop Calculation Architecture

In `AMIGO.mq5:474-530`, stop loss calculation occurs in sequential stages:
1. **Horizon Determination**: `selected_horizon` evaluates `g_cfg.tf_exec` and top-down alignment.
2. **Timeframe Selection (`stop_tf`)**:
   - Scalping: `stop_tf = (tf_exec == PERIOD_M1) ? PERIOD_M1 : PERIOD_M5`
   - Intraday: `stop_tf = (tf_context != 0) ? tf_context : PERIOD_M15`
   - Swing: `stop_tf = (tf_h4 != 0) ? tf_h4 : PERIOD_H4`
3. **Structural Invalidation Query**:
   `FindLatestConfirmedSwing(r, 200, is_high, structural_invalid, ts, k=2)`
   Where $k=2$ requires 2 lower highs / higher lows on each side to confirm a swing pivot.
4. **`SelectStop()` Invalidation Anchor (`Risk Engine.mqh:107-140`)**:
   - Validates that `structural_invalid` is on the protective side of entry.
   - If `MathAbs(entry - structural_invalid) <= 1.0 * atr`: uses `structural_invalid`.
   - Fallback: Uses entry $\mp 1.5 \times \text{ATR}_{14}$.
   - Clamps to broker `SYMBOL_TRADE_STOPS_LEVEL`.

---

## 2. Comparative Numerical Worked Example

Hypothetical Setup: XAUUSDm Long Entry at **2000.00**, M5 ATR = **$2.50**, H4 ATR = **$12.00**, Account Equity = **$10,000**, Approved Base Risk = **0.50% ($50.00)**. Broker Point = 0.01, Tick Value = $1.00 per point per 1.00 lot ($0.01 per point per 0.01 lot).

| Horizon | Invalidation TF | Swing Low Found | Selected Stop | Stop Distance | Lots Sizing Formula | Executable Volume | Monetary Risk |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **SCALPING** | M1 / M5 | 1998.00 | **1998.00** | **$2.00** (200 pts) | $\$50 / (200 \times \$1.00)$ | **0.25 Lots** | **$50.00** (0.50%) |
| **INTRADAY** | M15 | 1995.00 | **1995.00** | **$5.00** (500 pts) | $\$50 / (500 \times \$1.00)$ | **0.10 Lots** | **$50.00** (0.50%) |
| **SWING** | H4 | 1980.00 | **1980.00** | **$20.00** (2000 pts) | $\$50 / (2000 \times \$1.00)$ | **0.02 Lots** | **$40.00** (0.40%)* |

*\*Note on Volume Rounding*: For the Swing trade, theoretical lot size is $0.025$. Broker `volume_step = 0.01` rounds volume down to `0.02 Lots`, producing an actual monetary loss of $\$40.00$ ($0.40\%$), strictly below the $0.50\%$ ceiling.

---

## 3. Forensic Finding: Invalidation vs ATR Clamp in `SelectStop()`

Inspection of `Risk Engine.mqh:116-123` reveals a critical design detail:
```mql5
if(structural_invalid > 0.0 && structural_invalid < entry)
{
   double dist = entry - structural_invalid;
   if(dist <= 1.0 * atr) // <-- CLAMP RULE
      return structural_invalid;
}
return entry - 1.5 * atr; // Fallback
```

> [!WARNING]
> **Adversarial Finding**:
> If a genuine H4 structural swing low is $15.00$ points away from entry, but H4 ATR is $12.00$, the clamp condition `dist <= 1.0 * atr` will evaluate to **FALSE**.
> As a result, `SelectStop()` rejects the valid structural pivot and falls back to `entry - 1.5 * atr` ($18.00$ points)!
> **Conclusion**: The $1.0 \times \text{ATR}$ threshold in `SelectStop()` was originally hardcoded for M5 scalping, and can arbitrarily reject valid intermediate structural swing pivots. This represents an uncalibrated heuristic that requires architectural review.
