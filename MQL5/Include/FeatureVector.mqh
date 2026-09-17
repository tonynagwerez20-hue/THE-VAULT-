//+------------------------------------------------------------------+
//| FeatureVector.mqh - canonical feature assembly                   |
//+------------------------------------------------------------------+
#property strict

#include <Contracts header.mqh>
#include <Configuration.mqh>
#include <Bar Collector.mqh>
#include <OrderFlow.mqh>
#include <Structure Engine.mqh>
#include <FVG Engine.mqh>
#include <Auction.mqh>

bool BuildFeatureVector(const string symbol, const AlgoMindConfig &cfg,
                        FeatureSnapshot &fs)
{
   fs.timestamp = TimeCurrent();
   fs.feature_version = 1;

   MqlRates r[];
   int got = CopyRates(symbol, cfg.tf_exec, 1, 260, r);
   if(got < 60) return false;

   double atr = ComputeATR14(symbol, cfg.tf_exec, cfg.atr_period);
   if(atr <= 0.0) return false;
   fs.atr14 = atr;
   fs.range_ratio = ComputeRangeRatio(symbol, cfg.tf_exec);
   fs.vol_percentile = 50.0;

   static int s_prev_dir = 0;
   StructureState st = EvaluateStructure(symbol, cfg.tf_exec, atr, s_prev_dir);
   s_prev_dir = st.dir;
   fs.structure_dir = st.dir;
   fs.bull_choch = st.bull_choch;
   fs.bear_choch = st.bear_choch;
   fs.bos_age_bars = 0.0;

   datetime sess_start = iTime(symbol, PERIOD_D1, 0);
   fs.vwap = ComputeSessionVWAP(symbol, cfg.tf_exec, sess_start);
   fs.dev_vwap_atr = (fs.vwap > 0.0) ? (r[0].close - fs.vwap) / atr : 0.0;

   double poc = 0.0, vah = 0.0, val = 0.0;
   double bin = MathMax(4.0 * SymbolInfoDouble(symbol, SYMBOL_POINT),
                        SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE));
   ComputeValueArea(symbol, cfg.tf_exec, sess_start, bin, poc, vah, val);
   fs.poc = poc; fs.vah = vah; fs.val = val;

   if(vah > val)
   {
      if(r[0].close > vah) fs.value_state = +1;
      else if(r[0].close < val) fs.value_state = -1;
      else fs.value_state = 0;
   }
   else fs.value_state = 0;

   int tick_count = 0;
   datetime bar_close_0 = (1 < got) ? r[1].time : TimeCurrent();
   fs.delta_a = ComputeDeltaA(symbol, r[0].time, bar_close_0, tick_count);
   fs.delta_b = ComputeDeltaB(r, 0);

   double histA[], histB[];
   ArrayResize(histA, 20); ArrayResize(histB, 20);
   histA[0] = fs.delta_a; histB[0] = fs.delta_b;
   for(int i=1; i<20 && i<got; i++)
   {
      int tc = 0;
      datetime b_close = r[i-1].time;
      histA[i] = ComputeDeltaA(symbol, r[i].time, b_close, tc);
      histB[i] = ComputeDeltaB(r, i);
   }
   fs.fusion = ComputeFusion(fs.delta_a, fs.delta_b, histA, histB);

   if(fs.fusion >= cfg.pressure_threshold)        fs.pressure_state = +1;
   else if(fs.fusion <= -cfg.pressure_threshold)  fs.pressure_state = -1;
   else                                            fs.pressure_state = 0;

   static int s_prev_press = 0;
   fs.bull_flip = (s_prev_press == -1 && fs.pressure_state == +1);
   fs.bear_flip = (s_prev_press == +1 && fs.pressure_state == -1);
   s_prev_press = fs.pressure_state;

   fs.surge = (MathAbs(fs.fusion) >= cfg.surge_threshold);
   fs.persistence = 0;

   fs.fvg_active_bull = false;
   fs.fvg_active_bear = false;
   fs.fvg_fill_pct = 0.0;
   for(int i=2; i<MathMin(20, got-2); i++)
   {
      bool is_bull; double up, lo;
      if(DetectFVG(r, i, atr, is_bull, up, lo))
      {
         FVGEvent e;
         e.created_ts = r[i].time;
         e.is_bull = is_bull; e.upper = up; e.lower = lo;
         e.active = true; e.mitigated=false; e.invalidated=false; e.fill_pct=0.0;
         for(int j=i-1; j>=0; j--) UpdateFVGState(e, r, j);
         if(e.active)
         {
            if(e.is_bull) { fs.fvg_active_bull = true; fs.fvg_fill_pct = e.fill_pct; }
            else          { fs.fvg_active_bear = true; fs.fvg_fill_pct = e.fill_pct; }
            break;
         }
      }
   }

   fs.last_sweep_dir = 0;
   fs.sweep_reject = false;
   fs.acceptance_above = false;
   fs.acceptance_below = false;

   return true;
}
//+------------------------------------------------------------------+