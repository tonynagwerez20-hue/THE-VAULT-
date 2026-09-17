"""Local file bridge between MQL5 (broker truth) and Python (external info).

Per D4 REQ-030 / P-10: local file handshake is the first transport.
ZeroMQ is deferred.

Writes are atomic (temp file + os.replace). Readers see either the
previous complete file or the new complete file, never a partial write.
"""
from __future__ import annotations
import os
import time
from typing import Optional

from ..schema import MarketSnapshotIn, ExternalContext, parse_kv_file


def _atomic_write(path: str, content: str) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def read_market_snapshot(path: str) -> Optional[MarketSnapshotIn]:
    kv = parse_kv_file(path)
    if not kv:
        return None
    s = MarketSnapshotIn()
    try:
        s.snapshot_id     = int(kv.get("snapshot_id", 0))
        s.timestamp       = int(kv.get("timestamp", 0))
        s.symbol          = kv.get("symbol", "")
        s.bid             = float(kv.get("bid", 0.0))
        s.ask             = float(kv.get("ask", 0.0))
        s.spread          = float(kv.get("spread", 0.0))
        s.atr14           = float(kv.get("atr14", 0.0))
        s.structure_dir   = int(kv.get("structure_dir", 0))
        s.close           = float(kv.get("close", 0.0))
        s.equity          = float(kv.get("equity", 0.0))
        s.session_state   = int(kv.get("session_state", 0))
        s.schema_version  = int(kv.get("schema_version", 0))
    except (ValueError, TypeError):
        return None
    return s


def write_external_context(path: str, ctx: ExternalContext) -> None:
    _atomic_write(path, ctx.to_kv_lines())


def file_age_seconds(path: str) -> float:
    try:
        return time.time() - os.path.getmtime(path)
    except OSError:
        return float("inf")
