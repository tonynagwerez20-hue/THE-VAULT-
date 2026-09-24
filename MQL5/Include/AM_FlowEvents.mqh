//+------------------------------------------------------------------+
//|                                                AM_FlowEvents.mqh |
//|                                  Copyright 2026, AlgoMind / ASAP |
//|                                        Zero-Cost Order-Flow EA   |
//+------------------------------------------------------------------+
#property copyright "AlgoMind / ASAP"
#property link      "https://algomind.local"
#property strict

#include "AM_FlowQuality.mqh"
#include "AM_FlowPressure.mqh"

//--- Multi-bar event flags
struct MQL_FlowEvent
  {
   datetime          time;
   string            event_type; // PERSISTENCE | DIVERGENCE_BULL | DIVERGENCE_BEAR | ABSORPTION_CANDIDATE | EXHAUSTION_CANDIDATE
   double            pressure;
   ENUM_PRESSURE_STATE state;
  };

//+------------------------------------------------------------------+
//| Class CAM_FlowEvents                                             |
//| Detects Persistence, Divergence, Absorption, Exhaustion in MQL5 |
//+------------------------------------------------------------------+
class CAM_FlowEvents
  {
private:
   int               m_persistence_bars;
   ENUM_PRESSURE_STATE m_state_history[];
   double            m_pressure_history[];
   double            m_high_history[];
   double            m_low_history[];
   double            m_activity_history[];
   int               m_count;

public:
                     CAM_FlowEvents(int persistence_bars = 2)
     {
      m_persistence_bars = persistence_bars;
      Reset();
     }

   void Reset(void)
     {
      ArrayResize(m_state_history, 0);
      ArrayResize(m_pressure_history, 0);
      ArrayResize(m_high_history, 0);
      ArrayResize(m_low_history, 0);
      ArrayResize(m_activity_history, 0);
      m_count = 0;
     }

   void AddBar(datetime bar_time, double pressure, ENUM_PRESSURE_STATE state, double high_price, double low_price, double total_activity)
     {
      m_count++;
      ArrayResize(m_state_history, m_count);
      ArrayResize(m_pressure_history, m_count);
      ArrayResize(m_high_history, m_count);
      ArrayResize(m_low_history, m_count);
      ArrayResize(m_activity_history, m_count);

      int idx = m_count - 1;
      m_state_history[idx]    = state;
      m_pressure_history[idx] = pressure;
      m_high_history[idx]     = high_price;
      m_low_history[idx]      = low_price;
      m_activity_history[idx] = total_activity;
     }

   //--- Persistence check
   bool IsPersistent(void) const
     {
      if(m_count < m_persistence_bars)
         return false;

      ENUM_PRESSURE_STATE target = m_state_history[m_count - 1];
      if(target == PRESSURE_STATE_NEUTRAL)
         return false;

      for(int i = m_count - m_persistence_bars; i < m_count; i++)
        {
         if(m_state_history[i] != target)
            return false;
        }
      return true;
     }

   //--- Bullish Divergence check (Price lower-low, pressure higher-low)
   bool IsBullishDivergence(void) const
     {
      if(m_count < 3) return false;
      int curr = m_count - 1;
      int prev = m_count - 2;
      return (m_low_history[curr] < m_low_history[prev] && m_pressure_history[curr] > m_pressure_history[prev]);
     }

   //--- Bearish Divergence check (Price higher-high, pressure lower-high)
   bool IsBearishDivergence(void) const
     {
      if(m_count < 3) return false;
      int curr = m_count - 1;
      int prev = m_count - 2;
      return (m_high_history[curr] > m_high_history[prev] && m_pressure_history[curr] < m_pressure_history[prev]);
     }
  };
