# AMIGO — Break-Even and Trailing Semantics Mathematical Audit

## 1. Disambiguation of Percentage Metrics

A critical source of confusion in strategy design is the ambiguity between "Percentage of TP Progress" vs "Percentage of Favourable Profit Ratchet". This report establishes the exact mathematical formulas implemented in `Position Manager.mqh`:

### A. Break-Even Trigger: Percentage of TP Target Distance
In `PositionManagerRegister()` (`Position Manager.mqh:60-72`):
$$\text{TP\_Distance} = |\text{Target} - \text{Entry}|$$
$$\text{BE\_Trigger} = \begin{cases}
  \text{Entry} + (\text{TP\_Distance} \times \text{be\_ratio}) & \text{if Long} (+1) \\
  \text{Entry} - (\text{TP\_Distance} \times \text{be\_ratio}) & \text{if Short} (-1)
\end{cases}$$
Where:
- **Scalping**: `be_ratio = 0.33` (33% of the distance from Entry to TP).
- **Intraday**: `be_ratio = 0.50` (50% of the distance from Entry to TP — preserved baseline).
- **Swing**: `be_ratio = 0.60` (60% of the distance from Entry to TP).

### B. Dynamic Trailing: Percentage Ratchet of Favourable Movement
In `PositionManagerTick()` (`Position Manager.mqh:315-327`):
$$\text{Profit\_Dist} = \begin{cases}
  \text{Current\_Price} - \text{Entry} & \text{if Long} \\
  \text{Entry} - \text{Current\_Price} & \text{if Short}
\end{cases}$$
$$\text{Trailing\_Dist} = \text{Profit\_Dist} \times \text{trail\_factor}$$
$$\text{Proposed\_SL} = \begin{cases}
  \text{Current\_Price} - \text{Trailing\_Dist} & \text{if Long} \\
  \text{Current\_Price} + \text{Trailing\_Dist} & \text{if Short}
\end{cases}$$
Where:
- **Scalping**: `trail_factor = 0.15` (Stop trails $15\%$ behind current market price relative to accumulated profit).
- **Intraday**: `trail_factor = 0.25` (Stop trails $25\%$ behind current price — preserved baseline).
- **Swing**: `trail_factor = 0.35` (Stop trails $35\%$ behind current price).

---

## 2. Comparative Numerical Example

Assume an XAUUSDm Long trade:
- **Entry**: $2000.00$
- **Initial Stop**: $1990.00$ ($\text{Risk} = 10.00$)
- **Take Profit**: $2040.00$ ($\text{TP\_Distance} = 40.00$)

### Step 1: Break-Even Trigger Activation Price
- **Scalp (33%)**: $2000.00 + (40.00 \times 0.33) = \mathbf{2013.20}$
- **Intraday (50%)**: $2000.00 + (40.00 \times 0.50) = \mathbf{2020.00}$
- **Swing (60%)**: $2000.00 + (40.00 \times 0.60) = \mathbf{2024.00}$

### Step 2: Dynamic Stop Loss when Price Reaches 2025.00
Profit distance = $2025.00 - 2000.00 = 25.00$.
All three profiles have passed their BE trigger ($\text{be\_activated} = \text{true}$).
- **Scalping (15% Ratchet)**:
  $$\text{Trailing\_Dist} = 25.00 \times 0.15 = 3.75 \implies \text{Proposed\_SL} = 2025.00 - 3.75 = \mathbf{2021.25}$$
  Profit locked in = $+21.25$ points ($+2.12$ R).
- **Intraday (25% Ratchet)**:
  $$\text{Trailing\_Dist} = 25.00 \times 0.25 = 6.25 \implies \text{Proposed\_SL} = 2025.00 - 6.25 = \mathbf{2018.75}$$
  Profit locked in = $+18.75$ points ($+1.87$ R).
- **Swing (35% Ratchet)**:
  $$\text{Trailing\_Dist} = 25.00 \times 0.35 = 8.75 \implies \text{Proposed\_SL} = 2025.00 - 8.75 = \mathbf{2016.25}$$
  Profit locked in = $+16.25$ points ($+1.62$ R).

---

## 3. Mandatory Ratchet Rule Verification

In `Position Manager.mqh:328-330`:
```mql5
bool is_improvement = (dir == +1) ? (proposed_sl > cur_sl)
                                  : (proposed_sl < cur_sl);
```
- **Ratchet Guarantee**: Stop loss modifications are permitted **only if `is_improvement == true`**.
- If market price retraces from $2025.00$ back to $2022.00$, `proposed_sl` decreases, `is_improvement` evaluates to `false`, and the stop loss **remains locked at $2021.25$ / $2018.75$ / $2016.25$**.
- **Verdict**: **Stops never loosen under any circumstance**.
