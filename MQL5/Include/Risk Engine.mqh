//+------------------------------------------------------------------+
//| RiskEngine.mqh - hard risk, sizing, stop selection               |
//+------------------------------------------------------------------+
#property strict

#include <Contracts header.mqh>
#include <Configuration.mqh>
#include <Logger.mqh>

//--- Persistent risk state
struct RiskState
{
   double   start_of_day_equity;
   double   peak_equity;
   bool     daily_locked;
   bool     total_locked;
   datetime last_day;
};

RiskState g_risk;

void RiskInit()
{
   g_risk.start_of_day_equity = AccountInfoDouble(ACCOUNT_EQUITY);
   g_risk.peak_equity          = g_risk.start_of_day_equity;
   g_risk.daily_locked         = false;
   g_risk.total_locked         = false;
   g_risk.last_day             = iTime(_Symbol, PERIOD_D1, 0);
}

void RiskTick()
{
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(eq > g_risk.peak_equity) g_risk.peak_equity = eq;

   datetime today = iTime(_Symbol, PERIOD_D1, 0);
   if(today != g_risk.last_day)
   {
      g_risk.last_day             = today;
      g_risk.start_of_day_equity  = eq;
      g_risk.daily_locked         = false;
   }

   double daily_loss_pct = 0.0;
   if(g_risk.start_of_day_equity > 0.0)
      daily_loss_pct = (g_risk.start_of_day_equity - eq)
                       / g_risk.start_of_day_equity * 100.0;

   double dd_pct = 0.0;
   if(g_risk.peak_equity > 0.0)
      dd_pct = (g_risk.peak_equity - eq) / g_risk.peak_equity * 100.0;

   if(g_cfg.daily_loss_pct > 0.0 && daily_loss_pct >= g_cfg.daily_loss_pct) g_risk.daily_locked = true;
   if(g_cfg.total_dd_pct   > 0.0 && dd_pct         >= g_cfg.total_dd_pct)   g_risk.total_locked = true;
}

bool RiskAllows(const AlgoMindConfig &cfg, string &reason)
{
   if(g_risk.daily_locked)
   {
      reason = "DAILY_LOCK";
      return false;
   }
   if(g_risk.total_locked)
   {
      reason = "TOTAL_DD_LOCK";
      return false;
   }
   if(!MQLInfoInteger(MQL_TRADE_ALLOWED))
   {
      reason = "TRADE_NOT_ALLOWED";
      return false;
   }
   if(!AccountInfoInteger(ACCOUNT_TRADE_EXPERT))
   {
      reason = "EXPERT_DISABLED";
      return false;
   }
   reason = "";
   return true;
}

//--- Position size per Math Spec §24.2
double ComputeLotSize(string symbol, double entry, double stop, double risk_pct,
                      double &risk_actual_out, string &err)
{
   risk_actual_out = 0.0;
   err = "";

   double equity      = AccountInfoDouble(ACCOUNT_EQUITY);
   double risk_amount = equity * (risk_pct / 100.0);
   double tick_size   = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
   double tick_value  = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
   double vol_min     = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double vol_max     = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
   double vol_step    = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);

   if(tick_size <= 0.0 || tick_value <= 0.0 || vol_step <= 0.0)
   {
      err = "INVALID_SYMBOL_PROPS";
      return 0.0;
   }

   double stop_distance = MathAbs(entry - stop);
   if(stop_distance <= 0.0)
   {
      err = "ZERO_STOP_DISTANCE";
      return 0.0;
   }

   double loss_per_lot = (stop_distance / tick_size) * tick_value;
   if(loss_per_lot <= 0.0)
   {
      err = "INVALID_LOSS_PER_LOT";
      return 0.0;
   }

   double raw  = risk_amount / loss_per_lot;
   double lots = MathFloor(raw / vol_step) * vol_step;

   if(lots < vol_min)
   {
      if(vol_min * loss_per_lot > risk_amount)
      {
         err = "MIN_LOT_EXCEEDS_RISK";
         LogMsg(LOG_INFO, "SIZE_DIAG", StringFormat("eq=%.2f risk_amt=%.2f stop_dist=%.4f tick_sz=%.5f tick_val=%.2f loss_per_lot=%.2f min_lot_loss=%.2f min_vol=%.2f",
                equity, risk_amount, stop_distance, tick_size, tick_value, loss_per_lot, vol_min * loss_per_lot, vol_min));
         return 0.0;
      }
      lots = vol_min;
   }
   if(lots > vol_max) lots = vol_max;

   risk_actual_out = lots * loss_per_lot;
   return lots;
}

//--- Stop selection per Math Spec §24.4
double SelectStop(string symbol, int direction, double entry,
                  double structural_invalid, double atr)
{
   double sl = 0.0;

   if(direction == +1)
   {
      double fallback = entry - 1.5 * atr;
      if(structural_invalid > 0.0 && structural_invalid < entry)
         sl = MathMin(structural_invalid, entry - 1.0 * atr);
      else
         sl = fallback;
   }
   else
   {
      double fallback = entry + 1.5 * atr;
      if(structural_invalid > entry && structural_invalid > 0.0)
         sl = MathMax(structural_invalid, entry + 1.0 * atr);
      else
         sl = fallback;
   }

   double stops_level = (double)SymbolInfoInteger(symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double point       = SymbolInfoDouble(symbol, SYMBOL_POINT);
   double min_dist    = stops_level * point;

   if(min_dist > 0.0)
   {
      if(direction == +1 && (entry - sl) < min_dist) sl = entry - min_dist;
      if(direction == -1 && (sl - entry) < min_dist) sl = entry + min_dist;
   }

   return NormalizeDouble(sl, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS));
}
//+------------------------------------------------------------------+