"""Model contract tests for AlgoMind canonical domain objects (Phase 0)."""

from __future__ import annotations

import pytest

from algomind.core.enums import Direction, Regime, StrategyType
from algomind.core.models import (
    DecisionMessage,
    FeatureSnapshot,
    MarketSnapshot,
    MarketState,
    Signal,
)
from algomind.core.serialization import dumps, loads


def test_market_snapshot_minimum_contract() -> None:
    snap = MarketSnapshot(
        symbol="XAUUSD",
        timestamp="2026-09-01T00:00:00+00:00",
        bid=100.0,
        ask=100.5,
        ohlc={"high": 101.0, "low": 99.0, "open": 100.0, "close": 100.5},
    )
    assert snap.snapshot_id.startswith("snap-")
    assert snap.schema_version >= 1
    assert snap.bid == 100.0


def test_market_state_regime_unclassified_is_none() -> None:
    state = MarketState(
        symbol="XAUUSD",
        timestamp="2026-09-01T00:00:00+00:00",
    )
    assert state.trend_state is None
    assert state.volatility_state is None
    assert state.value_state is None
    assert state.structure_state is None


def test_signal_regime_unclassified_is_none() -> None:
    signal = Signal(
        symbol="XAUUSD",
        timestamp="2026-09-01T00:00:00+00:00",
        direction=Direction.BUY,
        strategy=StrategyType.CONTINUATION,
        confidence=0.7,
    )
    assert signal.regime is None


def test_signal_serialization_round_trip() -> None:
    signal = Signal(
        symbol="XAUUSD",
        timestamp="2026-09-01T00:00:00+00:00",
        direction=Direction.BUY,
        strategy=StrategyType.CONTINUATION,
        confidence=0.7,
        regime=Regime.TREND_UP,
    )
    blob = dumps(signal, message_type="signal", message_id=signal.signal_id)
    restored = loads(blob, Signal)
    assert restored.strategy == StrategyType.CONTINUATION
    assert restored.regime == Regime.TREND_UP


def test_feature_snapshot_buckets_present() -> None:
    fs = FeatureSnapshot(symbol="XAUUSD", timestamp="2026-09-01T00:00:00+00:00")
    for key in (
        "price_features", "volatility_features", "structure_features", "vwap_features",
        "value_area_features", "liquidity_features", "imbalance_features",
        "orderflow_features", "options_features", "news_features", "session_features",
        "execution_features", "cftc_features", "metadata",
    ):
        assert hasattr(fs, key), key


def test_decision_message_expiry_validation() -> None:
    with pytest.raises(ValueError):
        DecisionMessage(
            symbol="XAUUSD",
            timestamp="2026-09-01T10:00:00+00:00",
            expiry="2026-09-01T09:00:00+00:00",
        )
