//+------------------------------------------------------------------+
//| Logger.mqh                                                       |
//+------------------------------------------------------------------+
#property strict

//--- Contract.mqh must be included so ENUM_ACTION / ENUM_REGIME /
//--- ENUM_HYPOTHESIS are visible in this translation unit.
#include <Contracts header.mqh>

enum ENUM_LOG_LEVEL
{
   LOG_DEBUG = 0,
   LOG_INFO  = 1,
   LOG_WARN  = 2,
   LOG_ERROR = 3
};

int  g_log_level    = LOG_INFO;
long g_decision_seq = 0;

void LogInit(int level)
{
   g_log_level = level;
}

void LogMsg(ENUM_LOG_LEVEL lvl, string module, string msg)
{
   if(lvl < g_log_level) return;
   string tag = (lvl == LOG_DEBUG ? "DEBUG" :
                 lvl == LOG_INFO  ? "INFO"  :
                 lvl == LOG_WARN  ? "WARN"  : "ERROR");
   PrintFormat("[AlgoMind][%s][%s] %s", tag, module, msg);
}

void LogDecision(long decision_id, string symbol, ENUM_ACTION action,
                 ENUM_REGIME regime, ENUM_HYPOTHESIS hyp,
                 double score, string reason)
{
   PrintFormat("[AlgoMind][DECISION] id=%I64d sym=%s act=%d reg=%d hyp=%d score=%.4f reason=%s",
               decision_id, symbol, (int)action, (int)regime, (int)hyp, score, reason);
}

void LogFeatureDiagnostics(datetime ts, string symbol, ENUM_TIMEFRAMES tf,
                           int regime, int struct_dir, double fusion,
                           bool bull_flip, bool bear_flip, bool surge,
                           bool sweep_reject, double cont_l, double cont_s,
                           double mr_l, double mr_s, double s_l, double s_s,
                           double best_score, double margin, double th,
                           double margin_th, ENUM_ACTION action, string reason)
{
   if(LOG_INFO < g_log_level) return;
   PrintFormat("[AlgoMind][DIAG] ts=%s sym=%s tf=%d reg=%d dir=%d fus=%.3f flip_u=%d flip_d=%d surge=%d swp=%d cntL=%.3f cntS=%.3f mrL=%.3f mrS=%.3f sL=%.3f sS=%.3f best=%.3f mrg=%.3f th=%.2f mrg_th=%.2f act=%d rsn=%s",
               TimeToString(ts, TIME_DATE|TIME_MINUTES), symbol, (int)tf, regime, struct_dir,
               fusion, (int)bull_flip, (int)bear_flip, (int)surge, (int)sweep_reject,
               cont_l, cont_s, mr_l, mr_s, s_l, s_s, best_score, margin, th, margin_th,
               (int)action, reason);
}

void LogMGLEShadow(datetime ts, string symbol, string macro_regime, double ry_z, double usd_z, double cftc_pct, string cftc_extreme, double geo_index, int active_levels_count)
{
   if(LOG_INFO < g_log_level) return;
   PrintFormat("[AlgoMind][MGLE_SHADOW] ts=%s sym=%s reg=%s ry_z=%.2f usd_z=%.2f cftc_pct=%.1f%% cftc_ext=%s geo_idx=%.2f active_lvls=%d (SHADOW_MODE=1)",
               TimeToString(ts, TIME_DATE|TIME_MINUTES), symbol, macro_regime, ry_z, usd_z, cftc_pct, cftc_extreme, geo_index, active_levels_count);
}

long NextDecisionId()
{
   g_decision_seq++;
   return (long)TimeCurrent() * 1000 + g_decision_seq;
}
//+------------------------------------------------------------------+