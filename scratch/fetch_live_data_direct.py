import MetaTrader5 as mt5
import pandas as pd
import sys

print("Initializing MT5 without arguments to attach to open terminal...")
if not mt5.initialize():
    print("Failed to attach to MT5 terminal:", mt5.last_error())
    sys.exit(1)

acc = mt5.account_info()
print("\n=== LIVE MT5 ACCOUNT INFO ===")
print("Login:", acc.login)
print("Server:", acc.server)
print("Balance: $", acc.balance)
print("Equity: $", acc.equity)
print("Margin Free: $", acc.margin_free)
print("Leverage: 1:", acc.leverage)
print("Currency:", acc.currency)

symbol = "XAUUSD"
if not mt5.symbol_select(symbol, True):
    symbol = "XAUUSDm"
    mt5.symbol_select(symbol, True)

s = mt5.symbol_info(symbol)
print(f"\n=== LIVE SYMBOL SPECIFICATIONS ({symbol}) ===")
print("Digits:", s.digits)
print("Point:", s.point)
print("Tick Size:", s.trade_tick_size)
print("Tick Value:", s.trade_tick_value)
print("Contract Size:", s.trade_contract_size)
print("Volume Min:", s.volume_min)
print("Volume Step:", s.volume_step)
print("Volume Max:", s.volume_max)
print("Stops Level:", s.trade_stops_level)

rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 5000)
if rates is not None and len(rates) > 0:
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    print(f"\nSuccessfully fetched {len(df)} live M5 bars from {df['time'].iloc[0]} to {df['time'].iloc[-1]}")
    df.to_csv("c:/Users/USER/Desktop/Amigo/scratch/live_xauusd_m5.csv", index=False)
    print("Saved to scratch/live_xauusd_m5.csv")

mt5.shutdown()

