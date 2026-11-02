# AMIGO — Production Horizon Implementation Design

## 1. Overview & Architectural Intent
The AMIGO system defines three analytical and operational trading horizons:
- **`HORIZON_SCALPING` (1)**: Seconds to minutes duration. Exploits order flow micro-imbalances, delta flips, and short-term volatility bursts.
- **`HORIZON_INTRADAY` (2)**: Minutes to hours duration. Structured setups on M5/M15 with H1 directional alignment.
- **`HORIZON_SWING` (3)**: Hours to days duration. Higher timeframe directional trades (H1/H4/D1).

Prior to this implementation, the system suffered from three critical defects:
1. **Horizon Disconnect**: `TradeIntent` did not propagate horizon identity, and `PositionManagerRegister` lacked horizon input, defaulting all positions to a generic profile.
2. **Homogeneous Management**: Scalping, Intraday, and Swing positions used identical break-even triggers, trailing stop increments, and hold lifetimes.
3. **Parameter Inflexibility**: Management rules were uniform regardless of execution timeframe or structural context.

## 2. Integrated Solution Architecture

### A. Contract Evolution (`Contracts header.mqh`)
`struct TradeIntent` was extended to include:
```mql5
ENUM_HORIZON horizon; // Section 1 Three-Horizon Architecture
```
This ensures strict end-to-end data provenance from analytical qualification through to execution and reconciliation.

### B. Analytical Horizon Determination (`AMIGO.mq5`)
The analytical engine evaluates timeframe structure and top-down alignment during `OnClosedBar`:
```mql5
ENUM_HORIZON selected_horizon = HORIZON_INTRADAY;
if(g_cfg.tf_exec == PERIOD_M1) 
   selected_horizon = HORIZON_SCALPING;
else if(g_cfg.tf_exec == PERIOD_H1 || g_cfg.tf_exec == PERIOD_H4) 
   selected_horizon = HORIZON_SWING;
else if(td.aligned && (td.h4_dir == dr.direction || td.h1_dir == dr.direction)) 
   selected_horizon = HORIZON_INTRADAY;
ti.horizon = selected_horizon;
```

### C. State Registration & Parameter Calibration (`Position Manager.mqh`)
`PositionManagerRegister` accepts `ENUM_HORIZON horiz` and customizes the break-even progress threshold:
- **Scalping**: `be_ratio = 0.33` (locks in quick gains to protect micro-alpha)
- **Intraday**: `be_ratio = 0.50` (standard 50% target progress)
- **Swing**: `be_ratio = 0.60` (allows wider volatility swings without premature stop-out)

### D. Horizon-Specific Lifecycle Management (`PositionManagerTick`)
1. **Scalping Lifetimes**: Enforces a strict 3600-second (1-hour) timeout if break-even has not been activated.
2. **Intraday Liquidation**: Closes positions prior to end-of-session boundaries.
3. **Swing Preservation**: Immune to intraday session close; manages via wider ATR trailing and structural pivots.
4. **Dynamic Trailing Profiling**:
   - Scalping: 15% dynamic trail factor / 1.0x ATR multiplier
   - Intraday: 25% dynamic trail factor / 1.5x ATR multiplier
   - Swing: 35% dynamic trail factor / 2.5x ATR multiplier
