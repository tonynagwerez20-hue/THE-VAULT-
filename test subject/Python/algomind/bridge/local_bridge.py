"""Local file bridge between MQL5 (broker truth) and Python (external info).

Per D4 REQ-030 / P-10: local file handshake is the first transport.
ZeroMQ is deferred.

Publication uses a same-directory temporary file and replace only.
Failures never deliberately truncate or overwrite the destination. Filesystem atomicity
and crash durability still require platform-specific validation.
"""
from __future__ import annotations
import os
import math
import time
import tempfile
from typing import Optional

from ..schema import SCHEMA_VERSION, MarketSnapshotIn, ExternalContext, parse_kv_file


def _atomic_write(path: str, content: str) -> None:
    import tempfile
    destination = os.path.abspath(path)
    directory = os.path.dirname(destination)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".amigo-publish-", suffix=".tmp", dir=directory)
    last_error = None
    try:
        # Failure before publication must propagate; never overwrite destination.
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            # A flush failure aborts before replace so the previous complete
            # destination remains authoritative. This still does not prove
            # crash durability of the file or containing directory.
            os.fsync(f.fileno())
        for attempt in range(5):
            try:
                os.replace(tmp, destination)
                return
            except OSError as exc:
                last_error = exc
                if attempt < 4:
                    time.sleep(0.05 * (attempt + 1))
        raise OSError("AMIGO publication failed; destination was not directly overwritten") from last_error
    finally:
        try:
            os.remove(tmp)
        except FileNotFoundError:
            pass
        except OSError:
            # Orphan cleanup failure must not trigger a destination rewrite.
            pass


def read_market_snapshot(path: str) -> Optional[MarketSnapshotIn]:
    # This local artifact is refreshed by MQL5 for each evaluated opportunity.
    # Its filesystem age is a transport-freshness check, not proof that the
    # broker's independently sampled fields were atomic.
    kv = parse_kv_file(path)
    required = {
        "snapshot_id", "decision_boundary", "closed_bar_time", "timeframe", "max_age_s",
        "timestamp", "symbol", "bid", "ask", "spread",
        "atr14", "structure_dir", "close", "equity", "session_state",
        "schema_version",
    }
    if not kv or not required.issubset(kv):
        return None
    s = MarketSnapshotIn()
    try:
        s.snapshot_id     = int(kv.get("snapshot_id", 0))
        s.decision_boundary = int(kv.get("decision_boundary", 0))
        s.closed_bar_time = int(kv.get("closed_bar_time", 0))
        s.timeframe       = int(kv.get("timeframe", 0))
        s.max_age_s       = int(kv.get("max_age_s", 0))
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
    numeric = (s.bid, s.ask, s.spread, s.atr14, s.close, s.equity)
    if (s.snapshot_id <= 0 or s.decision_boundary <= 0 or s.closed_bar_time <= 0 or
            s.closed_bar_time >= s.decision_boundary or s.timeframe <= 0 or s.max_age_s <= 0 or
            s.timestamp <= 0 or not s.symbol.strip() or
            s.schema_version != SCHEMA_VERSION or
            any(not math.isfinite(value) for value in numeric) or
            s.bid <= 0 or s.ask < s.bid or s.spread < 0 or
            s.atr14 <= 0 or s.close <= 0 or s.equity <= 0 or
            s.structure_dir not in (-1, 0, 1)):
        return None
    try:
        snapshot_age = time.time() - os.path.getmtime(path)
    except OSError:
        return None
    if (not math.isfinite(snapshot_age) or snapshot_age < 0.0 or
            snapshot_age > s.max_age_s):
        return None
    return s


def write_external_context(path: str, ctx: ExternalContext) -> None:
    _atomic_write(path, ctx.to_kv_lines())


def file_age_seconds(path: str) -> float:
    try:
        return time.time() - os.path.getmtime(path)
    except OSError:
        return float("inf")
