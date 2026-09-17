//+------------------------------------------------------------------+
//| ExternalContext.mqh - read external context, write market state  |
//+------------------------------------------------------------------+
#property strict

#include <Contracts header.mqh>
#include <Configuration.mqh>
#include <Logger.mqh>

//--- Read the external-context file written by Python.
//--- Format: one "key=value" per line, ANSI text, shared-read.
bool ReadExternalContext(string path, ExternalContext &ctx, string &err)
{
   err = "";

   //--- Staleness check: reject file if modified >120 seconds ago
   datetime file_time = (datetime)FileGetInteger(path, FILE_MODIFY_DATE, false);
   if(file_time > 0 && (TimeCurrent() - file_time > 120))
   {
      err = "FILE_STALE";
      ctx.data_quality |= DQ_STALE_EXTERNAL;
      return false;
   }

   int h = FileOpen(path, FILE_READ|FILE_TXT|FILE_ANSI|FILE_SHARE_READ);
   if(h == INVALID_HANDLE)
   {
      err = "FILE_OPEN_FAIL";
      return false;
   }

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
   ctx.news_event_ts            = 0;
   ctx.news_active_window       = false;
   ctx.news_surprise            = 0.0;
   ctx.news_relative_surprise   = 0.0;

   while(!FileIsEnding(h))
   {
      string line = FileReadString(h);
      int eq = StringFind(line, "=");
      if(eq <= 0) continue;

      string k = StringSubstr(line, 0, eq);
      string v = StringSubstr(line, eq + 1);
      StringTrimLeft(k);  StringTrimRight(k);
      StringTrimLeft(v);  StringTrimRight(v);

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
      else if(k == "news_ts")           ctx.news_event_ts          = (datetime)StringToInteger(v);
      else if(k == "news_active")       ctx.news_active_window     = (v == "1");
      else if(k == "news_surprise")     ctx.news_surprise          = StringToDouble(v);
      else if(k == "news_rel_surprise") ctx.news_relative_surprise = StringToDouble(v);
   }
   FileClose(h);

   //--- Validate schema version
   if(ctx.schema_version != ALGOMIND_SCHEMA_VERSION)
   {
      ctx.data_quality |= DQ_SCHEMA_MISMATCH;
   }

   //--- Point-in-time correctness: reject anything stamped in the future.
   datetime now = TimeCurrent();
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
   if(ctx.news_valid && ctx.news_event_ts > now)
   {
      ctx.news_valid    = false;
      ctx.data_quality |= DQ_STALE_EXTERNAL;
   }
   return true;
}

//--- Write the current market snapshot for Python to read.
//--- Format matches the Python bridge's key=value parser.
void WriteSnapshotForExternal(string path, const MarketSnapshot &s,
                              const FeatureSnapshot &f)
{
   int h = FileOpen(path, FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(h == INVALID_HANDLE) return;

   FileWriteString(h, StringFormat("snapshot_id=%I64d\n", s.snapshot_id));
   FileWriteString(h, StringFormat("timestamp=%d\n",     (int)s.timestamp));
   FileWriteString(h, StringFormat("symbol=%s\n",        s.symbol));
   FileWriteString(h, StringFormat("bid=%.5f\n",         s.bid));
   FileWriteString(h, StringFormat("ask=%.5f\n",         s.ask));
   FileWriteString(h, StringFormat("spread=%.5f\n",      s.spread));
   FileWriteString(h, StringFormat("atr14=%.5f\n",       f.atr14));
   FileWriteString(h, StringFormat("structure_dir=%d\n", f.structure_dir));
   FileWriteString(h, StringFormat("close=%.5f\n",       iClose(s.symbol, g_cfg.tf_exec, 1)));
   FileWriteString(h, StringFormat("equity=%.2f\n",      AccountInfoDouble(ACCOUNT_EQUITY)));
   FileWriteString(h, StringFormat("session_state=%d\n", s.session_state));
   FileWriteString(h, StringFormat("schema_version=%d\n", ALGOMIND_SCHEMA_VERSION));

   FileClose(h);
}
//+------------------------------------------------------------------+