#ifndef AMIGO_INCLUDE_STRUCTURE_ENGINE_MQH
#define AMIGO_INCLUDE_STRUCTURE_ENGINE_MQH
#property strict

#include <Chronology Validation.mqh>

//--- Confirmed 2-left/2-right fractal swing (Math Spec §6.1)
//--- Only confirmed once t+2 closed. We only ever query CLOSED bars,
//--- so scanning index >= 2 from current-1 is causal.

struct SwingPoint
{
   datetime time;
   double   price;
   bool     is_high;
   datetime confirm_ts;  // = time of bar t+2 close
};

//--- Returns true if bar at shift (>=2) is a confirmed swing high
bool IsConfirmedSwingHigh(const MqlRates &r[], int shift, int k=2)
{
   int size=ArraySize(r);
   // Check both neighbor bounds before dereferencing the candidate bar.
   if(k<=0 || k>=size || shift<k || shift>=size-k) return false;
   double h = r[shift].high;
   for(int i=1; i<=k; i++)
   {
      if(h <= r[shift-i].high) return false;
      if(h <  r[shift+i].high) return false;
   }
   return true;
}

bool IsConfirmedSwingLow(const MqlRates &r[], int shift, int k=2)
{
   int size=ArraySize(r);
   // Check both neighbor bounds before dereferencing the candidate bar.
   if(k<=0 || k>=size || shift<k || shift>=size-k) return false;
   double l = r[shift].low;
   for(int i=1; i<=k; i++)
   {
      if(l >= r[shift-i].low) return false;
      if(l >  r[shift+i].low) return false;
   }
   return true;
}

//--- Latest confirmed swing high/low strictly BEFORE decision timestamp
bool FindLatestConfirmedSwing(const MqlRates &r[], int total, bool want_high,
                              double &price_out, datetime &time_out, int k=2)
{
   price_out=0.0;
   time_out=0;
   if(total<=0 || total>ArraySize(r) || k<=0 || k>(total-1)/2 ||
      !ArrayGetAsSeries(r)) return false;
   // r[0] is most recent CLOSED bar; r[i] older.
   // A bar at index i is confirmed only when i >= k is valid AND
   // bars i-1..i-k exist. We scan from newest to oldest.
   for(int i = k; i < total - k; i++)
   {
      if(want_high && IsConfirmedSwingHigh(r, i, k))
      {
         price_out = r[i].high;
         time_out  = r[i].time;
         return true;
      }
      if(!want_high && IsConfirmedSwingLow(r, i, k))
      {
         price_out = r[i].low;
         time_out  = r[i].time;
         return true;
      }
   }
   return false;
}

//--- BOS/CHOCH/Sweep (Math Spec §7)
struct StructureState
{
   int      dir;              // -1/0/+1
   bool     bull_bos;
   bool     bear_bos;
   bool     bull_choch;
   bool     bear_choch;
   double   last_swing_high;
   double   last_swing_low;
   bool     bull_sweep;
   bool     bear_sweep;
   bool     sweep_reject;
   int      last_sweep_dir;   // +1=bull sweep (liquidity grab low), -1=bear sweep (liquidity grab high)
};

StructureState EvaluateStructure(const string symbol, ENUM_TIMEFRAMES tf,
                                 double atr, int prev_dir)
{
   StructureState s;
   s.dir = prev_dir;
   s.bull_bos = false; s.bear_bos = false;
   s.bull_choch = false; s.bear_choch = false;
   s.last_swing_high = 0.0; s.last_swing_low = 0.0;
   s.bull_sweep = false; s.bear_sweep = false;
   s.sweep_reject = false; s.last_sweep_dir = 0;

   MqlRates r[];
   if(!ArraySetAsSeries(r, true)) return s;
   int got = CopyRates(symbol, tf, 1, 200, r);
   if(got < 50) return s;

   double sh, sl;
   datetime ts;
   if(FindLatestConfirmedSwing(r, got, true, sh, ts)) s.last_swing_high = sh;
   if(FindLatestConfirmedSwing(r, got, false, sl, ts)) s.last_swing_low = sl;

   // BOS uses last CLOSED bar's close vs confirmed swing level + 0.05*ATR
   double close_t = r[0].close;
   double high_t  = r[0].high;
   double low_t   = r[0].low;

   if(s.last_swing_high > 0.0 && close_t > s.last_swing_high + 0.05*atr)
      s.bull_bos = true;
   if(s.last_swing_low > 0.0 && close_t < s.last_swing_low - 0.05*atr)
      s.bear_bos = true;

   // Liquidity Sweep Rejection: wick breaches swing level, but close rejects back inside
   if(s.last_swing_low > 0.0 && low_t < s.last_swing_low && close_t >= s.last_swing_low)
   {
      s.bull_sweep = true;
   }
   if(s.last_swing_high > 0.0 && high_t > s.last_swing_high && close_t <= s.last_swing_high)
   {
      s.bear_sweep = true;
   }

   s.sweep_reject = (s.bull_sweep || s.bear_sweep);
   s.last_sweep_dir = s.bull_sweep ? +1 : (s.bear_sweep ? -1 : 0);

   int new_dir = prev_dir;
   if(s.bull_bos) new_dir = +1;
   if(s.bear_bos) new_dir = -1;

   if(new_dir != prev_dir && prev_dir != 0)
   {
      if(new_dir == +1) s.bull_choch = true;
      if(new_dir == -1) s.bear_choch = true;
   }
   s.dir = new_dir;
   return s;
}

// Candidate-only execution-timeframe evaluation from the already validated
// closed-bar snapshot, avoiding a second independently timed history read.
bool EvaluateStructureFromClosedRates(const MqlRates &r[], int total,
                                      double atr, int prev_dir, StructureState &out)
{
   if(total<50 || total>200 || total>ArraySize(r) || !ArrayGetAsSeries(r) ||
      !MathIsValidNumber(atr) || atr<=0.0) return false;
   StructureState s;
   s.dir=prev_dir;
   s.bull_bos=false; s.bear_bos=false;
   s.bull_choch=false; s.bear_choch=false;
   s.last_swing_high=0.0; s.last_swing_low=0.0;
   s.bull_sweep=false; s.bear_sweep=false;
   s.sweep_reject=false; s.last_sweep_dir=0;
   double sh, sl;
   datetime ts;
   if(FindLatestConfirmedSwing(r,total,true,sh,ts)) s.last_swing_high=sh;
   if(FindLatestConfirmedSwing(r,total,false,sl,ts)) s.last_swing_low=sl;
   double close_t=r[0].close, high_t=r[0].high, low_t=r[0].low;
   if(s.last_swing_high>0.0 && close_t>s.last_swing_high+0.05*atr) s.bull_bos=true;
   if(s.last_swing_low>0.0 && close_t<s.last_swing_low-0.05*atr) s.bear_bos=true;
   if(s.last_swing_low>0.0 && low_t<s.last_swing_low && close_t>=s.last_swing_low) s.bull_sweep=true;
   if(s.last_swing_high>0.0 && high_t>s.last_swing_high && close_t<=s.last_swing_high) s.bear_sweep=true;
   s.sweep_reject=(s.bull_sweep || s.bear_sweep);
   s.last_sweep_dir=s.bull_sweep ? +1 : (s.bear_sweep ? -1 : 0);
   int new_dir=prev_dir;
   if(s.bull_bos) new_dir=+1;
   if(s.bear_bos) new_dir=-1;
   if(new_dir!=prev_dir && prev_dir!=0)
   {
      if(new_dir==+1) s.bull_choch=true;
      if(new_dir==-1) s.bear_choch=true;
   }
   s.dir=new_dir;
   out=s;
   return true;
}

// Candidate-only timestamp-bounded reader for top-down context. A successful
// result is based on closed bars no later than the execution opportunity.
bool TryEvaluateClosedStructure(const string symbol, ENUM_TIMEFRAMES tf,
                                const int atr_period, const datetime asof_boundary,
                                StructureState &out)
{
   if(asof_boundary<=0 || atr_period<=0 || atr_period>=200) return false;
   int seconds=PeriodSeconds(tf);
   if(seconds<=0) return false;
   datetime current_bar=iTime(symbol,tf,0);
   datetime latest_closed=iTime(symbol,tf,1);
   if(current_bar<=0 || latest_closed<=0 || latest_closed>=current_bar ||
      current_bar>asof_boundary || asof_boundary-current_bar>=seconds) return false;
   MqlRates rates[];
   if(!ArraySetAsSeries(rates,true)) return false;
   int got=CopyRates(symbol,tf,1,200,rates);
   if(!ValidateClosedRateSequence(rates,got,asof_boundary,latest_closed,50,200,
                                  seconds,false)) return false;
   for(int i=0;i<got;i++)
      if(rates[i].time>=current_bar) return false;
   if(iTime(symbol,tf,0)!=current_bar || iTime(symbol,tf,1)!=latest_closed) return false;
   // Same arithmetic true-range mean used by ComputeATR14, but taken from
   // this timeframe's validated snapshot instead of a separate history read.
   if(got<=atr_period) return false;
   double atr=0.0;
   for(int i=0;i<atr_period;i++)
   {
      double tr=MathMax(rates[i].high-rates[i].low,
                       MathMax(MathAbs(rates[i].high-rates[i+1].close),
                               MathAbs(rates[i].low-rates[i+1].close)));
      if(!MathIsValidNumber(tr) || tr<0.0) return false;
      atr+=tr/(double)atr_period;
   }
   if(!MathIsValidNumber(atr) || atr<=0.0) return false;
   return EvaluateStructureFromClosedRates(rates,got,atr,0,out);
}

//+------------------------------------------------------------------+
//| Section 6: Top-Down Market Analysis Multi-Timeframe Structure    |
//| D1/H4 (Swing/Macro Regime), H1/M30 (Intraday Structure),         |
//| M15/M5 (Context), M1 (Scalp Precision Execution)                |
//+------------------------------------------------------------------+
struct TopDownContext
{
   bool   complete; // True only after all seven closed-history reads succeed.
   datetime asof_boundary;
   int    d1_dir;           // +1 bull, -1 bear, 0 neutral (Macro Swing context)
   int    h4_dir;           // +1 bull, -1 bear, 0 neutral (Swing Horizon)
   int    h1_dir;           // +1 bull, -1 bear, 0 neutral (HTF Intermediate)
   int    m30_dir;          // +1 bull, -1 bear, 0 neutral (Intraday Swing Horizon)
   int    m15_dir;          // +1 bull, -1 bear, 0 neutral (Context Structure)
   int    m5_dir;           // +1 bull, -1 bear, 0 neutral (Execution Structure)
   int    m1_dir;           // +1 bull, -1 bear, 0 neutral (Scalp Precision Horizon)
   bool   aligned;          // True when HTF and LTF have non-conflicting alignment
   bool   conflict;         // True when HTF directional context directly contradicts LTF
   double alignment_score;  // Multi-timeframe synthesis weight in [0.0, 1.0]
   string summary;          // Diagnostic summary
};

bool EvaluateTopDownContext(const string symbol, const int atr_period,
                            const datetime asof_boundary, TopDownContext &td)
{
   td.complete=false;
   td.asof_boundary=asof_boundary;
   td.d1_dir  = 0;
   td.h4_dir  = 0;
   td.h1_dir  = 0;
   td.m30_dir = 0;
   td.m15_dir = 0;
   td.m5_dir  = 0;
   td.m1_dir  = 0;
   td.aligned = false;
   td.conflict = false;
   td.alignment_score = 0.50;
   td.summary = "UNINITIALIZED";

   // 1. Evaluate D1 macro regime (causal: closed bars only)
   StructureState d1_state;
   if(!TryEvaluateClosedStructure(symbol,PERIOD_D1,atr_period,asof_boundary,d1_state)) return false;
   td.d1_dir = d1_state.dir;

   // 2. Evaluate H4 broader structural direction (Swing Horizon)
   StructureState h4_state;
   if(!TryEvaluateClosedStructure(symbol,PERIOD_H4,atr_period,asof_boundary,h4_state)) return false;
   td.h4_dir = h4_state.dir;

   // 3. Evaluate H1 intermediate structural direction
   StructureState h1_state;
   if(!TryEvaluateClosedStructure(symbol,PERIOD_H1,atr_period,asof_boundary,h1_state)) return false;
   td.h1_dir = h1_state.dir;

   // 4. Evaluate M30 intermediate structural direction (Intraday Swing Horizon)
   StructureState m30_state;
   if(!TryEvaluateClosedStructure(symbol,PERIOD_M30,atr_period,asof_boundary,m30_state)) return false;
   td.m30_dir = m30_state.dir;

   // 5. Evaluate M15 local structural direction
   StructureState m15_state;
   if(!TryEvaluateClosedStructure(symbol,PERIOD_M15,atr_period,asof_boundary,m15_state)) return false;
   td.m15_dir = m15_state.dir;

   // 6. Evaluate M5 local execution direction
   StructureState m5_state;
   if(!TryEvaluateClosedStructure(symbol,PERIOD_M5,atr_period,asof_boundary,m5_state)) return false;
   td.m5_dir = m5_state.dir;

   // 7. Evaluate M1 micro-precision direction (Scalping Horizon)
   StructureState m1_state;
   if(!TryEvaluateClosedStructure(symbol,PERIOD_M1,atr_period,asof_boundary,m1_state)) return false;
   td.m1_dir = m1_state.dir;

   // 8. Synthesize alignment and conflicts
   int htf_bias = 0;
   if(td.h4_dir == td.h1_dir && td.h4_dir != 0)
      htf_bias = td.h4_dir;
   else if(td.h1_dir != 0)
      htf_bias = td.h1_dir;
   else
      htf_bias = td.h4_dir;

   // D1 Macro Context Integration (Workstream B):
   // D1 serves as macro authority constraint. If D1 strongly opposes the H4/H1 bias,
   // HTF bias is neutralized to avoid trend continuation against macro market structure.
   if(htf_bias != 0 && td.d1_dir != 0 && htf_bias != td.d1_dir)
   {
      htf_bias = 0; // Macro conflict neutralizes higher-timeframe continuation authority
   }

   int ltf_bias = 0;
   if(td.m15_dir != 0)
      ltf_bias = td.m15_dir;
   else if(td.m30_dir != 0)
      ltf_bias = td.m30_dir;
   else
      ltf_bias = td.m5_dir;

   if(htf_bias != 0 && ltf_bias != 0)
   {
      if(htf_bias == ltf_bias)
      {
         td.aligned = true;
         td.conflict = false;
         td.alignment_score = 0.85;
         td.summary = (htf_bias == 1) ? "BULLISH_HTF_ALIGNMENT" : "BEARISH_HTF_ALIGNMENT";
      }
      else
      {
         td.aligned = false;
         td.conflict = true;
         td.alignment_score = 0.25;
         td.summary = "HTF_LTF_CONFLICT";
      }
   }
   else
   {
      td.aligned = false;
      td.conflict = false;
      td.alignment_score = 0.50;
      td.summary = "BALANCED_OR_INSUFFICIENT_HTF_DATA";
   }

   td.complete=true;
   return true;
}

#endif // AMIGO_INCLUDE_STRUCTURE_ENGINE_MQH
