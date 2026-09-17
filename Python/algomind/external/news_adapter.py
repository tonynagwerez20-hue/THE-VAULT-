"""News / economic-calendar adapter — AUTONOMOUS.

Fetches the ForexFactory XML calendar feed directly.
No API key required.

Per D1 §22 and Math Spec §21:
  * Scheduled time and actual release time are separate.
  * Revisions must carry their own availability timestamp (PIT).
  * Reaction window baseline: 3 M5 bars; pre-event buffer 30 min.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional
import xml.etree.ElementTree as ET

import requests


FOREXFACTORY_XML = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"

IMPACT_HIGH = "High"
IMPACT_MEDIUM = "Medium"

RELEVANT_CURRENCIES = {"USD"}
RELEVANT_KEYWORDS = {
    "cpi", "non-farm", "nonfarm", "fomc", "interest rate",
    "gdp", "unemployment", "retail sales", "pce", "ppi",
}


@dataclass
class NewsEvent:
    scheduled_ts: datetime
    actual_ts: Optional[datetime]
    event: str
    currency: str
    impact: str
    forecast: str
    actual: str


def fetch_news_events(timeout: int = 30) -> list[NewsEvent]:
    """Fetch this week's economic calendar from ForexFactory XML."""
    try:
        r = requests.get(FOREXFACTORY_XML, timeout=timeout)
        if r.status_code != 200:
            return []
        root = ET.fromstring(r.content)
    except (requests.RequestException, ET.ParseError):
        return []

    events: list[NewsEvent] = []
    for ev in root.findall(".//event"):
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
                continue

            dt_str = f"{date_str} {time_str}"
            try:
                dt = datetime.strptime(dt_str, "%m-%d-%Y %I:%M%p")
            except ValueError:
                continue

            offset = timedelta(hours=-4) if 3 <= dt.month <= 10 else timedelta(hours=-5)
            sched = dt.replace(tzinfo=timezone(offset)).astimezone(timezone.utc)

            actual_str = (ev.findtext("actual") or "").strip()
            actual_ts = None
            if actual_str:
                actual_ts = datetime.now(timezone.utc)

            events.append(NewsEvent(
                scheduled_ts=sched,
                actual_ts=actual_ts,
                event=title,
                currency=currency,
                impact=impact,
                forecast=(ev.findtext("forecast") or "").strip(),
                actual=actual_str,
            ))
        except Exception:
            continue

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
                    buffer_minutes: int = 30,
                    reaction_bars: int = 3,
                    bar_minutes: int = 5) -> dict:
    """Point-in-time news context from live ForexFactory feed."""
    events = fetch_news_events()
    buf = buffer_minutes * 60
    reaction_secs = reaction_bars * bar_minutes * 60

    for e in events:
        secs_to_event = (e.scheduled_ts - now).total_seconds()
        secs_since_event = (now - e.scheduled_ts).total_seconds()
        # Active window: [scheduled - buffer_minutes, scheduled + reaction_secs]
        if secs_to_event > buf:
            continue  # event is more than buffer_minutes away in the future
        if secs_since_event > reaction_secs:
            continue  # event is further back than the reaction window

        out = {
            "news_valid":             True,
            "news_event_ts":          int(e.scheduled_ts.timestamp()),
            "news_active_window":     True,
            "news_surprise":          0.0,
            "news_relative_surprise": 0.0,
        }
        if e.actual_ts is not None and e.actual_ts <= now:
            f = _parse_float(e.forecast)
            a = _parse_float(e.actual)
            if f is not None and a is not None:
                surprise = a - f
                rel = surprise / max(abs(f), 1e-9)
                out["news_surprise"] = surprise
                out["news_relative_surprise"] = rel
        return out

    return {"news_valid": False,
            "news_event_ts": 0,
            "news_active_window": False,
            "news_surprise": 0.0,
            "news_relative_surprise": 0.0}
