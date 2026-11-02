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
//| Account-Aware Adaptive Stop-Loss Engine (Prompts §1-§19)          |
//+------------------------------------------------------------------+
AdaptiveSLResult EvaluateAdaptiveStop(string symbol, int direction, double entry,
                                      double original_sl, double target,
                                      double structural_invalid, double atr,
                                      double target_risk_pct, const AlgoMindConfig &cfg)
{
   AdaptiveSLResult res;
   ZeroMemory(res);
   res.status               = NO_VALID_SL;
   res.original_sl          = original_sl;
   res.original_stop_dist   = MathAbs(entry - original_sl);
   res.max_account_stop_dist= 0.0;
   res.candidate_sl         = 0.0;
   res.candidate_stop_dist  = 0.0;
   res.selected_sl          = original_sl;
   res.selected_stop_dist   = res.original_stop_dist;
   res.rr                   = (res.original_stop_dist > 0.0) ? (MathAbs(target - entry) / res.original_stop_dist) : 0.0;
   res.reason               = "UNINITIALIZED";

   //--- Retrieve live symbol properties
   double tick_sz  = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
   double tick_val = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
   double vol_min  = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double point    = SymbolInfoDouble(symbol, SYMBOL_POINT);
   long   stops_lvl= SymbolInfoInteger(symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double min_stop_dist = stops_lvl * point;
   int    digits   = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);

   double equity = AccountInfoDouble(ACCOUNT_EQUITY);

   //--- Fail closed on invalid symbol/account economics
   if(tick_sz <= 0.0 || tick_val <= 0.0 || vol_min <= 0.0 || equity <= 0.0 || res.original_stop_dist <= 0.0)
   {
      res.status = ADAPTIVE_SL_REJECTED;
      res.reason = "INVALID_SYMBOL_OR_ACCOUNT_ECONOMICS";
      return res;
   }

   double target_risk_amt = equity * (target_risk_pct / 100.0);
   double max_distortion  = (cfg.max_allowed_distortion > 0.0) ? cfg.max_allowed_distortion : 1.0;
   double max_risk_allowed= target_risk_amt * max_distortion;

   //--- Calculate maximum stop distance that minimum executable volume can support
   double val_per_unit = (tick_val / tick_sz);
   res.max_account_stop_dist = max_risk_allowed / (vol_min * val_per_unit);

   //--- 1. Is original SL executable within small account risk ceiling?
   if(res.original_stop_dist <= res.max_account_stop_dist)
   {
      res.status      = ORIGINAL_SL_EXECUTABLE;
      res.selected_sl = original_sl;
      res.selected_stop_dist = res.original_stop_dist;
      res.reason      = "ORIGINAL_SL_EXECUTABLE";
      return res;
   }

   //--- 2. Adaptation is REQUIRED
   res.status = ADAPTIVE_SL_REQUIRED;

   //--- Retrieve legitimate strategy-derived SL candidates
   //--- Candidate A: Structural swing point (if available, tighter than original, and valid side of entry)
   //--- Candidate B: 1.0 * ATR stop (existing strategy volatility bound)
   double cand_a = 0.0;
   double cand_b = 0.0;

   if(direction == +1)
   {
      if(structural_invalid > 0.0 && structural_invalid < entry && structural_invalid > original_sl)
         cand_a = structural_invalid;
      if(atr > 0.0)
         cand_b = entry - 1.0 * atr;
   }
   else
   {
      if(structural_invalid > entry && structural_invalid < original_sl)
         cand_a = structural_invalid;
      if(atr > 0.0)
         cand_b = entry + 1.0 * atr;
   }

   double candidates[2];
   candidates[0] = cand_a;
   candidates[1] = cand_b;

   //--- Evaluate candidates sequentially (preserving strategy structural hierarchy: Structure > ATR)
   for(int i = 0; i < 2; i++)
   {
      double c_sl = candidates[i];
      if(c_sl <= 0.0) continue;

      c_sl = NormalizeDouble(c_sl, digits);
      double c_dist = MathAbs(entry - c_sl);

      // Rule 1: Correct side of entry (Long: SL < entry, Short: SL > entry)
      if(direction == +1 && c_sl >= entry) continue;
      if(direction == -1 && c_sl <= entry) continue;

      // Rule 2: Non-zero stop distance
      if(c_dist <= 0.0) continue;

      // Rule 3: Broker minimum stop distance
      if(min_stop_dist > 0.0 && c_dist < min_stop_dist) continue;

      // Rule 4: Must be within account-compatible maximum distance
      if(c_dist > res.max_account_stop_dist) continue;

      // Rule 5: Strategy minimum RR requirement (e.g. 1:2.0 or cfg.partial_rr)
      double cand_rr = (c_dist > 0.0) ? (MathAbs(target - entry) / c_dist) : 0.0;
      double min_rr  = (cfg.partial_rr > 0.0) ? cfg.partial_rr : 2.0;
      if(cand_rr < min_rr) continue;

      //--- Found valid strategy-derived adaptive candidate!
      res.status              = ADAPTIVE_SL_ACCEPTED;
      res.candidate_sl        = c_sl;
      res.candidate_stop_dist = c_dist;
      res.selected_sl         = c_sl;
      res.selected_stop_dist  = c_dist;
      res.rr                  = cand_rr;
      res.reason              = (i == 0) ? "VALID_STRATEGY_STRUCTURE" : "VALID_STRATEGY_ATR";
      return res;
   }

   //--- No valid strategy-derived adaptive SL found
   res.status   = ADAPTIVE_SL_REJECTED;
   res.selected_sl = original_sl;
   res.selected_stop_dist = res.original_stop_dist;
   res.reason   = "NO_VALID_ADAPTIVE_SL";
   return res;
}
//+------------------------------------------------------------------+