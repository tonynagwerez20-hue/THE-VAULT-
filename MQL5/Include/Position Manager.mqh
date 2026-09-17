//+------------------------------------------------------------------+
//| PositionManager.mqh - partials, trailing, break-even             |
//+------------------------------------------------------------------+
#property strict

#include <Contracts header.mqh>
#include <Configuration.mqh>
#include <Logger.mqh>
#include <Execution Engine.mqh>   // provides CTrade g_trade

struct PositionState
{
   ulong    position_id;
   int      direction;
   double   entry;
   double   initial_stop;
   double   initial_target;
   double   initial_atr;
   double   initial_risk_per_unit;
   bool     partial_done;
   double   current_stop;
   datetime opened;
};

PositionState g_positions[];

//--- Round a raw volume to the broker's allowed step.
//--- MQL5 reference (Symbol Properties):
//---   SYMBOL_VOLUME_STEP / SYMBOL_VOLUME_MIN / SYMBOL_VOLUME_MAX
//--- There is no "volume digits" property. Volume is step-quantised.
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

   g_positions[n].position_id           = pid;
   g_positions[n].direction             = dir;
   g_positions[n].entry                 = entry;
   g_positions[n].initial_stop          = stop;
   g_positions[n].initial_target        = target;
   g_positions[n].initial_atr           = atr;
   g_positions[n].initial_risk_per_unit = MathAbs(entry - stop);
   g_positions[n].partial_done          = false;
   g_positions[n].current_stop          = stop;
   g_positions[n].opened                = TimeCurrent();
}

void PositionManagerTick(const AlgoMindConfig &cfg)
{
   for(int i = ArraySize(g_positions) - 1; i >= 0; i--)
   {
      ulong pid = g_positions[i].position_id;

      if(!PositionSelectByTicket(pid))
      {
         for(int j = i; j < ArraySize(g_positions) - 1; j++)
            g_positions[j] = g_positions[j + 1];
         ArrayResize(g_positions, ArraySize(g_positions) - 1);
         continue;
      }

      double cur_sl    = PositionGetDouble(POSITION_SL);
      double cur_tp    = PositionGetDouble(POSITION_TP);
      double cur_price = PositionGetDouble(POSITION_PRICE_CURRENT);
      int    dir       = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? +1 : -1;

      double r_unit = g_positions[i].initial_risk_per_unit;
      if(r_unit <= 0.0) continue;

      //--- Partial exit at 2R
      if(!g_positions[i].partial_done)
      {
         double target_2r = (dir == +1)
                            ? (g_positions[i].entry + cfg.partial_rr * r_unit)
                            : (g_positions[i].entry - cfg.partial_rr * r_unit);

         bool hit = (dir == +1) ? (cur_price >= target_2r)
                                : (cur_price <= target_2r);

         if(hit)
         {
            double vol  = PositionGetDouble(POSITION_VOLUME);
            double raw  = vol * cfg.partial_fraction;
            double part = RoundVolume(_Symbol, raw);

            double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);

            //--- Only partial-close if both the partial and the
            //--- remainder are at least the broker minimum.
            if(part >= vmin && (vol - part) >= vmin)
            {
               g_trade.PositionClosePartial(pid, part);
               g_positions[i].partial_done = true;
            }
         }
      }

      //--- Trailing stop, activated only after +1R of excursion
      double excursion = (dir == +1) ? (cur_price - g_positions[i].entry)
                                     : (g_positions[i].entry - cur_price);

      if(excursion >= cfg.trail_activate_r * r_unit)
      {
         double atr = g_positions[i].initial_atr;
         double proposed;
         if(dir == +1)
            proposed = MathMax(cur_sl, cur_price - cfg.trail_atr_mult * atr);
         else
            proposed = MathMin(cur_sl, cur_price + cfg.trail_atr_mult * atr);

         int    digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
         double point  = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
         proposed = NormalizeDouble(proposed, digits);

         if(MathAbs(proposed - cur_sl) > point)
            g_trade.PositionModify(pid, proposed, cur_tp);
      }
   }
}
//+------------------------------------------------------------------+