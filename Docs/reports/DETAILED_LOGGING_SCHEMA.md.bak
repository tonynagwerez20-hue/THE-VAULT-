# DETAILED LOGGING SCHEMA SPECIFICATION
**AlgoMind / ASAP Retail Order-Flow System**

## 1. Governance & Structured Format
Every EA decision, trade intent, shadow evaluation, and rejection MUST produce a structured log entry.

## 2. Canonical Log Schema (`[ALGOMIND_DECISION]`)

```text
[ALGOMIND_DECISION]
decision_id                 = <UUID / Hash>
timestamp_utc               = YYYY-MM-DDTHH:MM:SS.sssZ
symbol                      = XAUUSD
broker                      = BrokerName
server                      = ServerName
account_mode                = MICRO / SMALL / STANDARD / PROPFIRM
balance                     = 1000.00
equity                      = 1000.00
margin_free                 = 950.00

regime                      = TREND_UP / BALANCED / EXPANSION / NO_TRADE
regime_confidence           = 0.85

MR_score                    = 0.42
MR_grade                    = B
continuation_score          = 0.78
continuation_grade          = A

footprint_quality           = PROXY
buy_activity                = 150.5
sell_activity               = 82.0
delta                       = 68.5
cumulative_delta            = 320.0
footprint_pressure          = 0.55
is_surge                    = 1
is_flip                     = 0
transition_event            = NEUTRAL_TO_BULLISH
persistence                 = 3
divergence                  = NONE
absorption_candidate        = 0
exhaustion_candidate        = 0

vwap                        = 2000.45
vwap_dev                    = 0.65
poc                         = 2000.50
vah                         = 2001.10
val                         = 1999.80
atr                         = 3.20

news_event_id               = US_CPI_20260923
news_state                  = EVENT_EXPIRED
news_match_status           = MATCHED

entry                       = 2001.20
sl                          = 1998.00
tp                          = 2007.60
rr                          = 2.00

requested_volume            = 0.05
minimum_volume              = 0.01
executed_volume             = 0.05

spread                      = 0.15
margin_req                  = 40.02
slippage                    = 0.00

action                      = ACTION_TRADE / ACTION_WAIT / ACTION_NO_TRADE
rejection_reason            = OK / SCORE_GATE / REGIME_HYP_MISMATCH / DQ_FATAL
```

## 3. Explicit Rejection Reason Codes
- `STRATEGY_GRADE_BELOW_MODE_THRESHOLD`
- `MANDATORY_CONDITION_FAILED`
- `NEWS_DATA_UNCONFIRMED`
- `NEWS_DATA_CONFLICT`
- `SPREAD_TOO_HIGH`
- `MINIMUM_VOLUME_RISK_TOO_HIGH`
- `INSUFFICIENT_MARGIN`
- `STALE_EXTERNAL_DATA`
- `MISSING_CRITICAL_FEATURE`
- `INVALID_STOP_DISTANCE`
- `REGIME_INCOMPATIBLE`
- `HARD_RISK_VETO`
