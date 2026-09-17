# 10 — FAILURE ANALYSIS AND BREACH MODES

## 1. Why Balances Below $1,500 Fail Real-World Trading
1. **Minimum-Lot Distortion**: The 0.01 lot minimum volume forces a fixed dollar risk per point of stop distance ($1.00 per point). On a $100 balance, a 15-point stop risks $15.00 (15% of account), causing rapid ruin during normal losing streaks.
2. **Margin Depletion**: Balances < $50 cannot afford MT5 margin ($38.70 per 0.01 lot XAUUSDm at 1:100 leverage).

## 2. Why Prop-Firm Accounts Fail at Default 0.50% Risk
- Default 0.50% risk produces a max daily closed loss of 8.49% ($4,243.83 on $50k account).
- This violates the 5% ($2,500) FundedNext and FundingPips daily loss limit.
- **Solution**: Scale risk down to **0.20% per trade** for prop-firm challenge phases.
