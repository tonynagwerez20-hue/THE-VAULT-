//+------------------------------------------------------------------+
//|                                                AM_FlowEvents.mqh |
//|                                  Copyright 2026, Amigo / ASAP |
//|                                        Zero-Cost Order-Flow EA   |
//+------------------------------------------------------------------+
#property copyright "Amigo / ASAP"
#property link      "https://Amigo.local"
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
   int               m_history_limit;

public:
                     CAM_FlowEvents(int persistence_bars = 2)
     {
      m_persistence_bars = persistence_bars;
      if(m_persistence_bars < 1) m_persistence_bars = 1;
      // Persistence needs m_persistence_bars observations; divergence only
      // compares the latest two, so three slots preserve all existing queries.
      // This diagnostic history must not grow for the lifetime of the EA.
      m_history_limit = (m_persistence_bars > 3) ? m_persistence_bars : 3;
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
      int idx=0;
      if(m_count < m_history_limit)
        {
         int next_count=m_count+1;
         if(ArrayResize(m_state_history,next_count)!=next_count ||
            ArrayResize(m_pressure_history,next_count)!=next_count ||
            ArrayResize(m_high_history,next_count)!=next_count ||
            ArrayResize(m_low_history,next_count)!=next_count ||
            ArrayResize(m_activity_history,next_count)!=next_count)
           {
            // Parallel arrays must remain aligned. On allocation failure,
            // discard the incomplete diagnostic window rather than exposing
            // mismatched indices to persistence/divergence queries.
            Reset();
            return;
           }
         m_count=next_count;
         idx=m_count-1;
        }
      else
        {
         // Retain only the newest bounded window. All existing readers use
         // recent persistence state or the latest two bars.
         for(int i=1;i<m_history_limit;i++)
           {
            m_state_history[i-1]=m_state_history[i];
            m_pressure_history[i-1]=m_pressure_history[i];
            m_high_history[i-1]=m_high_history[i];
            m_low_history[i-1]=m_low_history[i];
            m_activity_history[i-1]=m_activity_history[i];
           }
         idx=m_history_limit-1;
        }
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

