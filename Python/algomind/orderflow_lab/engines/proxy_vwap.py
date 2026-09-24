"""Proxy VWAP Engine (spec §16).

Implements three weighting alternatives:
  1. TICK_PRICE   — tick-level price × activity weighting (default)
  2. TYPICAL      — (H+L+C)/3 weighting (for OHLC bars)
  3. OHLC4        — (O+H+L+C)/4 weighting

All labelled PROXY.  Never disguised as transaction VWAP.

Calculates:
  VWAP_dev = (Price − ProxyVWAP) / (ATR + ε)
"""

from __future__ import annotations
from typing import Dict, List, Optional
from enum import Enum

from algomind.orderflow_lab.schema import (
    FootprintBin, ProxyVWAPSnapshot, DataQualityTag
)


class VWAPMethod(str, Enum):
    TICK_PRICE = "TICK_PRICE"
    TYPICAL = "TYPICAL"
    OHLC4 = "OHLC4"


class ProxyVWAPEngine:
    """Compute proxy VWAP from price-level bins or OHLC data."""

    def __init__(self, method: VWAPMethod = VWAPMethod.TICK_PRICE):
        self.method = method
        # Running accumulators for incremental (session-level) VWAP
        self._cum_weighted_price: float = 0.0
        self._cum_activity: float = 0.0

    def reset(self) -> None:
        """Reset accumulators (call at session boundary)."""
        self._cum_weighted_price = 0.0
        self._cum_activity = 0.0

    # ------------------------------------------------------------------
    # Tick-price method: from FootprintBin dict
    # ------------------------------------------------------------------
    def update_from_bins(self, bins: Dict[float, FootprintBin]) -> float:
        """Add a bar's worth of bins to the running VWAP.

        Returns current proxy VWAP.
        """
        for price, b in bins.items():
            self._cum_weighted_price += price * b.observed_activity
            self._cum_activity += b.observed_activity
        return self.current_vwap

    # ------------------------------------------------------------------
    # OHLC-based methods (for reference OHLCV data)
    # ------------------------------------------------------------------
    def update_from_ohlc(
        self,
        open_: float,
        high: float,
        low: float,
        close: float,
        volume: float,
    ) -> float:
        """Add a single OHLC bar to the running VWAP.

        Uses method-specific typical price.
        Returns current proxy VWAP.
        """
        if self.method == VWAPMethod.TYPICAL:
            tp = (high + low + close) / 3.0
        elif self.method == VWAPMethod.OHLC4:
            tp = (open_ + high + low + close) / 4.0
        else:
            # Default TICK_PRICE on OHLC falls back to typical
            tp = (high + low + close) / 3.0

        self._cum_weighted_price += tp * volume
        self._cum_activity += volume
        return self.current_vwap

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------
    @property
    def current_vwap(self) -> float:
        if self._cum_activity <= 0:
            return 0.0
        return self._cum_weighted_price / self._cum_activity

    def compute_deviation(self, current_price: float, atr: float) -> float:
        """VWAP_dev = (Price − ProxyVWAP) / (ATR + ε)"""
        eps = 1e-12
        return (current_price - self.current_vwap) / (atr + eps)

    def snapshot(
        self,
        timestamp: float,
        symbol: str,
        current_price: float,
        atr: float = 1.0,
    ) -> ProxyVWAPSnapshot:
        """Build an immutable snapshot of current VWAP state."""
        return ProxyVWAPSnapshot(
            timestamp=timestamp,
            symbol=symbol,
            proxy_vwap=self.current_vwap,
            typical_price=current_price,
            vwap_deviation=self.compute_deviation(current_price, atr),
            cum_weighted_price=self._cum_weighted_price,
            cum_activity=self._cum_activity,
            quality_tag=DataQualityTag.PROXY,
        )
