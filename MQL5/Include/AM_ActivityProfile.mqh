//+------------------------------------------------------------------+
//|                                           AM_ActivityProfile.mqh |
//|                                  Copyright 2026, AlgoMind / ASAP |
//|                                        Zero-Cost Order-Flow EA   |
//+------------------------------------------------------------------+
#property copyright "AlgoMind / ASAP"
#property link      "https://algomind.local"
#property strict

#include "AM_FlowQuality.mqh"

//--- Structure for price-level activity bin in MQL5
struct MQL_FootprintBin
  {
   double            price;
   double            observed_activity;
   int               tick_count;
   double            estimated_buy_activity;
   double            estimated_sell_activity;
   double            estimated_delta;
   double            price_response;
   double            pressure;
  };

//+------------------------------------------------------------------+
//| Class CAM_ActivityProfile                                        |
//| Derives Proxy POC, VAH (70%), VAL, and Concentration (Spec 17)   |
//+------------------------------------------------------------------+
class CAM_ActivityProfile
  {
private:
   double            m_value_area_pct;
   double            m_poc_price;
   double            m_vah_price;
   double            m_val_price;
   double            m_concentration;
   ENUM_DATA_QUALITY_TAG m_quality;

public:
                     CAM_ActivityProfile(double value_area_pct = 0.70)
     {
      m_value_area_pct = value_area_pct;
      Reset();
     }

   void Reset(void)
     {
      m_poc_price     = 0.0;
      m_vah_price     = 0.0;
      m_val_price     = 0.0;
      m_concentration = 0.0;
      m_quality       = DATA_QUALITY_PROXY;
     }

   //--- Compute POC, VAH, VAL from array of FootprintBins
   void Compute(const MQL_FootprintBin &bins[], int count)
     {
      if(count <= 0)
        {
         Reset();
         m_quality = DATA_QUALITY_MISSING;
         return;
        }

      double total_activity = 0.0;
      double max_act = -1.0;
      int poc_idx = 0;

      for(int i = 0; i < count; i++)
        {
         total_activity += bins[i].observed_activity;
         if(bins[i].observed_activity > max_act)
           {
            max_act = bins[i].observed_activity;
            poc_idx = i;
           }
        }

      if(total_activity <= 0.0)
        {
         m_poc_price = bins[count / 2].price;
         m_vah_price = bins[count - 1].price;
         m_val_price = bins[0].price;
         m_concentration = 0.0;
         m_quality = DATA_QUALITY_MISSING;
         return;
        }

      m_poc_price = bins[poc_idx].price;

      // Copy indices for sorting by activity descending
      int indices[];
      ArrayResize(indices, count);
      for(int i = 0; i < count; i++) indices[i] = i;

      // Bubble sort indices by observed_activity descending (stable & reliable for MQL5 array size)
      for(int i = 0; i < count - 1; i++)
        {
         for(int j = 0; j < count - i - 1; j++)
           {
            if(bins[indices[j]].observed_activity < bins[indices[j + 1]].observed_activity)
              {
               int tmp = indices[j];
               indices[j] = indices[j + 1];
               indices[j + 1] = tmp;
              }
           }
        }

      double target_act = m_value_area_pct * total_activity;
      double cum_act = 0.0;

      double vah = -1.0;
      double val = 1e15;
      double va_activity = 0.0;

      for(int i = 0; i < count; i++)
        {
         int idx = indices[i];
         cum_act += bins[idx].observed_activity;
         va_activity += bins[idx].observed_activity;

         if(bins[idx].price > vah) vah = bins[idx].price;
         if(bins[idx].price < val) val = bins[idx].price;

         if(cum_act >= target_act)
            break;
        }

      m_vah_price     = (vah > 0.0) ? vah : m_poc_price;
      m_val_price     = (val < 1e14) ? val : m_poc_price;
      m_concentration = va_activity / total_activity;
      m_quality       = DATA_QUALITY_PROXY;
     }

   //--- Getters
   double GetPOC(void)           const { return m_poc_price; }
   double GetVAH(void)           const { return m_vah_price; }
   double GetVAL(void)           const { return m_val_price; }
   double GetConcentration(void) const { return m_concentration; }
   ENUM_DATA_QUALITY_TAG GetQuality(void) const { return m_quality; }
  };
