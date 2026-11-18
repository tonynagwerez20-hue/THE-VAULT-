// Offline native assertions. Production event handlers are renamed, never run.
#define OnInit ProductionOnInit
#define OnTick ProductionOnTick
#define OnTimer ProductionOnTimer
#define OnDeinit ProductionOnDeinit
#define OnTradeTransaction ProductionOnTradeTransaction
#include "AMIGO.mq5"
#undef OnInit
#undef OnTick
#undef OnTimer
#undef OnDeinit
#undef OnTradeTransaction

void OnStart()
{
   int failures=0;
   double mve=RiskControllerGetMinimumViableEquity(10.0,1.5,5.0);
   if(MathAbs(mve-276.393202250021)>0.000001) failures++;
   if(MathAbs(RiskControllerGetNormalEquity(10.0)-2000.0)>0.000001) failures++;
   TickImbalanceBars tib; tib.Reset(2); TIBBar b;
   if(tib.Add(100,101,1000)) failures++;
   if(tib.Add(101,102,1001)) failures++;
   if(!tib.Add(102,103,1002)) failures++;
   if(tib.ClosedBefore(1002,b)) failures++;
   if(!tib.ClosedBefore(1003,b) || b.tick_count!=3 || b.imbalance!=2 || b.open!=100 || b.close!=102) failures++;
   if(tib.Add(102,103,1003)) failures++;
   if(tib.Add(101,102,1004)) failures++;
   if(!tib.Add(100,101,1005)) failures++;
   if(!tib.ClosedBefore(1006,b) || b.tick_count!=3 || b.open!=102 || b.imbalance!=-2) failures++;
   tib.Add(0,1,1006);
   if(tib.ClosedBefore(1007,b)) failures++;
   int f=FileOpen("quant_native_result.txt",FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(f!=INVALID_HANDLE) { FileWrite(f,"failures="+IntegerToString(failures)); FileClose(f); }
   PrintFormat("QUANT_NATIVE_ASSERTIONS failures=%d MVE=%.10f",failures,mve);
}
