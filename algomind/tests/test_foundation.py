"""Phase-0 contract tests: package imports and configuration foundation."""

from __future__ import annotations

import algomind
from algomind.config.loader import load_config
from algomind.core.enums import DecisionAction, Regime


def test_package_imports_and_version() -> None:
    assert algomind.__version__ == "0.1.0"
    for name in (
        "DataQuality", "DecisionAction", "Direction", "NewsMode",
        "OrderStatus", "Regime", "StrategyType",
        "AlgoMindError", "CommunicationError", "ConfigurationError",
        "DataError", "ExecutionError", "RiskError", "SignalError",
        "ValidationError",
    ):
        assert hasattr(algomind, name), name


def test_canonical_regime_vocabulary() -> None:
    """D4 REQ-012: canonical regime states must exist."""
    expected = {"TREND_UP", "TREND_DOWN", "BALANCED", "EXPANSION",
        "EXHAUSTION", "NEWS", "NO_TRADE"}
    assert {r.value for r in Regime} == expected


def test_canonical_action_vocabulary() -> None:
    """D4 REQ-013 decision gate: Trade/reduce/wait/NO_TRADE."""
    expected = {"TRADE", "REDUCE", "WAIT", "NO_TRADE"}
    assert {a.value for a in DecisionAction} == expected


def test_default_config_loads() -> None:
    config = load_config()
    assert config.get_float("risk", "total_limit_pct") == 5.0
    assert config.get_float("risk", "risk_per_trade_pct") == 0.5
    assert config.get_float("risk", "daily_limit_pct") == 2.0
    assert config.get_str("news", "mode") == "NEWS_OFF"
    assert config.get_str("system", "environment") == "research"
