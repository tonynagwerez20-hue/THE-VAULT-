"""Order-Flow Lab Data Source Adapters.

Each adapter normalises an external data source into the canonical
OrderFlowTick / DataFrame schema with strict provenance metadata.
"""

from Amigo.orderflow_lab.data_sources.mt5_adapter import MT5Adapter
from Amigo.orderflow_lab.data_sources.portara_adapter import PortaraAdapter
from Amigo.orderflow_lab.data_sources.evlabs_adapter import EVLabsAdapter
from Amigo.orderflow_lab.data_sources.hyperliquid_adapter import HyperliquidAdapter
from Amigo.orderflow_lab.data_sources.futures_ohlcv_adapter import FuturesOHLCVAdapter
from Amigo.orderflow_lab.data_sources.manual_sample_adapter import ManualSampleAdapter

__all__ = [
    "MT5Adapter",
    "PortaraAdapter",
    "EVLabsAdapter",
    "HyperliquidAdapter",
    "FuturesOHLCVAdapter",
    "ManualSampleAdapter",
]

