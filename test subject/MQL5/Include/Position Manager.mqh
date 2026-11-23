#ifndef AMIGO_INCLUDE_POSITION_MANAGER_MQH
#define AMIGO_INCLUDE_POSITION_MANAGER_MQH
//+------------------------------------------------------------------+
//| PositionManager.mqh - Horizon-Aware Trade Lifecycle & Management |
//| Partials, Break-Even, Dynamic Trailing, Expiry & Session Policy  |
//+------------------------------------------------------------------+
#property strict

#include <Contracts header.mqh>
#include <Configuration.mqh>
#include <Logger.mqh>
#include <Execution Engine.mqh>   // provides CTrade g_trade

struct PositionState
{
   ulong              position_id;
   int                direction;             // +1 Buy, -1 Sell
   double             entry;
   double             initial_stop;
   double             initial_target;
   double             initial_atr;
   double             initial_risk_per_unit;  // |entry - stop|
   double             initial_volume;
   double             current_volume;
   bool               partial_done;
   double             current_stop;
   bool               be_activated;           // True once BE condition is confirmed on broker
   double             be_trigger_price;       // Horizon-specific BE trigger
   double             last_applied_stop;      // Last stop loss confirmed
   ENUM_TRAILING_MODE trailing_mode;
   ENUM_HORIZON       horizon;                // Trading horizon: SCALPING, INTRADAY, SWING
   datetime           opened;
   double             partial_rr,partial_fraction,trail_atr_mult,trail_activate_r;
   int                session_end_hour;
   int                opened_bar_count;       // Bars elapsed since entry
};

PositionState g_positions[];
bool g_position_state_faulted = false;
bool g_position_registration_persisted=false;

#include <PositionRecovery.mqh>

void PositionManagerLatchStateFault(const string reason)
{
   if(!g_position_state_faulted)
      LogMsg(LOG_ERROR, "POSITION_STATE", "Admission quarantined: " + reason);
   g_position_state_faulted = true;
}

bool PositionManagerAdmissionAllowed()
{
   return !g_position_state_faulted && !g_position_protection_repair_required;
}

// A stable position identifier does not prove that the current broker
// position still belongs to this AMIGO instance. Revalidate ownership and
// direction before any stop/close/partial-close action.
bool PositionManagerSelectedIdentityMatches(const PositionState &p,
                                             const string expected_symbol,
                                             const ulong expected_magic)
{
   if(expected_symbol=="" || expected_magic==0 || p.position_id==0 ||
      (p.direction!=-1 && p.direction!=1)) return false;
   if((ulong)PositionGetInteger(POSITION_IDENTIFIER)!=p.position_id ||
      PositionGetString(POSITION_SYMBOL)!=expected_symbol ||
      (ulong)PositionGetInteger(POSITION_MAGIC)!=expected_magic) return false;
   ENUM_POSITION_TYPE broker_type=(ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
   return (p.direction==1 && broker_type==POSITION_TYPE_BUY) ||
          (p.direction==-1 && broker_type==POSITION_TYPE_SELL);
}

// CTrade's bool reports local request validation; confirm the server result
// before mutating the in-memory lifecycle state.
bool PositionManagerTradeSucceeded(const bool call_ok, const bool allow_partial,
                                   const bool allow_no_changes = false)
{
   if(!call_ok) return false;
   uint retcode = g_trade.ResultRetcode();
   if(retcode == TRADE_RETCODE_DONE) return true;
   if(allow_no_changes && retcode == TRADE_RETCODE_NO_CHANGES) return true;
   return (allow_partial && retcode == TRADE_RETCODE_DONE_PARTIAL);
}

enum ENUM_POSITION_LOOKUP_STATUS
{
   POSITION_LOOKUP_UNKNOWN = -1,
   POSITION_LOOKUP_ABSENT = 0,
   POSITION_LOOKUP_FOUND = 1
};

// The durable position identifier is not the same field as a current ticket.
// Resolve the current ticket by identifier before calling ticket-based APIs.
// Preserve enumeration/selection failures as UNKNOWN instead of pretending
// that an uninspectable position is absent.
ENUM_POSITION_LOOKUP_STATUS PositionLookupByIdentifier(const ulong identifier,
                                                        ulong &ticket_out)
{
   ticket_out = 0;
   if(identifier == 0) return POSITION_LOOKUP_UNKNOWN;

   int total=PositionsTotal();
   if(total<0) return POSITION_LOOKUP_UNKNOWN;
   for(int i = total - 1; i >= 0; i--)
   {
      ulong candidate_ticket = PositionGetTicket(i);
      if(candidate_ticket == 0) return POSITION_LOOKUP_UNKNOWN;
      ulong candidate_id = (ulong)PositionGetInteger(POSITION_IDENTIFIER);
      if(candidate_id != identifier) continue;
      if(!PositionSelectByTicket(candidate_ticket)) return POSITION_LOOKUP_UNKNOWN;
      ticket_out = candidate_ticket;
      return POSITION_LOOKUP_FOUND;
   }
   return POSITION_LOOKUP_ABSENT;
}

bool PositionSelectByIdentifier(const ulong identifier, ulong &ticket_out)
{
   return PositionLookupByIdentifier(identifier,ticket_out)==POSITION_LOOKUP_FOUND;
}

// Clear only the recoverable startup stop-repair gate, and only after every
// accepted position has a current broker stop at least as protective as the
// saved ratchet. Persistent state must already have been saved by the caller.
bool PositionManagerClearProtectionRepairIfComplete(const AmigoConfig &cfg)
{
   if(!g_position_protection_repair_required) return true;
   for(int i=0;i<ArraySize(g_positions);i++)
   {
      ulong ticket=0;
      if(PositionLookupByIdentifier(g_positions[i].position_id,ticket)!=POSITION_LOOKUP_FOUND ||
         ticket==0 || !PositionSelectByTicket(ticket)) return false;
      if(!PositionManagerSelectedIdentityMatches(g_positions[i],cfg.symbol,cfg.magic_number))
         return false;
      double broker_stop=PositionGetDouble(POSITION_SL);
      double current_price=PositionGetDouble(POSITION_PRICE_CURRENT);
      double required_stop=g_positions[i].current_stop;
      if(!MathIsValidNumber(required_stop) || required_stop<=0.0 ||
         !MathIsValidNumber(current_price) || current_price<=0.0) return false;
      if(g_positions[i].direction==+1)
      {
         if(g_positions[i].last_applied_stop>required_stop) required_stop=g_positions[i].last_applied_stop;
         if(g_positions[i].initial_stop>required_stop) required_stop=g_positions[i].initial_stop;
         if(!MathIsValidNumber(broker_stop) || broker_stop<=0.0 || broker_stop<required_stop ||
            !MathIsValidNumber(current_price) || current_price<=broker_stop) return false;
      }
      else if(g_positions[i].direction==-1)
      {
         if(required_stop<=0.0 || (g_positions[i].last_applied_stop>0.0 && g_positions[i].last_applied_stop<required_stop))
            required_stop=g_positions[i].last_applied_stop;
         if(required_stop<=0.0 || (g_positions[i].initial_stop>0.0 && g_positions[i].initial_stop<required_stop))
            required_stop=g_positions[i].initial_stop;
         if(!MathIsValidNumber(broker_stop) || broker_stop<=0.0 || broker_stop>required_stop ||
            !MathIsValidNumber(current_price) || current_price>=broker_stop) return false;
      }
      else return false;
   }
   g_position_protection_repair_required=false;
   LogMsg(LOG_INFO,"POSITION_STOP_RESTORE","All recovered positions have broker-confirmed protective stops; entry admission repair gate cleared.");
   return true;
}


// A broker position without a server-side stop is not allowed to continue
// unmanaged. Restore only a stop previously confirmed and persisted by AMIGO,
// and only while that stop remains valid beyond broker minimum distance.
// If restoration cannot be proven from fresh broker state, quarantine entries
// and require manual intervention rather than guessing at a new stop.
bool PositionManagerRestoreMissingProtectiveStop(const int idx,ulong &ticket,
                                                 double &cur_sl,const double cur_tp,
                                                 const double cur_price,
                                                 const int digits,const double point,
                                                 const double min_stop_dist,
                                                 const AmigoConfig &cfg)
{
   if(cfg.shadow_only) return true;
   if(idx<0 || idx>=ArraySize(g_positions)) return false;

   PositionState p;
   p=g_positions[idx];
   if(!PositionManagerSelectedIdentityMatches(p,cfg.symbol,cfg.magic_number))
   {
      PositionManagerLatchStateFault(StringFormat("position %I64u ownership or direction changed before stop restoration",p.position_id));
      return false;
   }
   double recovery_stop=0.0;
   if(p.direction==+1)
   {
      if(MathIsValidNumber(p.current_stop) && p.current_stop>recovery_stop) recovery_stop=p.current_stop;
      if(MathIsValidNumber(p.last_applied_stop) && p.last_applied_stop>recovery_stop) recovery_stop=p.last_applied_stop;
      if(MathIsValidNumber(p.initial_stop) && p.initial_stop>recovery_stop) recovery_stop=p.initial_stop;
   }
   else if(p.direction==-1)
   {
      if(MathIsValidNumber(p.current_stop) && p.current_stop>0.0 &&
         (recovery_stop==0.0 || p.current_stop<recovery_stop)) recovery_stop=p.current_stop;
      if(MathIsValidNumber(p.last_applied_stop) && p.last_applied_stop>0.0 &&
         (recovery_stop==0.0 || p.last_applied_stop<recovery_stop)) recovery_stop=p.last_applied_stop;
      if(MathIsValidNumber(p.initial_stop) && p.initial_stop>0.0 &&
         (recovery_stop==0.0 || p.initial_stop<recovery_stop)) recovery_stop=p.initial_stop;
   }

   if((p.direction!=+1 && p.direction!=-1) || !MathIsValidNumber(cur_price) || cur_price<=0.0 ||
      !MathIsValidNumber(point) || point<=0.0 || !MathIsValidNumber(min_stop_dist) ||
      min_stop_dist<0.0 || !MathIsValidNumber(recovery_stop) || recovery_stop<=0.0)
   {
      PositionManagerLatchStateFault(StringFormat("position %I64u has no protective stop and no valid persisted stop for restoration",p.position_id));
      return false;
   }

   recovery_stop=NormalizeDouble(recovery_stop,digits);
   double tolerance=MathMax(point*0.5,1e-10);
   if(MathIsValidNumber(cur_sl) && cur_sl>0.0)
   {
      bool crossed=(p.direction==+1) ? cur_price<=cur_sl : cur_price>=cur_sl;
      bool at_least_as_protective=(p.direction==+1) ?
         (cur_sl+tolerance>=recovery_stop) : (cur_sl-tolerance<=recovery_stop);
      if(crossed)
      {
         PositionManagerLatchStateFault(StringFormat("position %I64u broker stop is at or beyond the current quote; broker exit state requires reconciliation",p.position_id));
         return false;
      }
      if(at_least_as_protective) return true;
   }

   bool stop_crossed=(p.direction==+1) ? cur_price<=recovery_stop : cur_price>=recovery_stop;
   double available_distance=(p.direction==+1) ? (cur_price-recovery_stop) : (recovery_stop-cur_price);
   if(stop_crossed || available_distance<min_stop_dist)
   {
      PositionManagerLatchStateFault(StringFormat("position %I64u is unprotected and its last confirmed stop cannot be safely restored; manual intervention required",p.position_id));
      return false;
   }

   LogMsg(LOG_WARN,"POSITION_STOP_RESTORE",StringFormat("position=%I64u broker stop missing; restoring last confirmed stop %.10f",p.position_id,recovery_stop));
   bool modify_call_ok=g_trade.PositionModify(ticket,recovery_stop,cur_tp);
   bool modify_reported=PositionManagerTradeSucceeded(modify_call_ok,false,true);

   // A CTrade return code alone is not state proof. Re-select by stable ID and
   // accept only a protective broker-side stop at least as tight as the saved one.
   ulong verified_ticket=0;
   ENUM_POSITION_LOOKUP_STATUS lookup=PositionLookupByIdentifier(p.position_id,verified_ticket);
   if(lookup!=POSITION_LOOKUP_FOUND || verified_ticket==0 ||
      !PositionSelectByTicket(verified_ticket))
   {
      PositionManagerLatchStateFault(StringFormat("stop restoration outcome for position %I64u is ambiguous",p.position_id));
      return false;
   }
   if(!PositionManagerSelectedIdentityMatches(p,cfg.symbol,cfg.magic_number))
   {
      PositionManagerLatchStateFault(StringFormat("position %I64u ownership or direction changed during stop restoration",p.position_id));
      return false;
   }
   double verified_stop=PositionGetDouble(POSITION_SL);
   double verified_price=PositionGetDouble(POSITION_PRICE_CURRENT);
   bool protective=(MathIsValidNumber(verified_stop) && verified_stop>0.0 &&
                    MathIsValidNumber(verified_price) && verified_price>0.0 &&
                    ((p.direction==+1 && verified_stop>=recovery_stop &&
                      verified_price-verified_stop>=min_stop_dist) ||
                     (p.direction==-1 && verified_stop<=recovery_stop &&
                      verified_stop-verified_price>=min_stop_dist)));
   if(!protective)
   {
      PositionManagerLatchStateFault(StringFormat("broker did not confirm a protective stop for position %I64u%s",p.position_id,
                                                   modify_reported?" after successful request":" after unconfirmed request"));
      return false;
   }

   g_positions[idx].current_stop=verified_stop;
   g_positions[idx].last_applied_stop=verified_stop;
   cur_sl=verified_stop;
   ticket=verified_ticket;
   if(!PositionSaveState(cfg))
   {
      PositionManagerLatchStateFault(StringFormat("restored stop for position %I64u was not durably saved",p.position_id));
      return false;
   }
   PositionManagerClearProtectionRepairIfComplete(cfg);
   if(MathAbs(verified_stop-recovery_stop)>tolerance)
      LogMsg(LOG_INFO,"POSITION_STOP_RESTORE",StringFormat("position=%I64u broker confirmed a tighter stop %.10f",p.position_id,verified_stop));
   return true;
}


//--- Round a raw volume to the broker's allowed step.
double RoundVolume(string symbol, double raw)
{
   double step = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
   double vmin = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double vmax = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
   if(!MathIsValidNumber(raw) || raw <= 0.0 ||
      !MathIsValidNumber(step) || step <= 0.0 ||
      !MathIsValidNumber(vmin) || vmin <= 0.0 ||
      !MathIsValidNumber(vmax) || vmax < vmin)
      return 0.0;

   // A partial close must never exceed the requested fraction. Rounding to
   // nearest or clamping up to volume_min can close materially more than the
   // strategy requested, especially for small positions. Untradeable dust is
   // left open and the caller skips the partial close.
   double rounding_epsilon=step*1e-9;
   double rounded=MathFloor((raw+rounding_epsilon)/step)*step;
   double max_aligned=MathFloor((vmax+rounding_epsilon)/step)*step;
   if(rounded>max_aligned) rounded=max_aligned;
   if(rounded<vmin || rounded>raw+rounding_epsilon) return 0.0;

   return rounded;
}

//+------------------------------------------------------------------+
//| Register a newly filled or synthetic position with its horizon   |
//+------------------------------------------------------------------+
bool PositionManagerHasCapacity()
{
   return ArraySize(g_positions)<AMIGO_STATE_MAX_POSITIONS;
}

void PositionManagerRegister(ulong pid, double entry, double stop, double target, double filled_volume,
                             int dir, double atr, const AmigoConfig &cfg,
                             ENUM_HORIZON horiz)
{
   g_position_registration_persisted=false;
   bool geometry_valid=(dir==+1 && stop<entry && target>entry) ||
                       (dir==-1 && stop>entry && target<entry);
   double stop_distance=MathAbs(entry-stop);
   if(pid==0 || (dir!=-1 && dir!=+1) || !MathIsValidNumber(entry) || entry<=0.0 ||
      !MathIsValidNumber(stop) || stop<=0.0 || !MathIsValidNumber(target) || target<=0.0 ||
      !MathIsValidNumber(atr) || atr<=0.0 || !MathIsValidNumber(filled_volume) || filled_volume<=0.0 ||
      !MathIsValidNumber(stop_distance) || stop_distance<=0.0 || !geometry_valid ||
      horiz<HORIZON_SCALPING || horiz>HORIZON_SWING)
   {
      PositionManagerLatchStateFault("cannot register position with invalid identity, direction, volume, geometry, ATR, or horizon");
      return;
   }
   for(int i=0; i<ArraySize(g_positions); i++)
   {
      if(g_positions[i].position_id == pid)
      {
         PositionManagerLatchStateFault(StringFormat("duplicate registration for position %I64u", pid));
         return;
      }
   }

   double tp_distance = MathAbs(target - entry);
   
   //--- Horizon-specific break-even trigger calibration:
   // SCALPING: fast break-even at 33% progress (protect short-term alpha)
   // INTRADAY: standard break-even at 50% progress (preserved baseline)
   // SWING: wide structural break-even at 60% progress (allow macro breathing room)
   double be_ratio = 0.50;
   if(horiz == HORIZON_SCALPING) be_ratio = 0.33;
   else if(horiz == HORIZON_SWING) be_ratio = 0.60;

   double be_trigger = (dir == +1) ? (entry + tp_distance * be_ratio)
                                   : (entry - tp_distance * be_ratio);

   datetime registration_now=TimeCurrent();
   datetime opened=registration_now;
   if(!cfg.shadow_only)
   {
      ulong ticket=0;
      long identifier=0,magic=0,type=0,broker_opened=0;
      string symbol="";
      if(!PositionSelectByIdentifier(pid,ticket) ||
         !PositionGetInteger(POSITION_IDENTIFIER,identifier) ||
         !PositionGetInteger(POSITION_MAGIC,magic) ||
         !PositionGetInteger(POSITION_TYPE,type) ||
         !PositionGetInteger(POSITION_TIME,broker_opened) ||
         !PositionGetString(POSITION_SYMBOL,symbol) || identifier<=0 || (ulong)identifier!=pid ||
         (ulong)magic!=cfg.magic_number || symbol!=cfg.symbol ||
         (dir==1 && type!=POSITION_TYPE_BUY) || (dir==-1 && type!=POSITION_TYPE_SELL) ||
         broker_opened<=0 || broker_opened>(long)registration_now)
      {
         PositionManagerLatchStateFault("registration cannot establish broker opening time and identity");
         return;
      }
      opened=(datetime)broker_opened;
   }
   if(!MathIsValidNumber(cfg.partial_rr) || cfg.partial_rr<=0.0 ||
      !MathIsValidNumber(cfg.partial_fraction) || cfg.partial_fraction<=0.0 || cfg.partial_fraction>=1.0 ||
      !MathIsValidNumber(cfg.trail_atr_mult) || !MathIsValidNumber(cfg.trail_activate_r) ||
      (cfg.trail_mode==TRAIL_ATR && (cfg.trail_atr_mult<=0.0 || cfg.trail_activate_r<=0.0)) ||
      cfg.session_end_hour<0 || cfg.session_end_hour>24 ||
      !PositionManagerHasCapacity() || opened<=0 ||
      !MathIsValidNumber(tp_distance) || tp_distance<=0.0 ||
      !MathIsValidNumber(be_trigger) || be_trigger<=0.0 ||
      (dir==+1 && (be_trigger<=entry || be_trigger>=target)) ||
      (dir==-1 && (be_trigger>=entry || be_trigger<=target)) ||
      (cfg.trail_mode!=TRAIL_OFF && cfg.trail_mode!=TRAIL_DYNAMIC_25_PERCENT && cfg.trail_mode!=TRAIL_ATR))
   {
      PositionManagerLatchStateFault("registration capacity, clock or management state invalid");
      return;
   }
   int n = ArraySize(g_positions);
   if(ArrayResize(g_positions, n + 1) != n + 1)
   {
      PositionManagerLatchStateFault("position-state allocation failed");
      return;
   }

   g_positions[n].position_id           = pid;
   g_positions[n].direction             = dir;
   g_positions[n].entry                 = entry;
   g_positions[n].initial_stop          = stop;
   g_positions[n].initial_target        = target;
   g_positions[n].initial_atr           = atr;
   g_positions[n].initial_risk_per_unit = MathAbs(entry - stop);
   g_positions[n].initial_volume        = filled_volume;
   g_positions[n].current_volume        = filled_volume;
   g_positions[n].partial_done          = false;
   g_positions[n].current_stop          = stop;
   g_positions[n].be_activated          = false;
   g_positions[n].be_trigger_price      = be_trigger;
   g_positions[n].last_applied_stop     = stop;
   g_positions[n].trailing_mode         = cfg.trail_mode;
   g_positions[n].horizon               = horiz;
   g_positions[n].opened                = opened;
   g_positions[n].opened_bar_count      = 0;
   g_positions[n].partial_rr=cfg.partial_rr;
   g_positions[n].partial_fraction=cfg.partial_fraction;
   g_positions[n].trail_atr_mult=cfg.trail_atr_mult;
   g_positions[n].trail_activate_r=cfg.trail_activate_r;
   g_positions[n].session_end_hour=cfg.session_end_hour;


   string h_name = (horiz == HORIZON_SCALPING) ? "SCALPING" : (horiz == HORIZON_SWING) ? "SWING" : "INTRADAY";
   LogMsg(LOG_INFO, "POSITION_MGMT", StringFormat("ticket=%I64u horizon=%s dir=%s entry=%.5f current=%.5f tp=%.5f be_trigger=%.5f be_ratio=%.2f trail_mode=%d",
          pid, h_name, (dir == +1) ? "BUY" : "SELL", entry, entry, target, be_trigger, be_ratio, (int)cfg.trail_mode));

   // Persist updated position state
   if(!PositionSaveState(cfg))
      PositionManagerLatchStateFault("position registration was not durably saved");
   else g_position_registration_persisted=true;
}

//+------------------------------------------------------------------+
//| Close or remove position by index                                |
//+------------------------------------------------------------------+
// Recover only a missing file for one untouched, fully evidenced opening fill.
// Never replace damaged/legacy files or clear the admission/risk quarantine.
bool PositionRecoverMissingFileFromJournal(const AmigoConfig &cfg)
{
   if(cfg.shadow_only || ArraySize(g_positions)!=0 || !ReconScopeStillCurrent(cfg) ||
      !ReconLoadCurrentIntent() || !g_recon_recovered_present || g_recon_recovered_stage<1)
      return false;
   string primary,temp;
   long login=0,server=0,symbol_hash=0,currency=0;
   int margin=-1,trade=-1,version=0;
   if(!PositionStatePaths(cfg,primary,temp,login,server,symbol_hash,currency,margin,trade,version) ||
      PositionStateLegacyPresent() || FileIsExist(primary) || FileIsExist(temp)) return false;
   ReconRecoveredIntent saved=g_recon_recovered;
   ReconRecoveredResponse evidence=g_recon_response;
   if(g_recon_event_present) evidence=g_recon_event_response;
   if(!ReconResponseSupportsOutcome(evidence,4) || saved.intent.symbol!=cfg.symbol ||
      saved.request.magic!=cfg.magic_number) return false;
   string reason="";
   ulong deal=evidence.result.deal,order=evidence.result.order;
   if(!ExecutionDealMatchesIntent(deal,saved.intent,saved.request,order,reason)) return false;
   long position=0;
   if(!HistoryDealGetInteger(deal,DEAL_POSITION_ID,position) || position<=0) return false;
   double volume=0.0,price=0.0,step=0.0;
   if(!SymbolInfoDouble(cfg.symbol,SYMBOL_VOLUME_STEP,step) || !MathIsValidNumber(step) || step<=0.0)
      return false;
   double tolerance=MathMax(0.00000001,step*0.000001);
   if(!ExecutionAggregateOrderDeals(saved.intent,saved.request,order,(ulong)position,deal,volume,price,reason) ||
      MathAbs(volume-saved.request.volume)>tolerance ||
      MathAbs(volume-evidence.result.volume)>tolerance ||
      !ExecutionCompletedOrderMatches(saved.intent,saved.request,order,(ulong)position,tolerance,reason))
      return false;
   int managed=0,total=PositionsTotal();
   if(total<0) return false;
   for(int i=0;i<total;i++)
   {
      if(PositionGetTicket(i)==0) return false;
      string sym=""; long magic=0,id=0;
      if(!PositionGetString(POSITION_SYMBOL,sym) || !PositionGetInteger(POSITION_MAGIC,magic) ||
         !PositionGetInteger(POSITION_IDENTIFIER,id)) return false;
      if(sym==cfg.symbol && (ulong)magic==cfg.magic_number)
      {
         if(id!=position) return false;
         managed++;
      }
   }
   if(managed!=1 || PositionsTotal()!=total || ExecutionHasManagedWorkingOrder(cfg)) return false;
   ulong ticket=0;
   double current_volume=0.0,current_entry=0.0,sl=0.0,tp=0.0;
   if(!PositionSelectByIdentifier((ulong)position,ticket) ||
      !PositionGetDouble(POSITION_VOLUME,current_volume) || !PositionGetDouble(POSITION_PRICE_OPEN,current_entry) ||
      !PositionGetDouble(POSITION_SL,sl) || !PositionGetDouble(POSITION_TP,tp) ||
      !MathIsValidNumber(current_volume) || !MathIsValidNumber(current_entry) ||
      MathAbs(current_volume-volume)>tolerance || current_entry!=price ||
      sl!=saved.request.sl || tp!=saved.request.tp) return false;
   // Preserve the original policy; cfg is used only for the current runtime scope.
   AmigoConfig management=cfg;
   management.partial_rr=saved.management.partial_rr;
   management.partial_fraction=saved.management.partial_fraction;
   management.trail_atr_mult=saved.management.trail_atr_mult;
   management.trail_activate_r=saved.management.trail_activate_r;
   management.trail_mode=saved.management.trail_mode;
   management.session_end_hour=saved.management.session_end_hour;
   if(!ReconScopeStillCurrent(cfg)) return false;
   PositionManagerRegister((ulong)position,price,saved.request.sl,saved.request.tp,volume,
                           saved.intent.direction,saved.atr,management,saved.intent.horizon);
   // Registration retains memory if persistence fails; require the exact saved
   // record readback performed by PositionSaveState before reporting success.
   if(!g_position_registration_persisted || ArraySize(g_positions)!=1 ||
      !FileIsExist(primary) || FileIsExist(temp)) return false;
   PositionManagerLatchStateFault("journal position reconstructed; risk reconciliation still required");
   return true;
}

void PositionManagerRemove(int idx, const string reason, double exit_price, const AmigoConfig &cfg)
{
   ulong pid = g_positions[idx].position_id;
   ENUM_HORIZON h = g_positions[idx].horizon;
   string h_name = (h == HORIZON_SCALPING) ? "SCALPING" : (h == HORIZON_SWING) ? "SWING" : "INTRADAY";

   LogMsg(LOG_INFO, "POSITION_EXIT", StringFormat("ticket=%I64u horizon=%s reason=%s exit_price=%.5f",
          pid, h_name, reason, exit_price));

   if(!cfg.shadow_only)
   {
      // A requested close is not complete merely because CTrade accepted it.
      // Retain lifecycle state until the server confirms the close.
      ulong current_ticket = 0;
      if(!PositionSelectByIdentifier(pid, current_ticket))
      {
         LogMsg(LOG_WARN, "POSITION_EXIT", StringFormat("ticket=%I64u close not submitted: position not selected", pid));
         PositionManagerLatchStateFault(StringFormat("close target %I64u requires reconciliation", pid));
         return;
      }
      if(!PositionManagerSelectedIdentityMatches(g_positions[idx],cfg.symbol,cfg.magic_number))
      {
         PositionManagerLatchStateFault(StringFormat("close target %I64u ownership or direction changed",pid));
         return;
      }
      bool close_call_ok = g_trade.PositionClose(current_ticket);
      if(!PositionManagerTradeSucceeded(close_call_ok, false))
      {
         LogMsg(LOG_WARN, "POSITION_EXIT", StringFormat("ticket=%I64u close unconfirmed retcode=%u", pid, g_trade.ResultRetcode()));
         PositionManagerLatchStateFault(StringFormat("close outcome for position %I64u requires reconciliation",pid));
         return;
      }
      ulong remaining_ticket=0;
      ENUM_POSITION_LOOKUP_STATUS remaining=PositionLookupByIdentifier(pid,remaining_ticket);
      if(remaining!=POSITION_LOOKUP_ABSENT)
      {
         string detail=(remaining==POSITION_LOOKUP_FOUND)?"position remains after close":"position state unavailable after close";
         LogMsg(LOG_WARN,"POSITION_EXIT",StringFormat("ticket=%I64u close response did not establish flat state: %s",pid,detail));
         PositionManagerLatchStateFault(StringFormat("%s for position %I64u",detail,pid));
         return;
      }
   }

   for(int j = idx; j < ArraySize(g_positions) - 1; j++)
      g_positions[j] = g_positions[j + 1];
   ArrayResize(g_positions, ArraySize(g_positions) - 1);
   if(!PositionSaveState(cfg))
      PositionManagerLatchStateFault("position removal was not durably saved");
}

//+------------------------------------------------------------------+
//| Active position management tick with horizon-specific lifecycle   |
//+------------------------------------------------------------------+
// -1 invalid clock/policy, 0 not due (or explicitly disabled), 1 expired.
// Server calendar dates share the same timestamp domain as position.opened.
int PositionIntradaySessionStatus(const datetime opened,const datetime now,const int end_hour)
{
   if(opened<=0 || now<opened || end_hour<0 || end_hour>24) return -1;
   if(end_hour==0) return 0; // preserve existing disabled-policy sentinel
   MqlDateTime start,current;
   if(!TimeToStruct(opened,start) || !TimeToStruct(now,current)) return -1;
   if(current.year>start.year ||
      (current.year==start.year && current.day_of_year>start.day_of_year)) return 1;
   if(current.year!=start.year || current.day_of_year!=start.day_of_year) return -1;
   return current.hour>=end_hour ? 1 : 0;
}

// Validate the policy saved with THIS trade before any timer-driven action.
// Never replace a missing horizon/policy with the newest signal/configuration.
bool PositionSavedHorizonPolicyValid(const PositionState &p,const datetime now)
{
   if(p.horizon<HORIZON_SCALPING || p.horizon>HORIZON_SWING ||
      (p.direction!=1 && p.direction!=-1) || p.opened<=0 || now<p.opened ||
      !MathIsValidNumber(p.partial_rr) || p.partial_rr<=0.0 ||
      !MathIsValidNumber(p.partial_fraction) || p.partial_fraction<=0.0 || p.partial_fraction>=1.0 ||
      !MathIsValidNumber(p.trail_atr_mult) || !MathIsValidNumber(p.trail_activate_r) ||
      p.session_end_hour<0 || p.session_end_hour>24 ||
      (p.trailing_mode!=TRAIL_OFF && p.trailing_mode!=TRAIL_DYNAMIC_25_PERCENT && p.trailing_mode!=TRAIL_ATR)) return false;
   if(p.trailing_mode==TRAIL_ATR && (p.trail_atr_mult<=0.0 || p.trail_activate_r<=0.0)) return false;
   return true;
}

void PositionManagerTick(const AmigoConfig &cfg)
{
   bool state_dirty = false;
   string sym = (StringLen(cfg.symbol) > 0) ? cfg.symbol : _Symbol;
   int    digits = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   double point  = SymbolInfoDouble(sym, SYMBOL_POINT);
   double stops_level = (double)SymbolInfoInteger(sym, SYMBOL_TRADE_STOPS_LEVEL);
   double freeze_level = (double)SymbolInfoInteger(sym, SYMBOL_TRADE_FREEZE_LEVEL);
   double min_stop_dist = stops_level * point;
   double freeze_dist   = freeze_level * point;

   datetime now_t = TimeCurrent();
   MqlDateTime dt;
   if(now_t<=0 || !TimeToStruct(now_t, dt)) return;

   // One validated quote snapshot for all synthetic positions in this timer
   // invocation. Invalid/stale prices must not manufacture shadow exits or
   // advance lifecycle state. Age is relative to broker observation time.
   MqlTick shadow_quote;
   ZeroMemory(shadow_quote);
   if(cfg.shadow_only && ArraySize(g_positions)>0)
   {
      if(!SymbolInfoTick(sym,shadow_quote) ||
         !MathIsValidNumber(shadow_quote.bid) || shadow_quote.bid<=0.0 ||
         !MathIsValidNumber(shadow_quote.ask) || shadow_quote.ask<shadow_quote.bid ||
         shadow_quote.time<=0 || shadow_quote.time>now_t ||
         cfg.stale_threshold_s<=0 || now_t-shadow_quote.time>cfg.stale_threshold_s)
         return;
   }

   for(int i = ArraySize(g_positions) - 1; i >= 0; i--)
   {
      ulong pid = g_positions[i].position_id;
      ulong position_ticket = 0;
      int   dir = g_positions[i].direction;
      ENUM_HORIZON horiz = g_positions[i].horizon;
      if(!PositionSavedHorizonPolicyValid(g_positions[i],now_t))
      {
         PositionManagerLatchStateFault(StringFormat("position %I64u saved horizon/policy invalid",pid));
         continue;
      }

      double cur_sl;
      double cur_tp;
      double cur_price;

      if(!cfg.shadow_only)
      {
         //--- Live Trading Mode: inspect active terminal position
         if(!PositionSelectByIdentifier(pid, position_ticket))
         {
            // Absence from the current position list is ambiguous (including
            // temporary selection/history failures). Keep the record and
            // quarantine new entries until explicit reconciliation.
            PositionManagerLatchStateFault(StringFormat("position %I64u unresolved during management", pid));
            continue;
         }
         if(!PositionManagerSelectedIdentityMatches(g_positions[i],sym,cfg.magic_number))
         {
            PositionManagerLatchStateFault(StringFormat("position %I64u ownership or direction changed during management",pid));
            continue;
         }

         cur_sl    = PositionGetDouble(POSITION_SL);
         cur_tp    = PositionGetDouble(POSITION_TP);
         cur_price = PositionGetDouble(POSITION_PRICE_CURRENT);
         if(!PositionManagerRestoreMissingProtectiveStop(i,position_ticket,cur_sl,cur_tp,
                                                         cur_price,digits,point,min_stop_dist,cfg))
            continue;

         // Runtime volume changes invalidate the persisted lifecycle snapshot
         // (for example, a delayed partial fill or an external/manual change).
         // Keep protective-stop recovery above this check, then quarantine any
         // mismatch before partial-close or other lifecycle actions use stale
         // state. A matching volume is refreshed by stable position identity.
         if(!PositionSelectByIdentifier(pid,position_ticket))
         {
            PositionManagerLatchStateFault(StringFormat("position %I64u volume identity unavailable during management",pid));
            continue;
         }
         if(!PositionManagerSelectedIdentityMatches(g_positions[i],sym,cfg.magic_number))
         {
            PositionManagerLatchStateFault(StringFormat("position %I64u ownership or direction changed before lifecycle action",pid));
            continue;
         }
         double broker_volume=PositionGetDouble(POSITION_VOLUME);
         double volume_step=SymbolInfoDouble(sym,SYMBOL_VOLUME_STEP);
         double volume_tolerance=(MathIsValidNumber(volume_step) && volume_step>0.0) ?
                                 volume_step*0.25 : 0.0;
         if(!MathIsValidNumber(broker_volume) || broker_volume<=0.0 ||
            !MathIsValidNumber(g_positions[i].current_volume) || g_positions[i].current_volume<=0.0 ||
            volume_tolerance<=0.0 ||
            MathAbs(broker_volume-g_positions[i].current_volume)>volume_tolerance)
         {
            LogMsg(LOG_ERROR,"POSITION_VOLUME",
                   StringFormat("position=%I64u persisted=%.8f broker=%.8f tolerance=%.8f; lifecycle quarantined",
                                pid,g_positions[i].current_volume,broker_volume,volume_tolerance));
            PositionManagerLatchStateFault(StringFormat("runtime volume mismatch for position %I64u",pid));
            continue;
         }
      }
      else
      {
         //--- Shadow Safety Mode: track synthetic position against live symbol quotes
         cur_sl    = g_positions[i].current_stop;
         cur_tp    = g_positions[i].initial_target;
         cur_price = (dir == +1) ? shadow_quote.bid : shadow_quote.ask;

         if(cur_price <= 0.0) continue;

         // Check Shadow Exit Conditions (SL / TP hit)
         if(dir == +1)
         {
            if(cur_price <= g_positions[i].current_stop)
            {
               PositionManagerRemove(i, "STOP_LOSS", cur_price, cfg);
               continue;
            }
            if(cur_tp > 0.0 && cur_price >= cur_tp)
            {
               PositionManagerRemove(i, "TAKE_PROFIT", cur_price, cfg);
               continue;
            }
         }
         else
         {
            if(cur_price >= g_positions[i].current_stop)
            {
               PositionManagerRemove(i, "STOP_LOSS", cur_price, cfg);
               continue;
            }
            if(cur_tp > 0.0 && cur_price <= cur_tp)
            {
               PositionManagerRemove(i, "TAKE_PROFIT", cur_price, cfg);
               continue;
            }
         }
      }

      //================================================================
      // HORIZON-SPECIFIC LIFECYCLE CONTROLS
      //================================================================

      // 1. SCALPING EXPIRY: Max holding period = 3600 seconds (1 hour)
      // If a scalp stalls without hitting TP or BE, exit to prevent it from becoming an unmanaged swing
      if(horiz == HORIZON_SCALPING)
      {
         int elapsed_sec = (int)(now_t - g_positions[i].opened);
         if(elapsed_sec >= 3600 && !g_positions[i].be_activated)
         {
            PositionManagerRemove(i, "SCALP_TIME_EXPIRED", cur_price, cfg);
            continue;
         }
      }

      // 2. INTRADAY SESSION POLICY: Liquidate before server session close
      // Intraday trades must not be carried across rollover into overnight sessions
      if(horiz == HORIZON_INTRADAY)
      {
         int session_status=PositionIntradaySessionStatus(g_positions[i].opened,now_t,
                                                         g_positions[i].session_end_hour);
         if(session_status<0)
         {
            PositionManagerLatchStateFault("intraday session clock or saved policy invalid");
            continue;
         }
         if(session_status==1)
         {
            PositionManagerRemove(i, "INTRADAY_SESSION_CLOSE", cur_price, cfg);
            continue;
         }
      }

      // 3. SWING PERSISTENCE: Multi-session, exempt from short-term time expiry or session closes.

      double r_unit = g_positions[i].initial_risk_per_unit;
      if(r_unit <= 0.0) continue;

      //--- Partial exit rules:
      // Scalping: 1.5R partial
      // Intraday / Swing: 2.0R partial (preserved baseline)
      double partial_rr_target = (horiz == HORIZON_SCALPING) ? 1.5 : g_positions[i].partial_rr;
      if(!g_positions[i].partial_done && PositionManagerAdmissionAllowed())
      {
         double target_partial = (dir == +1)
                                ? (g_positions[i].entry + partial_rr_target * r_unit)
                                : (g_positions[i].entry - partial_rr_target * r_unit);

         bool hit = (dir == +1) ? (cur_price >= target_partial)
                                : (cur_price <= target_partial);

         if(hit)
         {
            if(!cfg.shadow_only)
            {
               double vol = PositionGetDouble(POSITION_VOLUME);
               double raw  = vol * g_positions[i].partial_fraction;
               double part = RoundVolume(sym, raw);
               string partial_volume_reason="";

               if(part>0.0 && part<vol &&
                  ExecutionVolumeValid(sym,part,partial_volume_reason) &&
                  ExecutionVolumeValid(sym,vol-part,partial_volume_reason))
               {
                  bool partial_call_ok = g_trade.PositionClosePartial(position_ticket, part);
                  // Do not treat DONE_PARTIAL as completion of the intended
                  // reduction. The broker may have changed volume even though
                  // the requested amount was not fully closed. Re-select by
                  // stable identifier and verify the exact remaining volume
                  // before mutating lifecycle state.
                  if(PositionManagerTradeSucceeded(partial_call_ok, false))
                  {
                     ulong refreshed_ticket=0;
                     double remaining_volume=0.0;
                     double volume_step=SymbolInfoDouble(sym,SYMBOL_VOLUME_STEP);
                     double tolerance=(volume_step>0.0 ? volume_step*0.25 : 1e-8);
                     bool remaining_ok=PositionSelectByIdentifier(pid,refreshed_ticket);
                     if(remaining_ok)
                     {
                        remaining_volume=PositionGetDouble(POSITION_VOLUME);
                        remaining_ok=(PositionManagerSelectedIdentityMatches(g_positions[i],sym,cfg.magic_number) &&
                                      MathIsValidNumber(remaining_volume) && remaining_volume>0.0 &&
                                      MathAbs(remaining_volume-(vol-part))<=tolerance);
                     }
                     if(!remaining_ok)
                     {
                        LogMsg(LOG_WARN,"PARTIAL_EXIT","Server acknowledged the requested reduction but the resulting managed position volume did not match; state requires reconciliation.");
                        PositionManagerLatchStateFault(StringFormat("partial-close volume mismatch for position %I64u",pid));
                     }
                     else
                     {
                        // Partial execution can change the current position
                        // ticket while preserving its stable identifier. Use
                        // the reselected ticket for any stop management later
                        // in this same tick.
                        position_ticket = refreshed_ticket;
                        g_positions[i].partial_done = true;
                        g_positions[i].current_volume = remaining_volume;
                        state_dirty = true;
                        if(!PositionSaveState(cfg))
                           PositionManagerLatchStateFault(StringFormat("confirmed partial close for position %I64u was not saved",pid));
                        LogMsg(LOG_INFO, "PARTIAL_EXIT", StringFormat("ticket=%I64u horizon=%d vol=%.2f part=%.2f remaining=%.2f target=%.5f",
                               pid, (int)horiz, vol, part, remaining_volume, target_partial));
                     }
                  }
                  else
                  {
                     LogMsg(LOG_WARN, "PARTIAL_FAILED", StringFormat("ticket=%I64u retcode=%u", pid, g_trade.ResultRetcode()));
                     PositionManagerLatchStateFault(StringFormat("partial-close outcome requires reconciliation for position %I64u", pid));
                  }
               }
            }
            else
            {
               // Synthetic reductions must be representable by the same
               // broker volume grid as real reductions; never manufacture dust.
               double vol=g_positions[i].current_volume;
               double part=RoundVolume(sym,vol*g_positions[i].partial_fraction);
               string partial_volume_reason="";
               if(part>0.0 && part<vol &&
                  ExecutionVolumeValid(sym,part,partial_volume_reason) &&
                  ExecutionVolumeValid(sym,vol-part,partial_volume_reason))
               {
                  g_positions[i].partial_done = true;
                  g_positions[i].current_volume = vol-part;
                  state_dirty = true;
                  LogMsg(LOG_INFO, "SHADOW_PARTIAL", StringFormat("ticket=%I64u horizon=%d partial_hit=true price=%.5f part=%.8f remaining=%.8f",
                         pid, (int)horiz, cur_price,part,vol-part));
               }
            }
         }
      }

      //--- Invalid TP check guard
      double tp_distance = MathAbs(cur_tp - g_positions[i].entry);
      if(cur_tp <= 0.0 || tp_distance <= 0.0) continue;

      //================================================================
      // BREAK-EVEN LOGIC (Completely decoupled from trailing mode)
      //================================================================
      if(!g_positions[i].be_activated)
      {
         bool be_reached = (dir == +1) ? (cur_price >= g_positions[i].be_trigger_price)
                                       : (cur_price <= g_positions[i].be_trigger_price);

         if(be_reached)
         {
            double proposed_be_sl = NormalizeDouble(g_positions[i].entry, digits);
            bool   stops_ok       = (dir == +1) ? ((cur_price - proposed_be_sl) >= min_stop_dist)
                                                : ((proposed_be_sl - cur_price) >= min_stop_dist);

            if(stops_ok)
            {
               bool is_be_improvement = (dir == +1) ? (proposed_be_sl > cur_sl)
                                                    : (proposed_be_sl < cur_sl);
               if(is_be_improvement)
               {
                  bool modify_success = true;
                  if(!cfg.shadow_only)
                  {
                     bool modify_call_ok = g_trade.PositionModify(position_ticket, proposed_be_sl, cur_tp);
                     modify_success = PositionManagerTradeSucceeded(modify_call_ok, false, true);
                     if(!modify_success)
                     {
                        LogMsg(LOG_WARN, "BE_FAILED", StringFormat("ticket=%I64u retcode=%u", pid, g_trade.ResultRetcode()));
                     }
                  }

                  // ONLY mark be_activated and update state if broker confirmed (or shadow mode)
                  if(modify_success)
                  {
                     g_positions[i].be_activated      = true;
                     g_positions[i].current_stop      = proposed_be_sl;
                     g_positions[i].last_applied_stop = proposed_be_sl;
                     state_dirty = true;
                     cur_sl                           = proposed_be_sl;
                     LogMsg(LOG_INFO, "BE_ACTIVATED", StringFormat("ticket=%I64u horizon=%d entry=%.5f sl=%.5f",
                            pid, (int)horiz, g_positions[i].entry, proposed_be_sl));
                  }
               }
               else
               {
                  // The stop being at/beyond entry does not prove AMIGO's
                  // break-even transition was previously confirmed. Preserve
                  // the persisted lifecycle flag; do not infer history from
                  // the current broker stop alone.
               }
            }
         }
      }

      // If trailing is off, break-even is evaluated but trailing is skipped
      if(g_positions[i].trailing_mode == TRAIL_OFF) continue;

      //================================================================
      // DYNAMIC TRAILING STOP LOGIC (Horizon-Aware Ratchet Calibration)
      //================================================================
      if(g_positions[i].be_activated && g_positions[i].trailing_mode == TRAIL_DYNAMIC_25_PERCENT)
      {
         double profit_dist = (dir == +1) ? (cur_price - g_positions[i].entry)
                                          : (g_positions[i].entry - cur_price);
         if(profit_dist > 0.0)
         {
            // Preserve the approved 25% of favourable movement from entry
            // after confirmed break-even activation for every horizon.
            double trail_factor = 0.25;

            double trailing_dist = profit_dist * trail_factor;
            double proposed_sl   = (dir == +1) ? (cur_price - trailing_dist)
                                               : (cur_price + trailing_dist);
            proposed_sl          = NormalizeDouble(proposed_sl, digits);

            bool is_improvement = (dir == +1) ? (proposed_sl > cur_sl)
                                              : (proposed_sl < cur_sl);

            if(is_improvement)
            {
               bool stops_ok  = (dir == +1) ? ((cur_price - proposed_sl) >= min_stop_dist)
                                            : ((proposed_sl - cur_price) >= min_stop_dist);
               bool freeze_ok = (freeze_dist <= 0.0) || (MathAbs(cur_price - cur_sl) > freeze_dist);

               if(stops_ok && freeze_ok)
               {
                  bool mod_ok = true;
                  if(!cfg.shadow_only)
                  {
                     bool modify_call_ok = g_trade.PositionModify(position_ticket, proposed_sl, cur_tp);
                     mod_ok = PositionManagerTradeSucceeded(modify_call_ok, false, true);
                     if(!mod_ok)
                     {
                        LogMsg(LOG_WARN, "TRAIL_BLOCKED", StringFormat("reason=MODIFY_FAILED retcode=%u", g_trade.ResultRetcode()));
                     }
                  }
                  if(mod_ok)
                  {
                     LogMsg(LOG_INFO, "TRAIL_UPDATE", StringFormat("ticket=%I64u horizon=%d trail_factor=%.2f old_sl=%.5f new_sl=%.5f",
                            pid, (int)horiz, trail_factor, cur_sl, proposed_sl));
                     g_positions[i].current_stop      = proposed_sl;
                     g_positions[i].last_applied_stop = proposed_sl;
                     state_dirty = true;
                  }
               }
            }
         }
      }
      else if(g_positions[i].trailing_mode == TRAIL_ATR)
      {
         //--- Legacy ATR Trailing Stop (Strict broker check and stop levels applied)
         double excursion = (dir == +1) ? (cur_price - g_positions[i].entry)
                                        : (g_positions[i].entry - cur_price);

         if(excursion >= g_positions[i].trail_activate_r * r_unit)
         {
            double atr = g_positions[i].initial_atr;
            double mult = (horiz == HORIZON_SCALPING) ? 1.0 : (horiz == HORIZON_SWING) ? 2.5 : g_positions[i].trail_atr_mult;
            double proposed;
            if(dir == +1) proposed = MathMax(cur_sl, cur_price - mult * atr);
            else          proposed = MathMin(cur_sl, cur_price + mult * atr);

            proposed = NormalizeDouble(proposed, digits);

            bool is_improvement = (dir == +1) ? (proposed > cur_sl) : (proposed < cur_sl);
            if(is_improvement && (MathAbs(proposed - cur_sl) > point))
            {
               bool stops_ok  = (dir == +1) ? ((cur_price - proposed) >= min_stop_dist)
                                            : ((proposed - cur_price) >= min_stop_dist);
               bool freeze_ok = (freeze_dist <= 0.0) || (MathAbs(cur_price - cur_sl) > freeze_dist);

               if(stops_ok && freeze_ok)
               {
                  bool mod_ok = true;
                  if(!cfg.shadow_only)
                  {
                     bool modify_call_ok = g_trade.PositionModify(position_ticket, proposed, cur_tp);
                     mod_ok = PositionManagerTradeSucceeded(modify_call_ok, false, true);
                     if(!mod_ok)
                     {
                        LogMsg(LOG_WARN, "ATR_TRAIL_BLOCKED", StringFormat("reason=MODIFY_FAILED retcode=%u", g_trade.ResultRetcode()));
                     }
                  }
                  if(mod_ok)
                  {
                     LogMsg(LOG_INFO, "TRAIL_UPDATE", StringFormat("ticket=%I64u horizon=%d old_sl=%.5f new_sl=%.5f (ATR mult=%.1f)",
                            pid, (int)horiz, cur_sl, proposed, mult));
                     g_positions[i].current_stop      = proposed;
                     g_positions[i].last_applied_stop = proposed;
                     state_dirty = true;
                  }
               }
            }
         }
      }
   }

   if(state_dirty && !PositionSaveState(cfg))
      PositionManagerLatchStateFault("updated lifecycle state was not durably saved");
   else PositionManagerClearProtectionRepairIfComplete(cfg);
}
//+------------------------------------------------------------------+

#endif // AMIGO_INCLUDE_POSITION_MANAGER_MQH
