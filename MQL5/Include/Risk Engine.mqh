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

#include <Account Execution Engine.mqh>

//--- Position size per Math Spec §24.2 (Unified with Account Execution Engine)
double ComputeLotSize(string symbol, double entry, double stop, double risk_pct,
                      double &risk_actual_out, string &err)
{
   risk_actual_out = 0.0;
   err = "";

   AccountExecutionEnvelope env = AccountExecutionEvaluate(
      symbol, +1, entry, stop, entry + MathAbs(entry - stop), risk_pct, g_cfg, ACTION_TRADE
   );

   if(env.final_action != ACTION_TRADE)
   {
      err = env.reason;
      return 0.0;
   }

   risk_actual_out = env.actual_risk;
   return env.executable_volume;
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