//+------------------------------------------------------------------+
//|   Test_RegimeReachability.mq5                                    |
//+------------------------------------------------------------------+
#property script_show_inputs

#include <Contracts header.mqh>
#include <Configuration.mqh>
#include <Structure Engine.mqh>
#include <Regime Engine.mqh>

void OnStart()
{
   Print("--- REGIME REACHABILITY TEST SUITE ---");
   FeatureSnapshot f;
   ZeroMemory(f);
   
   // Test TREND_UP
   f.structure_dir = +1;
   f.fusion = 0.8;
   f.bull_flip = true;
   f.bear_flip = false;
   f.surge = true;
   RegimeState rs_up = EvaluateRegime(f, g_cfg);
   PrintFormat("Test 1 (Trend Up): Regime=%d (Expected 1) Conf=%.2f", (int)rs_up.regime, rs_up.confidence);

   // Test TREND_DOWN
   f.structure_dir = -1;
   f.fusion = -0.8;
   f.bull_flip = false;
   f.bear_flip = true;
   f.surge = true;
   RegimeState rs_down = EvaluateRegime(f, g_cfg);
   PrintFormat("Test 2 (Trend Down): Regime=%d (Expected 2) Conf=%.2f", (int)rs_down.regime, rs_down.confidence);

   // Test BALANCED
   f.structure_dir = 0;
   f.fusion = 0.05;
   f.bull_flip = false;
   f.bear_flip = false;
   f.surge = false;
   f.range_ratio = 0.5;
   RegimeState rs_bal = EvaluateRegime(f, g_cfg);
   PrintFormat("Test 3 (Balanced): Regime=%d (Expected 3) Conf=%.2f", (int)rs_bal.regime, rs_bal.confidence);

   Print("--- REGIME REACHABILITY TESTS COMPLETED ---");
}
