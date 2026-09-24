"""Event Reaction Engine (spec §33-36).

Measures market reaction to news releases using pre-event ATR baselines and
post-release ATR-normalized displacement tracking.

Calculates:
  - Pre-event baseline ATR
  - 1m, 3m, 5m, 15m ATR-normalized price displacement
  - Post-event spread expansion
  - Footprint activity & delta reaction
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class EventReactionResult:
    event_id: str
    pre_event_price: float
    pre_event_atr: float
    disp_1m_atr: float
    disp_3m_atr: float
    disp_5m_atr: float
    disp_15m_atr: float
    spread_expansion_ratio: float
    footprint_delta_reaction: float
    cumulative_delta_reaction: float
    is_valid_reaction: bool


class EventReactionEngine:
    """Calculates pre-event ATR baselines and post-release ATR-normalized market response."""

    def __init__(self, atr_period: int = 14):
        self.atr_period = atr_period

    def calculate_reaction(
        self,
        event_id: str,
        pre_event_price: float,
        pre_event_atr: float,
        price_1m: float,
        price_3m: float,
        price_5m: float,
        price_15m: float,
        pre_spread: float,
        post_spread: float,
        post_delta: float = 0.0,
        post_cd: float = 0.0,
    ) -> EventReactionResult:
        """Calculate normalized price displacement and activity metrics."""
        eps = 1e-12
        atr_denom = pre_event_atr if pre_event_atr > 0.0 else 1.0

        disp_1m = abs(price_1m - pre_event_price) / (atr_denom + eps)
        disp_3m = abs(price_3m - pre_event_price) / (atr_denom + eps)
        disp_5m = abs(price_5m - pre_event_price) / (atr_denom + eps)
        disp_15m = abs(price_15m - pre_event_price) / (atr_denom + eps)

        spread_ratio = (post_spread / pre_spread) if (pre_spread > 0.0) else 1.0

        return EventReactionResult(
            event_id=event_id,
            pre_event_price=pre_event_price,
            pre_event_atr=pre_event_atr,
            disp_1m_atr=disp_1m,
            disp_3m_atr=disp_3m,
            disp_5m_atr=disp_5m,
            disp_15m_atr=disp_15m,
            spread_expansion_ratio=spread_ratio,
            footprint_delta_reaction=post_delta,
            cumulative_delta_reaction=post_cd,
            is_valid_reaction=(pre_event_price > 0.0 and pre_event_atr > 0.0),
        )
