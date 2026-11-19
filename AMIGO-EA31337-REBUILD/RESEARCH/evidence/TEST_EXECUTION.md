# Executed audit checks

Commands executed from `E:\AMIGO-EA31337-REBUILD` in PowerShell unless stated otherwise. All returned exit code 0. No existing test files were changed. `-B` suppresses bytecode; pytest cache and plugin autoload were disabled. These tests do not connect to a broker or launch MetaTrader. Some assert source text or run independent Python reference calculations; they are not native runtime parity evidence.

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -B -m pytest -q -p no:cacheprovider Python/test_quant_regression.py AMIGO_BASELINE/Python/algomind/tests/test_approved_horizon_selector_candidate.py AMIGO_BASELINE/Python/algomind/tests/test_saved_horizon_management.py AMIGO_BASELINE/Python/algomind/tests/test_horizon_decision_contract_candidate.py AMIGO_BASELINE/Python/algomind/tests/test_timeframe_input_ladder.py AMIGO_BASELINE/Python/algomind/tests/test_tick_proxy_math.py AMIGO_BASELINE/Python/algomind/tests/test_topdown_volatility_candidate.py --junitxml=C:/Users/USER/Documents/Codex/2026-11-18/e-amigo-ea31337-rebuild/outputs/audit_tests.xml
```

Result: 56 collected, 56 passed, 0 failed, 0 skipped. Terminal summary: `56 passed in 3.41s`.

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:PYTHONPATH='E:\AMIGO-EA31337-REBUILD\AMIGO_BASELINE\Python'
python -B -m pytest -q -p no:cacheprovider AMIGO_BASELINE/Python/algomind/orderflow_lab/tests/test_horizons.py AMIGO_BASELINE/Python/algomind/orderflow_lab/tests/test_python_mql5_parity.py --junitxml=C:/Users/USER/Documents/Codex/2026-11-18/e-amigo-ea31337-rebuild/outputs/horizon_tests.xml
```

Result: 16 collected, 16 passed, 0 failed, 0 skipped. Terminal summary: `16 passed in 0.40s`.

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -B -m pytest -q -p no:cacheprovider AMIGO_BASELINE/Python/algomind/tests/test_completion_lock_order_candidate.py AMIGO_BASELINE/Python/algomind/tests/test_chronology_bounds_candidate.py AMIGO_BASELINE/Python/algomind/tests/test_risk_arithmetic_guards.py --junitxml=C:/Users/USER/Documents/Codex/2026-11-18/e-amigo-ea31337-rebuild/outputs/guard_tests.xml
```

Result: 30 collected, 30 passed, 0 failed, 0 skipped. Terminal summary: `30 passed in 0.93s`.

Per-file/per-class counts and machine-recorded timings are in `test_execution_summary.json`. The selected total is 102 tests, not the full repository suite. Native runtime, history import, real broker cost schedules, transaction rejections/partial fills and ten-year performance were not exercised by these commands.

From `C:\Users\USER\Documents\Codex\2026-11-18\e-amigo-ea31337-rebuild`:

```powershell
python -B work\audit_probes.py
```

Result: 80 completed cash-risk scenarios spanning $5–$10,000 and one metric-accounting probe; output `account_scenario_audit.json`. These use hypothetical contract/cost assumptions. They do not submit orders or establish historical profitability.

Data acquisition command, same workspace:

```powershell
python -B work\acquire_histdata.py
```

Original ZIP destination: `E:\AMIGO-EA31337-REBUILD\research-data\histdata`. Monthly results and source URLs/checksums are recorded in `histdata_acquisition_manifest.json`. Archive acquisition success and backtest acceptance are separate: `quality_failure` records must not be treated as valid chronological input.
