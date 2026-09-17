//+------------------------------------------------------------------+
//| ExecutionEngine.mqh - OrderCheck, order send, fill verification  |
//+------------------------------------------------------------------+
#property strict

#include <Contracts header.mqh>
#include <Configuration.mqh>
#include <Logger.mqh>
#include <Trade/Trade.mqh>

//--- Global CTrade instance (shared with PositionManager)
CTrade g_trade;

struct ExecutionResult
{
   bool     accepted;
   ulong    order_ticket;
   ulong    deal_ticket;
   ulong    position_id;
   double   fill_price;
   double   fill_volume;
   uint     retcode;
   string   comment;
};

//--- Spread gate per Math Spec §25
bool SpreadOK(string symbol, double atr, const AlgoMindConfig &cfg, string &reason)
{
   reason = "";
   double ask    = SymbolInfoDouble(symbol, SYMBOL_ASK);
   double bid    = SymbolInfoDouble(symbol, SYMBOL_BID);
   double spread = ask - bid;
   double point  = SymbolInfoDouble(symbol, SYMBOL_POINT);
   if(point <= 0.0)
   {
      reason = "INVALID_POINT";
      return false;
   }

   if(cfg.max_spread_points > 0.0)
   {
      if(spread / point > cfg.max_spread_points)
      {
         reason = "MAX_SPREAD_POINTS";
         return false;
      }
   }
   return true;
}

//--- Intent validation per Math Spec §17
bool ValidateIntent(const TradeIntent &ti, const AlgoMindConfig &cfg, string &reason)
{
   reason = "";

   if(ti.expiry < TimeCurrent())
   {
      reason = "INTENT_EXPIRED";
      return false;
   }
   if(ti.direction != +1 && ti.direction != -1)
   {
      reason = "BAD_DIRECTION";
      return false;
   }
   if(ti.stop <= 0.0 || ti.target <= 0.0)
   {
      reason = "BAD_SL_TP";
      return false;
   }
   if(ti.direction == +1 && (ti.stop >= ti.entry_reference ||
                             ti.target <= ti.entry_reference))
   {
      reason = "BAD_GEOMETRY_LONG";
      return false;
   }
   if(ti.direction == -1 && (ti.stop <= ti.entry_reference ||
                             ti.target >= ti.entry_reference))
   {
      reason = "BAD_GEOMETRY_SHORT";
      return false;
   }
   return true;
}

//--- OrderCheck then OrderSend (per D4 REQ-014 / D3 §17)
ExecutionResult ExecuteIntent(const TradeIntent &ti, double lots,
                              const AlgoMindConfig &cfg)
{
   ExecutionResult r;
   r.accepted     = false;
   r.order_ticket = 0;
   r.deal_ticket  = 0;
   r.position_id  = 0;
   r.fill_price   = 0.0;
   r.fill_volume  = 0.0;
   r.retcode      = 0;
   r.comment      = "";

   MqlTradeRequest req;
   ZeroMemory(req);
   MqlTradeResult res;
   ZeroMemory(res);

   req.action       = TRADE_ACTION_DEAL;
   req.symbol       = ti.symbol;
   req.volume       = lots;
   req.type         = (ti.direction == +1) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   req.price        = (ti.direction == +1)
                      ? SymbolInfoDouble(ti.symbol, SYMBOL_ASK)
                      : SymbolInfoDouble(ti.symbol, SYMBOL_BID);
   req.sl           = ti.stop;
   req.tp           = ti.target;
   req.deviation    = 20;
   req.magic        = 20260908;
   req.comment      = "AlgoMind";
   //--- Set appropriate order filling mode based on symbol capabilities (per MQL5 reference)
   uint filling = (uint)SymbolInfoInteger(ti.symbol, SYMBOL_FILLING_MODE);
   if((filling & SYMBOL_FILLING_FOK) != 0)
      req.type_filling = ORDER_FILLING_FOK;
   else if((filling & SYMBOL_FILLING_IOC) != 0)
      req.type_filling = ORDER_FILLING_IOC;
   else
      req.type_filling = ORDER_FILLING_RETURN;

   //--- OrderCheck first
   MqlTradeCheckResult chk;
   ZeroMemory(chk);
   if(!OrderCheck(req, chk))
   {
      r.retcode = chk.retcode;
      r.comment = "ORDERCHECK_FAIL:" + chk.comment;
      return r;
   }

   if(!OrderSend(req, res))
   {
      r.retcode = res.retcode;
      r.comment = "ORDERSEND_FAIL:" + res.comment;
      return r;
   }

   r.retcode      = res.retcode;
   r.order_ticket = res.order;
   r.deal_ticket  = res.deal;

   if(res.retcode == TRADE_RETCODE_DONE || res.retcode == TRADE_RETCODE_PLACED)
   {
      r.accepted    = true;
      r.fill_price  = res.price;
      r.fill_volume = res.volume;
      r.comment     = "OK";

      //--- Try to resolve the position ticket (may need a tick to appear)
      if(PositionSelect(ti.symbol))
         r.position_id = (ulong)PositionGetInteger(POSITION_IDENTIFIER);
   }
   else
   {
      r.comment = "RETCODE_" + IntegerToString((int)res.retcode);
   }
   return r;
}
//+------------------------------------------------------------------+