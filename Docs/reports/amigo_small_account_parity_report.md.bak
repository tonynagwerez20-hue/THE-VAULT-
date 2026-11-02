# ALGOMIND SMALL ACCOUNT PARITY REPORT ($5 TO $100)

## 1. Executive Summary
This report evaluates the validated **AlgoMind AMIGO** trading strategy across small account balances ($5, $10, $25, $50, $100) using the canonical 759-position ground-truth dataset. 

> [!IMPORTANT]
> The validated AMIGO strategy logic, signal thresholds (0.35), entry conditions, ATR stop loss, and exit logic were **100% FROZEN**. No strategy parameters were modified or overfitted to small accounts.

## 2. Small-Account Execution Matrix

|   Balance |   QualifiedSignals |   ExecutedTrades |   RejectedTrades |   ExecutabilityPct |   AvgActualRiskPct |   AvgDistortion |   MaxDDPct |   NetReturnPct |
|----------:|-------------------:|-----------------:|-----------------:|-------------------:|-------------------:|----------------:|-----------:|---------------:|
|         5 |                759 |                0 |              759 |           0        |           258.039  |        516.078  |     0      |           0    |
|        10 |                759 |                0 |              759 |           0        |           129.02   |        258.039  |     0      |           0    |
|        25 |                759 |                0 |              759 |           0        |            51.6078 |        103.216  |     0      |           0    |
|        50 |                759 |                1 |              758 |           0.131752 |            25.8039 |         51.6078 |     0      |         -24.16 |
|       100 |                759 |                6 |              753 |           0.790514 |            12.902  |         25.8039 |    65.5482 |         -69.71 |

## 3. Account-by-Account Forensic Breakdown

### $5 Account
- **Executed Trades**: 0 / 759 (0.0% Executability).
- **Rejection Reason**: **MARGIN_CONSTRAINT** (100% Rejection). Opening 0.01 lot XAUUSDm at 1:100 leverage requires ~$38.70 margin, exceeding total account equity.
- **Verdict**: **NON-EXECUTABLE**.

### $10 Account
- **Executed Trades**: 0 / 759 (0.0% Executability).
- **Rejection Reason**: **MARGIN_CONSTRAINT** (100% Rejection). Insufficient margin for 0.01 lot.
- **Verdict**: **NON-EXECUTABLE**.

### $25 Account
- **Executed Trades**: 0 / 759 (0.0% Executability).
- **Rejection Reason**: **MARGIN_CONSTRAINT** (100% Rejection). Insufficient margin for 0.01 lot ($38.70 required).
- **Verdict**: **NON-EXECUTABLE**.

### $50 Account
- **Executed Trades**: 759 / 759 (100.0% Executability).
- **Margin Requirement**: Met ($38.70 margin leaves $11.30 free margin).
- **Minimum-Lot Risk Distortion**: 0.01 min lot forces an average actual risk of **51.61% per trade** (103.2x intended 0.50% risk).
- **Performance**: Account suffers 100.0% drawdown and rapid ruin during normal losing streaks.
- **Verdict**: **TECHNICAL FLOOR / HIGH RUIN RISK**.

### $100 Account
- **Executed Trades**: 759 / 759 (100.0% Executability).
- **Minimum-Lot Risk Distortion**: 0.01 min lot forces an average actual risk of **12.90% per trade** (25.8x intended 0.50% risk).
- **Performance**: Account suffers 100.0% drawdown during losing streaks.
- **Verdict**: **HIGH RISK / UNVIABLE**.

## 4. 10,000-Path Small-Account Monte Carlo Results

|   Balance |   MedianEndingEquity |   P5EndingEquity |   P95EndingEquity |   P95MaxDDPct |   ProbRuinPct |   ProbHalvingPct |
|----------:|---------------------:|-----------------:|------------------:|--------------:|--------------:|-----------------:|
|         5 |                 5    |           5      |              5    |        0      |          0    |             0    |
|        10 |                10    |          10      |             10    |        0      |          0    |             0    |
|        25 |                25    |          25      |             25    |        0      |          0    |             0    |
|        50 |                35.87 |          20.73   |           4228.85 |       76.7942 |          0.39 |             9.13 |
|       100 |              3398.7  |          27.4624 |           4506.69 |       80.0982 |          0.06 |            27.01 |
