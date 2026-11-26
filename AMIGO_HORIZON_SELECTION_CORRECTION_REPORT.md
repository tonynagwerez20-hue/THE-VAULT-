# AMIGO HORIZON SELECTION CORRECTION REPORT

## 1. Executive Summary

`SelectApprovedHorizon` in `MQL5/Include/Strategy Engine.mqh` was rewritten from a strict all-7-timeframes-must-agree veto into hierarchical independent per-horizon evaluation. Longer-horizon failure no longer suppresses shorter valid horizons. Missing/invalid TF data is a hard failure, never neutral. Countertrend scalps are now permitted when setup+entry support the direction.

**Compilation:** 0 errors, 0 warnings (AMIGO.mq5 + Strategy Engine.mqh).

---

## 2. Exact Source File Changed

| File | Path | Change |
|------|------|--------|
| Strategy Engine | `MQL5/Include/Strategy Engine.mqh` (315 lines) | `SelectApprovedHorizon` rewritten; new `TFBias` helper added |
| AMIGO.mq5 | `MQL5/Experts/AMIGO.mq5` | No change (horizon consumers unchanged) |

---

## 3. Before/After Behavior

### Before (lines 37-68 original)
- All 7 TFs must be in {-1,0,+1} and none opposing direction.
- `m1_dir != d` → reject.
- Continuation: `m5_dir != d` → reject; then single horizon assignment.
- Mean-reversion: requires balanced regime with neutral higher TFs.
- **Any opposing TF → NO_TRADE.**

### After
- `TFBias()` computes weighted directional bias per TF group.
- Each horizon (Swing → Intraday → Scalp) evaluated independently with its own context/setup/entry groups.
- Swing requires ctx bias ≥ +0.25, setup bias ≥ +0.25, entry trigger.
- Intraday allows neutral/mixed context (≥ -0.25), setup ≥ +0.25, entry trigger.
- Scalp permits countertrend (opposing HTF) when setup + entry support direction.
- Missing/invalid TF data → hard reject (not neutral).
- Longer failure → continue to next shorter horizon.

---

## 4. Hierarchical Role Mapping

| Horizon | Context TFs | Setup TFs | Entry TFs |
|---------|-------------|-----------|-----------|
| Swing | D1, H4 | H1, M30, M15 | M5, M1 |
| Intraday | D1, H4 | H1, M30 | M15, M5 |
| Scalping | H1, M30 | M15, M5 | M1 |

---

## 5. Directional Bias Formula

```
B_d = SUM(w_i * c_i * d_i) / SUM(w_i * c_i)
```

- w_i = timeframe weight (1.0 provisional, configurable)
- c_i = normalized confidence (1.0 provisional)
- d_i = +1 support, 0 neutral, -1 opposing
- Missing TFs excluded from denominator (not treated as neutral)
- Coverage tracked separately via valid_count

### Provisional Thresholds (configurable)
- B_d ≥ +0.25: SUPPORTIVE
- -0.25 < B_d < +0.25: NEUTRAL_OR_MIXED
- B_d ≤ -0.25: OPPOSING
- B_d ≤ -0.60: STRONGLY_OPPOSING

---

## 6. Hard Vetoes Retained

- Fatal data quality (DQ_FATAL)
- Missing core ticks / broker invalid
- Regime NO_TRADE
- News admission failure
- Score gate (best_score < 0.45 or margin < 0.05)
- Regime/hypothesis mismatch
- Invalid TF values outside [-1,1]
- Missing entry trigger for each horizon
- Proxy agreement (footprint, persistence, divergence)
- Risk controller hard gates (min-lot, daily loss, distortion)
- Broker volume/stop/margin checks

---

## 7. Risk Policy

**Unchanged.** No risk policy modifications. Per-trade ceiling, 2% daily loss, 5x distortion, min-lot feasibility, broker checks, max 5 entries/day, idempotency — all preserved.

---

## 8. Compilation Evidence

```
Compilation succeeded: 0 errors, 0 warnings found.
cpu='X64 Regular', 7165 ms elapsed
```

---

## 9. Unresolved / Provisional Items

1. Weights and confidence normalization are provisional (1.0). Need calibration.
2. TFBias uses integer TF directions only; float confidence not yet threaded.
3. Python parity not implemented — no Python mirror of SelectApprovedHorizon exists.
4. Countertrend confirmation classes (2 for scalp, 3 for intraday) not yet wired; currently proxy-based.
5. No deterministic tests yet for the 23 required scenarios.
6. Per-horizon performance metrics not yet added.

---

## 10. Execution Boundary Compliance

- No trading account connected.
- No orders submitted.
- No EA attached to chart.
- No remote push.
- Offline compilation only.
- Risk policy unchanged.
