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


def build_context(mkt_path: str, now: datetime) -> ExternalContext:
    ctx = ExternalContext(timestamp=int(now.timestamp()))
    snap = read_market_snapshot(mkt_path)

    # --- CFTC (autonomous, official cftc.gov source)
    try:
        for k, v in cftc_ctx(now).items():
            setattr(ctx, k, v)
    except Exception:
        ctx.cftc_valid = False
        ctx.data_quality |= DataQuality.EXTERNAL_ABSENT

    # --- Options (CBOE -> yfinance fallback)
    try:
        spot = snap.close if snap and snap.close > 0 else 0.0
        atr = snap.atr14 if snap else 0.0
        for k, v in options_ctx(spot, atr, gc_price=None, now=now).items():
            setattr(ctx, k, v)
    except Exception:
        ctx.options_valid = False
        ctx.options_source = "NONE"
        ctx.data_quality |= DataQuality.EXTERNAL_ABSENT

    # --- News (autonomous, ForexFactory XML feed)
    try:
        for k, v in news_ctx(now, buffer_minutes=30, reaction_bars=3,
                             bar_minutes=5).items():
            setattr(ctx, k, v)
    except Exception:
        ctx.news_valid = False
        ctx.data_quality |= DataQuality.EXTERNAL_ABSENT

    return ctx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mkt", required=True, help="Full path to MarketSnapshot file")
    ap.add_argument("--out", required=True, help="Full path to write ExternalContext file")
    ap.add_argument("--interval", type=float, default=5.0, help="Loop interval seconds")
    args = ap.parse_args()

    print(f"[ExternalService] started; mkt={args.mkt} out={args.out}")
    print("[ExternalService] CFTC source: official cftc.gov ZIPs (autonomous)")
    print("[ExternalService] News source: ForexFactory XML (autonomous)")
    print("[ExternalService] Options source: CBOE -> yfinance fallback")

    while True:
        try:
            now = datetime.now(timezone.utc)
            ctx = build_context(args.mkt, now)
            write_external_context(args.out, ctx)
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
