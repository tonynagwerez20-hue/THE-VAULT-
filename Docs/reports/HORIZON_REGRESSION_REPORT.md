# AMIGO — Horizon Implementation Regression Report

## 1. Scope of Regression Testing
Regression analysis was conducted across:
1. Core Strategy Scoring (`Strategy Engine.mqh`)
2. Feature Vector Generation (`FeatureVector.mqh`)
3. Risk & Account Constraints (`Risk Engine.mqh`, `RiskController.mqh`, `Account Execution Engine.mqh`)
4. Shadow Isolation & Safe Execution Gate (`Execution Engine.mqh`)

## 2. Findings
- **Strategy & Regime Independence**: Strategy scoring formulas (`ContinuationEvidence`, `MR_Evidence`) remain 100% unchanged.
- **Account Sizing Invariance**: Sizing algorithms and distortion calculations are untouched; account size has zero impact on horizon classification.
- **Shadow Mode Integrity**: Retains fail-safe operation; zero orders dispatched to live broker when `shadow_only = true`.
- **Zero Regressions Detected**: 98/98 Python parity tests passed cleanly, and all MQL5 scripts compile with zero errors and zero warnings.
