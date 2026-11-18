#ifndef AMIGO_TRENDSTRATEGY_MQH
#define AMIGO_TRENDSTRATEGY_MQH
// TrendStrategy.mqh - Real-time trend detection strategy
// Implements MA-based trend detection with RSI confirmation for entry signals

#include <Object.mqh>
#include <Contracts header.mqh>
#include "Strategy_Framework.mqh"

class TrendStrategy : public Strategy {
protected:
    // Trend tracking
    double  m_ma_slow;
    double  m_ma_fast;
    int     m_ma_period;

    // RSI state
    double  m_rsi;
    int     m_rsi_period;

    // Signal state
    bool    m_trend_up;
    bool    m_trend_down;
    datetime m_last_signal_time;

    // Configuration
    double  m_signal_threshold;
    int     m_min_confirmation_bars;

public:
    TrendStrategy(const string name, const ulong magic)
        : Strategy(name, "Trend", magic),
          m_ma_slow(0), m_ma_fast(0), m_ma_period(20),
          m_rsi(0), m_rsi_period(14), m_trend_up(false), m_trend_down(false),
          m_last_signal_time(0), m_signal_threshold(0.5), m_min_confirmation_bars(3) {}

    virtual ~TrendStrategy() {}

    virtual void OnTick() override {
        m_trend_up = m_trend_down = false;
        if (!m_initialized || !m_enabled) return;

        datetime bar_time = iTime(m_symbol, (ENUM_TIMEFRAMES)m_timeframe, 1);
        if (bar_time <= 0) return;

        MqlRates rates[];
        if (CopyRates(m_symbol, (ENUM_TIMEFRAMES)m_timeframe, 1, m_ma_period, rates) == m_ma_period) {
            double sum_slow = 0, sum_fast = 0;
            int sz = ArraySize(rates);
            if (sz <= 0) return;
            for (int i = 0; i < sz; i++) {
                sum_slow += rates[i].close;
                if (i >= m_ma_period / 2) sum_fast += rates[i].close;
            }
            m_ma_slow = sum_slow / sz;
            int fast_len = sz / 2;
            m_ma_fast = (fast_len > 0) ? (sum_fast / fast_len) : m_ma_slow;
        }

        if(ArraySize(rates)!=m_ma_period) return;
        // Calculate RSI
        if (ArraySize(rates) < 2) return;
        double gains = 0, losses = 0;
        int rate_sz = ArraySize(rates);
        for (int i = 1; i < rate_sz; i++) {
            double change = rates[i].close - rates[i-1].close;
            if (change > 0) gains += change;
            else losses -= change;
        }
        double avg_gain = (gains > 0) ? gains / rate_sz : 0;
        double avg_loss = (losses > 0) ? losses / rate_sz : 0;
        m_rsi = (avg_gain+avg_loss>0) ? 100.0*avg_gain/(avg_gain+avg_loss) : 50.0;

        if (m_ma_fast > m_ma_slow) {
            m_trend_up = true;
            m_trend_down = false;
        } else if (m_ma_fast < m_ma_slow) {
            m_trend_up = false;
            m_trend_down = true;
        }
    }

    virtual bool GenerateProposal(const long snapshot_id, const string symbol, const int timeframe, TradeIntent &proposal) override {
        ZeroMemory(proposal);
        // intent_id and snapshot_id are pipeline-owned; strategy receives snapshot_id as immutable context
        proposal.schema_version = Amigo_SCHEMA_VERSION;
        proposal.strategy_version = 1;
        proposal.symbol = symbol;


        if (m_trend_up && m_rsi > 50 && m_rsi < 70) {
            proposal.direction = 1;
            proposal.hypothesis = HYP_CONTINUATION;
            proposal.horizon = HORIZON_SWING;
        } else if (m_trend_down && m_rsi > 30 && m_rsi < 50) {
            proposal.direction = -1;
            proposal.hypothesis = HYP_CONTINUATION;
            proposal.horizon = HORIZON_SWING;
        } else {
            return false;
        }

        proposal.regime = proposal.direction>0 ? REGIME_TREND_UP : REGIME_TREND_DOWN;
        proposal.confidence = m_rsi / 100.0;
        proposal.reason_codes = "MA_CROSS_RSI";

        // Proposal only: geometry and execution identity belong to the caller.
        if(!m_initialized || !m_enabled || symbol!=m_symbol || timeframe!=m_timeframe ||
           !MathIsValidNumber(proposal.confidence) || proposal.confidence<0 || proposal.confidence>1)
            return false;

        return true;
    }
};

#endif
