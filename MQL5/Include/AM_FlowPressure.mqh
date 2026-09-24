//+------------------------------------------------------------------+
//|                                              AM_FlowPressure.mqh |
//|                                  Copyright 2026, AlgoMind / ASAP |
//|                                        Zero-Cost Order-Flow EA   |
//+------------------------------------------------------------------+
#property copyright "AlgoMind / ASAP"
#property link      "https://algomind.local"
#property strict

#include "AM_FlowQuality.mqh"

//+------------------------------------------------------------------+
//| Class CAM_FlowPressure                                           |
//| Tracks pressure, state transitions, flips, and baseline activity |
//+------------------------------------------------------------------+
class CAM_FlowPressure
  {
private:
   double                m_pressure_threshold;
   double                m_surge_threshold;
   double                m_surge_act_mult;

   ENUM_PRESSURE_STATE   m_prev_state;
   double                m_prev_pressure;
   double                m_activity_baseline;
   double                m_alpha;

public:
                     CAM_FlowPressure(double pressure_threshold = 0.25,
                                      double surge_threshold    = 0.60,
                                      double surge_act_mult     = 1.5)
     {
      m_pressure_threshold = pressure_threshold;
      m_surge_threshold    = surge_threshold;
      m_surge_act_mult     = surge_act_mult;

      m_prev_state        = PRESSURE_STATE_NEUTRAL;
      m_prev_pressure     = 0.0;
      m_activity_baseline = 0.0;
      m_alpha             = 0.1;
     }

   void Reset(void)
     {
      m_prev_state        = PRESSURE_STATE_NEUTRAL;
      m_prev_pressure     = 0.0;
      m_activity_baseline = 0.0;
     }

   //--- Classify state from pressure value
   ENUM_PRESSURE_STATE ClassifyState(double pressure) const
     {
      if(pressure >= m_pressure_threshold)  return PRESSURE_STATE_BULLISH;
      if(pressure <= -m_pressure_threshold) return PRESSURE_STATE_BEARISH;
      return PRESSURE_STATE_NEUTRAL;
     }

   //--- Check if current bar qualifies as a Surge
   bool IsSurge(double pressure, double total_activity) const
     {
      if(MathAbs(pressure) < m_surge_threshold)
         return false;
      if(m_activity_baseline <= 0.0)
         return false;
      return (total_activity >= m_activity_baseline * m_surge_act_mult);
     }

   //--- Check for direct directional reversal (Flip)
   bool IsFlip(ENUM_PRESSURE_STATE current_state, int &out_direction) const
     {
      out_direction = 0;
      if(m_prev_state == PRESSURE_STATE_BULLISH && current_state == PRESSURE_STATE_BEARISH)
        {
         out_direction = -1;
         return true;
        }
      if(m_prev_state == PRESSURE_STATE_BEARISH && current_state == PRESSURE_STATE_BULLISH)
        {
         out_direction = 1;
         return true;
        }
      return false;
     }

   //--- Update baseline activity EMA and record state
   void UpdateState(double pressure, double total_activity, ENUM_PRESSURE_STATE new_state)
     {
      if(m_activity_baseline <= 0.0)
         m_activity_baseline = total_activity;
      else
         m_activity_baseline = (m_alpha * total_activity) + ((1.0 - m_alpha) * m_activity_baseline);

      m_prev_state    = new_state;
      m_prev_pressure = pressure;
     }

   ENUM_PRESSURE_STATE GetPreviousState(void)   const { return m_prev_state;        }
   double              GetPreviousPressure(void)const { return m_prev_pressure;     }
   double              GetActivityBaseline(void)const { return m_activity_baseline; }
  };
