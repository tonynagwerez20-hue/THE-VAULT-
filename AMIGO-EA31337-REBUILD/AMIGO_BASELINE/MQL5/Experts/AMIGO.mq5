//+------------------------------------------------------------------+
//|                                                     Amigo.mq5 |
//|                    Deterministic MQL5-first trading core         |
//|                    (ML gate present but disabled by default)     |
//+------------------------------------------------------------------+
#property copyright "Amigo"
#property version   "1.00"
#property strict

//--- Project includes (flat layout under MQL5\Include\)
#include <Contracts header.mqh>
#include <Configuration.mqh>
#include <Logger.mqh>
#include <Market Snapshot Builder.mqh>
#include <Bar Collector.mqh>
#include <OrderFlow.mqh>
#include <Structure Engine.mqh>
#include <FVG Engine.mqh>
#include <Auction.mqh>
#include <FeatureVector.mqh>
#include <Chronology Validation.mqh>
#include <Regime Engine.mqh>
#include <Strategy Engine.mqh>
#include <Risk Engine.mqh>
#include <Account Execution Engine.mqh>
#include <RiskController.mqh>
#include <Execution Engine.mqh>
#include <Position Manager.mqh>
#include <TransactionRecon.mqh>
#include <External Context Compactor.mqh>
#include <ML gate hook.mqh>
#include <TickImbalanceBars.mqh>

//--- Order-Flow ASAP / Amigo Native Engines
#include <AM_FlowQuality.mqh>
#include <AM_ProxyVWAP.mqh>
#include <AM_ActivityProfile.mqh>
#include <AM_Footprint.mqh>
#include <AM_FlowPressure.mqh>
#include <AM_FlowEvents.mqh>
#include <AM_ProxyDOM.mqh>

//--- Inputs
input group "=== Execution Mode Safety ==="
input bool   InpShadowOnly        = true;         // true = SHADOW MODE (blocks live OrderSend)
   input bool   InpEnableTickPressure = false;      // Experimental proxy scoring; disabled by default
input bool   InpInitializeRiskLedger = false;     // Explicit baseline only if no persistent ledger exists

input group "=== Symbol & Timeframes ==="
input string InpSymbol            = "";           // empty = current symbol
input ENUM_TIMEFRAMES InpTFD1     = PERIOD_D1;  // D1 macro context
input ENUM_TIMEFRAMES InpTFH4     = PERIOD_H4;  // H4 swing context
input ENUM_TIMEFRAMES InpTFHTF    = PERIOD_H1;  // H1 directional context
input ENUM_TIMEFRAMES InpTFM30    = PERIOD_M30; // M30 structure
input ENUM_TIMEFRAMES InpTFContext= PERIOD_M15; // M15 local context
input ENUM_TIMEFRAMES InpTFM5     = PERIOD_M5;  // M5 setup structure
input ENUM_TIMEFRAMES InpTFExec   = PERIOD_M1;  // M1 execution and microstructure

input group "=== Risk (starting research params) ==="
input double InpRiskPerTrade      = 0.5;     // % per trade
input double InpDailyLossPct      = 2.0;     // % hard daily
input double InpTotalDDPct        = 5.0;     // % hard total DD
input double InpPartialRR         = 2.0;
input double InpPartialFraction   = 0.50;
input double InpTrailATRMult      = 1.5;
input double InpTrailActivateR    = 1.0;
input ENUM_TRAILING_MODE InpTrailMode = TRAIL_DYNAMIC_25_PERCENT; // Trailing mode
input bool   InpAllowMinLotOverride   = true;    // Allow min lot override up to max distortion
input double InpMaxAllowedDistortion  = 5.0;     // Max allowed risk distortion (5.0 = 5x)


input group "=== Spread ==="
input double InpMaxSpreadPoints   = 0.0;     // 0 = disabled
input double InpMaxSpreadATRPct   = 0.10;    // spread <= 10% of stop distance

input group "=== Session (server time) ==="
input int    InpSessionStartHour  = 0;
input int    InpSessionEndHour    = 24;

input group "=== News ==="
input int    InpNewsMode          = 0;       // 0=OFF 1=FILTER 2=POST-RELEASE TRADE 3=HYBRID (experimental)
input int    InpNewsBufferMins    = AMIGO_NEWS_BUFFER_MINUTES;

input group "=== External influence caps ==="
input double InpCFTCMaxInfluence  = 0.05;
input double InpOptionsMaxInfl    = 0.10;

input group "=== Strategy Thresholds ==="
input double InpScoreThreshold     = 0.35;    // Min score required to trade
input double InpScoreMargin        = 0.05;    // Min score difference between long & short

input group "=== Bridge ==="
input string InpBridgeInbox       = "Amigo_ext_in.txt";
input string InpBridgeOutbox      = "Amigo_mkt_out.txt";
input int    InpStaleThresholdSec = 120;

input group "=== ML (Phase 8 - disabled by default) ==="
input bool   InpMLEnabled         = false;
input string InpMLModelPath       = "";

input group "=== Logging ==="
input int    InpLogLevel          = 1;       // 0=DEBUG 1=INFO 2=WARN 3=ERROR

input group "=== Dual-Account Isolation ==="
input long   InpExpectedLogin     = 0;        // 0 = unconstrained
input ulong  InpMagicNumber       = 20260908; // Scoped Magic Number

input group "=== Tick imbalance confirmation ==="
input int InpTIBThreshold=100; // Same quote imbalance threshold as Python reference.

//--- Globals
TickImbalanceBars g_tib;
TIBBar g_tib_decision;
bool g_tib_decision_ready=false;
datetime g_tib_last_boundary=0;
string          g_symbol;
datetime        g_last_bar_time = 0;
datetime        g_last_ext_read = 0;
ExternalContext g_ext;
MarketSnapshot  g_snap;
FeatureSnapshot g_feat;
bool            g_risk_admission_ready = false;

//--- Order-Flow Engine Instances
CAM_ProxyVWAP       g_vwap_engine;
CAM_Footprint       g_footprint_engine;
CAM_ActivityProfile g_profile_engine;
CAM_FlowPressure    g_pressure_engine;
CAM_FlowEvents      g_events_engine;
bool                g_flow_session_initialized = false;
bool                g_flow_was_in_session = false;
int                 g_flow_last_session_open_epoch = -1;

bool AMIGOScoreInputsValid(const double score_threshold,const double score_margin)
{
   return MathIsValidNumber(score_threshold) && score_threshold>0.0 && score_threshold<=1.0 &&
          MathIsValidNumber(score_margin) && score_margin>0.0 && score_margin<=1.0;
}

bool AMIGOPartialInputsValid(const double partial_rr,const double partial_fraction)
{
   return MathIsValidNumber(partial_rr) && partial_rr>=2.0 &&
          MathIsValidNumber(partial_fraction) && partial_fraction>0.0 && partial_fraction<1.0;
}

bool AMIGOTrailingInputsValid(const ENUM_TRAILING_MODE mode,const double atr_mult,
                              const double activate_r)
{
   if(mode!=TRAIL_OFF && mode!=TRAIL_DYNAMIC_25_PERCENT && mode!=TRAIL_ATR)
      return false;
   if(mode==TRAIL_ATR &&
      (!MathIsValidNumber(atr_mult) || atr_mult<=0.0 ||
       !MathIsValidNumber(activate_r) || activate_r<=0.0))
      return false;
   return true;
}

// Diagnostic bar-state is advanced only after a complete opportunity has
// reached an accepted outcome. It is never used as strategy authority.
void CommitFlowOpportunityDiagnostics(const MqlRates &closed_rate[],
                                      const datetime decision_boundary,
                                      const double atr)
{
   if(!InpEnableTickPressure) return;
   if(ArraySize(closed_rate)<=0 || closed_rate[0].time<=0 ||
      !MathIsValidNumber(closed_rate[0].high) || !MathIsValidNumber(closed_rate[0].low) ||
      closed_rate[0].high<closed_rate[0].low) return;

   double fp_pressure=g_footprint_engine.CalculateFootprintPressure();
   MQL_FootprintBin bins[];
   g_footprint_engine.GetBins(bins);
   g_profile_engine.Compute(bins,ArraySize(bins));
   ENUM_PRESSURE_STATE p_state=g_pressure_engine.ClassifyState(fp_pressure);
   double total_activity=g_footprint_engine.GetTotalActivity();
   g_pressure_engine.UpdateState(fp_pressure,total_activity,p_state);
   g_events_engine.AddBar(decision_boundary,fp_pressure,p_state,
                          closed_rate[0].high,closed_rate[0].low,total_activity);

   double current_price=SymbolInfoDouble(g_symbol,SYMBOL_BID);
   LogMsg(LOG_INFO,"FLOW_DIAG",StringFormat("ts=%s vwap=%.5f dev=%.2f poc=%.5f vah=%.5f val=%.5f cd=%.2f fp_press=%.4f state=%d shadow=%s",
      TimeToString(TimeCurrent(),TIME_DATE|TIME_MINUTES),g_vwap_engine.GetVWAP(),
      g_vwap_engine.GetDeviation(current_price,atr),g_profile_engine.GetPOC(),
      g_profile_engine.GetVAH(),g_profile_engine.GetVAL(),g_footprint_engine.GetCumulativeDelta(),
      fp_pressure,(int)p_state,g_cfg.shadow_only?"TRUE":"FALSE"));
}
CAM_ProxyDOM        g_dom_engine;

//+------------------------------------------------------------------+
int OnInit()
{
   if(!InpShadowOnly && !MQLInfoInteger(MQL_TESTER)) return INIT_PARAMETERS_INCORRECT;
   if(InpTIBThreshold<=0) return INIT_PARAMETERS_INCORRECT;
   g_tib.Reset(InpTIBThreshold);
   if(InpDailyLossPct!=2.0 || InpMaxAllowedDistortion<1.0 || InpMaxAllowedDistortion>5.0) return INIT_PARAMETERS_INCORRECT;
   LogInit(InpLogLevel);
   if(InpTFExec!=PERIOD_M1 || InpTFM5!=PERIOD_M5 || InpTFContext!=PERIOD_M15 ||
      InpTFM30!=PERIOD_M30 || InpTFHTF!=PERIOD_H1 || InpTFH4!=PERIOD_H4 || InpTFD1!=PERIOD_D1)
   {
      Print("[TIMEFRAME_CONFIG_ERROR] Required analysis ladder: D1,H4,H1,M30,M15,M5,M1; all entries execute on M1.");
      return INIT_PARAMETERS_INCORRECT;
   }


   if(!AMIGOScoreInputsValid(InpScoreThreshold,InpScoreMargin))
   {
      PrintFormat("[STRATEGY_CONFIG_ERROR] Score threshold and margin must be finite fractions in (0,1]. threshold=%.8f margin=%.8f. INIT_PARAMETERS_INCORRECT.",
                  InpScoreThreshold,InpScoreMargin);
      return INIT_PARAMETERS_INCORRECT;
   }
   if(!AMIGOPartialInputsValid(InpPartialRR,InpPartialFraction))
   {
      PrintFormat("[POSITION_CONFIG_ERROR] Partial RR must be finite and positive; partial fraction must be finite and strictly between zero and one. rr=%.8f fraction=%.8f. INIT_PARAMETERS_INCORRECT.",
                  InpPartialRR,InpPartialFraction);
      return INIT_PARAMETERS_INCORRECT;
   }
   if(!AMIGOTrailingInputsValid(InpTrailMode,InpTrailATRMult,InpTrailActivateR))
   {
      PrintFormat("[POSITION_CONFIG_ERROR] Trailing mode is unsupported or its ATR parameters are invalid. mode=%d atr_mult=%.8f activate_r=%.8f. INIT_PARAMETERS_INCORRECT.",
                  (int)InpTrailMode,InpTrailATRMult,InpTrailActivateR);
      return INIT_PARAMETERS_INCORRECT;
   }

   if(InpNewsMode<0 || InpNewsMode>3)
   {
      PrintFormat("[NEWS_CONFIG_ERROR] Unsupported InpNewsMode=%d; supported values are OFF(0), FILTER(1), post-release TRADE(2), HYBRID(3). INIT_PARAMETERS_INCORRECT.",InpNewsMode);
      return INIT_PARAMETERS_INCORRECT;
   }
   // Today's bridge file is not historical news evidence. Tester TimeGMT()
   // is simulated server time, not a verified historical UTC conversion.
   if((MQLInfoInteger(MQL_TESTER) || MQLInfoInteger(MQL_OPTIMIZATION)) && InpNewsMode!=0)
   {
      Print("[NEWS_REPLAY_REQUIRED] Historical news replay and broker-to-UTC mapping are not implemented. News-enabled testing rejected; no live-feed fallback.");
      return INIT_PARAMETERS_INCORRECT;
   }
   if(InpNewsBufferMins!=AMIGO_NEWS_BUFFER_MINUTES)
   {
      PrintFormat("[NEWS_CONFIG_ERROR] News buffer is fixed at %d minutes until bridge propagation is implemented. INIT_PARAMETERS_INCORRECT.",AMIGO_NEWS_BUFFER_MINUTES);
      return INIT_PARAMETERS_INCORRECT;
   }

   if(InpExpectedLogin > 0 && AccountInfoInteger(ACCOUNT_LOGIN) != InpExpectedLogin)
   {
      PrintFormat("[ACCOUNT_MISMATCH] Expected login %I64d but connected to %I64d. INIT_FAILED.",
                  InpExpectedLogin, AccountInfoInteger(ACCOUNT_LOGIN));
      return INIT_FAILED;
   }

   g_symbol = (StringLen(InpSymbol) > 0) ? InpSymbol : _Symbol;

   g_cfg.symbol              = g_symbol;
   g_cfg.magic_number        = InpMagicNumber;
   g_cfg.expected_login      = InpExpectedLogin;
   g_cfg.shadow_only         = InpShadowOnly;
   g_cfg.tf_exec             = InpTFExec;
   g_cfg.tf_context          = InpTFContext;
   g_cfg.tf_htf              = InpTFHTF;
   g_cfg.tf_m1               = InpTFExec; // same M1 boundary, not a second input
   g_cfg.tf_m30              = InpTFM30;
   g_cfg.tf_h4               = InpTFH4;
   g_cfg.atr_period          = 14;
   g_cfg.swing_k             = 2;
   g_cfg.zscore_window       = 20;
   g_cfg.value_area_pct      = 0.70;
   g_cfg.pressure_threshold  = 0.25;
   g_cfg.surge_threshold     = 0.35;
   g_cfg.score_threshold     = InpScoreThreshold;
   g_cfg.score_margin        = InpScoreMargin;
   g_cfg.regime_threshold    = 0.60;
   g_cfg.regime_hysteresis   = 0.10;
   g_cfg.regime_persistence  = 2;
   g_cfg.risk_per_trade_pct  = InpRiskPerTrade;
   g_cfg.daily_loss_pct      = InpDailyLossPct;
   g_cfg.total_dd_pct        = InpTotalDDPct;
   g_cfg.partial_rr          = InpPartialRR;
   g_cfg.partial_fraction    = InpPartialFraction;
   g_cfg.trail_atr_mult      = InpTrailATRMult;
   g_cfg.trail_activate_r    = InpTrailActivateR;
   g_cfg.trail_mode          = InpTrailMode;
   g_cfg.allow_min_lot_override = InpAllowMinLotOverride;
   g_cfg.max_allowed_distortion = InpMaxAllowedDistortion;
   g_cfg.max_spread_atr_pct  = InpMaxSpreadATRPct;
   g_cfg.max_spread_points   = InpMaxSpreadPoints;
   g_cfg.session_start_hour  = InpSessionStartHour;
   g_cfg.session_end_hour    = InpSessionEndHour;
   g_cfg.news_mode           = InpNewsMode;
   g_cfg.news_buffer_mins    = AMIGO_NEWS_BUFFER_MINUTES;
   g_cfg.cftc_max_influence  = InpCFTCMaxInfluence;
   g_cfg.options_max_influence = InpOptionsMaxInfl;
   g_cfg.ml_enabled          = InpMLEnabled;
   g_cfg.ml_model_path       = InpMLModelPath;
   g_cfg.tick_pressure_enabled = InpEnableTickPressure;
   g_cfg.bridge_inbox        = InpBridgeInbox;
   g_cfg.bridge_outbox       = InpBridgeOutbox;
   g_cfg.stale_threshold_s   = InpStaleThresholdSec;

   if(!g_cfg.shadow_only && AMIGO_LIVE_EXECUTION_READY==0)
   {
      Print("[LIVE_EXECUTION_BLOCKED] Durable order/deal reconciliation is not verified. Use shadow mode only.");
      return INIT_FAILED;
   }

   if(!PositionStateOwnerAcquire(g_cfg))
   {
      Print("[POSITION_OWNER] State namespace unavailable or owned by another instance; initialization blocked.");
      return INIT_FAILED;
   }
   bool risk_state_ready=RiskInit(InpInitializeRiskLedger);
   if(!risk_state_ready)
   {
      Print("[RISK_LEDGER] Persistent risk state missing, invalid or ambiguous; initialize explicitly before admission.");
   }
   else if(!RiskControllerInit())
   {
      Print("[RISK_LEDGER] Adaptive risk state could not be restored; new risk admission remains blocked.");
   }
   else g_risk_admission_ready=true;
   if(!ReconJournalInit(g_cfg))
   {
      g_risk_admission_ready=false;
      PositionManagerLatchStateFault("execution journal contains unresolved or unreadable evidence");
   }
   if(!ReconValidateRiskRecovery(g_cfg,g_risk_admission_ready,
                                 g_risk.last_opportunity_id,g_risk.last_opportunity_outcome))
   {
      g_risk_admission_ready=false;
      PositionManagerLatchStateFault("risk ledger and execution journal disagree or recovery is incomplete");
   }
   ZeroMemory(g_ext);

   //--- Start the position-manager / reconciliation timer.
   //--- Without this, OnTimer never fires and partials/trailing never run.
   //--- Reconcile and Recover Persistent Position State (Workstream C)
   int recovery_status=PositionReconcileState(g_cfg);
   if(recovery_status<0 && PositionRecoverMissingFileFromJournal(g_cfg))
      recovery_status=ArraySize(g_positions);
   if(recovery_status<0)
   {
      Print("[PERSIST_LOAD] Recovery state is ambiguous or invalid; EA initialization blocked.");
      return INIT_FAILED;
   }
   if(g_position_protection_repair_required)
   {
      Print("[POSITION_STOP_RECOVERY] Entry admission quarantined before ticks; timer-driven stop repair must be confirmed before the gate clears.");
   }
   if(ExecutionHasManagedWorkingOrder(g_cfg))
   {
      PositionManagerLatchStateFault("managed order exists or order enumeration is incomplete; manual reconciliation required");
      Print("[EXEC_RECOVERY] Managed working order found; new admission quarantined.");
   }

   if(!EventSetTimer(5))
   {
      g_risk_admission_ready=false;
      PrintFormat("[LIFECYCLE_TIMER_FAILED] Cannot start position management timer (err=%d); initialization blocked.",GetLastError());
      return INIT_FAILED;
   }

   LogMsg(LOG_INFO, "INIT", StringFormat("Amigo started on %s tf=%d ML=%s",
          g_symbol, (int)InpTFExec, InpMLEnabled?"ON":"OFF"));

   //--- Task 1 & 2: Complete Empirical Runtime Symbol & OrderCalcProfit Audit
   double ts = SymbolInfoDouble(g_symbol, SYMBOL_TRADE_TICK_SIZE);
   double tv = SymbolInfoDouble(g_symbol, SYMBOL_TRADE_TICK_VALUE);
   double tv_p = SymbolInfoDouble(g_symbol, SYMBOL_TRADE_TICK_VALUE_PROFIT);
   double tv_l = SymbolInfoDouble(g_symbol, SYMBOL_TRADE_TICK_VALUE_LOSS);
   double cs = SymbolInfoDouble(g_symbol, SYMBOL_TRADE_CONTRACT_SIZE);
   double v_min = SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_MIN);
   double v_step = SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_STEP);
   double v_max = SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_MAX);
   double v_min_valid = AccountVolumeCeilToStep(v_min,v_step);
   double tv_loss_risk = AccountSymbolLossTickValue(g_symbol);
   double pt = SymbolInfoDouble(g_symbol, SYMBOL_POINT);
   long   dg = SymbolInfoInteger(g_symbol, SYMBOL_DIGITS);

   PrintFormat("[P22_AUDIT][TASK1] TICK_SZ=%.5f TICK_VAL=%.5f TICK_VAL_PROF=%.5f TICK_VAL_LOSS=%.5f CS=%.1f VOL_MIN=%.2f VOL_STEP=%.2f VOL_MAX=%.2f PT=%.5f DIG=%d",
               ts, tv, tv_p, tv_l, cs, v_min, v_step, v_max, pt, (int)dg);

   // Task 2: OrderCalcProfit table for BUY and SELL
   double p_b_1_0001=0, p_b_1_0010=0, p_b_1_1000=0;
   double p_b_01_0001=0, p_b_01_0010=0, p_b_01_1000=0;
   double p_b_001_0001=0, p_b_001_0010=0, p_b_001_1000=0;
   bool ocp_ok = true;
   if(!MathIsValidNumber(v_min_valid) || v_min_valid<=0.0 ||
      !MathIsValidNumber(tv_loss_risk) || tv_loss_risk<=0.0)
      ocp_ok=false;
   ocp_ok &= OrderCalcProfit(ORDER_TYPE_BUY, g_symbol, 1.00, 2000.000, 2000.001, p_b_1_0001);
   ocp_ok &= OrderCalcProfit(ORDER_TYPE_BUY, g_symbol, 1.00, 2000.000, 2000.010, p_b_1_0010);
   ocp_ok &= OrderCalcProfit(ORDER_TYPE_BUY, g_symbol, 1.00, 2000.000, 2001.000, p_b_1_1000);

   ocp_ok &= OrderCalcProfit(ORDER_TYPE_BUY, g_symbol, 0.10, 2000.000, 2000.001, p_b_01_0001);
   ocp_ok &= OrderCalcProfit(ORDER_TYPE_BUY, g_symbol, 0.10, 2000.000, 2000.010, p_b_01_0010);
   ocp_ok &= OrderCalcProfit(ORDER_TYPE_BUY, g_symbol, 0.10, 2000.000, 2001.000, p_b_01_1000);

   ocp_ok &= OrderCalcProfit(ORDER_TYPE_BUY, g_symbol, 0.01, 2000.000, 2000.001, p_b_001_0001);
   ocp_ok &= OrderCalcProfit(ORDER_TYPE_BUY, g_symbol, 0.01, 2000.000, 2000.010, p_b_001_0010);
   ocp_ok &= OrderCalcProfit(ORDER_TYPE_BUY, g_symbol, 0.01, 2000.000, 2001.000, p_b_001_1000);

   PrintFormat("[P22_AUDIT][TASK2_BUY] 1.00lot(0.001=%.4f, 0.01=%.4f, 1.00=%.4f) | 0.10lot(0.001=%.4f, 0.01=%.4f, 1.00=%.4f) | 0.01lot(0.001=%.4f, 0.01=%.4f, 1.00=%.4f)",
               p_b_1_0001, p_b_1_0010, p_b_1_1000, p_b_01_0001, p_b_01_0010, p_b_01_1000, p_b_001_0001, p_b_001_0010, p_b_001_1000);

   double p_s_1_1000=0, p_s_01_1000=0, p_s_001_1000=0;
   ocp_ok &= OrderCalcProfit(ORDER_TYPE_SELL, g_symbol, 1.00, 2000.000, 1999.000, p_s_1_1000);
   ocp_ok &= OrderCalcProfit(ORDER_TYPE_SELL, g_symbol, 0.10, 2000.000, 1999.000, p_s_01_1000);
   ocp_ok &= OrderCalcProfit(ORDER_TYPE_SELL, g_symbol, 0.01, 2000.000, 1999.000, p_s_001_1000);
   PrintFormat("[P22_AUDIT][TASK2_SELL] 1.00lot(1.00=%.4f) | 0.10lot(1.00=%.4f) | 0.01lot(1.00=%.4f)",
               p_s_1_1000, p_s_01_1000, p_s_001_1000);

   // Task 4: Empirical ComputeLotSize vs OrderCalcProfit Audit
   double test_stops[7] = {0.50, 1.00, 1.50, 2.00, 2.50, 3.00, 5.00};
   for(int k=0; k<7; k++)
   {
      double st_d = test_stops[k];
      double act_risk = 0.0; string err = "";
      double raw_l = (ts>0.0 && tv_loss_risk>0.0) ? (2.50) / ((st_d / ts) * tv_loss_risk) : 0.0;
      double calc_lots = ComputeLotSize(g_symbol, 2000.0, 2000.0 - st_d, 0.5, act_risk, err);
      double ocp_min_loss = 0.0;
      if(v_min_valid<=0.0 || !OrderCalcProfit(ORDER_TYPE_BUY, g_symbol, v_min_valid, 2000.0, 2000.0 - st_d, ocp_min_loss))
      {
         ocp_ok = false;
      }
      double estimate_min_loss=(ts>0.0 && tv_loss_risk>0.0 && v_min_valid>0.0) ?
                               (st_d/ts)*tv_loss_risk*v_min_valid : 0.0;
      PrintFormat("[P22_AUDIT][TASK4] stop=%.2f risk_b=2.50 raw=%.5f norm=%.2f min_volume=%.5f estimated_min_loss=%.2f ocp_min_loss=%.2f dec=%s",
                  st_d, raw_l, calc_lots, v_min_valid, estimate_min_loss,
                  MathAbs(ocp_min_loss), (calc_lots>0)?"APPROVED":"REJECTED");
   }
   if(!ocp_ok)
   {
      LogMsg(LOG_ERROR, "INIT", "OrderCalcProfit audit experienced call failures; EA initialization blocked.");
      return INIT_FAILED;
   }

   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
   ReconJournalClose();
   PositionStateOwnerClose();
   LogMsg(LOG_INFO, "DEINIT", StringFormat("reason=%d", reason));
}

//+------------------------------------------------------------------+
void OnTick()
{
   if(!PositionStateOwnerMatches(g_cfg)) return;
   // Lifecycle/persistence ambiguity blocks new opportunities. Timer-driven
   // management continues so existing positions can still be reconciled.
   if(!PositionManagerAdmissionAllowed()) return;
   // Position recovery and timer-driven management can still operate when
   // the account risk ledger is unavailable, but no entry analysis may run.
   if(!g_risk_admission_ready) return;

   //--- Diagnostic Point 1: Throttled OnTick Heartbeat (every 60 seconds)
   static datetime s_last_tick_diag = 0;
   if(TimeCurrent() - s_last_tick_diag >= 60)
   {
      double cur_bid = SymbolInfoDouble(g_symbol, SYMBOL_BID);
      double cur_ask = SymbolInfoDouble(g_symbol, SYMBOL_ASK);
      datetime cur_bar = iTime(g_symbol, g_cfg.tf_exec, 0);
      PrintFormat("[RUNTIME_DIAG][OnTick] server_time=%s sym=%s bid=%.5f ask=%.5f cur_bar=%s last_bar=%s",
                  TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES|TIME_SECONDS),
                  g_symbol, cur_bid, cur_ask,
                  TimeToString(cur_bar, TIME_DATE|TIME_MINUTES|TIME_SECONDS),
                  TimeToString(g_last_bar_time, TIME_DATE|TIME_MINUTES|TIME_SECONDS));
      s_last_tick_diag = TimeCurrent();
   }

   //--- Risk update every tick
   bool risk_update_ok=RiskTick();
   if(!risk_update_ok && RiskAccountLockWasContended())
      return; // another chart currently owns account serialization; retry on a later tick
   if(risk_update_ok) risk_update_ok=RiskControllerUpdate();
   if(!risk_update_ok && RiskAccountLockWasContended())
      return; // transient account-wide contention is not ledger corruption
   if(!risk_update_ok)
   {
      PositionManagerLatchStateFault("risk ledger update failed; new admission blocked");
      return;
   }

   //--- Feed live tick observation into native order-flow engines
   double last_bid = SymbolInfoDouble(g_symbol, SYMBOL_BID);
   double last_ask = SymbolInfoDouble(g_symbol, SYMBOL_ASK);
   double last_price = (last_bid > 0.0) ? last_bid : _Point;
   long last_vol = SymbolInfoInteger(g_symbol, SYMBOL_VOLUME);
   double tick_vol = (last_vol > 0) ? (double)last_vol : 1.0;
   if(InpEnableTickPressure)
   {
      MqlDateTime tick_dt;
      TimeToStruct(TimeCurrent(),tick_dt);
      bool tick_in_session=(tick_dt.hour>=g_cfg.session_start_hour &&
                            tick_dt.hour<g_cfg.session_end_hour);
      int tick_session_tag=(int)((TimeCurrent()-g_cfg.session_start_hour*3600)/86400);
      bool tick_session_started=tick_in_session &&
         (!g_flow_session_initialized || !g_flow_was_in_session ||
          g_flow_last_session_open_epoch!=tick_session_tag);
      if(tick_session_started)
      {
         // These are streaming diagnostic accumulators, partitioned at the
         // observed session boundary before the first tick is ingested.
         g_footprint_engine.Reset();
         g_vwap_engine.Reset();
         g_flow_last_session_open_epoch=tick_session_tag;
      }
      g_flow_session_initialized=true;
      g_flow_was_in_session=tick_in_session;
      g_footprint_engine.AddTick(last_price, tick_vol, 0);
      g_vwap_engine.AddObservation(last_price, tick_vol);
   }

   //--- External context refresh (throttled to one read every 5 seconds)
   if(TimeCurrent() - g_last_ext_read >= 5)
   {
      string err;
      ExternalContext tmp;
      ZeroMemory(tmp);
      if(ReadExternalContext(g_cfg.bridge_inbox, tmp, err,g_cfg.stale_threshold_s))
      {
         g_ext = tmp;
         g_last_ext_read = TimeCurrent();
      }
      else
      {
         // Preserve non-news context for diagnostics, but never preserve a
         // prior news-clear state after a failed current read.
         g_ext.news_valid=false;
         g_ext.data_quality |= DQ_STALE_EXTERNAL;
         // Bound repeated file-open attempts when the bridge is unavailable.
         // The news filter remains fail-closed until a later read succeeds.
         g_last_ext_read = TimeCurrent();
      }
   }
   // Re-evaluate the retained snapshot on every tick. Read failures and
   // expiry both make NEWS FILTER unavailable instead of silently quiet.
   // ExternalContext.timestamp and news_observed_ts are UTC epoch values
   // produced by Python datetime.now(timezone.utc); compare them in UTC.
   datetime ext_now=TimeGMT();
   if(g_ext.timestamp<=0 || ext_now<g_ext.timestamp ||
      (ext_now-g_ext.timestamp)>g_cfg.stale_threshold_s)
   {
      g_ext.news_valid=false;
      g_ext.data_quality |= DQ_STALE_EXTERNAL;
   }

   //--- Decision only on new closed bar
   datetime bar_time = iTime(g_symbol, g_cfg.tf_exec, 0);
   datetime closed_bar_time = iTime(g_symbol, g_cfg.tf_exec, 1);
   // Reject unavailable/inconsistent boundaries. A durable scoped reservation
   // is written before analysis; repeated and backward opportunities fail closed.
   if(bar_time<=0 || closed_bar_time<=0 || closed_bar_time>=bar_time ||
      (g_last_bar_time>0 && bar_time<g_last_bar_time)) return;
   if(bar_time != g_last_bar_time)
   {
      PrintFormat("[RUNTIME_DIAG][NEW_BAR] server_time=%s bar_time=%s prev_last_bar=%s iTime_ok=%s",
                  TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES|TIME_SECONDS),
                  TimeToString(bar_time, TIME_DATE|TIME_MINUTES|TIME_SECONDS),
                  TimeToString(g_last_bar_time, TIME_DATE|TIME_MINUTES|TIME_SECONDS),
                  (bar_time > 0) ? "YES" : "NO");
   }
   if(bar_time == g_last_bar_time) return;
   long opportunity_id=0;
   if(!RiskBeginOpportunity(bar_time,opportunity_id))
   {
      LogMsg(LOG_WARN,"OPPORTUNITY","Duplicate, stale or ambiguous opportunity identity; admission blocked.");
      return;
   }
   g_last_bar_time = bar_time;

   int outcome=OnClosedBar(opportunity_id);
   // Verify journal completion while the account admission lock remains held.
   // Failure leaves the persisted opportunity RESERVED for reconciliation.
   if(!ReconFinishOpportunity(opportunity_id,outcome,g_cfg))
      PositionManagerLatchStateFault("execution journal cannot retire this opportunity");
   else if(!RiskCompleteOpportunity(outcome))
      PositionManagerLatchStateFault("opportunity outcome could not be durably committed");
}

//+------------------------------------------------------------------+
int OnClosedBar(const long opportunity_id)
{
   datetime decision_boundary=iTime(g_symbol,g_cfg.tf_exec,0);
   datetime closed_bar_time=iTime(g_symbol,g_cfg.tf_exec,1);
   if(opportunity_id<=0 || decision_boundary<=0 || closed_bar_time<=0 ||
      decision_boundary!=g_last_bar_time || closed_bar_time>=decision_boundary)
      return RISK_OP_REJECTED;
   //--- Diagnostic Point 3: OnClosedBar Entry & Session Audit
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   bool session_pass = (dt.hour >= g_cfg.session_start_hour && dt.hour < g_cfg.session_end_hour);
   PrintFormat("[RUNTIME_DIAG][OnClosedBar] server_time=%s sym=%s tf=%d closed_bar=%s hour=%d session=[%d-%d] pass=%s",
               TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES|TIME_SECONDS),
               g_symbol, (int)g_cfg.tf_exec,
               TimeToString(iTime(g_symbol, g_cfg.tf_exec, 0), TIME_DATE|TIME_MINUTES|TIME_SECONDS),
               dt.hour, g_cfg.session_start_hour, g_cfg.session_end_hour,
               session_pass ? "YES" : "NO");

   // Replay the full closed interval, including ticks coalesced by OnTick.
   // A missed interval/restart resets warm-up rather than stitching a gap.
   if(g_tib_last_boundary!=closed_bar_time) g_tib.Reset(InpTIBThreshold);
   MqlTick tib_ticks[];
   int tib_count=CopyTicksRange(g_symbol,tib_ticks,COPY_TICKS_ALL,
                               (ulong)closed_bar_time*1000,(ulong)decision_boundary*1000-1);
   if(tib_count<=0) { g_tib.Reset(InpTIBThreshold); return RISK_OP_REJECTED; }
   for(int i=0;i<tib_count;i++)
   {
      if(tib_ticks[i].time_msc<(long)closed_bar_time*1000 ||
         tib_ticks[i].time_msc>=(long)decision_boundary*1000 ||
         !MathIsValidNumber(tib_ticks[i].bid) || !MathIsValidNumber(tib_ticks[i].ask) ||
         tib_ticks[i].bid<=0 || tib_ticks[i].ask<tib_ticks[i].bid ||
         (i>0 && tib_ticks[i].time_msc<tib_ticks[i-1].time_msc))
      { g_tib.Reset(InpTIBThreshold); g_tib_last_boundary=0; return RISK_OP_REJECTED; }
      g_tib.Add(tib_ticks[i].bid,tib_ticks[i].ask,tib_ticks[i].time_msc);
   }
   g_tib_last_boundary=decision_boundary;
   g_tib_decision_ready=g_tib.ClosedBefore((long)decision_boundary*1000,g_tib_decision);
   if(!g_tib_decision_ready || g_tib_decision.close_msc<(long)closed_bar_time*1000)
      return RISK_OP_NO_TRADE;

   //--- 0) Session hour gate
   if(dt.hour < g_cfg.session_start_hour || dt.hour >= g_cfg.session_end_hour)
   {
      return RISK_OP_REJECTED;
   }

   // NEWS FILTER is admission-only and runs before any session/profile,
   // feature, regime, or strategy state mutation. A failed or stale provider
   // observation is not equivalent to a quiet calendar.
   string news_reason="";
   if(!ExternalNewsFilterAllows(g_ext,g_cfg.news_mode,TimeGMT(),
                               g_cfg.stale_threshold_s,news_reason))
   {
      LogMsg(LOG_WARN,"NEWS_FILTER",news_reason);
      return RISK_OP_REJECTED;
   }

   //--- 1) Snapshot
   MarketSnapshot candidate_snap;
   FeatureSnapshot candidate_feat;
   AMIGOFeatureState candidate_feature_state = g_amigo_feature_state;
   MqlRates candidate_feature_rates[];
   RegimePersist candidate_regime = g_regime_state;
   ZeroMemory(candidate_snap);
   ZeroMemory(candidate_feat);
   bool snap_res = BuildMarketSnapshot(g_symbol,candidate_snap,decision_boundary,
                                       closed_bar_time,opportunity_id,g_cfg.tf_exec);
   PrintFormat("[RUNTIME_DIAG][SNAPSHOT] server_time=%s success=%s bid=%.5f ask=%.5f dq=%d",
               TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES|TIME_SECONDS),
               snap_res ? "YES" : "NO", candidate_snap.bid, candidate_snap.ask, candidate_snap.data_quality);
   if(!snap_res)
   {
      LogMsg(LOG_WARN, "BAR", "snapshot build failed");
      return RISK_OP_REJECTED;
   }
   if(candidate_snap.snapshot_id!=opportunity_id ||
      candidate_snap.decision_boundary!=decision_boundary ||
      candidate_snap.closed_bar_time!=closed_bar_time)
      return RISK_OP_REJECTED;
   candidate_snap.external_max_age_s=g_cfg.stale_threshold_s;

   //--- 2) Features
   bool feat_res = BuildFeatureVector(g_symbol, g_cfg, candidate_feat, candidate_feature_state,
                                      candidate_feature_rates);
   PrintFormat("[RUNTIME_DIAG][FEATURES] server_time=%s success=%s ts=%s atr14=%.5f fusion=%.2f",
               TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES|TIME_SECONDS),
               feat_res ? "YES" : "NO",
               TimeToString(candidate_feat.timestamp, TIME_DATE|TIME_MINUTES|TIME_SECONDS),
               candidate_feat.atr14, candidate_feat.fusion);
   if(!feat_res)
   {
      LogMsg(LOG_WARN, "BAR", "feature build failed");
      return RISK_OP_REJECTED;
   }
   if(candidate_feat.timestamp!=closed_bar_time ||
      iTime(g_symbol,g_cfg.tf_exec,0)!=decision_boundary ||
      iTime(g_symbol,g_cfg.tf_exec,1)!=closed_bar_time)
      return RISK_OP_REJECTED;
   // Bind the exported close to the exact validated history read that produced
   // the feature snapshot. Do not re-read iClose during later publication.
   int validated_feature_count=ArraySize(candidate_feature_rates);
   if(validated_feature_count<=0 || !ArrayGetAsSeries(candidate_feature_rates) ||
      candidate_feature_rates[0].time!=closed_bar_time ||
      !MathIsValidNumber(candidate_feature_rates[0].close) ||
      candidate_feature_rates[0].close<=0.0)
      return RISK_OP_REJECTED;
   candidate_snap.closed_bar_close=candidate_feature_rates[0].close;
   candidate_feat.snapshot_id=opportunity_id;
   candidate_feat.decision_boundary=decision_boundary;
   candidate_feat.closed_bar_time=closed_bar_time;
   candidate_feat.symbol=g_symbol;
   candidate_feat.timeframe=(int)g_cfg.tf_exec;

   //--- Diagnostic Top-Down Multi-Timeframe Context (Section 7)
   TopDownContext td;
   if(!EvaluateTopDownContext(g_symbol,g_cfg.atr_period,decision_boundary,td) ||
      td.asof_boundary!=decision_boundary ||
      iTime(g_symbol,g_cfg.tf_exec,0)!=decision_boundary ||
      iTime(g_symbol,g_cfg.tf_exec,1)!=closed_bar_time)
   {
      LogMsg(LOG_WARN,"TOPDOWN","INCOMPLETE_OR_MIXED_TIME_HISTORY");
      return RISK_OP_REJECTED;
   }
   LogMsg(LOG_INFO, "TOPDOWN_DIAG", StringFormat("ts=%s d1=%d h4=%d h1=%d m15=%d aligned=%s score=%.2f summary=%s",
          TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES),
          td.d1_dir, td.h4_dir, td.h1_dir, td.m15_dir,
          td.aligned ? "TRUE" : "FALSE", td.alignment_score, td.summary));

   //--- 4) Multi-Timeframe Regime
   FeatureSnapshot decision_feat = candidate_feat;
   if(!g_cfg.tick_pressure_enabled)
   {
      // Keep raw proxy values for diagnostics, but prevent them influencing
      // authoritative regime/strategy scores unless explicitly enabled.
      decision_feat.fusion = 0.0;
      decision_feat.pressure_state = 0;
      decision_feat.bull_flip = false;
      decision_feat.bear_flip = false;
      decision_feat.surge = false;
      decision_feat.delta_divergence = 0.0;
      decision_feat.divergence_bull = 0.0;
      decision_feat.divergence_bear = 0.0;
   }
   RegimeState rs = EvaluateRegimeWithState(decision_feat, td, g_cfg, candidate_regime);
   if(rs.snapshot_id!=opportunity_id || decision_feat.snapshot_id!=candidate_snap.snapshot_id)
      return RISK_OP_REJECTED;

   //--- 5) Strategy scores
   StrategyScores ss = ScoreStrategies(decision_feat, g_ext, g_cfg);

   //--- 6) ML gate (no-op when disabled)
   MLGateResult ml = MLGateEvaluate(candidate_feat, ss, g_cfg);
   if(ml.available && !ml.pass)
   {
      long did = opportunity_id;
      LogDecision(did, g_symbol, ACTION_NO_TRADE, rs.regime, HYP_NONE,
                  MathMax(ss.s_long, ss.s_short), "ML_VETO");
      return RISK_OP_REJECTED;
   }

   //--- 7) Decision gate
   DecisionResult dr = Decide(ss, rs, g_ext, g_cfg,
                              g_ext.data_quality | candidate_snap.data_quality);
   if(dr.snapshot_id!=opportunity_id ||
      iTime(g_symbol,g_cfg.tf_exec,0)!=decision_boundary ||
      iTime(g_symbol,g_cfg.tf_exec,1)!=closed_bar_time)
      return RISK_OP_REJECTED;
   if(dr.action==ACTION_TRADE && dr.hypothesis==HYP_CONTINUATION &&
      dr.direction*g_tib_decision.imbalance<=0)
   {
      dr.action=ACTION_NO_TRADE;
      dr.reason="TIB_OPPOSES_CONTINUATION";
   }
   long decision_id = opportunity_id;
   LogDecision(decision_id, g_symbol, dr.action, rs.regime, dr.hypothesis,
               dr.best_score, dr.reason);

   LogFeatureDiagnostics(candidate_feat.timestamp, g_symbol, g_cfg.tf_exec,
                         (int)rs.regime, candidate_feat.structure_dir, candidate_feat.fusion,
                         candidate_feat.bull_flip, candidate_feat.bear_flip, candidate_feat.surge,
                         candidate_feat.sweep_reject, ss.long_cont, ss.short_cont,
                         ss.long_mr, ss.short_mr, ss.s_long, ss.s_short,
                         dr.best_score, dr.margin, g_cfg.score_threshold,
                         g_cfg.score_margin, dr.action, dr.reason);

   if(dr.action != ACTION_TRADE)
   {
      // A fully assembled and evaluated no-trade opportunity may advance accepted
      // strategy history. Invalid/failed paths above leave globals untouched.
      CommitFlowOpportunityDiagnostics(candidate_feature_rates,decision_boundary,candidate_feat.atr14);
      g_snap = candidate_snap;
      g_feat = candidate_feat;
      g_amigo_feature_state = candidate_feature_state;
      g_regime_state = candidate_regime;
      WriteSnapshotForExternal(g_cfg.bridge_outbox, candidate_snap, candidate_feat);
      return RISK_OP_NO_TRADE;
   }

   //--- M1 Microstructure Execution Filter (Workstream B):
   // For SCALPING horizon (or M1/M5 execution), check M1 structure for immediate adverse impulse.
   if(g_cfg.tf_exec == PERIOD_M1 || (g_cfg.tf_exec == PERIOD_M5 && td.m1_dir != 0 && td.m1_dir != dr.direction))
   {
      if(td.m1_dir != 0 && td.m1_dir != dr.direction)
      {
         LogMsg(LOG_INFO, "EXEC_M1_VETO", StringFormat("M1 adverse microstructure veto: m1_dir=%d trade_dir=%d", td.m1_dir, dr.direction));
         return RISK_OP_REJECTED;
      }
   }

   ENUM_HORIZON selected_horizon=(ENUM_HORIZON)0;
   if(!SelectApprovedHorizon(td,dr,rs.regime,decision_boundary,selected_horizon))
   {
      LogDecision(decision_id,g_symbol,ACTION_NO_TRADE,rs.regime,dr.hypothesis,
                  dr.best_score,"NO_ELIGIBLE_HORIZON");
      return RISK_OP_NO_TRADE;
   }
   dr.horizon=selected_horizon;
   string horizon_news_reason="";
   if(!AmigoNewsHorizonAllows(g_ext,g_cfg.news_mode,dr.horizon,TimeGMT(),
                              g_cfg.stale_threshold_s,horizon_news_reason))
   {
      LogDecision(decision_id,g_symbol,ACTION_NO_TRADE,rs.regime,dr.hypothesis,
                  dr.best_score,horizon_news_reason);
      return RISK_OP_REJECTED;
   }
   LogMsg(LOG_INFO,"NEWS_HORIZON",StringFormat("id=%I64d horizon=%d event_utc=%I64d reason=%s",
          decision_id,(int)dr.horizon,(long)g_ext.news_event_ts,horizon_news_reason));
   LogMsg(LOG_INFO,"FROZEN_FOOTPRINT",StringFormat("id=%I64d horizon=%d strategy=%d available=%s pressure=%.4f poc=%.5f concentration=%.4f observations=%d persistent=%s bull_div=%s bear_div=%s provenance=MT5_TICK_PROXY",
      decision_id,(int)dr.horizon,(int)dr.hypothesis,decision_feat.footprint_available?"TRUE":"FALSE",
      decision_feat.footprint_pressure,decision_feat.footprint_poc,decision_feat.footprint_concentration,
      decision_feat.footprint_observations,decision_feat.footprint_persistent?"TRUE":"FALSE",
      decision_feat.footprint_divergence_bull?"TRUE":"FALSE",decision_feat.footprint_divergence_bear?"TRUE":"FALSE"));

   string proxy_reason;
   if(!HorizonProxyAgreement(decision_feat,td,dr,rs.regime,g_cfg,decision_boundary,proxy_reason))
   {
      LogDecision(decision_id,g_symbol,ACTION_NO_TRADE,rs.regime,dr.hypothesis,dr.best_score,proxy_reason);
      return RISK_OP_NO_TRADE;
   }
   LogMsg(LOG_INFO,"HORIZON_PROXY",StringFormat("id=%I64d horizon=%d hypothesis=%d pressure=%.3f bull_div=%.3f bear_div=%.3f provenance=%s streaming_footprint=DIAGNOSTIC broker_depth=UNAVAILABLE",
      decision_id,(int)dr.horizon,(int)dr.hypothesis,decision_feat.fusion,
      decision_feat.divergence_bull,decision_feat.divergence_bear,proxy_reason));


   //--- 8) Risk gate
   string risk_reason;
   if(!RiskAllows(g_cfg, risk_reason))
   {
      LogMsg(LOG_WARN, "RISK", risk_reason);
      return RISK_OP_REJECTED;
   }

   //--- 9) Entry geometry uses the already frozen horizon.
   double ask = SymbolInfoDouble(g_symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(g_symbol, SYMBOL_BID);
   double entry = (dr.direction == +1) ? ask : bid;
   double atr = candidate_feat.atr14;
   if(atr <= 0.0) return RISK_OP_REJECTED;

   // Horizon-specific structural invalidation timeframe
   ENUM_TIMEFRAMES stop_tf = g_cfg.tf_exec;
   if(dr.horizon == HORIZON_SCALPING) stop_tf = (g_cfg.tf_exec == PERIOD_M1) ? PERIOD_M1 : PERIOD_M5;
   else if(dr.horizon == HORIZON_SWING) stop_tf = (g_cfg.tf_h4 != 0) ? g_cfg.tf_h4 : PERIOD_H4;
   else stop_tf = (g_cfg.tf_context != 0) ? g_cfg.tf_context : PERIOD_M15;

   double structural_invalid = 0.0;
   MqlRates r[];
   int got=0;
   if(stop_tf==g_cfg.tf_exec)
   {
      got=ArraySize(candidate_feature_rates);
      if(got<50 || !ArrayGetAsSeries(candidate_feature_rates)) return RISK_OP_REJECTED;
      if(ArrayResize(r,got)!=got || !ArraySetAsSeries(r,true)) return RISK_OP_REJECTED;
      for(int q=0;q<got;q++) r[q]=candidate_feature_rates[q];
   }
   else
   {
      if(!ArraySetAsSeries(r, true)) return RISK_OP_REJECTED;
      datetime geometry_boundary=iTime(g_symbol,stop_tf,0);
      datetime geometry_latest=iTime(g_symbol,stop_tf,1);
      if(geometry_boundary<=0 || geometry_latest<=0 || geometry_latest>=geometry_boundary ||
         geometry_boundary>decision_boundary || geometry_latest>=decision_boundary)
         return RISK_OP_REJECTED;
      got=CopyRates(g_symbol, stop_tf, 1, 200, r);
      if(!ValidateClosedRateSequence(r,got,geometry_boundary,geometry_latest,50,200,
                                     PeriodSeconds(stop_tf),false) ||
         iTime(g_symbol,stop_tf,0)!=geometry_boundary ||
         iTime(g_symbol,stop_tf,1)!=geometry_latest ||
         iTime(g_symbol,g_cfg.tf_exec,0)!=decision_boundary ||
         iTime(g_symbol,g_cfg.tf_exec,1)!=closed_bar_time) return RISK_OP_REJECTED;
   }
   // Both reused feature history and independently copied geometry must
   // still belong to the frozen opportunity before swing calculation.
   if(iTime(g_symbol,g_cfg.tf_exec,0)!=decision_boundary ||
           iTime(g_symbol,g_cfg.tf_exec,1)!=closed_bar_time)
      return RISK_OP_REJECTED;
   if(got > 20)
   {
      double sp; datetime ts;
      if(dr.direction == +1 && FindLatestConfirmedSwing(r, got, false, sp, ts))
         structural_invalid = sp;
      if(dr.direction == -1 && FindLatestConfirmedSwing(r, got, true, sp, ts))
         structural_invalid = sp;
   }

   double original_sl = SelectStop(g_symbol, dr.direction, entry, structural_invalid, atr);
   double original_stop_dist = MathAbs(entry - original_sl);
   double tp;
   if(dr.direction == +1) tp = entry + g_cfg.partial_rr * original_stop_dist;
   else                   tp = entry - g_cfg.partial_rr * original_stop_dist;
   tp = NormalizeDouble(tp, (int)SymbolInfoInteger(g_symbol, SYMBOL_DIGITS));

   //--- Account-Aware Adaptive Stop-Loss Evaluation Layer (Prompts §1-§19)
   // 1. Evaluate Automatic Equity-Responsive Risk Controller
   AdaptiveRiskResult risk_auto = RiskControllerEvaluate(g_symbol, entry, original_sl, g_cfg, g_risk.daily_locked);
   RiskControllerLogDiagnostic(risk_auto);

   if(!risk_auto.trade_allowed)
   {
      LogMsg(LOG_WARN, "RISK_AUTO_BLOCKED", StringFormat("status=%s reason=%s risk_budget=%.5f",
             (risk_auto.risk_state == RISK_STATE_DAILY_STOP) ? "DAILY_STOP" : "UNSAFE",
             risk_auto.reason, risk_auto.risk_budget));
      return RISK_OP_REJECTED;
   }

   //--- Apply Authoritative Regime Risk Modifier (Workstream A Integration)
   double reg_mod = rs.risk_modifier;
   if(reg_mod < 0.10 || reg_mod > 1.00 || !MathIsValidNumber(reg_mod))
   {
      // Never turn an invalid/zero regime modifier into full risk. A zero
      // modifier is the regime engine's explicit non-tradable value.
      LogMsg(LOG_WARN, "RISK_MODIFIER_INVALID",
             StringFormat("regime=%d modifier=%.8f; opportunity rejected",
                          (int)rs.regime, reg_mod));
      return RISK_OP_REJECTED;
   }
   double effective_risk_pct = risk_auto.effective_risk_percent * reg_mod;

   AdaptiveSLResult adapt_res = EvaluateAdaptiveStop(
      g_symbol, dr.direction, entry, original_sl, tp, structural_invalid, atr, effective_risk_pct, g_cfg
   );

   // If adaptive SL was rejected, use original_sl so AccountExecutionEvaluate can properly classify infeasibility
   double sl = (adapt_res.status == ADAPTIVE_SL_ACCEPTED) ? adapt_res.selected_sl : original_sl;
   double stop_dist = MathAbs(entry - sl);

   // Recalculate TP for adaptive SL using original strategy RR requirement
   if(adapt_res.status == ADAPTIVE_SL_ACCEPTED)
   {
      if(dr.direction == +1) tp = entry + g_cfg.partial_rr * stop_dist;
      else                   tp = entry - g_cfg.partial_rr * stop_dist;
      tp = NormalizeDouble(tp, (int)SymbolInfoInteger(g_symbol, SYMBOL_DIGITS));
   }

   //--- Spread vs stop distance check
   double spread = ask - bid;
   if(stop_dist > 0.0 && spread > g_cfg.max_spread_atr_pct * stop_dist)
   {
      LogMsg(LOG_WARN, "EXEC", "spread too large relative to stop");
      return RISK_OP_REJECTED;
   }

   //--- Netting Account Single-Active-Horizon Invariant Gate
   ENUM_ACCOUNT_MARGIN_MODE margin_mode = (ENUM_ACCOUNT_MARGIN_MODE)AccountInfoInteger(ACCOUNT_MARGIN_MODE);
   if(margin_mode == ACCOUNT_MARGIN_MODE_RETAIL_NETTING && !g_cfg.shadow_only)
   {
      if(PositionsTotal() > 0 && PositionSelect(g_symbol))
      {
         LogMsg(LOG_WARN, "NETTING_GATE", "NETTING_CONCURRENT_POSITION_BLOCKED: Symbol already has active position");
         return RISK_OP_REJECTED;
      }
   }

   //--- 10) Account-Aware Execution Evaluation & Risk Sizing
   AccountExecutionEnvelope acc_env = AccountExecutionEvaluate(
      g_symbol, dr.direction, entry, sl, tp, effective_risk_pct, g_cfg, dr.action, risk_auto.max_allowed_distortion
   );

   // Populate adaptive SL fields into execution envelope for diagnostics audit trail
   acc_env.original_sl            = original_sl;
   acc_env.original_stop_distance = original_stop_dist;
   acc_env.adaptive_sl            = adapt_res.candidate_sl;
   acc_env.selected_sl            = sl;
   acc_env.max_account_stop_dist  = adapt_res.max_account_stop_dist;
   acc_env.sl_adapt_status        = adapt_res.status;
   acc_env.sl_adapt_reason        = adapt_res.reason;

   if(acc_env.final_action != ACTION_TRADE)
   {
      LogMsg(LOG_WARN, "ACCOUNT_FEASIBILITY", StringFormat("BLOCKED status=%d reason=%s",
             (int)acc_env.feasibility, acc_env.reason));
      return RISK_OP_REJECTED;
   }

   double lots = acc_env.executable_volume;

   //--- 11) Build intent
   TradeIntent ti;
   ZeroMemory(ti);
   ti.intent_id        = decision_id;
   ti.snapshot_id      = dr.snapshot_id;
   ti.decision_id      = decision_id;
   ti.signal_id        = decision_id;
   ti.idempotency_key  = decision_id;
   ti.submission_attempt_id = 0; // will be injected before ExecuteIntent call
   ti.schema_version   = Amigo_SCHEMA_VERSION;
   ti.strategy_version = 1;
   ti.feature_version  = candidate_feat.feature_version;
   ti.model_version    = ml.available ? 1 : 0;
   ti.symbol           = g_symbol;
   ti.direction        = dr.direction;
   ti.timestamp        = TimeCurrent();
   ti.expiry           = ti.timestamp + 60;
   // A delayed evaluation cannot extend the frozen bar's opportunity.
   datetime opportunity_expiry=decision_boundary+PeriodSeconds(g_cfg.tf_exec);
   if(ti.expiry>opportunity_expiry) ti.expiry=opportunity_expiry;
   ti.entry_reference  = entry;
   ti.stop             = sl;
   ti.target           = tp;
   ti.score            = dr.best_score;
   ti.confidence       = dr.confidence;
   ti.regime           = rs.regime;
   ti.hypothesis       = dr.hypothesis;
   ti.horizon          = dr.horizon;
   ti.reason_codes     = dr.reason;
   ti.risk_allocation  = risk_auto.effective_risk_percent;
   ti.risk_modifier    = reg_mod;
   ti.data_quality     = g_ext.data_quality | candidate_snap.data_quality;

   string vreason;
   if(!ValidateIntent(ti, g_cfg, vreason))
   {
      LogMsg(LOG_WARN, "INTENT", vreason);
      return RISK_OP_REJECTED;
   }

   if(!PositionManagerHasCapacity())
   {
      LogMsg(LOG_WARN,"POSITION_CAPACITY","persistent position capacity reached; no new entry");
      return RISK_OP_REJECTED;
   }

   //--- 12) Inject submission_attempt_id before ExecuteIntent call
   // P0 identity chain: submission_attempt_id is a per-call counter that
   // preserves submission identity across terminal restarts when combined
   // with durable decision_id binding.
   static long g_submission_attempt_counter = 0;
   g_submission_attempt_counter++;
   ti.submission_attempt_id = g_submission_attempt_counter;

   ExecutionResult er = ExecuteIntent(ti, lots, g_cfg, stop_dist,
                                      effective_risk_pct,risk_auto.max_allowed_distortion,atr);
   if(er.risk_guard_blocked)
   {
      LogMsg(LOG_WARN, "EXEC", er.comment);
      return RISK_OP_REJECTED;
   }
   // A proven deal that is partial must be registered before quarantine so
   // its known exposure remains under management. A full fill is registered
   // only after current broker identity and account exposure are confirmed.
   if(er.outcome_uncertain)
   {
      LogMsg(LOG_ERROR,"EXEC_UNCERTAIN",
             StringFormat("intent=%I64d order=%I64u deal=%I64u retcode=%u detail=%s; admission quarantined",
                          decision_id,er.order_ticket,er.deal_ticket,er.retcode,er.comment));
      if(er.position_id!=0 && er.accepted)
         PositionManagerRegister(er.position_id,er.fill_price,sl,tp,er.fill_volume,
                                 dr.direction,atr,g_cfg,ti.horizon);
      PositionManagerLatchStateFault("execution outcome is uncertain; reconcile before new admission");
      return RISK_OP_UNCERTAIN;
   }
   if(!er.accepted && !g_cfg.shadow_only)
   {
      LogMsg(LOG_ERROR, "EXEC", StringFormat("fail retcode=%u %s",
             er.retcode, er.comment));
      return RISK_OP_REJECTED;
   }
   if(er.accepted)
   {
      LogMsg(LOG_INFO, "EXEC", StringFormat("filled dir=%d lots=%.2f price=%.5f",
             dr.direction, lots, er.fill_price));
   }
   if(er.position_id == 0 && !g_cfg.shadow_only && er.accepted)
   {
      PositionManagerLatchStateFault("accepted execution has no stable position identifier");
      return RISK_OP_UNCERTAIN;
   }
   else if(er.position_id == 0 && g_cfg.shadow_only)
   {
      // Use the exact quote/volume accepted by final preflight, not the older
      // strategy quote. A synthetic reference is never a confirmed broker fill.
      if(!er.shadow_evaluated || !MathIsValidNumber(er.shadow_entry) || er.shadow_entry<=0.0 ||
         !MathIsValidNumber(er.shadow_volume) || er.shadow_volume<=0.0)
         return RISK_OP_REJECTED;
      PositionManagerRegister((ulong)decision_id, er.shadow_entry, sl, tp, er.shadow_volume, dr.direction,
                              atr, g_cfg, ti.horizon);
   }

   if(!g_cfg.shadow_only && er.accepted)
   {
      ulong execution_magic=(g_cfg.magic_number>0)?g_cfg.magic_number:20260908;
      if(!AccountManagedPositionVisible(er.position_id,ti.symbol,execution_magic,er.fill_volume))
      {
         PositionManagerLatchStateFault("confirmed fill is not yet visible with expected identity, volume and stop");
         return RISK_OP_UNCERTAIN;
      }
      // The fill already exists. Retain its management state before any
      // post-fill risk failure quarantines admission. This records exposure;
      // it does not approve the opportunity or commit strategy state.
      PositionManagerRegister(er.position_id,er.fill_price,sl,tp,er.fill_volume,
                              dr.direction,atr,g_cfg,ti.horizon);
      if(!PositionManagerAdmissionAllowed()) return RISK_OP_UNCERTAIN;

      double reconciled_stop_risk=0.0;
      string reconciled_risk_reason="";
      double reconciled_equity=AccountInfoDouble(ACCOUNT_EQUITY);
      if(!MathIsValidNumber(reconciled_equity) || reconciled_equity<=0.0 ||
         !AccountEstimatedStopRisk(reconciled_stop_risk,reconciled_risk_reason) ||
         !MathIsValidNumber(reconciled_stop_risk) ||
         reconciled_stop_risk/reconciled_equity*100.0>AMIGO_MAX_ESTIMATED_STOP_LOSS_PERCENT)
      {
         PositionManagerLatchStateFault("post-fill aggregate stop-risk verification failed: "+reconciled_risk_reason);
         return RISK_OP_UNCERTAIN;
      }
   }

   if(!PositionManagerAdmissionAllowed()) return RISK_OP_UNCERTAIN;

   // Single accepted-state commit point after geometry, risk, final quote,
   // confirmed execution outcome and position registration all succeed.
   CommitFlowOpportunityDiagnostics(candidate_feature_rates,decision_boundary,candidate_feat.atr14);
   g_snap = candidate_snap;
   g_feat = candidate_feat;
   g_amigo_feature_state = candidate_feature_state;
   g_regime_state = candidate_regime;
   WriteSnapshotForExternal(g_cfg.bridge_outbox, candidate_snap, candidate_feat);
   return g_cfg.shadow_only ? RISK_OP_SHADOW : RISK_OP_CONFIRMED;
}

//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
{
   if(trans.type==TRADE_TRANSACTION_REQUEST && !ReconCaptureRequestEvent(request,result,g_cfg))
   {
      g_risk_admission_ready=false;
      PositionManagerLatchStateFault("request callback evidence could not be matched or persisted");
   }
   TransactionReconHandle(trans, request, result);
}

//+------------------------------------------------------------------+
void OnTimer()
{
   if(!PositionStateOwnerMatches(g_cfg))
   {
      PositionManagerLatchStateFault("position state ownership or account scope changed");
      return;
   }
   PositionManagerTick(g_cfg);
}
//+------------------------------------------------------------------+ // force timestamp change
