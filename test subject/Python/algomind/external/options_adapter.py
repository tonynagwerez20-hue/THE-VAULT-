"""GLD research fetch helpers. Production compute_context is unavailable.

No validated ETF mapping or dealer-side inventory is provided by this adapter.

The governing documents (D5 §12, D3 §24) require:
  * Options are CONTEXT ONLY. Never a trigger.
  * Score influence capped at ±0.10.
  * Missing data => explicit ABSENT, never fabricated.
  * Every row carries a source timestamp.

Source priority:
  1. CBOE delayed quotes (no API key, official exchange feed).
     URL: https://cdn.cboe.com/api/global/delayed_quotes/options/{SYMBOL}.json
     Provides: strike, OI, IV, delta, gamma. Delay ~15-20 minutes.

  2. yfinance fallback. Provides strike, OI, IV — NO GREEKS.
     When used, gamma_regime is set to 0 (neutral).

Both sources cover GLD (US-listed ETF options), the proxy for COMEX
gold options positioning. This is NOT XAUUSD or COMEX options.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
import json
import re
import requests


CBOE_BASE = "https://cdn.cboe.com/api/global/delayed_quotes/options"

SOURCE_CBOE = "PROXY_GLD_CBOE"
SOURCE_YF   = "PROXY_GLD_YF"
SOURCE_NONE = "NONE"


@dataclass
class OptionsRow:
    expiry: datetime
    strike: float
    oi: float
    iv: float
    delta: float
    gamma: float


# ------------------------------------------------------------------
# CBOE source
# ------------------------------------------------------------------

_OCC_RE = re.compile(r"^([A-Z]{1,6})(\d{6})([CP])(\d{8})$")


def _parse_occ(occ: str) -> Optional[tuple[datetime, float, str]]:
    """Parse OCC symbol into (expiry, strike, 'C'/'P')."""
    m = _OCC_RE.match(occ)
    if not m:
        return None
    try:
        exp = datetime.strptime(m.group(2), "%y%m%d").replace(tzinfo=timezone.utc)
        strike = int(m.group(4)) / 1000.0
        return exp, strike, m.group(3)
    except (ValueError, TypeError):
        return None


def fetch_gld_cboe(symbol: str = "GLD", timeout: int = 30) -> list[OptionsRow]:
    """Fetch GLD options chain from CBOE delayed quotes API."""
    url = f"{CBOE_BASE}/{symbol}.json"
    try:
        r = requests.get(url, timeout=timeout, headers={
            "User-Agent": "Amigo/1.0 (research)"
        })
        if r.status_code != 200:
            return []
        payload = r.json()
    except (requests.RequestException, json.JSONDecodeError):
        return []

    data = payload.get("data", {})
    raw_options = data.get("options", [])
    if not isinstance(raw_options, list):
        return []

    rows: list[OptionsRow] = []
    for opt in raw_options:
        occ = opt.get("option") or opt.get("contract") or ""
        parsed = _parse_occ(occ)
        if parsed is None:
            continue
        exp, strike, _cp = parsed

        try:
            oi = float(opt.get("open_interest", 0) or 0)
            iv = float(opt.get("iv", 0) or 0)
            greeks = opt.get("greeks") or {}
            delta = float(greeks.get("delta", opt.get("delta", 0)) or 0)
            gamma = float(greeks.get("gamma", opt.get("gamma", 0)) or 0)
        except (ValueError, TypeError):
            continue

        rows.append(OptionsRow(
            expiry=exp, strike=strike, oi=oi, iv=iv,
            delta=delta, gamma=gamma,
        ))

    return rows


# ------------------------------------------------------------------
# yfinance fallback (no Greeks)
# ------------------------------------------------------------------

def fetch_gld_yfinance(symbol: str = "GLD",
                       max_expirations: int = 2) -> list[OptionsRow]:
    """Fetch GLD options chain from yfinance.

    yfinance does NOT provide Greeks. gamma and delta are set to 0.
    Caller sets gamma_regime=0 when this source is used.
    """
    try:
        import yfinance as yf
    except ImportError:
        return []

    try:
        tk = yf.Ticker(symbol)
        expirations = tk.options
    except Exception:
        return []

    if not expirations:
        return []

    now = datetime.now(timezone.utc)
    rows: list[OptionsRow] = []

    for exp_str in expirations[:max_expirations]:
        try:
            exp_dt = datetime.strptime(exp_str, "%Y-%m-%d").replace(
                tzinfo=timezone.utc)
        except ValueError:
            continue
        if exp_dt.date() < now.date():
            continue

        try:
            chain = tk.option_chain(exp_str)
        except Exception:
            continue

        for df in (chain.calls, chain.puts):
            for _, row in df.iterrows():
                try:
                    strike = float(row.get("strike", 0) or 0)
                    oi = float(row.get("openInterest", 0) or 0)
                    iv = float(row.get("impliedVolatility", 0) or 0)
                except (ValueError, TypeError):
                    continue
                rows.append(OptionsRow(
                    expiry=exp_dt, strike=strike, oi=oi, iv=iv,
                    delta=0.0, gamma=0.0,
                ))

    return rows


# ------------------------------------------------------------------
# Unified fetch with source fallback
# ------------------------------------------------------------------

def fetch_gld_chain(symbol: str = "GLD") -> tuple[list[OptionsRow], str]:
    """Fetch GLD chain from CBOE, fall back to yfinance."""
    rows = fetch_gld_cboe(symbol)
    if rows:
        return rows, SOURCE_CBOE

    rows = fetch_gld_yfinance(symbol)
    if rows:
        return rows, SOURCE_YF

    return [], SOURCE_NONE


# ------------------------------------------------------------------
# Context computation
# ------------------------------------------------------------------

def compute_context(spot: float, atr: float,
                    gc_price: Optional[float],
                    now: datetime) -> dict:
    """Unavailable until a validated ETF mapping and positioning contract exists.

    GC minus spot is not a GLD strike conversion. Unsigned gamma times OI
    cannot identify dealer inventory. Raw fetch helpers remain research-only.
    """
    return {"options_valid": False, "options_source": SOURCE_NONE,
            "options_obs_ts": 0, "options_gamma_regime": 0}
