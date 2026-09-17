#property strict

//--- Completed-bar only ATR (Math Spec §3.2)
//--- Uses immutable closed bars; forming bar excluded.

double ComputeATR14(const string symbol, ENUM_TIMEFRAMES tf, int period=14)
{
   double tr[];
   ArrayResize(tr, period);
   int need = period + 1;
   MqlRates rates[];
   int got = CopyRates(symbol, tf, 1, need, rates); // skip current forming bar
   if(got < need) return 0.0;

   for(int i=0; i<period; i++)
   {
      double h = rates[i].high;
      double l = rates[i].low;
      double pc= rates[i+1].close;
      double a = h - l;
      double b = MathAbs(h - pc);
      double c = MathAbs(l - pc);
      tr[i] = MathMax(a, MathMax(b, c));
   }
   double sum = 0;
   for(int i=0; i<period; i++) sum += tr[i];
   return sum / period;
}

//--- Robust volatility: sigma20 and range ratio (Math Spec §3.3)
double ComputeSigma20(const string symbol, ENUM_TIMEFRAMES tf)
{
   MqlRates r[];
   int got = CopyRates(symbol, tf, 1, 21, r);
   if(got < 21) return 0.0;
   double rets[20];
   for(int i=0; i<20; i++)
   {
      double c0 = r[i].close;
      double c1 = r[i+1].close;
      rets[i] = (c1 != 0.0) ? (c0 / c1 - 1.0) : 0.0;
   }
   double mean = 0;
   for(int i=0; i<20; i++) mean += rets[i];
   mean /= 20.0;
   double var = 0;
   for(int i=0; i<20; i++) var += (rets[i]-mean)*(rets[i]-mean);
   var /= 19.0;
   return MathSqrt(var);
}

double ComputeRangeRatio(const string symbol, ENUM_TIMEFRAMES tf)
{
   MqlRates r[];
   int got = CopyRates(symbol, tf, 1, 21, r);
   if(got < 21) return 1.0;
   double cur = r[0].high - r[0].low;
   double ranges[20];
   for(int i=0; i<20; i++) ranges[i] = r[i+1].high - r[i+1].low;
   ArraySort(ranges);
   double med = ranges[10];
   if(med <= 0.0) return 1.0;
   return cur / med;
}