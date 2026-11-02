import MetaTrader5 as mt5
import sys

print("Initializing MT5...")
if not mt5.initialize():
    print("Initialize failed:", mt5.last_error())
    sys.exit(1)

print("Terminal info:", mt5.terminal_info())
print("Account info:", mt5.account_info())

# Try login
login = 296222644
password = "@Tony.123"
server = "Exness-Real27"

res = mt5.login(login=login, password=password, server=server)
print("Login result:", res, "Last error:", mt5.last_error())

acc = mt5.account_info()
if acc:
    print(f"Logged in: {acc.login}, balance={acc.balance}, equity={acc.equity}, leverage={acc.leverage}, currency={acc.currency}")
else:
    print("No account info after login attempt")

mt5.shutdown()
