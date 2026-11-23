//+------------------------------------------------------------------+
//| Test_ChronologyContract.mq5 - pure synthetic no-order fixture     |
//+------------------------------------------------------------------+
#property script_show_inputs

#include <Chronology Validation.mqh>

int g_cases=0;
int g_failures=0;

void Expect(const string name,const bool actual,const bool expected)
{
   g_cases++;
   if(actual!=expected)
   {
      g_failures++;
      PrintFormat("[CHRONOLOGY_FAIL] %s expected=%s actual=%s",name,
                  expected ? "true" : "false",actual ? "true" : "false");
   }
   else PrintFormat("[CHRONOLOGY_PASS] %s value=%s",name,actual ? "true" : "false");
}

bool MakeSeries(MqlRates &bars[],const int count,const datetime boundary,
                const int seconds)
{
   if(count<=0 || seconds<=0 || ArrayResize(bars,count)!=count ||
      !ArraySetAsSeries(bars,true)) return false;
   for(int i=0;i<count;i++)
   {
      bars[i].time=boundary-(datetime)(i+1)*seconds;
      bars[i].open=100.0+i;
      bars[i].high=101.0+i;
      bars[i].low=99.0+i;
      bars[i].close=100.5+i;
      bars[i].tick_volume=1;
      bars[i].real_volume=0;
      bars[i].spread=1;
   }
   return true;
}

void OnStart()
{
   const datetime boundary=(datetime)1000000;
   const int interval=60;
   MqlRates bars[];
   if(!MakeSeries(bars,4,boundary,interval))
   {
      Print("[CHRONOLOGY_FINAL] FAIL fixture construction");
      return;
   }
   const datetime latest=bars[0].time;
   Expect("complete_closed_series",ValidateClosedRateSequence(bars,4,boundary,latest,4,4,interval,false),true);
   bars[1].time-=interval;
   Expect("session_gap_allowed_without_calendar",ValidateClosedRateSequence(bars,4,boundary,latest,4,4,interval,false),true);
   Expect("session_gap_rejected_when_contiguous_required",ValidateClosedRateSequence(bars,4,boundary,latest,4,4,interval,true),false);

   bars[0].time=0;
   Expect("zero_timestamp",ValidateClosedRateSequence(bars,4,boundary,latest,4,4,interval,false),false);
   MakeSeries(bars,4,boundary,interval);
   bars[0].time=boundary;
   Expect("forming_or_future_bar_rejected",ValidateClosedRateSequence(bars,4,boundary,latest,4,4,interval,false),false);
   MakeSeries(bars,4,boundary,interval);
   bars[1].time=bars[0].time;
   Expect("duplicate_timestamp",ValidateClosedRateSequence(bars,4,boundary,latest,4,4,interval,false),false);
   MakeSeries(bars,4,boundary,interval);
   bars[1].time=bars[0].time+interval;
   Expect("backward_or_out_of_order_timestamp",ValidateClosedRateSequence(bars,4,boundary,latest,4,4,interval,false),false);
   MakeSeries(bars,4,boundary,interval);
   Expect("stale_expected_latest_mismatch",ValidateClosedRateSequence(bars,4,boundary,latest-interval,4,4,interval,false),false);
   MqlRates partial[];
   MakeSeries(partial,3,boundary,interval);
   Expect("insufficient_history_after_partial_copy",ValidateClosedRateSequence(partial,3,boundary,partial[0].time,4,4,interval,false),false);
   Expect("partial_copy_at_minimum_contract",ValidateClosedRateSequence(partial,3,boundary,partial[0].time,3,4,interval,false),true);
   Expect("count_array_size_mismatch",ValidateClosedRateSequence(partial,4,boundary,partial[0].time,3,4,interval,false),false);
   Expect("invalid_boundary",ValidateClosedRateSequence(bars,4,0,latest,4,4,interval,false),false);
   Expect("invalid_period",ValidateClosedRateSequence(bars,4,boundary,latest,4,4,0,false),false);
   MakeSeries(bars,4,boundary,interval);
   bars[0].close=bars[0].high+1.0;
   Expect("invalid_ohlc",ValidateClosedRateSequence(bars,4,boundary,latest,4,4,interval,false),false);

   MqlRates empty[];
   ArraySetAsSeries(empty,true);
   Expect("empty_zero_minimum_rejected",ValidateClosedRateSequence(empty,0,boundary,latest,0,4,interval,false),false);
   Expect("negative_minimum_rejected",ValidateClosedRateSequence(partial,3,boundary,partial[0].time,-1,4,interval,false),false);
   Expect("inverted_count_limits_rejected",ValidateClosedRateSequence(partial,3,boundary,partial[0].time,4,3,interval,false),false);

   PrintFormat("[CHRONOLOGY_FINAL] %s cases=%d failures=%d",g_failures==0 ? "PASS" : "FAIL",g_cases,g_failures);
}
