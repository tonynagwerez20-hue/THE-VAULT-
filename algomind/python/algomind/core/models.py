"""Strongly typed, broker-agnostic domain models.

All market-information carriers are point-in-time: they carry an explicit
timestampand may only be built from data observed at or before that timestamp.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from algomind.core.enums import (
    DataQuality,
    DecisionAction,
    Direction,
    Regime,
    SessionState,
    StrategyType,
    StructureEventStatus,
    StructureEventType,
    Timeframe,
)

Price = float
Volume = float


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _is_nan(value: Any) -> bool:
    try:
        return math.isnan(value)
    except TypeError:
        return False


def _strip_nan_before(value: Any) -> Any:
    if _is_nan(value):
        return None
    return value


class PointInTime(BaseModel):
    """Mixin contract: every market-information carrier has a timestamp."""
    model_config = ConfigDict(str_strip_whitespace=True )

    timestamp: datetime

    @field_validator("timestamp")
    @classmethod
    def _timestamp_must_be_aware(cls, value: datetime ) -> datetime :
        if value.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware (UTC)")
        return value.astimezone(timezone.utc )


def _guard_increasing_timestamp(values: dict[str, Any]) -> dict[str, Any]:
    """Reject lifecycle windows whose end precedes their start."""
    pairs = [("start_timestamp", "end_timestamp"), ("timestamp", "expiry")]
    for start_key, end_key in pairs:
        start = values.get(start_key)
        end = values.get(end_key)
        if start is not None:
            if end is not None:
                if end < start:
                    raise ValueError(f"{end_key} must not be earlier than {start_key}" )
    return values


class MarketSnapshot(PointInTime):
    """Information observable about a symbol at a moment in time.



    Finalized to the documented minimum snapshot contract (D3 §20):
    snapshot_id, timestamp, symbol, timeframe, bid, ask, spread, OHLC
    state, broker metadata, account state, session, data-quality state,
    external-context availability and schema version. The authoritative engineering
    specification leaves the exact snapshot field schema NOT SPECIFIED (D4 §6);
    therefore documented structures without a frozen layout are carried as free-form
    dicts: exact field layout for OHLC/broker/account/session/external-context is
    left open so later phases can fill them without restructuring this model.



    """

    symbol: str = Field(min_length=1, max_length=32)
    snapshot_id: str = Field(default_factory=lambda: f"snap-{uuid4().hex[:16]}", max_length=64)
    bid: Price | None = Field(default=None, ge=0.0)
    ask: Price | None = Field(default=None, ge=0.0)
    last: Price | None = Field(default=None, ge=0.0)
    volume: Volume | None = Field(default=None, ge=0.0)
    tick_volume: Volume | None = Field(default=None, ge=0.0)
    spread: Price | None = Field(default=None, ge=0.0)
    timeframe: Timeframe | None = None
    ohlc: dict[str, Any] = Field(default_factory=dict)

    broker_metadata: dict[str, Any] = Field(default_factory=dict)



    account_state: dict[str, Any] = Field(default_factory=dict)



    session_state: SessionState | None = None
    external_context_availability: dict[str, Any] = Field(default_factory=dict)



    schema_version: int = Field(default=1, ge=1, le=99)
    data_quality: DataQuality = DataQuality.MISSING

    _normalize_prices = field_validator("bid", "ask", "last", mode="before")(lambda v: _strip_nan_before(v))

    @model_validator(mode="after")
    def _bid_not_above_ask(self) -> "MarketSnapshot":
        bid = self.bid
        ask = self.ask
        if bid is not None:
            if ask is not None:
                if bid > ask:
                    raise ValueError("bid must not exceed ask")
        return self

class OrderflowSnapshot(PointInTime):
    """Orderflow information available at a timestamp.

    ``data_quality`` distinguishes true/institutional orderflow (TRUE) from
    proxies (e.g. tick/candle volume: PROXY), limited samples (LIMITED),
    and missing data (MISSING). MT5 tick volume must never be labelled TRUE.
    """

    symbol: str = Field(min_length=1, max_length=32)
    buy_volume: Volume | None = Field(default=None, ge=0.0)
    sell_volume: Volume | None = Field(default=None, ge=0.0)
    delta: Volume | None = None
    cumulative_delta: Volume | None = None
    delta_change: Volume | None = None
    total_volume: Volume | None = None
    imbalance: float | None = Field(default=None, ge=-1.0, le=1.0)
    source: str | None = None
    data_quality: DataQuality = DataQuality.MISSING

    _normalize_volumes = field_validator("buy_volume", "sell_volume", "total_volume", mode="before")(lambda v: _strip_nan_before(v))


class FeatureSnapshot(PointInTime):
    """Container for calculated features at a timestamp.

    Feature groups finalize the documented canonical feature contract (D3 §9;
    D1 §13). The authoritative engineering specification defers exact formulas
    and units (D4 §7 feature engine), so each bucket is free-form:
    later phases can fill it without restructuring this model. All values must
    derive from data at timestamps <= ``timestamp``. Availability of external
    context (news, CFTC positioning) is carried as separate features so
    degraded/unavailable state is explicit, never silently neutral.
    """

    symbol: str = Field(min_length=1, max_length=32)
    price_features: dict[str, Any] = Field(default_factory=dict)
    volatility_features: dict[str, Any] = Field(default_factory=dict)
    structure_features: dict[str, Any] = Field(default_factory=dict)
    vwap_features: dict[str, Any] = Field(default_factory=dict)
    value_area_features: dict[str, Any] = Field(default_factory=dict)
    liquidity_features: dict[str, Any] = Field(default_factory=dict)
    imbalance_features: dict[str, Any] = Field(default_factory=dict)
    orderflow_features: dict[str, Any] = Field(default_factory=dict)
    options_features: dict[str, Any] = Field(default_factory=dict)
    news_features: dict[str, Any] = Field(default_factory=dict)
    session_features: dict[str, Any] = Field(default_factory=dict)
    execution_features: dict[str, Any] = Field(default_factory=dict)
    cftc_features: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
class MarketState(PointInTime):
    """Market regime/context at a point in time.

    Per-dimension state is carried as ``Regime | None``: ``None`` means "not
    yet classified" at this timestamp. The canonical regime vocabulary (D3 §13 /
    D4 REQ-012) has no UNKNOWN value; NO_TRADE is the documented fail-closed
    output for insufficient quality/conflicting evidence.
    """

    symbol: str = Field(min_length=1, max_length=32)
    trend_state: Regime | None = None
    volatility_state: Regime | None = None
    liquidity_state: Regime | None = None
    orderflow_state: Regime | None = None
    value_state: Regime | None = None
    structure_state: Regime | None = None
    session_state: SessionState | None = None
    directional_bias: Direction = Direction.NONE
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    data_quality: DataQuality = DataQuality.MISSING


class Signal(PointInTime):
    """A strategy-generated trade candidate; not yet risk-checked."""
    signal_id: str = Field(default_factory=lambda: f"sig-{uuid4().hex[:16]}", max_length=64)
    symbol: str = Field(min_length=1, max_length=32)
    direction: Direction
    strategy: StrategyType = StrategyType.NONE
    entry: Price | None = Field(default=None, ge=0.0)
    stop_loss: Price | None = Field(default=None, ge=0.0)
    take_profit: Price | None = Field(default=None, ge=0.0)
    timestamp: datetime
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    regime: Regime | None = None
    # None: regime not computed yet. Canonical vocabulary (D3/D4) has no UNKNOWN.
    reason_codes: list[str] = Field(default_factory=list)
    risk_multiplier: float = Field(default=1.0, gt=0.0)
    data_quality: DataQuality = DataQuality.MISSING

    _normalize_prices2 = field_validator("entry", "stop_loss", "take_profit", mode="before")(lambda v: _strip_nan_before(v))

    @model_validator(mode="after")
    def _direction_and_stops(self) -> "Signal":
        if self.direction is Direction.NONE:
            raise ValueError("Signal direction must be BUY or SELL; NONE is reserved for no-trade")
        if self.entry is None:
            return self
        if self.stop_loss is None:
            return self
        if self.direction is Direction.BUY:
            if self.stop_loss >= self.entry:
                raise ValueError("BUY stop_loss must be below entry")
        if self.direction is Direction.SELL:
            if self.stop_loss <= self.entry:
                raise ValueError("SELL stop_loss must be above entry")
        return self


class RiskDecision(BaseModel):
    """The risk engine decision on an evaluated trade."""
    approved: bool
    reason_codes: list[str] = Field(default_factory=list)
    risk_percent: float | None = Field(default=None, ge=0.0)
    position_size: float | None = Field(default=None, ge=0.0)
    stop_distance: Price | None = Field(default=None, ge=0.0)
    maximum_allowed_risk: float | None = Field(default=None, ge=0.0)
    timestamp: datetime = Field(default_factory=_now)


class ExecutionRequest(PointInTime):
    """A request from the strategy/risk layer toward execution."""
    request_id: str = Field(default_factory=lambda: f"req-{uuid4().hex[:16]}", max_length=64)
    timestamp: datetime
    symbol: str = Field(min_length=1, max_length=32)
    direction: Direction
    volume: Volume = Field(gt=0.0)
    order_type: Literal["MARKET", "LIMIT", "STOP"] = "MARKET"
    entry_price: Price | None = Field(default=None, ge=0.0)
    stop_loss: Price | None = Field(default=None, ge=0.0)
    take_profit: Price | None = Field(default=None, ge=0.0)
    signal_id: str | None = Field(default=None, max_length=64)
    strategy: StrategyType = StrategyType.NONE
    schema_version: int = Field(default=1, ge=1, le=99)

    _normalize_prices3 = field_validator("entry_price", "stop_loss", "take_profit", mode="before")(lambda v: _strip_nan_before(v))

    @model_validator(mode="after")
    def _direction_not_none(self) -> "ExecutionRequest":
        if self.direction is Direction.NONE:
            raise ValueError("ExecutionRequest direction must be BUY or SELL")
        return self


class ExecutionResult(BaseModel) :
    """The response from the execution layer."""
    request_id: str = Field(min_length=1, max_length=64)
    timestamp: datetime = Field(default_factory=_now)
    success: bool
    order_id: str | None = Field(default=None, max_length=64)
    position_id: str | None = Field(default=None, max_length=64)
    executed_price: Price | None = Field(default=None, ge=0.0)
    executed_volume: Volume | None = Field(default=None, ge=0.0)
    slippage: float | None = None
    error_code: str | None = None
    error_message: str | None = None

    @model_validator(mode="after")
    def _failure_carries_error(self) -> "ExecutionResult" :
        if self.success:
            return self
        if self.error_code is None:
            raise ValueError("a failed ExecutionResult must carry an error_code")
        return self


class StructureEvent(PointInTime) :
    """A market-structure event tracked through its lifecycle.

    Status transitions MUST happen incrementally in real time (CREATED ->
    ACTIVE -> PARTIALLY_FILLED -> FILLED -> INVALIDATED. A past final
    state (e.g. FILLED) must never be applied retroactively to earlier
    timestamps. Phase 1 defines the model only;no structure engine is
    implemented yet.
    """

    event_id: str = Field(default_factory=lambda: f"evt-{uuid4().hex[:16]}", max_length=64)
    event_type: StructureEventType
    symbol: str = Field(min_length=1, max_length=32)
    timestamp: datetime
    start_timestamp: datetime | None = None
    end_timestamp: datetime | None = None
    status: StructureEventStatus = StructureEventStatus.CREATED
    price_range_high: Price | None = Field(default=None, ge=0.0)
    price_range_low: Price | None = Field(default=None, ge=0.0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _guard_price_range(self) -> "StructureEvent" :
        high = self.price_range_high
        low = self.price_range_low
        if high is not None:
            if low is not None:
                if high < low:
                    raise ValueError("price_range_high must not be below price_range_low")
        return _guard_increasing_timestamp(self.model_dump())

class DecisionMessage(PointInTime):
    """Canonical decision message (D4 REQ-029; D3 §20; D1 §16).

    Carries the required documented concepts: decision_id, timestamp, symbol,
    regime, hypothesis, action, confidence, entry/reference zone, stop, target,
    risk allocation, feature_version, model_version, data_quality, reason_code,
    expiry and schema_version.

    The authoritative engineering specification (D4 §8) leaves the exact serialization
    format, field types, optionality rules and transport framing NOT SPECIFIED.
    Where a field type is not documented, it is marked REQUIRES DECISION below and
    carried with the least-committal scaffold-compatible carrier (e.g. free-form dict)
    so the contract can be frozen at Phase 0 without inventing semantics.
    """

    decision_id: str = Field(default_factory=lambda: f"dec-{uuid4().hex[:16]}", max_length=64)
    symbol: str = Field(min_length=1, max_length=32)
    regime: Regime | None = None
    hypothesis: StrategyType = StrategyType.NONE
    action: DecisionAction = DecisionAction.NO_TRADE
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    # entry_reference_zone: exact structure NOT SPECIFIED (D4 REQ-029) → free-form.
    entry_reference_zone: dict[str, Any] = Field(default_factory=dict)
    stop: Price | None = Field(default=None, ge=0.0)
    target: Price | None = Field(default=None, ge=0.0)
    # risk_allocation: exact structure NOT SPECIFIED (D4 REQ-029) → free-form.
    risk_allocation: dict[str, Any] = Field(default_factory=dict)
    # feature_version/model_version: exact types NOT SPECIFIED (D4 §8) → REQUIRES DECISION.
    feature_version: str | None = None
    model_version: str | None = None
    data_quality: DataQuality = DataQuality.MISSING
    # reason_code: documented field name (D4 REQ-029); type/optionality NOT SPECIFIED.
    reason_code: str | None = None
    expiry: datetime | None = None
    schema_version: int = Field(default=1, ge=1, le=99)

    @field_validator("stop", "target", mode="before")
    @classmethod
    def _strip_nan_prices(cls, v: Any) -> Any:
        return _strip_nan_before(v)

    @model_validator(mode="after")
    def _expiry_not_before_timestamp(self) -> "DecisionMessage":
        if self.expiry is not None:
            if self.expiry < self.timestamp:
                raise ValueError("expiry must not be earlier than timestamp")
        return self

