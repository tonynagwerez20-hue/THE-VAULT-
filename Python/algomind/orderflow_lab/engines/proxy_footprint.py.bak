"""Proxy Footprint Engine (spec §18, §20, §21 & Master Prompt).

Consumes FootprintBin data from PriceBinEngine and produces:
  - ProxyFootprintSnapshot (per-bar aggregate)
  - Aggregate pressure   P = Σδ / (Σ|δ| + ε)   ∈ [-1, +1]
  - Cumulative Delta     CD_t = CD_{t-1} + Δ_t
  - PressureState         BULLISH / NEUTRAL / BEARISH
  - is_surge flag
  - is_flip / flip_direction
  - transition_event

Thresholds are configurable (spec §21 baseline ±0.25, spec §24 surge ≥0.60).
"""

from __future__ import annotations
from typing import Dict, Optional, Literal
from enum import Enum

from algomind.orderflow_lab.schema import (
    FootprintBin, ProxyFootprintSnapshot, PressureState, DataQualityTag
)


class ResetScope(str, Enum):
    SESSION = "SESSION"
    ROLLING_50 = "ROLLING_50"
    EVENT = "EVENT"


class ProxyFootprintEngine:
    """Build footprint snapshots and track pressure state and cumulative delta across bars."""

    def __init__(
        self,
        pressure_threshold: float = 0.25,
        surge_threshold: float = 0.60,
        surge_activity_multiplier: float = 1.5,
        reset_scope: ResetScope = ResetScope.SESSION,
    ):
        """
        Args:
            pressure_threshold: |P| above this → BULLISH/BEARISH.
            surge_threshold: |P| above this AND activity above baseline → surge.
            surge_activity_multiplier: Activity must exceed mean × this factor for surge.
            reset_scope: Cumulative Delta reset policy.
        """
        self.pressure_threshold = pressure_threshold
        self.surge_threshold = surge_threshold
        self.surge_activity_multiplier = surge_activity_multiplier
        self.reset_scope = reset_scope

        # State tracking across bars
        self._prev_state: PressureState = PressureState.NEUTRAL
        self._prev_pressure: float = 0.0
        self._activity_baseline: float = 0.0  # EMA of total activity
        self._alpha: float = 0.1  # EMA smoothing

        # Cumulative Delta tracking
        self._cumulative_delta: float = 0.0
        self._rolling_deltas: list[float] = []

    def reset_cumulative_delta(self) -> None:
        """Explicit reset for Cumulative Delta (session boundary or news release)."""
        self._cumulative_delta = 0.0
        self._rolling_deltas.clear()

    # ------------------------------------------------------------------
    # Pressure & Cumulative Delta computation
    # ------------------------------------------------------------------
    @staticmethod
    def compute_aggregate_pressure(bins: Dict[float, FootprintBin]) -> float:
        """P = Σδ / (Σ|δ| + ε)  → [-1, +1]"""
        eps = 1e-12
        sum_delta = sum(b.estimated_delta for b in bins.values())
        sum_abs_delta = sum(abs(b.estimated_delta) for b in bins.values())
        return sum_delta / (sum_abs_delta + eps)

    @staticmethod
    def classify_state(pressure: float, threshold: float) -> PressureState:
        if pressure >= threshold:
            return PressureState.BULLISH
        elif pressure <= -threshold:
            return PressureState.BEARISH
        return PressureState.NEUTRAL

    def update_cumulative_delta(self, bar_delta: float) -> float:
        """Update and return cumulative delta based on configured reset scope."""
        if self.reset_scope == ResetScope.ROLLING_50:
            self._rolling_deltas.append(bar_delta)
            if len(self._rolling_deltas) > 50:
                self._rolling_deltas.pop(0)
            self._cumulative_delta = sum(self._rolling_deltas)
        else:
            self._cumulative_delta += bar_delta
        return self._cumulative_delta

    # ------------------------------------------------------------------
    # Surge detection (spec §24)
    # ------------------------------------------------------------------
    def _detect_surge(
        self, pressure: float, total_activity: float
    ) -> bool:
        """Surge requires both high |pressure| AND abnormal activity."""
        if abs(pressure) < self.surge_threshold:
            return False
        if self._activity_baseline <= 0:
            return False
        return total_activity >= self._activity_baseline * self.surge_activity_multiplier

    # ------------------------------------------------------------------
    # Transition / Flip (spec §22, §23)
    # ------------------------------------------------------------------
    def _detect_transition(
        self, current_state: PressureState
    ) -> str:
        """Detect any state change."""
        if current_state == self._prev_state:
            return "NONE"
        return f"{self._prev_state.value}_TO_{current_state.value}"

    def _detect_flip(
        self, current_state: PressureState
    ) -> tuple[bool, int]:
        """Flip = direct directional reversal (BULL↔BEAR)."""
        if (
            self._prev_state == PressureState.BULLISH
            and current_state == PressureState.BEARISH
        ):
            return True, -1
        if (
            self._prev_state == PressureState.BEARISH
            and current_state == PressureState.BULLISH
        ):
            return True, 1
        return False, 0

    # ------------------------------------------------------------------
    # Snapshot builder
    # ------------------------------------------------------------------
    def build_snapshot(
        self,
        bins: Dict[float, FootprintBin],
        timestamp: float,
        symbol: str,
        timeframe: str = "M5",
    ) -> ProxyFootprintSnapshot:
        """Build a complete footprint snapshot from price-level bins.

        Also updates internal state tracking for transition/flip/surge/cumulative_delta.
        """
        if not bins:
            return ProxyFootprintSnapshot(
                timestamp=timestamp,
                symbol=symbol,
                timeframe=timeframe,
                quality_tag=DataQualityTag.MISSING,
            )

        total_activity = sum(b.observed_activity for b in bins.values())
        total_buy = sum(b.estimated_buy_activity for b in bins.values())
        total_sell = sum(b.estimated_sell_activity for b in bins.values())
        total_delta = sum(b.estimated_delta for b in bins.values())

        cum_delta = self.update_cumulative_delta(total_delta)
        pressure = self.compute_aggregate_pressure(bins)
        state = self.classify_state(pressure, self.pressure_threshold)

        # Surge
        is_surge = self._detect_surge(pressure, total_activity)

        # Transition / Flip
        transition = self._detect_transition(state)
        is_flip, flip_dir = self._detect_flip(state)

        snap = ProxyFootprintSnapshot(
            timestamp=timestamp,
            symbol=symbol,
            timeframe=timeframe,
            bins=dict(bins),
            total_activity=total_activity,
            total_buy_activity=total_buy,
            total_sell_activity=total_sell,
            total_delta=total_delta,
            footprint_pressure=pressure,
            pressure_state=state,
            is_surge=is_surge,
            is_flip=is_flip,
            flip_direction=flip_dir,
            transition_event=transition,
            quality_tag=DataQualityTag.PROXY,
        )

        # Update EMA baseline and state
        if self._activity_baseline <= 0:
            self._activity_baseline = total_activity
        else:
            self._activity_baseline = (
                self._alpha * total_activity
                + (1 - self._alpha) * self._activity_baseline
            )
        self._prev_state = state
        self._prev_pressure = pressure

        return snap

    @property
    def cumulative_delta(self) -> float:
        return self._cumulative_delta

    @property
    def previous_state(self) -> PressureState:
        return self._prev_state

    @property
    def previous_pressure(self) -> float:
        return self._prev_pressure

    @property
    def activity_baseline(self) -> float:
        return self._activity_baseline
