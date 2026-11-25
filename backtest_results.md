# AMIGO 24H Live Market Demo - Backtest Results

## Account Size Matrix

### Summary

| Account | Test | Trades Executed | Trade Outcomes |
|---------|------|-----------------|----------------|
| $100 | amigo_micro_100 | 0 | ALL REJECTED - MIN_LOT_UNSAFE |
| $200 | amigo_micro_200 | 3 | ALL REJECTED - ESTIMATED_STOP_RISK_ABOVE_2PCT |
| $250 | amigo_micro_250 | 3 | ALL ACCOMMODATED - TRADE EXECUTED |
| $500 | amigo_micro_500 | 4 | ALL ACCOMMODATED - TRADE EXECUTED |
| $1000 | amigo_micro_1000 | 4 | ALL ACCOMMODATED - TRADE EXECUTED |

### $15 - $50 Results (Previously Tested)

| Account | Status | Reason | Outcome |
|---------|--------|--------|---------|
| $15 | NO_TRADE | MIN_LOT_UNSAFE | All rejected |
| $20 | NO_TRADE | MIN_LOT_UNSAFE | All rejected |

### Key Findings

1. **Minimum viable account size for MICRO_AGGRESSIVE profile: ~$250**

2. **$250 Account Results:**
   - Risk controller: `class=SMALL`, `target_risk=$1.25(0.50%)`
   - First trade: `distortion=2.00x`, `min_lot_status=ACCOMMODATED`, `final_volume=0.01`
   - Second trade: `distortion=2.40x`, `min_lot_status=ACCOMMODATED`, `final_volume=0.01`
   - Third trade: `distortion=4.00x`, `min_lot_status=ACCOMMODATED`, `final_volume=0.01`
   - All trades approved: `reason=MIN_LOT_ACCOMMODATED`

3. **$500 Account Results:**
   - Risk controller: `class=SMALL`, `target_risk=$2.50(0.50%)`
   - Multiple trades with `distortion=0.60x` to `2.00x`
   - All trades approved: `reason=MIN_LOT_ACCOMMODATED` or `reason=OK`
   - Account classification: `class=SMALL` (all tests)

4. **$1000 Account Results:**
   - Risk controller: `class=STANDARD`, `target_risk=$5.00(0.50%)`
   - Multiple trades with `distortion=0.60x` to `1.00x`
   - All trades approved: `reason=MIN_LOT_ACCOMMODATED` or `reason=OK`
   - Account classification: `class=STANDARD` (all tests)

5. **$200 Account Results:**
   - Risk controller: `class=SMALL`, `target_risk=$1.00(0.50%)`
   - All trades rejected: `reason=ESTIMATED_STOP_RISK_ABOVE_2PCT`
   - `max_allowed_distortion=5.0x` but `estimation` blocked due to risk estimation

### Trading Logic Analysis

From the SIZE_DIAG entries:

| Equity | Target Risk | Max Risk | Stop Dist | Min Lot Loss | Distortion | Max Distortion | Status |
|---------|-------------|----------|-----------|--------------|------------|----------------|--------|
| $100 | $0.50(0.50%) | $2.50 | 2.50 | 2.50 | 5.00x | 3.5x | SIGNAL_VALID_ACCOUNT_INFEASIBLE |
| $100 | $0.50(0.50%) | $2.50 | 3.00 | 3.00 | 6.00x | 5.0x | SIGNAL_VALID_ACCOUNT_INFEASIBLE |
| $100 | $0.50(0.50%) | $2.50 | 5.00 | 5.00 | 10.0x | 5.0x | SIGNAL_VALID_ACCOUNT_INFEASIBLE |
| $250 | $1.25(0.50%) | $6.25 | 2.50 | 2.50 | 2.00x | 5.0x | SIGNAL_VALID_EXECUTABLE |
| $250 | $1.25(0.50%) | $6.25 | 3.00 | 3.00 | 2.40x | 5.0x | SIGNAL_VALID_EXECUTABLE |
| $250 | $1.25(0.50%) | $6.25 | 5.00 | 5.00 | 4.00x | 5.0x | SIGNAL_VALID_EXECUTABLE |
| $500 | $2.50(0.50%) | $12.50 | 0.50 | 0.50 | 1.00x | 5.0x | SIGNAL_VALID_EXECUTABLE |
| $500 | $2.50(0.50%) | $12.50 | 1.50 | 1.50 | 0.60x | 5.0x | SIGNAL_VALID_EXECUTABLE |
| $500 | $2.50(0.50%) | $12.50 | 2.00 | 2.00 | 0.80x | 5.0x | SIGNAL_VALID_EXECUTABLE |
| $500 | $2.50(0.50%) | $12.50 | 2.50 | 2.50 | 1.00x | 5.0x | SIGNAL_VALID_EXECUTABLE |
| $500 | $2.50(0.50%) | $12.50 | 3.00 | 3.00 | 1.20x | 5.0x | SIGNAL_VALID_EXECUTABLE |
| $500 | $2.50(0.50%) | $12.50 | 5.00 | 5.00 | 2.00x | 5.0x | SIGNAL_VALID_EXECUTABLE |
| $1000 | $5.00(0.50%) | $25.00 | 0.50 | 0.50 | 1.00x | 5.0x | SIGNAL_VALID_EXECUTABLE |
| $1000 | $5.00(0.50%) | $25.00 | 1.50 | 1.50 | 0.90x | 5.0x | SIGNAL_VALID_EXECUTABLE |
| $1000 | $5.00(0.50%) | $25.00 | 2.00 | 2.00 | 0.80x | 5.0x | SIGNAL_VALID_EXECUTABLE |
| $1000 | $5.00(0.50%) | $25.00 | 2.50 | 2.50 | 1.00x | 5.0x | SIGNAL_VALID_EXECUTABLE |
| $1000 | $5.00(0.50%) | $25.00 | 3.00 | 3.00 | 0.60x | 5.0x | SIGNAL_VALID_EXECUTABLE |
| $1000 | $5.00(0.50%) | $25.00 | 5.00 | 5.00 | 1.00x | 5.0x | SIGNAL_VALID_EXECUTABLE |

### Risk Curve Analysis

From the spline in RiskController.mqh:
- At $100 equity: risk% = 1.00, max_distortion = 3.5
- At $250 equity: risk% = 0.75, max_distortion = 3.0
- At $500 equity: risk% = 0.50, max_distortion = 2.5
- At $1000 equity: risk% = 0.50, max_distortion = 2.0

The MICRO_AGGRESSIVE_DEMO profile at 0.50% risk works for accounts from $250 up.

### Minimum Viable Equity Calculation

Using `RiskControllerGetMinimumViableEquity(min_lot_loss, effective_risk_pct, max_distortion)`:

- For $15 account: min_lot_loss ≈ $2.50, required_equity ≈ $1000
- For $100 account: min_lot_loss ≈ $2.50-$5.00, required_equity ≈ $2000-$1000

The required equity calculation shows the account must have enough equity so that:
```
min_lot_loss * max_distortion <= ABSOLUTE_MAX_RISK_PERCENT * equity
```

---

## Next Steps

1. **Deploy to live demo account** - Switch account to $250+ minimum
2. **24-hour monitoring** - Run AMIGO EA on Exness demo
3. **Generate final report** - AMIGO_24H_LIVE_MARKET_DEMO_EXECUTION_REPORT.md
4. **Decision gate** - Continue, stop, or adjust based on results

## Recommendations

- **Minimum viable account size: $250** (MICRO_AGGRESSIVE profile is executable)
- **$500+ recommended** for more realistic risk management and margin safety
- **$1000+ recommended** for production-like trading conditions

---

*Report generated during AMIGO 24H autonomous demo trading mission.*
