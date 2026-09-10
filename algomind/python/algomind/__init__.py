"""AlgoMind - hybrid retail trading research and execution system."""

from algomind.core.enums import (  # noqa: F401
    DataQuality,
    DecisionAction,
    Direction,
    NewsMode,
    OrderStatus,
    Regime,
    StrategyType,
)
from algomind.core.errors import (  # noqa: F401
    AlgoMindError,
    CommunicationError,
    ConfigurationError,
    DataError,
    ExecutionError,
    RiskError,
    SignalError,
    ValidationError,
)

__version__ = "0.1.0"
__all__ = [
    "__version__",
    "DataQuality",
    "DecisionAction",
    "Direction",
    "NewsMode",
    "OrderStatus",
    "Regime",
    "StrategyType",
    "AlgoMindError",
    "CommunicationError",
    "ConfigurationError",
    "DataError",
    "ExecutionError",
    "RiskError",
    "SignalError",
    "ValidationError",
]