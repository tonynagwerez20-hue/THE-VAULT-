//+------------------------------------------------------------------+
//| Snapshot.mqh - canonical market snapshot builder                 |
//+------------------------------------------------------------------+
#property strict

#include <Contracts header.mqh>

long g_snapshot_seq = 0;

bool BuildMarketSnapshot(string symbol, MarketSnapshot &s)
{
   s.snapshot_id   = (long)TimeCurrent() * 1000 + (++g_snapshot_seq);
   s.timestamp     = TimeCurrent();
   s.symbol        = symbol;
   s.broker_symbol = _Symbol;
   s.bid           = SymbolInfoDouble(symbol, SYMBOL_BID);
   s.ask           = SymbolInfoDouble(symbol, SYMBOL_ASK);
   s.spread        = s.ask - s.bid;
   s.digits        = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   s.point         = SymbolInfoDouble(symbol, SYMBOL_POINT);
   s.tick_size     = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
   s.tick_value    = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
   s.contract_size = SymbolInfoDouble(symbol, SYMBOL_TRADE_CONTRACT_SIZE);
   s.volume_min    = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   s.volume_max    = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
   s.volume_step   = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
   s.stops_level   = (double)SymbolInfoInteger(symbol, SYMBOL_TRADE_STOPS_LEVEL);
   s.freeze_level  = (double)SymbolInfoInteger(symbol, SYMBOL_TRADE_FREEZE_LEVEL);

   s.equity        = AccountInfoDouble(ACCOUNT_EQUITY);
   s.balance       = AccountInfoDouble(ACCOUNT_BALANCE);
   s.margin_free   = AccountInfoDouble(ACCOUNT_MARGIN_FREE);

   s.session_state = 0;
   s.data_quality  = DQ_OK;
   s.schema_version= ALGOMIND_SCHEMA_VERSION;

   if(s.bid <= 0 || s.ask <= 0 || s.point <= 0 || s.tick_size <= 0)
   {
      s.data_quality |= DQ_BROKER_INVALID | DQ_FATAL;
      return false;
   }
   return true;
}
//+------------------------------------------------------------------+