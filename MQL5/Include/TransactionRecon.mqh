#ifndef AMIGO_TRANSACTION_RECON_MQH
#define AMIGO_TRANSACTION_RECON_MQH
//+------------------------------------------------------------------+
//| TransactionRecon.mqh                                             |
//|                                                                  |
//| Transaction-stream observer; not an authoritative reconciler yet. |
//|                                                                  |
//| Per D4 REQ-037 / D3 ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â§18:                                         |
//|   * Events are logged with broker identifiers for investigation. |
//|   * This handler does NOT currently resolve an uncertain intent. |
//|   * Admission remains quarantined; no automatic retry is allowed. |
//|                                                                  |
//| The current implementation is deliberately fail-closed but       |
//| incomplete: callback logs only; write-ahead evidence added below.
//| Persistent intent matching,     |
//| partial-fill aggregation, position registration, and terminal-   |
//| restart reconciliation remain required before this can be called|
//| a completed order-state lifecycle.                               |
//+------------------------------------------------------------------+
#property strict

#include <Contracts header.mqh>
#include <Logger.mqh>
#include <Configuration.mqh>

// Write-ahead evidence journal. It does not automatically reconcile or retry.
// SQL commit success is not a verified MQL5 power-loss durability guarantee.
int g_recon_db=INVALID_HANDLE;
bool g_recon_fault=false;
long g_recon_prepared_id=0;
string g_recon_account="",g_recon_scope="";
// Daily fill accounting support: track confirmed successful fills for current broker day
long g_recon_daily_fill_count=0;
datetime g_recon_daily_fill_day=0;

// Request identifiers are session-local evidence, never restart identity.
uint g_recon_session_request=0;
long g_recon_session_intent=0;

string ReconField(const string value)
{
   return IntegerToString(StringLen(value))+":"+value;
}

string ReconCurrentAccountScope()
{
   long login=AccountInfoInteger(ACCOUNT_LOGIN);
   string server=AccountInfoString(ACCOUNT_SERVER),currency=AccountInfoString(ACCOUNT_CURRENCY);
   if(login<=0 || server=="" || currency=="") return "";
   return ReconField(StringFormat("%I64d",login))+ReconField(server)+ReconField(currency);
}

bool ReconScopeStillCurrent(const AmigoConfig &cfg)
{
   string account=ReconCurrentAccountScope();
   if(account=="" || account!=g_recon_account || cfg.symbol=="") return false;
   string scope=account+ReconField(StringFormat("%I64u",cfg.magic_number))+ReconField(cfg.symbol);
   return scope==g_recon_scope;
}

void ReconJournalClose()
{
   if(g_recon_db!=INVALID_HANDLE) DatabaseClose(g_recon_db);
   g_recon_db=INVALID_HANDLE;
}

bool ReconJournalFail()
{
   g_recon_fault=true;
   if(g_recon_db!=INVALID_HANDLE) DatabaseTransactionRollback(g_recon_db);
   return false;
}

bool ReconCommitOne(const int stmt)
{
   if(stmt==INVALID_HANDLE) return ReconJournalFail();
   ResetLastError();
   bool unexpected=DatabaseRead(stmt);
   int error=GetLastError();
   DatabaseFinalize(stmt);
   if(unexpected || error!=ERR_DATABASE_NO_MORE_DATA) return ReconJournalFail();
   int query=DatabasePrepare(g_recon_db,"SELECT changes()");
   int changed=0;
   bool ok=query!=INVALID_HANDLE && DatabaseRead(query) && DatabaseColumnInteger(query,0,changed);
   if(query!=INVALID_HANDLE) DatabaseFinalize(query);
   if(!ok || changed!=1 || !DatabaseTransactionCommit(g_recon_db)) return ReconJournalFail();
   return true;
}

bool ReconVerifyRecord(const long intent,const int stage,const string expected,const bool response)
{
   int stmt=DatabasePrepare(g_recon_db,
      "SELECT stage,payload,response FROM execution_journal_v1 WHERE scope=?1 AND account=?2 AND intent=?3");
   int actual=-1;
   string payload="",reply="";
   bool ok=stmt!=INVALID_HANDLE && DatabaseBind(stmt,0,g_recon_scope) && DatabaseBind(stmt,1,g_recon_account) &&
      DatabaseBind(stmt,2,intent) && DatabaseRead(stmt) && DatabaseColumnInteger(stmt,0,actual) &&
      DatabaseColumnText(stmt,1,payload) && DatabaseColumnText(stmt,2,reply) && actual==stage &&
      (response ? reply==expected : payload==expected);
   if(ok)
   {
      ResetLastError();
      bool duplicate=DatabaseRead(stmt);
      ok=!duplicate && GetLastError()==ERR_DATABASE_NO_MORE_DATA;
   }
   if(stmt!=INVALID_HANDLE) DatabaseFinalize(stmt);
   if(!ok) return ReconJournalFail();
   return true;
}

string ReconJournalDDL()
{
   return "CREATE TABLE IF NOT EXISTS execution_journal_v1 (scope TEXT PRIMARY KEY,account TEXT NOT NULL,"
          "intent INTEGER NOT NULL CHECK(intent>0),stage INTEGER NOT NULL CHECK(stage IN (0,1,2)),"
          "payload TEXT NOT NULL,response TEXT NOT NULL,outcome INTEGER NOT NULL)";
}

bool ReconCheckSingleValue(const string sql,const string expected,const bool integer_value=false)
{
   int stmt=DatabasePrepare(g_recon_db,sql);
   string text="";
   int number=0;
   bool ok=stmt!=INVALID_HANDLE && DatabaseRead(stmt);
   if(ok && integer_value)
      ok=DatabaseColumnInteger(stmt,0,number) && IntegerToString(number)==expected;
   else if(ok) ok=DatabaseColumnText(stmt,0,text) && text==expected;
   if(ok)
   {
      ResetLastError();
      bool extra=DatabaseRead(stmt);
      ok=!extra && GetLastError()==ERR_DATABASE_NO_MORE_DATA;
   }
   if(stmt!=INVALID_HANDLE) DatabaseFinalize(stmt);
   return ok;
}

string ReconEventDDL()
{
   return "CREATE TABLE IF NOT EXISTS execution_request_event_v1 (scope TEXT PRIMARY KEY,"
          "intent INTEGER NOT NULL CHECK(intent>0),response TEXT NOT NULL)";
}

bool ReconEventSchemaValid()
{
   string expected=ReconEventDDL();
   StringReplace(expected,"IF NOT EXISTS ","");
   return ReconCheckSingleValue("SELECT sql FROM sqlite_master WHERE type='table' AND name='execution_request_event_v1'",expected) &&
      ReconCheckSingleValue("SELECT COUNT(*) FROM sqlite_master WHERE type='trigger' AND tbl_name='execution_request_event_v1'","0",true);
}

bool ReconJournalSchemaValid()
{
   string expected=ReconJournalDDL();
   StringReplace(expected,"IF NOT EXISTS ","");
   // Strict versioned schema: no migration or automatic replacement of evidence.
   return ReconCheckSingleValue(
      "SELECT sql FROM sqlite_master WHERE type='table' AND name='execution_journal_v1'",expected) &&
      ReconCheckSingleValue(
      "SELECT COUNT(*) FROM sqlite_master WHERE type='trigger' AND tbl_name='execution_journal_v1'","0",true) &&
      ReconCheckSingleValue("PRAGMA synchronous","2",true) &&
      ReconCheckSingleValue("PRAGMA journal_mode","delete") &&
      ReconCheckSingleValue("PRAGMA integrity_check","ok");
}

// Daily fill accounting support functions
bool ReconInitializeDailyCounter(const datetime server_day)
{
   if(g_cfg.shadow_only) return true; // no accounting for shadow mode
   g_recon_daily_fill_day = server_day;
   g_recon_daily_fill_count = 0;

   // Reconstruct the confirmed-fill count for the current broker server day.
   // The journal schema is frozen (no broker-day column), but decision_id is
   // authored as boundary*1000000+suffix in RiskBeginOpportunity(), so integer
   // division intent/1000000 recovers the decision boundary datetime. Fills are
   // attributed to the broker day of their decision boundary, which is the
   // only day anchor available in the persisted row.
   int stmt = DatabasePrepare(g_recon_db,
      "SELECT COUNT(*) FROM execution_journal_v1 WHERE account=?1 AND stage=2 AND outcome=4 "
      "AND intent/1000000 >= ?2");
   if(stmt==INVALID_HANDLE) return false;

   bool ok = DatabaseBind(stmt,0,g_recon_account) &&
              DatabaseBind(stmt,1,(long)server_day) &&
              DatabaseRead(stmt);

   if(ok)
   {
      ok = DatabaseColumnLong(stmt,0,g_recon_daily_fill_count);
   }

   if(stmt!=INVALID_HANDLE) DatabaseFinalize(stmt);
   return ok;
}

bool ReconIncrementDailyFillCount(const long intent_id)
{
   if(g_cfg.shadow_only) return true;

   // Increment the in-memory confirmed-fill counter for the current broker day.
   // The journal row's stage/outcome transition is owned exclusively by
   // ReconFinishOpportunity; this function only advances the enforcement counter
   // after a fill has been durably confirmed (outcome=4, stage=2).
   g_recon_daily_fill_count++;
   return true;
}

bool ReconIsDailyFillLimitReached(const datetime server_day)
{
   if(g_cfg.shadow_only) return false;

   if(server_day!=g_recon_daily_fill_day)
   {
      // New day, reinitialize counter
      bool ok = ReconInitializeDailyCounter(server_day);
      if(!ok) return true; // Unknown counter blocks admission.
   }

   return g_recon_daily_fill_count >= 5;
}


struct ReconRecoveredIntent
{
   TradeIntent intent;
   MqlTradeRequest request;
   AmigoConfig management;
   double equity,stop_loss,existing_loss,risk_pct,distortion,atr;
};
ReconRecoveredIntent g_recon_recovered;
bool g_recon_recovered_present=false;
int g_recon_recovered_stage=-1;
int g_recon_recovered_outcome=-1;
string g_recon_recovered_response="";

bool ReconParseLong(const string text,long &value)
{
   if(text=="" || StringLen(text)>20) return false;
   long candidate=StringToInteger(text);
   if(StringFormat("%I64d",candidate)!=text) return false;
   value=candidate;
   return true;
}

bool ReconParseDouble(const string text,double &value)
{
   if(text=="" || StringLen(text)>32) return false;
   double candidate=StringToDouble(text);
   if(!MathIsValidNumber(candidate) || StringFormat("%.17g",candidate)!=text) return false;
   value=candidate;
   return true;
}

bool ReconReadField(const string payload,int &cursor,string &field)
{
   int size=StringLen(payload);
   if(cursor<0 || cursor>=size || size>16384) return false;
   int separator=StringFind(payload,":",cursor);
   if(separator<cursor || separator-cursor>5) return false;
   long length=0;
   if(!ReconParseLong(StringSubstr(payload,cursor,separator-cursor),length) ||
      length<0 || length>size-separator-1) return false;
   field=StringSubstr(payload,separator+1,(int)length);
   cursor=separator+1+(int)length;
   return true;
}

bool ReconDecodePrepared(const string payload,const long expected_id,ReconRecoveredIntent &output)
{
   string fields[9];
   int cursor=0;
   for(int i=0;i<9;i++) if(!ReconReadField(payload,cursor,fields[i])) return false;
   if(cursor!=StringLen(payload) || fields[0]!="AMIGO_INTENT_V1" || fields[1]=="" ||
      fields[3]!=fields[1] || expected_id<=0) return false;
   string integers[],prices[],request[],risk[];
   if(StringSplit(fields[5],'|',integers)!=17 || StringSplit(fields[6],'|',prices)!=7 ||
      StringSplit(fields[7],'|',request)!=9 || StringSplit(fields[8],'|',risk)!=13) return false;
   long ids[17],reqids[5],mgmt[3];
   double amounts[7],reqprices[4],envelope[10];
   for(int i=0;i<17;i++) if(!ReconParseLong(integers[i],ids[i])) return false;
   for(int i=0;i<7;i++) if(!ReconParseDouble(prices[i],amounts[i])) return false;
   for(int i=0;i<5;i++) if(!ReconParseLong(request[i],reqids[i])) return false;
   for(int i=0;i<4;i++) if(!ReconParseDouble(request[i+5],reqprices[i])) return false;
   for(int i=0;i<10;i++) if(!ReconParseDouble(risk[i],envelope[i])) return false;
   for(int i=0;i<3;i++) if(!ReconParseLong(risk[i+10],mgmt[i])) return false;
   if(ids[0]!=expected_id || ids[1]!=ids[0] || ids[2]!=ids[0] || ids[3]!=ids[0] || ids[4]!=ids[0] ||
      ids[5]<=0 || ids[6]!=Amigo_SCHEMA_VERSION ||
      ids[7]<0 || ids[7]>2147483647 || ids[8]<0 || ids[8]>2147483647 || ids[9]<0 || ids[9]>2147483647 ||
      (ids[10]!=1 && ids[10]!=-1) || ids[11]<=0 || ids[12]<=ids[11] ||
      ids[13]<0 || ids[13]>REGIME_NO_TRADE || (ids[14]!=HYP_CONTINUATION && ids[14]!=HYP_MEAN_REVERSION) ||
      ids[15]<HORIZON_SCALPING || ids[15]>HORIZON_SWING || ids[16]<0 || ids[16]>4294967295 ||
      fields[4]!=StringFormat("Amigo-%I64d",expected_id)) return false;
   if(reqids[0]!=TRADE_ACTION_DEAL || reqids[1]<0 || reqids[4]<0 ||
      reqids[2]!=(ids[10]==1 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL) || reqids[3]!=ORDER_FILLING_FOK ||
      reqprices[0]<=0.0 || reqprices[1]<=0.0 || reqprices[2]<=0.0 || reqprices[3]<=0.0 ||
      reqprices[2]!=amounts[1] || reqprices[3]!=amounts[2] || amounts[0]<=0.0 ||
      amounts[5]<=0.0 || amounts[6]<=0.0 ||
      (ids[10]==1 && !(amounts[1]<amounts[0] && amounts[2]>amounts[0] && reqprices[2]<reqprices[1] && reqprices[3]>reqprices[1])) ||
      (ids[10]==-1 && !(amounts[1]>amounts[0] && amounts[2]<amounts[0] && reqprices[2]>reqprices[1] && reqprices[3]<reqprices[1]))) return false;
   if(envelope[0]<=0.0 || envelope[1]<=0.0 || envelope[2]<0.0 || envelope[3]<=0.0 ||
      envelope[4]<=0.0 || envelope[5]<=0.0 || envelope[6]<=0.0 || envelope[7]<=0.0 || envelope[7]>=1.0 ||
      (mgmt[0]==TRAIL_ATR && (envelope[8]<=0.0 || envelope[9]<=0.0)) ||
      (mgmt[0]!=TRAIL_OFF && mgmt[0]!=TRAIL_DYNAMIC_25_PERCENT && mgmt[0]!=TRAIL_ATR) ||
      mgmt[1]<0 || mgmt[1]>23 || mgmt[2]<0 || mgmt[2]>24) return false;
   ReconRecoveredIntent candidate;
   ZeroMemory(candidate);
   candidate.intent.intent_id=ids[0]; candidate.intent.snapshot_id=ids[1];
   candidate.intent.decision_id=ids[2]; candidate.intent.signal_id=ids[3];
   candidate.intent.idempotency_key=ids[4]; candidate.intent.submission_attempt_id=ids[5];
   candidate.intent.schema_version=(int)ids[6]; candidate.intent.strategy_version=(int)ids[7];
   candidate.intent.feature_version=(int)ids[8]; candidate.intent.model_version=(int)ids[9];
   candidate.intent.direction=(int)ids[10]; candidate.intent.timestamp=(datetime)ids[11]; candidate.intent.expiry=(datetime)ids[12];
   candidate.intent.regime=(ENUM_REGIME)ids[13]; candidate.intent.hypothesis=(ENUM_HYPOTHESIS)ids[14];
   candidate.intent.horizon=(ENUM_HORIZON)ids[15]; candidate.intent.data_quality=(uint)ids[16];
   candidate.intent.symbol=fields[1]; candidate.intent.reason_codes=fields[2];
   candidate.intent.entry_reference=amounts[0]; candidate.intent.stop=amounts[1]; candidate.intent.target=amounts[2];
   candidate.intent.score=amounts[3]; candidate.intent.confidence=amounts[4];
   candidate.intent.risk_allocation=amounts[5]; candidate.intent.risk_modifier=amounts[6];
   candidate.request.action=(ENUM_TRADE_REQUEST_ACTIONS)reqids[0]; candidate.request.magic=(ulong)reqids[1];
   candidate.request.type=(ENUM_ORDER_TYPE)reqids[2]; candidate.request.type_filling=(ENUM_ORDER_TYPE_FILLING)reqids[3];
   candidate.request.deviation=(ulong)reqids[4]; candidate.request.volume=reqprices[0]; candidate.request.price=reqprices[1];
   candidate.request.sl=reqprices[2]; candidate.request.tp=reqprices[3]; candidate.request.symbol=fields[3]; candidate.request.comment=fields[4];
   candidate.equity=envelope[0]; candidate.stop_loss=envelope[1]; candidate.existing_loss=envelope[2];
   candidate.risk_pct=envelope[3]; candidate.distortion=envelope[4]; candidate.atr=envelope[5];
   candidate.management.shadow_only=true; // decoded evidence never grants live authority
   candidate.management.symbol=fields[1]; candidate.management.magic_number=(ulong)reqids[1];
   candidate.management.partial_rr=envelope[6]; candidate.management.partial_fraction=envelope[7];
   candidate.management.trail_atr_mult=envelope[8]; candidate.management.trail_activate_r=envelope[9];
   candidate.management.trail_mode=(ENUM_TRAILING_MODE)mgmt[0];
   candidate.management.session_start_hour=(int)mgmt[1]; candidate.management.session_end_hour=(int)mgmt[2];
   output=candidate; // reconstruction only; never an order authorization
   return true;
}

bool ReconRetcodeIsDefinitiveRejection(const uint retcode)
{
   switch(retcode)
   {
      case TRADE_RETCODE_REQUOTE:
      case TRADE_RETCODE_REJECT:
      case TRADE_RETCODE_CANCEL:
      case TRADE_RETCODE_INVALID:
      case TRADE_RETCODE_INVALID_VOLUME:
      case TRADE_RETCODE_INVALID_PRICE:
      case TRADE_RETCODE_INVALID_STOPS:
      case TRADE_RETCODE_TRADE_DISABLED:
      case TRADE_RETCODE_MARKET_CLOSED:
      case TRADE_RETCODE_NO_MONEY:
      case TRADE_RETCODE_PRICE_CHANGED:
      case TRADE_RETCODE_PRICE_OFF:
      case TRADE_RETCODE_INVALID_EXPIRATION:
      case TRADE_RETCODE_TOO_MANY_REQUESTS:
      case TRADE_RETCODE_SERVER_DISABLES_AT:
      case TRADE_RETCODE_CLIENT_DISABLES_AT:
      case TRADE_RETCODE_INVALID_FILL:
      case TRADE_RETCODE_ONLY_REAL:
      case TRADE_RETCODE_LIMIT_ORDERS:
      case TRADE_RETCODE_LIMIT_VOLUME:
      case TRADE_RETCODE_INVALID_ORDER:
      case TRADE_RETCODE_LIMIT_POSITIONS:
      case TRADE_RETCODE_REJECT_CANCEL:
      case TRADE_RETCODE_LONG_ONLY:
      case TRADE_RETCODE_SHORT_ONLY:
      case TRADE_RETCODE_CLOSE_ONLY:
      case TRADE_RETCODE_FIFO_CLOSE:
      case TRADE_RETCODE_HEDGE_PROHIBITED:
         return true;
   }
   return false;
}


struct ReconRecoveredResponse
{
   bool send_ok;
   MqlTradeResult result;
};
ReconRecoveredResponse g_recon_response;

bool ReconParseULong(const string text,ulong &value)
{
   int size=StringLen(text);
   if(size<=0 || size>20 || (size>1 && StringGetCharacter(text,0)=='0')) return false;
   ulong candidate=0;
   for(int i=0;i<size;i++)
   {
      ushort c=StringGetCharacter(text,i);
      if(c<'0' || c>'9') return false;
      ulong digit=(ulong)(c-'0');
      if(candidate>(ULONG_MAX-digit)/10) return false;
      candidate=candidate*10+digit;
   }
   value=candidate;
   return true;
}

bool ReconDecodeResponse(const string payload,ReconRecoveredResponse &output)
{
   int cursor=0;
   string numbers="",comment="",fields[];
   if(!ReconReadField(payload,cursor,numbers) || !ReconReadField(payload,cursor,comment) ||
      cursor!=StringLen(payload) || StringSplit(numbers,'|',fields)!=10) return false;
   long call_ok=0,external=0;
   ulong retcode=0,request=0,order=0,deal=0;
   double volume=0.0,price=0.0,bid=0.0,ask=0.0;
   if(!ReconParseLong(fields[0],call_ok) || (call_ok!=0 && call_ok!=1) ||
      !ReconParseULong(fields[1],retcode) || retcode>UINT_MAX ||
      !ReconParseULong(fields[2],request) || request>UINT_MAX ||
      !ReconParseLong(fields[3],external) || external<INT_MIN || external>INT_MAX ||
      !ReconParseULong(fields[4],order) || !ReconParseULong(fields[5],deal) ||
      !ReconParseDouble(fields[6],volume) || volume<0.0 ||
      !ReconParseDouble(fields[7],price) || price<0.0 ||
      !ReconParseDouble(fields[8],bid) || bid<0.0 ||
      !ReconParseDouble(fields[9],ask) || ask<0.0) return false;
   ReconRecoveredResponse candidate;
   ZeroMemory(candidate);
   candidate.send_ok=(call_ok==1);
   candidate.result.retcode=(uint)retcode; candidate.result.request_id=(uint)request;
   candidate.result.retcode_external=(int)external; candidate.result.order=order; candidate.result.deal=deal;
   candidate.result.volume=volume; candidate.result.price=price; candidate.result.bid=bid; candidate.result.ask=ask;
   candidate.result.comment=comment;
   output=candidate;
   return true;
}

bool ReconResponseSupportsOutcome(const ReconRecoveredResponse &response,const int outcome)
{
   if(!response.send_ok) return false;
   if(outcome==2)
      return ReconRetcodeIsDefinitiveRejection(response.result.retcode) && response.result.order==0 &&
         response.result.deal==0 && response.result.volume==0.0 && response.result.retcode_external==0;
   if(outcome==4)
      return response.result.retcode==TRADE_RETCODE_DONE && response.result.order>0 &&
         response.result.deal>0 && response.result.volume>0.0 && response.result.price>0.0;
   return false;
}

bool g_recon_event_present=false;
ReconRecoveredResponse g_recon_event_response;

// Local evidence consistency only. No broker-state or risk-release authority.
bool ReconEventMatchesResponse(const ReconRecoveredResponse &original,
                              const ReconRecoveredResponse &event,const int stage,const int outcome)
{
   if(stage<1 || stage>2 || !event.send_ok || original.result.request_id==0 ||
      event.result.request_id!=original.result.request_id) return false;
   if(original.result.order>0 && event.result.order!=original.result.order) return false;
   if(original.result.deal>0 && event.result.deal!=original.result.deal) return false;
   if(stage==2 && !ReconResponseSupportsOutcome(event,outcome)) return false;
   return true;
}

bool ReconLoadRequestEvent(const long intent,const int stage,const int outcome,
                          const ReconRecoveredResponse &original)
{
   g_recon_event_present=false;
   ZeroMemory(g_recon_event_response);
   int query=DatabasePrepare(g_recon_db,
      "SELECT intent,response,typeof(intent)='integer' AND typeof(response)='text' "
      "FROM execution_request_event_v1 WHERE scope=?1");
   if(query==INVALID_HANDLE) return false;
   if(!DatabaseBind(query,0,g_recon_scope)) { DatabaseFinalize(query); return false; }
   ResetLastError();
   if(!DatabaseRead(query))
   {
      int error=GetLastError(); DatabaseFinalize(query);
      return error==ERR_DATABASE_NO_MORE_DATA;
   }
   long event_intent=0;
   int types=0;
   string payload="";
   ReconRecoveredResponse decoded;
   bool ok=DatabaseColumnLong(query,0,event_intent) && DatabaseColumnText(query,1,payload) &&
      DatabaseColumnInteger(query,2,types) && types==1 && event_intent>0 &&
      intent>0 && event_intent<=intent && ReconDecodeResponse(payload,decoded) &&
      decoded.send_ok && decoded.result.request_id>0;
   if(ok && event_intent==intent)
      ok=ReconEventMatchesResponse(original,decoded,stage,outcome);
   if(ok)
   {
      ResetLastError();
      bool duplicate=DatabaseRead(query);
      ok=!duplicate && GetLastError()==ERR_DATABASE_NO_MORE_DATA;
   }
   DatabaseFinalize(query);
   if(!ok) return false;
   // A bounded slot for an older intent does not belong to this opportunity.
   if(event_intent==intent)
   {
      g_recon_event_response=decoded;
      g_recon_event_present=true;
   }
   return true;
}

bool ReconLoadCurrentIntent()
{
   g_recon_recovered_present=false;
   int query=DatabasePrepare(g_recon_db,
      "SELECT intent,stage,payload,response,outcome,typeof(intent)='integer' AND typeof(stage)='integer' AND typeof(outcome)='integer' "
      "FROM execution_journal_v1 WHERE scope=?1 AND account=?2");
   if(query==INVALID_HANDLE) return false;
   if(!DatabaseBind(query,0,g_recon_scope) || !DatabaseBind(query,1,g_recon_account))
   { DatabaseFinalize(query); return false; }
   ResetLastError();
   if(!DatabaseRead(query))
   {
      int error=GetLastError(); DatabaseFinalize(query);
      ReconRecoveredResponse empty; ZeroMemory(empty);
      return error==ERR_DATABASE_NO_MORE_DATA && ReconLoadRequestEvent(0,-1,0,empty);
   }
   long intent=0;
   int stage=-1,outcome=-1,types=0;
   string payload="",response="";
   ReconRecoveredIntent recovered;
   ReconRecoveredResponse decoded_response;
   ZeroMemory(decoded_response);
   bool ok=DatabaseColumnLong(query,0,intent) && DatabaseColumnInteger(query,1,stage) &&
      DatabaseColumnText(query,2,payload) && DatabaseColumnText(query,3,response) &&
      DatabaseColumnInteger(query,4,outcome) && DatabaseColumnInteger(query,5,types) && types==1 &&
      stage>=0 && stage<=2 && ((stage<2 && outcome==0) || (stage==2 && (outcome==2 || outcome==4))) &&
      ((stage==0 && response=="") || (stage>0 && ReconDecodeResponse(response,decoded_response))) &&
      (stage!=2 || ReconResponseSupportsOutcome(decoded_response,outcome)) && ReconDecodePrepared(payload,intent,recovered);
   if(ok)
   {
      string scope=g_recon_account+ReconField(StringFormat("%I64u",recovered.request.magic))+ReconField(recovered.intent.symbol);
      ok=scope==g_recon_scope;
      ResetLastError();
      bool duplicate=DatabaseRead(query);
      ok=ok && !duplicate && GetLastError()==ERR_DATABASE_NO_MORE_DATA;
   }
   DatabaseFinalize(query);
   if(!ok || !ReconLoadRequestEvent(intent,stage,outcome,decoded_response)) return false;
   g_recon_response=decoded_response;
   g_recon_recovered=recovered; g_recon_recovered_stage=stage;
   g_recon_recovered_outcome=outcome;
   g_recon_recovered_response=response; g_recon_recovered_present=true;
   return true;
}

bool ReconJournalInit(const AmigoConfig &cfg)
{
   if(cfg.shadow_only) return true; // no broker-intent journal for synthetic fills
   g_recon_fault=false; // clear any stale fault from previous runs
   if(g_recon_db!=INVALID_HANDLE) { DatabaseClose(g_recon_db); g_recon_db=INVALID_HANDLE; }
   g_recon_account=ReconCurrentAccountScope();
   if(g_recon_account=="" || cfg.symbol=="") return ReconJournalFail();
   g_recon_scope=g_recon_account+ReconField(StringFormat("%I64u",cfg.magic_number))+ReconField(cfg.symbol);
   string journal_name = MQLInfoInteger(MQL_TESTER) ?
                         "AMIGO_execution_journal_tester_v1.sqlite" :
                         "AMIGO_execution_journal_v1.sqlite";
   g_recon_db=DatabaseOpen(journal_name,DATABASE_OPEN_READWRITE|DATABASE_OPEN_CREATE);
   if(g_recon_db==INVALID_HANDLE) return ReconJournalFail();
   if(!DatabaseExecute(g_recon_db,"PRAGMA journal_mode=DELETE") ||
      !DatabaseExecute(g_recon_db,"PRAGMA synchronous=FULL") ||
      !DatabaseExecute(g_recon_db,ReconJournalDDL()) ||
      !ReconJournalSchemaValid() || !DatabaseExecute(g_recon_db,ReconEventDDL()) ||
      !ReconEventSchemaValid() || !ReconLoadCurrentIntent()) return ReconJournalFail();
   int query=DatabasePrepare(g_recon_db,
      "SELECT COUNT(*) FROM execution_journal_v1 WHERE account=?1 AND "
      "(stage!=2 OR outcome NOT IN (2,4) OR typeof(intent)!='integer' OR length(payload)=0 OR length(response)=0)");
   int unresolved=-1;
   bool ok=query!=INVALID_HANDLE && DatabaseBind(query,0,g_recon_account) && DatabaseRead(query) &&
           DatabaseColumnInteger(query,0,unresolved);
   if(query!=INVALID_HANDLE) DatabaseFinalize(query);
   if(!ok || unresolved!=0) return ReconJournalFail();
   return true;
}

// Compare independently loaded stores; never infer that a missing journal
// proves no submission. This predicate grants no lock or recovery authority.
bool ReconLedgerPairConsistent(const long risk_id,const int risk_outcome,
                              const bool present,const long journal_id,
                              const int stage,const int journal_outcome)
{
   if(risk_id<0 || risk_outcome<0 || risk_outcome>6) return false;
   if((risk_id==0)!=(risk_outcome==0)) return false;
   if(risk_outcome==1 || risk_outcome==5) return false;
   if(!present) return risk_outcome!=4;
   if(journal_id<=0 || stage!=2 || (journal_outcome!=2 && journal_outcome!=4)) return false;
   if(journal_id>risk_id) return false;
   if(journal_id==risk_id) return risk_outcome==journal_outcome;
   // A later confirmed fill must have replaced the journal's previous row.
   // Later preflight rejection/no-trade/shadow opportunities need no submission.
   return risk_outcome==2 || risk_outcome==3 || risk_outcome==6;
}

bool ReconValidateRiskRecovery(const AmigoConfig &cfg,const bool risk_ready,
                              const long risk_id,const int risk_outcome)
{
   if(cfg.shadow_only) return true;
   if(!risk_ready || g_recon_fault || !ReconScopeStillCurrent(cfg) ||
      !ReconLoadCurrentIntent()) return ReconJournalFail();
   long journal_id=g_recon_recovered_present ? g_recon_recovered.intent.intent_id : 0;
   if(!ReconLedgerPairConsistent(risk_id,risk_outcome,g_recon_recovered_present,
                                journal_id,g_recon_recovered_stage,g_recon_recovered_outcome))
      return ReconJournalFail();
   return true;
}

bool ReconPrepareIntent(const TradeIntent &ti,const MqlTradeRequest &req,const AmigoConfig &cfg,
                        const double equity,const double stop_loss,const double existing_loss,
                        const double risk_pct,const double distortion,const double atr)
{
   if(cfg.shadow_only || g_recon_fault || g_recon_db==INVALID_HANDLE || g_recon_prepared_id!=0 ||
      ti.intent_id<=0 || !MathIsValidNumber(atr) || atr<=0.0) return false;
   if(!ReconScopeStillCurrent(cfg) || req.magic!=cfg.magic_number || req.symbol!=cfg.symbol || ti.symbol!=cfg.symbol)
      return ReconJournalFail();
   // Length-prefix text fields; preserve doubles at round-trip precision.
   string payload=ReconField("AMIGO_INTENT_V1")+ReconField(ti.symbol)+ReconField(ti.reason_codes)+
      ReconField(req.symbol)+ReconField(req.comment)+
      ReconField(StringFormat("%I64d|%I64d|%I64d|%I64d|%I64d|%I64d|%d|%d|%d|%d|%d|%I64d|%I64d|%d|%d|%d|%u",
         ti.intent_id,ti.snapshot_id,ti.decision_id,ti.signal_id,ti.idempotency_key,
         ti.submission_attempt_id,ti.schema_version,ti.strategy_version,ti.feature_version,ti.model_version,
         ti.direction,(long)ti.timestamp,(long)ti.expiry,(int)ti.regime,(int)ti.hypothesis,(int)ti.horizon,ti.data_quality))+
      ReconField(StringFormat("%.17g|%.17g|%.17g|%.17g|%.17g|%.17g|%.17g",
         ti.entry_reference,ti.stop,ti.target,ti.score,ti.confidence,ti.risk_allocation,ti.risk_modifier))+
      ReconField(StringFormat("%d|%I64u|%d|%d|%I64u|%.17g|%.17g|%.17g|%.17g",
         (int)req.action,req.magic,(int)req.type,(int)req.type_filling,req.deviation,req.volume,req.price,req.sl,req.tp))+
      ReconField(StringFormat("%.17g|%.17g|%.17g|%.17g|%.17g|%.17g|%.17g|%.17g|%.17g|%.17g|%d|%d|%d",
         equity,stop_loss,existing_loss,risk_pct,distortion,atr,cfg.partial_rr,cfg.partial_fraction,
         cfg.trail_atr_mult,cfg.trail_activate_r,(int)cfg.trail_mode,cfg.session_start_hour,cfg.session_end_hour));
   ReconRecoveredIntent verify_payload;
   if(!ReconDecodePrepared(payload,ti.intent_id,verify_payload)) return ReconJournalFail();
   if(StringLen(payload)>16384 || !DatabaseTransactionBegin(g_recon_db)) return ReconJournalFail();
   string sql=
      "INSERT INTO execution_journal_v1(scope,account,intent,stage,payload,response,outcome) "
      "SELECT ?1,?2,?3,0,?4,'',0 WHERE NOT EXISTS "
      "(SELECT 1 FROM execution_journal_v1 WHERE account=?2 AND stage!=2) "
      "ON CONFLICT(scope) DO UPDATE SET intent=excluded.intent,stage=0,payload=excluded.payload,response='',outcome=0 "
      "WHERE execution_journal_v1.account=excluded.account AND execution_journal_v1.stage=2 "
      "AND execution_journal_v1.outcome IN (2,4) AND execution_journal_v1.intent<excluded.intent";
   int stmt=DatabasePrepare(g_recon_db,sql);
   bool bound=stmt!=INVALID_HANDLE && DatabaseBind(stmt,0,g_recon_scope) && DatabaseBind(stmt,1,g_recon_account) &&
              DatabaseBind(stmt,2,ti.intent_id) && DatabaseBind(stmt,3,payload);
   if(!bound) { if(stmt!=INVALID_HANDLE) DatabaseFinalize(stmt); return ReconJournalFail(); }
   if(!ReconCommitOne(stmt)) return false;
   if(!ReconVerifyRecord(ti.intent_id,0,payload,false)) return false;
   g_recon_prepared_id=ti.intent_id;
   return true;
}

bool ReconRecordResponse(const long intent,const bool send_ok,const MqlTradeResult &result)
{
   if(g_recon_fault || g_recon_db==INVALID_HANDLE || intent!=g_recon_prepared_id || intent<=0)
      return false;
   string response=ReconField(StringFormat("%d|%u|%u|%d|%I64u|%I64u|%.17g|%.17g|%.17g|%.17g",
      (int)send_ok,result.retcode,result.request_id,result.retcode_external,result.order,result.deal,
      result.volume,result.price,result.bid,result.ask))+ReconField(result.comment);
   if(!DatabaseTransactionBegin(g_recon_db)) return ReconJournalFail();
   int stmt=DatabasePrepare(g_recon_db,
      "UPDATE execution_journal_v1 SET stage=1,response=?3 WHERE scope=?1 AND intent=?2 AND stage=0");
   bool bound=stmt!=INVALID_HANDLE && DatabaseBind(stmt,0,g_recon_scope) &&
      DatabaseBind(stmt,1,intent) && DatabaseBind(stmt,2,response);
   if(!bound) { if(stmt!=INVALID_HANDLE) DatabaseFinalize(stmt); return ReconJournalFail(); }
   if(!ReconCommitOne(stmt) || !ReconVerifyRecord(intent,1,response,true)) return false;
   g_recon_session_request=result.request_id;
   g_recon_session_intent=intent;
   return true;
}

bool ReconFinishOpportunity(const long intent,const int outcome,const AmigoConfig &cfg)
{
   if(cfg.shadow_only) return true;
   if(g_recon_fault) return false;
   if(!ReconScopeStillCurrent(cfg)) return ReconJournalFail();
   if(g_recon_prepared_id==0) return true; // rejected before preparing a submission
   if(intent!=g_recon_prepared_id || (outcome!=2 && outcome!=4)) return false;
   if(!ReconLoadCurrentIntent() || !g_recon_recovered_present || g_recon_recovered_stage!=1 ||
      g_recon_recovered.intent.intent_id!=intent || !ReconResponseSupportsOutcome(g_recon_response,outcome))
      return ReconJournalFail();
   if(!DatabaseTransactionBegin(g_recon_db)) return ReconJournalFail();
   int stmt=DatabasePrepare(g_recon_db,
      "UPDATE execution_journal_v1 SET stage=2,outcome=?3 WHERE scope=?1 AND intent=?2 AND stage=1 AND length(response)>0");
   bool bound=stmt!=INVALID_HANDLE && DatabaseBind(stmt,0,g_recon_scope) &&
      DatabaseBind(stmt,1,intent) && DatabaseBind(stmt,2,outcome);
   if(!bound) { if(stmt!=INVALID_HANDLE) DatabaseFinalize(stmt); return ReconJournalFail(); }
   if(!ReconCommitOne(stmt)) return false;
   // Verify persisted completion before the caller releases account admission.
   if(!ReconLoadCurrentIntent() || !g_recon_recovered_present ||
      g_recon_recovered_stage!=2 || g_recon_recovered.intent.intent_id!=intent ||
      !ReconResponseSupportsOutcome(g_recon_response,outcome)) return ReconJournalFail();
   g_recon_prepared_id=0;
   // Advance the daily confirmed-fill enforcement counter only for a
   // durably confirmed fill (outcome=4). Rejections (outcome=2) are not fills.
   if(outcome==4) ReconIncrementDailyFillCount(intent);
   return true;
}


// Preserve a correlated callback separately from the original send response.
// One slot per scope bounds storage; same-intent conflicting evidence is never
// overwritten. This function does not authorize a fill, retry or risk release.
bool ReconCaptureRequestEvent(const MqlTradeRequest &request,const MqlTradeResult &result,
                             const AmigoConfig &cfg)
{
   if(cfg.shadow_only || g_recon_session_request==0 || result.request_id!=g_recon_session_request)
      return true; // not attributable to a request issued in this process
   if(g_recon_fault || !ReconScopeStillCurrent(cfg) || !ReconLoadCurrentIntent() ||
      !g_recon_recovered_present || g_recon_recovered.intent.intent_id!=g_recon_session_intent)
      return ReconJournalFail();
   MqlTradeRequest saved=g_recon_recovered.request;
   if(request.action!=saved.action || request.magic!=saved.magic || request.symbol!=saved.symbol ||
      request.comment!=saved.comment || request.type!=saved.type || request.type_filling!=saved.type_filling ||
      request.volume!=saved.volume || request.price!=saved.price || request.sl!=saved.sl || request.tp!=saved.tp ||
      request.deviation!=saved.deviation || request.order!=0 || request.position!=0 || request.position_by!=0 ||
      request.stoplimit!=0.0 || request.expiration!=0 || request.type_time!=ORDER_TIME_GTC)
      return ReconJournalFail();
   // The leading flag identifies receipt of a callback, not OrderSend success.
   // This separate artifact must never replace the raw synchronous response.
   string response=ReconField(StringFormat("%d|%u|%u|%d|%I64u|%I64u|%.17g|%.17g|%.17g|%.17g",
      1,result.retcode,result.request_id,result.retcode_external,result.order,result.deal,
      result.volume,result.price,result.bid,result.ask))+ReconField(result.comment);
   ReconRecoveredResponse decoded;
   if(!ReconDecodeResponse(response,decoded)) return ReconJournalFail();
   if(!DatabaseTransactionBegin(g_recon_db)) return ReconJournalFail();
   int stmt=DatabasePrepare(g_recon_db,
      "INSERT INTO execution_request_event_v1(scope,intent,response) VALUES(?1,?2,?3) "
      "ON CONFLICT(scope) DO UPDATE SET intent=excluded.intent,response=excluded.response "
      "WHERE execution_request_event_v1.intent<excluded.intent OR "
      "(execution_request_event_v1.intent=excluded.intent AND execution_request_event_v1.response=excluded.response)");
   bool bound=stmt!=INVALID_HANDLE && DatabaseBind(stmt,0,g_recon_scope) &&
      DatabaseBind(stmt,1,g_recon_session_intent) && DatabaseBind(stmt,2,response);
   if(!bound) { if(stmt!=INVALID_HANDLE) DatabaseFinalize(stmt); return ReconJournalFail(); }
   if(!ReconCommitOne(stmt)) return false;
   int query=DatabasePrepare(g_recon_db,
      "SELECT response FROM execution_request_event_v1 WHERE scope=?1 AND intent=?2");
   string actual="";
   bool ok=query!=INVALID_HANDLE && DatabaseBind(query,0,g_recon_scope) &&
      DatabaseBind(query,1,g_recon_session_intent) && DatabaseRead(query) &&
      DatabaseColumnText(query,0,actual) && actual==response;
   if(query!=INVALID_HANDLE) DatabaseFinalize(query);
   if(!ok) return ReconJournalFail();
   return true;
}

//--- Called from AMIGO.mq5 OnTradeTransaction().
//--- Signature must match the built-in MQL5 event handler parameters
//--- exactly, or the compiler will refuse the call site.
void TransactionReconHandle(const MqlTradeTransaction &trans,
                            const MqlTradeRequest &request,
                            const MqlTradeResult &result)
{
   switch(trans.type)
   {
      case TRADE_TRANSACTION_ORDER_ADD:
         LogMsg(LOG_DEBUG, "RECON",
                StringFormat("ORDER_ADD ticket=%I64u sym=%s",
                             trans.order, trans.symbol));
         break;

      case TRADE_TRANSACTION_ORDER_UPDATE:
         LogMsg(LOG_DEBUG, "RECON",
                StringFormat("ORDER_UPDATE ticket=%I64u state=%d",
                             trans.order, (int)trans.order_state));
         break;

      case TRADE_TRANSACTION_ORDER_DELETE:
         LogMsg(LOG_INFO, "RECON",
                StringFormat("ORDER_DELETE ticket=%I64u reason=%d",
                             trans.order, (int)trans.order_state));
         break;

      case TRADE_TRANSACTION_DEAL_ADD:
         LogMsg(LOG_INFO, "RECON",
                StringFormat("DEAL_ADD ticket=%I64u order=%I64u sym=%s vol=%.2f price=%.5f",
                             trans.deal, trans.order, trans.symbol,
                             trans.volume, trans.price));
         break;

      case TRADE_TRANSACTION_DEAL_UPDATE:
         LogMsg(LOG_DEBUG, "RECON",
                StringFormat("DEAL_UPDATE ticket=%I64u", trans.deal));
         break;

      case TRADE_TRANSACTION_DEAL_DELETE:
         LogMsg(LOG_INFO, "RECON",
                StringFormat("DEAL_DELETE ticket=%I64u", trans.deal));
         break;

      case TRADE_TRANSACTION_HISTORY_ADD:
         LogMsg(LOG_DEBUG, "RECON",
                StringFormat("HISTORY_ADD ticket=%I64u", trans.order));
         break;

      case TRADE_TRANSACTION_HISTORY_UPDATE:
         LogMsg(LOG_DEBUG, "RECON",
                StringFormat("HISTORY_UPDATE ticket=%I64u", trans.order));
         break;

      case TRADE_TRANSACTION_HISTORY_DELETE:
         LogMsg(LOG_INFO, "RECON",
                StringFormat("HISTORY_DELETE ticket=%I64u", trans.order));
         break;

      case TRADE_TRANSACTION_POSITION:
         LogMsg(LOG_INFO, "RECON",
                StringFormat("POSITION_UPDATE ticket=%I64u sym=%s",
                             trans.position, trans.symbol));
         break;

      case TRADE_TRANSACTION_REQUEST:
         LogMsg(LOG_INFO, "RECON",
                StringFormat("REQUEST intent=%s magic=%I64u request_id=%u retcode=%u order=%I64u deal=%I64u symbol=%s",
                             request.comment,request.magic,result.request_id,result.retcode,
                             result.order,result.deal,request.symbol));
         break;

      default:
         LogMsg(LOG_DEBUG, "RECON",
                StringFormat("UNHANDLED type=%d", (int)trans.type));
         break;
   }
}
//+------------------------------------------------------------------+

#endif // AMIGO_TRANSACTION_RECON_MQH
