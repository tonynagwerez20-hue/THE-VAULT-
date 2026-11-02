"""EV Trading Labs Spot FX / Gold Adapter.

Ingests free historical XAUUSD retail tick / bar data samples.
Appends strict provenance metadata: DataQualityTag = LIMITED.
"""
from __future__ import annotations
import os
import pandas as pd
from typing import List
from algomind.orderflow_lab.schema import (
    OrderFlowTick, SourceMetadata, DataQualityTag
)


class EVLabsAdapter:
    def __init__(self, data_path: str = "data/orderflow/evlabs_xauusd_sample.csv"):
        self.data_path = data_path

    def get_metadata(self) -> SourceMetadata:
        return SourceMetadata(
            source_name="EV Trading Labs Free Dataset",
            instrument="Spot Gold",
            venue="Independent Retail / FX Stream",
            symbol="XAUUSD",
            timezone="UTC",
            data_type="HISTORICAL_TICKS",
            price_type="SPOT",
            volume_type="TICK_COUNT",
            bid_available=True,
            ask_available=True,
            trade_available=False,
            depth_available=False,
            classification_method="TICK_RULE",
            license_notes="Free EV Trading Labs Public Download",
            quality_tag=DataQualityTag.LIMITED
        )

    def load_ticks(self) -> List[OrderFlowTick]:
        if not os.path.exists(self.data_path):
            return []
        
        df = pd.read_csv(self.data_path)
        ticks: List[OrderFlowTick] = []
        prev_price = None

        for _, row in df.iterrows():
            ts = float(row.get('timestamp', 0))
            price = float(row.get('close', row.get('price', 0.0)))
            bid = float(row.get('bid', price))
            ask = float(row.get('ask', price))
            vol = float(row.get('tick_volume', row.get('volume', 1.0)))

            direction = 0
            if prev_price is not None:
                if price > prev_price:
                    direction = 1
                elif price < prev_price:
                    direction = -1
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
                quality_tag=DataQualityTag.LIMITED
            ))
        return ticks
