//+------------------------------------------------------------------+
//|                                                AM_ProxyVWAP.mqh  |
//|                                  Copyright 2026, AlgoMind / ASAP |
//|                                        Zero-Cost Order-Flow EA   |
//+------------------------------------------------------------------+
#property copyright "AlgoMind / ASAP"
#property link      "https://algomind.local"
#property strict

#include "AM_FlowQuality.mqh"

//+------------------------------------------------------------------+
//| Class CAM_ProxyVWAP                                              |
//| Incremental Proxy VWAP Engine for MQL5 EA runtime (Spec Section 16)|
//+------------------------------------------------------------------+
class CAM_ProxyVWAP
  {
private:
   double            m_cum_weighted_price;
   double            m_cum_activity;
   ENUM_DATA_QUALITY_TAG m_quality;

public:
                     CAM_ProxyVWAP(void)
     {
      Reset();
      m_quality = DATA_QUALITY_PROXY;
     }

   //--- Reset session accumulators
   void Reset(void)
     {
      m_cum_weighted_price = 0.0;
      m_cum_activity       = 0.0;
     }

   //--- Add a single price/volume observation
   void AddObservation(double price, double volume)
     {
      if(price <= 0.0 || volume <= 0.0)
         return;

      m_cum_weighted_price += price * volume;
      m_cum_activity       += volume;
     }

   //--- Get current Proxy VWAP value
   double GetVWAP(void) const
     {
      if(m_cum_activity <= 0.0)
         return 0.0;
      return m_cum_weighted_price / m_cum_activity;
     }

   //--- Calculate ATR-normalized VWAP deviation: (Price - VWAP) / (ATR + eps)
   double GetDeviation(double current_price, double atr) const
     {
      double vwap = GetVWAP();
      if(vwap <= 0.0)
         return 0.0;

      double eps = 1e-12;
      double denom = (atr > 0.0) ? atr : 1.0;
      return (current_price - vwap) / (denom + eps);
     }

   //--- Accumulator getters
   double GetCumWeightedPrice(void) const { return m_cum_weighted_price; }
   double GetCumActivity(void)      const { return m_cum_activity;       }
   ENUM_DATA_QUALITY_TAG GetQuality(void) const { return m_quality; }
  };
