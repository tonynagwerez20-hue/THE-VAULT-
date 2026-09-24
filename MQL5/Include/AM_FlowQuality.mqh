//+------------------------------------------------------------------+
//|                                              AM_FlowQuality.mqh  |
//|                                  Copyright 2026, AlgoMind / ASAP |
//|                                        Zero-Cost Order-Flow EA   |
//+------------------------------------------------------------------+
#property copyright "AlgoMind / ASAP"
#property link      "https://algomind.local"
#property strict

//--- Data Quality Tags (Spec Section 14)
enum ENUM_DATA_QUALITY_TAG
  {
   DATA_QUALITY_TRUE,     // Actual exchange-traded bid/ask/trade data
   DATA_QUALITY_PROXY,    // Estimator derived from retail quotes / tick volume (e.g. MT5 tick direction)
   DATA_QUALITY_LIMITED,  // Partial historical sample or OHLCV-only context
   DATA_QUALITY_MISSING   // Data field absent / unpopulated
  };

//--- Flow Execution Mode (Spec Section 47)
enum ENUM_FLOW_MODE
  {
   FLOW_MODE_RESEARCH,    // Historical analysis only
   FLOW_MODE_SHADOW,      // Shadow execution alongside EA decision engine without altering trades
   FLOW_MODE_LIVE         // Authorized features influencing live decisions
  };

//--- Pressure State (Spec Section 21)
enum ENUM_PRESSURE_STATE
  {
   PRESSURE_STATE_BEARISH = -1,
   PRESSURE_STATE_NEUTRAL = 0,
   PRESSURE_STATE_BULLISH = 1
  };

//+------------------------------------------------------------------+
//| Utility function to convert Data Quality Tag to String            |
//+------------------------------------------------------------------+
string DataQualityTagToString(ENUM_DATA_QUALITY_TAG tag)
  {
   switch(tag)
     {
      case DATA_QUALITY_TRUE:    return "TRUE";
      case DATA_QUALITY_PROXY:   return "PROXY";
      case DATA_QUALITY_LIMITED: return "LIMITED";
      case DATA_QUALITY_MISSING: return "MISSING";
     }
   return "UNKNOWN";
  }

//+------------------------------------------------------------------+
//| Utility function to convert Pressure State to String             |
//+------------------------------------------------------------------+
string PressureStateToString(ENUM_PRESSURE_STATE state)
  {
   switch(state)
     {
      case PRESSURE_STATE_BEARISH: return "BEARISH";
      case PRESSURE_STATE_NEUTRAL: return "NEUTRAL";
      case PRESSURE_STATE_BULLISH: return "BULLISH";
     }
   return "NEUTRAL";
  }
