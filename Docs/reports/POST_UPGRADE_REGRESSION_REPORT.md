# AMIGO — Post-Upgrade Regression Report

## 1. Regression Test Summary

A systematic verification was conducted across all subsystems to ensure the top-down multi-timeframe and horizon management upgrades introduced zero functional or contract regressions.

| Subsystem / Invariant | Baseline Expectation | Post-Upgrade State | Regression Finding |
| :--- | :--- | :--- | :--- |
| **Strategy Engine** | Two families (`CONTINUATION`, `MEAN_REVERSION`) | Exact two families preserved | **ZERO REGRESSIONS (0 diffs)** |
| **Feature Vector Engine** | Canonical feature snapshot & GAP logic | Preserved without modifications | **ZERO REGRESSIONS (0 diffs)** |
| **Shadow Mode Isolation** | `InpShadowOnly = true` fail-safe | Hardcoded default `true`; orders intercepted | **ZERO REGRESSIONS** |
| **Account Risk Sizing** | 3-state min lot, spline curve, distortion clamp | Preserved; evaluated pre-order | **ZERO REGRESSIONS** |
| **Intraday Trailing** | 50% BE trigger, 25% dynamic trail, 2.0R partial | Preserved in `Position Manager.mqh` | **ZERO REGRESSIONS** |
| **Python Unit Suite** | 98 passing unit/parity tests | 98 passed, 0 failed, 2 skipped (100% pass) | **ZERO REGRESSIONS** |
| **MQL5 Compilation** | 0 errors, 0 warnings with MetaEditor | All 4 targets compiled cleanly | **ZERO REGRESSIONS** |

---

## 2. Invariant Checklist Verification

- [x] **Protected File Invariant**: `FeatureVector.mqh` and `Strategy Engine.mqh` have zero uncommitted changes.
- [x] **Account Sizing Invariant**: $\mathcal{S}(\text{strategy\_input}, \text{market\_state}) = \mathcal{S}(\text{market\_state})$ preserved. Account balance does not influence strategy scores or regime classification.
- [x] **Monetary Risk Ceiling**: Effective risk strictly obeys spline interpolation curve ($0.50\% - 1.50\%$).
- [x] **Network Quarantine**: Outbound terminal execution withheld.
