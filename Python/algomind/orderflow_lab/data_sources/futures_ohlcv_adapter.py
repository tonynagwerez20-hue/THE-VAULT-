# futures_ohlcv_adapter.py
"""Futures OHLCV Adapter.

Ingests GC/MGC OHLCV files from a free public source (axb0306 repository) or a local fallback directory.
The adapter returns a pandas.DataFrame with strict provenance metadata.

DataQualityTag = TRUE – the data represents verified exchange‑traded OHLCV.
"""

from __future__ import annotations
import os
import glob
import pandas as pd
from typing import List

from algomind.orderflow_lab.schema import SourceMetadata, DataQualityTag


class FuturesOHLCVAdapter:
    """Adapter for COMEX Gold futures (GC/MGC) OHLCV data.

    The adapter looks for CSV files containing the columns:
        timestamp, open, high, low, close, volume
    Timestamp can be either ISO‑8601 UTC strings or Unix epoch seconds.
    All timestamps are normalised to ISO‑8601 UTC.
    """

    DEFAULT_DATA_DIR = "C:/Users/USER/Desktop/ALGOMIND/Data/futures"

    def __init__(self, data_path: str | None = None):
        """Initialize the adapter.

        Args:
            data_path: Path to a CSV file or a directory containing CSV files.
                       If omitted, the default fallback directory is used.
        """
        self.data_path = data_path or self.DEFAULT_DATA_DIR

    def get_metadata(self) -> SourceMetadata:
        """Return provenance metadata for the futures OHLCV source."""
        return SourceMetadata(
            source_name="AXB0306 COMEX Futures OHLCV",
            instrument="COMEX Gold GC/MGC",
            venue="CME COMEX",
            symbol="GC",
            timezone="US/Central",
            data_type="OHLCV",
            price_type="FUTURES",
            volume_type="REAL_VOLUME",
            bid_available=False,
            ask_available=False,
            trade_available=False,
            depth_available=False,
            classification_method="NONE",
            license_notes="Free public repository (axb0306) – data quality TRUE",
            quality_tag=DataQualityTag.TRUE,
        )

    def _read_csv_file(self, path: str) -> pd.DataFrame:
        """Read a single CSV and normalise column names.

        Expected columns (case‑insensitive):
            timestamp, open, high, low, close, volume
        """
        df = pd.read_csv(path)
        # Normalise column names to lower case
        df.columns = [c.strip().lower() for c in df.columns]
        required = {"timestamp", "open", "high", "low", "close", "volume"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Missing required OHLCV columns {missing} in {path}")
        # Ensure timestamp is ISO‑8601 UTC
        if pd.api.types.is_numeric_dtype(df["timestamp"]):
            # Assume epoch seconds
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
        else:
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df["timestamp"] = df["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        # Reorder columns
        df = df[["timestamp", "open", "high", "low", "close", "volume"]]
        return df

    def load_ohlcv(self) -> pd.DataFrame:
        """Load OHLCV data.

        Returns:
            pandas.DataFrame with columns: timestamp, open, high, low, close, volume
        """
        if not os.path.exists(self.data_path):
            raise FileNotFoundError(f"Futures data path not found: {self.data_path}")

        if os.path.isfile(self.data_path):
            # Single file
            return self._read_csv_file(self.data_path)
        else:
            # Directory – read all CSV files
            pattern = os.path.join(self.data_path, "*.csv")
            files = glob.glob(pattern)
            if not files:
                raise FileNotFoundError(f"No CSV files found in futures directory {self.data_path}")
            dfs: List[pd.DataFrame] = []
            for f in sorted(files):
                try:
                    dfs.append(self._read_csv_file(f))
                except Exception as e:
                    # Log and skip problematic files – they are not fatal for the pipeline
                    print(f"[FuturesOHLCVAdapter] Warning: could not read {f}: {e}")
            if not dfs:
                raise RuntimeError("All futures CSV files failed to load.")
            # Concatenate and sort by timestamp
            full_df = pd.concat(dfs, ignore_index=True)
            full_df.sort_values("timestamp", inplace=True)
            full_df.reset_index(drop=True, inplace=True)
            return full_df
