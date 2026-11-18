#ifndef AMIGO_TICK_IMBALANCE_BARS_MQH
#define AMIGO_TICK_IMBALANCE_BARS_MQH

// Quote-tick imbalance, not exchange traded volume. Each observation belongs
// to one bar only; equal bid quotes count as ticks with zero directional weight.
struct TIBBar
{
   double open,high,low,close;
   long tick_count,imbalance;
   long open_msc,close_msc;
};

class TickImbalanceBars
{
private:
   int m_threshold;
   double m_previous;
   long m_last_msc;
   TIBBar m_building,m_closed;
   bool m_ready;
public:
   TickImbalanceBars() { Reset(100); }
   void Reset(const int threshold)
   {
      m_threshold=threshold; m_previous=0; m_last_msc=0; m_ready=false;
      ZeroMemory(m_building); ZeroMemory(m_closed);
   }
   bool Add(const double bid,const double ask,const long time_msc)
   {
      if(m_threshold<=0 || !MathIsValidNumber(bid) || !MathIsValidNumber(ask) ||
         bid<=0 || ask<bid || time_msc<=0 || time_msc<m_last_msc)
      { Reset(m_threshold); return false; }
      int direction=m_previous==0 ? 0 : (bid>m_previous ? 1 : (bid<m_previous ? -1 : 0));
      m_previous=bid; m_last_msc=time_msc;
      if(m_building.tick_count==0)
      {
         m_building.open=bid; m_building.high=bid; m_building.low=bid;
         m_building.open_msc=time_msc;
      }
      m_building.high=MathMax(m_building.high,bid);
      m_building.low=MathMin(m_building.low,bid);
      m_building.close=bid; m_building.close_msc=time_msc;
      m_building.tick_count++; m_building.imbalance+=direction;
      if(MathAbs(m_building.imbalance)<m_threshold) return false;
      m_closed=m_building; m_ready=true; ZeroMemory(m_building);
      return true;
   }
   bool ClosedBefore(const long boundary_msc,TIBBar &bar) const
   {
      if(!m_ready || m_closed.close_msc>=boundary_msc) return false;
      bar=m_closed;
      return true;
   }
};
#endif
