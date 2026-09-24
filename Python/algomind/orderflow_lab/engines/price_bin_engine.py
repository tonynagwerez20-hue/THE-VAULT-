"""Price-Bin Engine (spec §18).

Receives a stream of OrderFlowTick objects and aggregates them into
price-level bins for a given timeframe window.

The engine is designed for incremental updates so that the same logic
can later be ported to MQL5 without full-history recalculation (spec §33).

Output: Dict[float, FootprintBin] keyed by normalised price level.
"""

from __future__ import annotations
import math
from typing import Dict, List, Optional

from algomind.orderflow_lab.schema import (
    OrderFlowTick, FootprintBin, DataQualityTag
)


def _normalise_price(price: float, tick_size: float) -> float:
    """Round price to the nearest tick-size boundary (spec §35)."""
    if tick_size <= 0:
        return price
    return round(round(price / tick_size) * tick_size, 10)


class PriceBinEngine:
    """Aggregate ticks into price-level bins.

    Parameters
    ----------
    tick_size : float
        Symbol tick size (e.g. 0.01 for XAUUSD).  Obtained at runtime from
        MQL5 SYMBOL_TRADE_TICK_SIZE; configurable here for research.
    """

    def __init__(self, tick_size: float = 0.01):
        if tick_size <= 0:
            raise ValueError(f"tick_size must be positive, got {tick_size}")
        self.tick_size = tick_size
        self._bins: Dict[float, FootprintBin] = {}

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------
    def reset(self) -> None:
        """Clear all bins (call at the start of each new timeframe window)."""
        self._bins.clear()

    def add_tick(self, tick: OrderFlowTick) -> None:
        """Incrementally update bins with a single tick."""
        price_key = _normalise_price(tick.price, self.tick_size)

        if price_key not in self._bins:
            self._bins[price_key] = FootprintBin(
                price=price_key,
                quality_tag=tick.quality_tag,
            )

        b = self._bins[price_key]
        b.tick_count += 1
        b.observed_activity += tick.volume

        if tick.direction == 1:
            b.estimated_buy_activity += tick.volume
        elif tick.direction == -1:
            b.estimated_sell_activity += tick.volume
        # direction == 0 → activity recorded but not classified

        b.estimated_delta = b.estimated_buy_activity - b.estimated_sell_activity

    def add_ticks(self, ticks: List[OrderFlowTick]) -> None:
        """Convenience: add multiple ticks at once."""
        for t in ticks:
            self.add_tick(t)

    # ------------------------------------------------------------------
    # Computed fields
    # ------------------------------------------------------------------
    def compute_price_response(self) -> None:
        """Compute price_response for each bin.

        price_response(p) = delta(p) / (activity(p) + eps)
        Measures directional efficiency at each price level.
        """
        eps = 1e-12
        for b in self._bins.values():
            b.price_response = b.estimated_delta / (b.observed_activity + eps)

    def compute_pressure(self) -> None:
        """Compute per-bin pressure: delta / (|delta| + eps).

        This is a normalised [-1, +1] measure of directional dominance
        at an individual price level.
        """
        eps = 1e-12
        for b in self._bins.values():
            b.pressure = b.estimated_delta / (abs(b.estimated_delta) + eps)

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------
    @property
    def bins(self) -> Dict[float, FootprintBin]:
        """Return current price-level bins (read-only view)."""
        return dict(self._bins)

    def get_total_activity(self) -> float:
        return sum(b.observed_activity for b in self._bins.values())

    def get_total_buy_activity(self) -> float:
        return sum(b.estimated_buy_activity for b in self._bins.values())

    def get_total_sell_activity(self) -> float:
        return sum(b.estimated_sell_activity for b in self._bins.values())

    def get_total_delta(self) -> float:
        return sum(b.estimated_delta for b in self._bins.values())

    def get_total_tick_count(self) -> int:
        return sum(b.tick_count for b in self._bins.values())

    def build_from_ticks(self, ticks: List[OrderFlowTick]) -> Dict[float, FootprintBin]:
        """One-shot: reset, ingest ticks, compute derived fields, return bins."""
        self.reset()
        self.add_ticks(ticks)
        self.compute_price_response()
        self.compute_pressure()
        return self.bins
