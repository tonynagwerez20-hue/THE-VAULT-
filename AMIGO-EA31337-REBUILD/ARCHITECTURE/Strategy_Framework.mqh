#ifndef AMIGO_STRATEGY_FRAMEWORK_MQH
#define AMIGO_STRATEGY_FRAMEWORK_MQH
// Strategy_Framework.mqh - Corrected, Minimal AMIGO Strategy Abstraction Layer
// Implements clean-room strategy proposal interface without execution or risk authority dependencies.

#include <Object.mqh>
#include <Contracts header.mqh>

// AMIGO Strategy Registration Interface (Pure Interface)
interface IAmigoStrategy {
    virtual bool Init() = 0;
    virtual void Deinit() = 0;
    virtual void OnTick() = 0;
    virtual bool IsEnabled() const = 0;
    virtual void Enable(bool state) = 0;
    // Proposals are identified by snapshot_id (decision_id)
    virtual bool GenerateProposal(const long snapshot_id, const string symbol, const int timeframe, TradeIntent &proposal) = 0;
    virtual const string GetName() const = 0;
    virtual const string GetType() const = 0;
    virtual ulong GetMagic() const = 0;
    virtual void SetSymbol(const string symbol) = 0;
    virtual void SetTimeframe(int timeframe) = 0;
    virtual bool ValidateInputs() const = 0;
};

// Strategy Registry & Proposal Aggregator (AMIGO-Owned)
class StrategyRegistry {
private:
    IAmigoStrategy *m_strategies[64];
    int             m_strategy_count;
    bool            m_is_initialized;

public:
    StrategyRegistry() : m_strategy_count(0), m_is_initialized(false) {
        for(int i=0;i<64;i++) m_strategies[i]=NULL;
    }

    ~StrategyRegistry() {
        Deinit();
    }

    bool Init() {
        if (m_is_initialized) return true;
        m_is_initialized = true;
        return true;
    }

    void Deinit() {
        if (!m_is_initialized) return;
        for (int i = 0; i < m_strategy_count; i++) {
            if (m_strategies[i] != NULL) {
                m_strategies[i].Deinit();
                delete m_strategies[i];
                m_strategies[i] = NULL;
            }
        }
        m_strategy_count = 0;
        m_is_initialized = false;
    }

    bool RegisterStrategy(IAmigoStrategy *strategy) {
        if (strategy == NULL || m_strategy_count >= 64) return false;
        if (!strategy.ValidateInputs()) return false;

        if (!strategy.Init()) return false;
        m_strategies[m_strategy_count] = strategy;
        m_strategy_count++;
        return true;
    }

    IAmigoStrategy *GetStrategy(const string name) {
        for (int i = 0; i < m_strategy_count; i++) {
            if (m_strategies[i] != NULL && StringCompare(m_strategies[i].GetName(), name) == 0) {
                return m_strategies[i];
            }
        }
        return NULL;
    }

    void OnTick() {
        if (!m_is_initialized) return;
        for (int i = 0; i < m_strategy_count; i++) {
            if (m_strategies[i] != NULL && m_strategies[i].IsEnabled()) {
                m_strategies[i].OnTick();
            }
        }
    }

    // Aggregates proposals across registered strategies and applies arbitration before final assembly
    bool GenerateProposals(const long snapshot_id, const string symbol, const int timeframe, TradeIntent &out_proposals[], int &out_count, const long decision_id=0, const ENUM_REGIME regime=REGIME_NO_TRADE, const uint data_quality=1) {
        out_count = 0;
        ArrayFree(out_proposals);
        if (!m_is_initialized || m_strategy_count == 0 || snapshot_id<=0 || decision_id<=0 || data_quality!=0 ||
            regime==REGIME_NO_TRADE || regime==REGIME_NEWS || regime==REGIME_NONE || regime==REGIME_EXPANSION) return false;

        // Step 1: Collect raw strategy proposals
        for (int i = 0; i < m_strategy_count; i++) {
            if (m_strategies[i] == NULL || !m_strategies[i].IsEnabled()) continue;

            TradeIntent prop;
            ZeroMemory(prop);
            // Strategy fills TradeIntent with strategy-owned fields only (no intent_id/snapshot_id)
            if (m_strategies[i].GenerateProposal(snapshot_id, symbol, timeframe, prop)) {
                bool compatible=(prop.hypothesis==HYP_CONTINUATION &&
                    ((regime==REGIME_TREND_UP && prop.direction==1) || (regime==REGIME_TREND_DOWN && prop.direction==-1))) ||
                    (prop.hypothesis==HYP_MEAN_REVERSION && regime==REGIME_BALANCED);
                if(!compatible) continue;
                int sz = ArraySize(out_proposals);
                ArrayResize(out_proposals, sz + 1);
                out_proposals[sz] = prop;
                out_count++;
            }
        }
        if (out_count == 0) return false;

        // ---------- Arbitration Rules ----------
        // 1. Reject if any proposal has zero direction (empty proposal)
        for (int i = 0; i < out_count; i++) {
            if (out_proposals[i].direction == 0) {
                return false; // NO_TRADE due to empty proposal
            }
        }

        // 2. Detect opposing directions (both BUY and SELL present)
        bool has_buy = false;
        bool has_sell = false;
        for (int i = 0; i < out_count; i++) {
            if (out_proposals[i].direction > 0) has_buy = true;
            if (out_proposals[i].direction < 0) has_sell = true;
        }
        if (has_buy && has_sell) {
            return false; // NO_TRADE due to opposing directions
        }

        // 3. Detect duplicate proposals (same direction and identical entry_reference)
        for (int i = 0; i < out_count; i++) {
            for (int j = i + 1; j < out_count; j++) {
                if (out_proposals[i].direction == out_proposals[j].direction &&
                    MathAbs(out_proposals[i].entry_reference - out_proposals[j].entry_reference) < 1e-6) {
                    return false; // NO_TRADE due to duplicate proposals
                }
            }
        }

        // No cross-family calibration exists. Multiple proposals fail closed.
        if(out_count!=1) return false;

        // ---------- Identity Assignment (Model B / Decision ID Binding) ----------
        TradeIntent p = out_proposals[0];
        p.intent_id = snapshot_id;
        p.snapshot_id = snapshot_id;
        // CRITICAL FIX: Preserve authoritative risk decision_id from RiskBeginOpportunity()
        // Do NOT overwrite with snapshot_id to maintain P0 identity contract invariant:
        // decision_id = signal_id = idempotency_key
        p.decision_id = decision_id; // Keep bound per P0 contract (CURRENT STATE)
        p.signal_id = p.decision_id;  // Alias to decision_id
        p.idempotency_key = p.decision_id; // Alias to decision_id

        // Log identity binding information for audit
        Print("Identity binding: intent_id=" + (string)p.intent_id + " decision_id=" + (string)p.decision_id + " signal_id=" + (string)p.signal_id + " idempotency_key=" + (string)p.idempotency_key);

        // CRITICAL: Verify that decision_id = signal_id = idempotency_key
        if (p.decision_id == p.signal_id && p.decision_id == p.idempotency_key) {
            Print("SUCCESS: P0 identity contract preserved\n");
        } else {
            Print("FAIL: P0 identity contract violated - decision_id != signal_id != idempotency_key\n");
            return false;
        }

        out_proposals[0]=p;
        // Return a proposal; execution geometry is still assembled by its owner.
        return true;
    }
};

// Minimal Strategy Base Class (Implementation Helper)
class Strategy : public IAmigoStrategy {
protected:
    string  m_name;
    string  m_type;
    ulong   m_magic;
    string  m_symbol;
    int     m_timeframe;
    bool    m_enabled;
    bool    m_initialized;

public:
    Strategy(const string name, const string type, const ulong magic)
        : m_name(name), m_type(type), m_magic(magic),
          m_symbol(""), m_timeframe(0), m_enabled(true), m_initialized(false) {}

    virtual ~Strategy() {}

    virtual bool Init() override {
        m_initialized = true;
        return true;
    }

    virtual void Deinit() override {
        m_initialized = false;
    }

    virtual void OnTick() override {}

    virtual bool IsEnabled() const override { return m_enabled; }
    virtual void Enable(bool state) override { m_enabled = state; }

    virtual const string GetName() const override { return m_name; }
    virtual const string GetType() const override { return m_type; }
    virtual ulong GetMagic() const override { return m_magic; }

    virtual void SetSymbol(const string symbol) override { m_symbol = symbol; }
    virtual void SetTimeframe(int timeframe) override { m_timeframe = timeframe; }

    virtual bool ValidateInputs() const override {
        if (m_name == "" || m_type == "" || m_magic == 0) return false;
        if (m_symbol == "" || m_timeframe <= 0) return false;
        return true;
    }

    virtual bool GenerateProposal(const long snapshot_id, const string symbol, const int timeframe, TradeIntent &proposal) override {
        return false;
    }
};

// Strategy Integration Facade
class StrategyManager {
private:
    StrategyRegistry m_registry;

public:
    StrategyManager() {}
    ~StrategyManager() {}

    bool Initialize() {
        return m_registry.Init();
    }

    void Deinitialize() {
        m_registry.Deinit();
    }

    bool Register(IAmigoStrategy *strategy) {
        return m_registry.RegisterStrategy(strategy);
    }

    void OnTick() {
        m_registry.OnTick();
    }

    bool EvaluateProposals(const long snapshot_id, const string symbol, const int timeframe, TradeIntent &out_proposals[], int &out_count, const long decision_id=0, const ENUM_REGIME regime=REGIME_NO_TRADE, const uint data_quality=1) {
        return m_registry.GenerateProposals(snapshot_id, symbol, timeframe, out_proposals, out_count, decision_id, regime, data_quality);
    }
};


#endif
