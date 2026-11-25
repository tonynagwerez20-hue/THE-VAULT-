# AMIGO 24H Live Market Demo Execution Report

## Mission Status: BLOCKED - Account Insufficiency

**Date:** 2026-11-25
**Account:** Exness-MT5Trial10 (AMIGO TEST SITE)
**Login:** 486121280
**Account Type:** DEMO
**Current Balance:** $53.34
**MICRO_AGGRESSIVE_DEMO Profile:** ACTIVE

---

## Executive Summary

The 24-hour autonomous demo trading mission for AMIGO EA could not proceed due to account insufficiency.

### Blocker

**Minimum viable account size: $250** (based on backtesting across account sizes).

**Current demo account balance: $53.34**

This is **4.7x below** the minimum viable account size for the MICRO_AGGRESSIVE_DEMO profile.

---

## Backtest Results Summary

### Account Size Matrix

| Account Size | Status | Reason | Trades Executed |
|--------------|--------|--------|------------------|
| $15 | NO_TRADE | MIN_LOT_UNSAFE | 0 |
| $20 | NO_TRADE | MIN_LOT_UNSAFE | 0 |
| $50 | NO_TRADE | MIN_LOT_UNSAFE | 0 |
| $100 | NO_TRADE | MIN_LOT_UNSAFE / ESTIMATED_STOP_RISK_ABOVE_2PCT | 0 |
| $200 | NO_TRADE | ESTIMATED_STOP_RISK_ABOVE_2PCT | 0 |
| **$250** | **ACCOMMODATED** | **MIN_LOT_ACCOMMODATED** | **3** |
| **$500** | **ACCOMMODATED** | **MIN_LOT_ACCOMMODATED / OK** | **4** |
| **$1000** | **ACCOMMODATED** | **MIN_LOT_ACCOMMODATED / OK** | **4** |

### Key Findings

1. **$250 is the minimum viable account** for MICRO_AGGRESSIVE_DEMO profile
2. **$500+ recommended** for production-like conditions
3. **$1000+ recommended** for full risk management capability

### Why Small Accounts Fail

The issue is the minimum lot size constraint:
- Risk per trade: 0.50% of equity
- For $100 account: target risk = $0.50
- Gold (XAUUSDm) minimum lot loss = $2.50 (for 1.00 lot)
- This means even 1.00 lot represents 2.5% of equity
- Minimum lot distortion exceeds max allowed (3x-5x)

### Why $250 Works

- Risk per trade: 0.50% of equity = $1.25
- Min lot loss: $2.50 (for 1.00 lot)
- Distortion: 2.0x - 4.0x (within max allowed 5x)
- Status: MIN_LOT_ACCOMMODATED

---

## Live Demo Execution Status

### Not Executed Due To:

1. **Account Balance Insufficient:** $53.34 < $250 minimum viable
2. **Risk Controller Would Reject:** MIN_LOT_UNSAFE for current equity level
3. **Live Trading Gate:** Cannot proceed without sufficient equity

---

## Next Steps Required

### Immediate Actions:

1. **Obtain adequate demo account funding:** Minimum $250 USD
2. **OR adjust MICRO_AGGRESSIVE_DEMO profile** for current balance level
3. **OR use a larger demo account** for the 24-hour mission

### Alternative Approaches:

- **Increase demo balance** via broker (may require new account)
- **Use Micro lot sizing** with reduced risk profile
- **Scale down risk parameters** for current balance

---

## Decision Flow

### Step 1: Account Balance Check ✅
- Current: $53.34
- Required: $250+
- **STATUS: FAIL**

### Step 2: Backtest Viability Check ✅
- At $250: Executable and ACCOMMODATED
- At $500: Executable and ACCOMMODATED
- At $1000: Executable and ACCOMMODATED
- **STATUS: PASS**

### Step 3: Live Execution Decision ⏸️
- **BLOCKED** pending account sufficiency

---

## Recommendations

1. **Funding Required:** Add minimum $250 USD to demo account
2. **Profile Validation:** MICRO_AGGRESSIVE_DEMO validated for $250+ accounts
3. **Mission Ready:** Once funded, proceed with 24-hour live demo

---

*Report generated: 2026-11-25*
*Mission: AMIGO 24H Live Market Demo*
