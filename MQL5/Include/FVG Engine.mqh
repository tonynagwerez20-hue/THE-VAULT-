#property strict

//--- 3-bar FVG (Math Spec §10). Lifecycle is evaluated bar-by-bar.

struct FVGEvent
{
   datetime created_ts;
   bool     is_bull;
   double   upper;
   double   lower;
   bool     active;
   bool     mitigated;
   bool     invalidated;
   double   fill_pct;     // current, point-in-time
};

//--- Detect FVG at closed-bar index i (i>=2), using r[i-2..i]
bool DetectFVG(const MqlRates &r[], int i, double atr, bool &is_bull,
               double &upper, double &lower)
{
   double gap_bull = r[i].low  - r[i-2].high;
   double gap_bear = r[i-2].low - r[i].high;
   double min_width = 0.10 * atr;

   if(gap_bull > min_width)
   {
      is_bull = true;
      upper = r[i].low;
      lower = r[i-2].high;
      return true;
   }
   if(gap_bear > min_width)
   {
      is_bull = false;
      upper = r[i-2].low;
      lower = r[i].high;
      return true;
   }
   return false;
}

//--- Evaluate a single FVG's fill state as of bar index j (j < i_creation in time)
//--- j is more recent than creation index. Point-in-time only.
void UpdateFVGState(FVGEvent &fvg, const MqlRates &r[], int j)
{
   if(!fvg.active) return;
   double width = fvg.upper - fvg.lower;
   if(width <= 0.0) { fvg.active = false; return; }

   double fill = 0.0;
   if(fvg.is_bull)
   {
      // Bull FVG: gap between lower (r[i-2].high) and upper (r[i].low)
      // Fill measured by how far price has retraced downward into the gap.
      double low_j = r[j].low;
      fill = (fvg.upper - low_j) / width;
   }
   else
   {
      double high_j = r[j].high;
      fill = (high_j - fvg.lower) / width;
   }
   if(fill < 0.0) fill = 0.0;
   if(fill > 1.0) fill = 1.0;
   fvg.fill_pct = fill;

   if(fill >= 0.50) fvg.mitigated = true;

   if(fvg.is_bull && r[j].close < fvg.lower) fvg.invalidated = true;
   if(!fvg.is_bull && r[j].close > fvg.upper) fvg.invalidated = true;
   if(fvg.invalidated) fvg.active = false;
}