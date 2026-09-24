"""Validation Framework (spec §37-40).

Compares proxy flow outputs against reference data using:
  - Sign agreement
  - Correlation / rank correlation
  - Event timing / precision / recall / F1
  - Session-level breakdown (Asia/London/NY)
  - Regime-level breakdown
  - No overall 'winner' score (spec §37)
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum


class TradingSession(str, Enum):
    ASIA = "ASIA"               # 00:00–08:00 UTC
    LONDON = "LONDON"           # 08:00–13:00 UTC
    NEW_YORK = "NEW_YORK"       # 13:00–17:00 UTC
    OVERLAP = "LONDON_NY_OVERLAP"  # 13:00–17:00 UTC (subset)
    OFF_HOURS = "OFF_HOURS"


def classify_session(hour_utc: int) -> TradingSession:
    """Classify a UTC hour into a trading session."""
    if 0 <= hour_utc < 8:
        return TradingSession.ASIA
    elif 8 <= hour_utc < 13:
        return TradingSession.LONDON
    elif 13 <= hour_utc < 17:
        return TradingSession.OVERLAP
    elif 17 <= hour_utc < 22:
        return TradingSession.NEW_YORK
    else:
        return TradingSession.OFF_HOURS


# ======================================================================
# Continuous metrics
# ======================================================================
@dataclass
class ContinuousMetrics:
    """Metrics for comparing two continuous series (e.g. pressure)."""
    n: int = 0
    sign_agreement: float = 0.0
    pearson_r: float = 0.0
    spearman_rho: float = 0.0
    mean_abs_error: float = 0.0
    rmse: float = 0.0

    def summary(self) -> str:
        return (
            f"  n={self.n}  sign_agree={self.sign_agreement:.3f}  "
            f"pearson_r={self.pearson_r:.3f}  spearman_rho={self.spearman_rho:.3f}  "
            f"MAE={self.mean_abs_error:.4f}  RMSE={self.rmse:.4f}"
        )


def _sign(x: float) -> int:
    if x > 0: return 1
    if x < 0: return -1
    return 0


def _pearson(xs: List[float], ys: List[float]) -> float:
    n = len(xs)
    if n < 3:
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    denom = math.sqrt(sxx * syy)
    return sxy / denom if denom > 0 else 0.0


def _rank(values: List[float]) -> List[float]:
    indexed = sorted(enumerate(values), key=lambda t: t[1])
    ranks = [0.0] * len(values)
    for rank, (idx, _) in enumerate(indexed, 1):
        ranks[idx] = float(rank)
    return ranks


def _spearman(xs: List[float], ys: List[float]) -> float:
    return _pearson(_rank(xs), _rank(ys))


def compute_continuous_metrics(
    proxy: List[float], reference: List[float]
) -> ContinuousMetrics:
    """Compare two aligned continuous series."""
    n = min(len(proxy), len(reference))
    if n == 0:
        return ContinuousMetrics()

    px = proxy[:n]
    rx = reference[:n]

    sign_agree = sum(1 for p, r in zip(px, rx) if _sign(p) == _sign(r)) / n
    mae = sum(abs(p - r) for p, r in zip(px, rx)) / n
    rmse = math.sqrt(sum((p - r) ** 2 for p, r in zip(px, rx)) / n)
    pr = _pearson(px, rx)
    sr = _spearman(px, rx)

    return ContinuousMetrics(
        n=n,
        sign_agreement=sign_agree,
        pearson_r=pr,
        spearman_rho=sr,
        mean_abs_error=mae,
        rmse=rmse,
    )


# ======================================================================
# Event metrics (spec §38)
# ======================================================================
@dataclass
class EventMatch:
    """A single event comparison record."""
    event_type: str
    proxy_timestamp: float
    reference_timestamp: float
    timing_difference: float
    proxy_direction: int
    reference_direction: int
    agreement: bool
    false_positive: bool
    false_negative: bool
    data_quality: str = "PROXY"


@dataclass
class EventMetrics:
    """Aggregate event-level metrics."""
    event_type: str
    proxy_count: int = 0
    reference_count: int = 0
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    mean_timing_error: float = 0.0

    @property
    def precision(self) -> float:
        d = self.true_positives + self.false_positives
        return self.true_positives / d if d > 0 else 0.0

    @property
    def recall(self) -> float:
        d = self.true_positives + self.false_negatives
        return self.true_positives / d if d > 0 else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0

    def summary(self) -> str:
        return (
            f"  {self.event_type}: proxy={self.proxy_count} ref={self.reference_count} "
            f"TP={self.true_positives} FP={self.false_positives} FN={self.false_negatives} "
            f"P={self.precision:.3f} R={self.recall:.3f} F1={self.f1:.3f} "
            f"timing_err={self.mean_timing_error:.1f}s"
        )


def compute_event_metrics(
    proxy_events: List[Tuple[float, int]],   # (timestamp, direction)
    ref_events: List[Tuple[float, int]],      # (timestamp, direction)
    event_type: str,
    max_timing_window: float = 300.0,         # 5 minutes default
) -> EventMetrics:
    """Match proxy events to reference events within a timing window.

    Args:
        proxy_events: List of (timestamp, direction) for proxy detections.
        ref_events: List of (timestamp, direction) for reference detections.
        event_type: Event type label.
        max_timing_window: Maximum seconds between proxy and reference to count as match.
    """
    metrics = EventMetrics(
        event_type=event_type,
        proxy_count=len(proxy_events),
        reference_count=len(ref_events),
    )

    matched_ref = set()
    timing_errors: List[float] = []

    for p_ts, p_dir in proxy_events:
        best_match = None
        best_diff = float("inf")
        for i, (r_ts, r_dir) in enumerate(ref_events):
            if i in matched_ref:
                continue
            diff = abs(p_ts - r_ts)
            if diff <= max_timing_window and diff < best_diff:
                best_match = i
                best_diff = diff

        if best_match is not None:
            metrics.true_positives += 1
            matched_ref.add(best_match)
            timing_errors.append(best_diff)
        else:
            metrics.false_positives += 1

    metrics.false_negatives = len(ref_events) - len(matched_ref)
    metrics.mean_timing_error = (
        sum(timing_errors) / len(timing_errors) if timing_errors else 0.0
    )

    return metrics


# ======================================================================
# Session / Regime breakdown (spec §39, §40)
# ======================================================================
@dataclass
class SessionBreakdown:
    """Metrics broken down by trading session."""
    session: TradingSession
    bar_count: int = 0
    continuous: Optional[ContinuousMetrics] = None
    events: Dict[str, EventMetrics] = field(default_factory=dict)


@dataclass
class RegimeBreakdown:
    """Metrics broken down by AlgoMind regime."""
    regime: str
    bar_count: int = 0
    continuous: Optional[ContinuousMetrics] = None
    events: Dict[str, EventMetrics] = field(default_factory=dict)


# ======================================================================
# Parity test (spec §46)
# ======================================================================
@dataclass
class ParityResult:
    """Single field parity comparison between Python and MQL5."""
    field_name: str
    timestamp: float
    python_value: float
    mql5_value: float
    tolerance: float
    passed: bool

    @property
    def absolute_difference(self) -> float:
        return abs(self.python_value - self.mql5_value)

    def to_dict(self) -> dict:
        return {
            "field": self.field_name,
            "timestamp": self.timestamp,
            "python": self.python_value,
            "mql5": self.mql5_value,
            "abs_diff": self.absolute_difference,
            "tolerance": self.tolerance,
            "passed": self.passed,
        }


def check_parity(
    field_name: str,
    timestamp: float,
    python_value: float,
    mql5_value: float,
    tolerance: float = 1e-6,
) -> ParityResult:
    """Compare a single Python value against its MQL5 counterpart."""
    passed = abs(python_value - mql5_value) <= tolerance
    return ParityResult(
        field_name=field_name,
        timestamp=timestamp,
        python_value=python_value,
        mql5_value=mql5_value,
        tolerance=tolerance,
        passed=passed,
    )


@dataclass
class ParityReport:
    """Aggregate parity comparison for a batch of fields."""
    results: List[ParityResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return self.total - self.passed

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total > 0 else 0.0

    def failures(self) -> List[ParityResult]:
        return [r for r in self.results if not r.passed]

    def summary(self) -> str:
        lines = [
            f"Parity Report: {self.passed}/{self.total} passed ({self.pass_rate:.1%})",
        ]
        if self.failed > 0:
            lines.append(f"  Failures ({self.failed}):")
            for f in self.failures()[:20]:
                lines.append(
                    f"    {f.field_name} @ {f.timestamp}: "
                    f"py={f.python_value:.8f} mql5={f.mql5_value:.8f} "
                    f"diff={f.absolute_difference:.2e} tol={f.tolerance:.2e}"
                )
        return "\n".join(lines)
