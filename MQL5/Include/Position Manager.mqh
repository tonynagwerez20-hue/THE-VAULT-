//+------------------------------------------------------------------+
//| PositionManager.mqh - Horizon-Aware Trade Lifecycle & Management |
//| Partials, Break-Even, Dynamic Trailing, Expiry & Session Policy  |
//+------------------------------------------------------------------+
#property strict

#include <Contracts header.mqh>
#include <Configuration.mqh>
#include <Logger.mqh>
#include <Execution Engine.mqh>   // provides CTrade g_trade
#include <PositionRecovery.mqh>

struct PositionState
{
   ulong              position_id;
   int                direction;             // +1 Buy, -1 Sell
   double             entry;
   double             initial_stop;
   double             initial_target;
   double             initial_atr;
   double             initial_risk_per_unit;  // |entry - stop|
   bool               partial_done;
   double             current_stop;
   bool               be_activated;           // True once BE condition is confirmed on broker
   double             be_trigger_price;       // Horizon-specific BE trigger
   double             last_applied_stop;      // Last stop loss confirmed
   ENUM_TRAILING_MODE trailing_mode;
   ENUM_HORIZON       horizon;                // Trading horizon: SCALPING, INTRADAY, SWING
   datetime           opened;
   int                opened_bar_count;       // Bars elapsed since entry
};

PositionState g_positions[];

//--- Round a raw volume to the broker's allowed step.
double RoundVolume(string symbol, double raw)
{
   double step = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
   if(step <= 0.0) return raw;

   double rounded = MathRound(raw / step) * step;

   double vmin = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double vmax = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
   if(vmin > 0.0 && rounded < vmin) rounded = vmin;
   if(vmax > 0.0 && rounded > vmax) rounded = vmax;

   return rounded;
}

//+------------------------------------------------------------------+
//| Register a newly filled or synthetic position with its horizon   |
//+------------------------------------------------------------------+
void PositionManagerRegister(ulong pid, double entry, double stop, double target,
                             int dir, double atr, const AmigoConfig &cfg,
                             ENUM_HORIZON horiz)
{
   int n = ArraySize(g_positions);
   ArrayResize(g_positions, n + 1);

   double tp_distance = MathAbs(target - entry);
   
   //--- Horizon-specific break-even trigger calibration:
   // SCALPING: fast break-even at 33% progress (protect short-term alpha)
   // INTRADAY: standard break-even at 50% progress (preserved baseline)
   // SWING: wide structural break-even at 60% progress (allow macro breathing room)
   double be_ratio = 0.50;
   if(horiz == HORIZON_SCALPING) be_ratio = 0.33;
   else if(horiz == HORIZON_SWING) be_ratio = 0.60;

   double be_trigger = (dir == +1) ? (entry + tp_distance * be_ratio)
                                   : (entry - tp_distance * be_ratio);

   g_positions[n].position_id           = pid;
   g_positions[n].direction             = dir;
   g_positions[n].entry                 = entry;
   g_positions[n].initial_stop          = stop;
   g_positions[n].initial_target        = target;
   g_positions[n].initial_atr           = atr;
   g_positions[n].initial_risk_per_unit = MathAbs(entry - stop);
   g_positions[n].partial_done          = false;
   g_positions[n].current_stop          = stop;
   g_positions[n].be_activated          = false;
   g_positions[n].be_trigger_price      = be_trigger;
   g_positions[n].last_applied_stop     = stop;
   g_positions[n].trailing_mode         = cfg.trail_mode;
   g_positions[n].horizon               = horiz;
   g_positions[n].opened                = TimeCurrent();
   g_positions[n].opened_bar_count      = 0;

   string h_name = (horiz == HORIZON_SCALPING) ? "SCALPING" : (horiz == HORIZON_SWING) ? "SWING" : "INTRADAY";
   LogMsg(LOG_INFO, "POSITION_MGMT", StringFormat("ticket=%I64u horizon=%s dir=%s entry=%.5f current=%.5f tp=%.5f be_trigger=%.5f be_ratio=%.2f trail_mode=%d",
          pid, h_name, (dir == +1) ? "BUY" : "SELL", entry, entry, target, be_trigger, be_ratio, (int)cfg.trail_mode));

   // Persist updated position state
   PositionSaveState(cfg);
}

//+------------------------------------------------------------------+
//| Close or remove position by index                                |
//+------------------------------------------------------------------+
void PositionManagerRemove(int idx, const string reason, double exit_price, const AmigoConfig &cfg)
{
   ulong pid = g_positions[idx].position_id;
   ENUM_HORIZON h = g_positions[idx].horizon;
   string h_name = (h == HORIZON_SCALPING) ? "SCALPING" : (h == HORIZON_SWING) ? "SWING" : "INTRADAY";

   LogMsg(LOG_INFO, "POSITION_EXIT", StringFormat("ticket=%I64u horizon=%s reason=%s exit_price=%.5f",
          pid, h_name, reason, exit_price));

   if(!cfg.shadow_only)
   {
      if(PositionSelectByTicket(pid))
         g_trade.PositionClose(pid);
   }

   for(int j = idx; j < ArraySize(g_positions) - 1; j++)
      g_positions[j] = g_positions[j + 1];
   ArrayResize(g_positions, ArraySize(g_positions) - 1);
   PositionSaveState(cfg);
}

//+------------------------------------------------------------------+
//| Active position management tick with horizon-specific lifecycle   |
//+------------------------------------------------------------------+
void PositionManagerTick(const AmigoConfig &cfg)
{
   string sym = (StringLen(cfg.symbol) > 0) ? cfg.symbol : _Symbol;
   int    digits = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   double point  = SymbolInfoDouble(sym, SYMBOL_POINT);
   double stops_level = (double)SymbolInfoInteger(sym, SYMBOL_TRADE_STOPS_LEVEL);
   double freeze_level = (double)SymbolInfoInteger(sym, SYMBOL_TRADE_FREEZE_LEVEL);
   double min_stop_dist = stops_level * point;
   double freeze_dist   = freeze_level * point;

   datetime now_t = TimeCurrent();
   MqlDateTime dt;
   TimeToStruct(now_t, dt);

   for(int i = ArraySize(g_positions) - 1; i >= 0; i--)
   {
      ulong pid = g_positions[i].position_id;
      int   dir = g_positions[i].direction;
      ENUM_HORIZON horiz = g_positions[i].horizon;
      double cur_sl;
      double cur_tp;
      double cur_price;

      if(!cfg.shadow_only)
      {
         //--- Live Trading Mode: inspect active terminal position
         if(!PositionSelectByTicket(pid))
         {
            LogMsg(LOG_INFO, "POSITION_EXIT", StringFormat("ticket=%I64u reason=CLOSED_OR_REMOVED", pid));
            for(int j = i; j < ArraySize(g_positions) - 1; j++)
               g_positions[j] = g_positions[j + 1];
            ArrayResize(g_positions, ArraySize(g_positions) - 1);
            continue;
         }

         cur_sl    = PositionGetDouble(POSITION_SL);
         cur_tp    = PositionGetDouble(POSITION_TP);
         cur_price = PositionGetDouble(POSITION_PRICE_CURRENT);
      }
      else
      {
         //--- Shadow Safety Mode: track synthetic position against live symbol quotes
         cur_sl    = g_positions[i].current_stop;
         cur_tp    = g_positions[i].initial_target;
         cur_price = (dir == +1) ? SymbolInfoDouble(sym, SYMBOL_BID)
                                 : SymbolInfoDouble(sym, SYMBOL_ASK);

         if(cur_price <= 0.0) continue;

         // Check Shadow Exit Conditions (SL / TP hit)
         if(dir == +1)
         {
            if(cur_price <= g_positions[i].current_stop)
            {
               PositionManagerRemove(i, "STOP_LOSS", cur_price, cfg);
               continue;
            }
            if(cur_tp > 0.0 && cur_price >= cur_tp)
            {
               PositionManagerRemove(i, "TAKE_PROFIT", cur_price, cfg);
               continue;
            }
         }
         else
         {
            if(cur_price >= g_positions[i].current_stop)
            {
               PositionManagerRemove(i, "STOP_LOSS", cur_price, cfg);
               continue;
            }
            if(cur_tp > 0.0 && cur_price <= cur_tp)
            {
               PositionManagerRemove(i, "TAKE_PROFIT", cur_price, cfg);
               continue;
            }
         }
      }

      //================================================================
      // HORIZON-SPECIFIC LIFECYCLE CONTROLS
      //================================================================

      // 1. SCALPING EXPIRY: Max holding period = 3600 seconds (1 hour)
      // If a scalp stalls without hitting TP or BE, exit to prevent it from becoming an unmanaged swing
      if(horiz == HORIZON_SCALPING)
      {
         int elapsed_sec = (int)(now_t - g_positions[i].opened);
         if(elapsed_sec >= 3600 && !g_positions[i].be_activated)
         {
            PositionManagerRemove(i, "SCALP_TIME_EXPIRED", cur_price, cfg);
            continue;
         }
      }

      // 2. INTRADAY SESSION POLICY: Liquidate before server session close
      // Intraday trades must not be carried across rollover into overnight sessions
      if(horiz == HORIZON_INTRADAY)
      {
         if(cfg.session_end_hour > 0 && dt.hour >= cfg.session_end_hour)
         {
            PositionManagerRemove(i, "INTRADAY_SESSION_CLOSE", cur_price, cfg);
            continue;
         }
      }

      // 3. SWING PERSISTENCE: Multi-session, exempt from short-term time expiry or session closes.

      double r_unit = g_positions[i].initial_risk_per_unit;
      if(r_unit <= 0.0) continue;

      //--- Partial exit rules:
      // Scalping: 1.5R partial
      // Intraday / Swing: 2.0R partial (preserved baseline)
      double partial_rr_target = (horiz == HORIZON_SCALPING) ? 1.5 : cfg.partial_rr;
      if(!g_positions[i].partial_done)
      {
         double target_partial = (dir == +1)
                                ? (g_positions[i].entry + partial_rr_target * r_unit)
                                : (g_positions[i].entry - partial_rr_target * r_unit);

         bool hit = (dir == +1) ? (cur_price >= target_partial)
                                : (cur_price <= target_partial);

         if(hit)
         {
            if(!cfg.shadow_only)
            {
               double vol = PositionGetDouble(POSITION_VOLUME);
               double raw  = vol * cfg.partial_fraction;
               double part = RoundVolume(sym, raw);
               double vmin = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);

               if(part >= vmin && (vol - part) >= vmin)
               {
                  if(g_trade.PositionClosePartial(pid, part))
                  {
                     g_positions[i].partial_done = true;
                     LogMsg(LOG_INFO, "PARTIAL_EXIT", StringFormat("ticket=%I64u horizon=%d vol=%.2f part=%.2f target=%.5f",
                            pid, (int)horiz, vol, part, target_partial));
                  }
                  else
                  {
                     LogMsg(LOG_WARN, "PARTIAL_FAILED", StringFormat("ticket=%I64u retcode=%u", pid, g_trade.ResultRetcode()));
                  }
               }
            }
            else
            {
               // In shadow mode, mark synthetic partial completion
               g_positions[i].partial_done = true;
               LogMsg(LOG_INFO, "SHADOW_PARTIAL", StringFormat("ticket=%I64u horizon=%d partial_hit=true price=%.5f",
                      pid, (int)horiz, cur_price));
            }
         }
      }

      //--- Invalid TP check guard
      double tp_distance = MathAbs(cur_tp - g_positions[i].entry);
      if(cur_tp <= 0.0 || tp_distance <= 0.0) continue;

      //================================================================
      // BREAK-EVEN LOGIC (Completely decoupled from trailing mode)
      //================================================================
      if(!g_positions[i].be_activated)
      {
         bool be_reached = (dir == +1) ? (cur_price >= g_positions[i].be_trigger_price)
                                       : (cur_price <= g_positions[i].be_trigger_price);

         if(be_reached)
         {
            double proposed_be_sl = NormalizeDouble(g_positions[i].entry, digits);
            bool   stops_ok       = (dir == +1) ? ((cur_price - proposed_be_sl) >= min_stop_dist)
                                                : ((proposed_be_sl - cur_price) >= min_stop_dist);

            if(stops_ok)
            {
               bool is_be_improvement = (dir == +1) ? (proposed_be_sl > cur_sl)
                                                    : (proposed_be_sl < cur_sl);
               if(is_be_improvement)
               {
                  bool modify_success = true;
                  if(!cfg.shadow_only)
                  {
                     modify_success = g_trade.PositionModify(pid, proposed_be_sl, cur_tp);
                     if(!modify_success)
                     {
                        LogMsg(LOG_WARN, "BE_FAILED", StringFormat("ticket=%I64u retcode=%u", pid, g_trade.ResultRetcode()));
                     }
                  }

                  // ONLY mark be_activated and update state if broker confirmed (or shadow mode)
                  if(modify_success)
                  {
                     g_positions[i].be_activated      = true;
                     g_positions[i].current_stop      = proposed_be_sl;
                     g_positions[i].last_applied_stop = proposed_be_sl;
                     cur_sl                           = proposed_be_sl;
                     LogMsg(LOG_INFO, "BE_ACTIVATED", StringFormat("ticket=%I64u horizon=%d entry=%.5f sl=%.5f",
                            pid, (int)horiz, g_positions[i].entry, proposed_be_sl));
                  }
               }
               else
               {
                  // Stop is already at or better than BE level
                  g_positions[i].be_activated = true;
               }
            }
         }
      }

      // If trailing is off, break-even is evaluated but trailing is skipped
      if(g_positions[i].trailing_mode == TRAIL_OFF) continue;

      //================================================================
      // DYNAMIC TRAILING STOP LOGIC (Horizon-Aware Ratchet Calibration)
      //================================================================
      if(g_positions[i].be_activated && g_positions[i].trailing_mode == TRAIL_DYNAMIC_25_PERCENT)
      {
         double profit_dist = (dir == +1) ? (cur_price - g_positions[i].entry)
                                          : (g_positions[i].entry - cur_price);
         if(profit_dist > 0.0)
         {
            double trail_factor = 0.25;
            if(horiz == HORIZON_SCALPING) trail_factor = 0.15;
            else if(horiz == HORIZON_SWING) trail_factor = 0.35;

            double trailing_dist = profit_dist * trail_factor;
            double proposed_sl   = (dir == +1) ? (cur_price - trailing_dist)
                                               : (cur_price + trailing_dist);
            proposed_sl          = NormalizeDouble(proposed_sl, digits);

            bool is_improvement = (dir == +1) ? (proposed_sl > cur_sl)
                                              : (proposed_sl < cur_sl);

            if(is_improvement)
            {
               bool stops_ok  = (dir == +1) ? ((cur_price - proposed_sl) >= min_stop_dist)
                                            : ((proposed_sl - cur_price) >= min_stop_dist);
               bool freeze_ok = (freeze_dist <= 0.0) || (MathAbs(cur_price - cur_sl) > freeze_dist);

               if(stops_ok && freeze_ok)
               {
                  bool mod_ok = true;
                  if(!cfg.shadow_only)
                  {
                     mod_ok = g_trade.PositionModify(pid, proposed_sl, cur_tp);
                     if(!mod_ok)
                     {
                        LogMsg(LOG_WARN, "TRAIL_BLOCKED", StringFormat("reason=MODIFY_FAILED retcode=%u", g_trade.ResultRetcode()));
                     }
                  }
                  if(mod_ok)
                  {
                     LogMsg(LOG_INFO, "TRAIL_UPDATE", StringFormat("ticket=%I64u horizon=%d trail_factor=%.2f old_sl=%.5f new_sl=%.5f",
                            pid, (int)horiz, trail_factor, cur_sl, proposed_sl));
                     g_positions[i].current_stop      = proposed_sl;
                     g_positions[i].last_applied_stop = proposed_sl;
                  }
               }
            }
         }
      }
      else if(g_positions[i].trailing_mode == TRAIL_ATR)
      {
         //--- Legacy ATR Trailing Stop (Strict broker check and stop levels applied)
         double excursion = (dir == +1) ? (cur_price - g_positions[i].entry)
                                        : (g_positions[i].entry - cur_price);

         if(excursion >= cfg.trail_activate_r * r_unit)
         {
            double atr = g_positions[i].initial_atr;
            double mult = (horiz == HORIZON_SCALPING) ? 1.0 : (horiz == HORIZON_SWING) ? 2.5 : cfg.trail_atr_mult;
            double proposed;
            if(dir == +1) proposed = MathMax(cur_sl, cur_price - mult * atr);
            else          proposed = MathMin(cur_sl, cur_price + mult * atr);

            proposed = NormalizeDouble(proposed, digits);

            bool is_improvement = (dir == +1) ? (proposed > cur_sl) : (proposed < cur_sl);
            if(is_improvement && (MathAbs(proposed - cur_sl) > point))
            {
               bool stops_ok  = (dir == +1) ? ((cur_price - proposed) >= min_stop_dist)
                                            : ((proposed - cur_price) >= min_stop_dist);
               bool freeze_ok = (freeze_dist <= 0.0) || (MathAbs(cur_price - cur_sl) > freeze_dist);

               if(stops_ok && freeze_ok)
               {
                  bool mod_ok = true;
                  if(!cfg.shadow_only)
                  {
                     mod_ok = g_trade.PositionModify(pid, proposed, cur_tp);
                     if(!mod_ok)
                     {
                        LogMsg(LOG_WARN, "ATR_TRAIL_BLOCKED", StringFormat("reason=MODIFY_FAILED retcode=%u", g_trade.ResultRetcode()));
                     }
                  }
                  if(mod_ok)
                  {
                     LogMsg(LOG_INFO, "TRAIL_UPDATE", StringFormat("ticket=%I64u horizon=%d old_sl=%.5f new_sl=%.5f (ATR mult=%.1f)",
                            pid, (int)horiz, cur_sl, proposed, mult));
                     g_positions[i].current_stop      = proposed;
                     g_positions[i].last_applied_stop = proposed;
                  }
               }
            }
         }
      }
   }
}
//+------------------------------------------------------------------+
