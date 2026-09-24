"""Hyperliquid Gold / Klustra Reference Adapter.

Ingests free Hyperliquid gold order-flow data as an independent crypto-perp reference stream.
Appends strict provenance metadata: DataQualityTag = PROXY.
Explicit Note: Hyperliquid Gold is NOT COMEX Gold!
"""
from __future__ import annotations
import os
import pandas as pd
from typing import List
from algomind.orderflow_lab.schema import (
    OrderFlowTick, SourceMetadata, DataQualityTag
)


class HyperliquidAdapter:
    def __init__(self, data_path: str = "data/orderflow/hyperliquid_gold_sample.csv"):
        self.data_path = data_path

    def get_metadata(self) -> SourceMetadata:
        return SourceMetadata(
            source_name="Hyperliquid DEX / Klustra Reference",
            instrument="Hyperliquid Gold Perp (GOLD-PERP)",
            venue="Hyperliquid Decentralized Exchange",
            symbol="GOLD",
            timezone="UTC",
            data_type="CRYPTO_PERP_TICK",
            price_type="SYNTHETIC_PERP",
            volume_type="REAL_VOLUME",
            bid_available=True,
            ask_available=True,
            trade_available=True,
            depth_available=False,
            classification_method="EXCHANGE_SIDE",
            license_notes="Free Hyperliquid Public L2/Trade Feed",
            quality_tag=DataQualityTag.PROXY
        )

    def load_ticks(self) -> List[OrderFlowTick]:
        if not os.path.exists(self.data_path):
            return []
        
        df = pd.read_csv(self.data_path)
        ticks: List[OrderFlowTick] = []

        for _, row in df.iterrows():
            ts = float(row.get('timestamp', 0))
            price = float(row.get('price', 0.0))
            side = str(row.get('side', '')).upper()
            vol = float(row.get('size', row.get('volume', 1.0)))

            direction = 1 if side in ['BUY', 'B'] else (-1 if side in ['SELL', 'S'] else 0)

            ticks.append(OrderFlowTick(
                timestamp=ts,
                price=price,
                bid=price,
                ask=price,
                volume=vol,
                tick_volume=int(vol),
                direction=direction,
                classified_by="EXCHANGE_TRADE_SIDE",
                quality_tag=DataQualityTag.PROXY
            ))
        return ticks
