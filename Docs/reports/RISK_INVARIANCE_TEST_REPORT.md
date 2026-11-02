# AMIGO — Risk Invariance & Account-Level Protection Report

## 1. Mathematical Proof of Risk Invariance

The AMIGO system enforces strict monetary risk invariance:
$$\text{Monetary Risk Dollar Loss} = \text{StopDistancePoints} \times \text{TickValuePerPoint} \times \text{ExecutableVolume} \le \text{ApprovedRiskBudget}$$

To verify this invariance across disparate horizons and stop distances, consider an account with **$10,000 Equity** and **0.50% Base Risk ($50.00)** on Gold (`XAUUSDm`):
- `SYMBOL_POINT = 0.01` ($1.00$ price change = $100$ points)
- `SYMBOL_VOLUME_MIN = 0.01`
- `SYMBOL_VOLUME_STEP = 0.01`
- `SYMBOL_TRADE_TICK_VALUE = 1.00` per full lot ($0.01$ per point for $0.01$ lots)

### Scenario Sweep:

| Horizon | Entry | Stop Loss | Stop Dist | Raw Lots | Rounded Executable Volume | Actual Dollar Risk at SL | Actual Risk % | Distortion | Feasibility |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Scalping** | 2000.00 | 1998.50 | 150 pts ($1.50) | 0.3333 | **0.33 Lots** | **$49.50** | **0.495%** | 1.00x | `FEASIBILITY_NORMAL` |
| **Intraday** | 2000.00 | 1995.00 | 500 pts ($5.00) | 0.1000 | **0.10 Lots** | **$50.00** | **0.500%** | 1.00x | `FEASIBILITY_NORMAL` |
| **Swing** | 2000.00 | 1975.00 | 2500 pts ($25.00) | 0.0200 | **0.02 Lots** | **$50.00** | **0.500%** | 1.00x | `FEASIBILITY_NORMAL` |
| **Macro Swing** | 2000.00 | 1940.00 | 6000 pts ($60.00) | 0.0083 | **0.00 (Infeasible)** | **$0.00** | **0.000%** | N/A | `FEASIBILITY_MIN_LOT_UNSAFE` |

---

## 2. Infeasibility Rejection & Anti-Distortion Invariants

1. **Macro Swing Infeasibility Protection**:
   - In row 4, a $60.00 wide swing stop requires a theoretical volume of $0.0083$ lots.
   - The broker's minimum volume is $0.01$ lots.
   - Executing $0.01$ lots would cause a dollar loss of:
     $$6000 \text{ pts} \times \$0.01 = \$60.00 \quad (0.60\% \text{ of equity})$$
   - On a mature $10,000 account, the maximum allowed distortion is clamped to **1.0x** (`risk_auto.max_allowed_distortion = 1.00`).
   - `AccountExecutionEvaluate()` detects that $0.01$ lots exceeds the 1.0x distortion ceiling and rejects the trade with:
     $$\text{FEASIBILITY\_MIN\_LOT\_UNSAFE} \implies \text{ACTION\_NO\_TRADE}$$
   - **Verdict**: AMIGO **never inflates risk** to force execution of wide swing stops on small capital allocations.
2. **Zero Maximum Drawdown Components**:
   - The risk architecture relies exclusively on high-water equity drawdown throttling and daily loss locks. No equity-curve fitting or arbitrary dynamic trailing drawdown rules are present.
