"""Event Engine (spec §22-28).

Consumes a sequence of ProxyFootprintSnapshot objects and emits
higher-level flow events:

  - Persistence       (spec §25)
  - Divergence        (spec §26)
  - Absorption        (spec §27)
  - Exhaustion        (spec §28)

Transition, Flip, and Surge are already produced by ProxyFootprintEngine;
this engine adds the remaining event types that require multi-bar context.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional

from algomind.orderflow_lab.schema import (
    ProxyFootprintSnapshot, PressureState, DataQualityTag
)


@dataclass
class FlowEvent:
    """A detected flow event with full provenance."""
    timestamp: float
    symbol: str
    event_type: str         # PERSISTENCE | DIVERGENCE_BULL | DIVERGENCE_BEAR
                            # | ABSORPTION_CANDIDATE | EXHAUSTION_CANDIDATE
    pressure: float
    state: PressureState
    detail: str = ""        # Human-readable description
    data_quality: str = "PROXY"
    bar_index: int = 0


class EventEngine:
    """Multi-bar event detector.

    Parameters
    ----------
    persistence_bars : int
        Number of consecutive same-state bars to qualify as persistence (spec §25).
    absorption_activity_mult : float
        Activity must exceed baseline × this factor for absorption candidate.
    absorption_max_displacement : float
        Maximum price displacement (ATR-normalised) for absorption.
    exhaustion_min_pressure : float
        Minimum |pressure| to consider exhaustion candidate.
    exhaustion_efficiency_threshold : float
        price_response below this = weakening efficiency.
    """

    def __init__(
        self,
        persistence_bars: int = 2,
        absorption_activity_mult: float = 2.0,
        absorption_max_displacement: float = 0.3,
        exhaustion_min_pressure: float = 0.40,
        exhaustion_efficiency_threshold: float = 0.10,
    ):
        self.persistence_bars = persistence_bars
        self.absorption_activity_mult = absorption_activity_mult
        self.absorption_max_displacement = absorption_max_displacement
        self.exhaustion_min_pressure = exhaustion_min_pressure
        self.exhaustion_efficiency_threshold = exhaustion_efficiency_threshold

        # Rolling history
        self._history: List[ProxyFootprintSnapshot] = []
        self._max_history: int = 50

    def reset(self) -> None:
        self._history.clear()

    def add_snapshot(self, snap: ProxyFootprintSnapshot) -> List[FlowEvent]:
        """Add a new bar snapshot and return any newly detected events."""
        self._history.append(snap)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        events: List[FlowEvent] = []
        n = len(self._history)

        # ----------------------------------------------------------
        # Persistence (spec §25)
        # ----------------------------------------------------------
        if n >= self.persistence_bars:
            recent = self._history[-self.persistence_bars:]
            states = [s.pressure_state for s in recent]
            if (
                all(s == PressureState.BULLISH for s in states)
                or all(s == PressureState.BEARISH for s in states)
            ):
                events.append(FlowEvent(
                    timestamp=snap.timestamp,
                    symbol=snap.symbol,
                    event_type="PERSISTENCE",
                    pressure=snap.footprint_pressure,
                    state=snap.pressure_state,
                    detail=f"{self.persistence_bars}-bar {snap.pressure_state.value} persistence",
                    bar_index=n - 1,
                ))

        # ----------------------------------------------------------
        # Divergence (spec §26)
        # ----------------------------------------------------------
        if n >= 3:
            prev2 = self._history[-3]
            prev1 = self._history[-2]
            curr = self._history[-1]

            # Need price info from bins
            prices_prev2 = self._get_price_range(prev2)
            prices_prev1 = self._get_price_range(prev1)
            prices_curr = self._get_price_range(curr)

            if prices_prev2 and prices_prev1 and prices_curr:
                low_prev2, high_prev2 = prices_prev2
                low_prev1, high_prev1 = prices_prev1
                low_curr, high_curr = prices_curr

                # Bullish divergence: price lower-low but pressure higher-low
                if (
                    low_curr < low_prev1
                    and curr.footprint_pressure > prev1.footprint_pressure
                ):
                    events.append(FlowEvent(
                        timestamp=snap.timestamp,
                        symbol=snap.symbol,
                        event_type="DIVERGENCE_BULL",
                        pressure=snap.footprint_pressure,
                        state=snap.pressure_state,
                        detail="Price lower-low, pressure higher-low → PROXY_DIVERGENCE",
                        bar_index=n - 1,
                    ))

                # Bearish divergence: price higher-high but pressure lower-high
                if (
                    high_curr > high_prev1
                    and curr.footprint_pressure < prev1.footprint_pressure
                ):
                    events.append(FlowEvent(
                        timestamp=snap.timestamp,
                        symbol=snap.symbol,
                        event_type="DIVERGENCE_BEAR",
                        pressure=snap.footprint_pressure,
                        state=snap.pressure_state,
                        detail="Price higher-high, pressure lower-high → PROXY_DIVERGENCE",
                        bar_index=n - 1,
                    ))

        # ----------------------------------------------------------
        # Absorption Candidate (spec §27)
        # ----------------------------------------------------------
        if n >= 2:
            curr = self._history[-1]
            prev = self._history[-2]

            # Conditions: high activity + limited price displacement + state change
            mean_activity = self._running_mean_activity()
            if mean_activity > 0:
                activity_ratio = curr.total_activity / mean_activity
                price_range = self._get_price_range(curr)
                if price_range:
                    displacement = abs(price_range[1] - price_range[0])
                    # Normalise by mean displacement
                    mean_disp = self._running_mean_displacement()
                    norm_disp = displacement / (mean_disp + 1e-12)

                    if (
                        activity_ratio >= self.absorption_activity_mult
                        and norm_disp <= self.absorption_max_displacement
                    ):
                        events.append(FlowEvent(
                            timestamp=snap.timestamp,
                            symbol=snap.symbol,
                            event_type="ABSORPTION_CANDIDATE",
                            pressure=snap.footprint_pressure,
                            state=snap.pressure_state,
                            detail=(
                                f"High activity ({activity_ratio:.1f}× baseline), "
                                f"limited displacement ({norm_disp:.2f}× mean)"
                            ),
                            bar_index=n - 1,
                        ))

        # ----------------------------------------------------------
        # Exhaustion Candidate (spec §28)
        # ----------------------------------------------------------
        if n >= 2:
            curr = self._history[-1]
            prev = self._history[-2]

            # Conditions: extreme pressure + weakening price response
            if abs(curr.footprint_pressure) >= self.exhaustion_min_pressure:
                avg_response = self._avg_price_response(curr)
                prev_response = self._avg_price_response(prev)

                if (
                    abs(avg_response) < self.exhaustion_efficiency_threshold
                    and abs(prev_response) > abs(avg_response)
                ):
                    events.append(FlowEvent(
                        timestamp=snap.timestamp,
                        symbol=snap.symbol,
                        event_type="EXHAUSTION_CANDIDATE",
                        pressure=snap.footprint_pressure,
                        state=snap.pressure_state,
                        detail=(
                            f"Extreme pressure ({curr.footprint_pressure:.3f}), "
                            f"declining efficiency ({avg_response:.4f} ← {prev_response:.4f})"
                        ),
                        bar_index=n - 1,
                    ))

        return events

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _get_price_range(snap: ProxyFootprintSnapshot) -> Optional[tuple]:
        if not snap.bins:
            return None
        prices = list(snap.bins.keys())
        return (min(prices), max(prices))

    @staticmethod
    def _avg_price_response(snap: ProxyFootprintSnapshot) -> float:
        if not snap.bins:
            return 0.0
        responses = [b.price_response for b in snap.bins.values()]
        return sum(responses) / len(responses) if responses else 0.0

    def _running_mean_activity(self) -> float:
        if not self._history:
            return 0.0
        return sum(s.total_activity for s in self._history) / len(self._history)

    def _running_mean_displacement(self) -> float:
        disps = []
        for s in self._history:
            pr = self._get_price_range(s)
            if pr:
                disps.append(abs(pr[1] - pr[0]))
        return sum(disps) / len(disps) if disps else 1.0
