#ifndef AMIGO_FROZEN_FOOTPRINT_MQH
#define AMIGO_FROZEN_FOOTPRINT_MQH
#define AM_FOOTPRINT_MAX_BINS 256
// MT5_TICK_PROXY: unit observation counts and tick-rule direction, NOT
// exchange volume, aggressive orders, displayed depth or actual absorption.
struct FrozenFootprint
{
   bool available,failed;
   int count,observations,up,down,neutral;
   double width,previous,pressure,poc,concentration;
   long keys[AM_FOOTPRINT_MAX_BINS];
   int activity[AM_FOOTPRINT_MAX_BINS];
   int delta[AM_FOOTPRINT_MAX_BINS];
};
void FrozenFootprintReset(FrozenFootprint &f,const double width)
{
   ZeroMemory(f); f.width=width;
}
bool FrozenFootprintAdd(FrozenFootprint &f,const double price)
{
   f.available=false;
   if(f.failed) return false;
   f.failed=true; // latch any rejected observation until reset
   if(f.observations>=8192) return false;
   if(!MathIsValidNumber(price) || price<=0.0 || !MathIsValidNumber(f.width) || f.width<=0.0) return false;
   double key_value=MathFloor(price/f.width);
   if(!MathIsValidNumber(key_value) || key_value<0.0 || key_value>9007199254740991.0) return false;
   long key=(long)key_value;
   int at=-1;
   for(int i=0;i<f.count;i++) if(f.keys[i]==key) { at=i; break; }
   if(at<0)
   {
      if(f.count>=AM_FOOTPRINT_MAX_BINS) return false;
      at=f.count++; f.keys[at]=key;
   }
   int direction=0;
   if(f.previous>0.0) direction=price>f.previous ? 1 : (price<f.previous ? -1 : 0);
   f.activity[at]++; f.delta[at]+=direction; f.observations++;
   if(direction>0) f.up++; else if(direction<0) f.down++; else f.neutral++;
   f.previous=price;
   f.failed=false;
   return true;
}
bool FrozenFootprintFinish(FrozenFootprint &f)
{
   f.available=false;
   if(f.failed || f.count<=0 || f.count>AM_FOOTPRINT_MAX_BINS || f.observations<2 || f.up+f.down+f.neutral!=f.observations) return false;
   int peak=0,net=0,absolute=0,total=0;
   for(int i=0;i<f.count;i++)
   {
      total+=f.activity[i]; net+=f.delta[i]; absolute+=(int)MathAbs(f.delta[i]);
      if(f.activity[i]>f.activity[peak] || (f.activity[i]==f.activity[peak] && f.keys[i]<f.keys[peak])) peak=i;
   }
   if(total!=f.observations || net!=f.up-f.down) return false;
   f.pressure=absolute>0 ? (double)net/(double)absolute : 0.0;
   f.poc=((double)f.keys[peak]+0.5)*f.width;
   f.concentration=(double)f.activity[peak]/(double)total;
   if(!MathIsValidNumber(f.poc) || !MathIsValidNumber(f.pressure)) return false;
   f.available=true; return true;
}
#endif
