"""Order-Flow Lab Core Engines.

Each engine corresponds to a layer in the flow architecture (spec §8):
  PriceBinEngine → ProxyVWAPEngine, ProxyProfileEngine, ProxyFootprintEngine
  → EventEngine, ProxyDOMEngine
"""

from Amigo.orderflow_lab.engines.price_bin_engine import PriceBinEngine
from Amigo.orderflow_lab.engines.proxy_vwap import ProxyVWAPEngine, VWAPMethod
from Amigo.orderflow_lab.engines.proxy_profile import ProxyProfileEngine
from Amigo.orderflow_lab.engines.proxy_footprint import ProxyFootprintEngine
from Amigo.orderflow_lab.engines.event_engine import EventEngine, FlowEvent
from Amigo.orderflow_lab.engines.proxy_dom import ProxyDOMEngine

__all__ = [
    "PriceBinEngine",
    "ProxyVWAPEngine",
    "VWAPMethod",
    "ProxyProfileEngine",
    "ProxyFootprintEngine",
    "EventEngine",
    "FlowEvent",
    "ProxyDOMEngine",
]

