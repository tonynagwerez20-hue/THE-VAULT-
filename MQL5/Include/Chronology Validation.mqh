//+------------------------------------------------------------------+
//| Chronology Validation.mqh - pure closed-bar input contract       |
//| No terminal reads, order APIs, or mutable global state.           |
//+------------------------------------------------------------------+
#property strict

#ifndef AMIGO_CHRONOLOGY_VALIDATION_MQH
#define AMIGO_CHRONOLOGY_VALIDATION_MQH

bool ValidateClosedRateSequence(const MqlRates &bars[], const int count,
                                const datetime decision_boundary,
                                const datetime expected_latest_closed,
                                const int minimum_count, const int maximum_count,
                                const int nominal_period_seconds,
                                const bool require_contiguous)
{
   if(minimum_count<=0 || maximum_count<minimum_count || count<=0 ||
      count<minimum_count || count>maximum_count || count!=ArraySize(bars) ||
      !ArrayGetAsSeries(bars) || decision_boundary<=0 ||
      expected_latest_closed<=0 || expected_latest_closed>=decision_boundary ||
      nominal_period_seconds<=0)
      return false;

   // Series indexing contract: [0] is the newest closed bar. Its timestamp
   // must agree with the caller's independently acquired closed-bar identity.
   if(bars[0].time!=expected_latest_closed)
      return false;

   for(int i=0;i<count;i++)
   {
      if(bars[i].time<=0 || bars[i].time>=decision_boundary ||
         (i>0 && bars[i].time>=bars[i-1].time) ||
         !MathIsValidNumber(bars[i].open) || !MathIsValidNumber(bars[i].high) ||
         !MathIsValidNumber(bars[i].low) || !MathIsValidNumber(bars[i].close) ||
         bars[i].open<=0.0 || bars[i].low<=0.0 || bars[i].high<bars[i].low ||
         bars[i].open<bars[i].low || bars[i].open>bars[i].high ||
         bars[i].close<bars[i].low || bars[i].close>bars[i].high ||
         bars[i].tick_volume<0 || bars[i].real_volume<0 || bars[i].spread<0)
         return false;

      // Only callers with a proven continuous-session contract may request
      // exact interval spacing. This helper does not infer market calendars.
      if(require_contiguous && i>0 &&
         bars[i-1].time-bars[i].time!=nominal_period_seconds)
         return false;
   }
   return true;
}

#endif // AMIGO_CHRONOLOGY_VALIDATION_MQH
