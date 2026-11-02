#property strict

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
   if(shift < k) return false;
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
   if(shift < k) return false;
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

//+------------------------------------------------------------------+
//| Section 6: Top-Down Market Analysis Multi-Timeframe Structure    |
//| D1/H4 (Swing/Macro Regime), H1/M30 (Intraday Structure),         |
//| M15/M5 (Context), M1 (Scalp Precision Execution)                |
//+------------------------------------------------------------------+
struct TopDownContext
{
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

TopDownContext EvaluateTopDownContext(const string symbol, double m5_atr)
{
   TopDownContext td;
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
   StructureState d1_state = EvaluateStructure(symbol, PERIOD_D1, m5_atr * 8.0, 0);
   td.d1_dir = d1_state.dir;

   // 2. Evaluate H4 broader structural direction (Swing Horizon)
   StructureState h4_state = EvaluateStructure(symbol, PERIOD_H4, m5_atr * 4.0, 0);
   td.h4_dir = h4_state.dir;

   // 3. Evaluate H1 intermediate structural direction
   StructureState h1_state = EvaluateStructure(symbol, PERIOD_H1, m5_atr * 2.0, 0);
   td.h1_dir = h1_state.dir;

   // 4. Evaluate M30 intermediate structural direction (Intraday Swing Horizon)
   StructureState m30_state = EvaluateStructure(symbol, PERIOD_M30, m5_atr * 1.8, 0);
   td.m30_dir = m30_state.dir;

   // 5. Evaluate M15 local structural direction
   StructureState m15_state = EvaluateStructure(symbol, PERIOD_M15, m5_atr * 1.5, 0);
   td.m15_dir = m15_state.dir;

   // 6. Evaluate M5 local execution direction
   StructureState m5_state = EvaluateStructure(symbol, PERIOD_M5, m5_atr * 1.0, 0);
   td.m5_dir = m5_state.dir;

   // 7. Evaluate M1 micro-precision direction (Scalping Horizon)
   StructureState m1_state = EvaluateStructure(symbol, PERIOD_M1, m5_atr * 0.5, 0);
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

   return td;
}