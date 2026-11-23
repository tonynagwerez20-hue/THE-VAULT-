//+------------------------------------------------------------------+
//| FeatureVector.mqh - canonical feature assembly                   |
//+------------------------------------------------------------------+
#property strict

#include <Contracts header.mqh>
#include <Configuration.mqh>
#include <Bar Collector.mqh>
#include <Chronology Validation.mqh>
#include <OrderFlow.mqh>
#include <Structure Engine.mqh>
#include <FVG Engine.mqh>
#include <Auction.mqh>
#include <AM_FlowEvents.mqh>

struct AMIGOFeatureState
{
   int structure_direction;
   int pressure_state;
};

AMIGOFeatureState g_amigo_feature_state = {0, 0};

bool FeatureSnapshotNumericsValid(const FeatureSnapshot &fs)
{
   return MathIsValidNumber(fs.atr14) && MathIsValidNumber(fs.range_ratio) &&
          MathIsValidNumber(fs.vol_percentile) && MathIsValidNumber(fs.bos_age_bars) &&
          MathIsValidNumber(fs.vwap) && MathIsValidNumber(fs.dev_vwap_atr) &&
          MathIsValidNumber(fs.poc) && MathIsValidNumber(fs.vah) &&
          MathIsValidNumber(fs.val) && MathIsValidNumber(fs.delta_a) &&
          MathIsValidNumber(fs.delta_b) && MathIsValidNumber(fs.fusion) &&
          MathIsValidNumber(fs.fvg_fill_pct) &&
          MathIsValidNumber(fs.delta_divergence) &&
          MathIsValidNumber(fs.divergence_bull) && MathIsValidNumber(fs.divergence_bear) &&
          MathIsValidNumber(fs.displacement);
}

bool BuildFeatureVector(const string symbol, const AmigoConfig &cfg,
                        FeatureSnapshot &fs, AMIGOFeatureState &state,
                        MqlRates &feature_evidence[])
{
   fs.feature_version = 2;
   // Keep caller-owned feature state transactional: this function has many
   // later failure exits, so stage pressure state until complete assembly.
   int next_pressure_state=state.pressure_state;

   MqlRates r[];
   if(!ArraySetAsSeries(r, true)) return false;
   int got = CopyRates(symbol, cfg.tf_exec, 1, 260, r);
   datetime feature_boundary=iTime(symbol,cfg.tf_exec,0);
   datetime feature_latest=iTime(symbol,cfg.tf_exec,1);
   int exec_period_seconds=PeriodSeconds(cfg.tf_exec);
   if(!ValidateClosedRateSequence(r,got,feature_boundary,feature_latest,60,260,
                                  exec_period_seconds,false)) return false;
   if(iTime(symbol,cfg.tf_exec,0)!=feature_boundary ||
      iTime(symbol,cfg.tf_exec,1)!=feature_latest) return false;
   fs.timestamp = feature_latest;

   // Derive ATR and range from this validated closed-bar snapshot. Separate
   // indicator/history reads could observe a different revision of the bars.
   if(cfg.atr_period<=0 || cfg.atr_period>=got || got<21) return false;
   double atr_sum=0.0;
   for(int p=0;p<cfg.atr_period;p++)
   {
      double h=r[p].high, l=r[p].low, previous_close=r[p+1].close;
      double tr=MathMax(h-l,MathMax(MathAbs(h-previous_close),MathAbs(l-previous_close)));
      if(!MathIsValidNumber(tr) || tr<0.0) return false;
      atr_sum+=tr;
      if(!MathIsValidNumber(atr_sum)) return false;
   }
   double atr=atr_sum/cfg.atr_period;
   double prior_ranges[20];
   for(int p=0;p<20;p++) prior_ranges[p]=r[p+1].high-r[p+1].low;
   if(!MathIsValidNumber(atr) || atr<=0.0 || !ArraySort(prior_ranges)) return false;
   double median_range=prior_ranges[10];
   double current_range=r[0].high-r[0].low;
   if(!MathIsValidNumber(median_range) || median_range<=0.0 ||
      !MathIsValidNumber(current_range) || current_range<0.0) return false;
   fs.atr14=atr;
   fs.range_ratio=current_range/median_range;
   if(!MathIsValidNumber(fs.range_ratio)) return false;
   // Volatility rank, not traded-volume rank: compare closed-bar ranges.
   if(!ProxyPriorPercentile(current_range,prior_ranges,fs.vol_percentile)) return false;

   int s_prev_dir = state.structure_direction;
   StructureState st;
   if(!EvaluateStructureFromClosedRates(r,(got<200 ? got : 200),atr,s_prev_dir,st)) return false;
   s_prev_dir = st.dir;
   fs.structure_dir = st.dir;
   fs.bull_choch = st.bull_choch;
   fs.bear_choch = st.bear_choch;
   fs.bos_age_bars = 0.0;

   datetime sess_start = iTime(symbol, PERIOD_D1, 0);
   if(sess_start<=0 || sess_start>feature_latest) return false;
   int nominal_seconds=PeriodSeconds(cfg.tf_exec);
   if(nominal_seconds<=0) return false;
   MqlRates session_rates[];
   if(!ArraySetAsSeries(session_rates,true)) return false;
   int session_count=Bars(symbol,cfg.tf_exec,sess_start,(datetime)(feature_boundary-1));
   if(session_count<5 || session_count>2048) return false;
   int session_copy=CopyRates(symbol,cfg.tf_exec,1,session_count,session_rates);
   if(session_copy!=session_count || ArraySize(session_rates)!=session_count ||
      !ValidateClosedRateSequence(session_rates,session_count,feature_boundary,
                                  feature_latest,5,2048,nominal_seconds,true) ||
      session_rates[session_count-1].time<sess_start ||
      Bars(symbol,cfg.tf_exec,sess_start,(datetime)(feature_boundary-1))!=session_count ||
      iTime(symbol,cfg.tf_exec,0)!=feature_boundary ||
      iTime(symbol,cfg.tf_exec,1)!=feature_latest ||
      iTime(symbol,PERIOD_D1,0)!=sess_start) return false;
   for(int q=0;q<session_count;q++)
   {
      if(session_rates[q].time<sess_start || session_rates[q].time>=feature_boundary ||
         (q>0 && session_rates[q].time>=session_rates[q-1].time) ||
         (q>0 && session_rates[q-1].time-session_rates[q].time!=nominal_seconds) ||
         !MathIsValidNumber(session_rates[q].open) || !MathIsValidNumber(session_rates[q].high) ||
         !MathIsValidNumber(session_rates[q].low) || !MathIsValidNumber(session_rates[q].close) ||
         session_rates[q].open<=0.0 || session_rates[q].low<=0.0 ||
         session_rates[q].high<session_rates[q].low ||
         session_rates[q].open<session_rates[q].low || session_rates[q].open>session_rates[q].high ||
         session_rates[q].close<session_rates[q].low || session_rates[q].close>session_rates[q].high ||
         session_rates[q].tick_volume<0 || session_rates[q].real_volume<0 || session_rates[q].spread<0)
         return false;
      if(q<got && (session_rates[q].time!=r[q].time ||
         session_rates[q].open!=r[q].open || session_rates[q].high!=r[q].high ||
         session_rates[q].low!=r[q].low || session_rates[q].close!=r[q].close ||
         session_rates[q].tick_volume!=r[q].tick_volume ||
         session_rates[q].real_volume!=r[q].real_volume || session_rates[q].spread!=r[q].spread))
         return false;
   }
   double poc = 0.0, vah = 0.0, val = 0.0, session_vwap=0.0;
   double bin = MathMax(4.0 * SymbolInfoDouble(symbol, SYMBOL_POINT),
                        SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE));
   if(!ComputeClosedSessionValue(session_rates,session_count,bin,session_vwap,poc,vah,val)) return false;
   fs.vwap=session_vwap;
   fs.dev_vwap_atr=(r[0].close-session_vwap)/atr;
   if(!MathIsValidNumber(fs.dev_vwap_atr) ||
      iTime(symbol,cfg.tf_exec,0)!=feature_boundary ||
      iTime(symbol,cfg.tf_exec,1)!=feature_latest ||
      iTime(symbol,PERIOD_D1,0)!=sess_start) return false;
   fs.poc = poc; fs.vah = vah; fs.val = val;

   if(vah > val)
   {
      if(r[0].close > vah) fs.value_state = +1;
      else if(r[0].close < val) fs.value_state = -1;
      else fs.value_state = 0;
   }
   else fs.value_state = 0;

   fs.footprint_available=false;
   fs.footprint_persistent=false; fs.footprint_divergence_bull=false; fs.footprint_divergence_bear=false;
   fs.footprint_pressure=0.0; fs.footprint_poc=0.0; fs.footprint_concentration=0.0; fs.footprint_observations=0;
   double histA[20], histB[20], normalizedA[20];
   double footprint_pressure[20],footprint_activity[20];
   if(got<21) return false;
   for(int i=0;i<20;i++) { histA[i]=0.0; histB[i]=0.0; normalizedA[i]=0.0; }
   if(cfg.tick_pressure_enabled)
   {
      long proxy_chart_mode=-1;
      if(!SymbolInfoInteger(symbol,SYMBOL_CHART_MODE,proxy_chart_mode) ||
         (proxy_chart_mode!=SYMBOL_CHART_MODE_BID && proxy_chart_mode!=SYMBOL_CHART_MODE_LAST)) return false;
      for(int i=0;i<20;i++)
      {
         int tc=0;
         FrozenFootprint window_footprint;
         datetime tick_end=(i==0) ? feature_boundary : r[i-1].time;
         // Without an authoritative calendar, a missing interval cannot be
         // labeled a normal closure. Do not aggregate across that gap.
         if(tick_end<=r[i].time || tick_end-r[i].time!=nominal_seconds ||
            r[i].tick_volume<=0 ||
            !TryComputeDeltaA(symbol,r[i].time,tick_end,histA[i],tc,window_footprint,bin,proxy_chart_mode)) return false;
         if(tc<=0 || !window_footprint.available) return false;
         footprint_pressure[i]=window_footprint.pressure;
         footprint_activity[i]=(double)window_footprint.observations;
         if(i==0)
         {
            fs.footprint_available=true;
            fs.footprint_pressure=window_footprint.pressure;
            fs.footprint_poc=window_footprint.poc;
            fs.footprint_concentration=window_footprint.concentration;
            fs.footprint_observations=window_footprint.observations;
         }
         normalizedA[i]=histA[i]/(double)tc; // signed price moves per observation, [-1,1]
         histB[i] = ComputeDeltaB(r, i);
         if(!MathIsValidNumber(histB[i])) return false;
      }
      long final_chart_mode=-1;
      if(!SymbolInfoInteger(symbol,SYMBOL_CHART_MODE,final_chart_mode) || final_chart_mode!=proxy_chart_mode) return false;
      // Replay the bounded closed evidence oldest-to-newest into a LOCAL
      // instance. No forming tick or persistent diagnostic state enters here.
      CAM_FlowEvents frozen_events(2);
      CAM_FlowPressure frozen_classifier(cfg.pressure_threshold,cfg.surge_threshold,1.5);
      for(int e=19;e>=0;e--)
         frozen_events.AddBar(r[e].time,footprint_pressure[e],
            frozen_classifier.ClassifyState(footprint_pressure[e]),r[e].high,r[e].low,footprint_activity[e]);
      fs.footprint_persistent=frozen_events.IsPersistent();
      fs.footprint_divergence_bull=frozen_events.IsBullishDivergence();
      fs.footprint_divergence_bear=frozen_events.IsBearishDivergence();
      fs.delta_a=histA[0];
      fs.delta_b=histB[0];
      fs.fusion = ComputeFusion(fs.delta_a, fs.delta_b, histA, histB);
      if(fs.fusion >= cfg.pressure_threshold)        fs.pressure_state = +1;
      else if(fs.fusion <= -cfg.pressure_threshold)  fs.pressure_state = -1;
      else                                            fs.pressure_state = 0;
      fs.bull_flip=(state.pressure_state==-1 && fs.pressure_state==+1);
      fs.bear_flip=(state.pressure_state==+1 && fs.pressure_state==-1);
      next_pressure_state=fs.pressure_state;
      fs.surge=(MathAbs(fs.fusion)>=cfg.surge_threshold);
   }
   else
   {
      // No tick-history dependency or scoring contribution when the proxy is
      // disabled. Preserve raw price-derived structure and value features.
      fs.delta_a=0.0; fs.delta_b=0.0; fs.fusion=0.0;
      fs.pressure_state=0; fs.bull_flip=false; fs.bear_flip=false; fs.surge=false;
      next_pressure_state=0;
   }
   fs.persistence = cfg.tick_pressure_enabled ? ProxyDirectionalPersistence(normalizedA,fs.pressure_state) : 0;

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

   fs.last_sweep_dir = st.last_sweep_dir;
   fs.sweep_reject   = st.sweep_reject;
   fs.acceptance_available=ClosedValueAcceptance(session_rates,session_count,bin,fs.acceptance_above,fs.acceptance_below);

   //--- Approved GAP-01 & GAP-02 Strategy Evidence Calculations
   //--- GAP-01: Classical Price vs Proxy-CVD Divergence
   double div_bear = 0.0, div_bull = 0.0;
   int sh_idx1 = -1, sh_idx2 = -1;
   int sl_idx1 = -1, sl_idx2 = -1;
   int max_lookback = MathMin(20, got - 2);
   for(int i=2; i<max_lookback; i++)
   {
      if(IsConfirmedSwingHigh(r, i, 2))
      {
         if(sh_idx1 < 0) sh_idx1 = i;
         else if(sh_idx2 < 0) { sh_idx2 = i; break; }
      }
   }
   for(int i=2; i<max_lookback; i++)
   {
      if(IsConfirmedSwingLow(r, i, 2))
      {
         if(sl_idx1 < 0) sl_idx1 = i;
         else if(sl_idx2 < 0) { sl_idx2 = i; break; }
      }
   }

   int hist_size = ArraySize(histA);
   if(sh_idx1 > 0 && sh_idx2 > sh_idx1 && sh_idx2 < hist_size)
   {
      double p1 = r[sh_idx2].high, p2 = r[sh_idx1].high;
      double d1 = normalizedA[sh_idx2],  d2 = normalizedA[sh_idx1];
      if(p2 > p1 && d2 < d1)
         div_bear = Clip01(((p2 - p1) / atr + (d1 - d2)) / 2.0);
   }
   if(sl_idx1 > 0 && sl_idx2 > sl_idx1 && sl_idx2 < hist_size)
   {
      double p1 = r[sl_idx2].low, p2 = r[sl_idx1].low;
      double d1 = normalizedA[sl_idx2], d2 = normalizedA[sl_idx1];
      if(p2 < p1 && d2 > d1)
         div_bull = Clip01(((p1 - p2) / atr + (d2 - d1)) / 2.0);
   }
   fs.divergence_bull=cfg.tick_pressure_enabled ? div_bull : 0.0;
   fs.divergence_bear=cfg.tick_pressure_enabled ? div_bear : 0.0;
   fs.delta_divergence = cfg.tick_pressure_enabled ? MathMax(div_bear, div_bull) : 0.0;

   //--- GAP-02: ATR-Normalized Confirmed BOS Displacement
   double disp_val = 0.0;
   if(st.bull_bos && st.last_swing_high > 0.0 && r[0].close > st.last_swing_high)
      disp_val = Clip01(((r[0].close - st.last_swing_high) / atr) / 1.5);
   else if(st.bear_bos && st.last_swing_low > 0.0 && r[0].close < st.last_swing_low)
      disp_val = Clip01(((st.last_swing_low - r[0].close) / atr) / 1.5);
   fs.displacement = disp_val;

   // Reject any non-finite derived feature before exporting evidence or
   // committing caller-owned feature state. Clip helpers do not sanitize NaN.
   if(!FeatureSnapshotNumericsValid(fs)) return false;
   if(ArrayResize(feature_evidence,got)!=got || !ArraySetAsSeries(feature_evidence,true)) return false;
   for(int e=0;e<got;e++) feature_evidence[e]=r[e];
   state.structure_direction = s_prev_dir;
   state.pressure_state = next_pressure_state;
   return true;
}
//+------------------------------------------------------------------+


// Compatibility entry point for non-AMIGO consumers. The canonical AMIGO path
// passes a staged state copy and commits it only after the opportunity validates.
bool BuildFeatureVector(const string symbol, const AmigoConfig &cfg,
                        FeatureSnapshot &fs)
{
   static AMIGOFeatureState legacy_state = {0, 0};
   MqlRates ignored_evidence[];
   return BuildFeatureVector(symbol, cfg, fs, legacy_state, ignored_evidence);
}

bool BuildFeatureVector(const string symbol, const AmigoConfig &cfg,
                        FeatureSnapshot &fs, AMIGOFeatureState &state)
{
   MqlRates ignored_evidence[];
   return BuildFeatureVector(symbol,cfg,fs,state,ignored_evidence);
}
