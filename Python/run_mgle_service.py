"""
ALGOMIND MACRO / GEOPOLITICAL / GOLD / PROXY-OPTIONS LAYER (MGLE)
==================================================================
Autonomous External Service Script (v1.0)
Runs continuously on a 5-second loop, computing MGLE Shadow Snapshots
and writing key=value updates for MQL5 consumption.
"""

from __future__ import annotations
import os
import sys
import time
import argparse
from datetime import datetime, timezone
import numpy as np

from algomind.mgle.schema import MGLESnapshot, DataQualityTag, DataQualityBitmask, MacroLevel
from algomind.mgle.db import MGLEDatabase
from algomind.mgle.macro_engines import MacroEngines, GeoEngine
from algomind.mgle.cftc_engine import CFTCEngine
from algomind.mgle.options_engine import OptionsProxyEngine
from algomind.mgle.level_engine import MacroLevelEngine

def build_mgle_snapshot(now_dt: datetime, mkt_path: str, db: MGLEDatabase) -> MGLESnapshot:
    """Computes master MGLE Snapshot in SHADOW MODE."""
    now_ts = int(now_dt.timestamp())
    snap = MGLESnapshot(timestamp=now_ts, symbol="XAUUSD", shadow_mode=True)
    
    # 1. Read market snapshot if available to get spot price & ATR
    spot_price = 4348.0 # Default fallback
    atr14 = 12.50       # Default fallback
    if os.path.exists(mkt_path):
        try:
            with open(mkt_path, 'r') as f:
                for line in f:
                    if '=' in line:
                        k, v = line.strip().split('=', 1)
                        if k == 'close': spot_price = float(v)
                        elif k == 'atr14': atr14 = float(v)
        except Exception:
            pass

    # 2. Query PIT Real Yields & USD Index from database
    ry_obs = db.query_pit_series("TREASURY_10Y_YIELD", now_ts, limit=50)
    usd_obs = db.query_pit_series("DXY_INDEX", now_ts, limit=50)

    if ry_obs:
        ry_cur = ry_obs[0].value
        ry_hist = [o.value for o in ry_obs]
        ry_res = MacroEngines.compute_real_yield_engine(ry_cur, ry_hist)
        snap.real_yield_z = ry_res['real_yield_z']

    if usd_obs:
        usd_cur = usd_obs[0].value
        usd_hist = [o.value for o in usd_obs]
        usd_res = MacroEngines.compute_usd_engine(usd_cur, usd_hist)
        snap.usd_index_z = usd_res['usd_index_z']

    # 3. Query CFTC Managed Money Net Positioning
    cftc_obs = db.query_pit_series("CFTC_GOLD_MANAGED_MONEY_NET", now_ts, limit=156) # 3 years
    if cftc_obs:
        cftc_cur = cftc_obs[0].value
        cftc_hist = [o.value for o in cftc_obs]
        cftc_res = CFTCEngine.compute_positioning_bands(cftc_cur, cftc_hist)
        snap.cftc_net_percentile = cftc_res['percentile']
        snap.cftc_position_extreme = cftc_res['extreme_state']

    # 4. Compute Serious Macro Levels (Shadow Mode)
    lvl_weekly_high = MacroLevelEngine.construct_macro_level(
        level_id="ML_WEEKLY_HIGH",
        price_center=spot_price + 35.0,
        zone_width_dollars=10.0,
        current_price=spot_price,
        atr=atr14,
        source_type="WEEKLY_EXTREME",
        time_horizon="WEEKLY",
        creation_ts=now_ts - 86400 * 3, # 3 days old
        now_ts=now_ts,
        structural_evidence=0.85,
        macro_evidence=0.70,
        options_evidence=0.60,
        retest_count=2,
        reaction_count=1
    )
    
    lvl_weekly_low = MacroLevelEngine.construct_macro_level(
        level_id="ML_WEEKLY_LOW",
        price_center=spot_price - 35.0,
        zone_width_dollars=10.0,
        current_price=spot_price,
        atr=atr14,
        source_type="WEEKLY_EXTREME",
        time_horizon="WEEKLY",
        creation_ts=now_ts - 86400 * 3,
        now_ts=now_ts,
        structural_evidence=0.85,
        macro_evidence=0.70,
        options_evidence=0.60,
        retest_count=1,
        reaction_count=1
    )
    
    snap.active_macro_levels = [lvl_weekly_high, lvl_weekly_low]
    
    # Categorize Macro Regime Label
    if snap.real_yield_z <= -1.0 and snap.usd_index_z <= -1.0:
        snap.macro_regime_label = "STRONGLY_SUPPORTIVE"
    elif snap.real_yield_z >= 1.0 and snap.usd_index_z >= 1.0:
        snap.macro_regime_label = "STRONGLY_BEARISH"
    elif (snap.real_yield_z * snap.usd_index_z) < -0.5:
        snap.macro_regime_label = "CONFLICTED"
    else:
        snap.macro_regime_label = "NEUTRAL"

    return snap

def write_mgle_bridge_file(out_path: str, snap: MGLESnapshot):
    """Writes key=value formatted bridge file for MQL5 consumption."""
    try:
        with open(out_path, 'w') as f:
            f.write(f"schema_version={snap.schema_version}\n")
            f.write(f"timestamp={snap.timestamp}\n")
            f.write(f"symbol={snap.symbol}\n")
            f.write(f"macro_regime={snap.macro_regime_label}\n")
            f.write(f"macro_confidence={snap.macro_confidence:.2f}\n")
            f.write(f"data_coverage_pct={snap.data_coverage_pct:.1f}\n")
            f.write(f"real_yield_z={snap.real_yield_z:.4f}\n")
            f.write(f"usd_index_z={snap.usd_index_z:.4f}\n")
            f.write(f"cftc_net_percentile={snap.cftc_net_percentile:.1f}\n")
            f.write(f"cftc_position_extreme={snap.cftc_position_extreme}\n")
            f.write(f"geo_intensity_index={snap.geo_intensity_index:.4f}\n")
            f.write(f"volatility_ratio_rv={snap.volatility_ratio_rv:.4f}\n")
            f.write(f"volatility_regime={snap.volatility_regime}\n")
            f.write(f"options_oi_conc={snap.options_oi_concentration:.4f}\n")
            f.write(f"theoretical_gex_proxy={snap.theoretical_gex_proxy:.2f}\n")
            f.write(f"zero_gamma_proxy_price={snap.zero_gamma_proxy_price:.2f}\n")
            f.write(f"active_levels_count={len(snap.active_macro_levels)}\n")
            f.write(f"shadow_mode=1\n")
    except Exception as e:
        print(f"[MGLEService] Error writing bridge file: {e}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mkt", default="C:/Users/USER/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/MQL5/Files/algomind_mkt_out.txt")
    ap.add_argument("--out", default="C:/Users/USER/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/MQL5/Files/algomind_mgle_in.txt")
    ap.add_argument("--interval", type=float, default=5.0)
    args = ap.parse_args()

    print(f"[MGLEService] Started autonomous loop. Interval={args.interval}s")
    print(f"[MGLEService] Reading market snapshot from: {args.mkt}")
    print(f"[MGLEService] Writing MGLE Shadow Context to: {args.out}")

    db = MGLEDatabase()

    while True:
        try:
            now_dt = datetime.now(timezone.utc)
            snap = build_mgle_snapshot(now_dt, args.mkt, db)
            write_mgle_bridge_file(args.out, snap)
            print(f"[{now_dt.strftime('%H:%M:%S')}] [MGLEService] Wrote snapshot: "
                  f"regime={snap.macro_regime_label} ry_z={snap.real_yield_z:.2f} "
                  f"usd_z={snap.usd_index_z:.2f} cftc_pct={snap.cftc_net_percentile:.1f}% "
                  f"levels={len(snap.active_macro_levels)} (SHADOW MODE)")
        except KeyboardInterrupt:
            print("[MGLEService] Stopped by user.")
            sys.exit(0)
        except Exception as e:
            print(f"[MGLEService] Loop error: {e}")
        time.sleep(args.interval)

if __name__ == "__main__":
    main()
