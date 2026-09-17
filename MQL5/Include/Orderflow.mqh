#property strict

//--- Proxy A: signed tick-price changes (Math Spec §11)
double ComputeDeltaA(const string symbol, datetime bar_open, datetime bar_close, int &tick_count)
{
   MqlTick ticks[];
   int got = CopyTicksRange(symbol, ticks, COPY_TICKS_ALL,
                            (ulong)bar_open*1000, (ulong)bar_close*1000);
   tick_count = 0;
   if(got < 2) return 0.0;
   double sum = 0.0;
   double prev = ticks[0].last;
   for(int i=1; i<got; i++)
   {
      double p = ticks[i].last;
      if(p <= 0.0) continue;
      if(p > prev) sum += 1.0;
      else if(p < prev) sum -= 1.0;
      prev = p;
      tick_count++;
   }
   return sum;
}

//--- Proxy B: CLV * tick volume (Math Spec §12)
double ComputeDeltaB(const MqlRates &r[], int shift)
{
   double h = r[shift].high, l = r[shift].low, c = r[shift].close;
   double range = h - l;
   double clv = (range > 0.0) ? ((2.0*c - h - l) / range) : 0.0;
   return clv * (double)r[shift].tick_volume;
}

//--- Rolling z-score over closed bars
double ZScore(const double &series[], int window)
{
   int n = ArraySize(series);
   if(n < window || window <= 1) return 0.0;
   double sum = 0.0;
   for(int i=0; i<window; i++) sum += series[i];
   double mean = sum / window;
   double var = 0.0;
   for(int i=0; i<window; i++) var += (series[i]-mean)*(series[i]-mean);
   var /= (window-1);
   double sd = MathSqrt(var);
   if(sd <= 0.0) return 0.0;
   return (series[0] - mean) / sd;
}

double Clip3(double z)
{
   if(z >  3.0) return  3.0;
   if(z < -3.0) return -3.0;
   return z;
}

//--- Fusion (Math Spec §13): 0.50*ZA + 0.50*ZB where Z are clipped/3
double ComputeFusion(double deltaA, double deltaB,
                     const double &histA[], const double &histB[])
{
   double zA = Clip3(ZScore(histA, 20)) / 3.0;
   double zB = Clip3(ZScore(histB, 20)) / 3.0;
   return 0.50*zA + 0.50*zB;
}