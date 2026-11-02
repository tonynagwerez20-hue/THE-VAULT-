//+------------------------------------------------------------------+
//| RegimeEngine.mqh - market state machine                          |
//+------------------------------------------------------------------+
#property strict

#include <Contracts header.mqh>
#include <Configuration.mqh>

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

double ScoreTrendUp(const FeatureSnapshot &f)
{
   double structure = (f.structure_dir == +1) ? 1.0 : 0.0;
   double pressure  = (f.pressure_state == +1) ? 1.0 : 0.0;
   double accept    = f.acceptance_above ? 1.0 : 0.0;
   double partic    = Clip01((f.persistence > 0) ? f.persistence / 5.0 : 0.0);
   return 0.35*structure + 0.25*pressure + 0.20*accept + 0.20*partic;
}

double ScoreTrendDown(const FeatureSnapshot &f)
{
   double structure = (f.structure_dir == -1) ? 1.0 : 0.0;
   double pressure  = (f.pressure_state == -1) ? 1.0 : 0.0;
   double accept    = f.acceptance_below ? 1.0 : 0.0;
   double partic    = Clip01((f.persistence < 0) ? -f.persistence / 5.0 : 0.0);
   return 0.35*structure + 0.25*pressure + 0.20*accept + 0.20*partic;
}

double ScoreExpansion(const FeatureSnapshot &f)
{
   double range_exp = Clip01((f.range_ratio - 1.0) / 1.0);
   double vol_exp   = Clip01((f.vol_percentile - 60.0) / 40.0);
   return 0.50*range_exp + 0.30*vol_exp + 0.20*0.0;
}

double ScoreBalance(const FeatureSnapshot &f)
{
   double inside   = (f.value_state == 0) ? 1.0 : 0.0;
   double vwap_rot = (MathAbs(f.dev_vwap_atr) < 0.5) ? 1.0 : 0.0;
   double low_dir  = (f.structure_dir == 0) ? 1.0 : 0.0;
   return 0.45*inside + 0.30*vwap_rot + 0.25*low_dir;
}

double ScoreExhaustion(const FeatureSnapshot &f)
{
   double div   = 0.0;
   double rej   = f.sweep_reject ? 1.0 : 0.0;
   double decay = 0.0;
   return 0.40*div + 0.30*rej + 0.30*decay;
}

RegimeState EvaluateRegime(const FeatureSnapshot &f, const AlgoMindConfig &cfg)
{
   RegimeState rs;
   rs.timestamp = f.timestamp;
   rs.reason_codes = "";

   double tu = ScoreTrendUp(f);
   double td = ScoreTrendDown(f);
   double ex = ScoreExpansion(f);
   double ba = ScoreBalance(f);
   double xh = ScoreExhaustion(f);

   double      cs[5];
   ENUM_REGIME cr[5];
   cs[0] = tu; cr[0] = REGIME_TREND_UP;
   cs[1] = td; cr[1] = REGIME_TREND_DOWN;
   cs[2] = ex; cr[2] = REGIME_EXPANSION;
   cs[3] = ba; cr[3] = REGIME_BALANCED;
   cs[4] = xh; cr[4] = REGIME_EXHAUSTION;

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
      case REGIME_EXHAUSTION:
         rs.preferred = HYP_MEAN_REVERSION;
         rs.risk_modifier = 1.0;
         break;
      case REGIME_EXPANSION:
         rs.preferred = HYP_NONE;
         rs.risk_modifier = 0.5;
         break;
      case REGIME_NEWS:
         rs.preferred = HYP_NONE;
         rs.risk_modifier = 0.5;
         break;
      default:
         rs.preferred = HYP_NONE;
         rs.risk_modifier = 0.0;
         break;
   }
   return rs;
}
//+------------------------------------------------------------------+