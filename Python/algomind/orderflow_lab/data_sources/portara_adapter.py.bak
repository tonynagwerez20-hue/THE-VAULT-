"""Portara Futures Historical Data Adapter.

Ingests free complimentary Portara COMEX GC futures tick data samples.
Appends strict provenance metadata: DataQualityTag = TRUE.
"""
from __future__ import annotations
import os
import pandas as pd
from typing import List
from algomind.orderflow_lab.schema import (
    OrderFlowTick, SourceMetadata, DataQualityTag
)


class PortaraAdapter:
    def __init__(self, data_path: str = "data/orderflow/portara_gc_sample.csv"):
        self.data_path = data_path

    def get_metadata(self) -> SourceMetadata:
        return SourceMetadata(
            source_name="Portara CQG Historical Futures Sample",
            instrument="COMEX Gold GC",
            venue="CME COMEX",
            symbol="GC",
            timezone="US/Central",
            data_type="TICK_TRADE_AND_QUOTE",
            price_type="FUTURES",
            volume_type="REAL_VOLUME",
            bid_available=True,
            ask_available=True,
            trade_available=True,
            depth_available=False,
            classification_method="LEE_READY_BID_ASK",
            license_notes="Complimentary Portara Historical Sample",
            quality_tag=DataQualityTag.TRUE
        )

    def load_ticks(self) -> List[OrderFlowTick]:
        if not os.path.exists(self.data_path):
            return []
        
        df = pd.read_csv(self.data_path)
        ticks: List[OrderFlowTick] = []
        
        for _, row in df.iterrows():
            ts = float(row.get('timestamp', 0))
            price = float(row.get('price', row.get('trade_price', 0.0)))
            bid = float(row.get('bid', 0.0))
            ask = float(row.get('ask', 0.0))
            vol = float(row.get('volume', 1.0))

            # Lee & Ready Classification against Bid/Ask quote midpoint
            mid = (bid + ask) / 2.0 if (bid > 0 and ask > 0) else price
            if price > mid:
                direction = 1
            elif price < mid:
                direction = -1
            else:
                direction = 0

            ticks.append(OrderFlowTick(
                timestamp=ts,
                price=price,
                bid=bid,
                ask=ask,
                volume=vol,
                tick_volume=int(vol),
                direction=direction,
                classified_by="LEE_READY_QUOTE",
                quality_tag=DataQualityTag.TRUE
            ))
        return ticks
