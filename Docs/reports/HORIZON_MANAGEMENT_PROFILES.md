# AMIGO — Horizon Management Profiles Specification

## 1. Parameter Matrix by Horizon

| Parameter | Scalping (`HORIZON_SCALPING`) | Intraday (`HORIZON_INTRADAY`) | Swing (`HORIZON_SWING`) |
| :--- | :--- | :--- | :--- |
| **Execution Horizon** | Seconds to Minutes | Minutes to Hours | Hours to Days |
| **Typical Execution TF** | M1 / M5 | M5 / M15 | H1 / H4 |
| **Break-Even Progress Target** | 33% of target distance | 50% of target distance | 60% of target distance |
| **Holding Time Limit** | 3600 seconds (1 hour) max | Intraday session boundary | Multi-day unconstrained |
| **Partial Exit Target** | 1.5R | 2.0R (or `cfg.partial_rr`) | 2.0R (or `cfg.partial_rr`) |
| **Dynamic Trail Factor** | 15% | 25% | 35% |
| **ATR Trailing Multiplier** | 1.0x ATR | 1.5x ATR (`cfg.trail_atr_mult`) | 2.5x ATR |
| **Session-End Liquidation** | Exempt (managed by 1h timer) | Active (closed at session end) | Exempt |

## 2. Policy Operational Details

### Scalping Profile
- Designed for rapid micro-structure capture.
- If market does not reach break-even within 60 minutes (`3600 seconds`), position is terminated to free margin and eliminate adverse regime shift risk.
- Break-even triggers aggressively at 33% progress to prevent scratch trades from turning into full-R losses.

### Intraday Profile
- Default profile for standard institutional intraday structure.
- Adheres strictly to market session boundaries (`session_end_hour`) to avoid overnight roll and spread expansion.
- Preserves the established 50% break-even and 25% dynamic trail baseline.

### Swing Profile
- Designed to absorb intermediate retracements without premature liquidation.
- Unbounded by session close, allowing overnight and multi-session holding.
- Break-even requires 60% progress, and dynamic trailing grants a generous 35% trailing room.
