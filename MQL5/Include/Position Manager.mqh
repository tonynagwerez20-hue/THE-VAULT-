//+------------------------------------------------------------------+
//| PositionManager.mqh - partials, 50% BE, 25% dynamic trailing      |
//+------------------------------------------------------------------+
#property strict

#include <Contracts header.mqh>
#include <Configuration.mqh>
#include <Logger.mqh>
#include <Execution Engine.mqh>   // provides CTrade g_trade

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
   bool               be_activated;           // True once 50% TP progress BE is activated
   double             be_trigger_price;       // Entry +/- (0.50 * |target - entry|)
   double             last_applied_stop;      // Last stop loss successfully applied/confirmed
   ENUM_TRAILING_MODE trailing_mode;
   datetime           opened;
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

void PositionManagerRegister(ulong pid, double entry, double stop, double target,
                             int dir, double atr, const AlgoMindConfig &cfg)
{
   int n = ArraySize(g_positions);
   ArrayResize(g_positions, n + 1);

   double tp_distance = MathAbs(target - entry);
   double be_trigger  = (dir == +1) ? (entry + tp_distance * 0.50)
                                    : (entry - tp_distance * 0.50);

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
   g_positions[n].opened                = TimeCurrent();

   LogMsg(LOG_INFO, "POSITION_MGMT", StringFormat("ticket=%I64u dir=%s entry=%.5f current=%.5f tp=%.5f be_trigger=%.5f trail_mode=%d",
          pid, (dir == +1) ? "BUY" : "SELL", entry, entry, target, be_trigger, (int)cfg.trail_mode));
}

void PositionManagerTick(const AlgoMindConfig &cfg)
{
   string sym = (StringLen(cfg.symbol) > 0) ? cfg.symbol : _Symbol;
   int    digits = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   double point  = SymbolInfoDouble(sym, SYMBOL_POINT);
   double stops_level = (double)SymbolInfoInteger(sym, SYMBOL_TRADE_STOPS_LEVEL);
   double freeze_level = (double)SymbolInfoInteger(sym, SYMBOL_TRADE_FREEZE_LEVEL);
   double min_stop_dist = stops_level * point;
   double freeze_dist   = freeze_level * point;

   for(int i = ArraySize(g_positions) - 1; i >= 0; i--)
   {
      ulong pid = g_positions[i].position_id;
      int   dir = g_positions[i].direction;
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
               LogMsg(LOG_INFO, "POSITION_EXIT", StringFormat("ticket=%I64u reason=STOP_LOSS price=%.5f sl=%.5f",
                      pid, cur_price, g_positions[i].current_stop));
               for(int j = i; j < ArraySize(g_positions) - 1; j++)
                  g_positions[j] = g_positions[j + 1];
               ArrayResize(g_positions, ArraySize(g_positions) - 1);
               continue;
            }
            if(cur_tp > 0.0 && cur_price >= cur_tp)
            {
               LogMsg(LOG_INFO, "POSITION_EXIT", StringFormat("ticket=%I64u reason=TAKE_PROFIT price=%.5f tp=%.5f",
                      pid, cur_price, cur_tp));
               for(int j = i; j < ArraySize(g_positions) - 1; j++)
                  g_positions[j] = g_positions[j + 1];
               ArrayResize(g_positions, ArraySize(g_positions) - 1);
               continue;
            }
         }
         else
         {
            if(cur_price >= g_positions[i].current_stop)
            {
               LogMsg(LOG_INFO, "POSITION_EXIT", StringFormat("ticket=%I64u reason=STOP_LOSS price=%.5f sl=%.5f",
                      pid, cur_price, g_positions[i].current_stop));
               for(int j = i; j < ArraySize(g_positions) - 1; j++)
                  g_positions[j] = g_positions[j + 1];
               ArrayResize(g_positions, ArraySize(g_positions) - 1);
               continue;
            }
            if(cur_tp > 0.0 && cur_price <= cur_tp)
            {
               LogMsg(LOG_INFO, "POSITION_EXIT", StringFormat("ticket=%I64u reason=TAKE_PROFIT price=%.5f tp=%.5f",
                      pid, cur_price, cur_tp));
               for(int j = i; j < ArraySize(g_positions) - 1; j++)
                  g_positions[j] = g_positions[j + 1];
               ArrayResize(g_positions, ArraySize(g_positions) - 1);
               continue;
            }
         }
      }

      double r_unit = g_positions[i].initial_risk_per_unit;
      if(r_unit <= 0.0) continue;

      //--- 1. Existing Partial exit at 2R (Preserved)
      if(!g_positions[i].partial_done)
      {
         double target_2r = (dir == +1)
                            ? (g_positions[i].entry + cfg.partial_rr * r_unit)
                            : (g_positions[i].entry - cfg.partial_rr * r_unit);

         bool hit = (dir == +1) ? (cur_price >= target_2r)
                                : (cur_price <= target_2r);

         if(hit)
         {
            double vol = (!cfg.shadow_only) ? PositionGetDouble(POSITION_VOLUME) : SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
            double raw  = vol * cfg.partial_fraction;
            double part = RoundVolume(sym, raw);

            double vmin = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);

            if(part >= vmin && (vol - part) >= vmin)
            {
               if(!cfg.shadow_only)
                  g_trade.PositionClosePartial(pid, part);
               g_positions[i].partial_done = true;
               LogMsg(LOG_INFO, "PARTIAL_EXIT", StringFormat("ticket=%I64u vol=%.2f part=%.2f target_2r=%.5f", pid, vol, part, target_2r));
            }
         }
      }

      //--- Invalid TP check guard
      double tp_distance = MathAbs(cur_tp - g_positions[i].entry);
      if(cur_tp <= 0.0 || tp_distance <= 0.0)
      {
         LogMsg(LOG_WARN, "TRAIL_BLOCKED", StringFormat("reason=INVALID_TP ticket=%I64u tp=%.5f", pid, cur_tp));
         continue;
      }

      if(g_positions[i].trailing_mode == TRAIL_OFF) continue;

      double progress_dist = (dir == +1) ? (cur_price - g_positions[i].entry)
                                         : (g_positions[i].entry - cur_price);
      double progress_pct  = (tp_distance > 0.0) ? (progress_dist / tp_distance * 100.0) : 0.0;

      //--- 2. Break-Even Check (50% of Entry->TP distance)
      if(!g_positions[i].be_activated)
      {
         bool be_reached = (dir == +1) ? (cur_price >= g_positions[i].be_trigger_price)
                                       : (cur_price <= g_positions[i].be_trigger_price);

         LogMsg(LOG_INFO, "BE_CHECK", StringFormat("progress=%.1f%% trigger=50%% status=%s ticket=%I64u",
                progress_pct, be_reached ? "REACHED" : "PENDING", pid));

         if(be_reached)
         {
            double proposed_be_sl = NormalizeDouble(g_positions[i].entry, digits);
            bool   stops_ok       = (dir == +1) ? ((cur_price - proposed_be_sl) >= min_stop_dist)
                                                : ((proposed_be_sl - cur_price) >= min_stop_dist);

            if(!stops_ok)
            {
               LogMsg(LOG_WARN, "TRAIL_BLOCKED", StringFormat("reason=STOPS_LEVEL proposed_be=%.5f current=%.5f min_dist=%.5f",
                      proposed_be_sl, cur_price, min_stop_dist));
            }
            else
            {
               g_positions[i].be_activated = true;
               LogMsg(LOG_INFO, "BE_ACTIVATED", StringFormat("ticket=%I64u entry=%.5f sl=%.5f",
                      pid, g_positions[i].entry, proposed_be_sl));

               // Apply BE stop if it improves current stop
               bool is_be_improvement = (dir == +1) ? (proposed_be_sl > cur_sl)
                                                    : (proposed_be_sl < cur_sl);
               if(is_be_improvement)
               {
                  if(!cfg.shadow_only)
                  {
                     if(!g_trade.PositionModify(pid, proposed_be_sl, cur_tp))
                     {
                        LogMsg(LOG_WARN, "TRAIL_BLOCKED", StringFormat("reason=MODIFY_FAILED retcode=%u", g_trade.ResultRetcode()));
                        continue;
                     }
                  }
                  LogMsg(LOG_INFO, "TRAIL_UPDATE", StringFormat("ticket=%I64u old_sl=%.5f new_sl=%.5f",
                         pid, cur_sl, proposed_be_sl));
                  g_positions[i].current_stop      = proposed_be_sl;
                  g_positions[i].last_applied_stop = proposed_be_sl;
                  cur_sl                           = proposed_be_sl;
               }
            }
         }
      }

      //--- 3. Dynamic 25% Trailing Stop Logic (Activated after Break-Even)
      if(g_positions[i].be_activated && g_positions[i].trailing_mode == TRAIL_DYNAMIC_25_PERCENT)
      {
         double profit_dist = (dir == +1) ? (cur_price - g_positions[i].entry)
                                          : (g_positions[i].entry - cur_price);
         if(profit_dist > 0.0)
         {
            double trailing_dist = profit_dist * 0.25;
            double proposed_sl   = (dir == +1) ? (cur_price - trailing_dist)
                                               : (cur_price + trailing_dist);
            proposed_sl          = NormalizeDouble(proposed_sl, digits);

            LogMsg(LOG_INFO, "TRAIL_CHECK", StringFormat("progress=%.1f%% trail_pct=25%% proposed_sl=%.5f current_sl=%.5f",
                   progress_pct, proposed_sl, cur_sl));

            // Mandatory Ratchet Protection Rule (Stop MUST NEVER loosen)
            bool is_improvement = (dir == +1) ? (proposed_sl > cur_sl)
                                                 : (proposed_sl < cur_sl);

            if(!is_improvement)
            {
               LogMsg(LOG_INFO, "TRAIL_HOLD", StringFormat("proposed_sl=%.5f existing_sl=%.5f reason=NO_IMPROVEMENT",
                      proposed_sl, cur_sl));
            }
            else
            {
               bool stops_ok  = (dir == +1) ? ((cur_price - proposed_sl) >= min_stop_dist)
                                            : ((proposed_sl - cur_price) >= min_stop_dist);
               bool freeze_ok = (freeze_dist <= 0.0) || (MathAbs(cur_price - cur_sl) > freeze_dist);

               if(!stops_ok)
               {
                  LogMsg(LOG_WARN, "TRAIL_BLOCKED", StringFormat("reason=STOPS_LEVEL proposed_sl=%.5f current=%.5f min_dist=%.5f",
                         proposed_sl, cur_price, min_stop_dist));
               }
               else if(!freeze_ok)
               {
                  LogMsg(LOG_WARN, "TRAIL_BLOCKED", StringFormat("reason=FREEZE_LEVEL proposed_sl=%.5f current=%.5f freeze_dist=%.5f",
                         proposed_sl, cur_price, freeze_dist));
               }
               else
               {
                  if(!cfg.shadow_only)
                  {
                     if(!g_trade.PositionModify(pid, proposed_sl, cur_tp))
                     {
                        LogMsg(LOG_WARN, "TRAIL_BLOCKED", StringFormat("reason=MODIFY_FAILED retcode=%u", g_trade.ResultRetcode()));
                        continue;
                     }
                  }
                  LogMsg(LOG_INFO, "TRAIL_UPDATE", StringFormat("ticket=%I64u old_sl=%.5f new_sl=%.5f",
                         pid, cur_sl, proposed_sl));
                  g_positions[i].current_stop      = proposed_sl;
                  g_positions[i].last_applied_stop = proposed_sl;
               }
            }
         }
      }
      else if(g_positions[i].trailing_mode == TRAIL_ATR)
      {
         //--- Legacy ATR Trailing Stop (Preserved)
         double excursion = (dir == +1) ? (cur_price - g_positions[i].entry)
                                        : (g_positions[i].entry - cur_price);

         if(excursion >= cfg.trail_activate_r * r_unit)
         {
            double atr = g_positions[i].initial_atr;
            double proposed;
            if(dir == +1) proposed = MathMax(cur_sl, cur_price - cfg.trail_atr_mult * atr);
            else          proposed = MathMin(cur_sl, cur_price + cfg.trail_atr_mult * atr);

            proposed = NormalizeDouble(proposed, digits);

            if(MathAbs(proposed - cur_sl) > point)
            {
               if(!cfg.shadow_only) g_trade.PositionModify(pid, proposed, cur_tp);
               LogMsg(LOG_INFO, "TRAIL_UPDATE", StringFormat("ticket=%I64u old_sl=%.5f new_sl=%.5f (ATR)", pid, cur_sl, proposed));
               g_positions[i].current_stop      = proposed;
               g_positions[i].last_applied_stop = proposed;
            }
         }
      }
   }
}
//+------------------------------------------------------------------+