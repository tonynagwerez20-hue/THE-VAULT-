"""MT5 Data Source Adapter.

Extracts MT5 tick/OHLC data from log files, export CSVs, or MetaTrader 5 Files directory.
Appends strict provenance metadata: DataQualityTag = PROXY.
"""
from __future__ import annotations
import os
import glob
import pandas as pd
import numpy as np
from typing import List, Tuple
from algomind.orderflow_lab.schema import (
    OrderFlowTick, SourceMetadata, DataQualityTag
)


class MT5Adapter:
    def __init__(self, data_dir: str = "C:/Users/USER/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/MQL5/Files"):
        self.data_dir = data_dir

    def get_metadata(self, symbol: str = "XAUUSD") -> SourceMetadata:
        return SourceMetadata(
            source_name="MetaTrader 5 Retail Feed",
            instrument="Spot Gold",
            venue="Broker MetaTrader 5 Server",
            symbol=symbol,
            timezone="MT5 Server Time",
            data_type="TICK_AND_OHLC",
            price_type="SPOT",
            volume_type="TICK_COUNT",
            bid_available=True,
            ask_available=True,
            trade_available=False,
            depth_available=False,
            classification_method="TICK_RULE",
            license_notes="Locally available MT5 client feed",
            quality_tag=DataQualityTag.PROXY
        )

    def load_ticks_from_csv(self, file_path: str) -> List[OrderFlowTick]:
        if not os.path.exists(file_path):
            return []
        
        df = pd.read_csv(file_path)
        ticks: List[OrderFlowTick] = []
        prev_price = None

        for _, row in df.iterrows():
            ts = float(row.get('timestamp', row.get('time', 0)))
            bid = float(row.get('bid', row.get('close', 0.0)))
            ask = float(row.get('ask', row.get('close', 0.0)))
            price = float(row.get('last', row.get('close', bid)))
            vol = float(row.get('volume', row.get('tick_volume', 1.0)))

            direction = 0
            if prev_price is not None:
                if price > prev_price:
                    direction = 1
                elif price < prev_price:
                    direction = -1
                else:
                    direction = 0
            prev_price = price

            ticks.append(OrderFlowTick(
                timestamp=ts,
                price=price,
                bid=bid,
                ask=ask,
                volume=vol,
                tick_volume=int(vol),
                direction=direction,
                classified_by="TICK_RULE",
                quality_tag=DataQualityTag.PROXY
            ))
        return ticks

    def load_ohlc_from_csv(self, file_path: str) -> pd.DataFrame:
        if not os.path.exists(file_path):
            return pd.DataFrame()
        return pd.read_csv(file_path)
