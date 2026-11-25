#ifndef AMIGO_INCLUDE_POSITIONRECOVERY_MQH
#define AMIGO_INCLUDE_POSITIONRECOVERY_MQH
//+------------------------------------------------------------------+
//| PositionRecovery.mqh - Versioned Persistent Position State &     |
//| Multi-Horizon Lifecycle Reconciliation Engine for AMIGO          |
//+------------------------------------------------------------------+
#property strict

#include <Contracts header.mqh>
#include <Configuration.mqh>
#include <Logger.mqh>

#define AMIGO_STATE_SCHEMA_VERSION 106
#define AMIGO_STATE_SCHEMA_LEGACY   104
#define AMIGO_STATE_SCHEMA_V103     103
#define AMIGO_STATE_LEGACY_PRIMARY "Amigo_positions.dat"
#define AMIGO_STATE_LEGACY_TEMP    "Amigo_positions.tmp"
#define AMIGO_STATE_MAX_POSITIONS  64
#define AMIGO_STATE_HEADER_BYTES   76
#define AMIGO_STATE_HEADER_V104    56
#define AMIGO_STATE_HEADER_V103    48
#define AMIGO_STATE_RECORD_BYTES   164
#define AMIGO_STATE_RECORD_V103    120

#define AMIGO_STATE_HASH_MOD       2147483647

// Set during successful reconciliation when any broker stop is absent or
// weaker than the persisted ratchet. OnInit quarantines entry admission while
// the timer-driven manager attempts a verified repair.
bool g_position_protection_repair_required=false;

long PositionStateHashMix(const long hash,const long value)
{
   long normalized=value%AMIGO_STATE_HASH_MOD;
   if(normalized<0) normalized+=AMIGO_STATE_HASH_MOD;
   return (hash*16777619+normalized)%AMIGO_STATE_HASH_MOD;
}

long PositionStateQuantize(const double value)
{
   if(!MathIsValidNumber(value) || MathAbs(value)>100000000.0) return -1;
   return (long)MathRound(value*1000000.0);
}

long PositionStateHeaderChecksum(const int schema,const long magic,const int count,
                                 const long saved_time,const long login,
                                 const long server_hash,const long symbol_hash,
                                 const long currency_hash,const int margin_mode,
                                 const int trade_mode,const int config_version)
{
   long hash=146959810;
   hash=PositionStateHashMix(hash,schema);
   hash=PositionStateHashMix(hash,magic);
   hash=PositionStateHashMix(hash,count);
   hash=PositionStateHashMix(hash,saved_time);
   hash=PositionStateHashMix(hash,login);
   hash=PositionStateHashMix(hash,server_hash);
   hash=PositionStateHashMix(hash,symbol_hash);
   hash=PositionStateHashMix(hash,currency_hash);
   hash=PositionStateHashMix(hash,margin_mode);
   hash=PositionStateHashMix(hash,trade_mode);
   hash=PositionStateHashMix(hash,config_version);
   return hash;
}

long PositionStateRecordChecksum(const PositionState &p)
{
   long hash=146959810;
   long values[23];
   values[0]=(long)p.position_id;
   values[1]=p.direction;
   values[2]=PositionStateQuantize(p.entry);
   values[3]=PositionStateQuantize(p.initial_stop);
   values[4]=PositionStateQuantize(p.initial_target);
   values[5]=PositionStateQuantize(p.initial_atr);
   values[6]=PositionStateQuantize(p.initial_risk_per_unit);
   values[7]=p.partial_done?1:0;
   values[8]=PositionStateQuantize(p.current_stop);
   values[9]=p.be_activated?1:0;
   values[10]=PositionStateQuantize(p.be_trigger_price);
   values[11]=PositionStateQuantize(p.last_applied_stop);
   values[12]=(int)p.trailing_mode;
   values[13]=(int)p.horizon;
   values[14]=(long)p.opened;
   values[15]=p.opened_bar_count;
   values[16]=PositionStateQuantize(p.initial_volume);
   values[17]=PositionStateQuantize(p.current_volume);
   values[18]=PositionStateQuantize(p.partial_rr);
   values[19]=PositionStateQuantize(p.partial_fraction);
   values[20]=PositionStateQuantize(p.trail_atr_mult);
   values[21]=PositionStateQuantize(p.trail_activate_r);
   values[22]=p.session_end_hour;
   for(int i=0;i<23;i++)
   {
      if(values[i]<0 && i!=1) return -1;
      hash=PositionStateHashMix(hash,values[i]);
   }
   return hash;
}

// Read back a complete serialized record and compare the payload itself with
// the state being committed. Checking only the checksum trailer could miss a
// failed/corrupt field write when the trailer was written successfully.
bool PositionStateFileRecordMatchesExpected(const int handle,const PositionState &expected)
{
   PositionState actual;
   ZeroMemory(actual);
   actual.position_id=(ulong)FileReadLong(handle);
   actual.direction=FileReadInteger(handle,INT_VALUE);
   actual.entry=FileReadDouble(handle);
   actual.initial_stop=FileReadDouble(handle);
   actual.initial_target=FileReadDouble(handle);
   actual.initial_atr=FileReadDouble(handle);
   actual.initial_risk_per_unit=FileReadDouble(handle);
   int partial_done=FileReadInteger(handle,INT_VALUE);
   actual.current_stop=FileReadDouble(handle);
   int be_activated=FileReadInteger(handle,INT_VALUE);
   actual.be_trigger_price=FileReadDouble(handle);
   actual.last_applied_stop=FileReadDouble(handle);
   actual.trailing_mode=(ENUM_TRAILING_MODE)FileReadInteger(handle,INT_VALUE);
   actual.horizon=(ENUM_HORIZON)FileReadInteger(handle,INT_VALUE);
   actual.opened=(datetime)FileReadLong(handle);
   actual.opened_bar_count=FileReadInteger(handle,INT_VALUE);
   actual.initial_volume=FileReadDouble(handle);
   actual.current_volume=FileReadDouble(handle);
   actual.partial_rr=FileReadDouble(handle);
   actual.partial_fraction=FileReadDouble(handle);
   actual.trail_atr_mult=FileReadDouble(handle);
   actual.trail_activate_r=FileReadDouble(handle);
   actual.session_end_hour=FileReadInteger(handle,INT_VALUE);
   long stored_checksum=FileReadLong(handle);
   actual.partial_done=(partial_done==1);
   actual.be_activated=(be_activated==1);

   if((partial_done!=0 && partial_done!=1) ||
      (be_activated!=0 && be_activated!=1) ||
      actual.position_id!=expected.position_id || actual.direction!=expected.direction ||
      actual.entry!=expected.entry || actual.initial_stop!=expected.initial_stop ||
      actual.initial_target!=expected.initial_target || actual.initial_atr!=expected.initial_atr ||
      actual.initial_risk_per_unit!=expected.initial_risk_per_unit ||
      actual.partial_done!=expected.partial_done || actual.current_stop!=expected.current_stop ||
      actual.be_activated!=expected.be_activated ||
      actual.be_trigger_price!=expected.be_trigger_price ||
      actual.last_applied_stop!=expected.last_applied_stop ||
      actual.trailing_mode!=expected.trailing_mode || actual.horizon!=expected.horizon ||
      actual.opened!=expected.opened || actual.opened_bar_count!=expected.opened_bar_count ||
      actual.initial_volume!=expected.initial_volume ||
      actual.current_volume!=expected.current_volume ||
      actual.partial_rr!=expected.partial_rr ||
      actual.partial_fraction!=expected.partial_fraction ||
      actual.trail_atr_mult!=expected.trail_atr_mult ||
      actual.trail_activate_r!=expected.trail_activate_r ||
      actual.session_end_hour!=expected.session_end_hour ||
      stored_checksum!=PositionStateRecordChecksum(actual) ||
      stored_checksum!=PositionStateRecordChecksum(expected))
      return false;
   return true;
}

long PositionStateIdentityHash(const string value)
{
   long hash=146959810;
   for(int i=0;i<StringLen(value);i++)
      hash=(hash*16777619+(long)StringGetCharacter(value,i))%2147483647;
   return hash;
}

bool PositionStatePaths(const AmigoConfig &cfg,string &primary,string &temp,
                        long &login,long &server_hash,long &symbol_hash,
                        long &currency_hash,int &margin_mode,int &trade_mode,
                        int &config_version)
{
   login=AccountInfoInteger(ACCOUNT_LOGIN);
   string server=AccountInfoString(ACCOUNT_SERVER);
   string symbol=cfg.symbol;
   string currency=AccountInfoString(ACCOUNT_CURRENCY);
   margin_mode=(int)AccountInfoInteger(ACCOUNT_MARGIN_MODE);
   trade_mode=(int)AccountInfoInteger(ACCOUNT_TRADE_MODE);
   config_version=Amigo_SCHEMA_VERSION;
   if(login<=0 || cfg.magic_number==0 || server=="" || symbol=="" || currency=="" ||
      margin_mode<0 || trade_mode<0 || config_version<=0) return false;
   server_hash=PositionStateIdentityHash(server);
   symbol_hash=PositionStateIdentityHash(symbol);
   currency_hash=PositionStateIdentityHash(currency);
   if(server_hash<=0 || symbol_hash<=0 || currency_hash<=0) return false;
   string stem=StringFormat("Amigo_%I64d_%I64u_%I64d_%I64d",login,cfg.magic_number,server_hash,symbol_hash);
   primary=stem+".dat";
   temp=stem+".tmp";
   return true;
}

// Lifetime ownership of this terminal-local position-state namespace.
// No sharing flags: cooperating candidate instances must acquire this handle
// before recovery/management. This is not proof of crash durability or a
// cross-terminal/account-wide execution lease; legacy code does not cooperate.
int g_position_owner_handle=INVALID_HANDLE;
string g_position_owner_path="";
string g_position_owner_server="",g_position_owner_currency="";
int g_position_owner_margin=-1,g_position_owner_trade=-1;

bool PositionStateOwnerMatches(const AmigoConfig &cfg)
{
   string primary,temp;
   long login=0,server=0,symbol=0,currency=0;
   int margin=-1,trade=-1,version=0;
   if(g_position_owner_handle==INVALID_HANDLE ||
      !PositionStatePaths(cfg,primary,temp,login,server,symbol,currency,margin,trade,version) ||
      g_position_owner_path!=primary+".owner" ||
      g_position_owner_server!=AccountInfoString(ACCOUNT_SERVER) ||
      g_position_owner_currency!=AccountInfoString(ACCOUNT_CURRENCY) ||
      g_position_owner_margin!=margin || g_position_owner_trade!=trade) return false;
   ResetLastError();
   ulong offset=FileTell(g_position_owner_handle);
   return GetLastError()==0 && offset==0; // owner handle never reads or writes
}

bool PositionStateOwnerAcquire(const AmigoConfig &cfg)
{
   if(g_position_owner_handle!=INVALID_HANDLE) return false;
   string primary,temp;
   long login=0,server=0,symbol=0,currency=0;
   int margin=-1,trade=-1,version=0;
   if(!PositionStatePaths(cfg,primary,temp,login,server,symbol,currency,margin,trade,version)) return false;
   string path=primary+".owner";
   int handle=FileOpen(path,FILE_READ|FILE_WRITE|FILE_BIN);
   if(handle==INVALID_HANDLE) return false;
   g_position_owner_handle=handle;
   g_position_owner_path=path;
   g_position_owner_server=AccountInfoString(ACCOUNT_SERVER);
   g_position_owner_currency=AccountInfoString(ACCOUNT_CURRENCY);
   g_position_owner_margin=margin; g_position_owner_trade=trade;
   if(PositionStateOwnerMatches(cfg)) return true;
   FileClose(g_position_owner_handle);
   g_position_owner_handle=INVALID_HANDLE;
   g_position_owner_path="";
   return false;
}

void PositionStateOwnerClose()
{
   if(g_position_owner_handle!=INVALID_HANDLE) FileClose(g_position_owner_handle);
   g_position_owner_handle=INVALID_HANDLE;
   g_position_owner_path="";
}

bool PositionStateLegacyPresent()
{
   return FileIsExist(AMIGO_STATE_LEGACY_PRIMARY) || FileIsExist(AMIGO_STATE_LEGACY_TEMP);
}

//+------------------------------------------------------------------+
//| Save Active Positions to Versioned Binary Persistent Storage     |
//| Checked Temp-File Write with Fail-Closed Recovery                |
//+------------------------------------------------------------------+
bool PositionSaveState(const AmigoConfig &cfg)
{
   string primary,temp;
   long login=0,server_hash=0,symbol_hash=0,currency_hash=0;
   int margin_mode=-1,trade_mode=-1,config_version=0;
   if(!PositionStatePaths(cfg,primary,temp,login,server_hash,symbol_hash,
                          currency_hash,margin_mode,trade_mode,config_version) ||
      PositionStateLegacyPresent()) return false;
   int count = ArraySize(g_positions);
   if(count < 0 || count > AMIGO_STATE_MAX_POSITIONS || FileIsExist(temp)) return false;

   // Write a temporary candidate; API success is not a crash-durability claim.
   int handle = FileOpen(temp, FILE_BIN|FILE_WRITE);
   if(handle == INVALID_HANDLE)
   {
      LogMsg(LOG_WARN, "PERSIST_SAVE", StringFormat("Failed to open temp state file %s (err=%d)", temp, GetLastError()));
      return false;
   }

   // 1. Header: identity/state metadata followed by a deterministic checksum.
   long saved_time=(long)TimeCurrent();
   FileWriteInteger(handle, AMIGO_STATE_SCHEMA_VERSION, INT_VALUE);
   FileWriteLong(handle, (long)cfg.magic_number);
   FileWriteInteger(handle, count, INT_VALUE);
   FileWriteLong(handle,saved_time);
   FileWriteLong(handle,login);
   FileWriteLong(handle,server_hash);
   FileWriteLong(handle,symbol_hash);
   FileWriteLong(handle,currency_hash);
   FileWriteInteger(handle,margin_mode,INT_VALUE);
   FileWriteInteger(handle,trade_mode,INT_VALUE);
   FileWriteInteger(handle,config_version,INT_VALUE);
   FileWriteLong(handle,PositionStateHeaderChecksum(AMIGO_STATE_SCHEMA_VERSION,
                  (long)cfg.magic_number,count,saved_time,login,server_hash,symbol_hash,
                  currency_hash,margin_mode,trade_mode,config_version));

   // 2. Records: Versioned fields per position
   for(int i = 0; i < count; i++)
   {
      FileWriteLong(handle, (long)g_positions[i].position_id);
      FileWriteInteger(handle, g_positions[i].direction, INT_VALUE);
      FileWriteDouble(handle, g_positions[i].entry);
      FileWriteDouble(handle, g_positions[i].initial_stop);
      FileWriteDouble(handle, g_positions[i].initial_target);
      FileWriteDouble(handle, g_positions[i].initial_atr);
      FileWriteDouble(handle, g_positions[i].initial_risk_per_unit);
      FileWriteInteger(handle, g_positions[i].partial_done ? 1 : 0, INT_VALUE);
      FileWriteDouble(handle, g_positions[i].current_stop);
      FileWriteInteger(handle, g_positions[i].be_activated ? 1 : 0, INT_VALUE);
      FileWriteDouble(handle, g_positions[i].be_trigger_price);
      FileWriteDouble(handle, g_positions[i].last_applied_stop);
      FileWriteInteger(handle, (int)g_positions[i].trailing_mode, INT_VALUE);
      FileWriteInteger(handle, (int)g_positions[i].horizon, INT_VALUE);
      FileWriteLong(handle, (long)g_positions[i].opened);
      FileWriteInteger(handle, g_positions[i].opened_bar_count, INT_VALUE);
      FileWriteDouble(handle, g_positions[i].initial_volume);
      FileWriteDouble(handle, g_positions[i].current_volume);
      FileWriteDouble(handle,g_positions[i].partial_rr);
      FileWriteDouble(handle,g_positions[i].partial_fraction);
      FileWriteDouble(handle,g_positions[i].trail_atr_mult);
      FileWriteDouble(handle,g_positions[i].trail_activate_r);
      FileWriteInteger(handle,g_positions[i].session_end_hour,INT_VALUE);
      long record_checksum=PositionStateRecordChecksum(g_positions[i]);
      if(record_checksum<0)
      {
         FileClose(handle);
         LogMsg(LOG_WARN,"PERSIST_SAVE","Invalid position data cannot be checksummed; previous primary preserved.");
         return false;
      }
      FileWriteLong(handle,record_checksum);
   }

   long expected_size=AMIGO_STATE_HEADER_BYTES+(long)count*AMIGO_STATE_RECORD_BYTES;
   if(FileTell(handle)!=expected_size)
   {
      FileClose(handle);
      LogMsg(LOG_WARN,"PERSIST_SAVE","Incomplete temporary state write; primary preserved.");
      return false;
   }
   FileFlush(handle);
   FileClose(handle);

   int verify=FileOpen(temp,FILE_BIN|FILE_READ);
   if(verify==INVALID_HANDLE || FileSize(verify)!=expected_size)
   {
      if(verify!=INVALID_HANDLE) FileClose(verify);
      LogMsg(LOG_WARN,"PERSIST_SAVE","Temporary state size verification failed; primary preserved.");
      return false;
   }
   // Verify actual bytes, not merely the checksum field we intended to write.
   // A matching checksum value cannot validate header fields that were skipped.
   bool header_matches=
      FileReadInteger(verify,INT_VALUE)==AMIGO_STATE_SCHEMA_VERSION &&
      FileReadLong(verify)==(long)cfg.magic_number &&
      FileReadInteger(verify,INT_VALUE)==count &&
      FileReadLong(verify)==saved_time &&
      FileReadLong(verify)==login &&
      FileReadLong(verify)==server_hash &&
      FileReadLong(verify)==symbol_hash &&
      FileReadLong(verify)==currency_hash &&
      FileReadInteger(verify,INT_VALUE)==margin_mode &&
      FileReadInteger(verify,INT_VALUE)==trade_mode &&
      FileReadInteger(verify,INT_VALUE)==config_version;
   if(!header_matches)
   {
      FileClose(verify);
      LogMsg(LOG_WARN,"PERSIST_SAVE","Temporary header payload verification failed; primary preserved.");
      return false;
   }
   long saved_header_checksum=FileReadLong(verify);
   if(saved_header_checksum!=PositionStateHeaderChecksum(AMIGO_STATE_SCHEMA_VERSION,
         (long)cfg.magic_number,count,saved_time,login,server_hash,symbol_hash,
         currency_hash,margin_mode,trade_mode,config_version))
   {
      FileClose(verify);
      LogMsg(LOG_WARN,"PERSIST_SAVE","Temporary header checksum verification failed; primary preserved.");
      return false;
   }
   for(int i=0;i<count;i++)
      if(!PositionStateFileRecordMatchesExpected(verify,g_positions[i]))
      {
         FileClose(verify);
         LogMsg(LOG_WARN,"PERSIST_SAVE","Temporary record payload/checksum verification failed; primary preserved.");
         return false;
      }
   if(FileTell(verify)!=expected_size)
   {
      FileClose(verify);
      LogMsg(LOG_WARN,"PERSIST_SAVE","Temporary record readback did not consume the expected payload; primary preserved.");
      return false;
   }
   FileClose(verify);

   // Request replacement without deleting the last complete primary first.
   // This is an API-level safeguard; MQL5 does not establish crash atomicity.
   if(!FileMove(temp, 0, primary, FILE_REWRITE))
   {
      LogMsg(LOG_WARN, "PERSIST_SAVE", StringFormat("Failed to replace primary state file with temp (err=%d); previous primary preserved if replacement was not performed.", GetLastError()));
      return false;
   }

   int primary_handle=FileOpen(primary,FILE_BIN|FILE_READ);
   if(primary_handle==INVALID_HANDLE || FileSize(primary_handle)!=expected_size)
   {
      if(primary_handle!=INVALID_HANDLE) FileClose(primary_handle);
      LogMsg(LOG_WARN,"PERSIST_SAVE","Replaced state failed size verification; recovery must remain blocked.");
      return false;
   }
   FileSeek(primary_handle,AMIGO_STATE_HEADER_BYTES-8,SEEK_SET);
   if(FileReadLong(primary_handle)!=PositionStateHeaderChecksum(AMIGO_STATE_SCHEMA_VERSION,
         (long)cfg.magic_number,count,saved_time,login,server_hash,symbol_hash,
         currency_hash,margin_mode,trade_mode,config_version))
   {
      FileClose(primary_handle);
      LogMsg(LOG_WARN,"PERSIST_SAVE","Replaced state header failed checksum readback; recovery must remain blocked.");
      return false;
   }
   for(int i=0;i<count;i++)
      if(!PositionStateFileRecordMatchesExpected(primary_handle,g_positions[i]))
      {
         FileClose(primary_handle);
         LogMsg(LOG_WARN,"PERSIST_SAVE","Replaced state record payload/checksum readback failed; recovery must remain blocked.");
         return false;
      }
   if(FileTell(primary_handle)!=expected_size)
   {
      FileClose(primary_handle);
      LogMsg(LOG_WARN,"PERSIST_SAVE","Replaced state readback did not consume the expected payload; recovery must remain blocked.");
      return false;
   }
   FileClose(primary_handle);

   return true;
}

//+------------------------------------------------------------------+
//| Load and Reconcile Positions from Persistent State on Startup    |
//| Enforces Strict Fail-Closed Verification against Broker State    |
//+------------------------------------------------------------------+
int PositionReconcileState(const AmigoConfig &cfg)
{
   bool staged_protection_repair_required=false;
   // Recovery is a one-shot startup transaction. Never merge a second recovery
   // attempt into already accepted in-memory records; ambiguous re-entry must
   // fail without changing the current state.
   if(ArraySize(g_positions)!=0)
   {
      LogMsg(LOG_WARN,"PERSIST_LOAD","Recovery called with existing in-memory position state; admission blocked.");
      return -1;
   }

   string primary,temp;
   long identity_login=0,identity_server_hash=0,identity_symbol_hash=0,identity_currency_hash=0;
   int identity_margin_mode=-1,identity_trade_mode=-1,identity_config_version=0;
   if(!PositionStatePaths(cfg,primary,temp,identity_login,identity_server_hash,identity_symbol_hash,
                          identity_currency_hash,identity_margin_mode,identity_trade_mode,
                          identity_config_version))
   {
      LogMsg(LOG_WARN,"PERSIST_LOAD","Cannot establish account/server/symbol state identity; recovery blocked.");
      return -1;
   }

   // The old fixed-name format did not identify account, server, or symbol.
   // Never ignore or guess ownership of that state during scoped recovery.
   if(PositionStateLegacyPresent())
   {
      LogMsg(LOG_WARN,"PERSIST_LOAD","Unscoped legacy state exists; ownership is ambiguous and recovery is blocked.");
      return -1;
   }

   if(!FileIsExist(primary))
   {
      if(FileIsExist(temp))
      {
         LogMsg(LOG_WARN,"PERSIST_LOAD","Temporary state exists without a primary; recovery is ambiguous.");
         return -1;
      }
      if(!cfg.shadow_only)
      {
         for(int i=0;i<PositionsTotal();i++)
         {
            ulong ticket=PositionGetTicket(i);
            if(ticket==0 || !PositionSelectByTicket(ticket))
            {
               LogMsg(LOG_WARN,"PERSIST_LOAD","Broker position enumeration is incomplete while state file is absent; recovery blocked.");
               return -1;
            }
            if(PositionGetString(POSITION_SYMBOL)==cfg.symbol &&
               (ulong)PositionGetInteger(POSITION_MAGIC)==cfg.magic_number)
            {
               LogMsg(LOG_WARN,"PERSIST_LOAD","Managed broker position exists without recovery state; admission blocked.");
               return -1;
            }
         }
      }
      LogMsg(LOG_INFO, "PERSIST_LOAD", "No prior position state found and no managed broker position detected.");
      g_position_protection_repair_required=staged_protection_repair_required;
      return 0;
   }

   if(FileIsExist(temp))
   {
      LogMsg(LOG_WARN,"PERSIST_LOAD","Both primary and temporary state exist; interrupted replacement is ambiguous.");
      return -1;
   }

   int handle = FileOpen(primary, FILE_BIN|FILE_READ);
   if(handle == INVALID_HANDLE)
   {
      LogMsg(LOG_WARN, "PERSIST_LOAD", StringFormat("Cannot open state file %s (err=%d)", primary, GetLastError()));
      return -1;
   }

   ulong file_size=FileSize(handle);
   if(file_size<AMIGO_STATE_HEADER_V103)
   {
      LogMsg(LOG_WARN,"PERSIST_LOAD","State file has truncated or trailing bytes; recovery blocked.");
      FileClose(handle);
      return -1;
   }

   // 1. Read & Validate Header
   int schema = FileReadInteger(handle, INT_VALUE);
   if(schema!=AMIGO_STATE_SCHEMA_VERSION)
   {
      LogMsg(LOG_WARN, "PERSIST_LOAD", StringFormat("State schema %d lacks the current full account/config identity. Explicit recovery is required; admission blocked.", schema));
      FileClose(handle);
      return -1;
   }

   long saved_magic = FileReadLong(handle);
   int count = FileReadInteger(handle, INT_VALUE);
   long saved_time = FileReadLong(handle);
   long saved_login=FileReadLong(handle);
   long saved_server_hash=FileReadLong(handle);
   long saved_symbol_hash=FileReadLong(handle);
   long saved_currency_hash=FileReadLong(handle);
   int saved_margin_mode=FileReadInteger(handle,INT_VALUE);
   int saved_trade_mode=FileReadInteger(handle,INT_VALUE);
   int saved_config_version=FileReadInteger(handle,INT_VALUE);
   long saved_header_checksum=FileReadLong(handle);
   long header_bytes=AMIGO_STATE_HEADER_BYTES;
   long record_bytes=AMIGO_STATE_RECORD_BYTES;
   if((ulong)saved_magic != cfg.magic_number)
   {
      LogMsg(LOG_WARN, "PERSIST_LOAD", StringFormat("Magic number mismatch in state file: file=%I64d current=%I64u. State ignored.", saved_magic, cfg.magic_number));
      FileClose(handle);
      return -1;
   }

   if(count < 0 || count > AMIGO_STATE_MAX_POSITIONS ||
      file_size!=(ulong)header_bytes+(ulong)count*(ulong)record_bytes || saved_time<=0 ||
      saved_time>(long)TimeCurrent())
   {
      LogMsg(LOG_WARN, "PERSIST_LOAD", StringFormat("Invalid or inconsistent state header/count %d. Recovery blocked.", count));
      FileClose(handle);
      return -1;
   }
   if(saved_header_checksum!=PositionStateHeaderChecksum(schema,saved_magic,count,saved_time,
         saved_login,saved_server_hash,saved_symbol_hash,saved_currency_hash,saved_margin_mode,
         saved_trade_mode,saved_config_version))
   {
      LogMsg(LOG_WARN,"PERSIST_LOAD","Header checksum mismatch; recovery blocked.");
      FileClose(handle);
      return -1;
   }
   if(saved_login!=identity_login || saved_server_hash!=identity_server_hash ||
      saved_symbol_hash!=identity_symbol_hash || saved_currency_hash!=identity_currency_hash ||
      saved_margin_mode!=identity_margin_mode || saved_trade_mode!=identity_trade_mode ||
      saved_config_version!=identity_config_version)
   {
      LogMsg(LOG_WARN,"PERSIST_LOAD","State account/server/symbol/currency/mode/config identity mismatch; recovery blocked.");
      FileClose(handle);
      return -1;
   }

   int recovered_count = 0;
   PositionState staged_positions[];

   // 2. Read each position and reconcile with broker/shadow state
   for(int k = 0; k < count; k++)
   {
      PositionState p;
      ZeroMemory(p);
      p.position_id           = (ulong)FileReadLong(handle);
      p.direction             = FileReadInteger(handle, INT_VALUE);
      p.entry                 = FileReadDouble(handle);
      p.initial_stop          = FileReadDouble(handle);
      p.initial_target        = FileReadDouble(handle);
      p.initial_atr           = FileReadDouble(handle);
      p.initial_risk_per_unit = FileReadDouble(handle);
      int partial_flag=FileReadInteger(handle,INT_VALUE);
      p.partial_done          = (partial_flag == 1);
      p.current_stop          = FileReadDouble(handle);
      int breakeven_flag=FileReadInteger(handle,INT_VALUE);
      p.be_activated          = (breakeven_flag == 1);
      p.be_trigger_price      = FileReadDouble(handle);
      p.last_applied_stop     = FileReadDouble(handle);
      p.trailing_mode         = (ENUM_TRAILING_MODE)FileReadInteger(handle, INT_VALUE);
      p.horizon               = (ENUM_HORIZON)FileReadInteger(handle, INT_VALUE);
      p.opened                = (datetime)FileReadLong(handle);
      p.opened_bar_count      = FileReadInteger(handle, INT_VALUE);
      if(schema>=102)
      {
         p.initial_volume=FileReadDouble(handle);
         p.current_volume=FileReadDouble(handle);
      }
      p.partial_rr=FileReadDouble(handle);
      p.partial_fraction=FileReadDouble(handle);
      p.trail_atr_mult=FileReadDouble(handle);
      p.trail_activate_r=FileReadDouble(handle);
      p.session_end_hour=FileReadInteger(handle,INT_VALUE);
      long saved_record_checksum=0;
      if(schema>=AMIGO_STATE_SCHEMA_VERSION) saved_record_checksum=FileReadLong(handle);

      // Initial risk is immutable lifecycle geometry, not an independent
      // positive scalar. Current stops may move through entry; initial stops
      // must remain on the original loss side of the saved entry.
      double initial_distance=MathAbs(p.entry-p.initial_stop);
      bool initial_geometry_valid=(p.direction==+1 && p.initial_stop<p.entry) ||
                                  (p.direction==-1 && p.initial_stop>p.entry);
      // A saved trigger must remain between entry and the original profit
      // target. Preserve its value; never silently rebuild it on restart.
      bool management_geometry_valid=
         (p.direction==+1 && p.initial_target>p.entry &&
          p.be_trigger_price>p.entry && p.be_trigger_price<p.initial_target) ||
         (p.direction==-1 && p.initial_target<p.entry &&
          p.be_trigger_price<p.entry && p.be_trigger_price>p.initial_target);
      if(p.position_id==0 || (p.direction!=-1 && p.direction!=1) ||
         !MathIsValidNumber(p.entry) || p.entry<=0.0 ||
         !MathIsValidNumber(p.initial_stop) || p.initial_stop<=0.0 ||
         !MathIsValidNumber(p.initial_target) || p.initial_target<=0.0 ||
         !MathIsValidNumber(p.initial_atr) || p.initial_atr<=0.0 ||
         !MathIsValidNumber(p.initial_risk_per_unit) || p.initial_risk_per_unit<=0.0 ||
         !initial_geometry_valid || !management_geometry_valid ||
         !MathIsValidNumber(initial_distance) || initial_distance<=0.0 ||
         MathAbs(p.initial_risk_per_unit-initial_distance)>MathMax(1.0,initial_distance)*0.0000000001 ||
         partial_flag<0 || partial_flag>1 || breakeven_flag<0 || breakeven_flag>1 ||
         !MathIsValidNumber(p.current_stop) || p.current_stop<0.0 ||
         !MathIsValidNumber(p.be_trigger_price) || p.be_trigger_price<0.0 ||
         !MathIsValidNumber(p.last_applied_stop) || p.last_applied_stop<0.0 ||
         (p.trailing_mode!=TRAIL_OFF && p.trailing_mode!=TRAIL_DYNAMIC_25_PERCENT &&
          p.trailing_mode!=TRAIL_ATR) ||
         (p.trailing_mode==TRAIL_ATR &&
          (!MathIsValidNumber(p.trail_atr_mult) || p.trail_atr_mult<=0.0 ||
           !MathIsValidNumber(p.trail_activate_r) || p.trail_activate_r<=0.0)) ||
         !MathIsValidNumber(p.partial_rr) || p.partial_rr<=0.0 ||
         !MathIsValidNumber(p.partial_fraction) || p.partial_fraction<=0.0 || p.partial_fraction>=1.0 ||
         !MathIsValidNumber(p.trail_atr_mult) || !MathIsValidNumber(p.trail_activate_r) ||
         p.session_end_hour<0 || p.session_end_hour>24 ||
         (int)p.horizon<HORIZON_SCALPING || (int)p.horizon>HORIZON_SWING ||
         p.opened<=0 || p.opened>(datetime)TimeCurrent() || p.opened_bar_count<0 ||
         (schema>=102 && (!MathIsValidNumber(p.initial_volume) || p.initial_volume<=0.0 ||
                          !MathIsValidNumber(p.current_volume) || p.current_volume<=0.0)))
      {
         LogMsg(LOG_WARN,"PERSIST_LOAD","Invalid position record; recovery blocked.");
         FileClose(handle);
         return -1;
      }
      if(schema>=AMIGO_STATE_SCHEMA_VERSION &&
         saved_record_checksum!=PositionStateRecordChecksum(p))
      {
         LogMsg(LOG_WARN,"PERSIST_LOAD","Position record checksum mismatch; recovery blocked.");
         FileClose(handle);
         return -1;
      }
      for(int prior=0;prior<recovered_count;prior++)
      {
         if(staged_positions[prior].position_id==p.position_id)
         {
            LogMsg(LOG_WARN,"PERSIST_LOAD","Duplicate position identity in state file; recovery blocked.");
            FileClose(handle);
            return -1;
         }
      }

      // Invariant Check: Broker Position Verification in live mode
      if(!cfg.shadow_only)
      {
         ulong current_ticket = 0;
         if(!PositionSelectByIdentifier(p.position_id, current_ticket))
         {
            LogMsg(LOG_WARN, "PERSIST_RECON", StringFormat("Persisted position identifier %I64u has no current ticket. Recovery blocked.", p.position_id));
            FileClose(handle);
            return -1;
         }

         // Verify symbol and magic number match
         string pos_sym = PositionGetString(POSITION_SYMBOL);
         ulong  pos_mag = (ulong)PositionGetInteger(POSITION_MAGIC);
         long pos_side=PositionGetInteger(POSITION_TYPE);
         bool side_matches=(p.direction==+1 && pos_side==POSITION_TYPE_BUY) ||
                           (p.direction==-1 && pos_side==POSITION_TYPE_SELL);
         if(pos_sym != cfg.symbol || pos_mag != cfg.magic_number || !side_matches)
         {
            LogMsg(LOG_WARN, "PERSIST_RECON", StringFormat("Position identifier %I64u ownership/direction conflict: sym=%s magic=%I64u side=%I64d. Recovery blocked.", p.position_id, pos_sym, pos_mag,pos_side));
            FileClose(handle);
            return -1;
         }

         // Preserve the tightest previously confirmed stop. A broker-side
         // stop that is absent or weaker must not erase the saved ratchet;
         // PositionManagerTick will attempt a validated restoration.
         double broker_stop=PositionGetDouble(POSITION_SL);
         double saved_protective_stop=p.current_stop;
         if(p.direction==+1)
         {
            if(MathIsValidNumber(p.last_applied_stop) && p.last_applied_stop>saved_protective_stop)
               saved_protective_stop=p.last_applied_stop;
            if(MathIsValidNumber(p.initial_stop) && p.initial_stop>saved_protective_stop)
               saved_protective_stop=p.initial_stop;
         }
         else
         {
            if(MathIsValidNumber(p.last_applied_stop) && p.last_applied_stop>0.0 &&
               (saved_protective_stop<=0.0 || p.last_applied_stop<saved_protective_stop))
               saved_protective_stop=p.last_applied_stop;
            if(MathIsValidNumber(p.initial_stop) && p.initial_stop>0.0 &&
               (saved_protective_stop<=0.0 || p.initial_stop<saved_protective_stop))
               saved_protective_stop=p.initial_stop;
         }
         bool broker_stop_valid=MathIsValidNumber(broker_stop) && broker_stop>0.0;
         bool broker_stop_at_least_as_protective=broker_stop_valid && saved_protective_stop>0.0 &&
            ((p.direction==+1 && broker_stop>=saved_protective_stop) ||
             (p.direction==-1 && broker_stop<=saved_protective_stop));
         if(broker_stop_at_least_as_protective)
            p.current_stop=broker_stop;
         else
         {
            staged_protection_repair_required=true;
            LogMsg(LOG_ERROR,"PERSIST_RECON","Recovered managed position has no stop or a weaker stop than the last confirmed AMIGO stop; retaining saved protection for guarded restoration.");
         }
         double broker_volume=PositionGetDouble(POSITION_VOLUME);
         if(!MathIsValidNumber(broker_volume) || broker_volume<=0.0)
         {
            LogMsg(LOG_WARN,"PERSIST_RECON","Broker returned invalid recovered position volume; recovery blocked.");
            FileClose(handle);
            return -1;
         }
         double volume_step=SymbolInfoDouble(cfg.symbol,SYMBOL_VOLUME_STEP);
         if(!MathIsValidNumber(volume_step) || volume_step<=0.0 ||
            MathAbs(broker_volume-p.current_volume)>volume_step*0.25)
         {
            LogMsg(LOG_WARN,"PERSIST_RECON",StringFormat(
               "Persisted/current broker volume mismatch for position %I64u; outcome is ambiguous and recovery is blocked.",
               p.position_id));
            FileClose(handle);
            return -1;
         }
         p.current_volume=broker_volume;
         if(p.initial_volume<=0.0) p.initial_volume=broker_volume; // legacy schema migration uses current observed volume only
         double cur_tp  = PositionGetDouble(POSITION_TP);
         if(cur_tp > 0.0) p.initial_target = cur_tp;

         // A broker stop at/beyond entry does not prove AMIGO confirmed the
         // break-even transition. Preserve only the explicitly persisted flag.
      }

      // Keep all recovered records private until the complete file and broker
      // reconciliation have succeeded. A later failure must not partially
      // mutate accepted strategy/position state.
      if(ArrayResize(staged_positions,recovered_count+1)!=recovered_count+1)
      {
         FileClose(handle);
         return -1;
      }
      staged_positions[recovered_count] = p;
      recovered_count++;

      string h_name = (p.horizon == HORIZON_SCALPING) ? "SCALPING" : (p.horizon == HORIZON_SWING) ? "SWING" : "INTRADAY";
      LogMsg(LOG_INFO, "PERSIST_RECON", StringFormat("Recovered position %I64u horizon=%s dir=%d entry=%.5f sl=%.5f be=%s partial=%s",
             p.position_id, h_name, p.direction, p.entry, p.current_stop, p.be_activated ? "YES" : "NO", p.partial_done ? "YES" : "NO"));
   }

   // The saved set must cover every current managed broker position. This
   // also catches an empty-but-valid file beside an untracked live position.
   if(!cfg.shadow_only)
   {
      for(int pos=0;pos<PositionsTotal();pos++)
      {
         ulong ticket=PositionGetTicket(pos);
         if(ticket==0 || !PositionSelectByTicket(ticket))
         {
            LogMsg(LOG_WARN,"PERSIST_RECON","Broker position enumeration is incomplete; recovery blocked.");
            FileClose(handle);
            return -1;
         }
         if(PositionGetString(POSITION_SYMBOL)!=cfg.symbol ||
            (ulong)PositionGetInteger(POSITION_MAGIC)!=cfg.magic_number) continue;
         ulong broker_id=(ulong)PositionGetInteger(POSITION_IDENTIFIER);
         bool known=false;
         for(int k=0;k<recovered_count;k++)
         {
            if(staged_positions[k].position_id==broker_id) { known=true; break; }
         }
         if(!known)
         {
            LogMsg(LOG_WARN,"PERSIST_RECON","Managed broker position has no durable state record; recovery blocked.");
            FileClose(handle);
            return -1;
         }
      }
   }

   if(FileTell(handle)<0 || (ulong)FileTell(handle)!=file_size)
   {
      LogMsg(LOG_WARN,"PERSIST_LOAD","State read did not consume the validated file exactly; recovery blocked.");
      FileClose(handle);
      return -1;
   }
   FileClose(handle);

   // Single in-memory commit point, reached only after complete structural,
   // record and broker-set validation. Array allocation is checked before
   // copying so allocation failure leaves the prior empty state unchanged.
   if(ArrayResize(g_positions,recovered_count)!=recovered_count)
   {
      LogMsg(LOG_WARN,"PERSIST_LOAD","Could not allocate the validated recovery set; admission blocked.");
      return -1;
   }
   for(int i=0;i<recovered_count;i++)
      g_positions[i]=staged_positions[i];
   g_position_protection_repair_required=staged_protection_repair_required;

   LogMsg(LOG_INFO, "PERSIST_LOAD", StringFormat("Reconciliation complete: %d active positions restored from disk.", recovered_count));
   return recovered_count;
}

#endif // AMIGO_INCLUDE_POSITIONRECOVERY_MQH
