//+------------------------------------------------------------------+
//| Snapshot.mqh - canonical market snapshot builder                 |
//+------------------------------------------------------------------+
#property strict

#include <Contracts header.mqh>

long g_snapshot_seq = 0;

bool BuildMarketSnapshot(string symbol, MarketSnapshot &s,
                         const datetime decision_boundary=0,
                         const datetime closed_bar_time=0,
                         const long snapshot_id=0,
                         const ENUM_TIMEFRAMES decision_timeframe=PERIOD_CURRENT)
{
   s.snapshot_id   = (snapshot_id>0) ? snapshot_id : (long)TimeCurrent() * 1000 + (++g_snapshot_seq);
   s.decision_boundary=decision_boundary;
   s.closed_bar_time=closed_bar_time;
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
   s.schema_version= Amigo_SCHEMA_VERSION;

   if(symbol=="" || !MathIsValidNumber(s.bid) || !MathIsValidNumber(s.ask) ||
      !MathIsValidNumber(s.spread) || !MathIsValidNumber(s.point) ||
      !MathIsValidNumber(s.tick_size) || s.bid<=0.0 || s.ask<s.bid ||
      s.spread<0.0 || s.point<=0.0 || s.tick_size<=0.0 ||
      !MathIsValidNumber(s.contract_size) || s.contract_size<=0.0 ||
      !MathIsValidNumber(s.volume_min) || s.volume_min<=0.0 ||
      !MathIsValidNumber(s.volume_max) || s.volume_max<s.volume_min ||
      !MathIsValidNumber(s.volume_step) || s.volume_step<=0.0 ||
      s.stops_level<0.0 || s.freeze_level<0.0 ||
      !MathIsValidNumber(s.tick_value))
   {
      s.data_quality |= DQ_BROKER_INVALID | DQ_FATAL;
      return false;
   }
   if(!MathIsValidNumber(s.equity) || s.equity<=0.0 ||
      !MathIsValidNumber(s.balance) || s.balance<0.0 ||
      !MathIsValidNumber(s.margin_free))
   {
      s.data_quality |= DQ_FATAL;
      return false;
   }
   if(decision_boundary>0 || closed_bar_time>0)
   {
      if(decision_boundary<=0 || closed_bar_time<=0 || closed_bar_time>=decision_boundary ||
         iTime(symbol,decision_timeframe,0)!=decision_boundary ||
         iTime(symbol,decision_timeframe,1)!=closed_bar_time)
      {
         s.data_quality|=DQ_CLOCK_MISMATCH|DQ_FATAL;
         return false;
      }
   }
   return true;
}
//+------------------------------------------------------------------+
