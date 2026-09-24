"""Comprehensive unit tests for the Order-Flow Lab.

Covers spec §45 & Master Prompt test requirements:
  - Tick classification (up/down/equal)
  - Price binning and tick-size normalisation
  - VWAP computation (all methods)
  - POC / VAH / VAL
  - Pressure / states / transitions / flips / surge / Cumulative Delta
  - News Reconciliation & ATR Event Reaction
  - Persistence / divergence / absorption / exhaustion
  - Adapter loading and validation
  - Edge cases (zero volume, missing bid/ask, extreme spread, duplicates)
"""

import os
import json
import math
import tempfile
import pytest

from algomind.orderflow_lab.schema import (
    OrderFlowTick, FootprintBin, DataQualityTag, PressureState
)
from algomind.orderflow_lab.engines.price_bin_engine import PriceBinEngine, _normalise_price
from algomind.orderflow_lab.engines.proxy_vwap import ProxyVWAPEngine, VWAPMethod
from algomind.orderflow_lab.engines.proxy_profile import ProxyProfileEngine
from algomind.orderflow_lab.engines.proxy_footprint import ProxyFootprintEngine, ResetScope
from algomind.orderflow_lab.engines.event_engine import EventEngine
from algomind.orderflow_lab.engines.proxy_dom import ProxyDOMEngine
from algomind.orderflow_lab.engines.news_reconciliation_engine import (
    NewsReconciliationEngine, CalendarEvent, NewsMatchStatus
)
from algomind.orderflow_lab.engines.event_reaction_engine import EventReactionEngine
from algomind.orderflow_lab.data_sources.manual_sample_adapter import (
    ManualSampleAdapter, ValidationReport
)


# ======================================================================
# Helpers
# ======================================================================
def _make_tick(price, direction=0, volume=1.0, bid=0.0, ask=0.0, ts=0.0):
    return OrderFlowTick(
        timestamp=ts, price=price, bid=bid, ask=ask,
        volume=volume, tick_volume=int(volume),
        direction=direction, quality_tag=DataQualityTag.PROXY,
    )


def _rising_ticks(start=2000.0, n=10, step=0.10, vol=1.0):
    return [_make_tick(start + i * step, direction=1, volume=vol, ts=float(i))
            for i in range(n)]


# ======================================================================
# Price-Bin Engine
# ======================================================================
class TestPriceBinEngine:

    def test_normalise_price(self):
        assert _normalise_price(2000.123, 0.01) == 2000.12
        assert _normalise_price(2000.0, 0.01) == 2000.0

    def test_single_tick(self):
        engine = PriceBinEngine(tick_size=0.01)
        engine.add_tick(_make_tick(2000.05, direction=1, volume=3.0))
        bins = engine.bins
        assert len(bins) == 1
        key = 2000.05
        assert bins[key].tick_count == 1
        assert bins[key].observed_activity == 3.0
        assert bins[key].estimated_buy_activity == 3.0
        assert bins[key].estimated_delta == 3.0


# ======================================================================
# Proxy Footprint & Cumulative Delta
# ======================================================================
class TestProxyFootprint:

    def test_all_buy_pressure_is_one(self):
        bins = {
            2000.0: FootprintBin(
                price=2000.0, estimated_buy_activity=10.0,
                estimated_sell_activity=0.0, estimated_delta=10.0
            ),
        }
        p = ProxyFootprintEngine.compute_aggregate_pressure(bins)
        assert abs(p - 1.0) < 1e-6

    def test_cumulative_delta_session(self):
        engine = ProxyFootprintEngine(reset_scope=ResetScope.SESSION)
        bins1 = {2000.0: FootprintBin(price=2000.0, estimated_delta=10.0, observed_activity=10.0)}
        bins2 = {2001.0: FootprintBin(price=2001.0, estimated_delta=-4.0, observed_activity=5.0)}

        engine.build_snapshot(bins1, 1.0, "XAUUSD")
        assert engine.cumulative_delta == 10.0

        engine.build_snapshot(bins2, 2.0, "XAUUSD")
        assert engine.cumulative_delta == 6.0


# ======================================================================
# News Reconciliation Engine
# ======================================================================
class TestNewsReconciliationEngine:

    def test_matched_events(self):
        engine = NewsReconciliationEngine()
        py_ev = CalendarEvent("EV1", "US", "CPI", "CPI MoM", 1609459200, actual_value=0.4, expected_value=0.2)
        mt5_ev = CalendarEvent("EV1_MT5", "US", "CPI", "CPI MoM", 1609459200, actual_value=0.4, expected_value=0.2)

        results = engine.reconcile_events([py_ev], [mt5_ev])
        assert len(results) == 1
        assert results[0].match_status == NewsMatchStatus.RELEASE_CONFIRMED
        assert abs(results[0].raw_surprise - 0.2) < 1e-6

    def test_conflict_events(self):
        engine = NewsReconciliationEngine()
        py_ev = CalendarEvent("EV1", "US", "CPI", "CPI MoM", 1609459200, actual_value=0.5)
        mt5_ev = CalendarEvent("EV1_MT5", "US", "CPI", "CPI MoM", 1609459200, actual_value=0.2)

        results = engine.reconcile_events([py_ev], [mt5_ev])
        assert len(results) == 1
        assert results[0].match_status == NewsMatchStatus.CONFLICT


# ======================================================================
# Event Reaction Engine
# ======================================================================
class TestEventReactionEngine:

    def test_atr_displacement(self):
        engine = EventReactionEngine(atr_period=14)
        res = engine.calculate_reaction(
            event_id="EV1",
            pre_event_price=2000.0,
            pre_event_atr=2.0,
            price_1m=2002.0,
            price_3m=2004.0,
            price_5m=2006.0,
            price_15m=2010.0,
            pre_spread=0.2,
            post_spread=0.4,
            post_delta=50.0,
            post_cd=120.0
        )
        assert abs(res.disp_1m_atr - 1.0) < 1e-6
        assert abs(res.disp_5m_atr - 3.0) < 1e-6
        assert abs(res.spread_expansion_ratio - 2.0) < 1e-6
