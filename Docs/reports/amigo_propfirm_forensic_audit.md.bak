# ALGOMIND PROP-FIRM FORENSIC AUDIT

## $5,000 Account

### Test Configuration
- Firm Model: FundedNext Stellar 2-Step (scaled to $5K)
- Profit Target Phase 1: 8% ($400)
- Profit Target Phase 2: 5% ($250)
- Daily Loss Limit: 5% ($250)
- Max Overall Loss: 10% ($500, static)
- EA Allowed: YES

> [!IMPORTANT]
> The $5K prop-firm rules were **ASSUMED** to be the same percentage-based rules as the $50K model.
> FundedNext does not offer a $5K Stellar model at this specification.
> STATUS: **ASSUMED — NOT VERIFIED**

### Results by Risk Level

|   AccountSize |   RiskPct | Status             |   P1Trades |   P1Days |   P2Trades |   P2Days |   WorstDailyP1 |   WorstDailyP1Pct |   Violations |
|--------------:|----------:|:-------------------|-----------:|---------:|-----------:|---------:|---------------:|------------------:|-------------:|
|          5000 |      0.1  | PASS               |        196 |       32 |         22 |        1 |        -153.4  |            3.068  |            0 |
|          5000 |      0.25 | PASS               |        118 |       22 |         94 |       11 |         -93.68 |            1.8736 |            0 |
|          5000 |      0.5  | FAIL_P1_DAILY_LOSS |         44 |        7 |          0 |        0 |        -267.47 |            5.3494 |            1 |

---

## $50,000 Account

### Test Configuration
- Firm Model: FundedNext Stellar 2-Step
- Profit Target Phase 1: 8% ($4,000)
- Profit Target Phase 2: 5% ($2,500)
- Daily Loss Limit: 5% ($2,500)
- Max Overall Loss: 10% ($5,000, static floor at $45,000)
- EA Allowed: YES

> [!NOTE]
> Rules verified against FundedNext official documentation (September 2026).

### Results by Risk Level

|   AccountSize |   RiskPct | Status             |   P1Trades |   P1Days |   P2Trades |   P2Days |   WorstDailyP1 |   WorstDailyP1Pct |   Violations |
|--------------:|----------:|:-------------------|-----------:|---------:|-----------:|---------:|---------------:|------------------:|-------------:|
|         50000 |      0.1  | PASS               |        230 |       32 |         74 |       14 |        -532.32 |            1.0646 |            0 |
|         50000 |      0.25 | PASS               |        197 |       32 |         17 |        1 |       -1474.12 |            2.9482 |            0 |
|         50000 |      0.3  | PASS               |        118 |       22 |         92 |       11 |       -1675.16 |            3.3503 |            0 |
|         50000 |      0.5  | FAIL_P2_DAILY_LOSS |         31 |        6 |         12 |        2 |       -1941.08 |            3.8822 |            1 |

### $50K 0.50% Failure Analysis

- **Status**: FAIL_P2_DAILY_LOSS
- **Worst Daily Loss (P1)**: $1,941.08 (3.88% of account)
- **Daily Limit**: $2,500.00 (5.00%)
- **Violation Trade Index**: 42
- **Violation Type**: DAILY_LOSS
- **Daily Loss at Breach**: $2,627.61
- **Balance at Breach**: $47,860.80
- **Date**: 2025-10-14

**Mechanical Cause**: At 0.50% risk on $50,000, the per-trade risk budget is $250.
Multiple losing trades on the same day compound the daily closed loss beyond the 5% ($2,500) daily limit.
The strategy's natural losing streak pattern, combined with the higher per-trade dollar exposure,
causes the cumulative intra-day loss to breach the daily ceiling.

## Prop-Firm Ruleset Integrity

| Rule | Source | Status |
|:-----|:-------|:-------|
| FundedNext Stellar 2-Step ($50K) | Official Documentation (Sept 2026) | VERIFIED |
| FundedNext Stellar 1-Step ($50K) | Official Documentation (Sept 2026) | VERIFIED |
| FundedNext Stellar Lite ($50K) | Official Documentation (Sept 2026) | VERIFIED |
| FundingPips 2-Step Standard ($50K) | Official Documentation (Sept 2026) | VERIFIED |
| FundedNext/FundingPips $5K models | Not specified | **ASSUMED — NOT VERIFIED** |
| Daily loss reset mechanism | Midnight MT5 time / UTC | **ASSUMED — implementation uses exit_date grouping** |
| Floating P&L in daily loss calc | Some firms include floating | **NOT MODELED — only closed P&L tracked** |
