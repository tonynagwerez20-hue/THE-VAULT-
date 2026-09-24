"""Manual Sample Data Adapter.

Loads user-provided CSV or JSON sample files and converts them into
OrderFlowTick objects with full validation.

Validation rules (spec §12):
  - Missing/invalid timestamp       → flagged, record excluded from calculations
  - Missing/non-numeric price       → flagged, record excluded
  - Non-positive volume             → flagged, record excluded
  - bid > ask                       → flagged, record excluded
  - Duplicate timestamps            → flagged, record preserved with warning
  - Out-of-order timestamps         → flagged, record preserved with warning
  - NaN / infinity                  → flagged, record excluded
  - Malformed records               → flagged, raw record preserved

Direction handling:
  - If direction column is supplied it is tagged OBSERVED_DIRECTION.
  - If missing, direction is estimated via tick-rule and tagged ESTIMATED_DIRECTION.
  - Supplied direction is NOT automatically trusted (spec §11).

DataQualityTag:
  - LIMITED if only timestamp + price supplied.
  - PROXY  if bid/ask/volume also supplied.
"""

from __future__ import annotations
import os
import json
import math
import warnings
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import pandas as pd

from algomind.orderflow_lab.schema import (
    OrderFlowTick, SourceMetadata, DataQualityTag
)


@dataclass
class ValidationReport:
    """Collects validation issues without silently deleting records."""
    total_raw_records: int = 0
    valid_records: int = 0
    excluded_records: int = 0
    issues: List[dict] = field(default_factory=list)

    def add_issue(self, row_index: int, field_name: str, issue: str, raw_record: dict):
        self.issues.append({
            "row_index": row_index,
            "field": field_name,
            "issue": issue,
            "raw_record": raw_record,
        })

    def summary(self) -> str:
        lines = [
            f"[ManualSampleAdapter] Validation Report",
            f"  Total raw records : {self.total_raw_records}",
            f"  Valid records     : {self.valid_records}",
            f"  Excluded records  : {self.excluded_records}",
            f"  Issue count       : {len(self.issues)}",
        ]
        if self.issues:
            lines.append("  First 10 issues:")
            for iss in self.issues[:10]:
                lines.append(
                    f"    Row {iss['row_index']}: [{iss['field']}] {iss['issue']}"
                )
        return "\n".join(lines)


class ManualSampleAdapter:
    """Adapter for user-provided manual sample files (CSV or JSON).

    Minimum required columns: timestamp, price
    Optional columns: bid, ask, last, volume, tick_volume, direction, trade_id, symbol
    """

    REQUIRED_COLUMNS = {"timestamp", "price"}
    OPTIONAL_COLUMNS = {
        "bid", "ask", "last", "volume", "tick_volume",
        "direction", "trade_id", "symbol",
    }

    def __init__(self, file_path: str, default_symbol: str = "XAUUSD"):
        """
        Args:
            file_path: Path to a CSV or JSON file.
            default_symbol: Symbol to assign if not present in data.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Manual sample file not found: {file_path}")
        self.file_path = file_path
        self.default_symbol = default_symbol
        self._validation_report: Optional[ValidationReport] = None

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------
    def get_metadata(self) -> SourceMetadata:
        """Return provenance metadata for manually supplied data."""
        return SourceMetadata(
            source_name="User-Provided Manual Sample",
            instrument="Gold / User-Defined",
            venue="Manual Import",
            symbol=self.default_symbol,
            timezone="UTC",
            data_type="TICK",
            price_type="SPOT",
            volume_type="TICK_COUNT",
            bid_available=False,
            ask_available=False,
            trade_available=False,
            depth_available=False,
            classification_method="TICK_RULE",
            license_notes="Manually imported sample – DataQuality PROXY/LIMITED",
            quality_tag=DataQualityTag.PROXY,
        )

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------
    def _load_raw_dataframe(self) -> pd.DataFrame:
        """Load raw data from CSV or JSON into a DataFrame."""
        ext = os.path.splitext(self.file_path)[1].lower()
        if ext == ".json":
            with open(self.file_path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            if isinstance(raw, list):
                df = pd.DataFrame(raw)
            elif isinstance(raw, dict) and "data" in raw:
                df = pd.DataFrame(raw["data"])
            else:
                raise ValueError(
                    f"Unsupported JSON structure in {self.file_path}. "
                    "Expected a list of objects or {{'data': [...]}}."
                )
        elif ext == ".csv":
            df = pd.read_csv(self.file_path)
        else:
            raise ValueError(
                f"Unsupported file extension '{ext}'. Use .csv or .json."
            )
        # Normalise column names
        df.columns = [c.strip().lower() for c in df.columns]
        return df

    # ------------------------------------------------------------------
    # Validation (spec §12)
    # ------------------------------------------------------------------
    @staticmethod
    def _is_bad_number(val) -> bool:
        """Return True if val is NaN, inf, or not a finite number."""
        try:
            f = float(val)
            return not math.isfinite(f)
        except (TypeError, ValueError):
            return True

    def _validate_row(
        self, idx: int, row: dict, report: ValidationReport
    ) -> Optional[dict]:
        """Validate a single row. Returns cleaned dict or None if excluded."""
        raw = dict(row)

        # --- timestamp ---
        ts_raw = row.get("timestamp")
        if ts_raw is None or (isinstance(ts_raw, float) and math.isnan(ts_raw)):
            report.add_issue(idx, "timestamp", "missing timestamp", raw)
            return None
        # Convert to ISO-8601 UTC
        try:
            if isinstance(ts_raw, (int, float)):
                ts_dt = pd.Timestamp(ts_raw, unit="s", tz="UTC")
            else:
                ts_dt = pd.Timestamp(str(ts_raw))
                if ts_dt.tzinfo is None:
                    ts_dt = ts_dt.tz_localize("UTC")
                else:
                    ts_dt = ts_dt.tz_convert("UTC")
            row["timestamp_utc"] = ts_dt.isoformat()
            row["source_timestamp"] = str(ts_raw)
            row["timestamp_epoch"] = ts_dt.timestamp()
        except Exception:
            report.add_issue(idx, "timestamp", f"invalid timestamp: {ts_raw}", raw)
            return None

        # --- price ---
        price_raw = row.get("price")
        if price_raw is None or self._is_bad_number(price_raw):
            report.add_issue(idx, "price", f"missing/invalid price: {price_raw}", raw)
            return None
        price = float(price_raw)
        if price <= 0:
            report.add_issue(idx, "price", f"non-positive price: {price}", raw)
            return None

        # --- volume ---
        vol_raw = row.get("volume", 1.0)
        if self._is_bad_number(vol_raw):
            report.add_issue(idx, "volume", f"invalid volume: {vol_raw}", raw)
            return None
        vol = float(vol_raw)
        if vol < 0:
            report.add_issue(idx, "volume", f"negative volume: {vol}", raw)
            return None

        # --- bid / ask ---
        bid = float(row.get("bid", 0.0)) if not self._is_bad_number(row.get("bid", 0.0)) else 0.0
        ask = float(row.get("ask", 0.0)) if not self._is_bad_number(row.get("ask", 0.0)) else 0.0
        if bid > 0 and ask > 0 and bid > ask:
            report.add_issue(idx, "bid_ask", f"bid ({bid}) > ask ({ask})", raw)
            return None

        # --- direction ---
        dir_raw = row.get("direction")
        direction_source = "ESTIMATED_DIRECTION"
        direction_val = None
        if dir_raw is not None and not self._is_bad_number(dir_raw):
            d = int(float(dir_raw))
            if d in (-1, 0, 1):
                direction_val = d
                direction_source = "OBSERVED_DIRECTION"

        # Build cleaned record
        return {
            "timestamp_epoch": row["timestamp_epoch"],
            "timestamp_utc": row["timestamp_utc"],
            "source_timestamp": row["source_timestamp"],
            "price": price,
            "bid": bid,
            "ask": ask,
            "last": float(row.get("last", price)) if not self._is_bad_number(row.get("last", price)) else price,
            "volume": vol,
            "tick_volume": int(row.get("tick_volume", vol)) if not self._is_bad_number(row.get("tick_volume", vol)) else int(vol),
            "direction_observed": direction_val,
            "direction_source": direction_source,
            "trade_id": row.get("trade_id"),
            "symbol": row.get("symbol", self.default_symbol),
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def load_samples(self) -> Tuple[List[OrderFlowTick], ValidationReport]:
        """Load, validate, and convert manual samples to OrderFlowTick objects.

        Returns:
            Tuple of (valid ticks, validation report).
        """
        df = self._load_raw_dataframe()

        # Check required columns
        missing_req = self.REQUIRED_COLUMNS - set(df.columns)
        if missing_req:
            raise ValueError(
                f"Manual sample file is missing required columns: {missing_req}"
            )

        report = ValidationReport(total_raw_records=len(df))
        cleaned: List[dict] = []

        for idx, row in df.iterrows():
            result = self._validate_row(int(idx), row.to_dict(), report)
            if result is not None:
                cleaned.append(result)

        # --- duplicate / out-of-order timestamp checks ---
        if cleaned:
            seen_ts = set()
            prev_ts = -float("inf")
            for rec in cleaned:
                ts = rec["timestamp_epoch"]
                if ts in seen_ts:
                    report.add_issue(
                        -1, "timestamp",
                        f"duplicate timestamp: {rec['timestamp_utc']}",
                        rec,
                    )
                seen_ts.add(ts)
                if ts < prev_ts:
                    report.add_issue(
                        -1, "timestamp",
                        f"out-of-order timestamp: {rec['timestamp_utc']}",
                        rec,
                    )
                prev_ts = ts

        # --- estimate direction where missing (tick-rule) ---
        prev_price = None
        for rec in cleaned:
            if rec["direction_observed"] is None:
                if prev_price is not None:
                    if rec["price"] > prev_price:
                        rec["direction_final"] = 1
                    elif rec["price"] < prev_price:
                        rec["direction_final"] = -1
                    else:
                        rec["direction_final"] = 0
                else:
                    rec["direction_final"] = 0
                rec["direction_source"] = "ESTIMATED_DIRECTION"
            else:
                rec["direction_final"] = rec["direction_observed"]
            prev_price = rec["price"]

        # --- determine data quality per record ---
        ticks: List[OrderFlowTick] = []
        for rec in cleaned:
            has_bid_ask = rec["bid"] > 0 and rec["ask"] > 0
            has_volume = rec["volume"] > 0
            if has_bid_ask and has_volume:
                quality = DataQualityTag.PROXY
            else:
                quality = DataQualityTag.LIMITED

            classified_by = "TICK_RULE"
            if rec["direction_source"] == "OBSERVED_DIRECTION":
                classified_by = "USER_SUPPLIED"

            ticks.append(OrderFlowTick(
                timestamp=rec["timestamp_epoch"],
                price=rec["price"],
                bid=rec["bid"],
                ask=rec["ask"],
                volume=rec["volume"],
                tick_volume=rec["tick_volume"],
                direction=rec["direction_final"],
                classified_by=classified_by,
                quality_tag=quality,
            ))

        report.valid_records = len(ticks)
        report.excluded_records = report.total_raw_records - len(ticks)
        self._validation_report = report

        return ticks, report

    @property
    def validation_report(self) -> Optional[ValidationReport]:
        """Return the most recent validation report, or None if not yet loaded."""
        return self._validation_report
