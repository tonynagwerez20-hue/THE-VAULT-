#property strict
#include "Strategy_Framework.mqh"
class FixtureStrategy : public Strategy {
public:
 FixtureStrategy():Strategy("fixture","fixture",1) { SetSymbol("TEST"); SetTimeframe(PERIOD_M30); }
 bool GenerateProposal(const long id,const string symbol,const int tf,TradeIntent &p) override {
  if(!m_initialized) return false;
  ZeroMemory(p); p.direction=1; p.confidence=.6; p.hypothesis=HYP_CONTINUATION;
  p.horizon=HORIZON_SWING; p.regime=REGIME_TREND_UP; return true;
 }
};
int OnInit() {
 StrategyRegistry r; r.Init();
 if(!r.RegisterStrategy(new FixtureStrategy())) return INIT_FAILED;
 TradeIntent p[]; int n=0;
 if(r.GenerateProposals(10,"TEST",PERIOD_M30,p,n)) return INIT_FAILED;
 if(!r.GenerateProposals(10,"TEST",PERIOD_M30,p,n,99,REGIME_TREND_UP,0) || n!=1) return INIT_FAILED;
 if(p[0].decision_id!=99 || p[0].snapshot_id!=10) return INIT_FAILED;
 if(r.GenerateProposals(11,"TEST",PERIOD_M30,p,n,100,REGIME_NEWS,0)) return INIT_FAILED;
 if(r.GenerateProposals(11,"TEST",PERIOD_M30,p,n,100,REGIME_TREND_UP,1)) return INIT_FAILED;
 Print("STRATEGY_LIFECYCLE_PASS"); return INIT_SUCCEEDED;
}
void OnTick() {}
