//+------------------------------------------------------------------+
//| RiskController.mqh                                               |
//| AMIGO Account-Size-Correlated Risk + Distortion Engine           |
//| Piecewise-Linear Spline, High-Water Throttle, Hard Safety Caps   |
//+------------------------------------------------------------------+
#property strict

#include <Contracts header.mqh>
#include <Configuration.mqh>
#include <Logger.mqh>
#include <Account Execution Engine.mqh>

//--- Absolute Safety Ceilings (Hard Guardrails - Section 4 & 14)
#define ABSOLUTE_MAX_RISK_PERCENT 2.00
#define ABSOLUTE_MAX_DISTORTION   10.00

//--- Spline Anchor Structure
struct RiskControlPoint
{
   double equity;
   double risk_percent;
   double max_distortion;
};

//--- Policy Control Points (Section 3 Approved Defaults)
#define RISK_SPLINE_POINTS 8

static RiskControlPoint g_risk_curve[RISK_SPLINE_POINTS] = {
   {   10.0, 1.50, 8.0 },
   {   50.0, 1.25, 6.0 },
   {  100.0, 1.00, 5.0 },
   {  250.0, 0.75, 4.0 },
   {  500.0, 0.50, 3.0 },
   { 1000.0, 0.50, 2.0 },
   { 5000.0, 0.50, 1.5 },
   {10000.0, 0.50, 1.0 }
};

//--- State tracking struct for Account-Size-Aware Risk
struct AdaptiveRiskState
{
   double   initial_equity;
   double   high_water_equity;
   double   last_equity;
   bool     initialized;
};

static AdaptiveRiskState g_adaptive_risk;

//+------------------------------------------------------------------+
//| Initialize Risk Controller State                                 |
//+------------------------------------------------------------------+
void RiskControllerInit(double equity = 0.0)
{
   if(equity <= 0.0) equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity <= 0.0) equity = AccountInfoDouble(ACCOUNT_BALANCE);

   g_adaptive_risk.initial_equity    = equity;
   g_adaptive_risk.high_water_equity = equity;
   g_adaptive_risk.last_equity       = equity;
   g_adaptive_risk.initialized       = (equity > 0.0);
}

//+------------------------------------------------------------------+
//| Update Risk Controller on Every Tick / Bar                       |
//+------------------------------------------------------------------+
void RiskControllerUpdate(double equity = 0.0)
{
   if(equity <= 0.0) equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity <= 0.0) equity = AccountInfoDouble(ACCOUNT_BALANCE);

   if(!g_adaptive_risk.initialized && equity > 0.0)
   {
      RiskControllerInit(equity);
      return;
   }

   g_adaptive_risk.last_equity = equity;

   // Monotonic non-decreasing high-water equity tracking
   if(equity > g_adaptive_risk.high_water_equity)
   {
      g_adaptive_risk.high_water_equity = equity;
   }
}

//+------------------------------------------------------------------+
//| Piecewise-Linear Interpolation for Account-Size Risk % Curve     |
//+------------------------------------------------------------------+
double InterpolateRiskCurve(double equity)
{
   if(equity <= g_risk_curve[0].equity)
      return g_risk_curve[0].risk_percent;

   int n = RISK_SPLINE_POINTS;
   if(equity >= g_risk_curve[n - 1].equity)
      return g_risk_curve[n - 1].risk_percent;

   for(int i = 0; i < n - 1; i++)
   {
      if(equity >= g_risk_curve[i].equity && equity <= g_risk_curve[i + 1].equity)
      {
         double t = (equity - g_risk_curve[i].equity) / (g_risk_curve[i + 1].equity - g_risk_curve[i].equity);
         double r = g_risk_curve[i].risk_percent + t * (g_risk_curve[i + 1].risk_percent - g_risk_curve[i].risk_percent);
         return MathMin(r, ABSOLUTE_MAX_RISK_PERCENT);
      }
   }

   return g_risk_curve[n - 1].risk_percent;
}

//+------------------------------------------------------------------+
//| Piecewise-Linear Interpolation for Account-Size Distortion Curve |
//+------------------------------------------------------------------+
double InterpolateDistortionCurve(double equity)
{
   if(equity <= g_risk_curve[0].equity)
      return g_risk_curve[0].max_distortion;

   int n = RISK_SPLINE_POINTS;
   if(equity >= g_risk_curve[n - 1].equity)
      return g_risk_curve[n - 1].max_distortion;

   for(int i = 0; i < n - 1; i++)
   {
      if(equity >= g_risk_curve[i].equity && equity <= g_risk_curve[i + 1].equity)
      {
         double t = (equity - g_risk_curve[i].equity) / (g_risk_curve[i + 1].equity - g_risk_curve[i].equity);
         double d = g_risk_curve[i].max_distortion + t * (g_risk_curve[i + 1].max_distortion - g_risk_curve[i].max_distortion);
         return MathMin(d, ABSOLUTE_MAX_DISTORTION);
      }
   }

   return g_risk_curve[n - 1].max_distortion;
}

//+------------------------------------------------------------------+
//| Calculate Informational Minimum Viable Equity (Diagnostic Only)   |
//+------------------------------------------------------------------+
double RiskControllerGetMinimumViableEquity(double min_lot_loss, double effective_risk_pct, double max_distortion)
{
   double r_dec = (effective_risk_pct > 0.0) ? (effective_risk_pct / 100.0) : 0.005;
   double denom = r_dec * max_distortion;
   if(denom <= 0.0 || min_lot_loss <= 0.0) return 0.0;
   return min_lot_loss / denom;
}

//+------------------------------------------------------------------+
//| Calculate Reverse Feasibility Required Risk % (Diagnostic Only)   |
//+------------------------------------------------------------------+
double RiskControllerGetRequiredRiskPercent(double min_lot_loss, double equity, double max_distortion)
{
   double denom = equity * max_distortion;
   if(denom <= 0.0 || min_lot_loss <= 0.0) return 999.0;
   return (min_lot_loss / denom) * 100.0;
}

//+------------------------------------------------------------------+
//| Evaluate Account-Size-Correlated Risk Budget & Feasibility Gate  |
//+------------------------------------------------------------------+
AdaptiveRiskResult RiskControllerEvaluate(
   string symbol,
   double entry,
   double stop,
   const AlgoMindConfig &cfg,
   bool daily_locked_status = false
)
{
   AdaptiveRiskResult res;
   ZeroMemory(res);

   double cur_eq  = AccountInfoDouble(ACCOUNT_EQUITY);
   double cur_bal = AccountInfoDouble(ACCOUNT_BALANCE);

   RiskControllerUpdate(cur_eq);

   res.equity            = cur_eq;
   res.balance           = cur_bal;
   res.high_water_equity = g_adaptive_risk.high_water_equity;

   // Growth percentage from baseline initial equity
   if(g_adaptive_risk.initial_equity > 0.0)
      res.growth_percent = (cur_eq - g_adaptive_risk.initial_equity) / g_adaptive_risk.initial_equity * 100.0;
   else
      res.growth_percent = 0.0;

   // Drawdown percentage from high-water mark (informational / throttle input only)
   if(res.high_water_equity > 0.0 && cur_eq < res.high_water_equity)
      res.drawdown_percent = (res.high_water_equity - cur_eq) / res.high_water_equity * 100.0;
   else
      res.drawdown_percent = 0.0;

   // Account classification (authoritative classification thresholds)
   if(cur_eq < 100.0)
      res.account_class = ACCOUNT_CLASS_MICRO;
   else if(cur_eq < 1000.0)
      res.account_class = ACCOUNT_CLASS_SMALL;
   else if(cur_eq < 10000.0)
      res.account_class = ACCOUNT_CLASS_STANDARD;
   else
      res.account_class = ACCOUNT_CLASS_LARGE;

   // 1. Derive Account-Size Baseline Risk % & Max Allowed Distortion from Spline Curves
   res.base_risk_percent        = InterpolateRiskCurve(cur_eq);
   res.max_allowed_distortion   = MathMin(InterpolateDistortionCurve(cur_eq), ABSOLUTE_MAX_DISTORTION);

   // 2. Broker symbol specifications for minimum lot risk and distortion
   double vol_min = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double tick_sz = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
   double tick_vl = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
   if(vol_min <= 0.0) vol_min = 0.01;
   res.minimum_lot = vol_min;

   double stop_dist = MathAbs(entry - stop);
   double risk_per_lot = 0.0;
   if(tick_sz > 0.0 && tick_vl > 0.0 && stop_dist > 0.0)
   {
      risk_per_lot = (stop_dist / tick_sz) * tick_vl;
   }
   res.minimum_lot_loss = vol_min * risk_per_lot;

   // Diagnostics: Required Risk % and Minimum Viable Equity
   res.required_risk_percent = RiskControllerGetRequiredRiskPercent(res.minimum_lot_loss, cur_eq, res.max_allowed_distortion);
   res.minimum_viable_equity = RiskControllerGetMinimumViableEquity(res.minimum_lot_loss, res.base_risk_percent, res.max_allowed_distortion);

   // 3. Active Hard Account-Loss Control: DAILY DRAWDOWN
   if(daily_locked_status)
   {
      res.risk_state             = RISK_STATE_DAILY_STOP;
      res.effective_risk_percent = 0.0;
      res.risk_budget            = 0.0;
      res.trade_allowed          = false;
      res.reason                 = "DAILY_STOP";
      return res;
   }

   // Fail closed if account equity is zero or negative
   if(cur_eq <= 0.0)
   {
      res.risk_state             = RISK_STATE_UNSAFE;
      res.effective_risk_percent = 0.0;
      res.risk_budget            = 0.0;
      res.trade_allowed          = false;
      res.reason                 = "ZERO_OR_NEGATIVE_EQUITY";
      return res;
   }

   // 4. High-Water Drawdown Throttle Multiplier (Drawdown may ONLY reduce risk, never increase it)
   double dd_mult = 1.0;
   if(res.drawdown_percent >= 3.5)
   {
      dd_mult        = 0.50;
      res.risk_state = RISK_STATE_RECOVERY;
   }
   else if(res.drawdown_percent >= 2.0)
   {
      dd_mult        = 0.70;
      res.risk_state = RISK_STATE_CAUTION;
   }
   else
   {
      dd_mult        = 1.00;
      res.risk_state = RISK_STATE_NORMAL;
   }

   double throttled_risk = res.base_risk_percent * dd_mult;
   res.effective_risk_percent = MathMin(throttled_risk, ABSOLUTE_MAX_RISK_PERCENT);

   // Recompute Minimum Viable Equity with effective risk percent
   res.minimum_viable_equity = RiskControllerGetMinimumViableEquity(res.minimum_lot_loss, res.effective_risk_percent, res.max_allowed_distortion);

   // 5. Compute Dollar Risk Budget
   res.risk_budget = cur_eq * (res.effective_risk_percent / 100.0);

   // 6. Actual Distortion Calculation
   if(res.risk_budget > 0.0 && res.minimum_lot_loss > 0.0)
   {
      res.distortion = res.minimum_lot_loss / res.risk_budget;
   }
   else
   {
      res.distortion = 999.0;
   }

   // 7. Strict Account-Size Distortion Feasibility Gate (Section 8, 9, 14)
   // Epsilon tolerance of 1e-5 for floating boundary
   if(res.distortion > (res.max_allowed_distortion + 0.00001))
   {
      res.risk_state    = RISK_STATE_UNSAFE;
      res.trade_allowed = false;
      res.reason        = "MIN_LOT_UNSAFE";
      return res;
   }

   // Trade is feasible under account-size risk and distortion policy
   res.trade_allowed = true;
   res.reason        = "RISK_OK";
   return res;
}

//+------------------------------------------------------------------+
//| Emit Structured [AMIGO][ACCOUNT_RISK] Diagnostic Log (Section 16, 23)|
//+------------------------------------------------------------------+
void RiskControllerLogDiagnostic(const AdaptiveRiskResult &r)
{
   string class_str = (r.account_class == ACCOUNT_CLASS_MICRO)    ? "MICRO" :
                      (r.account_class == ACCOUNT_CLASS_SMALL)    ? "SMALL" :
                      (r.account_class == ACCOUNT_CLASS_STANDARD) ? "STANDARD" :
                      (r.account_class == ACCOUNT_CLASS_LARGE)    ? "LARGE" : "PROP";

   string status_str = r.trade_allowed ? "EXECUTABLE" : "UNSAFE";
   string dec_str    = r.trade_allowed ? "TRADE" : "NO_TRADE";

   PrintFormat("[AMIGO][ACCOUNT_RISK] equity=%.2f class=%s risk_pct=%.2f%% risk_budget=%.4f min_lot_loss=%.2f actual_distortion=%.2fx allowed_distortion=%.2fx min_viable_equity=%.2f required_risk=%.2f%% status=%s decision=%s reason=%s",
               r.equity, class_str, r.effective_risk_percent, r.risk_budget,
               r.minimum_lot_loss, r.distortion, r.max_allowed_distortion,
               r.minimum_viable_equity, r.required_risk_percent,
               status_str, dec_str, r.reason);
}
