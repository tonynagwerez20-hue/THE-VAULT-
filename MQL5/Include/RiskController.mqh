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
#define ABSOLUTE_MAX_DISTORTION   5.00

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
   {   10.0, 1.50, 5.0 },
   {   50.0, 1.25, 4.0 },
   {  100.0, 1.00, 3.5 },
   {  250.0, 0.75, 3.0 },
   {  500.0, 0.50, 2.5 },
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
static datetime g_last_equity_persist_bar=0;

//+------------------------------------------------------------------+
//| Initialize Risk Controller State                                 |
//+------------------------------------------------------------------+
bool RiskControllerInit(double equity = 0.0)
{
   // The risk ledger is the sole baseline authority. Do not reset high-water
   // or initial equity from the current account value after a restart.
   if(!g_risk.initialized || !g_risk.persistence_ok) return false;
   g_adaptive_risk.initial_equity    = g_risk.initial_equity;
   g_adaptive_risk.high_water_equity = g_risk.adaptive_high_water;
   g_adaptive_risk.last_equity       = g_risk.adaptive_last_equity;
   g_adaptive_risk.initialized       = (g_adaptive_risk.initial_equity>0.0 &&
                                       g_adaptive_risk.high_water_equity>0.0 &&
                                       g_adaptive_risk.last_equity>0.0);
   return g_adaptive_risk.initialized;
}

//+------------------------------------------------------------------+
//| Update Risk Controller on Every Tick / Bar                       |
//+------------------------------------------------------------------+
bool RiskControllerUpdate()
{
   if(!g_adaptive_risk.initialized || !g_risk.initialized) return false;
   bool acquired_here=!g_risk_lock_owned;
   if(!RiskAcquireAccountLock()) return false;
   if(!RiskAccountRefresh())
   {
      g_risk.persistence_ok=false;
      if(acquired_here) RiskReleaseAccountLock();
      return false;
   }
   g_adaptive_risk.initial_equity=g_risk.initial_equity;
   g_adaptive_risk.high_water_equity=MathMax(g_adaptive_risk.high_water_equity,
                                             g_risk.adaptive_high_water);
   // Read after acquiring the account-wide lock. A caller-provided snapshot
   // may have gone stale while waiting behind another chart's ledger update.
   double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(!MathIsValidNumber(equity) || equity<=0.0)
   {
      if(acquired_here) RiskReleaseAccountLock();
      return false;
   }

   // Maintain the most recent equity observation for conservative daily
   // rollover. Persist at most once per execution bar (except a new high
   // water mark), avoiding a global-variable flush on every market tick.
   datetime observation_bar=iTime(g_cfg.symbol,g_cfg.tf_exec,0);
   bool observation_bar_due=(observation_bar>0 && observation_bar>g_last_equity_persist_bar);
   bool high_water_changed=(equity>g_adaptive_risk.high_water_equity);
   if(high_water_changed)
   {
      g_adaptive_risk.high_water_equity=equity;
      g_risk.initial_equity=g_adaptive_risk.initial_equity;
      g_risk.adaptive_high_water=equity;
   }
   g_adaptive_risk.last_equity=equity;
   g_risk.adaptive_last_equity=equity;
   bool ok=g_risk.persistence_ok;
   if(high_water_changed || observation_bar_due)
   {
      ok=RiskPersist(false);
      if(ok && observation_bar_due)
         g_last_equity_persist_bar=observation_bar;
   }
   bool released=true;
   if(acquired_here) released=RiskReleaseAccountLock();
   return ok && released;
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
   // Compatibility argument effective_risk_pct must not freeze R(E).
   if(!MathIsValidNumber(min_lot_loss) || min_lot_loss<=0.0 ||
      !MathIsValidNumber(max_distortion) || max_distortion<1.0 ||
      max_distortion>ABSOLUTE_MAX_DISTORTION) return 0.0;
   // Approved curve has nondecreasing E*R(E), including each spline segment.
   double lo=0.0, hi=10000.0;
   while(hi*InterpolateRiskCurve(hi)/100.0*max_distortion<min_lot_loss)
   {
      hi*=2.0;
      if(!MathIsValidNumber(hi)) return 0.0;
   }
   for(int i=0;i<100;i++)
   {
      double mid=lo+(hi-lo)/2.0;
      if(mid*InterpolateRiskCurve(mid)/100.0*max_distortion>=min_lot_loss) hi=mid;
      else lo=mid;
   }
   return hi;
}

double RiskControllerGetNormalEquity(double min_lot_loss)
{
   return RiskControllerGetMinimumViableEquity(min_lot_loss,0.0,1.0);
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
//| NOTE: Drawdown throttling removed per approved policy (P0)
//+------------------------------------------------------------------+
AdaptiveRiskResult RiskControllerEvaluate(
   string symbol,
   double entry,
   double stop,
   const AmigoConfig &cfg,
   bool daily_locked_status = false
)
{
   AdaptiveRiskResult res;
   ZeroMemory(res);

   double cur_eq=AccountInfoDouble(ACCOUNT_EQUITY);
   double cur_bal=AccountInfoDouble(ACCOUNT_BALANCE);

   if(!g_adaptive_risk.initialized || !RiskControllerUpdate())
   {
      res.trade_allowed=false;
      res.risk_state=RISK_STATE_UNSAFE;
      res.reason="RISK_LEDGER_UNAVAILABLE";
      return res;
   }

   // Synchronize the policy inputs with the post-lock account observation;
   // do not size from the equity snapshot captured before the ledger update.
   cur_eq=AccountInfoDouble(ACCOUNT_EQUITY);
   cur_bal=AccountInfoDouble(ACCOUNT_BALANCE);
   if(!MathIsValidNumber(cur_eq) || cur_eq<=0.0 ||
      !MathIsValidNumber(cur_bal) || cur_bal<0.0)
   {
      res.trade_allowed=false;
      res.risk_state=RISK_STATE_UNSAFE;
      res.reason="INVALID_ACCOUNT_EQUITY_OR_BALANCE";
      return res;
   }

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
   double vol_max = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
   double vol_step = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
   double tick_sz = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
   double tick_vl = AccountSymbolLossTickValue(symbol);
   if(!MathIsValidNumber(vol_min) || vol_min<=0.0 ||
      !MathIsValidNumber(vol_max) || vol_max<vol_min ||
      !MathIsValidNumber(vol_step) || vol_step<=0.0 ||
      !MathIsValidNumber(tick_sz) || tick_sz<=0.0 ||
      !MathIsValidNumber(tick_vl) || tick_vl<=0.0 ||
      !MathIsValidNumber(cur_eq) || cur_eq<=0.0)
   {
      res.risk_state=RISK_STATE_UNSAFE;
      res.trade_allowed=false;
      res.reason="INVALID_BROKER_RISK_METADATA";
      return res;
   }
   double minimum_valid_volume=AccountVolumeCeilToStep(vol_min,vol_step);
   double maximum_valid_volume=AccountVolumeFloorToStep(vol_max,vol_step);
   if(minimum_valid_volume<=0.0 || minimum_valid_volume<vol_min ||
      maximum_valid_volume<minimum_valid_volume)
   {
      res.risk_state=RISK_STATE_UNSAFE;
      res.trade_allowed=false;
      res.reason="INVALID_BROKER_VOLUME_GRID";
      return res;
   }
   res.minimum_lot = minimum_valid_volume;

   double stop_dist = MathAbs(entry - stop);
   double risk_per_lot = 0.0;
   if(tick_sz > 0.0 && tick_vl > 0.0 && stop_dist > 0.0)
   {
      risk_per_lot = (stop_dist / tick_sz) * tick_vl;
   }
   res.minimum_lot_loss = minimum_valid_volume * risk_per_lot;

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

   // 4. Effective Risk Percent (no drawdown throttle per approved policy)
   res.effective_risk_percent = MathMin(res.base_risk_percent, ABSOLUTE_MAX_RISK_PERCENT);
   res.risk_state = RISK_STATE_NORMAL;

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

   // 8. Absolute Risk Cap enforcement (Prompt §4)
   // The distortion policy must not override the absolute 2% exposure ceiling.
   double actual_risk_pct = (res.equity > 0.0) ? (res.minimum_lot_loss / res.equity * 100.0) : 0.0;
   if(actual_risk_pct > (ABSOLUTE_MAX_RISK_PERCENT + 0.00001))
   {
      res.risk_state    = RISK_STATE_UNSAFE;
      res.trade_allowed = false;
      res.reason        = "ESTIMATED_STOP_RISK_ABOVE_2PCT";
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

