//+------------------------------------------------------------------+
//| StrategyEngine.mqh - continuation vs mean-reversion scoring      |
//+------------------------------------------------------------------+
#property strict

#include <Contracts header.mqh>
#include <Configuration.mqh>
#include <Regime Engine.mqh>

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
   ENUM_ACTION     action;
   int             direction;
   ENUM_HYPOTHESIS hypothesis;
   double          best_score;
   double          margin;
   double          confidence;
   string          reason;
};

//--- Mean-reversion evidence (Math Spec §17), directional
double MR_Evidence(const FeatureSnapshot &f, int dir)
{
   double stretch       = MathAbs(f.dev_vwap_atr);
   double stretch_score = Clip01((stretch - 1.0) / 1.5);
   double rej_score     = f.sweep_reject ? 1.0 : 0.0;
   double div_score     = f.delta_divergence;
   double ret_val       = (f.value_state == 0) ? 1.0 : 0.0;

   //--- Directional stretch check: Long MR requires price below VWAP; Short MR requires price above VWAP
   bool direction_aligned = (dir == +1 && f.dev_vwap_atr <= 0) || (dir == -1 && f.dev_vwap_atr >= 0);
   if(!direction_aligned && stretch > 0.5) return 0.0;

   //--- Higher quality gate for Long MR: Require sweep rejection OR positive order flow fusion
   if(dir == +1 && !f.sweep_reject && f.fusion < 0.10) return 0.0;

   return 0.40*stretch_score + 0.25*rej_score + 0.20*div_score + 0.15*ret_val;
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

   double base_score = 0.30*structure + 0.20*disp + 0.20*accept + 0.20*pressure + 0.10*vol_supp;
   return Clip01(base_score + flip_bonus + surge_bonus);
}

//--- Combine the two hypotheses into long/short scores
StrategyScores ScoreStrategies(const FeatureSnapshot &f,
                               const ExternalContext &ext,
                               const AlgoMindConfig &cfg)
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
                     const ExternalContext &ext, const AlgoMindConfig &cfg,
                     uint data_quality)
{
   DecisionResult d;
   d.action     = ACTION_NO_TRADE;
   d.direction  = 0;
   d.hypothesis = HYP_NONE;
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