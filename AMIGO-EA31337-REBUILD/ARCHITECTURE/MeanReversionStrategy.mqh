#ifndef AMIGO_MEANREVERSIONSTRATEGY_MQH
#define AMIGO_MEANREVERSIONSTRATEGY_MQH
// MeanReversionStrategy.mqh - RSI-based mean reversion strategy
// Implements RSI reversal detection for potential mean-reversion opportunities

#include <Object.mqh>
#include <Contracts header.mqh>
#include "Strategy_Framework.mqh"

class MeanReversionStrategy : public Strategy {
protected:
    double  m_rsi;
    int     m_rsi_period;
    bool    m_bull_divergence;
    bool    m_bear_divergence;
    datetime m_last_signal_time;
    double  m_overbought_threshold;
    double  m_oversold_threshold;
    int     m_min_confirmation_bars;

public:
    MeanReversionStrategy(const string name, const ulong magic)
        : Strategy(name, "MeanReversion", magic),
          m_rsi(0), m_rsi_period(14), m_bull_divergence(false), m_bear_divergence(false),
          m_last_signal_time(0), m_overbought_threshold(70.0), m_oversold_threshold(30.0),
          m_min_confirmation_bars(3) {}

    virtual ~MeanReversionStrategy() {}

    virtual void OnTick() override {
        m_bull_divergence = m_bear_divergence = false;
        if (!m_initialized || !m_enabled) return;

        datetime bar_time = iTime(m_symbol, (ENUM_TIMEFRAMES)m_timeframe, 1);
        if (bar_time <= 0) return;

        MqlRates rates[];
        if (CopyRates(m_symbol, (ENUM_TIMEFRAMES)m_timeframe, 1, m_rsi_period+1, rates) != m_rsi_period+1) return;

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

        m_bull_divergence = (m_rsi < m_overbought_threshold) && (rates[rate_sz-1].close < rates[rate_sz-2].close);
        m_bear_divergence = (m_rsi > m_oversold_threshold) && (rates[rate_sz-1].close > rates[rate_sz-2].close);
    }

    virtual bool GenerateProposal(const long snapshot_id, const string symbol, const int timeframe, TradeIntent &proposal) override {
        ZeroMemory(proposal);
        // intent_id and snapshot_id are pipeline-owned; strategy receives snapshot_id as immutable context
        proposal.schema_version = Amigo_SCHEMA_VERSION;
        proposal.strategy_version = 1;
        proposal.symbol = symbol;


        if (m_bull_divergence) {
            proposal.direction = 1;
            proposal.hypothesis = HYP_MEAN_REVERSION;
            proposal.horizon = HORIZON_SCALPING;
        } else if (m_bear_divergence) {
            proposal.direction = -1;
            proposal.hypothesis = HYP_MEAN_REVERSION;
            proposal.horizon = HORIZON_SCALPING;
        } else {
            return false;
        }

        proposal.regime = REGIME_BALANCED;
        proposal.confidence = 1.0 - (m_rsi / 100.0);
        proposal.reason_codes = "RSI_REVERSAL";

        // Proposal only: geometry and execution identity belong to the caller.
        if(!m_initialized || !m_enabled || symbol!=m_symbol || timeframe!=m_timeframe ||
           !MathIsValidNumber(proposal.confidence) || proposal.confidence<0 || proposal.confidence>1)
            return false;

        return true;
    }
};

#endif
