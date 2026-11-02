import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import math
import sys
from datetime import datetime

# Initialize MT5
if not mt5.initialize():
    print("MT5 initialization failed:", mt5.last_error())
    sys.exit(1)

# Login to account
login = 296222644
password = "@Tony.123"
server = "Exness-Real27"

authorized = mt5.login(login=login, password=password, server=server)
if not authorized:
    print(f"Failed to connect to MT5 account {login} on {server}: {mt5.last_error()}")
    # Check current logged-in account info if already connected
    acc_info = mt5.account_info()
    if acc_info:
        print(f"Currently connected account: {acc_info.login}, server: {acc_info.server}, balance: {acc_info.balance}, equity: {acc_info.equity}, leverage: {acc_info.leverage}")
else:
    print(f"Successfully logged in to account {login} on {server}")

acc_info = mt5.account_info()
if acc_info is not None:
    print(f"\n--- ACCOUNT PROFILE ---")
    print(f"Login: {acc_info.login}")
    print(f"Server: {acc_info.server}")
    print(f"Company: {acc_info.company}")
    print(f"Currency: {acc_info.currency}")
    print(f"Balance: ${acc_info.balance:.2f}")
    print(f"Equity: ${acc_info.equity:.2f}")
    print(f"Leverage: 1:{acc_info.leverage}")
    print(f"Margin Free: ${acc_info.margin_free:.2f}")

# Look for symbol
symbols = mt5.symbols_get()
symbol_names = [s.name for s in symbols] if symbols else []
target_symbol = "XAUUSDm" if "XAUUSDm" in symbol_names else ("XAUUSD" if "XAUUSD" in symbol_names else (symbol_names[0] if symbol_names else "XAUUSD"))

sym_info = mt5.symbol_info(target_symbol)
if sym_info is None:
    mt5.symbol_select(target_symbol, True)
    sym_info = mt5.symbol_info(target_symbol)

if sym_info is not None:
    print(f"\n--- SYMBOL PROFILE ({target_symbol}) ---")
    print(f"Digits: {sym_info.digits}")
    print(f"Point: {sym_info.point}")
    print(f"Tick Size: {sym_info.trade_tick_size}")
    print(f"Tick Value: ${sym_info.trade_tick_value}")
    print(f"Contract Size: {sym_info.contract_size}")
    print(f"Volume Min: {sym_info.volume_min}")
    print(f"Volume Step: {sym_info.volume_step}")
    print(f"Volume Max: {sym_info.volume_max}")
    print(f"Stops Level: {sym_info.trade_stops_level}")

# Fetch historical data (M5 bars for 10,000 bars)
rates = mt5.copy_rates_from_pos(target_symbol, mt5.TIMEFRAME_M5, 0, 10000)
if rates is None or len(rates) == 0:
    print("Failed to fetch rates from MT5")
    mt5.shutdown()
    sys.exit(1)

df = pd.DataFrame(rates)
df['time'] = pd.to_datetime(df['time'], unit='s')
print(f"\nFetched {len(df)} M5 bars from {df['time'].iloc[0]} to {df['time'].iloc[-1]}")

mt5.shutdown()
