//+------------------------------------------------------------------+
//| RegimeEngine.mqh - multi-timeframe market state machine          |
//+------------------------------------------------------------------+
#property strict

#include <Contracts header.mqh>
#include <Configuration.mqh>
#include <Structure Engine.mqh>

struct RegimePersist
{
   ENUM_REGIME current;
   ENUM_REGIME candidate;
   int         candidate_count;
   double      current_score;
};

RegimePersist g_regime_state = {REGIME_NO_TRADE, REGIME_NONE, 0, 0.0};

double Clip01(double x)
{
   if(x < 0.0) return 0.0;
   if(x > 1.0) return 1.0;
   return x;
}

//+------------------------------------------------------------------+
//| Multi-Timeframe Scoring Functions                                |
//+------------------------------------------------------------------+
double ScoreTrendUp(const FeatureSnapshot &f, const TopDownContext &td)
{
   // Synthesize Higher-Timeframe (D1/H4/H1) structural authority
   int htf_bias = 0;
   if(td.h4_dir == td.h1_dir && td.h4_dir != 0) htf_bias = td.h4_dir;
   else if(td.h1_dir != 0)                      htf_bias = td.h1_dir;
   else                                         htf_bias = td.h4_dir;

   // D1 Macro Context Integration (Workstream B):
   // If D1 strongly opposes H4/H1 directional bias, neutralize HTF continuation weight
   if(htf_bias != 0 && td.d1_dir != 0 && htf_bias != td.d1_dir)
      htf_bias = 0;

   // FAIL-CLOSED ZERO-CREDIT FOR NEUTRAL OR OPPOSING HTF
   double htf_weight = (htf_bias == +1) ? 1.0 : 0.0;
   double ltf_weight = (f.structure_dir == +1) ? 1.0 : 0.0;
   double pressure   = (f.pressure_state == +1) ? 1.0 : 0.0;
   double accept     = f.acceptance_above ? 1.0 : 0.0;
   double align_mod  = td.alignment_score;

   // Mathematically Balanced Authority Weights:
   // 45% HTF Structural Authority, 20% Local Structure, 15% Flow Pressure, 10% Acceptance, 10% Alignment Score
   // When HTF is Neutral (htf_weight = 0): Max possible = 0.20 + 0.15 + 0.10 + (0.10 * 0.50) = 0.500 < 0.60
   // When HTF is Opposing (htf_weight = 0, conflict A=0.25): Max possible = 0.20 + 0.15 + 0.10 + (0.10 * 0.25) = 0.475 < 0.60
   return 0.45*htf_weight + 0.20*ltf_weight + 0.15*pressure + 0.10*accept + 0.10*align_mod;
}

double ScoreTrendDown(const FeatureSnapshot &f, const TopDownContext &td)
{
   int htf_bias = 0;
   if(td.h4_dir == td.h1_dir && td.h4_dir != 0) htf_bias = td.h4_dir;
   else if(td.h1_dir != 0)                      htf_bias = td.h1_dir;
   else                                         htf_bias = td.h4_dir;

   // D1 Macro Context Integration (Workstream B):
   // If D1 strongly opposes H4/H1 directional bias, neutralize HTF continuation weight
   if(htf_bias != 0 && td.d1_dir != 0 && htf_bias != td.d1_dir)
      htf_bias = 0;

   // FAIL-CLOSED ZERO-CREDIT FOR NEUTRAL OR OPPOSING HTF
   double htf_weight = (htf_bias == -1) ? 1.0 : 0.0;
   double ltf_weight = (f.structure_dir == -1) ? 1.0 : 0.0;
   double pressure   = (f.pressure_state == -1) ? 1.0 : 0.0;
   double accept     = f.acceptance_below ? 1.0 : 0.0;
   double align_mod  = td.alignment_score;

   return 0.45*htf_weight + 0.20*ltf_weight + 0.15*pressure + 0.10*accept + 0.10*align_mod;
}

double ScoreExpansion(const FeatureSnapshot &f, const TopDownContext &td)
{
   double range_exp = Clip01((f.range_ratio - 1.0) / 1.0);
   double vol_exp   = Clip01((f.vol_percentile - 60.0) / 40.0);
   double align_boost = td.aligned ? 0.20 : 0.0;
   return 0.50*range_exp + 0.30*vol_exp + align_boost;
}

double ScoreBalance(const FeatureSnapshot &f, const TopDownContext &td)
{
   double inside    = (f.value_state == 0) ? 1.0 : 0.0;
   double vwap_rot  = (MathAbs(f.dev_vwap_atr) < 0.5) ? 1.0 : 0.0;
   double conflict  = td.conflict ? 1.0 : 0.0;
   return 0.40*inside + 0.30*vwap_rot + 0.30*conflict;
}

double ScoreExhaustion(const FeatureSnapshot &f, const TopDownContext &td)
{
   // Strict conjunctive countertrend gating: requires confirmed sweep reject AND >= 2.0 ATR extension
   // Preserves the authoritative documented 2.0 ATR requirement (Section 6)
   if(!f.sweep_reject || MathAbs(f.dev_vwap_atr) < 2.0)
      return 0.0;

   double div = Clip01(f.delta_divergence);
   double ext = Clip01((MathAbs(f.dev_vwap_atr) - 2.0) / 2.0);
   return 0.50 + 0.25*div + 0.25*ext;
}

//+------------------------------------------------------------------+
//| Multi-Timeframe Regime Evaluator (Authoritative Context)         |
//+------------------------------------------------------------------+
RegimeState EvaluateRegime(const FeatureSnapshot &f, const TopDownContext &td, const AmigoConfig &cfg)
{
   RegimeState rs;
   rs.timestamp = f.timestamp;
   rs.reason_codes = td.summary;

   // Fail-closed guard: missing or corrupt higher timeframe context
   if(td.summary == "BALANCED_OR_INSUFFICIENT_HTF_DATA" && td.alignment_score < 0.40)
   {
      rs.regime = REGIME_NO_TRADE;
      rs.confidence = 0.0;
      rs.preferred = HYP_NONE;
      rs.risk_modifier = 0.0;
      return rs;
   }

   double tu = ScoreTrendUp(f, td);
   double td_score = ScoreTrendDown(f, td);
   double ex = ScoreExpansion(f, td);
   double ba = ScoreBalance(f, td);
   double xh = ScoreExhaustion(f, td);

   double      cs[5];
   ENUM_REGIME cr[5];
   cs[0] = tu;       cr[0] = REGIME_TREND_UP;
   cs[1] = td_score; cr[1] = REGIME_TREND_DOWN;
   cs[2] = ex;       cr[2] = REGIME_EXPANSION;
   cs[3] = ba;       cr[3] = REGIME_BALANCED;
   cs[4] = xh;       cr[4] = REGIME_EXHAUSTION;

   int best = 0;
   for(int i = 1; i < 5; i++)
      if(cs[i] > cs[best]) best = i;

   ENUM_REGIME new_cand  = cr[best];
   double      new_score = cs[best];

   if(new_cand == g_regime_state.candidate)
      g_regime_state.candidate_count++;
   else
   {
      g_regime_state.candidate = new_cand;
      g_regime_state.candidate_count = 1;
   }

   bool transition = false;
   if(g_regime_state.current == REGIME_NO_TRADE ||
      g_regime_state.current == REGIME_NONE)
   {
      if(new_score >= cfg.regime_threshold &&
         g_regime_state.candidate_count >= cfg.regime_persistence)
         transition = true;
   }
   else if(new_cand != g_regime_state.current)
   {
      if(new_score >= cfg.regime_threshold &&
         new_score >= g_regime_state.current_score + cfg.regime_hysteresis &&
         g_regime_state.candidate_count >= cfg.regime_persistence)
         transition = true;
   }

   if(transition)
   {
      g_regime_state.current = new_cand;
      g_regime_state.current_score = new_score;
   }

   rs.regime     = g_regime_state.current;
   rs.confidence = g_regime_state.current_score;

   switch(rs.regime)
   {
      case REGIME_TREND_UP:
      case REGIME_TREND_DOWN:
         rs.preferred = HYP_CONTINUATION;
         rs.risk_modifier = 1.0;
         break;
      case REGIME_BALANCED:
         rs.preferred = HYP_MEAN_REVERSION;
         rs.risk_modifier = 0.8;
         break;
      case REGIME_EXHAUSTION:
         rs.preferred = HYP_MEAN_REVERSION;
         rs.risk_modifier = 0.5; // Strictly aligned with documented 0.50 countertrend risk modifier
         break;
      case REGIME_EXPANSION:
         rs.preferred = HYP_NONE;
         rs.risk_modifier = 0.5;
         break;
      case REGIME_NEWS:
         rs.preferred = HYP_NONE;
         rs.risk_modifier = 0.0;
         break;
      default:
         rs.preferred = HYP_NONE;
         rs.risk_modifier = 0.0;
         break;
   }
   return rs;
}

//+------------------------------------------------------------------+
//| Backward Compatibility Overload                                  |
//+------------------------------------------------------------------+
RegimeState EvaluateRegime(const FeatureSnapshot &f, const AmigoConfig &cfg)
{
   TopDownContext dummy_td;
   dummy_td.d1_dir = 0;
   dummy_td.h4_dir = 0;
   dummy_td.h1_dir = 0;
   dummy_td.m30_dir = 0;
   dummy_td.m15_dir = 0;
   dummy_td.m5_dir = f.structure_dir;
   dummy_td.m1_dir = 0;
   dummy_td.aligned = false;
   dummy_td.conflict = false;
   dummy_td.alignment_score = 0.50;
   dummy_td.summary = "SINGLE_TF_FALLBACK";

   return EvaluateRegime(f, dummy_td, cfg);
}
//+------------------------------------------------------------------+
