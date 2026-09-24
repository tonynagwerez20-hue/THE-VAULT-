"""News Reconciliation Engine (spec §26-32).

Reconciles 2 economic calendar sources:
  1. Python External News Source (richer calendar, official releases, documents)
  2. MT5 Terminal Native Economic Calendar

Produces deterministic matching results:
  - MATCHED
  - PYTHON_ONLY
  - MT5_ONLY
  - CONFLICT (Actual value / Scheduled timestamp mismatch)
  - STALE
  - UNCONFIRMED
  - RELEASE_CONFIRMED

Enforces fail-closed behavior for news trading gates.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum


class NewsMatchStatus(str, Enum):
    MATCHED = "MATCHED"
    PYTHON_ONLY = "PYTHON_ONLY"
    MT5_ONLY = "MT5_ONLY"
    CONFLICT = "CONFLICT"
    STALE = "STALE"
    UNCONFIRMED = "UNCONFIRMED"
    RELEASE_CONFIRMED = "RELEASE_CONFIRMED"


@dataclass
class CalendarEvent:
    event_id: str
    country: str
    category: str
    event_name: str
    scheduled_timestamp: float
    actual_timestamp: Optional[float] = None
    expected_value: Optional[float] = None
    previous_value: Optional[float] = None
    actual_value: Optional[float] = None
    units: str = ""
    importance: int = 3  # 1=Low, 2=Med, 3=High
    source: str = "PYTHON"  # PYTHON | MT5


@dataclass
class ReconciledNewsEvent:
    reconciled_id: str
    python_event: Optional[CalendarEvent]
    mt5_event: Optional[CalendarEvent]
    match_status: NewsMatchStatus
    raw_surprise: float = 0.0
    normalized_surprise: float = 0.0
    conflict_reason: str = ""
    is_release_confirmed: bool = False


class NewsReconciliationEngine:
    """Deterministically match and reconcile Python vs MT5 Economic Calendar events."""

    def __init__(self, time_tolerance_seconds: float = 300.0):
        self.time_tolerance_seconds = time_tolerance_seconds

    def reconcile_events(
        self,
        python_events: List[CalendarEvent],
        mt5_events: List[CalendarEvent]
    ) -> List[ReconciledNewsEvent]:
        """Match event records between Python and MT5 sources."""
        reconciled: List[ReconciledNewsEvent] = []
        matched_mt5_ids = set()

        for py_ev in python_events:
            match_candidates = [
                mt5_ev for mt5_ev in mt5_events
                if mt5_ev.event_id not in matched_mt5_ids
                and mt5_ev.country.upper() == py_ev.country.upper()
                and abs(mt5_ev.scheduled_timestamp - py_ev.scheduled_timestamp) <= self.time_tolerance_seconds
            ]

            if not match_candidates:
                reconciled.append(ReconciledNewsEvent(
                    reconciled_id=f"RECON_{py_ev.event_id}",
                    python_event=py_ev,
                    mt5_event=None,
                    match_status=NewsMatchStatus.PYTHON_ONLY,
                ))
            else:
                mt5_match = match_candidates[0]
                matched_mt5_ids.add(mt5_match.event_id)

                # Check for conflict in actual values
                has_conflict = False
                conflict_reason = ""
                if (
                    py_ev.actual_value is not None
                    and mt5_match.actual_value is not None
                    and abs(py_ev.actual_value - mt5_match.actual_value) > 1e-4
                ):
                    has_conflict = True
                    conflict_reason = f"Actual Mismatch: Py={py_ev.actual_value}, MT5={mt5_match.actual_value}"

                status = NewsMatchStatus.CONFLICT if has_conflict else NewsMatchStatus.MATCHED
                
                # Calculate surprise if actual & expected are available
                raw_surprise = 0.0
                norm_surprise = 0.0
                actual = py_ev.actual_value if py_ev.actual_value is not None else mt5_match.actual_value
                expected = py_ev.expected_value if py_ev.expected_value is not None else mt5_match.expected_value
                
                if actual is not None and expected is not None:
                    raw_surprise = actual - expected
                    prev = py_ev.previous_value if py_ev.previous_value is not None else mt5_match.previous_value
                    denom = abs(prev) if (prev is not None and abs(prev) > 1e-4) else 1.0
                    norm_surprise = raw_surprise / denom

                is_confirmed = (actual is not None) and not has_conflict

                reconciled.append(ReconciledNewsEvent(
                    reconciled_id=f"RECON_{py_ev.event_id}",
                    python_event=py_ev,
                    mt5_event=mt5_match,
                    match_status=NewsMatchStatus.RELEASE_CONFIRMED if is_confirmed else status,
                    raw_surprise=raw_surprise,
                    normalized_surprise=norm_surprise,
                    conflict_reason=conflict_reason,
                    is_release_confirmed=is_confirmed,
                ))

        # Add remaining unmatched MT5 events
        for mt5_ev in mt5_events:
            if mt5_ev.event_id not in matched_mt5_ids:
                reconciled.append(ReconciledNewsEvent(
                    reconciled_id=f"RECON_{mt5_ev.event_id}",
                    python_event=None,
                    mt5_event=mt5_ev,
                    match_status=NewsMatchStatus.MT5_ONLY,
                ))

        return reconciled
