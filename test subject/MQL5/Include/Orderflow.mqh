#ifndef AMIGO_INCLUDE_ORDERFLOW_MQH
#define AMIGO_INCLUDE_ORDERFLOW_MQH
#property strict
#include <FrozenFootprint.mqh>
#define AM_MAX_PROXY_TICKS 8192

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

// Canonical fail-closed tick-window reader. The upper boundary is exclusive,
// the tick buffer is bounded, and an incomplete/invalid tick window is not
// converted into a valid zero-pressure observation.
bool TryComputeDeltaA(const string symbol, datetime bar_open, datetime bar_end_exclusive,
                      double &out, int &tick_count, FrozenFootprint &footprint,
                      const double bin_width,const long chart_mode=SYMBOL_CHART_MODE_LAST)
{
   out=0.0;
   tick_count=0;
   FrozenFootprintReset(footprint,bin_width);
   if(bar_open<=0 || bar_end_exclusive<=bar_open || bar_end_exclusive>9223372036854775)
      return false;

   if(chart_mode!=SYMBOL_CHART_MODE_BID && chart_mode!=SYMBOL_CHART_MODE_LAST) return false;
   bool bid_basis=(chart_mode==SYMBOL_CHART_MODE_BID);
   uint activity_flag=bid_basis ? TICK_FLAG_BID : TICK_FLAG_LAST;
   // MT5_TICK_PROXY: directional chart-price changes, not aggressor volume.
   long from_ms=(long)bar_open*1000;
   long end_ms=(long)bar_end_exclusive*1000;
   static MqlTick ticks[AM_MAX_PROXY_TICKS];
   ResetLastError();
   int got=CopyTicksRange(symbol,ticks,COPY_TICKS_ALL,(ulong)from_ms,(ulong)(end_ms-1));
   int read_error=GetLastError();
   if(read_error!=0 || got<2 || got>=AM_MAX_PROXY_TICKS) return false;

   double previous=bid_basis ? ticks[0].bid : ticks[0].last;
   if(!MathIsValidNumber(previous) || previous<=0.0 ||
      ticks[0].time_msc<from_ms || ticks[0].time_msc>=end_ms) return false;
   if(!FrozenFootprintAdd(footprint,previous)) return false;
   bool observed_price_activity=(ticks[0].flags & activity_flag)!=0;
   double sum=0.0;
   for(int i=1;i<got;i++)
   {
      double price=bid_basis ? ticks[i].bid : ticks[i].last;
      if(!MathIsValidNumber(price) || price<=0.0 ||
         ticks[i].time_msc<from_ms || ticks[i].time_msc>=end_ms ||
         ticks[i].time_msc<ticks[i-1].time_msc) return false;
      if(!FrozenFootprintAdd(footprint,price)) return false;
      if(price>previous) sum+=1.0;
      else if(price<previous) sum-=1.0;
      if((ticks[i].flags & activity_flag)!=0) observed_price_activity=true;
      previous=price;
   }
   if(!observed_price_activity || !MathIsValidNumber(sum)) return false;
   if(!FrozenFootprintFinish(footprint)) return false;
   out=sum;
   tick_count=got-1;
   return true;
}

// Compatibility caller: no footprint consumer, same validated reader.
bool TryComputeDeltaA(const string symbol,datetime start,datetime end,
                      double &out,int &count,const long mode=SYMBOL_CHART_MODE_LAST)
{
   double width=SymbolInfoDouble(symbol,SYMBOL_TRADE_TICK_SIZE);
   FrozenFootprint unused;
   return TryComputeDeltaA(symbol,start,end,out,count,unused,width,mode);
}

//--- Proxy B: CLV * tick volume (Math Spec §12)
double ComputeDeltaB(const MqlRates &r[], int shift)
{
   double h = r[shift].high, l = r[shift].low, c = r[shift].close;
   double range = h - l;
   double clv = (range > 0.0) ? ((2.0*c - h - l) / range) : 0.0;
   return clv * (double)r[shift].tick_volume;
}

// Percent rank against prior observations only. Ties receive midrank.
bool ProxyPriorPercentile(const double current,const double &prior[],double &rank)
{
   rank=0.0;
   int n=ArraySize(prior);
   if(n<20 || !MathIsValidNumber(current) || current<0.0) return false;
   double below=0.0,equal=0.0;
   for(int i=0;i<n;i++)
   {
      if(!MathIsValidNumber(prior[i]) || prior[i]<0.0) return false;
      if(prior[i]<current) below+=1.0;
      else if(prior[i]==current) equal+=1.0;
   }
   rank=100.0*(below+0.5*equal)/(double)n;
   return true;
}

// Consecutive directional quote-pressure observations, newest first.
// Neutral/opposing observations end the run; no skipped-bar stitching.
int ProxyDirectionalPersistence(const double &normalized[],const int direction)
{
   if(direction!=1 && direction!=-1) return 0;
   int count=0;
   for(int i=0;i<ArraySize(normalized);i++)
   {
      if(!MathIsValidNumber(normalized[i]) || MathAbs(normalized[i])>1.0) return 0;
      if((double)direction*normalized[i]<=0.0) break;
      count++;
   }
   return count;
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

#endif // AMIGO_INCLUDE_ORDERFLOW_MQH
