//+------------------------------------------------------------------+
//| ExternalContext.mqh - read external context, write market state  |
//+------------------------------------------------------------------+
#property strict

#include <Contracts header.mqh>
#include <Configuration.mqh>
#include <Logger.mqh>
#include <News Policy.mqh>

// Canonical nonnegative integer encoding used by the Python bridge. Reject
// truncation, suffixes and overflow rather than trusting StringToInteger's prefix.
bool ExternalCanonicalTimestamp(const string value)
{
   if(StringLen(value)==0) return false;
   for(int i=0;i<StringLen(value);i++)
   {
      ushort c=StringGetCharacter(value,i);
      if(c<'0' || c>'9') return false;
   }
   long parsed=StringToInteger(value);
   return parsed>=0 && StringFormat("%I64d",parsed)==value;
}

// Strict finite decimal grammar; StringToDouble alone accepts numeric prefixes.
bool ExternalFiniteNumber(const string value)
{
   int n=StringLen(value),i=0,digits=0;
   if(n==0) return false;
   if(StringGetCharacter(value,0)=='-' || StringGetCharacter(value,0)=='+') i++;
   while(i<n && StringGetCharacter(value,i)>='0' && StringGetCharacter(value,i)<='9') { i++; digits++; }
   if(i<n && StringGetCharacter(value,i)=='.')
   {
      i++;
      while(i<n && StringGetCharacter(value,i)>='0' && StringGetCharacter(value,i)<='9') { i++; digits++; }
   }
   if(digits==0) return false;
   if(i<n && (StringGetCharacter(value,i)=='e' || StringGetCharacter(value,i)=='E'))
   {
      i++; digits=0;
      if(i<n && (StringGetCharacter(value,i)=='-' || StringGetCharacter(value,i)=='+')) i++;
      while(i<n && StringGetCharacter(value,i)>='0' && StringGetCharacter(value,i)<='9') { i++; digits++; }
      if(digits==0) return false;
   }
   return i==n && MathIsValidNumber(StringToDouble(value));
}

//--- Read the external-context file written by Python.
//--- Format: one "key=value" per line, ANSI text, shared-read.
bool ReadExternalContext(string path, ExternalContext &ctx, string &err,
                         const int max_age_seconds=120)
{
   err = "";

   //--- Reset all fields (safety: caller may reuse the struct)
   ctx.schema_version           = 0;
   ctx.timestamp                = 0;
   ctx.data_quality             = DQ_OK;
   ctx.cftc_valid               = false;
   ctx.cftc_publication_ts      = 0;
   ctx.cftc_net_position        = 0.0;
   ctx.cftc_net_change          = 0.0;
   ctx.cftc_percentile          = 50.0;
   ctx.cftc_extreme             = false;
   ctx.cftc_release_age_s       = 0;
   ctx.options_valid            = false;
   ctx.options_obs_ts           = 0;
   ctx.options_basis            = 0.0;
   ctx.options_oi_concentration = 0.0;
   ctx.options_strike_distance_atr = 0.0;
   ctx.options_gamma_regime     = 0;
   ctx.news_valid               = false;
   ctx.news_observed_ts         = 0;
   ctx.news_event_ts            = 0;
   ctx.news_active_window       = false;
   ctx.news_released            = false;
   ctx.news_surprise            = 0.0;
   ctx.news_relative_surprise   = 0.0;

   if(MQLInfoInteger(MQL_TESTER) || MQLInfoInteger(MQL_OPTIMIZATION))
   {
      ctx.data_quality|=DQ_EXTERNAL_ABSENT;
      err="LIVE_EXTERNAL_BRIDGE_DISABLED_IN_TESTER";
      return false;
   }
   int h = FileOpen(path, FILE_READ|FILE_TXT|FILE_ANSI|FILE_SHARE_READ);
   if(h == INVALID_HANDLE)
   {
      err = "FILE_OPEN_FAIL";
      return false;
   }

   uint cftc_fields=0;
   bool cftc_payload_valid=true,publication_verified=false,payload_valid=true;
   string context_symbol="",seen_keys[];
   uint envelope_fields=0;
   uint outcome_fields=0;
   bool outcome_valid=true;
   uint news_fields=0;
   bool news_payload_valid=true;
   while(!FileIsEnding(h))
   {
      string line = FileReadString(h);
      int eq = StringFind(line, "=");
      if(eq <= 0)
      {
         StringTrimLeft(line); StringTrimRight(line);
         if(StringLen(line)>0) payload_valid=false;
         continue;
      }

      string k = StringSubstr(line, 0, eq);
      string v = StringSubstr(line, eq + 1);
      StringTrimLeft(k);  StringTrimRight(k);
      StringTrimLeft(v);  StringTrimRight(v);

      for(int j=0;j<ArraySize(seen_keys);j++)
         if(seen_keys[j]==k) payload_valid=false;
      int count=ArraySize(seen_keys);
      if(count>=128 || ArrayResize(seen_keys,count+1)!=count+1)
      { payload_valid=false; break; }
      seen_keys[count]=k;
      if(k=="schema_version" || k=="timestamp" || k=="data_quality")
      {
         if(!ExternalCanonicalTimestamp(v)) payload_valid=false;
         if(k=="schema_version") envelope_fields|=1;
         if(k=="timestamp") envelope_fields|=2;
         if(k=="data_quality") envelope_fields|=4;
      }
      if(k=="context_symbol") context_symbol=v;
      uint cb=0;
      if(k=="cftc_valid") cb=1;
      else if(k=="cftc_pub_ts") cb=2;
      else if(k=="cftc_net") cb=4;
      else if(k=="cftc_net_chg") cb=8;
      else if(k=="cftc_pct") cb=16;
      else if(k=="cftc_extreme") cb=32;
      else if(k=="cftc_pub_verified") { cb=64; publication_verified=(v=="1"); }
      if(cb!=0)
      {
         cftc_fields|=cb;
         if(cb==2) { if(!ExternalCanonicalTimestamp(v)) cftc_payload_valid=false; }
         else if(cb==4 || cb==8 || cb==16)
         { if(!ExternalFiniteNumber(v)) cftc_payload_valid=false; }
         else if(v!="0" && v!="1") cftc_payload_valid=false;
      }
      if(k=="news_surprise" || k=="news_rel_surprise")
      {
         outcome_fields|=(k=="news_surprise" ? 1 : 2);
         if(!ExternalFiniteNumber(v)) outcome_valid=false;
      }
      // Every admission-critical news field must occur exactly once, even
      // for a confirmed no-event observation. Equal duplicate values are not
      // proof of a complete publication.
      uint news_bit=0;
      if(k=="news_valid") news_bit=1;
      else if(k=="news_observed_ts") news_bit=2;
      else if(k=="news_ts") news_bit=4;
      else if(k=="news_active") news_bit=8;
      else if(k=="news_released") news_bit=16;
      if(news_bit!=0)
      {
         if((news_fields & news_bit)!=0) news_payload_valid=false;
         news_fields |= news_bit;
         if(news_bit==2 || news_bit==4)
         {
            if(!ExternalCanonicalTimestamp(v)) news_payload_valid=false;
         }
         else if(v!="0" && v!="1") news_payload_valid=false;
      }

      if(k == "schema_version")         ctx.schema_version         = (int)StringToInteger(v);
      else if(k == "timestamp")         ctx.timestamp              = (datetime)StringToInteger(v);
      else if(k == "data_quality")      ctx.data_quality           = (uint)StringToInteger(v);
      else if(k == "cftc_valid")        ctx.cftc_valid             = (v == "1");
      else if(k == "cftc_pub_ts")       ctx.cftc_publication_ts    = (datetime)StringToInteger(v);
      else if(k == "cftc_net")          ctx.cftc_net_position      = StringToDouble(v);
      else if(k == "cftc_net_chg")      ctx.cftc_net_change        = StringToDouble(v);
      else if(k == "cftc_pct")          ctx.cftc_percentile        = StringToDouble(v);
      else if(k == "cftc_extreme")      ctx.cftc_extreme           = (v == "1");
      else if(k == "options_valid")     ctx.options_valid          = (v == "1");
      else if(k == "options_obs_ts")    ctx.options_obs_ts         = (datetime)StringToInteger(v);
      else if(k == "options_basis")     ctx.options_basis          = StringToDouble(v);
      else if(k == "options_oi_conc")   ctx.options_oi_concentration = StringToDouble(v);
      else if(k == "options_sd_atr")    ctx.options_strike_distance_atr = StringToDouble(v);
      else if(k == "options_gamma")     ctx.options_gamma_regime   = (int)StringToInteger(v);
      else if(k == "news_valid")        ctx.news_valid             = (v == "1");
      else if(k == "news_observed_ts")  ctx.news_observed_ts       = (datetime)StringToInteger(v);
      else if(k == "news_ts")           ctx.news_event_ts          = (datetime)StringToInteger(v);
      else if(k == "news_active")       ctx.news_active_window     = (v == "1");
      else if(k == "news_released")     ctx.news_released          = (v == "1");
      else if(k == "news_surprise")     ctx.news_surprise          = StringToDouble(v);
      else if(k == "news_rel_surprise") ctx.news_relative_surprise = StringToDouble(v);
   }
   FileClose(h);

   if(!news_payload_valid || news_fields!=31 ||
      (ctx.news_released && (!outcome_valid || outcome_fields!=3)) ||
      ((ctx.news_active_window || ctx.news_released) && ctx.news_event_ts<=0))
   {
      ctx.news_valid=false;
      ctx.news_observed_ts=0;
      ctx.data_quality |= DQ_STALE_EXTERNAL;
      err="NEWS_PAYLOAD_INCOMPLETE_OR_INVALID";
   }

   //--- Validate schema version
   if(ctx.schema_version != Amigo_SCHEMA_VERSION)
   {
      ctx.data_quality |= DQ_SCHEMA_MISMATCH;
      // No provider field is trusted across an unknown bridge schema. Field
      // names or meanings may have changed even when parsing succeeded.
      ctx.cftc_valid = false;
      ctx.cftc_publication_ts = 0;
      ctx.options_valid = false;
      ctx.options_obs_ts = 0;
      ctx.news_valid = false;
      ctx.news_observed_ts = 0;
      ctx.news_event_ts = 0;
      ctx.news_active_window = false;
      ctx.news_surprise = 0.0;
      ctx.news_relative_surprise = 0.0;
   }

   //--- Point-in-time correctness: reject observations stamped in the future.
   // Python bridge observation/event timestamps are UTC epoch values.
   datetime now = TimeGMT();
   if(max_age_seconds<=0 || ctx.timestamp<=0 || ctx.timestamp>now ||
      (now-ctx.timestamp)>max_age_seconds)
   {
      err="CONTEXT_STALE_OR_INVALID_TIMESTAMP";
      ctx.data_quality |= DQ_STALE_EXTERNAL;
      ctx.cftc_valid=false;
      ctx.cftc_publication_ts=0;
      ctx.options_valid=false;
      ctx.options_obs_ts=0;
      ctx.news_valid=false;
      ctx.news_observed_ts=0;
      ctx.news_event_ts=0;
      ctx.news_active_window=false;
      ctx.news_surprise=0.0;
      ctx.news_relative_surprise=0.0;
   }
   if(ctx.cftc_valid && ctx.cftc_publication_ts > now)
   {
      ctx.cftc_valid    = false;
      ctx.data_quality |= DQ_STALE_EXTERNAL;
   }
   if(ctx.options_valid && ctx.options_obs_ts > now)
   {
      ctx.options_valid = false;
      ctx.data_quality |= DQ_STALE_EXTERNAL;
   }
   // UTC release age bound is an engineering freshness cap, not proof of
   // publication provenance. A release inferred from report date is rejected.
   string normalized=context_symbol; StringToUpper(normalized);
   if(!cftc_payload_valid || cftc_fields!=127 || !publication_verified ||
      context_symbol!=_Symbol || (normalized!="XAUUSD" && normalized!="XAUUSDM") ||
      ctx.cftc_publication_ts<=0 || ctx.cftc_publication_ts>now ||
      now-ctx.cftc_publication_ts>14*86400 ||
      ctx.cftc_percentile<0 || ctx.cftc_percentile>100)
   {
      ctx.cftc_valid=false;
      ctx.cftc_publication_ts=0;
      ctx.data_quality|=DQ_STALE_EXTERNAL;
   }
   // GLD strike mapping and dealer-side gamma are unvalidated. Old or forged
   // valid flags cannot reinstate this unsupported scoring input.
   ctx.options_valid=false;
   ctx.options_obs_ts=0;
   ctx.options_gamma_regime=0;
   if(!payload_valid || envelope_fields!=7)
   {
      ctx.cftc_valid=false;
      ctx.options_valid=false;
      ctx.news_valid=false;
      ctx.news_observed_ts=0;
      ctx.data_quality|=DQ_STALE_EXTERNAL;
      err="EXTERNAL_PAYLOAD_INVALID";
   }
   // Note: news_event_ts is the scheduled release timestamp, which can be in the future
   // during the pre-event blackout/buffer window (e.g. 30 min before release).
   // Reject as look-ahead if the payload claims the outcome has already been released (news_released == true)
   // before the scheduled event time has arrived.
   if(ctx.news_valid && ctx.news_event_ts > now && ctx.news_released)
   {
      ctx.news_valid    = false;
      ctx.data_quality |= DQ_STALE_EXTERNAL;
   }
   return true;
}

// Apply the supported NEWS policy at the MQL5 decision boundary.  A valid,
// fresh observation with no active window means healthy/no-event; missing,
// future-dated, stale, or malformed observations are unavailable and must
// fail closed in FILTER mode.  This consumes provider status only; it does
// not claim authoritative calendar coverage.
bool ExternalNewsFilterAllows(const ExternalContext &ctx,const int mode,
                              const datetime now,const int max_age_seconds,
                              string &reason)
{
   return AmigoNewsAdmission(ctx,mode,now,max_age_seconds,reason);
}

//--- Write the current market snapshot for Python to read.
//--- Format matches the Python bridge's key=value parser.
void WriteSnapshotForExternal(string path, const MarketSnapshot &s,
                              const FeatureSnapshot &f)
{
   // Simulated market observations must never be published as live inputs.
   if(MQLInfoInteger(MQL_TESTER) || MQLInfoInteger(MQL_OPTIMIZATION)) return;
   if(s.snapshot_id<=0 || s.snapshot_id!=f.snapshot_id ||
      s.decision_boundary<=0 || s.decision_boundary!=f.decision_boundary ||
      s.closed_bar_time<=0 || s.closed_bar_time!=f.closed_bar_time ||
      s.closed_bar_time>=s.decision_boundary ||
      s.external_max_age_s<=0 ||
      !MathIsValidNumber(s.closed_bar_close) || s.closed_bar_close<=0.0 ||
      !MathIsValidNumber(s.equity) || s.equity<=0.0 ||
      s.symbol=="" || s.symbol!=f.symbol || f.timeframe!=(int)g_cfg.tf_exec ||
      s.timestamp<=0 || f.timestamp!=s.closed_bar_time)
   {
      LogMsg(LOG_WARN,"BRIDGE_OUT","Market/feature snapshot identity or closed-bar boundary mismatch; publication rejected.");
      return;
   }
   string temp_path=path+".tmp";
   // An orphan temp means publication previously stopped mid-flight. Preserve
   // it and the last complete destination for explicit recovery.
   if(FileIsExist(temp_path)) return;
   int h = FileOpen(temp_path, FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(h == INVALID_HANDLE) return;
   string payload=StringFormat("snapshot_id=%I64d\ndecision_boundary=%I64d\nclosed_bar_time=%I64d\ntimeframe=%d\nmax_age_s=%d\ntimestamp=%I64d\nsymbol=%s\nbid=%.5f\nask=%.5f\nspread=%.5f\natr14=%.5f\nstructure_dir=%d\nclose=%.5f\nequity=%.2f\nsession_state=%d\nschema_version=%d\n",
                               s.snapshot_id,(long)s.decision_boundary,(long)s.closed_bar_time,
                               f.timeframe,s.external_max_age_s,(long)s.timestamp,s.symbol,s.bid,s.ask,s.spread,
                               f.atr14,f.structure_dir,s.closed_bar_close,
                               s.equity,s.session_state,Amigo_SCHEMA_VERSION);
   uint written=FileWriteString(h,payload);
   bool complete=(written==(uint)StringLen(payload));
   FileFlush(h);
   FileClose(h);
   if(!complete) return;

   int verify=FileOpen(temp_path,FILE_READ|FILE_TXT|FILE_ANSI);
   if(verify==INVALID_HANDLE) return;
   string first=FileReadString(verify);
   string last="";
   while(!FileIsEnding(verify)) last=FileReadString(verify);
   bool verified=(StringFind(first,"snapshot_id=")==0 &&
                  StringFind(last,"schema_version=")==0 &&
                  FileSize(verify)>0);
   FileClose(verify);
   if(!verified) return;

   // No direct-write fallback: failed replacement leaves the prior artifact.
   // MQL5 does not document this as crash-durable or cross-process atomic.
   if(!FileMove(temp_path,0,path,FILE_REWRITE))
      LogMsg(LOG_WARN,"BRIDGE_OUT",StringFormat("Snapshot publication failed; prior artifact retained if replacement did not occur (err=%d)",GetLastError()));
}
//+------------------------------------------------------------------+
