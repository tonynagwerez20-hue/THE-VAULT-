"""Quote imbalance reference; same flat-tick and ownership rules as native TIB."""
import math
class TIBGenerator:
    def __init__(self, threshold_ticks=100):
        if not isinstance(threshold_ticks,int) or threshold_ticks<=0: raise ValueError('positive integer threshold required')
        self.threshold=threshold_ticks
        self.last_price=None
        self.last_time=None
        self.current=None
    def process_tick(self,tick):
        bid,ask=float(tick['bid']),float(tick['ask'])
        ts=int(tick.get('time_msc',tick.get('time',0)*1000))
        if not all(math.isfinite(x) for x in (bid,ask)) or bid<=0 or ask<bid or ts<=0 or (self.last_time is not None and ts<self.last_time):
            self.__init__(self.threshold)
            raise ValueError('invalid or backward quote')
        direction=0 if self.last_price is None else int(bid>self.last_price)-int(bid<self.last_price)
        self.last_price,self.last_time=bid,ts
        if self.current is None:
            self.current=dict(open=bid,high=bid,low=bid,close=bid,tick_count=0,imbalance=0,threshold=self.threshold,open_msc=ts)
        b=self.current
        b.update(high=max(b['high'],bid),low=min(b['low'],bid),close=bid,tick_count=b['tick_count']+1,imbalance=b['imbalance']+direction,timestamp=ts/1000,close_msc=ts)
        if abs(b['imbalance'])<self.threshold: return None
        self.current=None
        return b
