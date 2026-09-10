"""Serialization foundation tests (Phase 0)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import algomind
from algomind.core.enums import DecisionAction, Regime
from algomind.core.models import DecisionMessage
from algomind.core.serialization import dumps, loads


def test_dumps_loads_round_trip_scalar() -> None:
    payload = {
        "symbol": "XAUUSD",
        "timestamp": "2026-09-01T00:00:00+00:00",
        "decision_id": "dec-1",
    }
    msg = DecisionMessage(**payload)
    blob = dumps(msg, message_type="test", message_id="m1")
    restored = loads(blob, DecisionMessage)
    assert restored.model_dump(mode="json")["symbol"] == "XAUUSD"
    assert restored.model_dump(mode="json")["decision_id"] == "dec-1"


def test_decision_message_round_trip() -> None:
    timestamp = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
    msg = DecisionMessage(
        symbol="XAUUSD",
        timestamp=timestamp,
        regime=Regime.TREND_UP,
        action=DecisionAction.TRADE,
        confidence=0.7,
        stop=Decimal("99.0"),
        target=Decimal("102.0"),
        feature_version="v1",
            )
    blob = dumps(msg, message_type="decision", message_id=msg.decision_id)
    restored = loads(blob, DecisionMessage)
    assert restored.model_dump(mode="json")["symbol"] == "XAUUSD"
    assert restored.action == DecisionAction.TRADE
    assert restored.regime == Regime.TREND_UP
    assert restored.schema_version == 1
    assert restored.decision_id == msg.decision_id


def test_decision_message_fail_closed_defaults() -> None:
    msg = DecisionMessage(symbol="XAUUSD", timestamp="2026-09-01T00:00:00+00:00")
    assert msg.action == DecisionAction.NO_TRADE
    assert msg.confidence == 0.0
    assert msg.data_quality == algomind.DataQuality.MISSING


def test_decision_id_unique() -> None:
    a = DecisionMessage(symbol="XAUUSD", timestamp="2026-09-01T00:00:00+00:00")
    b = DecisionMessage(symbol="XAUUSD", timestamp="2026-09-01T00:00:00+00:00")
    assert a.decision_id != b.decision_id
