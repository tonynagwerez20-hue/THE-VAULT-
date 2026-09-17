#property strict

//--- Session VWAP using HLC3 x tick volume (Math Spec §5.1)
double ComputeSessionVWAP(const string symbol, ENUM_TIMEFRAMES tf,
                          datetime session_start)
{
   MqlRates r[];
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