#ifndef AMIGO_INCLUDE_EXECUTION_ENGINE_MQH
#define AMIGO_INCLUDE_EXECUTION_ENGINE_MQH
//+------------------------------------------------------------------+
//| ExecutionEngine.mqh - OrderCheck, order send, fill verification  |
//+------------------------------------------------------------------+
#property strict

#include <Contracts header.mqh>
#include <Configuration.mqh>
#include <Logger.mqh>
#include <Account Execution Engine.mqh>
#include <Trade/Trade.mqh>
#include <TransactionRecon.mqh>

#ifndef AMIGO_MAX_ESTIMATED_STOP_LOSS_PERCENT
#define AMIGO_MAX_ESTIMATED_STOP_LOSS_PERCENT 2.0
#endif

//--- Global CTrade instance (shared with PositionManager)
CTrade g_trade;

bool ExecutionHasManagedWorkingOrder(const AmigoConfig &cfg)
{
   for(int i=OrdersTotal()-1;i>=0;i--)
   {
      ulong ticket=OrderGetTicket(i);
      if(ticket==0) return true; // incomplete enumeration is unsafe
      if(OrderGetString(ORDER_SYMBOL)==cfg.symbol &&
         (ulong)OrderGetInteger(ORDER_MAGIC)==cfg.magic_number)
         return true;
   }
   return false;
}

// Prevent a fresh entry from merging independent horizon state on netting
// accounts. Broker enumeration is a point-in-time check, not an atomic lock.
bool ExecutionSymbolAdmissionAllows(const string symbol,const ulong magic,string &reason)
{
   long mode=AccountInfoInteger(ACCOUNT_MARGIN_MODE);
   bool hedging=(mode==ACCOUNT_MARGIN_MODE_RETAIL_HEDGING);
   if(!hedging && mode!=ACCOUNT_MARGIN_MODE_RETAIL_NETTING && mode!=ACCOUNT_MARGIN_MODE_EXCHANGE)
   { reason="ACCOUNT_MARGIN_MODE_UNKNOWN"; return false; }
   if(!hedging)
   {
      for(int i=PositionsTotal()-1;i>=0;i--)
      {
         if(PositionGetTicket(i)==0)
         { reason="POSITION_ENUMERATION_INCOMPLETE"; return false; }
         if(PositionGetString(POSITION_SYMBOL)==symbol)
         { reason="NETTING_SYMBOL_POSITION_EXISTS"; return false; }
      }
   }
   for(int i=OrdersTotal()-1;i>=0;i--)
   {
      if(OrderGetTicket(i)==0)
      { reason="ORDER_ENUMERATION_INCOMPLETE"; return false; }
      if(OrderGetString(ORDER_SYMBOL)==symbol &&
         (!hedging || (ulong)OrderGetInteger(ORDER_MAGIC)==magic))
      { reason="SYMBOL_WORKING_ORDER_UNRESOLVED"; return false; }
   }
   return true;
}

// Best-effort containment for an order acknowledged as placed but not yet
// reconciled to a fill. Cancellation is attempted only for the exact returned
// ticket after verifying that the active order belongs to this symbol/magic.
// The caller must remain quarantined regardless of this helper's result:
// cancellation can race with execution and is not proof that no fill occurred.
string ExecutionCancelPlacedOrder(const ulong ticket,const string symbol,const ulong magic)
{
   if(ticket==0) return "NO_ORDER_TICKET";
   if(!OrderSelect(ticket)) return "ORDER_NOT_ACTIVE_OR_UNKNOWN";

   string active_symbol=OrderGetString(ORDER_SYMBOL);
   ulong active_magic=(ulong)OrderGetInteger(ORDER_MAGIC);
   if(active_symbol!=symbol || active_magic!=magic)
      return "ORDER_IDENTITY_MISMATCH";

   g_trade.SetExpertMagicNumber(magic);
   bool cancel_call_ok=g_trade.OrderDelete(ticket);
   uint cancel_retcode=g_trade.ResultRetcode();
   if(!cancel_call_ok || cancel_retcode!=TRADE_RETCODE_DONE)
      return StringFormat("CANCEL_UNCONFIRMED_CALL=%d_RETCODE=%u",
                          (int)cancel_call_ok,cancel_retcode);

   // Even a successful remove response cannot establish whether the order
   // filled immediately before cancellation. Keep the caller's outcome unknown.
   return "CANCEL_ACCEPTED_OUTCOME_STILL_UNCERTAIN";
}

struct ExecutionResult
{
   bool     accepted;
   bool     shadow_evaluated;
   double   shadow_entry;
   double   shadow_volume;
   bool     risk_guard_blocked;
   bool     outcome_uncertain;
   ulong    order_ticket;
   ulong    deal_ticket;
   ulong    position_id;
   double   fill_price;
   double   fill_volume;
   uint     retcode;
   string   comment;
};

//--- Spread gate per Math Spec §25
bool SpreadOK(string symbol, double atr, const AmigoConfig &cfg, string &reason)
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

bool ExecutionOnGrid(const double value,const double step)
{
   if(!MathIsValidNumber(value) || value<=0.0 ||
      !MathIsValidNumber(step) || step<=0.0) return false;
   double units=value/step;
   if(!MathIsValidNumber(units) || units<=0.0) return false;
   double nearest=MathRound(units);
   double tolerance=MathMax(0.000000001,MathAbs(nearest)*0.000000000001);
   return (MathAbs(units-nearest)<=tolerance);
}

double ExecutionVolumeCeilToStep(const double minimum,const double step)
{
   if(!MathIsValidNumber(minimum) || minimum<=0.0 ||
      !MathIsValidNumber(step) || step<=0.0) return 0.0;
   double ratio=minimum/step;
   if(!MathIsValidNumber(ratio) || ratio<=0.0) return 0.0;
   double nearest=MathRound(ratio);
   double tolerance=MathMax(0.000000000001,MathAbs(ratio)*0.000000000001);
   double steps=(MathAbs(ratio-nearest)<=tolerance)?nearest:MathCeil(ratio);
   double volume=steps*step;
   double volume_tolerance=MathMax(0.000000000001,MathAbs(minimum)*0.000000000001);
   while(volume<minimum-volume_tolerance) { steps+=1.0; volume=steps*step; }
   return (MathIsValidNumber(volume) && volume>0.0)?volume:0.0;
}

double ExecutionVolumeFloorToStep(const double maximum,const double step)
{
   if(!MathIsValidNumber(maximum) || maximum<=0.0 ||
      !MathIsValidNumber(step) || step<=0.0) return 0.0;
   double steps=MathFloor(maximum/step);
   if(!MathIsValidNumber(steps) || steps<0.0) return 0.0;
   double volume=steps*step;
   while(volume>maximum && steps>0.0) { steps-=1.0; volume=steps*step; }
   return (MathIsValidNumber(volume) && volume>0.0)?volume:0.0;
}

bool ExecutionVolumeValid(const string symbol,const double volume,string &reason)
{
   reason="";
   double minimum=SymbolInfoDouble(symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(symbol,SYMBOL_VOLUME_STEP);
   if(symbol=="" || !MathIsValidNumber(volume) || volume<=0.0 ||
      !MathIsValidNumber(minimum) || minimum<=0.0 ||
      !MathIsValidNumber(maximum) || maximum<minimum ||
      !MathIsValidNumber(step) || step<=0.0)
   { reason="BROKER_VOLUME_METADATA_INVALID"; return false; }
   double volume_tolerance=MathMax(0.000000000001,MathAbs(minimum)*0.000000000001);
   double minimum_valid=ExecutionVolumeCeilToStep(minimum,step);
   double maximum_valid=ExecutionVolumeFloorToStep(maximum,step);
   if(volume<minimum-volume_tolerance || volume>maximum+volume_tolerance ||
      minimum_valid<=0.0 || maximum_valid<minimum_valid ||
      volume<minimum_valid-volume_tolerance || !ExecutionOnGrid(volume,step))
   { reason="REQUEST_VOLUME_OUTSIDE_BROKER_GRID"; return false; }
   return true;
}

bool ExecutionPricesValid(const string symbol,const int direction,const double price,
                          const double stop,const double target,string &reason)
{
   reason="";
   double tick_size=SymbolInfoDouble(symbol,SYMBOL_TRADE_TICK_SIZE);
   if(symbol=="" || (direction!=+1 && direction!=-1) ||
      !MathIsValidNumber(tick_size) || tick_size<=0.0 ||
      !ExecutionOnGrid(price,tick_size) || !ExecutionOnGrid(stop,tick_size) ||
      !ExecutionOnGrid(target,tick_size))
   { reason="REQUEST_PRICE_TICK_GRID_INVALID"; return false; }
   if((direction==+1 && !(stop<price && target>price)) ||
      (direction==-1 && !(stop>price && target<price)))
   { reason="REQUEST_GEOMETRY_CROSSED_CURRENT_QUOTE"; return false; }
   return true;
}

bool ExecutionSelectFilling(const string symbol,ENUM_ORDER_TYPE_FILLING &policy,string &reason)
{
   reason="";
   policy=ORDER_FILLING_FOK;
   if(symbol=="") { reason="FILLING_SYMBOL_EMPTY"; return false; }
   uint allowed=(uint)SymbolInfoInteger(symbol,SYMBOL_FILLING_MODE);
   long execution=(long)SymbolInfoInteger(symbol,SYMBOL_TRADE_EXEMODE);
   if(execution!=SYMBOL_TRADE_EXECUTION_REQUEST &&
      execution!=SYMBOL_TRADE_EXECUTION_INSTANT &&
      execution!=SYMBOL_TRADE_EXECUTION_MARKET &&
      execution!=SYMBOL_TRADE_EXECUTION_EXCHANGE)
   { reason="TRADE_EXECUTION_MODE_UNKNOWN"; return false; }

   // AMIGO cannot yet durably aggregate asynchronous/multiple deal fills.
   // RETURN leaves the unfilled remainder active after a partial execution,
   // which can later create exposure that is absent from the registered
   // position lifecycle. Prefer FOK where execution semantics guarantee it;
   // for Market/Exchange execution require broker-advertised FOK and otherwise
   // reject before sending. Do not silently fall back to IOC or RETURN.
   if(execution==SYMBOL_TRADE_EXECUTION_REQUEST ||
      execution==SYMBOL_TRADE_EXECUTION_INSTANT)
   {
      policy=ORDER_FILLING_FOK;
      return true;
   }
   if((allowed & SYMBOL_FILLING_FOK)!=0)
   { policy=ORDER_FILLING_FOK; return true; }
   reason="NO_SUPPORTED_FULL_FILL_POLICY";
   return false;
}

//--- Intent validation per Math Spec §17
bool ValidateIntent(const TradeIntent &ti, const AmigoConfig &cfg, string &reason)
{
   reason = "";
   if(ti.horizon!=HORIZON_SCALPING && ti.horizon!=HORIZON_INTRADAY &&
      ti.horizon!=HORIZON_SWING)
   {
      reason="INVALID_HORIZON";
      return false;
   }
   if(!MathIsValidNumber(ti.entry_reference) || ti.entry_reference<=0.0 ||
      !MathIsValidNumber(ti.stop) || !MathIsValidNumber(ti.target))
   {
      reason="INVALID_INTENT_PRICE";
      return false;
   }

   if(ti.schema_version!=Amigo_SCHEMA_VERSION || ti.intent_id<=0 ||
      ti.snapshot_id!=ti.intent_id || ti.decision_id<=0 ||
      ti.signal_id<=0 || ti.idempotency_key<=0 || ti.submission_attempt_id<=0 ||
      ti.symbol=="" || ti.symbol!=cfg.symbol)
   {
      reason="INVALID_INTENT_IDENTITY";
      return false;
   }
   datetime now=TimeCurrent();
   if(now<=0 || ti.timestamp<=0 || ti.timestamp>now || ti.expiry<=ti.timestamp)
   {
      reason="INVALID_INTENT_TIME_WINDOW";
      return false;
   }
   if(ti.expiry <= now)
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

bool ExecutionDealMatchesIntent(const ulong deal_ticket,const TradeIntent &ti,
                                const MqlTradeRequest &request,const ulong expected_order,
                                string &reason)
{
   reason="";
   if(deal_ticket==0 || !HistoryDealSelect(deal_ticket))
   {
      reason="DEAL_NOT_SELECTABLE";
      return false;
   }
   long magic=0,type=0,entry=0,deal_order=0,stamp=0;
   string symbol="";
   if(!HistoryDealGetInteger(deal_ticket,DEAL_MAGIC,magic) ||
      !HistoryDealGetInteger(deal_ticket,DEAL_TYPE,type) ||
      !HistoryDealGetInteger(deal_ticket,DEAL_ENTRY,entry) ||
      !HistoryDealGetInteger(deal_ticket,DEAL_ORDER,deal_order) ||
      !HistoryDealGetInteger(deal_ticket,DEAL_TIME,stamp) ||
      !HistoryDealGetString(deal_ticket,DEAL_SYMBOL,symbol))
   {
      reason="DEAL_PROPERTIES_UNAVAILABLE";
      return false;
   }
   if(ti.timestamp<=0 || stamp<(long)ti.timestamp)
   {
      reason="DEAL_PRECEDES_INTENT";
      return false;
   }
   if(magic!=(long)request.magic)
   {
      reason="DEAL_MAGIC_MISMATCH";
      return false;
   }
   if(symbol!=ti.symbol)
   {
      reason="DEAL_SYMBOL_MISMATCH";
      return false;
   }
   long expected_type=(ti.direction==+1)?DEAL_TYPE_BUY:DEAL_TYPE_SELL;
   if(type!=expected_type)
   {
      reason="DEAL_DIRECTION_MISMATCH";
      return false;
   }
   // This EA only admits a fresh entry. Netting reversals/close deals are not
   // accepted as fills for a new intent, even if other fields happen to match.
   if(entry!=DEAL_ENTRY_IN)
   {
      reason="DEAL_ENTRY_NOT_OPEN";
      return false;
   }
   if(expected_order==0)
   {
      reason="EXPECTED_ORDER_MISSING";
      return false;
   }
   if(deal_order<=0 || (ulong)deal_order!=expected_order)
   {
      reason="DEAL_ORDER_MISMATCH";
      return false;
   }
   return true;
}

// Require matching terminal order evidence before calling a full fill final.
// This reads one exact ticket; missing history remains unresolved, never no-fill.
bool ExecutionCompletedOrderMatches(const TradeIntent &ti,const MqlTradeRequest &request,
                                    const ulong order,const ulong position,const double tolerance,
                                    string &reason)
{
   reason="";
   if(order==0 || position==0 || !MathIsValidNumber(tolerance) || tolerance<=0.0 ||
      !HistoryOrderSelect(order))
   { reason="COMPLETED_ORDER_UNAVAILABLE"; return false; }
   long magic=0,type=0,state=0,position_id=0,setup=0,done=0,filling=0;
   string symbol="";
   double initial=0.0,remaining=0.0;
   if(!HistoryOrderGetInteger(order,ORDER_MAGIC,magic) ||
      !HistoryOrderGetInteger(order,ORDER_TYPE,type) ||
      !HistoryOrderGetInteger(order,ORDER_STATE,state) ||
      !HistoryOrderGetInteger(order,ORDER_POSITION_ID,position_id) ||
      !HistoryOrderGetInteger(order,ORDER_TIME_SETUP,setup) ||
      !HistoryOrderGetInteger(order,ORDER_TIME_DONE,done) ||
      !HistoryOrderGetInteger(order,ORDER_TYPE_FILLING,filling) ||
      !HistoryOrderGetString(order,ORDER_SYMBOL,symbol) ||
      !HistoryOrderGetDouble(order,ORDER_VOLUME_INITIAL,initial) ||
      !HistoryOrderGetDouble(order,ORDER_VOLUME_CURRENT,remaining))
   { reason="COMPLETED_ORDER_PROPERTIES_UNAVAILABLE"; return false; }
   if(magic!=(long)request.magic || type!=(long)request.type || symbol!=ti.symbol ||
      position_id<=0 || (ulong)position_id!=position || filling!=(long)request.type_filling ||
      state!=ORDER_STATE_FILLED || ti.timestamp<=0 || setup<(long)ti.timestamp || done<setup)
   { reason="COMPLETED_ORDER_IDENTITY_OR_STATE_CONFLICT"; return false; }
   if(!MathIsValidNumber(initial) || initial<=0.0 || !MathIsValidNumber(remaining) ||
      remaining!=0.0 || !MathIsValidNumber(request.volume) || request.volume<=0.0 ||
      MathAbs(initial-request.volume)>tolerance)
   { reason="COMPLETED_ORDER_QUANTITY_CONFLICT"; return false; }
   return true;
}

// Aggregate only the already-visible opening deals of this exact order.
// A bounded history snapshot is not proof that no later deal can arrive.
bool ExecutionAggregateOrderDeals(const TradeIntent &ti,const MqlTradeRequest &request,
                                  const ulong order,const ulong position,const ulong seed_deal,
                                  double &volume,double &price,string &reason)
{
   reason="";
   if(order==0 || position==0 || seed_deal==0 || !HistorySelectByPosition(position))
   { reason="ORDER_DEAL_HISTORY_UNAVAILABLE"; return false; }
   int count=HistoryDealsTotal();
   // Operational resource bound: reject instead of allocating unbounded history.
   if(count<=0 || count>4096)
   { reason="ORDER_DEAL_HISTORY_COUNT_UNSUPPORTED"; return false; }
   ulong tickets[];
   if(ArrayResize(tickets,count)!=count)
   { reason="ORDER_DEAL_ALLOCATION_FAILED"; return false; }
   for(int i=0;i<count;i++)
   {
      tickets[i]=HistoryDealGetTicket(i);
      if(tickets[i]==0)
      { reason="ORDER_DEAL_ENUMERATION_FAILED"; return false; }
   }
   if(!ArraySort(tickets))
   { reason="ORDER_DEAL_SORT_FAILED"; return false; }
   double total_volume=0.0,weighted_price=0.0;
   bool seed_found=false;
   long expected_type=(ti.direction==+1)?DEAL_TYPE_BUY:DEAL_TYPE_SELL;
   for(int i=0;i<count;i++)
   {
      if(i>0 && tickets[i]==tickets[i-1])
      { reason="ORDER_DEAL_DUPLICATE"; return false; }
      ulong ticket=tickets[i];
      long deal_order=0,deal_position=0,magic=0,type=0,entry=0,stamp=0;
      string symbol="";
      double deal_volume=0.0,deal_price=0.0;
      // Do not call HistoryDealSelect here: it resets the selected deal list.
      if(!HistoryDealGetInteger(ticket,DEAL_ORDER,deal_order) ||
         !HistoryDealGetInteger(ticket,DEAL_POSITION_ID,deal_position) ||
         !HistoryDealGetInteger(ticket,DEAL_MAGIC,magic) ||
         !HistoryDealGetInteger(ticket,DEAL_TYPE,type) ||
         !HistoryDealGetInteger(ticket,DEAL_ENTRY,entry) ||
         !HistoryDealGetInteger(ticket,DEAL_TIME,stamp) ||
         !HistoryDealGetString(ticket,DEAL_SYMBOL,symbol) ||
         !HistoryDealGetDouble(ticket,DEAL_VOLUME,deal_volume) ||
         !HistoryDealGetDouble(ticket,DEAL_PRICE,deal_price))
      { reason="ORDER_DEAL_PROPERTIES_UNAVAILABLE"; return false; }
      if(deal_order<=0 || (ulong)deal_order!=order || deal_position<=0 ||
         (ulong)deal_position!=position || magic!=(long)request.magic ||
         symbol!=ti.symbol || type!=expected_type || entry!=DEAL_ENTRY_IN ||
         stamp<(long)ti.timestamp)
      { reason="ORDER_DEAL_IDENTITY_OR_LIFECYCLE_CONFLICT"; return false; }
      if(!MathIsValidNumber(deal_volume) || deal_volume<=0.0 ||
         !MathIsValidNumber(deal_price) || deal_price<=0.0)
      { reason="ORDER_DEAL_QUANTITY_INVALID"; return false; }
      total_volume+=deal_volume;
      weighted_price+=deal_volume*deal_price;
      if(!MathIsValidNumber(total_volume) || !MathIsValidNumber(weighted_price))
      { reason="ORDER_DEAL_AGGREGATE_INVALID"; return false; }
      if(ticket==seed_deal) seed_found=true;
   }
   if(!seed_found || total_volume<=0.0 || HistoryDealsTotal()!=count)
   { reason="ORDER_DEAL_SNAPSHOT_INCOMPLETE"; return false; }
   double average=weighted_price/total_volume;
   if(!MathIsValidNumber(average) || average<=0.0)
   { reason="ORDER_DEAL_AVERAGE_INVALID"; return false; }
   volume=total_volume;
   price=average;
   return true;
}

// Only server responses that explicitly reject/cancel this request may be
// treated as a retryable no-fill outcome. TIMEOUT, CONNECTION, ERROR, LOCKED,
// and any future/unrecognized retcode stay ambiguous and must quarantine the
// opportunity rather than silently releasing it for a duplicate submission.
bool ExecutionRetcodeIsDefinitiveRejection(const uint retcode)
{
   return ReconRetcodeIsDefinitiveRejection(retcode);
}

//--- OrderCheck then OrderSend (per D4 REQ-014 / D3 §17)
ExecutionResult ExecuteIntent(const TradeIntent &ti, double lots,
                              const AmigoConfig &cfg,const double stop_distance,
                              const double authorized_risk_pct,
                              const double max_allowed_distortion,
                              const double management_atr)
{
   ExecutionResult r;
   r.accepted          = false;
   r.shadow_evaluated  = false;
   r.shadow_entry      = 0.0;
   r.shadow_volume     = 0.0;
   r.risk_guard_blocked = false;
   r.outcome_uncertain = false;
   r.order_ticket = 0;
   r.deal_ticket  = 0;
   r.position_id  = 0;
   r.fill_price   = 0.0;
   r.fill_volume  = 0.0;
   r.retcode      = 0;
   r.comment      = "";

   string preflight_reason="";
   if(!ValidateIntent(ti,cfg,preflight_reason))
   {
      r.risk_guard_blocked=true;
      r.comment=preflight_reason;
      return r;
   }
   if(!ExecutionVolumeValid(ti.symbol,lots,preflight_reason))
   {
      r.risk_guard_blocked=true;
      r.comment=preflight_reason;
      return r;
   }

   if(!cfg.shadow_only && AMIGO_LIVE_EXECUTION_READY==0 && !MQLInfoInteger(MQL_TESTER))
   {
      r.risk_guard_blocked=true;
      r.comment="LIVE_EXECUTION_BLOCKED_UNRECONCILED_ORDER_LIFECYCLE";
      return r;
   }

   // The final quote check must receive the exact effective risk policy that
   // authorized sizing. Missing values fail closed; a shared execution entry
   // point must not silently fall back to the unthrottled configuration risk.
   if(!MathIsValidNumber(authorized_risk_pct) || authorized_risk_pct<=0.0 ||
      authorized_risk_pct>AMIGO_MAX_ESTIMATED_STOP_LOSS_PERCENT ||
      !MathIsValidNumber(max_allowed_distortion) || max_allowed_distortion<=0.0)
   {
      r.risk_guard_blocked=true;
      r.comment="FINAL_RISK_POLICY_UNAVAILABLE";
      return r;
   }

   MqlTradeRequest req;
   ZeroMemory(req);
   MqlTradeResult res;
   ZeroMemory(res);

   req.action       = TRADE_ACTION_DEAL;
   req.symbol       = ti.symbol;
   req.volume       = lots;
   req.type         = (ti.direction == +1) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   MqlTick execution_quote;
   ZeroMemory(execution_quote);
   if(!SymbolInfoTick(ti.symbol,execution_quote) ||
      !MathIsValidNumber(execution_quote.bid) || execution_quote.bid<=0.0 ||
      !MathIsValidNumber(execution_quote.ask) || execution_quote.ask<execution_quote.bid ||
      execution_quote.time<=0 || TimeCurrent()<execution_quote.time ||
      cfg.stale_threshold_s<=0 ||
      (TimeCurrent()-execution_quote.time)>cfg.stale_threshold_s)
   {
      r.risk_guard_blocked=true;
      r.comment="EXECUTION_QUOTE_UNAVAILABLE_OR_STALE";
      return r;
   }
   double execution_spread=execution_quote.ask-execution_quote.bid;
   double execution_point=SymbolInfoDouble(ti.symbol,SYMBOL_POINT);
   if(!MathIsValidNumber(execution_point) || execution_point<=0.0 ||
      (cfg.max_spread_points>0.0 && execution_spread/execution_point>cfg.max_spread_points) ||
      (cfg.max_spread_atr_pct>0.0 &&
       (!MathIsValidNumber(stop_distance) || stop_distance<=0.0 ||
        execution_spread>cfg.max_spread_atr_pct*stop_distance)))
   {
      r.risk_guard_blocked=true;
      r.comment="EXECUTION_SPREAD_LIMIT_EXCEEDED_OR_INVALID";
      return r;
   }
   req.price        = (ti.direction == +1) ? execution_quote.ask : execution_quote.bid;
   req.sl           = ti.stop;
   req.tp           = ti.target;
   req.deviation    = 20;
   req.magic        = (cfg.magic_number > 0) ? cfg.magic_number : 20260908;
   req.comment      = StringFormat("Amigo-%I64d", ti.intent_id);

   if(!ExecutionPricesValid(ti.symbol,ti.direction,req.price,req.sl,req.tp,preflight_reason))
   {
      r.risk_guard_blocked=true;
      r.comment=preflight_reason;
      return r;
   }

   if(!ExecutionSymbolAdmissionAllows(ti.symbol,req.magic,preflight_reason))
   {
      r.risk_guard_blocked=true;
      r.comment=preflight_reason;
      return r;
   }

   // Re-check the approved estimated stop-loss ceiling using the exact
   // request quote and rounded volume immediately before OrderCheck/OrderSend.
   // The earlier sizing check uses the strategy's quote; execution refreshes
   // bid/ask, so the two values can differ. This estimate does not bound gaps,
   // fill slippage, commission, or a later stop change.
   double request_stop_profit = 0.0;
   double request_equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(!MathIsValidNumber(request_equity) || request_equity <= 0.0 ||
      !MathIsValidNumber(req.volume) || req.volume <= 0.0 ||
      !MathIsValidNumber(req.price) || req.price <= 0.0 ||
      !MathIsValidNumber(req.sl) || req.sl <= 0.0 ||
      !OrderCalcProfit(req.type, req.symbol, req.volume, req.price, req.sl, request_stop_profit) ||
      !MathIsValidNumber(request_stop_profit) || request_stop_profit >= 0.0)
   {
      r.risk_guard_blocked = true;
      r.comment = "FINAL_REQUEST_STOP_RISK_UNAVAILABLE";
      return r;
   }
   double request_stop_risk_pct = (-request_stop_profit / request_equity) * 100.0;
   if(!MathIsValidNumber(request_stop_risk_pct) ||
      request_stop_risk_pct > AMIGO_MAX_ESTIMATED_STOP_LOSS_PERCENT)
   {
      r.risk_guard_blocked = true;
      r.comment = "FINAL_REQUEST_STOP_RISK_ABOVE_2PCT";
      return r;
   }
   double request_target_risk=request_equity*(authorized_risk_pct/100.0);
   // Positive finite factors can still underflow to zero. Validate the
   // denominator before division; a later check cannot catch a runtime fault.
   if(!MathIsValidNumber(request_target_risk) || request_target_risk<=0.0)
   {
      r.risk_guard_blocked=true;
      r.comment="FINAL_REQUEST_TARGET_RISK_INVALID";
      return r;
   }
   double request_risk_distortion=(-request_stop_profit)/request_target_risk;
   if(!MathIsValidNumber(request_risk_distortion) ||
      request_risk_distortion>(max_allowed_distortion+0.00001))
   {
      r.risk_guard_blocked=true;
      r.comment="FINAL_REQUEST_RISK_DISTORTION_ABOVE_POLICY";
      return r;
   }
   double existing_account_stop_risk=0.0;
   string aggregate_risk_reason="";
   if(!AccountEstimatedStopRisk(existing_account_stop_risk,aggregate_risk_reason))
   {
      r.risk_guard_blocked=true;
      r.comment="FINAL_ACCOUNT_EXPOSURE_UNKNOWN:"+aggregate_risk_reason;
      return r;
   }
   double aggregate_risk_pct=(existing_account_stop_risk-request_stop_profit)/request_equity*100.0;
   if(!MathIsValidNumber(aggregate_risk_pct) ||
      aggregate_risk_pct>AMIGO_MAX_ESTIMATED_STOP_LOSS_PERCENT)
   {
      r.risk_guard_blocked=true;
      r.comment="FINAL_AGGREGATE_AMIGO_STOP_RISK_ABOVE_2PCT";
      return r;
   }

   //--- Select only a policy allowed by the symbol's execution mode.
   ENUM_ORDER_TYPE_FILLING filling_policy=ORDER_FILLING_RETURN;
   if(!ExecutionSelectFilling(ti.symbol,filling_policy,preflight_reason))
   {
      r.risk_guard_blocked=true;
      r.comment=preflight_reason;
      return r;
   }
   req.type_filling=filling_policy;

   // Check daily fill limit before any order submission
   // P0 contract: maximum 5 successful logical entries per broker/server trading day
   // Enforce before any OrderSend() call
   if(ReconIsDailyFillLimitReached(RiskServerDayBoundary()))
   {
      r.risk_guard_blocked = true;
      r.comment = "DAILY_EXECUTION_LIMIT_REACHED";
      return r;
   }

   // Risk/metadata calls may outlive the intent. Revalidate before either
   // synthetic acceptance or the disabled live path continues.
   if(!ValidateIntent(ti,cfg,preflight_reason))
   {
      r.risk_guard_blocked=true;
      r.comment="PREFLIGHT_INTENT_INVALIDATED:"+preflight_reason;
      return r;
   }

   //--- Shadow mode evaluates the deterministic risk envelope above but does
   //--- not require terminal trading permission or a broker order check.
   //--- No order API is reached on this path.
   if(cfg.shadow_only)
   {
      LogMsg(LOG_INFO, "EXEC_SHADOW", StringFormat("[SHADOW MODE EXECUTION BLOCKED] dir=%d lots=%.2f price=%.5f sl=%.5f tp=%.5f score=%.3f hyp=%d",
             ti.direction, lots, req.price, ti.stop, ti.target, ti.score, (int)ti.hypothesis));
      r.accepted    = false;
      // Synthetic lifecycle reference only: these are not broker fills.
      r.shadow_evaluated = true;
      r.shadow_entry = req.price;
      r.shadow_volume = req.volume;
      r.retcode     = 10009; // TRADE_RETCODE_DONE equivalent or custom shadow code
      r.comment     = "SHADOW_MODE_EXECUTION_BLOCKED";
      return r;
   }

   //--- OrderCheck is required only for the live path, which is compile-time
   //--- disabled until order reconciliation and restart safety are verified.
   MqlTradeCheckResult chk;
   ZeroMemory(chk);
   if(!OrderCheck(req, chk))
   {
      r.retcode = chk.retcode;
      r.comment = "ORDERCHECK_FAIL:" + chk.comment;
      return r;
   }

   // OrderCheck can block. Do not submit an expired opportunity afterward.
   if(!ValidateIntent(ti,cfg,preflight_reason))
   {
      r.risk_guard_blocked=true;
      r.comment="POST_ORDERCHECK_INTENT_INVALIDATED:"+preflight_reason;
      return r;
   }

   // Check daily fill limit before any order submission
   // P0 contract: maximum 5 successful logical entries per broker/server trading day
   // Enforce before any OrderSend() call
   if(ReconIsDailyFillLimitReached(RiskServerDayBoundary()))
   {
      r.risk_guard_blocked = true;
      r.comment = "DAILY_EXECUTION_LIMIT_REACHED";
      return r;
   }

   if(!ReconPrepareIntent(ti,req,cfg,request_equity,-request_stop_profit,
                          existing_account_stop_risk,authorized_risk_pct,max_allowed_distortion,management_atr))
   {
      r.outcome_uncertain=true;
      r.comment="PRE_SUBMISSION_JOURNAL_UNAVAILABLE";
      return r;
   }
   // Journal I/O can outlive the opportunity or an account switch. Recheck both.
   if(!ReconScopeStillCurrent(cfg) || !ValidateIntent(ti,cfg,preflight_reason))
   {
      r.outcome_uncertain=true;
      r.comment="POST_JOURNAL_INTENT_EXPIRED_RECONCILIATION_REQUIRED";
      return r;
   }
   bool send_ok=OrderSend(req, res);
   if(!ReconRecordResponse(ti.intent_id,send_ok,res))
   {
      r.order_ticket=res.order; r.deal_ticket=res.deal; r.retcode=res.retcode;
      r.outcome_uncertain=true;
      r.comment="BROKER_RESPONSE_JOURNAL_UNRESOLVED";
      return r;
   }
   if(!send_ok)
   {
      r.retcode = res.retcode;
      // Preserve all returned broker identity even when the API reports failure.
      // A nonzero ID is evidence to reconcile, not proof of a confirmed fill.
      r.order_ticket=res.order;
      r.deal_ticket=res.deal;
      r.comment = StringFormat("ORDERSEND_FAIL:request_id=%u external=%d comment=%s",
                               res.request_id,res.retcode_external,res.comment);
      // A transport/API failure does not provide durable proof that the
      // server received no request. Quarantine rather than permit a retry.
      r.outcome_uncertain = true;
      return r;
   }

   r.retcode      = res.retcode;
   r.order_ticket = res.order;
   r.deal_ticket  = res.deal;

   if(res.retcode == TRADE_RETCODE_PLACED)
   {
      // Contain a still-active order where possible, but do not treat a
      // cancellation acknowledgement as proof that no fill occurred. Keep the
      // opportunity quarantined until transaction/history reconciliation.
      string cancel_status=ExecutionCancelPlacedOrder(r.order_ticket,ti.symbol,req.magic);
      r.outcome_uncertain = true;
      r.comment = "ORDER_PLACED_UNCONFIRMED:"+cancel_status;
      return r;
   }

   if(res.retcode == TRADE_RETCODE_DONE || res.retcode == TRADE_RETCODE_DONE_PARTIAL)
   {
      string deal_match_reason="";
      if(!ExecutionDealMatchesIntent(r.deal_ticket,ti,req,r.order_ticket,deal_match_reason))
      {
         r.outcome_uncertain = true;
         r.comment = "FILL_DEAL_IDENTITY_UNVERIFIED:"+deal_match_reason;
         return r;
      }
      long deal_position_id = HistoryDealGetInteger(r.deal_ticket, DEAL_POSITION_ID);
      double deal_price=HistoryDealGetDouble(r.deal_ticket,DEAL_PRICE);
      double deal_volume=HistoryDealGetDouble(r.deal_ticket,DEAL_VOLUME);
      if(deal_position_id<=0 || deal_price<=0.0 || deal_volume<=0.0 ||
         !MathIsValidNumber(deal_price) || !MathIsValidNumber(deal_volume))
      {
         r.outcome_uncertain = true;
         r.comment = "FILL_IDENTITY_OR_QUANTITY_INVALID";
         return r;
      }
      // Prefer the broker-history deal's actual price/volume over the
      // aggregate request response. Expand to the complete visible order-deal
      // snapshot below; disagreement still keeps the order quarantined.
      r.fill_price=deal_price;
      r.fill_volume=deal_volume;
      r.position_id = (ulong)deal_position_id;
      r.accepted = true;
      string aggregate_reason="";
      if(!ExecutionAggregateOrderDeals(ti,req,r.order_ticket,r.position_id,r.deal_ticket,
                                       r.fill_volume,r.fill_price,aggregate_reason))
      {
         // Preserve the individually proven seed deal for containment, but do
         // not approve or release the unresolved order on incomplete history.
         r.outcome_uncertain=true;
         r.comment="ORDER_DEAL_AGGREGATION_UNRESOLVED:"+aggregate_reason;
         return r;
      }
      double volume_tolerance=MathMax(0.00000001,SymbolInfoDouble(ti.symbol,SYMBOL_VOLUME_STEP)*0.000001);
      bool response_mismatch=!MathIsValidNumber(res.volume) || res.volume<=0.0 ||
                              MathAbs(res.volume-r.fill_volume)>volume_tolerance;
      bool volume_mismatch=(r.fill_volume+volume_tolerance<lots || r.fill_volume>lots+volume_tolerance ||
                            response_mismatch);
      if(res.retcode==TRADE_RETCODE_DONE_PARTIAL || volume_mismatch)
      {
         // A known partial deal is a real position that must be registered,
         // but the remainder's terminal/broker state is not resolved here.
         // Keep admission quarantined until explicit reconciliation.
         // For partial fills, increment the daily counter as they represent actual exposure
         bool increment_ok = ReconIncrementDailyFillCount(ti.intent_id);
         if(!increment_ok)
         {
            r.outcome_uncertain=true;
            r.comment="DAILY_FILL_INCREMENT_FAILED";
         }
         else
         {
            r.outcome_uncertain=true;
            r.comment="PARTIAL_FILL_REQUIRES_RECONCILIATION";
         }
      }
      else
      {
         string order_reason="";
         if(!ExecutionCompletedOrderMatches(ti,req,r.order_ticket,r.position_id,volume_tolerance,order_reason))
         {
            r.outcome_uncertain=true;
            r.comment="FILL_ORDER_COMPLETION_UNVERIFIED:"+order_reason;
         }
         else r.comment="FILL_CONFIRMED";
      }
   }
   else
   {
      // A refusal code alone cannot clear an attempt with contradictory order,
      // deal, fill-volume or external-system evidence. Do not permit re-entry.
      bool clean_rejection=ExecutionRetcodeIsDefinitiveRejection(res.retcode) &&
                           res.order==0 && res.deal==0 &&
                           MathIsValidNumber(res.volume) && res.volume==0.0 &&
                           res.retcode_external==0;
      if(clean_rejection)
      {
         r.comment=StringFormat("ORDERSEND_DEFINITIVE_REJECTION:retcode=%u comment=%s",
                                res.retcode,res.comment);
      }
      else
      {
         r.outcome_uncertain=true;
         r.comment=StringFormat("ORDERSEND_OUTCOME_UNCLASSIFIED:retcode=%u external=%d comment=%s",
                                res.retcode,res.retcode_external,res.comment);
      }
   }
   return r;
}
//+------------------------------------------------------------------+

#endif // AMIGO_INCLUDE_EXECUTION_ENGINE_MQH
