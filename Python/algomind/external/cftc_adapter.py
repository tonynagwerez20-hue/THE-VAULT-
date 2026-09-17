"""CFTC Commitments of Traders adapter — AUTONOMOUS.

Downloads official CFTC COT ZIP archives directly from cftc.gov.
No API key. No manual CSV preparation.

Point-in-time correctness (D5 §11.2, Math Spec §23):
  * A COT observation may only influence a decision AFTER its actual
    public release timestamp (Friday 15:30 ET).
  * Historical percentiles use only observations published <= now.
"""
from __future__ import annotations
import io
import os
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional

import pandas as pd
import requests


CFTC_BASE = "https://www.cftc.gov/files/dea/history"

# CFTC filename conventions (D5 §11.1).
REPORT_FILES = {
    "disaggregated_fut":   "f_disagg_txt_{year}.zip",
    "disaggregated_futopt":"com_disagg_txt_{year}.zip",
    "traders_in_financial_fut": "f_fin_txt_{year}.zip",
    "legacy_fut":          "fut_disagg_txt_{year}.zip",
}

_ET_STD = timedelta(hours=-5)
_ET_DST = timedelta(hours=-4)


def _is_dst(d: datetime) -> bool:
    return 3 <= d.month <= 10


def _publication_ts_from_report_date(report_date: datetime) -> datetime:
    """Friday 15:30 ET -> UTC for a given Tuesday as-of date."""
    days_ahead = (4 - report_date.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    release_date = report_date + timedelta(days=days_ahead)
    offset = _ET_DST if _is_dst(release_date) else _ET_STD
    local = datetime(release_date.year, release_date.month, release_date.day,
                     15, 30, tzinfo=timezone(offset))
    return local.astimezone(timezone.utc)


def _download_year(year: int, report_type: str) -> Optional[pd.DataFrame]:
    """Download and parse a single year's CFTC ZIP."""
    tmpl = REPORT_FILES.get(report_type)
    if not tmpl:
        return None
    fname = tmpl.format(year=year)
    url = f"{CFTC_BASE}/{fname}"
    try:
        r = requests.get(url, timeout=60)
        if r.status_code != 200:
            return None
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            names = z.namelist()
            data_name = next((n for n in names
                              if n.lower().endswith(('.txt', '.csv'))), None)
            if not data_name:
                return None
            with z.open(data_name) as f:
                df = pd.read_csv(f, encoding='latin-1', low_memory=False)
                return df
    except (requests.RequestException, zipfile.BadZipFile,
            pd.errors.ParserError):
        return None


def fetch_gold_managed_money(lookback_years: int = 3) -> list[dict]:
    """Fetch gold Disaggregated Managed Money positioning.

    Returns list of dicts: {report_date, long, short, oi}
    sorted by report_date ascending.
    """
    now = datetime.now(timezone.utc)
    end_year = now.year
    start_year = end_year - lookback_years

    rows = []
    for y in range(start_year, end_year + 1):
        df = _download_year(y, "disaggregated_fut")
        if df is None or df.empty:
            continue

        market_col = next((c for c in df.columns
                           if "Market" in c and "Exchange" in c), None)
        date_col   = next((c for c in df.columns if "Report_Date" in c), None)
        long_col   = next((c for c in df.columns
                           if "M_Money" in c and "Long" in c), None)
        short_col  = next((c for c in df.columns
                           if "M_Money" in c and "Short" in c), None)
        oi_col     = next((c for c in df.columns
                           if "Open_Interest_All" in c), None)

        if not all([market_col, date_col, long_col, short_col]):
            continue

        gold = df[df[market_col].astype(str).str.contains(
            "GOLD", case=False, na=False)]
        for _, row in gold.iterrows():
            try:
                rd = pd.to_datetime(row[date_col], format="%m/%d/%Y").to_pydatetime()
                rd = rd.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue
            rows.append({
                "report_date": rd,
                "long":  float(row.get(long_col, 0) or 0),
                "short": float(row.get(short_col, 0) or 0),
                "oi":    float(row.get(oi_col, 0) or 0) if oi_col else 0.0,
            })

    rows.sort(key=lambda r: r["report_date"])
    return rows


def percentile_rank(value: float, series: list[float]) -> float:
    if not series:
        return 50.0
    below = sum(1 for x in series if x < value)
    return 100.0 * below / len(series)


def compute_context(now: datetime, lookback_years: int = 3,
                    lookback_releases: int = 156) -> dict:
    """CFTC portion of ExternalContext as of `now` (point-in-time)."""
    rows = fetch_gold_managed_money(lookback_years=lookback_years)
    if not rows:
        return {"cftc_valid": False,
                "cftc_publication_ts": 0,
                "cftc_net_position":   0.0,
                "cftc_net_change":     0.0,
                "cftc_percentile":     50.0,
                "cftc_extreme":        False}

    for r in rows:
        r["publication_ts"] = _publication_ts_from_report_date(r["report_date"])

    eligible = [r for r in rows if r["publication_ts"] <= now]
    if not eligible:
        return {"cftc_valid": False,
                "cftc_publication_ts": 0,
                "cftc_net_position":   0.0,
                "cftc_net_change":     0.0,
                "cftc_percentile":     50.0,
                "cftc_extreme":        False}

    latest = eligible[-1]
    net = latest["long"] - latest["short"]

    history = [r["long"] - r["short"] for r in eligible[-lookback_releases:]]
    pct = percentile_rank(net, history)
    extreme = (pct <= 10.0) or (pct >= 90.0)

    prev_net = None
    if len(eligible) >= 2:
        prev_net = eligible[-2]["long"] - eligible[-2]["short"]

    net_change = net - prev_net if prev_net is not None else 0.0

    return {
        "cftc_valid":           True,
        "cftc_publication_ts":  int(latest["publication_ts"].timestamp()),
        "cftc_net_position":    net,
        "cftc_net_change":      net_change,
        "cftc_percentile":      pct,
        "cftc_extreme":         extreme,
    }
