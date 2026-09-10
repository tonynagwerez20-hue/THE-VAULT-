"""Enumerations shared across the AlgoMind domain."""

from __future__ import annotations

from enum import Enum


class Direction(str, Enum):
    """Trade direction."""

    BUY = "BUY"
    SELL = "SELL"
    NONE = "NONE"


class StrategyType(str, Enum):
    """High-level strategy family."""

    CONTINUATION = "CONTINUATION"
    MEAN_REVERSION = "MEAN_REVERSION"
    NONE = "NONE"


class DecisionAction(str, Enum):
    """Decision-gate output action (D4 REQ-013; D1 §5 L6).

    Canonical vocabulary: TRADE, REDUCE, WAIT, NO_TRADE. ``NO_TRADE``
    is the fail-closed output when evidence/quality/risk does not permit a
    trade (non-negotiable principle P-07.``.
    """

    TRADE = "TRADE"
    REDUCE = "REDUCE"
    WAIT = "WAIT"
    NO_TRADE = "NO_TRADE"


class Regime(str, Enum):
    """Market regime/context classification.

    Canonical vocabulary established by the authoritative engineering
    specification (D3 §13 / D4 REQ-012): TREND_UP, TREND_DOWN,
    BALANCED, EXPANSION, EXHAUSTION, NEWS and NO_TRADE. The superseded
    scaffold words (RANGE, COMPRESSION, REVERSAL, UNKNOWN) are removed
    because no equivalence to the canonical states is established in the
    authoritative documents.

    ``NO_TRADE`` is a valid regime/output, not a system failure.


    """

    TREND_UP = "TREND_UP"
    TREND_DOWN = "TREND_DOWN"
    BALANCED = "BALANCED"
    EXPANSION = "EXPANSION"
    EXHAUSTION = "EXHAUSTION"
    NEWS = "NEWS"
    NO_TRADE = "NO_TRADE"


class DataQuality(str, Enum):
    """Fidelity of a data source.



    Distinguish true/institutional orderflow from proxies and missing data.
"""

    TRUE = "TRUE"
    PROXY = "PROXY"
    LIMITED = "LIMITED"
    MISSING = "MISSING"


class NewsMode(str, Enum):
    """How news awareness influences the pipeline."""

    NEWS_OFF = "NEWS_OFF"
    NEWS_FILTER_ONLY = "NEWS_FILTER_ONLY"
    NEWS_TRADE = "NEWS_TRADE"
    NEWS_HYBRID = "NEWS_HYBRID"


class OrderStatus(str, Enum):
    """Lifecycle of an order."""

    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIAL = "PARTIAL"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class Timeframe(str, Enum):
    """Canonical MT5-compatible timeframes."""

    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    M30 = "M30"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"
    W1 = "W1"
    MN1 = "MN1"


class SessionState(str, Enum):
    """Market session context."""

    ASIA = "ASIA"
    LONDON = "LONDON"
    NEW_YORK = "NEW_YORK"
    OVERLAP = "OVERLAP"
    OFF_HOURS = "OFF_HOURS"
    UNKNOWN = "UNKNOWN"


class StructureEventType(str, Enum):
    """Types of market-structure events.



    Phase 1 defines the contract only; engines come in later phases.
"""

    FVG = "FVG"
    BOS = "BOS"
    CHOCH = "CHOCH"
    LIQUIDITY_SWEEP = "LIQUIDITY_SWEEP"
    REACTION = "REACTION"
    NONE = "NONE"


class StructureEventStatus(str, Enum):
    """Lifecycle state of a structure event.



    Model structure as events/lifecycles (CREATED -> ACTIVE -> ... ->
    INVALIDATED) rather than retroactively-labelled final states, so real-time
    consumers never observe a future-completed state. Consumers therefore
    transition states incrementally as new bars/ticks arrive; a structure that is
    later "filled" was only ever ACTIVE (or PARTIALLY_FILLED) at that moment.
"
"""

    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    INVALIDATED = "INVALIDATED"
    CONFIRMED = "CONFIRMED"