# 08 — PROP-FIRM LIFECYCLE SIMULATION & MONTE CARLO RESULTS (,000 ACCOUNT FOCUS)

## 1. 10,000-Path Monte Carlo Simulation Results

| Dataset | Trades | Risk % | P1 Pass Prob | Max Breach Prob | P95 Max DD % | P95 Max DD $ | P95 Losing Streak |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Full Dataset** | 759 | 0.25% | **100.00%** | **0.00%** | 3.64% | .48 | 13 trades |
| **In-Sample (IS)** | 531 | 0.25% | **98.00%** | **0.14%** | 7.00% | .27 | 14 trades |
| **Out-of-Sample (OOS)** | 228 | 0.25% | **100.00%** | **0.00%** | 2.53% | .10 | 8 trades |

## 2. In-Sample vs Out-of-Sample Performance Stability
- **In-Sample (70%)**: PF 1.31, Win Rate 44.07%, Max DD .30 (9.13%).
- **Out-of-Sample (30%)**: PF 2.72, Win Rate 60.96%, Max DD .69 (5.94%).
- **PF Retention**: **208.71%**, confirming robust edge expansion in out-of-sample data without parameter decay.
