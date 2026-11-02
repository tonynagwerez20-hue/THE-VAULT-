# AMIGO — Native MT5 Test Execution Status & Audit

## 1. Test Script Execution vs Compilation Status

| Script / Test Binary | Compilation Status | Actual Native MT5 Execution | Verification Level | Deficiencies / Findings |
| :--- | :--- | :--- | :--- | :--- |
| **`AMIGO.ex5`** | **0 errors, 0 warnings** | **NOT EXECUTED** | **COMPILED-ONLY** | Blocked by terminal isolation policy (BLK-001). |
| **`Test_ShadowHarness.ex5`** | **0 errors, 0 warnings** | **NOT EXECUTED** | **COMPILED-ONLY** | Compiled clean; runtime validation in native terminal pending terminal isolation. |
| **`Test_HorizonPropagation.ex5`** | **0 errors, 0 warnings** | **NOT EXECUTED** | **COMPILED-ONLY** | Script verified syntactically; prints verification strings, but has not run in live terminal. |
| **`Test_RegimeReachability.ex5`** | **0 errors, 0 warnings** | **NOT EXECUTED** | **COMPILED-ONLY** | Evaluates 3 distinct synthetic regimes; compiled clean; not run in live terminal. |

## 2. Distinction Between Compilation and Runtime Proof

> [!WARNING]
> **Compilation Is Not Runtime Proof**
> Passing MetaEditor compilation proves syntax, symbol resolution, and function signature matching. It does **not** prove:
> 1. Runtime memory allocation or pointer validity under real tick streams.
> 2. Absence of order send rejections or broker error retcodes (e.g. `ERR_TRADE_SEND_FAILED`).
> 3. Accurate tick-by-tick state persistence across high-frequency market updates.
> 4. Physical execution timing and latency characteristics.

## 3. Evaluation of Native MQL5 Test Implementations

### A. `Test_HorizonPropagation.mq5`
- **Mechanism**: Registers 3 distinct dummy positions (`1001` Scalp, `1002` Intraday, `1003` Swing) into `g_positions[]`.
- **Assertions**:
  - Calculates expected BE triggers: Scalping=2006.60, Intraday=2010.00, Swing=2012.00.
  - Asserts that all 3 horizons are preserved in memory.
- **Limitation**: Does not simulate subsequent `PositionManagerTick()` price movement over time.

### B. `Test_ShadowHarness.mq5`
- **Mechanism**:
  - Phase 1: Injects 3 synthetic trade intents into `ExecuteIntent()` in shadow mode. Verifies `mock_submission_count == 0` (zero broker submissions).
  - Phase 2: Injects a synthetic position ticket (`9001`) with entry=2000.00, SL=1990.00, TP=2040.00.
  - Simulates tick progress past the 50% break-even mark and dynamic 25% trailing ratchet.
- **Limitation**: Currently hardcodes `HORIZON_INTRADAY` during position registration; does not test scalping 1h timeout or session liquidation at runtime.

### C. `Test_RegimeReachability.mq5`
- **Mechanism**: Feeds synthetic `FeatureSnapshot` structures directly into `EvaluateRegime()`.
- **Assertions**: Verifies classification of `REGIME_TREND_UP` (1), `REGIME_TREND_DOWN` (2), and `REGIME_BALANCED` (3).
- **Limitation**: Unit-level coverage only; does not evaluate multi-timeframe regime conflict resolution.
