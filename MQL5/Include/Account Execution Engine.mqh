//+------------------------------------------------------------------+
//| Account Execution Engine.mqh                                     |
//| Surgical Account Identification, Symbol Capability Profile,      |
//| Provenance Tagging, 3-State Min-Lot Sizing, Risk & Feasibility   |
//+------------------------------------------------------------------+
#property strict

#include <Contracts header.mqh>
#include <Configuration.mqh>
#include <Logger.mqh>

//--- Data Provenance / Source Enum (Prompt §19)
enum ENUM_DATA_SOURCE
{
   SRC_UNAVAILABLE              = 0,
   SRC_MT5_DIRECT               = 1,
   SRC_ORDERCALCPROFIT_FALLBACK = 2,
   SRC_DERIVED                  = 3
};

//--- Enums
enum ENUM_ACCOUNT_CLASS
{
   ACCOUNT_CLASS_UNKNOWN   = 0,
   ACCOUNT_CLASS_MICRO     = 1,   // < $100 (Thresholds: REQUIRES DECISION)
   ACCOUNT_CLASS_SMALL     = 2,   // $100 - $1,000
   ACCOUNT_CLASS_STANDARD  = 3,   // $1,000 - $10,000
   ACCOUNT_CLASS_LARGE     = 4,   // > $10,000
   ACCOUNT_CLASS_PROP      = 5    // Prop-firm challenge account
};

enum ENUM_MIN_LOT_STATUS
{
   MIN_LOT_NORMAL          = 0,   // RawVolume >= VolumeMin
   MIN_LOT_ACCOMMODATED    = 1,   // RawVolume < VolumeMin, but actual risk at min lot is safe
   MIN_LOT_UNSAFE          = 2    // RawVolume < VolumeMin, actual risk exceeds distortion limit
};

enum ENUM_ACCOUNT_FEASIBILITY
{
   FEASIBILITY_NORMAL                  = 0,
   FEASIBILITY_MIN_LOT_ACCOMMODATED    = 1,
   FEASIBILITY_MIN_LOT_UNSAFE          = 2,
   FEASIBILITY_MARGIN_BLOCKED          = 3,
   FEASIBILITY_BROKER_BLOCKED          = 4,
   FEASIBILITY_INVALID_SYMBOL_SPEC     = 5,
   FEASIBILITY_RISK_LIMIT_BLOCKED      = 6,
   FEASIBILITY_STOPS_INVALID           = 7
};

//--- Structs
struct AccountIdentification
{
   long              login;
   string            broker;
   string            server;
   string            currency;
   double            balance;
   double            equity;
   double            margin;
   double            margin_free;
   double            margin_level;
   double            leverage;
   bool              trade_allowed;
   bool              trade_expert;
   int               margin_mode;
   int               trade_mode;
   ENUM_ACCOUNT_CLASS account_class;
   datetime          timestamp;
   bool              valid;
   string            invalid_reason;
};

struct SymbolCapability
{
   string           symbol;
   int              digits;
   double           point;
   double           tick_size;
   double           tick_value;
   ENUM_DATA_SOURCE tick_value_source; // Provenance: DIRECT vs FALLBACK vs DERIVED
   double           tick_value_profit;
   double           tick_value_loss;
   double           contract_size;
   double           volume_min;
   double           volume_max;
   double           volume_step;
   long             stops_level;
   long             freeze_level;
   long             trade_mode;
   long             filling_mode;
   double           margin_initial;
   double           margin_maintenance;
   bool             valid;
   string           invalid_reason;
};

struct AccountExecutionEnvelope
{
   AccountIdentification account;
   SymbolCapability     symbol_cap;
   
   //--- Trade Geometry
   int      direction;
   double   entry;
   double   stop;
   double   target;
   double   stop_distance;
   
   //--- Risk Sizing Metrics
   double   target_risk_pct;
   double   target_risk_amount;
   double   risk_per_lot;
   double   raw_volume;
   double   executable_volume;
   double   actual_risk;
   double   actual_risk_pct;
   double   risk_distortion;
   double   required_margin;
   
   //--- Adaptive Stop-Loss Envelope Tracking (Prompt §4, §5, §19)
   double                    original_sl;
   double                    original_stop_distance;
   double                    adaptive_sl;
   double                    selected_sl;
   double                    max_account_stop_dist;
   ENUM_SL_ADAPTATION_STATUS sl_adapt_status;
   string                    sl_adapt_reason;

   //--- Execution Feasibility States
   ENUM_MIN_LOT_STATUS                  min_lot_status;
   ENUM_ACCOUNT_FEASIBILITY             feasibility;
   ENUM_SIGNAL_EXECUTION_CLASSIFICATION execution_classification;
   ENUM_ACTION                          final_action;
   string                               reason;
};

//+------------------------------------------------------------------+
//| Populate Account Identification Struct directly from MT5 runtime |
//+------------------------------------------------------------------+
void AccountIdentify(AccountIdentification &acc)
{
   ZeroMemory(acc);
   acc.timestamp     = TimeCurrent();
   acc.login         = AccountInfoInteger(ACCOUNT_LOGIN);
   acc.broker        = AccountInfoString(ACCOUNT_COMPANY);
   acc.server        = AccountInfoString(ACCOUNT_SERVER);
   acc.currency      = AccountInfoString(ACCOUNT_CURRENCY);
   acc.balance       = AccountInfoDouble(ACCOUNT_BALANCE);
   acc.equity        = AccountInfoDouble(ACCOUNT_EQUITY);
   acc.margin        = AccountInfoDouble(ACCOUNT_MARGIN);
   acc.margin_free   = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   acc.margin_level  = AccountInfoDouble(ACCOUNT_MARGIN_LEVEL);
   acc.leverage      = (double)AccountInfoInteger(ACCOUNT_LEVERAGE);
   acc.trade_allowed = (bool)AccountInfoInteger(ACCOUNT_TRADE_ALLOWED);
   acc.trade_expert  = (bool)AccountInfoInteger(ACCOUNT_TRADE_EXPERT);
   acc.margin_mode   = (int)AccountInfoInteger(ACCOUNT_MARGIN_MODE);
   acc.trade_mode    = (int)AccountInfoInteger(ACCOUNT_TRADE_MODE);
   acc.valid         = true;
   acc.invalid_reason = "";

   //--- Account Classification (Note: Thresholds = REQUIRES DECISION)
   if(acc.equity < 100.0)
      acc.account_class = ACCOUNT_CLASS_MICRO;
   else if(acc.equity < 1000.0)
      acc.account_class = ACCOUNT_CLASS_SMALL;
   else if(acc.equity < 10000.0)
      acc.account_class = ACCOUNT_CLASS_STANDARD;
   else
      acc.account_class = ACCOUNT_CLASS_LARGE;
}

//+------------------------------------------------------------------+
//| Validate Account Identification (Prompt §4, §12 Fail-Closed)     |
//+------------------------------------------------------------------+
bool ValidateAccountIdentification(AccountIdentification &acc, string &err)
{
   err = "";
   if(acc.equity <= 0.0)
   {
      err = "INVALID_ACCOUNT_EQUITY_ZERO";
      acc.valid = false; acc.invalid_reason = err;
      return false;
   }
   if(StringLen(acc.currency) == 0)
   {
      err = "INVALID_ACCOUNT_CURRENCY_EMPTY";
      acc.valid = false; acc.invalid_reason = err;
      return false;
   }
   if(!acc.trade_allowed)
   {
      err = "ACCOUNT_TRADE_NOT_ALLOWED";
      acc.valid = false; acc.invalid_reason = err;
      return false;
   }
   if(!acc.trade_expert)
   {
      err = "ACCOUNT_EXPERT_DISABLED";
      acc.valid = false; acc.invalid_reason = err;
      return false;
   }
   acc.valid = true;
   return true;
}

//+------------------------------------------------------------------+
//| Build Runtime Symbol Capability Profile with Provenance Tagging   |
//+------------------------------------------------------------------+
void SymbolCapabilityBuild(string symbol, SymbolCapability &cap)
{
   ZeroMemory(cap);
   cap.symbol             = symbol;
   cap.digits             = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   cap.point              = SymbolInfoDouble(symbol, SYMBOL_POINT);
   cap.tick_size          = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
   cap.tick_value         = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
   cap.tick_value_profit  = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE_PROFIT);
   cap.tick_value_loss    = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE_LOSS);
   cap.contract_size      = SymbolInfoDouble(symbol, SYMBOL_TRADE_CONTRACT_SIZE);
   cap.volume_min         = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   cap.volume_max         = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
   cap.volume_step        = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
   cap.stops_level        = SymbolInfoInteger(symbol, SYMBOL_TRADE_STOPS_LEVEL);
   cap.freeze_level       = SymbolInfoInteger(symbol, SYMBOL_TRADE_FREEZE_LEVEL);
   cap.trade_mode         = SymbolInfoInteger(symbol, SYMBOL_TRADE_MODE);
   cap.filling_mode       = SymbolInfoInteger(symbol, SYMBOL_FILLING_MODE);
   cap.margin_initial     = SymbolInfoDouble(symbol, SYMBOL_MARGIN_INITIAL);
   cap.margin_maintenance = SymbolInfoDouble(symbol, SYMBOL_MARGIN_MAINTENANCE);
   cap.valid              = true;
   cap.invalid_reason     = "";

   if(cap.tick_value > 0.0)
   {
      cap.tick_value_source = SRC_MT5_DIRECT;
   }
   else
   {
      cap.tick_value_source = SRC_UNAVAILABLE;
      //--- Fallback: OrderCalcProfit for tick_value resolution (Prompt §6)
      if(cap.tick_size > 0.0)
      {
         double test_profit = 0.0;
         double ref_price   = SymbolInfoDouble(symbol, SYMBOL_ASK);
         if(ref_price <= 0.0) ref_price = 2000.0;
         if(OrderCalcProfit(ORDER_TYPE_BUY, symbol, 1.0, ref_price, ref_price + cap.tick_size, test_profit))
         {
            if(test_profit > 0.0)
            {
               cap.tick_value        = test_profit;
               cap.tick_value_source = SRC_ORDERCALCPROFIT_FALLBACK;
               LogMsg(LOG_INFO, "SYMBOL_CAP", StringFormat("Resolved TICK_VALUE via OrderCalcProfit fallback: %.5f (SRC=ORDERCALCPROFIT_FALLBACK)", cap.tick_value));
            }
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Deterministic Contract-Spec Validation (Prompt §6)              |
//+------------------------------------------------------------------+
bool ValidateSymbolCapability(SymbolCapability &cap, string &err)
{
   err = "";
   if(cap.tick_size <= 0.0)
   {
      err = "INVALID_TICK_SIZE";
      cap.valid = false; cap.invalid_reason = err;
      return false;
   }
   if(cap.tick_value <= 0.0)
   {
      err = "INVALID_TICK_VALUE";
      cap.valid = false; cap.invalid_reason = err;
      return false;
   }
   if(cap.contract_size <= 0.0)
   {
      err = "INVALID_CONTRACT_SIZE";
      cap.valid = false; cap.invalid_reason = err;
      return false;
   }
   if(cap.volume_min <= 0.0)
   {
      err = "INVALID_VOLUME_MIN";
      cap.valid = false; cap.invalid_reason = err;
      return false;
   }
   if(cap.volume_step <= 0.0)
   {
      err = "INVALID_VOLUME_STEP";
      cap.valid = false; cap.invalid_reason = err;
      return false;
   }
   if(cap.volume_max < cap.volume_min)
   {
      err = "INVALID_VOLUME_MAX";
      cap.valid = false; cap.invalid_reason = err;
      return false;
   }
   if(cap.digits < 0)
   {
      err = "INVALID_DIGITS";
      cap.valid = false; cap.invalid_reason = err;
      return false;
   }
   if(cap.point <= 0.0)
   {
      err = "INVALID_POINT";
      cap.valid = false; cap.invalid_reason = err;
      return false;
   }
   cap.valid = true;
   return true;
}

//+------------------------------------------------------------------+
//| Account Execution Evaluation Engine                              |
//+------------------------------------------------------------------+
AccountExecutionEnvelope AccountExecutionEvaluate(
   string symbol,
   int direction,
   double entry,
   double stop,
   double target,
   double target_risk_pct,
   const AlgoMindConfig &cfg,
   ENUM_ACTION strategy_proposed_action
)
{
   AccountExecutionEnvelope env;
   ZeroMemory(env);
   
   env.direction       = direction;
   env.entry           = entry;
   env.stop            = stop;
   env.target          = target;
   env.stop_distance   = MathAbs(entry - stop);
   env.target_risk_pct = target_risk_pct;
   env.final_action    = ACTION_NO_TRADE;
   env.reason          = "UNINITIALIZED";

   //--- 1. Account Identification & Live Query
   AccountIdentify(env.account);

   //--- 2. Account Validation (Fail-Closed Prompt §4, §12)
   string acc_err;
   if(!ValidateAccountIdentification(env.account, acc_err))
   {
      env.feasibility              = FEASIBILITY_BROKER_BLOCKED;
      env.execution_classification = SIGNAL_VALID_BROKER_INFEASIBLE;
      env.final_action             = ACTION_NO_TRADE;
      env.reason                   = "ACCOUNT_INVALID:" + acc_err;
      LogAccountExecutionDiagnostic(env);
      return env;
   }

   //--- 3. Symbol Capability Profile & Provenance
   SymbolCapabilityBuild(symbol, env.symbol_cap);

   //--- 4. Contract-Spec Validation (Prompt §6)
   string spec_err;
   if(!ValidateSymbolCapability(env.symbol_cap, spec_err))
   {
      env.feasibility              = FEASIBILITY_INVALID_SYMBOL_SPEC;
      env.execution_classification = SIGNAL_VALID_BROKER_INFEASIBLE;
      env.final_action             = ACTION_NO_TRADE;
      env.reason                   = "INVALID_SYMBOL_SPEC:" + spec_err;
      LogAccountExecutionDiagnostic(env);
      return env;
   }

   //--- 5. Account/Broker Permission Check
   if(env.symbol_cap.trade_mode == SYMBOL_TRADE_MODE_DISABLED)
   {
      env.feasibility              = FEASIBILITY_BROKER_BLOCKED;
      env.execution_classification = SIGNAL_VALID_BROKER_INFEASIBLE;
      env.final_action             = ACTION_NO_TRADE;
      env.reason                   = "SYMBOL_TRADE_MODE_DISABLED";
      LogAccountExecutionDiagnostic(env);
      return env;
   }

   //--- 6. Strategy Gate Respect (Account layer MUST NEVER override a strategy NO_TRADE)
   if(strategy_proposed_action != ACTION_TRADE)
   {
      env.execution_classification = SIGNAL_INVALID;
      env.final_action             = strategy_proposed_action;
      env.reason                   = "STRATEGY_NOT_TRADE";
      return env;
   }

   //--- 7. Geometry & Stop Distance Validation
   if(env.stop_distance <= 0.0)
   {
      env.feasibility              = FEASIBILITY_STOPS_INVALID;
      env.execution_classification = SIGNAL_VALID_BROKER_INFEASIBLE;
      env.final_action             = ACTION_NO_TRADE;
      env.reason                   = "ZERO_STOP_DISTANCE";
      LogAccountExecutionDiagnostic(env);
      return env;
   }

   double min_stop_dist = env.symbol_cap.stops_level * env.symbol_cap.point;
   if(min_stop_dist > 0.0 && env.stop_distance < min_stop_dist)
   {
      env.feasibility              = FEASIBILITY_STOPS_INVALID;
      env.execution_classification = SIGNAL_VALID_BROKER_INFEASIBLE;
      env.final_action             = ACTION_NO_TRADE;
      env.reason                   = "STOP_BELOW_STOPS_LEVEL";
      LogAccountExecutionDiagnostic(env);
      return env;
   }

   //--- 8. Risk Sizing & 3-State Minimum Lot Sizing (Prompt §9, §10, §11)
   env.target_risk_amount = env.account.equity * (target_risk_pct / 100.0);
   env.risk_per_lot       = (env.symbol_cap.tick_size > 0.0) ? ((env.stop_distance / env.symbol_cap.tick_size) * env.symbol_cap.tick_value) : 0.0;
   
   if(env.risk_per_lot <= 0.0)
   {
      env.feasibility              = FEASIBILITY_INVALID_SYMBOL_SPEC;
      env.execution_classification = SIGNAL_VALID_BROKER_INFEASIBLE;
      env.final_action             = ACTION_NO_TRADE;
      env.reason                   = "ZERO_RISK_PER_LOT";
      LogAccountExecutionDiagnostic(env);
      return env;
   }

   env.raw_volume = env.target_risk_amount / env.risk_per_lot;

   //--- 3-State Evaluation
   if(env.raw_volume >= env.symbol_cap.volume_min)
   {
      // STATE A: NORMAL
      env.min_lot_status    = MIN_LOT_NORMAL;
      env.executable_volume = MathFloor(env.raw_volume / env.symbol_cap.volume_step) * env.symbol_cap.volume_step;
      if(env.executable_volume < env.symbol_cap.volume_min) env.executable_volume = env.symbol_cap.volume_min;
      if(env.executable_volume > env.symbol_cap.volume_max) env.executable_volume = env.symbol_cap.volume_max;

      env.actual_risk     = env.executable_volume * env.risk_per_lot;
      env.actual_risk_pct = (env.account.equity > 0.0) ? (env.actual_risk / env.account.equity * 100.0) : 0.0;
      env.risk_distortion = (env.target_risk_amount > 0.0) ? (env.actual_risk / env.target_risk_amount) : 1.0;
      env.feasibility     = FEASIBILITY_NORMAL;
      env.execution_classification = SIGNAL_VALID_EXECUTABLE;
   }
   else
   {
      // Raw Volume < VolumeMin
      double min_lot_risk     = env.symbol_cap.volume_min * env.risk_per_lot;
      double min_lot_risk_pct = (env.account.equity > 0.0) ? (min_lot_risk / env.account.equity * 100.0) : 999.0;
      double distortion       = (env.target_risk_amount > 0.0) ? (min_lot_risk / env.target_risk_amount) : 999.0;

      double max_distortion = (cfg.max_allowed_distortion > 0.0) ? cfg.max_allowed_distortion : 1.0;

      if(cfg.allow_min_lot_override && distortion <= max_distortion)
      {
         // STATE B: MINIMUM-LOT ACCOMMODATED
         env.min_lot_status           = MIN_LOT_ACCOMMODATED;
         env.executable_volume        = env.symbol_cap.volume_min;
         env.actual_risk              = min_lot_risk;
         env.actual_risk_pct          = min_lot_risk_pct;
         env.risk_distortion          = distortion;
         env.feasibility              = FEASIBILITY_MIN_LOT_ACCOMMODATED;
         env.execution_classification = SIGNAL_VALID_EXECUTABLE;
      }
      else
      {
         // STATE C: MINIMUM-LOT UNSAFE
         env.min_lot_status           = MIN_LOT_UNSAFE;
         env.executable_volume        = 0.0;
         env.actual_risk              = min_lot_risk;
         env.actual_risk_pct          = min_lot_risk_pct;
         env.risk_distortion          = distortion;
         env.feasibility              = FEASIBILITY_MIN_LOT_UNSAFE;
         env.execution_classification = SIGNAL_VALID_ACCOUNT_INFEASIBLE;
         env.final_action             = ACTION_NO_TRADE;
         env.reason                   = "MIN_LOT_UNSAFE";
         LogAccountExecutionDiagnostic(env);
         return env;
      }
   }

   //--- 9. Margin Verification
   double margin_required = 0.0;
   if(OrderCalcMargin((direction == +1) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL, symbol, env.executable_volume, entry, margin_required))
   {
      env.required_margin = margin_required;
   }
   else
   {
      // Fallback margin estimate using leverage
      double lev = (env.account.leverage > 0.0) ? env.account.leverage : 100.0;
      env.required_margin = (env.executable_volume * env.symbol_cap.contract_size * entry) / lev;
   }

   if(env.account.margin_free > 0.0 && env.required_margin > env.account.margin_free * 0.95)
   {
      env.feasibility              = FEASIBILITY_MARGIN_BLOCKED;
      env.execution_classification = SIGNAL_VALID_ACCOUNT_INFEASIBLE;
      env.final_action             = ACTION_NO_TRADE;
      env.reason                   = "INSUFFICIENT_MARGIN";
      LogAccountExecutionDiagnostic(env);
      return env;
   }

   //--- 10. Final Action Resolution
   env.execution_classification = SIGNAL_VALID_EXECUTABLE;
   env.final_action             = ACTION_TRADE;
   env.reason                   = (env.min_lot_status == MIN_LOT_ACCOMMODATED) ? "MIN_LOT_ACCOMMODATED" : "OK";

   //--- 11. Structured Diagnostic Output (Prompt §15, §19 Data Provenance)
   LogAccountExecutionDiagnostic(env);

   return env;
}

//+------------------------------------------------------------------+
//| Emit Structured Diagnostic Log with Data Provenance Tagging       |
//+------------------------------------------------------------------+
void LogAccountExecutionDiagnostic(const AccountExecutionEnvelope &env)
{
   string class_name = (env.account.account_class == ACCOUNT_CLASS_MICRO)    ? "MICRO" :
                       (env.account.account_class == ACCOUNT_CLASS_SMALL)    ? "SMALL" :
                       (env.account.account_class == ACCOUNT_CLASS_STANDARD) ? "STANDARD" :
                       (env.account.account_class == ACCOUNT_CLASS_LARGE)    ? "LARGE" : "PROP";

   string min_lot_str = (env.min_lot_status == MIN_LOT_NORMAL)       ? "NORMAL" :
                        (env.min_lot_status == MIN_LOT_ACCOMMODATED) ? "ACCOMMODATED" : "UNSAFE";

   string act_str = (env.final_action == ACTION_TRADE) ? "TRADE" :
                    (env.final_action == ACTION_REDUCE) ? "REDUCE" :
                    (env.final_action == ACTION_WAIT)   ? "WAIT" : "NO_TRADE";

   string src_str = (env.symbol_cap.tick_value_source == SRC_MT5_DIRECT)               ? "MT5_DIRECT" :
                    (env.symbol_cap.tick_value_source == SRC_ORDERCALCPROFIT_FALLBACK) ? "ORDERCALCPROFIT_FALLBACK" :
                    (env.symbol_cap.tick_value_source == SRC_DERIVED)                  ? "DERIVED" : "UNAVAILABLE";

   string class_str = (env.execution_classification == SIGNAL_VALID_EXECUTABLE)         ? "SIGNAL_VALID_EXECUTABLE" :
                      (env.execution_classification == SIGNAL_VALID_ACCOUNT_INFEASIBLE)  ? "SIGNAL_VALID_ACCOUNT_INFEASIBLE" :
                      (env.execution_classification == SIGNAL_VALID_BROKER_INFEASIBLE)   ? "SIGNAL_VALID_BROKER_INFEASIBLE" : "SIGNAL_INVALID";

   PrintFormat("[ACCOUNT_ID] login=%I64d company=%s server=%s currency=%s balance=%.2f equity=%.2f free_margin=%.2f leverage=%.0f margin_mode=%d trade_allowed=%s expert_allowed=%s class=%s",
               env.account.login, env.account.broker, env.account.server, env.account.currency,
               env.account.balance, env.account.equity, env.account.margin_free, env.account.leverage,
               env.account.margin_mode, env.account.trade_allowed ? "YES" : "NO", env.account.trade_expert ? "YES" : "NO", class_name);

   PrintFormat("[SYMBOL_CAP] symbol=%s digits=%d point=%.5f tick_sz=%.5f tick_val=%.5f(src=%s) contract_sz=%.1f vol_min=%.2f vol_step=%.2f vol_max=%.2f stops_lvl=%I64d freeze_lvl=%I64d trade_mode=%I64d fill_mode=%I64d valid=%s",
               env.symbol_cap.symbol, env.symbol_cap.digits, env.symbol_cap.point, env.symbol_cap.tick_size, env.symbol_cap.tick_value, src_str,
               env.symbol_cap.contract_size, env.symbol_cap.volume_min, env.symbol_cap.volume_step, env.symbol_cap.volume_max,
               env.symbol_cap.stops_level, env.symbol_cap.freeze_level, env.symbol_cap.trade_mode, env.symbol_cap.filling_mode, env.symbol_cap.valid ? "PASS" : "FAIL");

   PrintFormat("[SETUP] dir=%s entry=%.5f sl=%.5f tp=%.5f stop_dist=%.5f",
               (env.direction == +1) ? "BUY" : "SELL", env.entry, env.stop, env.target, env.stop_distance);

   PrintFormat("[RISK] target_risk=$%.2f(%.2f%%) risk_per_lot=$%.2f raw_vol=%.5f exec_vol=%.2f actual_risk=$%.2f(%.2f%%) distortion=%.2fx",
               env.target_risk_amount, env.target_risk_pct, env.risk_per_lot, env.raw_volume, env.executable_volume,
               env.actual_risk, env.actual_risk_pct, env.risk_distortion);

   PrintFormat("[ACCOUNT_HANDLING] class=%s status=%d min_lot_status=%s margin_req=$%.2f",
               class_name, (int)env.feasibility, min_lot_str, env.required_margin);

   string adapt_status_str = (env.sl_adapt_status == ORIGINAL_SL_EXECUTABLE) ? "ORIGINAL_SL_EXECUTABLE" :
                             (env.sl_adapt_status == ADAPTIVE_SL_REQUIRED)   ? "ADAPTIVE_SL_REQUIRED" :
                             (env.sl_adapt_status == ADAPTIVE_SL_ACCEPTED)   ? "ACCEPTED" :
                             (env.sl_adapt_status == ADAPTIVE_SL_REJECTED)   ? "REJECTED" : "NO_VALID_SL";

   double rr_val = (env.stop_distance > 0.0) ? (MathAbs(env.target - env.entry) / env.stop_distance) : 0.0;

   PrintFormat("[AlgoMind][SL_ADAPT] sym=%s dir=%s entry=%.5f original_sl=%.5f original_dist=%.5f adaptive_required=%d max_account_stop_dist=%.5f candidate_sl=%.5f candidate_dist=%.5f selected_sl=%.5f rr=%.2f target_risk=%.2f actual_risk=%.2f actual_risk_pct=%.2f final_volume=%.2f status=%s reason=%s",
               env.symbol_cap.symbol, (env.direction == +1) ? "BUY" : "SELL", env.entry, env.original_sl, env.original_stop_distance,
               (env.sl_adapt_status != ORIGINAL_SL_EXECUTABLE) ? 1 : 0, env.max_account_stop_dist, env.adaptive_sl,
               (env.adaptive_sl > 0.0) ? MathAbs(env.entry - env.adaptive_sl) : 0.0, env.selected_sl, rr_val,
               env.target_risk_amount, env.actual_risk, env.actual_risk_pct, env.executable_volume,
               adapt_status_str, (StringLen(env.sl_adapt_reason) > 0) ? env.sl_adapt_reason : env.reason);

   //--- Comprehensive Auditable Size Diagnostic (Prompt REQ-07)
   double max_distortion = (g_cfg.max_allowed_distortion > 0.0) ? g_cfg.max_allowed_distortion : 1.0;
   double max_risk_allowed = env.target_risk_amount * max_distortion;
   double stop_dist_ticks = (env.symbol_cap.tick_size > 0.0) ? (env.stop_distance / env.symbol_cap.tick_size) : 0.0;
   double min_lot_loss = env.symbol_cap.volume_min * env.risk_per_lot;
   double target_risk_pct_dec = (g_cfg.risk_per_trade_pct > 0.0) ? (g_cfg.risk_per_trade_pct / 100.0) : 0.005;
   double req_equity = (target_risk_pct_dec * max_distortion > 0.0) ? (min_lot_loss / (target_risk_pct_dec * max_distortion)) : 0.0;
   double broker_min_stop = env.symbol_cap.stops_level * env.symbol_cap.point;
   string sl_source_str = (env.sl_adapt_status == ADAPTIVE_SL_ACCEPTED) ? env.sl_adapt_reason : "PRIMARY_STRUCTURE";
   int cand_count = (env.sl_adapt_status != ORIGINAL_SL_EXECUTABLE) ? 2 : 1;
   int exec_cand_count = (env.sl_adapt_status == ADAPTIVE_SL_ACCEPTED || env.sl_adapt_status == ORIGINAL_SL_EXECUTABLE) ? 1 : 0;

   PrintFormat("[SIZE_DIAG] equity=%.2f target_risk=%.2f max_risk=%.2f entry=%.5f primary_sl=%.5f selected_sl=%.5f sl_source=%s stop_dist_price=%.5f stop_dist_ticks=%.0f min_volume=%.2f min_lot_loss=%.2f distortion=%.2fx max_distortion=%.2fx required_equity=%.2f broker_min_stop=%.5f rr=%.2f candidate_count=%d executable_candidate_count=%d classification=%s reason=%s",
               env.account.equity, env.target_risk_amount, max_risk_allowed, env.entry,
               env.original_sl, env.selected_sl, sl_source_str, env.stop_distance,
               stop_dist_ticks, env.symbol_cap.volume_min, min_lot_loss, env.risk_distortion,
               max_distortion, req_equity, broker_min_stop, rr_val,
               cand_count, exec_cand_count, class_str, env.reason);

   PrintFormat("[FINAL_ACTION] action=%s classification=%s reason=%s", act_str, class_str, env.reason);
}
//+------------------------------------------------------------------+
