"""News / economic-calendar adapter — AUTONOMOUS.

Fetches the ForexFactory XML calendar feed directly.
No API key required.

Per D1 §22 and Math Spec §21:
  * Scheduled time and actual release time are separate.
  * Revisions must carry their own availability timestamp (PIT).
  * Production reaction window: 15 elapsed minutes; pre-event buffer 30 min.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional
import xml.etree.ElementTree as ET

import requests
import math


FOREXFACTORY_XML = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"
DEFAULT_BUFFER_MINUTES = 30

IMPACT_HIGH = "High"
IMPACT_MEDIUM = "Medium"

RELEVANT_CURRENCIES = {"USD"}
RELEVANT_KEYWORDS = {
    "cpi", "non-farm", "nonfarm", "fomc", "interest rate",
    "gdp", "unemployment", "retail sales", "pce", "ppi",
}


def _nth_sunday(year: int, month: int, occurrence: int) -> int:
    """Return the day-of-month for an occurrence of Sunday (1-based)."""
    first = datetime(year, month, 1)
    first_sunday = 1 + ((6 - first.weekday()) % 7)
    return first_sunday + 7 * (occurrence - 1)


def _eastern_local_to_utc(local_time: datetime) -> datetime:
    """Convert a naive America/New_York wall time for current US DST rules.

    The calendar feed's event date/time is interpreted as Eastern wall time.
    Reject transition-hour times that are nonexistent or occur twice; choosing
    an offset for those values would fabricate a release instant.
    """
    if local_time.tzinfo is not None or local_time.year < 2007:
        raise ValueError("unsupported Eastern local-time input")

    spring_transition = datetime(local_time.year, 3,
                                 _nth_sunday(local_time.year, 3, 2), 2)
    fall_transition = datetime(local_time.year, 11,
                               _nth_sunday(local_time.year, 11, 1), 2)
    spring_gap_end = spring_transition + timedelta(hours=1)
    fall_ambiguous_start = fall_transition - timedelta(hours=1)
    if spring_transition <= local_time < spring_gap_end:
        raise ValueError("nonexistent Eastern local time")
    if fall_ambiguous_start <= local_time < fall_transition:
        raise ValueError("ambiguous Eastern local time")

    daylight_start = spring_gap_end
    daylight_end = fall_ambiguous_start
    utc_offset = timedelta(hours=-4 if daylight_start <= local_time < daylight_end else -5)
    return local_time.replace(tzinfo=timezone(utc_offset)).astimezone(timezone.utc)


@dataclass
class NewsEvent:
    scheduled_ts: datetime
    event: str
    currency: str
    impact: str
    forecast: str
    actual: str


def fetch_news_events(timeout: int = 30) -> Optional[list[NewsEvent]]:
    """Return events on a valid response, or None when availability is unknown."""
    try:
        r = requests.get(FOREXFACTORY_XML, timeout=timeout)
        if r.status_code != 200:
            return None
        root = ET.fromstring(r.content)
    except (requests.RequestException, ET.ParseError):
        return None

    # HTTP 200 plus parseable XML is not enough to establish calendar
    # availability: proxy/error documents can also be valid XML. Require the
    # feed's documented root before an empty event set can mean no event.
    root_name = root.tag.rsplit("}", 1)[-1].lower()
    if root_name != "weeklyevents":
        return None

    raw_events = root.findall(".//event")
    if not raw_events:
        # An empty weekly root has no positive evidence that the provider
        # delivered a complete event set. Do not infer a healthy quiet week.
        return None

    events: list[NewsEvent] = []
    for ev in raw_events:
        try:
            currency = (ev.findtext("country") or "").strip().upper()
            impact   = (ev.findtext("impact") or "").strip()
            title    = (ev.findtext("title") or "").strip()
            date_str = (ev.findtext("date") or "").strip()
            time_str = (ev.findtext("time") or "").strip()

            is_relevant = (
                currency in RELEVANT_CURRENCIES and
                impact in (IMPACT_HIGH, IMPACT_MEDIUM)
            ) or any(k in title.lower() for k in RELEVANT_KEYWORDS)

            if not is_relevant:
                continue

            if not date_str or not time_str or time_str.lower() == "all day":
                # A relevant event without a usable scheduled time makes
                # calendar coverage unknown; do not report a healthy quiet feed.
                return None

            dt_str = f"{date_str} {time_str}"
            try:
                dt = datetime.strptime(dt_str, "%m-%d-%Y %I:%M%p")
            except ValueError:
                return None

            try:
                sched = _eastern_local_to_utc(dt)
            except ValueError:
                # Calendar coverage is ambiguous at the DST transition; do
                # not guess an instant or report a healthy no-event state.
                return None

            actual_str = (ev.findtext("actual") or "").strip()

            events.append(NewsEvent(
                scheduled_ts=sched,
                event=title,
                currency=currency,
                impact=impact,
                forecast=(ev.findtext("forecast") or "").strip(),
                actual=actual_str,
            ))
        except Exception:
            # Unknown parsing failures make coverage incomplete, not quiet.
            return None

    events.sort(key=lambda e: e.scheduled_ts)
    return events


def _parse_float(s: str) -> Optional[float]:
    """Parse a release value like '2.9', '180K', '1.5M', '3.1%'."""
    if not s:
        return None
    s = s.strip().replace(",", "")
    mult = 1.0
    if s.endswith("%"):
        s = s[:-1]
    if s.endswith("K"):
        s = s[:-1]; mult = 1e3
    elif s.endswith("M"):
        s = s[:-1]; mult = 1e6
    elif s.endswith("B"):
        s = s[:-1]; mult = 1e9
    try:
        return float(s) * mult
    except ValueError:
        return None


def compute_context(now: datetime,
                    buffer_minutes: int = DEFAULT_BUFFER_MINUTES,
                    reaction_bars: int = 3,
                    bar_minutes: int = 5,
                    fetch_completed_at: Optional[datetime] = None,
                    reaction_minutes: Optional[int] = None) -> dict:
    """Point-in-time news context from live ForexFactory feed."""
    events = fetch_news_events()
    if events is None:
        return {"news_valid": False,
                "news_event_ts": 0,
                "news_active_window": False,
                "news_released": False,
                "news_surprise": 0.0,
                "news_relative_surprise": 0.0,
                "news_observed_ts": 0}
    # `now` is supplied by the polling loop before a synchronous provider
    # request. Use the post-fetch observation time for point-in-time decisions
    # so an event/value arriving during the request cannot be backdated.
    observed_at = fetch_completed_at or datetime.now(timezone.utc)
    if (now.tzinfo is None or observed_at.tzinfo is None or
            observed_at.astimezone(timezone.utc) < now.astimezone(timezone.utc)):
        return {"news_valid": False,
                "news_event_ts": 0,
                "news_active_window": False,
                "news_released": False,
                "news_surprise": 0.0,
                "news_relative_surprise": 0.0,
                "news_observed_ts": 0}
    as_of = observed_at.astimezone(timezone.utc)
    observed_ts = int(as_of.timestamp())
    buf = buffer_minutes * 60
    reaction_secs = (reaction_minutes if reaction_minutes is not None
                     else reaction_bars * bar_minutes) * 60

    def release_confirmed(e):
        f, a = _parse_float(e.forecast), _parse_float(e.actual)
        return (e.scheduled_ts <= as_of and f is not None and a is not None
                and math.isfinite(f) and math.isfinite(a))

    # Deterministic overlap policy: an upcoming/unconfirmed event wins over
    # a released catalyst; otherwise select the most recent release.
    events = sorted(events, key=lambda e: (release_confirmed(e), -e.scheduled_ts.timestamp()))
    for e in events:
        secs_to_event = (e.scheduled_ts - as_of).total_seconds()
        secs_since_event = (as_of - e.scheduled_ts).total_seconds()
        # Active window: [scheduled - buffer_minutes, scheduled + reaction_secs]
        if secs_to_event > buf:
            continue  # event is more than buffer_minutes away in the future
        # Retain a confirmed catalyst for horizon-specific admission up to4h.
        # The FILTER blackout remains reaction_secs, independent of retention.
        retention_secs = 14400 if release_confirmed(e) else reaction_secs
        if secs_since_event > retention_secs:
            continue

        out = {
            "news_valid":             True,
            "news_event_ts":          int(e.scheduled_ts.timestamp()),
            "news_active_window":     secs_since_event <= reaction_secs,
            "news_released":          False,
            "news_surprise":          0.0,
            "news_relative_surprise": 0.0,
            "news_observed_ts":       observed_ts,
        }
        # A populated numeric actual is provider evidence that the value has
        # been released and observed in this fetched snapshot. Do not compare
        # a fetch-time timestamp with the caller's pre-fetch `now`: that made
        # actual_ts later than now on every normal request and suppressed all
        # surprises. A future scheduled event is never treated as released.
        if e.scheduled_ts <= as_of:
            f = _parse_float(e.forecast)
            a = _parse_float(e.actual)
            if f is not None and a is not None and math.isfinite(f) and math.isfinite(a):
                surprise = a - f
                rel = surprise / max(abs(f), 1e-9)
                if not math.isfinite(surprise) or not math.isfinite(rel):
                    return {"news_valid": False, "news_observed_ts": 0}
                out["news_released"] = True
                out["news_surprise"] = surprise
                out["news_relative_surprise"] = rel
        return out

    # An empty event set is a healthy no-event observation only when the feed
    # itself was fetched and parsed successfully (events is not None above).
    return {"news_valid": True,
            "news_event_ts": 0,
            "news_active_window": False,
            "news_released": False,
            "news_surprise": 0.0,
            "news_relative_surprise": 0.0,
            "news_observed_ts": observed_ts}
