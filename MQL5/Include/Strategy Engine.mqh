#ifndef AMIGO_INCLUDE_STRATEGY_ENGINE_MQH
#define AMIGO_INCLUDE_STRATEGY_ENGINE_MQH
//+------------------------------------------------------------------+
//| StrategyEngine.mqh - continuation vs mean-reversion scoring      |
//+------------------------------------------------------------------+
#property strict

#include <Contracts header.mqh>
#include <Configuration.mqh>
#include <Regime Engine.mqh>
#include <News Policy.mqh>

struct StrategyScores
{
   double s_long;
   double s_short;
   double long_cont;
   double short_cont;
   double long_mr;
   double short_mr;
};

struct DecisionResult
{
   long            snapshot_id;
   ENUM_ACTION     action;
   int             direction;
   ENUM_HYPOTHESIS hypothesis;
   ENUM_HORIZON    horizon; // Unresolved until explicit horizon selection; never default intraday.
   double          best_score;
   double          margin;
   double          confidence;
   string          reason;
};

// Approved context eligibility; this never creates or rescues a strategy signal.
bool SelectApprovedHorizon(const TopDownContext &td,const DecisionResult &decision,
                           const ENUM_REGIME regime,const datetime boundary,
                           ENUM_HORIZON &horizon)
{
   horizon=(ENUM_HORIZON)0;
   if(!td.complete || boundary<=0 || td.asof_boundary!=boundary ||
      decision.action!=ACTION_TRADE || (decision.direction!=1 && decision.direction!=-1)) return false;
   int dirs[7]={td.d1_dir,td.h4_dir,td.h1_dir,td.m30_dir,td.m15_dir,td.m5_dir,td.m1_dir};
   int d=decision.direction;
   for(int i=0;i<7;i++)
      if(dirs[i]<-1 || dirs[i]>1 || dirs[i]==-d) return false;
   if(td.m1_dir!=d) return false;
   if(decision.hypothesis==HYP_CONTINUATION)
   {
      if(td.m5_dir!=d) return false;
      if(td.d1_dir==d && td.h4_dir==d && td.h1_dir==d)
         horizon=HORIZON_SWING;
      else if(td.h1_dir==d && td.m30_dir==d && td.m15_dir==d)
         horizon=HORIZON_INTRADAY;
      else horizon=HORIZON_SCALPING;
      return true;
   }
   if(decision.hypothesis==HYP_MEAN_REVERSION && regime==REGIME_BALANCED)
   {
      if(td.h1_dir==0 && td.m30_dir==0 && td.m15_dir==0)
         horizon=HORIZON_INTRADAY;
      else if(td.m15_dir==0 && td.m5_dir==0)
         horizon=HORIZON_SCALPING;
      return horizon!=(ENUM_HORIZON)0;
   }
   return false;
}

// One frozen entry-proxy assessment for the already selected strategy/horizon.
// Higher-timeframe eligibility remains in SelectApprovedHorizon; M1 pressure
// is never interpreted as evidence of multi-session persistence.
bool HorizonProxyAgreement(const FeatureSnapshot &f,const TopDownContext &td,
                           const DecisionResult &decision,const ENUM_REGIME regime,
                           const AmigoConfig &cfg,const datetime boundary,string &reason)
{
   reason="PROXY_SNAPSHOT_INVALID";
   if(f.snapshot_id<=0 || decision.snapshot_id!=f.snapshot_id ||
      f.decision_boundary!=boundary || f.closed_bar_time<=0 ||
      f.closed_bar_time>=boundary || f.timeframe!=PERIOD_M1 ||
      f.timestamp!=f.closed_bar_time || f.symbol!=cfg.symbol) return false;
   ENUM_HORIZON eligible=(ENUM_HORIZON)0;
   if(!SelectApprovedHorizon(td,decision,regime,boundary,eligible) || eligible!=decision.horizon)
   { reason="PROXY_HORIZON_MISMATCH"; return false; }
   if(!MathIsValidNumber(f.fusion) || !MathIsValidNumber(cfg.pressure_threshold) ||
      cfg.pressure_threshold<=0.0 || cfg.pressure_threshold>1.0)
      return false;
   if(cfg.tick_pressure_enabled && (!f.footprint_available || f.footprint_observations<2 ||
      !MathIsValidNumber(f.footprint_pressure) || MathAbs(f.footprint_pressure)>1.0))
   { reason="FROZEN_FOOTPRINT_UNAVAILABLE"; return false; }
   // Footprint pressure is correlated with delta: use as consistency veto,
   // never as an additional weighted vote. Applies to both strategies/horizons.
   if(cfg.tick_pressure_enabled && (double)decision.direction*f.footprint_pressure<=-cfg.pressure_threshold)
   { reason="FROZEN_FOOTPRINT_OPPOSES_ENTRY"; return false; }
   if(cfg.tick_pressure_enabled && (double)decision.direction*f.fusion<=-cfg.pressure_threshold)
   { reason="PROXY_PRESSURE_OPPOSES_ENTRY"; return false; }
   // Do not award extra points for correlated footprint events. Reject
   // contradictory divergence for continuation; MR can legitimately fade it.
   if(cfg.tick_pressure_enabled && decision.hypothesis==HYP_CONTINUATION &&
      ((decision.direction==1 && f.footprint_divergence_bear) ||
       (decision.direction==-1 && f.footprint_divergence_bull)))
   { reason="FOOTPRINT_DIVERGENCE_AGAINST_CONTINUATION"; return false; }
   if(cfg.tick_pressure_enabled && decision.hypothesis==HYP_CONTINUATION &&
      decision.horizon!=HORIZON_SCALPING && !f.footprint_persistent)
   { reason="FOOTPRINT_CONTINUATION_NOT_PERSISTENT"; return false; }
   // M1 persistence supports entry timing only, never the lifetime of a swing.
   // Scalp timing may use one observation; longer continuation horizons require
   // confirmation across at least two adjacent closed M1 observations.
   if(cfg.tick_pressure_enabled && decision.hypothesis==HYP_CONTINUATION &&
      decision.horizon!=HORIZON_SCALPING &&
      (f.pressure_state!=decision.direction || f.persistence<2))
   { reason="PROXY_CONTINUATION_NOT_PERSISTENT"; return false; }
   reason=cfg.tick_pressure_enabled ? "MT5_TICK_PROXY_AND_BROKER_TICK_VOLUME" : "BROKER_TICK_VOLUME_PRESSURE_DISABLED";
   return true;
}

//--- Mean-reversion evidence (Math Spec §17), directional
double MR_Evidence(const FeatureSnapshot &f, int dir)
{
   double stretch       = MathAbs(f.dev_vwap_atr);
   double stretch_score = Clip01((stretch - 1.0) / 1.5);
   bool directional_rejection=f.sweep_reject && f.last_sweep_dir==-dir;
   double rej_score     = directional_rejection ? 1.0 : 0.0;
   double div_score     = f.feature_version>=2 ? ((dir==1) ? f.divergence_bull : f.divergence_bear) : 0.0;
   double ret_val       = (f.value_state == 0) ? 1.0 : 0.0;

   //--- Directional stretch check: Long MR requires price below VWAP; Short MR requires price above VWAP
   bool direction_aligned = (dir == +1 && f.dev_vwap_atr <= 0) || (dir == -1 && f.dev_vwap_atr >= 0);
   if(!direction_aligned && stretch > 0.5) return 0.0;

   // Rejection or directionally supportive proxy pressure is required on both sides.
   // Disabled pressure is zero: neither side may treat it as confirmation.
   if(!directional_rejection && (double)dir*f.fusion < 0.10) return 0.0;

   //--- EXP-2026-05-NT: TIB directional-persistence veto + confidence boost
   // When a closed TIB bar exists and its imbalance direction opposes the
   // candidate signal, veto the hypothesis (mirrors Python TIB dir_persistence veto).
   if(f.tib_available && f.tib_direction != 0 && dir * f.tib_direction < 0) return 0.0;

   double ret = 0.40*stretch_score + 0.25*rej_score + 0.20*div_score + 0.15*ret_val;
   // Confidence boost scaled by TIB imbalance intensity (mirrors Python imb_intensity factor).
   if(f.tib_available)
   {
      double boost = Clip01(f.tib_imb_atr);
      ret = Clip01(ret * (1.0 + boost));
   }
   return ret;
}

//--- Continuation evidence (Math Spec §18), directional
double ContinuationEvidence(const FeatureSnapshot &f, int dir)
{
   double structure = 0.0;
   if((dir == +1 && f.structure_dir == +1) ||
      (dir == -1 && f.structure_dir == -1))
      structure = 1.0;

   double disp   = f.displacement;
   double accept = 0.0;
   if((dir == +1 && f.acceptance_above) ||
      (dir == -1 && f.acceptance_below))
      accept = 1.0;

   double dir_fusion = (double)dir * f.fusion;
   double pressure   = Clip01((dir_fusion - 0.25) / 0.75);
   double vol_supp   = Clip01((f.range_ratio - 1.0) / 1.0);

   //--- Delta Flip and Surge bonuses per Math Spec §15
   double flip_bonus  = ((dir == +1 && f.bull_flip) || (dir == -1 && f.bear_flip)) ? 0.15 : 0.0;
   double surge_bonus = (f.surge && dir_fusion > 0.0) ? 0.10 : 0.0;

   //--- EXP-2026-05-NT: TIB directional-persistence veto + confidence boost
   // When a closed TIB bar exists and its imbalance direction opposes the
   // candidate signal, veto the continuation hypothesis (mirrors Python TIB dir_persistence veto).
   if(f.tib_available && f.tib_direction != 0 && dir * f.tib_direction < 0) return 0.0;

   double boost = 0.0;
   if(f.tib_available)
   {
      double ib_atr = f.tib_imb_atr;
      if(ib_atr > 0.0) boost = Clip01(ib_atr);
   }
   double base_score = 0.30*structure + 0.20*disp + 0.20*accept + 0.20*pressure + 0.10*vol_supp;
   return Clip01(base_score + flip_bonus + surge_bonus + boost);
}

//--- Combine the two hypotheses into long/short scores
StrategyScores ScoreStrategies(const FeatureSnapshot &f,
                               const ExternalContext &ext,
                               const AmigoConfig &cfg)
{
   StrategyScores s;
   s.long_cont  = ContinuationEvidence(f, +1);
   s.short_cont = ContinuationEvidence(f, -1);
   s.long_mr    = MR_Evidence(f, +1);
   s.short_mr   = MR_Evidence(f, -1);

   //--- Dynamic hypothesis scoring matching current regime strength
   s.s_long  = MathMax(s.long_cont, s.long_mr);
   s.s_short = MathMax(s.short_cont, s.short_mr);

   //--- CFTC modifier (Math Spec §23, capped ±cfg.cftc_max_influence)
   if(ext.cftc_valid)
   {
      double cftc_mod = 0.0;
      if(ext.cftc_extreme)
      {
         if(ext.cftc_percentile >= 90.0)      cftc_mod = -cfg.cftc_max_influence;
         else if(ext.cftc_percentile <= 10.0) cftc_mod = +cfg.cftc_max_influence;
      }
      s.s_long  += cftc_mod;
      s.s_short -= cftc_mod;
   }

   //--- Options modifier (Math Spec §22, capped ±cfg.options_max_influence)
   if(ext.options_valid)
   {
      double opt_mod = 0.0;
      if(ext.options_gamma_regime < 0)      opt_mod = -0.05;
      else if(ext.options_gamma_regime > 0) opt_mod = +0.05;
      if(opt_mod >  cfg.options_max_influence) opt_mod =  cfg.options_max_influence;
      if(opt_mod < -cfg.options_max_influence) opt_mod = -cfg.options_max_influence;
      s.s_long  += opt_mod;
      s.s_short -= opt_mod;
   }

   s.s_long  = Clip01(s.s_long);
   s.s_short = Clip01(s.s_short);
   return s;
}

//--- Final deterministic decision gate (Math Spec §26)
DecisionResult Decide(const StrategyScores &s, const RegimeState &rs,
                     const ExternalContext &ext, const AmigoConfig &cfg,
                     uint data_quality)
{
   DecisionResult d;
   d.snapshot_id = rs.snapshot_id;
   d.action     = ACTION_NO_TRADE;
   d.direction  = 0;
   d.hypothesis = HYP_NONE;
   d.horizon    = (ENUM_HORIZON)0;
   d.best_score = MathMax(s.s_long, s.s_short);
   d.margin     = MathAbs(s.s_long - s.s_short);
   d.confidence = Clip01((d.best_score - 0.50) / 0.40);
   d.reason     = "";

   //--- Hard data-quality vetoes
   if((data_quality & DQ_FATAL) != 0)
   {
      d.action = ACTION_NO_TRADE;
      d.reason = "DQ_FATAL";
      return d;
   }
   if((data_quality & (DQ_MISSING_TICKS | DQ_BROKER_INVALID)) != 0)
   {
      d.action = ACTION_NO_TRADE;
      d.reason = "DQ_CORE_MISSING";
      return d;
   }

   //--- Regime block
   if(rs.regime == REGIME_NO_TRADE)
   {
      d.action = ACTION_NO_TRADE;
      d.reason = "REGIME_NO_TRADE";
      return d;
   }

   //--- NEWS policy shared with the early admission gate.
   datetime news_now=TimeGMT();
   string news_reason="";
   if(!AmigoNewsAdmission(ext,cfg.news_mode,news_now,cfg.stale_threshold_s,news_reason))
   {
      d.action=ACTION_NO_TRADE;
      d.reason=news_reason;
      return d;
   }

   //--- Score gate
   if(d.best_score < cfg.score_threshold || d.margin < cfg.score_margin)
   {
      d.action = ACTION_WAIT;
      d.reason = "SCORE_GATE";
      return d;
   }

   //--- Direction and hypothesis selection
   if(s.s_long >= s.s_short)
   {
      d.direction  = +1;
      d.hypothesis = (s.long_cont >= s.long_mr) ? HYP_CONTINUATION : HYP_MEAN_REVERSION;
   }
   else
   {
      d.direction  = -1;
      d.hypothesis = (s.short_cont >= s.short_mr) ? HYP_CONTINUATION : HYP_MEAN_REVERSION;
   }

   //--- Regime/hypothesis compatibility
   if(rs.preferred != HYP_NONE && rs.preferred != d.hypothesis)
   {
      d.action = ACTION_WAIT;
      d.reason = "REGIME_HYP_MISMATCH";
      return d;
   }

   d.action = ACTION_TRADE;
   d.reason = "OK";
   return d;
}
//+------------------------------------------------------------------+

#endif // AMIGO_INCLUDE_STRATEGY_ENGINE_MQH
