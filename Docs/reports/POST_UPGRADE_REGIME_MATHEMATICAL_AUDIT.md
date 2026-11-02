# AMIGO — Post-Upgrade Regime & Mathematical Audit

## 1. Mathematical Structure of the Regime State Machine

The multi-timeframe regime engine evaluates five competing hypotheses on each closed execution bar:
$$C = \{ \text{TREND\_UP}, \text{TREND\_DOWN}, \text{EXPANSION}, \text{BALANCED}, \text{EXHAUSTION} \}$$

Let:
$$Score^* = \max_{c \in C} Score(c), \quad Candidate = \arg\max_{c \in C} Score(c)$$

### Transition Rules with Hysteresis and Persistence:
1. **Initial Transition (from `NO_TRADE` or `NONE`)**:
   $$\text{Transition} = \mathbf{1}_{\{Score^* \ge \text{regime\_threshold}\}} \land \mathbf{1}_{\{\text{candidate\_count} \ge \text{regime\_persistence}\}}$$
   Where `regime_threshold` = $0.60$ and `regime_persistence` = $3$ bars.
2. **Active Regime Transition**:
   $$\text{Transition} = \mathbf{1}_{\{Score^* \ge \text{regime\_threshold}\}} \land \mathbf{1}_{\{Score^* \ge \text{CurrentScore} + \text{regime\_hysteresis}\}} \land \mathbf{1}_{\{\text{candidate\_count} \ge \text{regime\_persistence}\}}$$
   Where `regime_hysteresis` = $0.10$.

### Impact of Multi-Timeframe Integration:
- In the older version, local M5 noise could oscillate $Score(TrendUp)$ across the threshold on consecutive bars, causing whipsaw regime transitions.
- Under the upgraded formula, the 35% HTF structural weight ($S_{HTF}$) and 15% alignment score ($A_{score}$) act as a **low-pass filter**. When higher timeframes are in a persistent macro trend, $Score(TrendUp)$ or $Score(TrendDown)$ retains a stable baseline of $\ge 0.45$, preventing spurious flips into opposing regimes.
