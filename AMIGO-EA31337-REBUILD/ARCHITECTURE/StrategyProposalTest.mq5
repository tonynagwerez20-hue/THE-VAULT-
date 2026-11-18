#property strict
#include "TrendStrategy.mqh"
#include "MeanReversionStrategy.mqh"
int OnInit() {
 TrendStrategy trend("trend",1); MeanReversionStrategy mr("mr",2);
 TradeIntent p;
 if(trend.GenerateProposal(1,"TEST",PERIOD_M30,p)) return INIT_FAILED;
 if(mr.GenerateProposal(1,"TEST",PERIOD_M30,p)) return INIT_FAILED;
 Print("UNINITIALIZED_PROPOSALS_BLOCKED"); return INIT_SUCCEEDED;
}
void OnTick() {}
