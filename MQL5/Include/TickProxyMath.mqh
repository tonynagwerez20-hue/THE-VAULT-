//+------------------------------------------------------------------+
//| TickProxyMath.mqh                                                |
//| Diagnostic-only compact tick proxy mathematics                   |
//| Hardened pure bounded calculations; NO STRATEGY CONSUMPTION      |
//+------------------------------------------------------------------+
#ifndef AMIGO_INCLUDE_TICK_PROXY_MATH_MQH
#define AMIGO_INCLUDE_TICK_PROXY_MATH_MQH

#property strict

// Upper bound for batch size to prevent unbounded execution loops
#define TICK_PROXY_MAX_BATCH_SIZE 100000

enum ENUM_PROXY_MATH_QUALITY
{
   PROXY_QUALITY_INVALID = 0,
   PROXY_QUALITY_EMPTY   = 1,
   PROXY_QUALITY_FLAT    = 2,
   PROXY_QUALITY_VALID   = 3
};

struct TickProxyMetrics
{
   int                      n;
   int                      u;
   int                      d;
   int                      unchanged;
   double                   directional_balance;
   double                   moving_fraction;
   double                   normalized_pressure;
   double                   activity_rate;
   bool                     activity_rate_available;
   double                   directional_efficiency;
   bool                     directional_efficiency_available;
   double                   normalized_displacement;
   bool                     normalized_displacement_available;
   ENUM_PROXY_MATH_QUALITY  quality;
};

//+------------------------------------------------------------------+
//| Pure functional evaluation of tick deltas with hardened checks   |
//+------------------------------------------------------------------+
bool CalculateTickProxyMetrics(const double &deltas[],
                               const int count,
                               const double elapsed_seconds,
                               const double prior_atr,
                               TickProxyMetrics &out)
{
   ZeroMemory(out);
   out.quality = PROXY_QUALITY_INVALID;

   int array_len = ArraySize(deltas);
   if(count <= 0 || count > array_len || count > TICK_PROXY_MAX_BATCH_SIZE)
   {
      if(count == 0) out.quality = PROXY_QUALITY_EMPTY;
      return false;
   }

   int u = 0, d = 0, flat = 0;
   double net_disp = 0.0;
   double gross_disp = 0.0;

   for(int i = 0; i < count; i++)
   {
      double delta = deltas[i];
      if(!MathIsValidNumber(delta)) return false;

      if(delta > 0.0) u++;
      else if(delta < 0.0) d++;
      else flat++;

      net_disp += delta;
      gross_disp += MathAbs(delta);

      // Guard against intermediate sum overflow
      if(!MathIsValidNumber(net_disp) || !MathIsValidNumber(gross_disp))
         return false;
   }

   out.n = count;
   out.u = u;
   out.d = d;
   out.unchanged = flat;

   int moving = u + d;
   out.moving_fraction = (double)moving / (double)count;
   out.directional_balance = (moving > 0) ? ((double)(u - d) / (double)moving) : 0.0;
   out.normalized_pressure = (double)(u - d) / (double)count;

   // Activity rate contract
   if(MathIsValidNumber(elapsed_seconds) && elapsed_seconds > 0.0)
   {
      double rate = (double)count / elapsed_seconds;
      if(MathIsValidNumber(rate) && rate >= 0.0)
      {
         out.activity_rate = rate;
         out.activity_rate_available = true;
      }
   }

   // Directional efficiency contract
   if(gross_disp > 0.0)
   {
      double eff = MathAbs(net_disp) / gross_disp;
      if(MathIsValidNumber(eff) && eff >= 0.0 && eff <= 1.00000001)
      {
         out.directional_efficiency = MathMin(1.0, eff);
         out.directional_efficiency_available = true;
      }
   }

   // Normalized displacement contract
   if(MathIsValidNumber(prior_atr) && prior_atr > 0.0)
   {
      double norm_disp = net_disp / prior_atr;
      if(MathIsValidNumber(norm_disp))
      {
         out.normalized_displacement = norm_disp;
         out.normalized_displacement_available = true;
      }
   }

   // Quality classification:
   // FLAT if all deltas are zero (gross_disp == 0)
   // VALID if gross_disp > 0 and metrics are finite
   if(gross_disp == 0.0)
   {
      out.quality = PROXY_QUALITY_FLAT;
   }
   else
   {
      out.quality = PROXY_QUALITY_VALID;
   }

   return true;
}

#endif // AMIGO_INCLUDE_TICK_PROXY_MATH_MQH
