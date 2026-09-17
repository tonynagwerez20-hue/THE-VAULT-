//+------------------------------------------------------------------+
//| Contract.mqh - Canonical data contracts (frozen Phase-0 schema)  |
//+------------------------------------------------------------------+
#property copyright "AlgoMind"
#property strict

#define ALGOMIND_SCHEMA_VERSION 100   // v1.0.0
#define ALGOMIND_MAX_REASON_CODES 16

//--- Regime enum (per Master Harmonized Spec §13)
enum ENUM_REGIME
{
   REGIME_NONE        = 0,
   REGIME_TREND_UP    = 1,
   REGIME_TREND_DOWN  = 2,
   REGIME_BALANCED    = 3,
   REGIME_EXPANSION   = 4,
   REGIME_EXHAUSTION  = 5,
   REGIME_NEWS        = 6,
   REGIME_NO_TRADE    = 7
};

//--- Hypothesis enum
enum ENUM_HYPOTHESIS
{
   HYP_NONE          = 0,
   HYP_CONTINUATION  = 1,
   HYP_MEAN_REVERSION= 2
};

//--- Decision action (frozen Phase-0 contract)
enum ENUM_ACTION
{
   ACTION_TRADE   = 1,
   ACTION_REDUCE  = 2,
   ACTION_WAIT    = 3,
   ACTION_NO_TRADE= 4
};

//--- Data quality flags (bitmask)
#define DQ_OK               0x0000
#define DQ_MISSING_TICKS    0x0001
#define DQ_STALE_EXTERNAL   0x0002
#define DQ_SCHEMA_MISMATCH  0x0004
#define DQ_CLOCK_MISMATCH   0x0008
#define DQ_BROKER_INVALID   0x0010
#define DQ_EXTERNAL_ABSENT  0x0020
#define DQ_MODEL_MISMATCH   0x0040
#define DQ_FATAL            0x8000

//--- Canonical market snapshot
struct MarketSnapshot
{
   long     snapshot_id;
   datetime timestamp;
   string   symbol;
   string   broker_symbol;
   double   bid;
   double   ask;
   double   spread;
   int      digits;
   double   point;
   double   tick_size;
   double   tick_value;
   double   contract_size;
   double   volume_min;
   double   volume_max;
   double   volume_step;
   double   stops_level;
   double   freeze_level;
   double   equity;
   double   balance;
   double   margin_free;
   int      session_state;
   uint     data_quality;
   int      schema_version;
};

//--- Regime state
struct RegimeState
{
   ENUM_REGIME regime;
   double      confidence;
   ENUM_HYPOTHESIS preferred;
   double      risk_modifier;
   string      reason_codes;
   datetime    timestamp;
};

//--- Trade intent
struct TradeIntent
{
   long            intent_id;
   int             schema_version;
   int             strategy_version;
   int             feature_version;
   int             model_version;   // 0 if no ML
   string          symbol;
   int             direction;       // +1 long, -1 short
   datetime        timestamp;
   datetime        expiry;
   double          entry_reference;
   double          stop;
   double          target;
   double          score;
   double          confidence;
   ENUM_REGIME     regime;
   ENUM_HYPOTHESIS hypothesis;
   string          reason_codes;
   double          risk_allocation;
   uint            data_quality;
};

//--- External context (from Python)
struct ExternalContext
{
   int      schema_version;
   datetime timestamp;
   uint     data_quality;

   //--- CFTC (per Mathematical Spec §23)
   bool     cftc_valid;
   datetime cftc_publication_ts;
   double   cftc_net_position;
   double   cftc_net_change;
   double   cftc_percentile;      // 0..100
   bool     cftc_extreme;         // percentile <=10 or >=90
   int      cftc_release_age_s;

   //--- Options (Pizzo-style, per Math Spec §22)
   bool     options_valid;
   datetime options_obs_ts;
   double   options_basis;        // GC - XAUUSD
   double   options_oi_concentration;
   double   options_strike_distance_atr; // nearest notable strike
   int      options_gamma_regime; // -1,0,+1 heuristic (context only)

   //--- News
   bool     news_valid;
   datetime news_event_ts;
   bool     news_active_window;
   double   news_surprise;
   double   news_relative_surprise;
};

//--- Feature snapshot (canonical feature vector)
struct FeatureSnapshot
{
   datetime timestamp;
   int      feature_version;

   //--- Price / volatility
   double   atr14;
   double   range_ratio;
   double   vol_percentile;

   //--- Structure
   int      structure_dir;        // -1/0/+1
   double   bos_age_bars;
   bool     bull_choch;
   bool     bear_choch;

   //--- VWAP / value
   double   vwap;
   double   dev_vwap_atr;
   double   poc;
   double   vah;
   double   val;
   int      value_state;          // -1 below, 0 inside, +1 above

   //--- Order flow (proxy — labelled)
   double   delta_a;
   double   delta_b;
   double   fusion;               // clipped -1..+1
   int      pressure_state;       // -1/0/+1
   bool     bull_flip;
   bool     bear_flip;
   bool     surge;
   int      persistence;

   //--- Liquidity
   int      last_sweep_dir;       // +1 high sweep, -1 low sweep
   bool     sweep_reject;

   //--- FVG
   bool     fvg_active_bull;
   bool     fvg_active_bear;
   double   fvg_fill_pct;         // point-in-time

   //--- Acceptance
   bool     acceptance_above;
   bool     acceptance_below;
};