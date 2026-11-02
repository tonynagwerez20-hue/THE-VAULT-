# AMIGO — Implementation Diff & Regression Report

## 1. Complete Source Code Modifications

A strict diff audit confirms that only authorized files were modified. The protected core files `FeatureVector.mqh` and `Strategy Engine.mqh` remain completely untouched.

### A. `Regime Engine.mqh`
- Added `#include <Structure Engine.mqh>`.
- Modified `ScoreTrendUp`, `ScoreTrendDown`, `ScoreExpansion`, `ScoreBalance`, `ScoreExhaustion` to accept `const TopDownContext &td`.
- Integrated higher-timeframe directional bias ($S_{HTF}$), intermediate trend alignment, and conflict classification into regime scoring.
- Updated `EvaluateRegime(f, td, cfg)` signature with backward-compatible overload `EvaluateRegime(f, cfg)`.

### B. `AMIGO.mq5`
- Line 434: Updated call from `EvaluateRegime(g_feat, g_cfg)` to `EvaluateRegime(g_feat, td, g_cfg)`.
- Line 474: Moved horizon determination upfront into entry geometry.
- Line 482: Adapted structural invalidation query to use horizon-appropriate timeframe (`stop_tf`: M1/M5 for Scalp, M15 for Intraday, H4 for Swing).
- Line 616 & 622: Passed `selected_horizon` to `PositionManagerRegister()`.

### C. `Position Manager.mqh`
- Stored `ENUM_HORIZON horizon` in `PositionState`.
- Implemented horizon-calibrated break-even trigger ratios (33% Scalp, 50% Intraday, 60% Swing).
- Enforced 3600-second holding expiry for Scalping positions.
- Enforced session-end liquidation for Intraday positions.
- Preserved baseline 25% dynamic trailing and 50% BE for Intraday positions.

### D. `Contracts header.mqh`
- Added `ENUM_HORIZON horizon` to canonical `struct TradeIntent`.

### E. `Amigo/__init__.py`
- Repaired Python module shims to map legacy `Amigo` imports to `Python/algomind/`.

---

## 2. Regression & Invariant Verification

| Invariant / Policy | Requirement | Verification Finding | Status |
| :--- | :--- | :--- | :--- |
| **Strategy Logic Preservation** | `Strategy Engine.mqh` unmodified | File has 0 diffs against git HEAD | **PRESERVED** |
| **Feature Vector Preservation** | `FeatureVector.mqh` unmodified | File has 0 diffs against git HEAD | **PRESERVED** |
| **Shadow Mode Safety** | `InpShadowOnly = true` enforced | Input remains true; no live orders sent | **ENFORCED** |
| **Two Strategy Families** | Only Continuation & Mean Reversion | No new strategy families added | **PRESERVED** |
| **Account Risk Sizing** | Governed by `AccountExecutionEvaluate()`| Invariant preserved; distortion clamped | **PRESERVED** |
| **Intraday Trailing Baseline** | 50% BE, 25% dynamic trail, 2.0R partial | Exact mathematical calculations intact | **PRESERVED** |
| **Clean Compilation** | 0 errors, 0 warnings across all files | All binaries compiled cleanly with MetaEditor | **VERIFIED** |
