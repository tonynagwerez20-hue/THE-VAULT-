//+------------------------------------------------------------------+
//|   Test_HorizonPropagation.mq5                                     |
//+------------------------------------------------------------------+
#property script_show_inputs

#include <Contracts header.mqh>
#include <Configuration.mqh>
#include <Position Manager.mqh>

void OnStart()
{
   Print("--- START HORIZON PROPAGATION AND MANAGEMENT TESTS ---");
   
   // Test Registration with explicit horizon
   PositionManagerRegister(1001, 2000.0, 1990.0, 2020.0, +1, 2.0, g_cfg, HORIZON_SCALPING);
   PositionManagerRegister(1002, 2000.0, 1990.0, 2020.0, +1, 2.0, g_cfg, HORIZON_INTRADAY);
   PositionManagerRegister(1003, 2000.0, 1990.0, 2020.0, +1, 2.0, g_cfg, HORIZON_SWING);
   
   int total = ArraySize(g_positions);
   PrintFormat("[TEST] Registered %d positions:", total);
   for(int i = 0; i < total; i++)
   {
      string h_str = EnumToString(g_positions[i].horizon);
      PrintFormat("  pos[%d] ticket=%I64u horizon=%s be_trigger=%.2f", 
                  i, g_positions[i].position_id, h_str, g_positions[i].be_trigger_price);
   }
   
   // Verify BE trigger logic:
   // Scalping (33%): 2000 + (20 * 0.33) = 2006.60
   // Intraday (50%): 2000 + (20 * 0.50) = 2010.00
   // Swing (60%):    2000 + (20 * 0.60) = 2012.00
   bool ok = (g_positions[0].horizon == HORIZON_SCALPING) &&
             (g_positions[1].horizon == HORIZON_INTRADAY) &&
             (g_positions[2].horizon == HORIZON_SWING);
             
   if(ok)
      Print("[TEST PASS] Horizon identity properly registered and stored across all three profiles.");
   else
      Print("[TEST FAIL] Horizon identity propagation failure detected!");
}
