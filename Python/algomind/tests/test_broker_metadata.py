# test_broker_metadata.py
"""Broker metadata regression test for XAUUSD contracts.

This test validates that the broker's contract specifications (as reported
by the MetaTrader5 API) match the expectations encoded in the AMIGO
configuration. It is the first step in the three‑phase validation plan:

1️⃣ Broker‑metadata regression test (Contract C verification)
2️⃣ Shadow‑mode MT5 validation (runtime telemetry vs Phase D expectations)
3️⃣ Demo execution (final end‑to‑end check)

The test runs in *shadow* mode – it does **not** place any orders. It simply
fetches symbol information and asserts that the key parameters required by
`AccountExecutionEngine.mqh` are correct.

If the `MetaTrader5` Python package is unavailable the test is skipped.
"""

import pytest

# Attempt to import MetaTrader5; skip the test if not present.
try:
    import MetaTrader5 as mt5
except ImportError:  # pragma: no cover
    mt5 = None

# Expected broker contract parameters for XAUUSD and XAUUSDm.
# These values should be derived from the broker's specification sheet.
# Adjust them as needed before running the test.
EXPECTED_METADATA = {
    "XAUUSD": {
        "volume_min": 0.01,          # 0.01 lot = $1 per point (example)
        "volume_step": 0.01,
        "volume_max": 100.0,
        "contract_size": 100.0,      # typical for XAUUSD (100 oz per lot)
        "point": 0.01,
        "digits": 2,
        "trade_tick_value": 1.0,    # $1 per point per 0.01 lot
        "trade_tick_size": 0.01,
        "trade_stops_level": 0,      # broker‑specific, often 0 for XAU
    },
    "XAUUSDm": {
        "volume_min": 0.01,
        "volume_step": 0.01,
        "volume_max": 100.0,
        "contract_size": 100.0,
        "point": 0.01,
        "digits": 2,
        "trade_tick_value": 1.0,
        "trade_tick_size": 0.01,
        "trade_stops_level": 0,
    },
}

@pytest.fixture(scope="module")
def mt5_connection():
    """Initialize MetaTrader5 connection for the duration of the module.

    The fixture is automatically used by all tests in this file. It will
    shutdown the connection on teardown.
    """
    if mt5 is None:
        pytest.skip("MetaTrader5 Python package not installed; cannot fetch broker metadata.")
    # Initialise with default path – adjust if a custom terminal location is required.
    if not mt5.initialize():
        raise RuntimeError(f"Failed to initialize MetaTrader5: {mt5.last_error()}")
    yield
    mt5.shutdown()

def _fetch_symbol_info(symbol: str):
    """Return a dict of relevant symbol fields from MetaTrader5.

    The keys match those in ``EXPECTED_METADATA`` for straightforward
    comparison.
    """
    info = mt5.symbol_info(symbol)
    if info is None:
        raise ValueError(f"Symbol {symbol!r} not found in the connected MT5 terminal.")

    return {
        "volume_min": info.volume_min,
        "volume_step": info.volume_step,
        "volume_max": info.volume_max,
        "contract_size": info.trade_contract_size,
        "point": info.point,
        "digits": info.digits,
        "trade_tick_value": info.trade_tick_value,
        "trade_tick_size": info.trade_tick_size,
        "trade_stops_level": info.trade_stops_level,
    }

@pytest.mark.parametrize("symbol", ["XAUUSD", "XAUUSDm"])
def test_broker_contract_parameters(mt5_connection, symbol):
    """Validate that the broker's contract parameters match expectations.

    The test asserts equality for each field defined in ``EXPECTED_METADATA``.
    If a field differs, the test will fail with a clear diff.
    """
    expected = EXPECTED_METADATA[symbol]
    actual = _fetch_symbol_info(symbol)

    mismatches = []
    for key, exp_val in expected.items():
        act_val = actual.get(key)
        # Use a tolerance for floating‑point values to avoid flaky failures.
        if isinstance(exp_val, float):
            if not pytest.approx(act_val, rel=1e-6) == exp_val:
                mismatches.append(f"{key}: expected {exp_val}, got {act_val}")
        else:
            if act_val != exp_val:
                mismatches.append(f"{key}: expected {exp_val}, got {act_val}")

    assert not mismatches, f"Broker metadata mismatch for {symbol}:\n" + "\n".join(mismatches)
