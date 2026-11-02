"""Proxy Activity Profile Engine (spec §17).

Builds a price-binned activity histogram and derives:
  - Proxy POC  (Point of Control – price with highest observed activity)
  - Proxy VAH  (Value Area High)
  - Proxy VAL  (Value Area Low)
  - HVN / LVN candidates (High / Low Volume Nodes)
  - Activity concentration

Value-area algorithm:
  1. Sort bins by observed_activity descending.
  2. Accumulate until cumulative activity >= value_area_pct × total activity.
  3. VAH = max price in value area; VAL = min price in value area.
"""

from __future__ import annotations
from typing import Dict, List

from algomind.orderflow_lab.schema import (
    FootprintBin, ProxyProfileSnapshot, DataQualityTag
)


class ProxyProfileEngine:
    """Compute proxy activity profile from price-level bins."""

    def __init__(self, value_area_pct: float = 0.70):
        """
        Args:
            value_area_pct: Fraction of total activity that defines the value area.
                            Default 70% per spec §17.
        """
        if not (0.0 < value_area_pct <= 1.0):
            raise ValueError(f"value_area_pct must be in (0,1], got {value_area_pct}")
        self.value_area_pct = value_area_pct

    def compute(
        self,
        bins: Dict[float, FootprintBin],
        timestamp: float,
        symbol: str,
    ) -> ProxyProfileSnapshot:
        """Compute POC, VAH, VAL, HVN, LVN, and concentration from bins.

        Returns a ProxyProfileSnapshot.
        """
        if not bins:
            return ProxyProfileSnapshot(
                timestamp=timestamp,
                symbol=symbol,
                poc_price=0.0,
                vah_price=0.0,
                val_price=0.0,
                value_area_pct=self.value_area_pct,
                quality_tag=DataQualityTag.MISSING,
            )

        total_activity = sum(b.observed_activity for b in bins.values())

        if total_activity <= 0:
            all_prices = sorted(bins.keys())
            return ProxyProfileSnapshot(
                timestamp=timestamp,
                symbol=symbol,
                poc_price=all_prices[len(all_prices) // 2] if all_prices else 0.0,
                vah_price=all_prices[-1] if all_prices else 0.0,
                val_price=all_prices[0] if all_prices else 0.0,
                value_area_pct=self.value_area_pct,
                quality_tag=DataQualityTag.MISSING,
            )

        # --- POC ---
        poc_price = max(bins, key=lambda p: bins[p].observed_activity)

        # --- Value Area ---
        sorted_by_activity = sorted(
            bins.items(), key=lambda kv: kv[1].observed_activity, reverse=True
        )
        threshold = self.value_area_pct * total_activity
        cum = 0.0
        va_prices: List[float] = []
        for price, b in sorted_by_activity:
            cum += b.observed_activity
            va_prices.append(price)
            if cum >= threshold:
                break

        vah_price = max(va_prices) if va_prices else poc_price
        val_price = min(va_prices) if va_prices else poc_price

        # --- Concentration ---
        # Fraction of total activity in the value area
        va_activity = sum(bins[p].observed_activity for p in va_prices)
        concentration = va_activity / total_activity if total_activity > 0 else 0.0

        # --- HVN / LVN ---
        mean_activity = total_activity / len(bins)
        hvn: List[float] = []
        lvn: List[float] = []
        for price, b in bins.items():
            if b.observed_activity >= 1.5 * mean_activity:
                hvn.append(price)
            elif b.observed_activity <= 0.5 * mean_activity and b.observed_activity > 0:
                lvn.append(price)

        return ProxyProfileSnapshot(
            timestamp=timestamp,
            symbol=symbol,
            poc_price=poc_price,
            vah_price=vah_price,
            val_price=val_price,
            value_area_pct=self.value_area_pct,
            activity_concentration=concentration,
            high_activity_nodes=sorted(hvn),
            low_activity_nodes=sorted(lvn),
            quality_tag=DataQualityTag.PROXY,
        )
