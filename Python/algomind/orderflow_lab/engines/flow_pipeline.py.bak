"""Flow Pipeline Orchestrator.

Wires together all engines into a single pipeline that processes
a list of OrderFlowTick objects (one bar's worth) and produces
all proxy outputs in a single pass.

This is the main entry point for both research and shadow-mode use.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from algomind.orderflow_lab.schema import (
    OrderFlowTick, FootprintBin, DataQualityTag, PressureState,
    ProxyFootprintSnapshot, ProxyVWAPSnapshot, ProxyProfileSnapshot,
    ProxyDOMSnapshot, FlowShadowLogEntry,
)
from algomind.orderflow_lab.engines.price_bin_engine import PriceBinEngine
from algomind.orderflow_lab.engines.proxy_vwap import ProxyVWAPEngine, VWAPMethod
from algomind.orderflow_lab.engines.proxy_profile import ProxyProfileEngine
from algomind.orderflow_lab.engines.proxy_footprint import ProxyFootprintEngine
from algomind.orderflow_lab.engines.event_engine import EventEngine, FlowEvent
from algomind.orderflow_lab.engines.proxy_dom import ProxyDOMEngine


@dataclass
class BarResult:
    """All outputs for a single timeframe bar."""
    timestamp: float
    symbol: str
    footprint: ProxyFootprintSnapshot
    vwap: ProxyVWAPSnapshot
    profile: ProxyProfileSnapshot
    dom: ProxyDOMSnapshot
    events: List[FlowEvent] = field(default_factory=list)

    def to_shadow_log(self, current_fusion: float = 0.0,
                      current_state: str = "NEUTRAL",
                      current_surge: bool = False,
                      current_transition: str = "NONE",
                      current_flip: str = "NONE") -> FlowShadowLogEntry:
        """Build a shadow log entry comparing current EA vs footprint."""
        import datetime
        ts_str = datetime.datetime.utcfromtimestamp(self.timestamp).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        return FlowShadowLogEntry(
            timestamp=ts_str,
            symbol=self.symbol,
            current_fusion=current_fusion,
            footprint_pressure=self.footprint.footprint_pressure,
            current_state=current_state,
            footprint_state=self.footprint.pressure_state.value,
            current_surge=current_surge,
            footprint_surge=self.footprint.is_surge,
            current_transition=current_transition,
            footprint_transition=self.footprint.transition_event,
            current_flip=current_flip,
            footprint_flip=f"{'FLIP' if self.footprint.is_flip else 'NONE'}_{self.footprint.flip_direction}",
            proxy_vwap=self.vwap.proxy_vwap,
            vwap_dev=self.vwap.vwap_deviation,
            poc=self.profile.poc_price,
            vah=self.profile.vah_price,
            val=self.profile.val_price,
            dom_mode="PROXY",
            data_quality="PROXY",
        )


class FlowPipeline:
    """Orchestrates the full flow pipeline for a single symbol/timeframe.

    Usage:
        pipeline = FlowPipeline("XAUUSD", tick_size=0.01)
        for bar_ticks in tick_stream:
            result = pipeline.process_bar(bar_ticks, timestamp, price, atr)
    """

    def __init__(
        self,
        symbol: str = "XAUUSD",
        tick_size: float = 0.01,
        vwap_method: VWAPMethod = VWAPMethod.TICK_PRICE,
        value_area_pct: float = 0.70,
        pressure_threshold: float = 0.25,
        surge_threshold: float = 0.60,
        surge_activity_multiplier: float = 1.5,
        persistence_bars: int = 2,
        dom_ladder_depth: int = 20,
    ):
        self.symbol = symbol
        self.bin_engine = PriceBinEngine(tick_size=tick_size)
        self.vwap_engine = ProxyVWAPEngine(method=vwap_method)
        self.profile_engine = ProxyProfileEngine(value_area_pct=value_area_pct)
        self.footprint_engine = ProxyFootprintEngine(
            pressure_threshold=pressure_threshold,
            surge_threshold=surge_threshold,
            surge_activity_multiplier=surge_activity_multiplier,
        )
        self.event_engine = EventEngine(persistence_bars=persistence_bars)
        self.dom_engine = ProxyDOMEngine(ladder_depth=dom_ladder_depth)

        self._bar_count: int = 0
        self._results: List[BarResult] = []

    def reset_session(self) -> None:
        """Reset VWAP accumulator and event history (call at session boundary)."""
        self.vwap_engine.reset()
        self.event_engine.reset()
        self._bar_count = 0
        self._results.clear()

    def process_bar(
        self,
        ticks: List[OrderFlowTick],
        timestamp: float,
        current_price: float,
        atr: float = 1.0,
        best_bid: float = 0.0,
        best_ask: float = 0.0,
        timeframe: str = "M5",
    ) -> BarResult:
        """Process one bar's worth of ticks through the full pipeline.

        Args:
            ticks: OrderFlowTick objects for this bar.
            timestamp: Bar open timestamp (epoch seconds).
            current_price: Current/close price for VWAP deviation.
            atr: ATR value for normalisation.
            best_bid: Broker best bid (0 if unavailable).
            best_ask: Broker best ask (0 if unavailable).
            timeframe: Timeframe string (e.g. "M5").

        Returns:
            BarResult with all proxy outputs.
        """
        # 1. Price binning
        bins = self.bin_engine.build_from_ticks(ticks)

        # 2. VWAP (cumulative across session)
        self.vwap_engine.update_from_bins(bins)
        vwap_snap = self.vwap_engine.snapshot(
            timestamp, self.symbol, current_price, atr
        )

        # 3. Activity Profile
        profile_snap = self.profile_engine.compute(bins, timestamp, self.symbol)

        # 4. Footprint (pressure, state, transition, flip, surge)
        fp_snap = self.footprint_engine.build_snapshot(
            bins, timestamp, self.symbol, timeframe
        )

        # 5. Events (persistence, divergence, absorption, exhaustion)
        events = self.event_engine.add_snapshot(fp_snap)

        # 6. DOM
        dom_snap = self.dom_engine.build_snapshot(
            bins, timestamp, self.symbol, best_bid, best_ask
        )

        result = BarResult(
            timestamp=timestamp,
            symbol=self.symbol,
            footprint=fp_snap,
            vwap=vwap_snap,
            profile=profile_snap,
            dom=dom_snap,
            events=events,
        )

        self._bar_count += 1
        self._results.append(result)

        return result

    @property
    def bar_count(self) -> int:
        return self._bar_count

    @property
    def results(self) -> List[BarResult]:
        return list(self._results)

    @property
    def latest(self) -> Optional[BarResult]:
        return self._results[-1] if self._results else None
