"""Project-level exception hierarchy.



Errors must remain observable: raise, log, and surface - never silently ignore.
"""

from __future__ import annotations


class AlgoMindError(Exception):
    """Base class for all AlgoMind errors."""


class ConfigurationError(AlgoMindError):
    """Invalid, missing, or unreadable configuration."""


class DataError(AlgoMindError):
    """Invalid, inconsistent, or unavailable market data."""


class ValidationError(AlgoMindError):
    """A domain object failed validation."""


class SignalError(AlgoMindError):
    """A strategy could not produce a valid signal."""


class RiskError(AlgoMindError):
    """The risk engine rejected or failed to evaluate a trade."""


class ExecutionError(AlgoMindError):
    """The execution layer could not place or manage an order."""


class CommunicationError(AlgoMindError):
    """Python <-> MQL5 communication failed."""