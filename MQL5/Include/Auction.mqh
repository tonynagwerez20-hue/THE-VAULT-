#ifndef AMIGO_INCLUDE_AUCTION_MQH
#define AMIGO_INCLUDE_AUCTION_MQH
#property strict

//--- Session VWAP using HLC3 x tick volume (Math Spec §5.1)
double ComputeSessionVWAP(const string symbol, ENUM_TIMEFRAMES tf,
                          datetime session_start)
{
   MqlRates r[];
   if(!ArraySetAsSeries(r, true)) return 0.0;
   int got = CopyRates(symbol, tf, session_start, TimeCurrent(), r);
   if(got <= 0) return 0.0;
   double num = 0.0, den = 0.0;
   for(int i=0; i<got; i++)
   {
      double tp = (r[i].high + r[i].low + r[i].close) / 3.0;
      double v  = (double)r[i].tick_volume;
      num += tp * v;
      den += v;
   }
   if(den <= 0.0) return 0.0;
   return num / den;
}

//--- Simple value profile: allocate each bar's volume to TP bin
//--- bin_width = 4 * Point for XAUUSD (Math Spec §5.3)
void ComputeValueArea(const string symbol, ENUM_TIMEFRAMES tf,
                      datetime session_start, double bin_width,
                      double &poc, double &vah, double &val)
{
   poc = 0.0; vah = 0.0; val = 0.0;
   MqlRates r[];
   if(!ArraySetAsSeries(r, true)) return;
   int got = CopyRates(symbol, tf, session_start, TimeCurrent(), r);
   if(got < 5 || bin_width <= 0.0) return;

   double pmin = r[0].low, pmax = r[0].high;
   for(int i=0; i<got; i++)
   {
      if(r[i].low  < pmin) pmin = r[i].low;
      if(r[i].high > pmax) pmax = r[i].high;
   }
   int nbins = (int)MathFloor((pmax - pmin) / bin_width) + 1;
   if(nbins <= 0 || nbins > 100000) return;

   double vols[];
   ArrayResize(vols, nbins);
   ArrayInitialize(vols, 0.0);

   for(int i=0; i<got; i++)
   {
      double tp = (r[i].high + r[i].low + r[i].close) / 3.0;
      int b = (int)MathFloor((tp - pmin) / bin_width);
      if(b < 0) b = 0;
      if(b >= nbins) b = nbins-1;
      vols[b] += (double)r[i].tick_volume;
   }
   double total = 0.0;
   int poc_bin = 0;
   double poc_vol = 0.0;
   for(int b=0; b<nbins; b++)
   {
      total += vols[b];
      if(vols[b] > poc_vol) { poc_vol = vols[b]; poc_bin = b; }
   }
   if(total <= 0.0) return;

   poc = pmin + (poc_bin + 0.5) * bin_width;

   // Expand from POC until 70% included
   double target = 0.70 * total;
   double included = vols[poc_bin];
   int lo = poc_bin, hi = poc_bin;
   while(included < target && (lo > 0 || hi < nbins-1))
   {
      double vlo = (lo > 0) ? vols[lo-1] : -1.0;
      double vhi = (hi < nbins-1) ? vols[hi+1] : -1.0;
      if(vhi > vlo) { hi++; included += vhi; }
      else if(vlo >= 0.0) { lo--; included += vlo; }
      else break;
   }
   val = pmin + lo * bin_width;
   vah = pmin + (hi+1) * bin_width;
}

// Candidate-only profile calculation from one caller-acquired closed-bar
// snapshot. The caller remains responsible for coverage/provenance checks.
bool ComputeClosedSessionValue(const MqlRates &r[], int total, double bin_width,
                               double &vwap, double &poc, double &vah, double &val)
{
   if(total<5 || total!=ArraySize(r) || !ArrayGetAsSeries(r) ||
      !MathIsValidNumber(bin_width) || bin_width<=0.0) return false;
   double pmin=r[0].low, pmax=r[0].high, numerator=0.0, denominator=0.0;
   for(int i=0;i<total;i++)
   {
      if(!MathIsValidNumber(r[i].high) || !MathIsValidNumber(r[i].low) ||
         !MathIsValidNumber(r[i].close) || r[i].low<=0.0 ||
         r[i].high<r[i].low || r[i].close<r[i].low || r[i].close>r[i].high ||
         r[i].tick_volume<0 || r[i].tick_volume>9007199254740991) return false;
      if(r[i].low<pmin) pmin=r[i].low;
      if(r[i].high>pmax) pmax=r[i].high;
      double tp=(r[i].high+r[i].low+r[i].close)/3.0;
      double volume=(double)r[i].tick_volume;
      numerator+=tp*volume;
      denominator+=volume;
      if(!MathIsValidNumber(tp) || !MathIsValidNumber(numerator) ||
         !MathIsValidNumber(denominator)) return false;
   }
   if(denominator<=0.0) return false;
   double bins_count=MathFloor((pmax-pmin)/bin_width)+1.0;
   if(!MathIsValidNumber(bins_count) || bins_count<1.0 || bins_count>100000.0) return false;
   int nbins=(int)bins_count;
   double vols[];
   if(ArrayResize(vols,nbins)!=nbins || ArrayInitialize(vols,0.0)!=nbins) return false;
   for(int i=0;i<total;i++)
   {
      double tp=(r[i].high+r[i].low+r[i].close)/3.0;
      int b=(int)MathFloor((tp-pmin)/bin_width);
      if(b<0) b=0;
      if(b>=nbins) b=nbins-1;
      vols[b]+=(double)r[i].tick_volume;
      if(!MathIsValidNumber(vols[b])) return false;
   }
   double summed=0.0, peak=0.0;
   int peak_bin=0;
   for(int b=0;b<nbins;b++)
   {
      summed+=vols[b];
      if(vols[b]>peak) { peak=vols[b]; peak_bin=b; }
   }
   if(!MathIsValidNumber(summed) || summed<=0.0) return false;
   double target=0.70*summed, included=vols[peak_bin];
   int lo=peak_bin, hi=peak_bin;
   while(included<target && (lo>0 || hi<nbins-1))
   {
      double vlo=(lo>0) ? vols[lo-1] : -1.0;
      double vhi=(hi<nbins-1) ? vols[hi+1] : -1.0;
      if(vhi>vlo) { hi++; included+=vhi; }
      else if(vlo>=0.0) { lo--; included+=vlo; }
      else break;
   }
   double next_vwap=numerator/denominator;
   double next_poc=pmin+(peak_bin+0.5)*bin_width;
   double next_val=pmin+lo*bin_width;
   double next_vah=pmin+(hi+1)*bin_width;
   if(!MathIsValidNumber(included) || !MathIsValidNumber(next_vwap) ||
      !MathIsValidNumber(next_poc) || !MathIsValidNumber(next_val) ||
      !MathIsValidNumber(next_vah)) return false;
   vwap=next_vwap; poc=next_poc; vah=next_vah; val=next_val;
   return true;
}

// BROKER_TICK_VOLUME acceptance proxy. Reference value excludes BOTH
// confirmation bars, so their own activity cannot move the threshold.
bool ClosedValueAcceptance(const MqlRates &session_rates[],const int count,
                           const double bin_width,bool &above,bool &below)
{
   above=false; below=false;
   if(count<7 || count!=ArraySize(session_rates) || !ArrayGetAsSeries(session_rates)) return false;
   for(int i=0;i<count;i++)
      if(session_rates[i].time<=0 || (i>0 && session_rates[i-1].time<=session_rates[i].time)) return false;
   MqlRates prior[];
   if(ArrayResize(prior,count-2)!=count-2 || !ArraySetAsSeries(prior,true)) return false;
   for(int i=2;i<count;i++) prior[i-2]=session_rates[i];
   double vwap=0.0,poc=0.0,vah=0.0,val=0.0;
   if(!ComputeClosedSessionValue(prior,count-2,bin_width,vwap,poc,vah,val) || vah<=val) return false;
   for(int i=0;i<2;i++)
      if(!MathIsValidNumber(session_rates[i].close) || session_rates[i].close<=0.0) return false;
   above=session_rates[0].close>vah && session_rates[1].close>vah;
   below=session_rates[0].close<val && session_rates[1].close<val;
   return true;
}

#endif // AMIGO_INCLUDE_AUCTION_MQH
