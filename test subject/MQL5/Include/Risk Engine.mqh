//+------------------------------------------------------------------+
//| RiskEngine.mqh - hard risk, sizing, stop selection               |
//+------------------------------------------------------------------+
#property strict

#include <Contracts header.mqh>
#include <Configuration.mqh>
#include <Logger.mqh>

//--- Persistent risk state
struct RiskState
{
   double   start_of_day_equity;
   double   peak_equity;
   double   initial_equity;
   double   adaptive_high_water;
   double   adaptive_last_equity;
   bool     daily_locked;
   bool     total_locked;
   bool     initialized;
   bool     persistence_ok;
   datetime last_day;
   datetime last_opportunity_bar;
   long     last_opportunity_id;
   int      last_opportunity_outcome; // 0 none, 1 reserved/ambiguous, 2 reject, 3 no-trade, 4 confirmed, 5 uncertain, 6 shadow
   long     generation;
};

RiskState g_risk;
bool g_risk_opportunity_inflight=false;
bool g_risk_lock_owned=false;
bool g_risk_lock_contended=false;
double g_risk_lock_token=0.0;
string g_risk_lock_key="";
bool g_risk_lock_fault=false;

#define RISK_OP_RESERVED 1
#define RISK_OP_REJECTED 2
#define RISK_OP_NO_TRADE 3
#define RISK_OP_CONFIRMED 4
#define RISK_OP_UNCERTAIN 5
#define RISK_OP_SHADOW 6

// All AMIGO charts on one broker account use the broker-server calendar date
// for the shared daily-risk boundary. Opportunity timestamps remain per symbol.
datetime RiskServerDayBoundary()
{
   MqlDateTime value;
   if(!TimeToStruct(TimeCurrent(),value)) return 0;
   value.hour=0; value.min=0; value.sec=0;
   return StructToTime(value);
}

bool RiskSameServerDate(const datetime left,const datetime right)
{
   MqlDateTime a,b;
   if(!TimeToStruct(left,a) || !TimeToStruct(right,b)) return false;
   return a.year==b.year && a.mon==b.mon && a.day==b.day;
}

int RiskServerDateCode(const datetime value)
{
   MqlDateTime date;
   if(!TimeToStruct(value,date)) return 0;
   return date.year*10000+date.mon*100+date.day;
}

long RiskScopeHash(const string value)
{
   long hash=146959810;
   for(int i=0;i<StringLen(value);i++) hash=(hash*16777619+(long)StringGetCharacter(value,i))%2147483647;
   return hash;
}

double RiskAccountIdentityCode()
{
   string currency=AccountInfoString(ACCOUNT_CURRENCY);
   int margin_mode=(int)AccountInfoInteger(ACCOUNT_MARGIN_MODE);
   int trade_mode=(int)AccountInfoInteger(ACCOUNT_TRADE_MODE);
   if(currency=="" || margin_mode<0 || trade_mode<0 || Amigo_RISK_STATE_POLICY_VERSION<=0) return 0.0;
   string identity=StringFormat("%s|%d|%d|%d",currency,margin_mode,trade_mode,Amigo_RISK_STATE_POLICY_VERSION);
   long code=RiskScopeHash(identity);
   return (code>0)?(double)code:0.0;
}

bool RiskAccountSlotIdentityValid(const string prefix,const string slot,const long generation)
{
   double expected=RiskAccountIdentityCode();
   string key=prefix+slot+".X";
   string generation_key=prefix+slot+".XG";
   if(expected<=0.0 || generation<=0 || !GlobalVariableCheck(key) ||
      !GlobalVariableCheck(generation_key)) return false;
   double actual=GlobalVariableGet(key);
   double actual_generation=GlobalVariableGet(generation_key);
   return MathIsValidNumber(actual) && actual==expected &&
          MathIsValidNumber(actual_generation) && actual_generation==(double)generation;
}

string RiskLedgerPrefix()
{
   // Per-symbol opportunity consumption remains in the legacy AMR namespace.
   string scope=StringFormat("%I64d|%I64u|%s|%s",AccountInfoInteger(ACCOUNT_LOGIN),g_cfg.magic_number,
                             AccountInfoString(ACCOUNT_SERVER),g_cfg.symbol);
   return StringFormat("AMR.%I64d.%I64u.%I64d.",AccountInfoInteger(ACCOUNT_LOGIN),g_cfg.magic_number,RiskScopeHash(scope));
}

string RiskAccountLedgerPrefix()
{
   string scope=StringFormat("%I64d|%I64u|%s",AccountInfoInteger(ACCOUNT_LOGIN),
                             g_cfg.magic_number,AccountInfoString(ACCOUNT_SERVER));
   return StringFormat("AMRA.%I64d.%I64u.%I64d.",AccountInfoInteger(ACCOUNT_LOGIN),
                       g_cfg.magic_number,RiskScopeHash(scope));
}

string RiskOpportunityLockKey()
{
   // One terminal-local admission mutex for the entire account/server, including
   // different magic numbers. Per-strategy ledgers do not define account exposure.
   string scope=StringFormat("%I64d|%s",AccountInfoInteger(ACCOUNT_LOGIN),
                             AccountInfoString(ACCOUNT_SERVER));
   return StringFormat("AMR.L.%I64d.%I64d.M3",AccountInfoInteger(ACCOUNT_LOGIN),
                       RiskScopeHash(scope));
}

bool RiskLegacyAdmissionLocksClear()
{
   // Do not silently bypass an outstanding old-version reservation on upgrade.
   // This is not coordination with running legacy EAs: mixed versions remain unsupported.
   string prefix=StringFormat("AMR.L.%I64d.",AccountInfoInteger(ACCOUNT_LOGIN));
   int count=GlobalVariablesTotal();
   for(int i=0;i<count;i++)
   {
      string key=GlobalVariableName(i);
      if(key=="") return false;
      if(StringFind(key,prefix)!=0 || StringLen(key)<3 ||
         StringSubstr(key,StringLen(key)-3)!=".M2") continue;
      double owner=0.0;
      if(!GlobalVariableGet(key,owner) || !MathIsValidNumber(owner) || owner!=0.0) return false;
   }
   return GlobalVariablesTotal()==count;
}

bool RiskAccountLockWasContended()
{
   return g_risk_lock_contended;
}

bool RiskVerifyAccountLockOwnership()
{
   double observed=0.0;
   if(!g_risk_lock_fault && g_risk_lock_owned &&
      g_risk_lock_key==RiskOpportunityLockKey() && g_risk_lock_key!="" &&
      MathIsValidNumber(g_risk_lock_token) && g_risk_lock_token>0.0 &&
      GlobalVariableGet(g_risk_lock_key,observed) &&
      MathIsValidNumber(observed) && observed==g_risk_lock_token) return true;
   // Never reacquire or release a different owner's token after local ownership
   // becomes ambiguous. The existing callers propagate false into quarantine.
   g_risk_lock_fault=true;
   g_risk.persistence_ok=false;
   g_risk_lock_owned=false;
   g_risk_lock_token=0.0;
   g_risk_lock_key="";
   return false;
}

bool RiskAcquireAccountLock()
{
   g_risk_lock_contended=false;
   if(g_risk_lock_fault) return false;
   if(g_risk_lock_owned) return RiskVerifyAccountLockOwnership();
   if(!RiskLegacyAdmissionLocksClear()) return false;
   string key=RiskOpportunityLockKey();
   // Create-once; never reset an existing owner's token after a separate
   // existence check. GlobalVariableSetOnCondition then arbitrates the lock.
   if(!GlobalVariableTemp(key) && !GlobalVariableCheck(key)) return false;
   double token=(double)(ChartID()%1000000000)*1000000.0+(double)(GetTickCount()%1000000);
   if(token<=0.0) return false;
   if(!GlobalVariableSetOnCondition(key,token,0.0))
   {
      // The owner may release between the failed CAS and this check. Treat any
      // still-existing lock key as a retryable serialization race; do not turn
      // a transient cross-chart collision into a permanent state-fault latch.
      // Admission still stops for this tick, and no owner token is changed.
      g_risk_lock_contended=GlobalVariableCheck(key);
      return false;
   }
   g_risk_lock_owned=true;
   g_risk_lock_token=token;
   g_risk_lock_key=key;
   return true;
}

bool RiskReleaseAccountLock()
{
   if(!g_risk_lock_owned) return false;
   if(!RiskVerifyAccountLockOwnership()) return false;
   if(!GlobalVariableSetOnCondition(g_risk_lock_key,0.0,g_risk_lock_token))
   {
      g_risk_lock_fault=true;
      g_risk.persistence_ok=false;
      g_risk_lock_owned=false;
      g_risk_lock_token=0.0;
      g_risk_lock_key="";
      return false;
   }
   g_risk_lock_owned=false;
   g_risk_lock_token=0.0;
   g_risk_lock_key="";
   return true;
}

double RiskLedgerChecksum(const RiskState &s)
{
   return 1.0*s.generation+3.0*s.start_of_day_equity+5.0*s.peak_equity+
          7.0*(s.daily_locked?1.0:0.0)+11.0*(s.total_locked?1.0:0.0)+
          13.0*(double)s.last_day+17.0*s.initial_equity+
          19.0*s.adaptive_high_water+23.0*s.adaptive_last_equity+
          29.0*(double)s.last_opportunity_bar+31.0*(double)s.last_opportunity_id+
          37.0*(double)s.last_opportunity_outcome;
}

bool RiskLedgerSlotRead(const string prefix,const string slot,RiskState &s)
{
   string keys[13]={"G","S","P","D","T","Y","I","H","E","B","Q","O","C"};
   double v[13];
   for(int i=0;i<13;i++)
   {
      string key=prefix+slot+"."+keys[i];
      if(!GlobalVariableCheck(key)) return false;
      v[i]=GlobalVariableGet(key);
      if(!MathIsValidNumber(v[i])) return false;
   }
   if(v[0]<1.0 || v[0]>9007199254740000.0 || v[3]<0.0 || v[3]>1.0 || v[4]<0.0 || v[4]>1.0 ||
      v[1]<=0.0 || v[2]<=0.0 || v[5]<=0.0 || v[6]<=0.0 || v[7]<=0.0 || v[8]<=0.0 ||
      v[9]<0.0 || v[10]<0.0 || v[11]<0.0 || v[11]>6.0 ||
      v[0]!=MathFloor(v[0]) || v[3]!=MathFloor(v[3]) || v[4]!=MathFloor(v[4]) ||
      v[5]!=MathFloor(v[5]) || v[9]!=MathFloor(v[9]) || v[10]!=MathFloor(v[10]) ||
      v[11]!=MathFloor(v[11]) || ((v[9]==0.0)!=(v[10]==0.0)) ||
      ((v[9]==0.0)!=(v[11]==0.0))) return false;
   s.generation=(long)v[0]; s.start_of_day_equity=v[1]; s.peak_equity=v[2];
   s.daily_locked=(v[3]==1.0); s.total_locked=(v[4]==1.0); s.last_day=(datetime)v[5];
   s.initial_equity=v[6]; s.adaptive_high_water=v[7]; s.adaptive_last_equity=v[8];
   s.last_opportunity_bar=(datetime)v[9]; s.last_opportunity_id=(long)v[10]; s.last_opportunity_outcome=(int)v[11];
   return MathAbs(RiskLedgerChecksum(s)-v[12])<=0.000001;
}

// Never fall back to an older slot when another slot has incomplete evidence.
// This is a conservative recovery check, not a crash-durability guarantee.
bool RiskLedgerPairConsistent(const string prefix,const bool va,const RiskState &a,
                              const bool vb,const RiskState &b)
{
   string slots[2]={"A","B"};
   string keys[15]={"G","S","P","D","T","Y","I","H","E","B","Q","O","C","X","XG"};
   for(int slot=0;slot<2;slot++)
   {
      bool valid=(slot==0)?va:vb;
      bool present=false;
      for(int k=0;k<15;k++)
         if(GlobalVariableCheck(prefix+slots[slot]+"."+keys[k])) present=true;
      if(present && !valid) return false;
      if(valid && prefix==RiskAccountLedgerPrefix())
      {
         long generation=(slot==0)?a.generation:b.generation;
         if(!RiskAccountSlotIdentityValid(prefix,slots[slot],generation)) return false;
      }
   }
   if(va && a.generation%2!=0) return false;
   if(vb && b.generation%2!=1) return false;
   if(va && vb) return MathAbs((double)(a.generation-b.generation))==1.0;
   // The only legitimate one-slot state is the initial B generation.
   // Missing either member of a later pair is an ambiguous loss of history.
   if(va) return false;
   if(vb) return b.generation==1;
   return true; // both absent: existing explicit bootstrap policy still applies
}

bool RiskLedgerSlotWrite(const string prefix,const string slot,const RiskState &s)
{
   string keys[12]={"S","P","D","T","Y","I","H","E","B","Q","O","C"};
   double v[12]={s.start_of_day_equity,s.peak_equity,s.daily_locked?1.0:0.0,
      s.total_locked?1.0:0.0,(double)s.last_day,s.initial_equity,
      s.adaptive_high_water,s.adaptive_last_equity,(double)s.last_opportunity_bar,
      (double)s.last_opportunity_id,(double)s.last_opportunity_outcome,RiskLedgerChecksum(s)};
   for(int i=0;i<12;i++) if(GlobalVariableSet(prefix+slot+"."+keys[i],v[i])==0) return false;
   GlobalVariablesFlush();
   if(GlobalVariableSet(prefix+slot+".G",(double)s.generation)==0) return false; // commit marker last
   GlobalVariablesFlush();
   RiskState verify;
   // A valid checksum/generation is insufficient: verify the intended payload
   // exactly, including consumed-opportunity identity/outcome and risk limits.
   return RiskLedgerSlotRead(prefix,slot,verify) &&
      verify.generation==s.generation &&
      verify.start_of_day_equity==s.start_of_day_equity &&
      verify.peak_equity==s.peak_equity &&
      verify.daily_locked==s.daily_locked && verify.total_locked==s.total_locked &&
      verify.last_day==s.last_day && verify.initial_equity==s.initial_equity &&
      verify.adaptive_high_water==s.adaptive_high_water &&
      verify.adaptive_last_equity==s.adaptive_last_equity &&
      verify.last_opportunity_bar==s.last_opportunity_bar &&
      verify.last_opportunity_id==s.last_opportunity_id &&
      verify.last_opportunity_outcome==s.last_opportunity_outcome;
}

void RiskCopyAccountFields(RiskState &destination,const RiskState &source)
{
   destination.start_of_day_equity=source.start_of_day_equity;
   destination.peak_equity=source.peak_equity;
   destination.initial_equity=source.initial_equity;
   destination.adaptive_high_water=source.adaptive_high_water;
   destination.adaptive_last_equity=source.adaptive_last_equity;
   destination.daily_locked=source.daily_locked;
   destination.total_locked=source.total_locked;
   destination.last_day=source.last_day;
}

bool RiskAccountRefresh()
{
   string prefix=RiskAccountLedgerPrefix();
   RiskState a,b;
   bool va=RiskLedgerSlotRead(prefix,"A",a),vb=RiskLedgerSlotRead(prefix,"B",b);
   if(!RiskLedgerPairConsistent(prefix,va,a,vb,b)) return false;
   if(!va && !vb) return false;
   RiskState latest=(!vb || (va && a.generation>=b.generation))?a:b;
   if(!RiskAccountSlotIdentityValid(prefix,(latest.generation%2==0)?"A":"B",latest.generation)) return false;
   RiskCopyAccountFields(g_risk,latest);
   return true;
}

bool RiskSymbolRefresh()
{
   string prefix=RiskLedgerPrefix();
   RiskState a,b;
   bool va=RiskLedgerSlotRead(prefix,"A",a),vb=RiskLedgerSlotRead(prefix,"B",b);
   if(!RiskLedgerPairConsistent(prefix,va,a,vb,b)) return false;
   if(!va && !vb) return false;
   RiskState latest=(!vb || (va && a.generation>=b.generation))?a:b;
   g_risk.last_opportunity_bar=latest.last_opportunity_bar;
   g_risk.last_opportunity_id=latest.last_opportunity_id;
   g_risk.last_opportunity_outcome=latest.last_opportunity_outcome;
   g_risk.generation=latest.generation;
   return true;
}

bool RiskPersistSymbol()
{
   if(!g_risk.initialized) return false;
   string prefix=RiskLedgerPrefix();
   string active=(g_risk.generation%2==0)?"A":"B";
   string target=(active=="A")?"B":"A";
   g_risk.generation++;
   if(!RiskLedgerSlotWrite(prefix,target,g_risk))
   {
      g_risk.persistence_ok=false;
      return false;
   }
   g_risk.persistence_ok=true;
   return true;
}

bool RiskPersistAccount()
{
   string prefix=RiskAccountLedgerPrefix();
   RiskState a,b;
   bool va=RiskLedgerSlotRead(prefix,"A",a),vb=RiskLedgerSlotRead(prefix,"B",b);
   if(!RiskLedgerPairConsistent(prefix,va,a,vb,b)) return false;
   bool any=false;
   string slots[2]={"A","B"};
   string keys[13]={"G","S","P","D","T","Y","I","H","E","B","Q","O","C"};
   for(int s=0;s<2;s++)
      for(int k=0;k<13;k++)
         if(GlobalVariableCheck(prefix+slots[s]+"."+keys[k])) any=true;
   if(any && !va && !vb) return false;

   long generation=0;
   if(va || vb)
   {
      RiskState latest=(!vb || (va && a.generation>=b.generation))?a:b;
      string latest_slot=(latest.generation%2==0)?"A":"B";
      if(!RiskAccountSlotIdentityValid(prefix,latest_slot,latest.generation)) return false;
      if(MathAbs(latest.initial_equity-g_risk.initial_equity)>0.000001) return false;
      if(latest.last_day>g_risk.last_day)
      {
         g_risk.last_day=latest.last_day;
         g_risk.start_of_day_equity=latest.start_of_day_equity;
         g_risk.daily_locked=latest.daily_locked;
      }
      else if(latest.last_day==g_risk.last_day)
      {
         // A higher same-day baseline is the conservative merge for the
         // (baseline-equity)/baseline drawdown calculation.
         g_risk.start_of_day_equity=MathMax(g_risk.start_of_day_equity,latest.start_of_day_equity);
         g_risk.daily_locked=(g_risk.daily_locked || latest.daily_locked);
      }
      g_risk.peak_equity=MathMax(g_risk.peak_equity,latest.peak_equity);
      g_risk.total_locked=(g_risk.total_locked || latest.total_locked);
      g_risk.adaptive_high_water=MathMax(g_risk.adaptive_high_water,latest.adaptive_high_water);
      generation=latest.generation;
   }

   RiskState account_state=g_risk;
   account_state.last_opportunity_bar=0;
   account_state.last_opportunity_id=0;
   account_state.last_opportunity_outcome=0;
   account_state.generation=generation+1;
   string target=(generation%2==0)?"B":"A";
   double identity_code=RiskAccountIdentityCode();
   if(identity_code<=0.0 || GlobalVariableSet(prefix+target+".X",identity_code)==0 ||
      GlobalVariableSet(prefix+target+".XG",(double)account_state.generation)==0) return false;
   GlobalVariablesFlush();
   if(!RiskLedgerSlotWrite(prefix,target,account_state)) return false;
   return true;
}

bool RiskPersist(const bool persist_symbol=true)
{
   if(!g_risk.initialized || !g_risk.persistence_ok) return false;
   bool acquired_here=!g_risk_lock_owned;
   if(!RiskAcquireAccountLock()) return false;
   bool symbol_ok=!persist_symbol || RiskPersistSymbol();
   bool account_ok=symbol_ok && RiskPersistAccount();
   if(!symbol_ok || !account_ok) g_risk.persistence_ok=false;
   bool released=true;
   if(acquired_here) released=RiskReleaseAccountLock();
   return symbol_ok && account_ok && released;
}

int RiskCollectLegacyLedgerPrefixes(string &prefixes[])
{
   ArrayResize(prefixes,0);
   string base=StringFormat("AMR.%I64d.%I64u.",AccountInfoInteger(ACCOUNT_LOGIN),g_cfg.magic_number);
   int total=GlobalVariablesTotal();
   for(int i=0;i<total;i++)
   {
      string name=GlobalVariableName(i);
      if(StringFind(name,base,0)!=0) continue;
      int hash_end=StringFind(name,".",StringLen(base));
      if(hash_end<0) continue;
      int slot_pos=hash_end+1;
      if(slot_pos+1>=StringLen(name)) continue;
      string slot=StringSubstr(name,slot_pos,1);
      if((slot!="A" && slot!="B") || StringSubstr(name,slot_pos+1,1)!=".") continue;
      string prefix=StringSubstr(name,0,hash_end+1);
      bool duplicate=false;
      for(int p=0;p<ArraySize(prefixes);p++) if(prefixes[p]==prefix) { duplicate=true; break; }
      if(duplicate) continue;
      int n=ArraySize(prefixes);
      if(ArrayResize(prefixes,n+1)!=n+1) return -1;
      prefixes[n]=prefix;
   }
   return ArraySize(prefixes);
}

int RiskLegacyOpportunityStatus()
{
   string prefixes[];
   int count=RiskCollectLegacyLedgerPrefixes(prefixes);
   if(count<0) return -1;
   for(int i=0;i<count;i++)
   {
      RiskState a,b;
      bool va=RiskLedgerSlotRead(prefixes[i],"A",a),vb=RiskLedgerSlotRead(prefixes[i],"B",b);
      if(!RiskLedgerPairConsistent(prefixes[i],va,a,vb,b)) return -1;
      if(!va && !vb) return -1;
      RiskState state=(!vb || (va && a.generation>=b.generation))?a:b;
      if(state.last_opportunity_outcome==RISK_OP_RESERVED ||
         state.last_opportunity_outcome==RISK_OP_UNCERTAIN) return 1;
   }
   return 0;
}

bool RiskLegacyAggregate(const datetime today,const string current_symbol_prefix,
                         RiskState &account_state,RiskState &symbol_state,
                         bool &symbol_found,bool &uncertain_found)
{
   string prefixes[];
   int count=RiskCollectLegacyLedgerPrefixes(prefixes);
   // Legacy names store only a hash of server+symbol. We cannot safely
   // attribute multiple hashes to this broker account. Migrate only the
   // single exact current account/server/symbol ledger; otherwise require
   // explicit recovery instead of mixing unknown histories.
   if(count!=1) return false;
   if(prefixes[0]!=current_symbol_prefix) return false;
   bool any_today=false;
   bool any=false;
   double max_day_equity=0.0;
   ZeroMemory(account_state);
   ZeroMemory(symbol_state);
   symbol_found=false;
   uncertain_found=false;
   double current_equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(!MathIsValidNumber(current_equity) || current_equity<=0.0) return false;

   for(int i=0;i<count;i++)
   {
      RiskState a,b;
      bool va=RiskLedgerSlotRead(prefixes[i],"A",a),vb=RiskLedgerSlotRead(prefixes[i],"B",b);
      if(!RiskLedgerPairConsistent(prefixes[i],va,a,vb,b)) return false;
      if(!va && !vb) return false; // an artifact with no valid committed slot is ambiguous
      RiskState state=(!vb || (va && a.generation>=b.generation))?a:b;
      int state_date=RiskServerDateCode(state.last_day);
      int today_date=RiskServerDateCode(today);
      if(state_date<=0 || today_date<=0 || state_date>today_date) return false;
      if(any && state.initial_equity>account_state.initial_equity)
         account_state.initial_equity=state.initial_equity;
      else if(!any) account_state.initial_equity=state.initial_equity;
      account_state.peak_equity=MathMax(account_state.peak_equity,state.peak_equity);
      account_state.total_locked=(account_state.total_locked || state.total_locked);
      account_state.adaptive_high_water=MathMax(account_state.adaptive_high_water,state.adaptive_high_water);
      if(RiskSameServerDate(state.last_day,today))
      {
         any_today=true;
         max_day_equity=MathMax(max_day_equity,state.start_of_day_equity);
         account_state.daily_locked=(account_state.daily_locked || state.daily_locked);
      }
      if(state.last_opportunity_outcome==RISK_OP_RESERVED ||
         state.last_opportunity_outcome==RISK_OP_UNCERTAIN) uncertain_found=true;
      if(prefixes[i]==current_symbol_prefix)
      {
         symbol_state=state;
         symbol_found=true;
      }
      any=true;
   }
   if(!any || !any_today || account_state.initial_equity<=0.0 ||
      account_state.peak_equity<=0.0 || account_state.adaptive_high_water<=0.0) return false;
   account_state.start_of_day_equity=max_day_equity;
   account_state.adaptive_last_equity=current_equity;
   account_state.last_day=today;
   account_state.generation=0;
   account_state.last_opportunity_bar=0;
   account_state.last_opportunity_id=0;
   account_state.last_opportunity_outcome=0;
   return true;
}

bool RiskInitLocked(const bool allow_explicit_bootstrap)
{
   string symbol_prefix=RiskLedgerPrefix();
   string account_prefix=RiskAccountLedgerPrefix();
   RiskState symbol_a,symbol_b,account_a,account_b;
   bool symbol_va=RiskLedgerSlotRead(symbol_prefix,"A",symbol_a);
   bool symbol_vb=RiskLedgerSlotRead(symbol_prefix,"B",symbol_b);
   bool account_va=RiskLedgerSlotRead(account_prefix,"A",account_a);
   bool account_vb=RiskLedgerSlotRead(account_prefix,"B",account_b);
   if(!RiskLedgerPairConsistent(symbol_prefix,symbol_va,symbol_a,symbol_vb,symbol_b) ||
      !RiskLedgerPairConsistent(account_prefix,account_va,account_a,account_vb,account_b)) return false;
   bool account_ledger_found=(account_va || account_vb);
   string slots[2]={"A","B"};
   string keys[13]={"G","S","P","D","T","Y","I","H","E","B","Q","O","C"};
   bool symbol_any=false,account_any=false;
   for(int s=0;s<2;s++)
      for(int k=0;k<13;k++)
      {
         if(GlobalVariableCheck(symbol_prefix+slots[s]+"."+keys[k])) symbol_any=true;
         if(GlobalVariableCheck(account_prefix+slots[s]+"."+keys[k])) account_any=true;
      }
   if((symbol_any && !symbol_va && !symbol_vb) || (account_any && !account_va && !account_vb))
      return false;
   if(account_ledger_found)
   {
      RiskState latest_account=(!account_vb || (account_va && account_a.generation>=account_b.generation))?account_a:account_b;
      string latest_slot=(latest_account.generation%2==0)?"A":"B";
      // An older ledger without an identity marker is ambiguous. Do not
      // silently initialize a fresh account baseline over it.
      if(!RiskAccountSlotIdentityValid(account_prefix,latest_slot,latest_account.generation)) return false;
   }

   datetime today=RiskServerDayBoundary();
   datetime current_bar=iTime(g_cfg.symbol,g_cfg.tf_exec,0);
   double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(today<=0 || current_bar<=0 || !MathIsValidNumber(equity) || equity<=0.0) return false;

   bool symbol_found=(symbol_va || symbol_vb);
   if(symbol_found) g_risk=(!symbol_vb || (symbol_va && symbol_a.generation>=symbol_b.generation))?symbol_a:symbol_b;
   else ZeroMemory(g_risk);

   bool legacy_uncertain=false;
   if(account_ledger_found)
   {
      RiskState account_state=(!account_vb || (account_va && account_a.generation>=account_b.generation))?account_a:account_b;
      RiskCopyAccountFields(g_risk,account_state);
   }
   else
   {
      if(account_any) return false;
      RiskState migrated_account,migrated_symbol;
      bool migrated_symbol_found=false;
      if(RiskLegacyAggregate(today,symbol_prefix,migrated_account,migrated_symbol,
                             migrated_symbol_found,legacy_uncertain))
      {
         if(!symbol_found && migrated_symbol_found)
         {
            g_risk=migrated_symbol;
            symbol_found=true;
         }
         if(!symbol_found && !allow_explicit_bootstrap) return false;
         RiskCopyAccountFields(g_risk,migrated_account);
         account_ledger_found=true;
      }
      else
      {
         string legacy_prefixes[];
         int legacy_count=RiskCollectLegacyLedgerPrefixes(legacy_prefixes);
         if(legacy_count<0 || legacy_count>0 || !allow_explicit_bootstrap) return false;
         ZeroMemory(g_risk);
         g_risk.start_of_day_equity=equity;
         g_risk.peak_equity=equity;
         g_risk.initial_equity=equity;
         g_risk.adaptive_high_water=equity;
         g_risk.adaptive_last_equity=equity;
         g_risk.daily_locked=false;
         g_risk.total_locked=false;
         g_risk.last_day=today;
      }
   }

   // A validated shared account ledger is sufficient authority to seed a new
   // per-symbol opportunity record; explicit bootstrap is needed only when
   // no account-wide risk history exists at all.
   if(!symbol_found && !allow_explicit_bootstrap && !account_ledger_found) return false;
   if(!symbol_found)
   {
      g_risk.last_opportunity_bar=0;
      g_risk.last_opportunity_id=0;
      g_risk.last_opportunity_outcome=0;
      g_risk.generation=0;
   }
   if(g_risk.last_day<=0 || g_risk.last_day>today ||
      (g_risk.last_opportunity_bar>0 && g_risk.last_opportunity_bar>current_bar)) return false;
   int legacy_opportunity_status=RiskLegacyOpportunityStatus();
   if(legacy_opportunity_status<0) return false;
   if(legacy_uncertain || legacy_opportunity_status>0)
   {
      // Old ambiguous intents cannot be automatically attributed to a full
      // execution record. Preserve the global admission lock for owner review.
      GlobalVariableSet(RiskOpportunityLockKey(),-1.0);
      g_risk_lock_owned=false;
      g_risk_lock_token=0.0;
      return false;
   }

   g_risk.initialized=true;
   g_risk.persistence_ok=true;
   if(!RiskPersist()) return false;
   return true;
}

bool RiskInit(const bool allow_explicit_bootstrap=false)
{
   if(!RiskAcquireAccountLock()) return false;
   bool ok=RiskInitLocked(allow_explicit_bootstrap);
   if(g_risk_lock_owned && !RiskReleaseAccountLock()) return false;
   return ok;
}

bool RiskBeginOpportunity(const datetime boundary,long &decision_id)
{
   decision_id=0;
   if(!g_risk.initialized || !g_risk.persistence_ok || boundary<=0 ||
      g_risk.last_opportunity_outcome==RISK_OP_RESERVED ||
      g_risk.last_opportunity_outcome==RISK_OP_UNCERTAIN ||
      boundary<=g_risk.last_opportunity_bar) return false;
   if(!RiskAcquireAccountLock()) return false;
   if(!RiskAccountRefresh())
   {
      g_risk.persistence_ok=false;
      return false; // retain the admission lock on an unreadable shared ledger
   }
   if(!RiskSymbolRefresh())
   {
      g_risk.persistence_ok=false;
      return false; // retain the admission lock on an unreadable symbol opportunity ledger
   }
   if(g_risk.last_opportunity_outcome==RISK_OP_RESERVED ||
      g_risk.last_opportunity_outcome==RISK_OP_UNCERTAIN ||
      boundary<=g_risk.last_opportunity_bar)
   {
      RiskReleaseAccountLock();
      return false;
   }
   long suffix=RiskScopeHash(RiskLedgerPrefix())%1000000;
   decision_id=(long)boundary*1000000+suffix;
   if(decision_id<=0) return false;
   g_risk.last_opportunity_bar=boundary;
   g_risk.last_opportunity_id=decision_id;
   g_risk.last_opportunity_outcome=RISK_OP_RESERVED;
   if(!RiskPersist()) return false;
   g_risk_opportunity_inflight=true;
   return true;
}

bool RiskCompleteOpportunity(const int outcome)
{
   if(!g_risk_opportunity_inflight || g_risk.last_opportunity_outcome!=RISK_OP_RESERVED ||
      outcome<RISK_OP_REJECTED || outcome>RISK_OP_SHADOW) return false;
   g_risk.last_opportunity_outcome=outcome;
   g_risk_opportunity_inflight=false;
   if(!RiskPersist()) return false;
   // Keep a crashed/uncertain attempt locked for explicit reconciliation.
   if(outcome==RISK_OP_UNCERTAIN) return true;
   return RiskReleaseAccountLock();
}

bool RiskTick()
{
   if(!g_risk.initialized) return false;
   bool acquired_here=!g_risk_lock_owned;
   if(!RiskAcquireAccountLock()) return false; // another chart owns the account admission/update lock
   if(!RiskAccountRefresh())
   {
      g_risk.persistence_ok=false;
      if(acquired_here) RiskReleaseAccountLock();
      return false;
   }
   double eq=AccountInfoDouble(ACCOUNT_EQUITY);
   if(!MathIsValidNumber(eq) || eq<=0.0)
   {
      g_risk.persistence_ok=false;
      if(acquired_here) RiskReleaseAccountLock();
      return false;
   }
   bool changed=false;
   if(eq>g_risk.peak_equity) { g_risk.peak_equity=eq; changed=true; }
   datetime today=RiskServerDayBoundary();
   if(today<=0)
   {
      g_risk.persistence_ok=false;
      if(acquired_here) RiskReleaseAccountLock();
      return false;
   }
   if(today!=g_risk.last_day)
   {
      // TimeCurrent may not advance during a market closure. The first quote
      // on the new server date can therefore arrive only after a gap move. Do
      // not baseline to that post-gap equity and erase the intervening loss;
      // carry forward the last persisted observation as a conservative proxy
      // for the unobserved day boundary.
      double rollover_baseline=g_risk.adaptive_last_equity;
      if(!MathIsValidNumber(rollover_baseline) || rollover_baseline<=0.0)
      {
         g_risk.persistence_ok=false;
         if(acquired_here) RiskReleaseAccountLock();
         return false;
      }
      g_risk.last_day=today;
      g_risk.start_of_day_equity=rollover_baseline;
      g_risk.daily_locked=false;
      changed=true;
   }
   double daily_loss_pct=(g_risk.start_of_day_equity-eq)/g_risk.start_of_day_equity*100.0;
   double dd_pct=(g_risk.peak_equity-eq)/g_risk.peak_equity*100.0;
   if(g_cfg.daily_loss_pct>0.0 && daily_loss_pct>=g_cfg.daily_loss_pct && !g_risk.daily_locked)
      { g_risk.daily_locked=true; changed=true; }
   if(g_cfg.total_dd_pct>0.0 && dd_pct>=g_cfg.total_dd_pct && !g_risk.total_locked)
      { g_risk.total_locked=true; changed=true; }
   bool ok=changed ? RiskPersist(false) : g_risk.persistence_ok;
   bool released=true;
   if(acquired_here) released=RiskReleaseAccountLock();
   return ok && released;
}

bool RiskAllows(const AmigoConfig &cfg, string &reason)
{
   if(!g_risk.initialized || !g_risk.persistence_ok)
   {
      reason = "RISK_LEDGER_UNAVAILABLE";
      return false;
   }
   if(!g_risk_opportunity_inflight &&
      (g_risk.last_opportunity_outcome==RISK_OP_RESERVED ||
       g_risk.last_opportunity_outcome==RISK_OP_UNCERTAIN))
   {
      reason="OPPORTUNITY_RECOVERY_AMBIGUOUS";
      return false;
   }
   if(g_risk.daily_locked)
   {
      reason = "DAILY_LOCK";
      return false;
   }
   if(g_risk.total_locked)
   {
      reason = "TOTAL_DD_LOCK";
      return false;
   }
   if(!cfg.shadow_only && !MQLInfoInteger(MQL_TRADE_ALLOWED))
   {
      reason = "TRADE_NOT_ALLOWED";
      return false;
   }
   if(!cfg.shadow_only && !AccountInfoInteger(ACCOUNT_TRADE_EXPERT))
   {
      reason = "EXPERT_DISABLED";
      return false;
   }
   reason = "";
   return true;
}

#include <Account Execution Engine.mqh>

//--- Position size per Math Spec §24.2 (Unified with Account Execution Engine)
double ComputeLotSize(string symbol, double entry, double stop, double risk_pct,
                      double &risk_actual_out, string &err)
{
   risk_actual_out = 0.0;
   err = "";

   AccountExecutionEnvelope env = AccountExecutionEvaluate(
      symbol, +1, entry, stop, entry + MathAbs(entry - stop), risk_pct, g_cfg, ACTION_TRADE
   );

   if(env.final_action != ACTION_TRADE)
   {
      err = env.reason;
      return 0.0;
   }

   risk_actual_out = env.actual_risk;
   return env.executable_volume;
}

//--- Stop selection per Math Spec §24.4
double SelectStop(string symbol, int direction, double entry,
                  double structural_invalid, double atr)
{
   double sl = 0.0;

   if(direction == +1)
   {
      double fallback = entry - 1.5 * atr;
      if(structural_invalid > 0.0 && structural_invalid < entry)
         sl = MathMin(structural_invalid, entry - 1.0 * atr);
      else
         sl = fallback;
   }
   else
   {
      double fallback = entry + 1.5 * atr;
      if(structural_invalid > entry && structural_invalid > 0.0)
         sl = MathMax(structural_invalid, entry + 1.0 * atr);
      else
         sl = fallback;
   }

   double stops_level = (double)SymbolInfoInteger(symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double point       = SymbolInfoDouble(symbol, SYMBOL_POINT);
   double min_dist    = stops_level * point;

   if(min_dist > 0.0)
   {
      if(direction == +1 && (entry - sl) < min_dist) sl = entry - min_dist;
      if(direction == -1 && (sl - entry) < min_dist) sl = entry + min_dist;
   }

   return NormalizeDouble(sl, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS));
}

//+------------------------------------------------------------------+
//| Account-Aware Adaptive Stop-Loss Engine (Prompts §1-§19)          |
//+------------------------------------------------------------------+
AdaptiveSLResult EvaluateAdaptiveStop(string symbol, int direction, double entry,
                                      double original_sl, double target,
                                      double structural_invalid, double atr,
                                      double target_risk_pct, const AmigoConfig &cfg)
{
   AdaptiveSLResult res;
   ZeroMemory(res);
   res.status               = NO_VALID_SL;
   res.original_sl          = original_sl;
   res.original_stop_dist   = MathAbs(entry - original_sl);
   res.max_account_stop_dist= 0.0;
   res.candidate_sl         = 0.0;
   res.candidate_stop_dist  = 0.0;
   res.selected_sl          = original_sl;
   res.selected_stop_dist   = res.original_stop_dist;
   res.rr                   = (res.original_stop_dist > 0.0) ? (MathAbs(target - entry) / res.original_stop_dist) : 0.0;
   res.reason               = "UNINITIALIZED";

   //--- Retrieve live symbol properties
   double tick_sz  = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
   double tick_val = AccountSymbolLossTickValue(symbol);
   double vol_min  = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double vol_max  = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
   double vol_step = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
   double point    = SymbolInfoDouble(symbol, SYMBOL_POINT);
   long   stops_lvl= SymbolInfoInteger(symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double min_stop_dist = stops_lvl * point;
   int    digits   = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);

   double equity = AccountInfoDouble(ACCOUNT_EQUITY);

   //--- Fail closed on invalid symbol/account economics
   double min_valid_volume=AccountVolumeCeilToStep(vol_min,vol_step);
   double max_valid_volume=AccountVolumeFloorToStep(vol_max,vol_step);
   if(!MathIsValidNumber(tick_sz) || tick_sz<=0.0 || !MathIsValidNumber(tick_val) || tick_val<=0.0 ||
      !MathIsValidNumber(vol_min) || vol_min<=0.0 || !MathIsValidNumber(vol_max) || vol_max<vol_min ||
      !MathIsValidNumber(vol_step) || vol_step<=0.0 || min_valid_volume<=0.0 ||
      max_valid_volume<min_valid_volume || !MathIsValidNumber(equity) || equity<=0.0 ||
      !MathIsValidNumber(res.original_stop_dist) || res.original_stop_dist<=0.0)
   {
      res.status = ADAPTIVE_SL_REJECTED;
      res.reason = "INVALID_SYMBOL_OR_ACCOUNT_ECONOMICS";
      return res;
   }

   double target_risk_amt = equity * (target_risk_pct / 100.0);
   double max_distortion  = (cfg.max_allowed_distortion > 0.0) ? cfg.max_allowed_distortion : 1.0;
   double max_risk_allowed= target_risk_amt * max_distortion;

   //--- Calculate maximum stop distance that minimum executable volume can support
   double val_per_unit = (tick_val / tick_sz);
   res.max_account_stop_dist = max_risk_allowed / (min_valid_volume * val_per_unit);

   //--- 1. Is original SL executable within small account risk ceiling?
   if(res.original_stop_dist <= res.max_account_stop_dist)
   {
      res.status      = ORIGINAL_SL_EXECUTABLE;
      res.selected_sl = original_sl;
      res.selected_stop_dist = res.original_stop_dist;
      res.reason      = "ORIGINAL_SL_EXECUTABLE";
      return res;
   }

   //--- 2. Adaptation is REQUIRED
   res.status = ADAPTIVE_SL_REQUIRED;

   //--- Retrieve legitimate strategy-derived SL candidates
   //--- Candidate A: Structural swing point (if available, tighter than original, and valid side of entry)
   //--- Candidate B: 1.0 * ATR stop (existing strategy volatility bound)
   double cand_a = 0.0;
   double cand_b = 0.0;

   if(direction == +1)
   {
      if(structural_invalid > 0.0 && structural_invalid < entry && structural_invalid > original_sl)
         cand_a = structural_invalid;
      if(atr > 0.0)
         cand_b = entry - 1.0 * atr;
   }
   else
   {
      if(structural_invalid > entry && structural_invalid < original_sl)
         cand_a = structural_invalid;
      if(atr > 0.0)
         cand_b = entry + 1.0 * atr;
   }

   double candidates[2];
   candidates[0] = cand_a;
   candidates[1] = cand_b;

   //--- Evaluate candidates sequentially (preserving strategy structural hierarchy: Structure > ATR)
   for(int i = 0; i < 2; i++)
   {
      double c_sl = candidates[i];
      if(c_sl <= 0.0) continue;

      c_sl = NormalizeDouble(c_sl, digits);
      double c_dist = MathAbs(entry - c_sl);

      // Rule 1: Correct side of entry (Long: SL < entry, Short: SL > entry)
      if(direction == +1 && c_sl >= entry) continue;
      if(direction == -1 && c_sl <= entry) continue;

      // Rule 2: Non-zero stop distance
      if(c_dist <= 0.0) continue;

      // Rule 3: Broker minimum stop distance
      if(min_stop_dist > 0.0 && c_dist < min_stop_dist) continue;

      // Rule 4: Must be within account-compatible maximum distance
      if(c_dist > res.max_account_stop_dist) continue;

      // Rule 5: Strategy minimum RR requirement (e.g. 1:2.0 or cfg.partial_rr)
      double cand_rr = (c_dist > 0.0) ? (MathAbs(target - entry) / c_dist) : 0.0;
      double min_rr  = (cfg.partial_rr > 0.0) ? cfg.partial_rr : 2.0;
      if(cand_rr < min_rr) continue;

      //--- Found valid strategy-derived adaptive candidate!
      res.status              = ADAPTIVE_SL_ACCEPTED;
      res.candidate_sl        = c_sl;
      res.candidate_stop_dist = c_dist;
      res.selected_sl         = c_sl;
      res.selected_stop_dist  = c_dist;
      res.rr                  = cand_rr;
      res.reason              = (i == 0) ? "VALID_STRATEGY_STRUCTURE" : "VALID_STRATEGY_ATR";
      return res;
   }

   //--- No valid strategy-derived adaptive SL found
   res.status   = ADAPTIVE_SL_REJECTED;
   res.selected_sl = original_sl;
   res.selected_stop_dist = res.original_stop_dist;
   res.reason   = "NO_VALID_ADAPTIVE_SL";
   return res;
}
//+------------------------------------------------------------------+
