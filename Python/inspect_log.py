"""
Parse the correct MT5 tester log for DECISION records.
Uses a line-by-line approach with flexible regex.
"""
import re
from pathlib import Path

LOG_PATHS = [
    Path(r"C:\Users\USER\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\Tester\logs\20260916.log"),
    Path(r"C:\Users\USER\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Logs\20260916.log"),
    Path(r"C:\Users\USER\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\logs\20260916.log"),
]

for LOG_PATH in LOG_PATHS:
    if not LOG_PATH.exists():
        print(f"NOT FOUND: {LOG_PATH}")
        continue
    size = LOG_PATH.stat().st_size
    print(f"\n{'='*60}")
    print(f"File: {LOG_PATH}")
    print(f"Size: {size:,} bytes")
    with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    print(f"Lines: {len(lines):,}")

    # Count occurrences of key strings
    dec_count   = sum(1 for l in lines if "[DECISION]" in l)
    action_count= sum(1 for l in lines if "[ACTION_TRADE]" in l or "ACTION_TRADE" in l)
    minlot_count= sum(1 for l in lines if "MIN_LOT" in l)
    score_count = sum(1 for l in lines if "reason=" in l)
    algomind_ct = sum(1 for l in lines if "[AlgoMind]" in l or "AlgoMind" in l)

    print(f"Lines with [DECISION]     : {dec_count:,}")
    print(f"Lines with ACTION_TRADE   : {action_count:,}")
    print(f"Lines with MIN_LOT        : {minlot_count:,}")
    print(f"Lines with reason=        : {score_count:,}")
    print(f"Lines with AlgoMind       : {algomind_ct:,}")

    # Print first 5 DECISION lines raw
    if dec_count > 0:
        print("\nFirst 5 [DECISION] raw lines:")
        shown = 0
        for i, l in enumerate(lines):
            if "[DECISION]" in l:
                print(f"  [{i}] {repr(l[:200])}")
                if i+1 < len(lines):
                    print(f"  [{i+1}] {repr(lines[i+1][:200])}")
                shown += 1
                if shown >= 5:
                    break
    else:
        print("\nNo [DECISION] lines found. Showing first 5 lines:")
        for l in lines[:5]:
            print(f"  {repr(l[:200])}")
