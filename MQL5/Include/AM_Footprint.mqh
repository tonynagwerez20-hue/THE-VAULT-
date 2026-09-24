//+------------------------------------------------------------------+
//|                                                 AM_Footprint.mqh |
//|                                  Copyright 2026, AlgoMind / ASAP |
//|                                        Zero-Cost Order-Flow EA   |
//+------------------------------------------------------------------+
#property copyright "AlgoMind / ASAP"
#property link      "https://algomind.local"
#property strict

#include "AM_FlowQuality.mqh"
#include "AM_ActivityProfile.mqh"

//+------------------------------------------------------------------+
//| Class CAM_Footprint                                              |
//| Price binning, tick-rule classification & pressure calculation   |
//+------------------------------------------------------------------+
class CAM_Footprint
  {
private:
   double            m_tick_size;
   MQL_FootprintBin  m_bins[];
   int               m_bin_count;
   double            m_prev_price;
   double            m_cumulative_delta;

public:
                     CAM_Footprint(double tick_size = 0.01)
     {
      m_tick_size        = (tick_size > 0.0) ? tick_size : 0.01;
      m_bin_count        = 0;
      m_prev_price       = 0.0;
      m_cumulative_delta = 0.0;
     }

   void Reset(void)
     {
      ArrayResize(m_bins, 0);
      m_bin_count  = 0;
      m_prev_price = 0.0;
     }

   void ResetCumulativeDelta(void)
     {
      m_cumulative_delta = 0.0;
     }

   //--- Normalise price to tick boundary
   double NormalisePrice(double price) const
     {
      if(m_tick_size <= 0.0) return price;
      return MathRound(price / m_tick_size) * m_tick_size;
     }

   //--- Find or create bin index for price
   int GetBinIndex(double normalised_price)
     {
      for(int i = 0; i < m_bin_count; i++)
        {
         if(MathAbs(m_bins[i].price - normalised_price) < 1e-7)
            return i;
        }

      // Add new bin
      int new_idx = m_bin_count;
      m_bin_count++;
      ArrayResize(m_bins, m_bin_count);

      m_bins[new_idx].price                  = normalised_price;
      m_bins[new_idx].observed_activity      = 0.0;
      m_bins[new_idx].tick_count             = 0;
      m_bins[new_idx].estimated_buy_activity  = 0.0;
      m_bins[new_idx].estimated_sell_activity = 0.0;
      m_bins[new_idx].estimated_delta         = 0.0;
      m_bins[new_idx].price_response         = 0.0;
      m_bins[new_idx].pressure               = 0.0;

      return new_idx;
     }

   //--- Add a single tick (Tick Rule estimator)
   void AddTick(double price, double volume, int direction = 0)
     {
      if(price <= 0.0 || volume <= 0.0)
         return;

      int final_dir = direction;
      if(final_dir == 0 && m_prev_price > 0.0)
        {
         if(price > m_prev_price)      final_dir = 1;
         else if(price < m_prev_price) final_dir = -1;
        }
      m_prev_price = price;

      double norm_p = NormalisePrice(price);
      int idx = GetBinIndex(norm_p);

      m_bins[idx].tick_count += 1;
      m_bins[idx].observed_activity += volume;

      if(final_dir == 1)
        {
         m_bins[idx].estimated_buy_activity += volume;
         m_cumulative_delta += volume;
        }
      else if(final_dir == -1)
        {
         m_bins[idx].estimated_sell_activity += volume;
         m_cumulative_delta -= volume;
        }

      m_bins[idx].estimated_delta = m_bins[idx].estimated_buy_activity - m_bins[idx].estimated_sell_activity;
     }

   //--- Calculate Footprint Pressure: P = Σδ / (Σ|δ| + eps)
   double CalculateFootprintPressure(void)
     {
      double sum_delta = 0.0;
      double sum_abs_delta = 0.0;

      for(int i = 0; i < m_bin_count; i++)
        {
         sum_delta += m_bins[i].estimated_delta;
         sum_abs_delta += MathAbs(m_bins[i].estimated_delta);
        }

      double eps = 1e-12;
      return sum_delta / (sum_abs_delta + eps);
     }

   //--- Get total activity
   double GetTotalActivity(void) const
     {
      double tot = 0.0;
      for(int i = 0; i < m_bin_count; i++) tot += m_bins[i].observed_activity;
      return tot;
     }

   //--- Get total delta
   double GetTotalDelta(void) const
     {
      double tot = 0.0;
      for(int i = 0; i < m_bin_count; i++) tot += m_bins[i].estimated_delta;
      return tot;
     }

   double GetCumulativeDelta(void) const
     {
      return m_cumulative_delta;
     }

   //--- Copy bins out for profile calculations
   void GetBins(MQL_FootprintBin &out_bins[]) const
     {
      ArrayResize(out_bins, m_bin_count);
      for(int i = 0; i < m_bin_count; i++)
         out_bins[i] = m_bins[i];
     }

   int GetBinCount(void) const { return m_bin_count; }
  };
