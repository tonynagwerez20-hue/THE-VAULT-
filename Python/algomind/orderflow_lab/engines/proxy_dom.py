"""Proxy DOM Engine (spec §29, §30).

Builds an ALGOMIND PROXY DOM / Activity-at-Price Ladder from
FootprintBin data, optionally enriched with broker Market Book
(MQL5 MarketBookGet) if available.

The output is explicitly labelled PROXY_ACTIVITY_LADDER.
No resting-liquidity quantities are fabricated.
No claim of being a centralized institutional DOM.
"""

from __future__ import annotations
from typing import Dict, List, Optional

from algomind.orderflow_lab.schema import (
    FootprintBin, ProxyDOMRow, ProxyDOMSnapshot, DataQualityTag
)


class ProxyDOMEngine:
    """Build an activity-at-price ladder from footprint bins."""

    def __init__(self, ladder_depth: int = 20):
        """
        Args:
            ladder_depth: Number of rows above/below best price to show.
        """
        self.ladder_depth = ladder_depth

    def build_snapshot(
        self,
        bins: Dict[float, FootprintBin],
        timestamp: float,
        symbol: str,
        best_bid: float = 0.0,
        best_ask: float = 0.0,
    ) -> ProxyDOMSnapshot:
        """Build a DOM snapshot from price bins.

        Args:
            bins: Footprint bins from PriceBinEngine.
            timestamp: Bar timestamp.
            symbol: Instrument symbol.
            best_bid: Top-of-book bid (from broker if available).
            best_ask: Top-of-book ask (from broker if available).

        Returns:
            ProxyDOMSnapshot with activity ladder.
        """
        if not bins:
            return ProxyDOMSnapshot(
                timestamp=timestamp,
                symbol=symbol,
                quality_tag=DataQualityTag.MISSING,
            )

        spread = (best_ask - best_bid) if (best_bid > 0 and best_ask > 0) else 0.0

        # Sort bins by price
        sorted_prices = sorted(bins.keys())

        # If we have a best bid/ask, centre the ladder around the mid
        if best_bid > 0 and best_ask > 0:
            mid = (best_bid + best_ask) / 2.0
        else:
            # Use the price with highest activity as the centre
            mid = max(bins, key=lambda p: bins[p].observed_activity)

        # Build rows — include all bins or limit to ladder_depth around mid
        rows: List[ProxyDOMRow] = []
        for price in sorted_prices:
            b = bins[price]
            is_bid = (price <= best_bid) if best_bid > 0 else False
            is_ask = (price >= best_ask) if best_ask > 0 else False

            rows.append(ProxyDOMRow(
                price=price,
                observed_activity=b.observed_activity,
                est_buy=b.estimated_buy_activity,
                est_sell=b.estimated_sell_activity,
                est_delta=b.estimated_delta,
                tick_count=b.tick_count,
                pressure=b.pressure,
                best_bid=(price == best_bid and best_bid > 0),
                best_ask=(price == best_ask and best_ask > 0),
            ))

        # Trim to ladder_depth around mid
        if len(rows) > self.ladder_depth * 2:
            mid_idx = len(rows) // 2
            # Find the row closest to mid
            for i, r in enumerate(rows):
                if r.price >= mid:
                    mid_idx = i
                    break
            lo = max(0, mid_idx - self.ladder_depth)
            hi = min(len(rows), mid_idx + self.ladder_depth)
            rows = rows[lo:hi]

        return ProxyDOMSnapshot(
            timestamp=timestamp,
            symbol=symbol,
            best_bid=best_bid,
            best_ask=best_ask,
            spread=spread,
            dom_rows=rows,
            dom_mode="PROXY_ACTIVITY_LADDER",
            quality_tag=DataQualityTag.PROXY,
        )
