"""Python ↔ MQL5 Parity Test Suite (Spec §46).

Validates numerical parity between Python orderflow_lab engines and native MQL5 algorithms.
Tests VWAP, Footprint Pressure, POC, VAH, VAL, and State transitions on identical tick inputs.

Tolerance bounds:
  - VWAP difference: < 1e-5
  - Footprint Pressure difference: < 1e-5
  - POC difference: < 1e-5
  - VAH difference: < 1e-5
  - VAL difference: < 1e-5
  - State match: 100% agreement
"""

import pytest
import math
from algomind.orderflow_lab.schema import OrderFlowTick, DataQualityTag, PressureState
from algomind.orderflow_lab.engines.price_bin_engine import PriceBinEngine
from algomind.orderflow_lab.engines.proxy_vwap import ProxyVWAPEngine, VWAPMethod
from algomind.orderflow_lab.engines.proxy_profile import ProxyProfileEngine
from algomind.orderflow_lab.engines.proxy_footprint import ProxyFootprintEngine
from algomind.orderflow_lab.engines.event_engine import EventEngine


# ----------------------------------------------------------------------
# Pure Python implementation of the exact MQL5 C++ logic for direct parity validation
# ----------------------------------------------------------------------
class MQL5ParitySimulator:
    """Simulates exact MQL5 C++ struct & class operations in Python for numerical parity check."""

    def __init__(self, tick_size=0.01, value_area_pct=0.70, pressure_threshold=0.25):
        self.tick_size = tick_size
        self.value_area_pct = value_area_pct
        self.pressure_threshold = pressure_threshold

    def run_tick_sequence(self, ticks):
        # 1. VWAP
        cum_weighted = 0.0
        cum_vol = 0.0
        for t in ticks:
            cum_weighted += t.price * t.volume
            cum_vol += t.volume
        mql_vwap = cum_weighted / cum_vol if cum_vol > 0 else 0.0

        # 2. Footprint Bins
        bins = {}
        prev_p = 0.0
        for t in ticks:
            direction = t.direction
            if direction == 0 and prev_p > 0.0:
                if t.price > prev_p: direction = 1
                elif t.price < prev_p: direction = -1
            prev_p = t.price

            norm_p = round(round(t.price / self.tick_size) * self.tick_size, 10)
            if norm_p not in bins:
                bins[norm_p] = {"act": 0.0, "buy": 0.0, "sell": 0.0, "delta": 0.0}

            bins[norm_p]["act"] += t.volume
            if direction == 1:
                bins[norm_p]["buy"] += t.volume
            elif direction == -1:
                bins[norm_p]["sell"] += t.volume
            bins[norm_p]["delta"] = bins[norm_p]["buy"] - bins[norm_p]["sell"]

        # 3. Footprint Pressure
        sum_delta = sum(b["delta"] for b in bins.values())
        sum_abs_delta = sum(abs(b["delta"]) for b in bins.values())
        mql_pressure = sum_delta / (sum_abs_delta + 1e-12)

        # 4. State
        if mql_pressure >= self.pressure_threshold: mql_state = "BULLISH"
        elif mql_pressure <= -self.pressure_threshold: mql_state = "BEARISH"
        else: mql_state = "NEUTRAL"

        # 5. Profile (POC, VAH, VAL)
        poc_p = max(bins, key=lambda p: bins[p]["act"])
        sorted_by_act = sorted(bins.items(), key=lambda kv: kv[1]["act"], reverse=True)
        tot_act = sum(b["act"] for b in bins.values())
        target_act = self.value_area_pct * tot_act
        cum = 0.0
        va_prices = []
        for p, b in sorted_by_act:
            cum += b["act"]
            va_prices.append(p)
            if cum >= target_act:
                break

        mql_vah = max(va_prices) if va_prices else poc_p
        mql_val = min(va_prices) if va_prices else poc_p

        return {
            "vwap": mql_vwap,
            "pressure": mql_pressure,
            "state": mql_state,
            "poc": poc_p,
            "vah": mql_vah,
            "val": mql_val,
        }


class TestPythonMQL5Parity:

    def test_parity_vwap_and_pressure(self):
        # Generate test ticks
        ticks = [
            OrderFlowTick(timestamp=1.0, price=2000.10, volume=2.0, direction=1),
            OrderFlowTick(timestamp=2.0, price=2000.20, volume=5.0, direction=1),
            OrderFlowTick(timestamp=3.0, price=2000.15, volume=3.0, direction=-1),
            OrderFlowTick(timestamp=4.0, price=2000.30, volume=10.0, direction=1),
        ]

        # Python Engine
        bin_engine = PriceBinEngine(tick_size=0.01)
        bins = bin_engine.build_from_ticks(ticks)

        vwap_engine = ProxyVWAPEngine(method=VWAPMethod.TICK_PRICE)
        vwap_engine.update_from_bins(bins)
        py_vwap = vwap_engine.current_vwap

        py_pressure = ProxyFootprintEngine.compute_aggregate_pressure(bins)
        py_state = ProxyFootprintEngine.classify_state(py_pressure, 0.25).value

        profile_engine = ProxyProfileEngine(value_area_pct=0.70)
        profile_snap = profile_engine.compute(bins, 0.0, "XAUUSD")

        # MQL5 Simulator
        mql_sim = MQL5ParitySimulator(tick_size=0.01)
        mql_res = mql_sim.run_tick_sequence(ticks)

        # Tolerance checks
        assert abs(py_vwap - mql_res["vwap"]) < 1e-5, f"VWAP Mismatch: Py={py_vwap}, MQL={mql_res['vwap']}"
        assert abs(py_pressure - mql_res["pressure"]) < 1e-5, f"Pressure Mismatch: Py={py_pressure}, MQL={mql_res['pressure']}"
        assert py_state == mql_res["state"], f"State Mismatch: Py={py_state}, MQL={mql_res['state']}"
        assert abs(profile_snap.poc_price - mql_res["poc"]) < 1e-5, f"POC Mismatch: Py={profile_snap.poc_price}, MQL={mql_res['poc']}"
        assert abs(profile_snap.vah_price - mql_res["vah"]) < 1e-5, f"VAH Mismatch: Py={profile_snap.vah_price}, MQL={mql_res['vah']}"
        assert abs(profile_snap.val_price - mql_res["val"]) < 1e-5, f"VAL Mismatch: Py={profile_snap.val_price}, MQL={mql_res['val']}"

    def test_parity_mixed_tick_series(self):
        ticks = [
            OrderFlowTick(timestamp=float(i), price=2000.0 + (i % 5) * 0.10, volume=float((i % 3) + 1), direction=1 if i % 2 == 0 else -1)
            for i in range(50)
        ]

        bin_engine = PriceBinEngine(tick_size=0.01)
        bins = bin_engine.build_from_ticks(ticks)

        vwap_engine = ProxyVWAPEngine(method=VWAPMethod.TICK_PRICE)
        vwap_engine.update_from_bins(bins)

        py_vwap = vwap_engine.current_vwap
        py_pressure = ProxyFootprintEngine.compute_aggregate_pressure(bins)

        mql_sim = MQL5ParitySimulator(tick_size=0.01)
        mql_res = mql_sim.run_tick_sequence(ticks)

        assert abs(py_vwap - mql_res["vwap"]) < 1e-5
        assert abs(py_pressure - mql_res["pressure"]) < 1e-5
