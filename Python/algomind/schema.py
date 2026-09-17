"""AlgoMind canonical schema definitions (Python side).

Mirrors Contract.mqh. Any field-name or type change is a breaking
change and requires a new schema version per D3 §31.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict

SCHEMA_VERSION = 100  # v1.0.0


class DataQuality:
    OK              = 0x0000
    MISSING_TICKS   = 0x0001
    STALE_EXTERNAL  = 0x0002
    SCHEMA_MISMATCH = 0x0004
    CLOCK_MISMATCH  = 0x0008
    BROKER_INVALID  = 0x0010
    EXTERNAL_ABSENT = 0x0020
    MODEL_MISMATCH  = 0x0040
    FATAL           = 0x8000


@dataclass
class ExternalContext:
    """Canonical external-context payload exchanged with MQL5."""
    schema_version: int = SCHEMA_VERSION
    timestamp: int = 0
    data_quality: int = DataQuality.OK

    # CFTC (Math Spec §23)
    cftc_valid: bool = False
    cftc_publication_ts: int = 0
    cftc_net_position: float = 0.0
    cftc_net_change: float = 0.0
    cftc_percentile: float = 50.0
    cftc_extreme: bool = False

    # Options / Pizzo-style (Math Spec §22)
    options_valid: bool = False
    options_obs_ts: int = 0
    options_basis: float = 0.0
    options_oi_concentration: float = 0.0
    options_strike_distance_atr: float = 0.0
    options_gamma_regime: int = 0  # -1, 0, +1
    options_source: str = "NONE"   # PROXY_GLD_CBOE | PROXY_GLD_YF | NONE

    # News
    news_valid: bool = False
    news_event_ts: int = 0
    news_active_window: bool = False
    news_surprise: float = 0.0
    news_relative_surprise: float = 0.0

    def to_kv_lines(self) -> str:
        """Serialize to key=value lines for MQL5's line-based reader."""
        d = asdict(self)
        renamed = {
            "schema_version":    d["schema_version"],
            "timestamp":         d["timestamp"],
            "data_quality":      d["data_quality"],
            "cftc_valid":        d["cftc_valid"],
            "cftc_pub_ts":       d["cftc_publication_ts"],
            "cftc_net":          d["cftc_net_position"],
            "cftc_net_chg":      d["cftc_net_change"],
            "cftc_pct":          d["cftc_percentile"],
            "cftc_extreme":      d["cftc_extreme"],
            "options_valid":     d["options_valid"],
            "options_obs_ts":    d["options_obs_ts"],
            "options_basis":     d["options_basis"],
            "options_oi_conc":   d["options_oi_concentration"],
            "options_sd_atr":    d["options_strike_distance_atr"],
            "options_gamma":     d["options_gamma_regime"],
            "options_source":    d["options_source"],
            "news_valid":        d["news_valid"],
            "news_ts":           d["news_event_ts"],
            "news_active":       d["news_active_window"],
            "news_surprise":     d["news_surprise"],
            "news_rel_surprise": d["news_relative_surprise"],
        }
        lines = []
        for k, v in renamed.items():
            if isinstance(v, bool):
                v = 1 if v else 0
            lines.append(f"{k}={v}")
        return "\n".join(lines) + "\n"


@dataclass
class MarketSnapshotIn:
    """Market snapshot written by MQL5 for Python to read."""
    snapshot_id: int = 0
    timestamp: int = 0
    symbol: str = ""
    bid: float = 0.0
    ask: float = 0.0
    spread: float = 0.0
    atr14: float = 0.0
    structure_dir: int = 0
    close: float = 0.0
    equity: float = 0.0
    session_state: int = 0
    schema_version: int = 0


def parse_kv_file(path: str) -> dict:
    """Read key=value lines from a file written by MQL5.

    Missing file or read error -> empty dict.
    Malformed lines are skipped; caller treats empty result as absent.
    """
    out = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    except (FileNotFoundError, OSError):
        pass
    return out
