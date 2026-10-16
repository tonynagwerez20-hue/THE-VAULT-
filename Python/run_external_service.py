"""AlgoMind external-information service — AUTONOMOUS.

Fetches CFTC COT (official cftc.gov ZIPs), ForexFactory news (XML),
and GLD options (CBOE primary, yfinance fallback).

Never issues executable orders. Never bypasses MQL5 hard risk.
Fail closed: on any error, write a context marked unavailable.
"""
from __future__ import annotations
import argparse
import time
from datetime import datetime, timezone

from algomind.schema import ExternalContext, DataQuality
from algomind.bridge.local_bridge import (
    read_market_snapshot, write_external_context,
)
from algomind.external.cftc_adapter import compute_context as cftc_ctx
from algomind.external.options_adapter import compute_context as options_ctx
from algomind.external.news_adapter import compute_context as news_ctx

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

    # --- CFTC (autonomous, official cftc.gov source, refresh every 1 hour)
    if _cached_cftc is None or (now_ts - _last_cftc_fetch) >= 3600.0:
        try:
            _cached_cftc = cftc_ctx(now)
            _last_cftc_fetch = now_ts
        except Exception:
            _cached_cftc = None

    if _cached_cftc and _cached_cftc.get("cftc_valid"):
        for k, v in _cached_cftc.items():
            setattr(ctx, k, v)
    else:
        ctx.cftc_valid = False
        ctx.data_quality |= DataQuality.EXTERNAL_ABSENT

    # --- Options (CBOE -> yfinance fallback, refresh every 60s)
    spot = snap.close if snap and snap.close > 0 else 0.0
    atr = snap.atr14 if snap else 0.0
    if _cached_options is None or (now_ts - _last_options_fetch) >= 60.0:
        try:
            _cached_options = options_ctx(spot, atr, gc_price=None, now=now)
            _last_options_fetch = now_ts
        except Exception:
            _cached_options = None

    if _cached_options and _cached_options.get("options_valid"):
        for k, v in _cached_options.items():
            setattr(ctx, k, v)
    else:
        ctx.options_valid = False
        ctx.options_source = "NONE"
        ctx.data_quality |= DataQuality.EXTERNAL_ABSENT

    # --- News (autonomous, ForexFactory XML feed, refresh every 60s)
    if _cached_news is None or (now_ts - _last_news_fetch) >= 60.0:
        try:
            _cached_news = news_ctx(now, buffer_minutes=30, reaction_bars=3,
                                    bar_minutes=5)
            _last_news_fetch = now_ts
        except Exception:
            _cached_news = None

    if _cached_news and _cached_news.get("news_valid"):
        for k, v in _cached_news.items():
            setattr(ctx, k, v)
    else:
        ctx.news_valid = False
        # Note: news is only valid/active during news events; if inactive, not an external error unless fetch failed completely

    return ctx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mkt", required=True, help="Full path to MarketSnapshot file")
    ap.add_argument("--out", required=True, help="Full path to write ExternalContext file")
    ap.add_argument("--out2", default=None, help="Optional secondary path to write ExternalContext file (e.g. Account B)")
    ap.add_argument("--interval", type=float, default=5.0, help="Loop interval seconds")
    args = ap.parse_args()

    targets = [args.out]
    if args.out2:
        targets.append(args.out2)

    print(f"[ExternalService] started; mkt={args.mkt} targets={targets}")
    print("[ExternalService] CFTC source: official cftc.gov ZIPs (autonomous)")
    print("[ExternalService] News source: ForexFactory XML (autonomous)")
    print("[ExternalService] Options source: CBOE -> yfinance fallback")

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
