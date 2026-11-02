//+------------------------------------------------------------------+
//|                                                  AM_ProxyDOM.mqh |
//|                                  Copyright 2026, AlgoMind / ASAP |
//|                                        Zero-Cost Order-Flow EA   |
//+------------------------------------------------------------------+
#property copyright "AlgoMind / ASAP"
#property link      "https://algomind.local"
#property strict

#include "AM_FlowQuality.mqh"
#include "AM_ActivityProfile.mqh"

//+------------------------------------------------------------------+
//| Class CAM_ProxyDOM                                               |
//| Native MQL5 Activity-at-Price Ladder & MarketBook Integration    |
//+------------------------------------------------------------------+
class CAM_ProxyDOM
  {
private:
   int                   m_depth;
   ENUM_DATA_QUALITY_TAG m_quality;

public:
                     CAM_ProxyDOM(int depth = 20)
     {
      m_depth   = depth;
      m_quality = DATA_QUALITY_PROXY;
     }

   //--- Subscribe to MarketBook if broker provides depth
   bool SubscribeBook(string symbol)
     {
      return MarketBookAdd(symbol);
     }

   //--- Unsubscribe
   bool UnsubscribeBook(string symbol)
     {
      return MarketBookRelease(symbol);
     }

   //--- Get snapshot of broker depth if available (Spec Section 30)
   bool GetBrokerDepth(string symbol, MqlBookInfo &book_array[])
     {
      bool res = MarketBookGet(symbol, book_array);
      if(!res || ArraySize(book_array) == 0)
        {
         m_quality = DATA_QUALITY_PROXY;
         return false;
        }
      m_quality = DATA_QUALITY_PROXY; // Tagged BROKER-SUPPLIED DEPTH, not central DOM
      return true;
     }

   ENUM_DATA_QUALITY_TAG GetQuality(void) const { return m_quality; }
  };
