"""Amigo external-information service — AUTONOMOUS.

Fetches CFTC COT (official cftc.gov ZIPs), ForexFactory news (XML),
with unsupported GLD scoring disabled. CFTC release provenance must be verified.

Never issues executable orders. Never bypasses MQL5 hard risk.
Fail closed: on any error, write a context marked unavailable.
"""
from __future__ import annotations
import argparse
import math
import time
from datetime import datetime, timezone

from algomind.schema import ExternalContext, DataQuality
from algomind.bridge.local_bridge import (
    read_market_snapshot, write_external_context,
)
from algomind.external.cftc_adapter import compute_context as cftc_ctx
from algomind.external.options_adapter import compute_context as options_ctx
from algomind.external.news_adapter import DEFAULT_BUFFER_MINUTES, compute_context as news_ctx

_last_cftc_fetch = 0.0
_cached_cftc = None

_last_options_fetch = 0.0
_cached_options = None

_last_news_fetch = 0.0
_cached_news = None


def build_context(mkt_path: str, now: datetime) -> ExternalContext:
    global _last_cftc_fetch, _cached_cftc
    global _last_options_fetch, _cached_options
    global _last_news_fetch, _cached_news

    ctx = ExternalContext(timestamp=int(now.timestamp()))
    snap = read_market_snapshot(mkt_path)
    now_ts = now.timestamp()

    ctx.context_symbol = snap.symbol if snap is not None else ""
    gold_supported = ctx.context_symbol.upper() in {"XAUUSD", "XAUUSDM"}
    # COMEX positioning is optional gold context, never generic FX/crypto flow.
    # Publication dates inferred from report dates are not verified releases.
    if gold_supported and (now_ts < _last_cftc_fetch or
                           now_ts - _last_cftc_fetch >= 3600.0):
        _last_cftc_fetch = now_ts
        try:
            _cached_cftc = cftc_ctx(now)
        except Exception:
            _cached_cftc = None
    data = _cached_cftc or {}
    fields = ("cftc_publication_ts", "cftc_net_position", "cftc_net_change", "cftc_percentile")
    numeric = all(type(data.get(k)) in (int, float) and math.isfinite(data[k]) for k in fields)
    valid_cftc = (gold_supported and data.get("cftc_valid") is True and
                  data.get("cftc_publication_verified") is True and numeric and
                  type(data.get("cftc_extreme")) is bool and
                  type(data.get("cftc_publication_ts")) is int and
                  0 < data["cftc_publication_ts"] <= now_ts and
                  now_ts - data["cftc_publication_ts"] <= 14 * 86400 and
                  0 <= data["cftc_percentile"] <= 100)
    if valid_cftc:
        for k in (*fields, "cftc_extreme", "cftc_valid", "cftc_publication_verified"):
            setattr(ctx, k, data[k])
    else:
        ctx.data_quality |= DataQuality.EXTERNAL_ABSENT

    # No validated GLD-to-broker-gold mapping or dealer inventory exists.
    # Do not fetch/cache/publish derived options as authoritative context.
    _cached_options = None
    ctx.options_valid = False
    ctx.options_source = "NONE"
    ctx.data_quality |= DataQuality.EXTERNAL_ABSENT

    # --- News (autonomous, ForexFactory XML feed, refresh every 60s)
    if _cached_news is None or (now_ts - _last_news_fetch) >= 60.0:
        # Rate-limit attempts as well as successes. An unavailable result is
        # cached explicitly so a provider outage does not create 5-second retry churn.
        _last_news_fetch = now_ts
        try:
            _cached_news = news_ctx(now, buffer_minutes=DEFAULT_BUFFER_MINUTES, reaction_minutes=15)
        except Exception:
            _cached_news = {"news_valid": False,
                            "news_observed_ts": 0,
                            "news_event_ts": 0,
                            "news_active_window": False,
                            "news_released": False,
                            "news_surprise": 0.0,
                            "news_relative_surprise": 0.0}

    if _cached_news is not None:
        for k, v in _cached_news.items():
            setattr(ctx, k, v)
    if not ctx.news_valid:
        ctx.news_valid = False
        ctx.news_observed_ts = 0
        ctx.data_quality |= DataQuality.EXTERNAL_ABSENT

    return ctx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mkt", required=True, help="Full path to MarketSnapshot file")
    ap.add_argument("--out", required=True, help="Full path to write ExternalContext file")
    ap.add_argument("--out2", default=None, help="Optional secondary path to write ExternalContext file (e.g. Account B)")
    ap.add_argument("--interval", type=float, default=5.0, help="Loop interval seconds")
    args = ap.parse_args()

    if not math.isfinite(args.interval) or args.interval < 1.0:
        ap.error("--interval must be finite and at least 1 second")
    if args.out2:
        ap.error("--out2 is disabled: use a separate launcher and snapshot for each terminal")
    targets = [args.out]
    if args.out2:
        targets.append(args.out2)

    print(f"[ExternalService] started; mkt={args.mkt} targets={targets}")
    print("[ExternalService] CFTC source: official cftc.gov ZIPs (autonomous)")
    print("[ExternalService] News source: ForexFactory XML (autonomous)")
    print("[ExternalService] Options scoring DISABLED; CFTC publication provenance UNVERIFIED")

    while True:
        try:
            now = datetime.now(timezone.utc)
            ctx = build_context(args.mkt, now)
            for target in targets:
                write_external_context(target, ctx)
            print(f"[ExternalService] wrote ctx "
                  f"cftc={ctx.cftc_valid} opt={ctx.options_valid} "
                  f"src={ctx.options_source} news={ctx.news_valid} "
                  f"dq=0x{ctx.data_quality:04X}")
        except KeyboardInterrupt:
            print("[ExternalService] interrupted; exiting")
            return
        except Exception as e:
            print(f"[ExternalService] ERROR: {e}")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()

