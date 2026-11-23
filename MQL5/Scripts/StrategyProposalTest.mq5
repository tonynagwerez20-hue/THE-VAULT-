// StrategyProposalTest.mq5 - TradeIntent proposal validation test
// Verifies GenerateProposals returns valid TradeIntent structures

#property strict

#include <Contracts header.mqh>
#include "Strategy_Framework.mqh"
#include "StrategyRegistration.mqh"

// Test globals
StrategyRegistry g_registry;
TradeIntent g_proposals[];

//+------------------------------------------------------------------+
int OnInit() {
    Print("Running StrategyProposalTest...\n");

    // Initialize registry
    if (!g_registry.Init()) {
        Print("Registry initialization failed\n");
        return INIT_FAILED;
    }

    // Register strategies
    ulong magic = 20260908;
    if (!RegisterStrategies(g_registry, magic)) {
        Print("Strategy registration failed\n");
        return INIT_FAILED;
    }

    // Test snapshot ID
    long snapshot_id = TimeCurrent();
    string symbol = _Symbol;
    int timeframe = PERIOD_M30;

    // Generate proposals
    int count = 0;
    bool result = g_registry.GenerateProposals(snapshot_id, symbol, timeframe, g_proposals, count);

    if (!result || count == 0) {
        Print("No proposals generated (result=" + (result ? "true" : "false") + ", count=" + count + ")\n");
        return INIT_FAILED;
    }

    // Validate each proposal
    for (int i = 0; i < count; i++) {
        TradeIntent p = g_proposals[i];
        Print("Proposal " + (i+1) + ": id=" + p.intent_id + ", dir=" + p.direction + ", regime=" + p.regime +
              ", conf=" + (p.confidence > 0 ? p.confidence : 0) + ", schema=" + p.schema_version);

        // Required fields check
        if (p.intent_id != snapshot_id) {
            Print("Intent ID mismatch\n");
            return INIT_FAILED;
        }
        if (p.snapshot_id != snapshot_id) {
            Print("Snapshot ID mismatch\n");
            return INIT_FAILED;
        }
        if (p.decision_id != snapshot_id || p.signal_id != snapshot_id || p.idempotency_key != snapshot_id) {
            Print("Decision ID / Signal ID / Idempotency Key binding invariant violated\n");
            return INIT_FAILED;
        }

        // CRITICAL: Validate that decision_id = signal_id = idempotency_key = snapshot_id
        // as per the P0 contract (decision_id should be from RiskBeginOpportunity)
        if (p.decision_id == snapshot_id && p.signal_id == snapshot_id && p.idempotency_key == snapshot_id) {
            Print("INFO: Decision ID binding invariant satisfied\n");
        } else {
            Print("INFO: Decision ID binding invariant violated - decision_id != signal_id != idempotency_key\n");
            return INIT_FAILED;
        }
        if (p.schema_version != Amigo_SCHEMA_VERSION) {
            Print("Schema version mismatch\n");
            return INIT_FAILED;
        }
        if (p.symbol != symbol) {
            Print("Symbol mismatch\n");
            return INIT_FAILED;
        }
        if (p.direction != 1 && p.direction != -1) {
            Print("Invalid direction\n");
            return INIT_FAILED;
        }
        if (p.regime == REGIME_NONE) {
            Print("Invalid regime\n");
            return INIT_FAILED;
        }

        // Add confidence validation
        if (p.confidence <= 0) {
            Print("Confidence value invalid or missing\n");
            return INIT_FAILED;
        }

        Print("Proposal validated successfully\n");
    }

    Print("StrategyProposalTest passed\n");
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason) {
    g_registry.Deinit();
}