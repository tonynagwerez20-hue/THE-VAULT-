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