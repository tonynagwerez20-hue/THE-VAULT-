#property strict

//--- Custom trailing-stop mode enumeration
enum ENUM_TRAILING_MODE
{
   TRAIL_NONE,
   TRAIL_FIXED,
   TRAIL_ATR,
   TRAIL_DYNAMIC_25_PERCENT
};

//--- Inputs are declared in main EA. This struct holds the resolved config.
struct AmigoConfig
{
   //--- Symbol
   string   symbol;

   //--- Timeframes (original)
   ENUM_TIMEFRAMES tf_exec;       // M5
   ENUM_TIMEFRAMES tf_context;    // M15
   ENUM_TIMEFRAMES tf_htf;        // H1

   //--- Timeframes (new – top-down multi-horizon)
   ENUM_TIMEFRAMES tf_m1;         // M1  – scalping horizon
   ENUM_TIMEFRAMES tf_m30;        // M30 – intraday swing
   ENUM_TIMEFRAMES tf_h4;         // H4  – swing / trend

   //--- Feature periods (per Math Spec S1)
   int      atr_period;           // 14
   int      swing_k;              // 2
   int      zscore_window;        // 20

   //--- VWAP / value
   double   value_area_pct;       // 0.70
   double   vwap_bin_price;       // 4 * Point for XAUUSD

   //--- Delta
   double   pressure_threshold;   // 0.25
   double   surge_threshold;      // 0.35 (Recalibrated from 0.60 for proxy fusion)

   //--- Strategy gate
   double   score_threshold;      // 0.65
   double   score_margin;         // 0.15

   //--- Regime
   double   regime_threshold;     // 0.60
   double   regime_hysteresis;    // 0.10
   int      regime_persistence;   // 2

   //--- Risk (per Math Spec S24)
   double   risk_per_trade_pct;   // 0.5
   double   daily_loss_pct;       // 2.0
   double   total_dd_pct;         // 5.0
   double   partial_rr;           // 2.0
   double   partial_fraction;     // 0.50
   double   trail_atr_mult;       // 1.5
   double   trail_activate_r;     // 1.0
   ENUM_TRAILING_MODE trail_mode; // Trailing mode

   //--- Spread
   double   max_spread_atr_pct;   // 0.10 of stop distance
   double   max_spread_points;    // 0 = disabled

   //--- Session (server time)
   int      session_start_hour;
   int      session_end_hour;

   //--- News
   int      news_mode;            // 0=OFF 1=FILTER 2=TRADE 3=HYBRID
   int      news_buffer_mins;     // 30

   //--- Min Lot Risk Override
   bool     allow_min_lot_override; // false = strict EA risk cap; true = allow min lot override
   double   max_allowed_distortion; // e.g. 5.0 = allow up to 5x risk distortion

   //--- External context influence caps (per Math Spec S27)
   double   options_max_influence; // 0.10
   double   cftc_max_influence;    // 0.05

   //--- ML
   bool     ml_enabled;            // false by default
   string   ml_model_path;

   //--- Bridge
   string   bridge_inbox;
   string   bridge_outbox;
   int      stale_threshold_s;     // seconds

   //--- Execution Mode Safety
   bool     shadow_only;           // true = SHADOW MODE (blocks live OrderSend calls)

   //--- Dual-Account Isolation Metadata (Additive)
   ulong    magic_number;          // Scoped Magic Number
   long     expected_login;        // Identity validation (0 = unconstrained/audit-only)
};

AmigoConfig g_cfg;
