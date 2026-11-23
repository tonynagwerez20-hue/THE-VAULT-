//+------------------------------------------------------------------+
//| Test_TickProxyMath.mq5                                           |
//| Standalone validation script for TickProxyMath.mqh               |
//+------------------------------------------------------------------+
#property script_show_inputs
#property strict

#include <TickProxyMath.mqh>

void OnStart()
{
   Print("=== RUNNING HARDENED TICK PROXY MATH STANDALONE CHECKS ===");
   int pass_count = 0;
   int fail_count = 0;

   // Test 1: Bounds violation - count exceeds array size
   double small_arr[2];
   small_arr[0] = 1.0; small_arr[1] = 2.0;
   TickProxyMetrics mb;
   if(!CalculateTickProxyMetrics(small_arr, 5, 60.0, 1.0, mb) && mb.quality == PROXY_QUALITY_INVALID)
      pass_count++;
   else
   {
      Print("FAIL: Bounds violation check failed");
      fail_count++;
   }

   // Test 2: Nonfinite delta rejection
   double nan_arr[3];
   nan_arr[0] = 1.0; nan_arr[1] = MathSqrt(-1.0); nan_arr[2] = 2.0;
   TickProxyMetrics mn;
   if(!CalculateTickProxyMetrics(nan_arr, 3, 60.0, 1.0, mn) && mn.quality == PROXY_QUALITY_INVALID)
      pass_count++;
   else
   {
      Print("FAIL: Nonfinite delta rejection failed");
      fail_count++;
   }

   // Test 3: Intermediate sum overflow guard
   double ovf_arr[2];
   ovf_arr[0] = 1.7e308; ovf_arr[1] = 1.7e308;
   TickProxyMetrics mo;
   if(!CalculateTickProxyMetrics(ovf_arr, 2, 60.0, 1.0, mo) && mo.quality == PROXY_QUALITY_INVALID)
      pass_count++;
   else
   {
      Print("FAIL: Sum overflow check failed");
      fail_count++;
   }

   // Test 4: Flat path - quality FLAT, zero balance, but valid rate if time valid
   double flat_arr[10];
   ArrayInitialize(flat_arr, 0.0);
   TickProxyMetrics mf;
   if(CalculateTickProxyMetrics(flat_arr, 10, 5.0, 1.0, mf) &&
      mf.quality == PROXY_QUALITY_FLAT &&
      mf.activity_rate_available &&
      MathAbs(mf.activity_rate - 2.0) < 1e-6 &&
      !mf.directional_efficiency_available)
      pass_count++;
   else
   {
      Print("FAIL: Flat path check failed");
      fail_count++;
   }

   // Test 5: Invalid normalization inputs - rate/displacement unavailable but quality VALID
   double valid_arr[3];
   valid_arr[0] = 1.0; valid_arr[1] = 2.0; valid_arr[2] = -1.0;
   TickProxyMetrics mv;
   if(CalculateTickProxyMetrics(valid_arr, 3, 0.0, -1.0, mv) &&
      mv.quality == PROXY_QUALITY_VALID &&
      !mv.activity_rate_available &&
      !mv.normalized_displacement_available &&
      mv.directional_efficiency_available)
      pass_count++;
   else
   {
      Print("FAIL: Normalization availability check failed");
      fail_count++;
   }

   // Test 6: Plan reference case: 1 up, 99 flat
   double d1[100];
   ArrayInitialize(d1, 0.0);
   d1[0] = 1.0;
   TickProxyMetrics m1;
   if(CalculateTickProxyMetrics(d1, 100, 60.0, 1.0, m1) &&
      MathAbs(m1.directional_balance - 1.0) < 1e-6 &&
      MathAbs(m1.normalized_pressure - 0.01) < 1e-6 &&
      m1.quality == PROXY_QUALITY_VALID)
      pass_count++;
   else
   {
      Print("FAIL: Plan reference 1 up 99 flat failed");
      fail_count++;
   }

   // Test 7: Plan reference case: 100 up
   double d2[100];
   ArrayInitialize(d2, 1.0);
   TickProxyMetrics m2;
   if(CalculateTickProxyMetrics(d2, 100, 60.0, 1.0, m2) &&
      MathAbs(m2.directional_balance - 1.0) < 1e-6 &&
      MathAbs(m2.normalized_pressure - 1.0) < 1e-6 &&
      MathAbs(m2.directional_efficiency - 1.0) < 1e-6)
      pass_count++;
   else
   {
      Print("FAIL: Plan reference 100 up failed");
      fail_count++;
   }

   Print(StringFormat("RESULT: %d passed, %d failed", pass_count, fail_count));
}
