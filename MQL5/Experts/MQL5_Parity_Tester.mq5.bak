//+------------------------------------------------------------------+
//|                                         MQL5_Parity_Tester.mq5   |
//|                                  Copyright 2026, AlgoMind / ASAP |
//|                                        Zero-Cost Order-Flow EA   |
//+------------------------------------------------------------------+
#property copyright "AlgoMind / ASAP"
#property link      "https://algomind.local"
#property version   "1.00"
#property script_show_inputs

#include <AM_FlowQuality.mqh>
#include <AM_ProxyVWAP.mqh>
#include <AM_ActivityProfile.mqh>
#include <AM_Footprint.mqh>
#include <AM_FlowPressure.mqh>

//+------------------------------------------------------------------+
//| Script program start function                                    |
//+------------------------------------------------------------------+
void OnStart()
  {
   Print("=== ALGOMIND MQL5 ORDER-FLOW PARITY TESTER ===");

   CAM_ProxyVWAP      vwap_engine;
   CAM_Footprint      footprint(0.01);
   CAM_ActivityProfile profile(0.70);
   CAM_FlowPressure   pressure_engine(0.25, 0.60, 1.5);

   // Add sample ticks
   footprint.AddTick(2000.10, 2.0, 1);
   vwap_engine.AddObservation(2000.10, 2.0);

   footprint.AddTick(2000.20, 5.0, 1);
   vwap_engine.AddObservation(2000.20, 5.0);

   footprint.AddTick(2000.15, 3.0, -1);
   vwap_engine.AddObservation(2000.15, 3.0);

   footprint.AddTick(2000.30, 10.0, 1);
   vwap_engine.AddObservation(2000.30, 10.0);

   double vwap_val = vwap_engine.GetVWAP();
   double press_val = footprint.CalculateFootprintPressure();
   ENUM_PRESSURE_STATE state = pressure_engine.ClassifyState(press_val);

   MQL_FootprintBin bins[];
   footprint.GetBins(bins);
   profile.Compute(bins, ArraySize(bins));

   PrintFormat("[PARITY_MQL5] VWAP=%.5f PRESSURE=%.5f STATE=%s POC=%.2f VAH=%.2f VAL=%.2f",
               vwap_val, press_val, PressureStateToString(state),
               profile.GetPOC(), profile.GetVAH(), profile.GetVAL());
  }
