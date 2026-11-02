//+------------------------------------------------------------------+
//|                                                     AlgoMind.mq5 |
//|                    Deterministic MQL5-first trading core         |
//|                    (ML gate present but disabled by default)     |
//+------------------------------------------------------------------+
#property copyright "AlgoMind"
#property version   "1.00"
#property strict

//--- Project includes (flat layout under MQL5\Include\)
#include <Contract.mqh>
#include <Config.mqh>
#include <Logger.mqh>
#include <Snapshot.mqh>
#include <Volatility.mqh>
#include <OrderFlow.mqh>
#include <Structure.mqh>
#include <FVG.mqh>
#include <Auction.mqh>
#include <FeatureVector.mqh>
#include <RegimeEngine.mqh>
#include <StrategyEngine.mqh>
#include <RiskEngine.mqh>
#include <ExecutionEngine.mqh>
#include <PositionManager.mqh>
#include <TransactionRecon.mqh>
#include <ExternalContext.mqh>
#include <MLGate.mqh>

//--- Inputs
input group "=== Symbol & Timeframes ==="
input string InpSymbol            = "";           // empty = current symbol
input ENUM_TIMEFRAMES InpTFExec   = PERIOD_M5;
input ENUM_TIMEFRAMES InpTFContext= PERIOD_M15;
input ENUM_TIMEFRAMES InpTFHTF    = PERIOD_H1;

input group "=== Risk (starting research params) ==="
input double InpRiskPerTrade      = 0.5;     // % per trade
input double InpDailyLossPct      = 2.0;     // % hard daily
input double InpTotalDDPct        = 5.0;     // % hard total DD
input double InpPartialRR         = 2.0;
input double InpPartialFraction   = 0.50;
input double InpTrailATRMult      = 1.5;
input double InpTrailActivateR    = 1.0;

input group "=== Spread ==="
input double InpMaxSpreadPoints   = 0.0;     // 0 = disabled
input double InpMaxSpreadATRPct   = 0.10;    // spread <= 10% of stop distance

input group "=== Session (server time) ==="
input int    InpSessionStartHour  = 0;
input int    InpSessionEndHour    = 24;

input group "=== News ==="
input int    InpNewsMode          = 0;       // 0=OFF 1=FILTER 2=TRADE 3=HYBRID
input int    InpNewsBufferMins    = 30;

input group "=== External influence caps ==="
input double InpCFTCMaxInfluence  = 0.05;
input double InpOptionsMaxInfl    = 0.10;

input group "=== Bridge ==="
input string InpBridgeInbox       = "algomind_ext_in.txt";
input string InpBridgeOutbox      = "algomind_mkt_out.txt";
input int    InpStaleThresholdSec = 120;

input group "=== ML (Phase 8 - disabled by default) ==="
input bool   InpMLEnabled         = false;
input string InpMLModelPath       = "";

input group "=== Logging ==="
input int    InpLogLevel          = 1;       // 0=DEBUG 1=INFO 2=WARN 3=ERROR

//--- Globals
string          g_symbol;
datetime        g_last_bar_time = 0;
datetime        g_last_ext_read = 0;
ExternalContext g_ext;
MarketSnapshot  g_snap;
FeatureSnapshot g_feat;

//+------------------------------------------------------------------+
int OnInit()
{
   LogInit(InpLogLevel);

   g_symbol = (StringLen(InpSymbol) > 0) ? InpSymbol : _Symbol;

   g_cfg.symbol              = g_symbol;
   g_cfg.tf_exec             = InpTFExec;
   g_cfg.tf_context          = InpTFContext;
   g_cfg.tf_htf              = InpTFHTF;
   g_cfg.atr_period          = 14;
   g_cfg.swing_k             = 2;
   g_cfg.zscore_window       = 20;
   g_cfg.value_area_pct      = 0.70;
   g_cfg.pressure_threshold  = 0.25;
   g_cfg.surge_threshold     = 0.35;
   g_cfg.score_threshold     = 0.65;
   g_cfg.score_margin        = 0.15;
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
   g_cfg.max_spread_atr_pct  = InpMaxSpreadATRPct;
   g_cfg.max_spread_points   = InpMaxSpreadPoints;
   g_cfg.session_start_hour  = InpSessionStartHour;
   g_cfg.session_end_hour    = InpSessionEndHour;
   g_cfg.news_mode           = InpNewsMode;
   g_cfg.news_buffer_mins    = InpNewsBufferMins;
   g_cfg.cftc_max_influence  = InpCFTCMaxInfluence;
   g_cfg.options_max_influence = InpOptionsMaxInfl;
   g_cfg.ml_enabled          = InpMLEnabled;
   g_cfg.ml_model_path       = InpMLModelPath;
   g_cfg.bridge_inbox        = InpBridgeInbox;
   g_cfg.bridge_outbox       = InpBridgeOutbox;
   g_cfg.stale_threshold_s   = InpStaleThresholdSec;

   RiskInit();
   ZeroMemory(g_ext);

   //--- Start the position-manager / reconciliation timer.
   //--- Without this OnTimer never fires and partials/trailing never run.
   EventSetTimer(5);

   LogMsg(LOG_INFO, "INIT", StringFormat("AlgoMind started on %s tf=%d ML=%s",
          g_symbol, (int)InpTFExec, InpMLEnabled?"ON":"OFF"));
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
   LogMsg(LOG_INFO, "DEINIT", StringFormat("reason=%d", reason));
}

//+------------------------------------------------------------------+
void OnTick()
{
   //--- Risk update every tick
   RiskTick();

   //--- External context refresh (throttled to one read every 5 seconds)
   if(TimeCurrent() - g_last_ext_read >= 5)
   {
      string err;
      ExternalContext tmp;
      ZeroMemory(tmp);
      if(ReadExternalContext(g_cfg.bridge_inbox, tmp, err))
      {
         g_ext = tmp;
         g_last_ext_read = TimeCurrent();

         //--- Freshness gate: only flag stale when a real timestamp exists
         //--- and it has aged past the threshold.
         if(g_ext.timestamp > 0 &&
            (TimeCurrent() - g_ext.timestamp) > g_cfg.stale_threshold_s)
         {
            g_ext.data_quality |= DQ_STALE_EXTERNAL;
         }
      }
   }

   //--- Decision only on new closed bar
   datetime bar_time = iTime(g_symbol, g_cfg.tf_exec, 0);
   if(bar_time == g_last_bar_time) return;
   g_last_bar_time = bar_time;

   OnClosedBar();
}

//+------------------------------------------------------------------+
void OnClosedBar()
{
   //--- 1) Snapshot
   if(!BuildMarketSnapshot(g_symbol, g_snap))
   {
      LogMsg(LOG_WARN, "BAR", "snapshot build failed");
      return;
   }

   //--- 2) Features
   if(!BuildFeatureVector(g_symbol, g_cfg, g_feat))
   {
      LogMsg(LOG_WARN, "BAR", "feature build failed");
      return;
   }

   //--- 3) Publish snapshot for Python (external context)
   WriteSnapshotForExternal(g_cfg.bridge_outbox, g_snap, g_feat);

   //--- 4) Regime
   RegimeState rs = EvaluateRegime(g_feat, g_cfg);

   //--- 5) Strategy scores
   StrategyScores ss = ScoreStrategies(g_feat, g_ext, g_cfg);

   //--- 6) ML gate (no-op when disabled)
   MLGateResult ml = MLGateEvaluate(g_feat, ss, g_cfg);
   if(ml.available && !ml.pass)
   {
      long did = NextDecisionId();
      LogDecision(did, g_symbol, ACTION_NO_TRADE, rs.regime, HYP_NONE,
                  MathMax(ss.s_long, ss.s_short), "ML_VETO");
      return;
   }

   //--- 7) Decision gate
   DecisionResult dr = Decide(ss, rs, g_ext, g_cfg,
                              g_ext.data_quality | g_snap.data_quality);
   long decision_id = NextDecisionId();
   LogDecision(decision_id, g_symbol, dr.action, rs.regime, dr.hypothesis,
               dr.best_score, dr.reason);

   if(dr.action != ACTION_TRADE) return;

   //--- 8) Risk gate
   string risk_reason;
   if(!RiskAllows(g_cfg, risk_reason))
   {
      LogMsg(LOG_WARN, "RISK", risk_reason);
      return;
   }

   //--- 9) Entry geometry
   double ask = SymbolInfoDouble(g_symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(g_symbol, SYMBOL_BID);
   double entry = (dr.direction == +1) ? ask : bid;
   double atr = g_feat.atr14;
   if(atr <= 0.0) return;

   double structural_invalid = 0.0;
   MqlRates r[];
   int got = CopyRates(g_symbol, g_cfg.tf_exec, 1, 200, r);
   if(got > 20)
   {
      double sp; datetime ts;
      if(dr.direction == +1 && FindLatestConfirmedSwing(r, got, false, sp, ts))
         structural_invalid = sp;
      if(dr.direction == -1 && FindLatestConfirmedSwing(r, got, true, sp, ts))
         structural_invalid = sp;
   }

   double sl = SelectStop(g_symbol, dr.direction, entry, structural_invalid, atr);
   double stop_dist = MathAbs(entry - sl);
   double tp;
   if(dr.direction == +1) tp = entry + g_cfg.partial_rr * stop_dist;
   else                   tp = entry - g_cfg.partial_rr * stop_dist;
   tp = NormalizeDouble(tp, (int)SymbolInfoInteger(g_symbol, SYMBOL_DIGITS));

   //--- Spread vs stop distance check
   double spread = ask - bid;
   if(stop_dist > 0.0 && spread > g_cfg.max_spread_atr_pct * stop_dist)
   {
      LogMsg(LOG_WARN, "EXEC", "spread too large relative to stop");
      return;
   }

   //--- 10) Sizing
   double actual_risk = 0.0;
   string size_err;
   double lots = ComputeLotSize(g_symbol, entry, sl, g_cfg.risk_per_trade_pct,
                                actual_risk, size_err);
   if(lots <= 0.0)
   {
      LogMsg(LOG_WARN, "SIZE", size_err);
      return;
   }

   //--- 11) Build intent
   TradeIntent ti;
   ZeroMemory(ti);
   ti.intent_id        = decision_id;
   ti.schema_version   = ALGOMIND_SCHEMA_VERSION;
   ti.strategy_version = 1;
   ti.feature_version  = g_feat.feature_version;
   ti.model_version    = ml.available ? 1 : 0;
   ti.symbol           = g_symbol;
   ti.direction        = dr.direction;
   ti.timestamp        = TimeCurrent();
   ti.expiry           = TimeCurrent() + 60;
   ti.entry_reference  = entry;
   ti.stop             = sl;
   ti.target           = tp;
   ti.score            = dr.best_score;
   ti.confidence       = dr.confidence;
   ti.regime           = rs.regime;
   ti.hypothesis       = dr.hypothesis;
   ti.reason_codes     = dr.reason;
   ti.risk_allocation  = g_cfg.risk_per_trade_pct;
   ti.data_quality     = g_ext.data_quality | g_snap.data_quality;

   string vreason;
   if(!ValidateIntent(ti, g_cfg, vreason))
   {
      LogMsg(LOG_WARN, "INTENT", vreason);
      return;
   }

   //--- 12) Execute
   ExecutionResult er = ExecuteIntent(ti, lots, g_cfg);
   if(!er.accepted)
   {
      LogMsg(LOG_ERROR, "EXEC", StringFormat("fail retcode=%u %s",
             er.retcode, er.comment));
      return;
   }
   LogMsg(LOG_INFO, "EXEC", StringFormat("filled dir=%d lots=%.2f price=%.5f",
          dr.direction, lots, er.fill_price));

   //--- 13) Register position for management
   if(er.position_id == 0 && PositionSelect(g_symbol))
      er.position_id = (ulong)PositionGetInteger(POSITION_IDENTIFIER);
   if(er.position_id != 0)
      PositionManagerRegister(er.position_id, entry, sl, tp, dr.direction,
                              atr, g_cfg);
}

//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
{
   TransactionReconHandle(trans, request, result);
}

//+------------------------------------------------------------------+
void OnTimer()
{
   PositionManagerTick(g_cfg);
}
//+------------------------------------------------------------------+