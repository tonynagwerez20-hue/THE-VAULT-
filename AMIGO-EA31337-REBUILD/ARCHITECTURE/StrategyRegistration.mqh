// StrategyRegistration.mqh - Central strategy registration module
// Registers all concrete strategies with the StrategyRegistry

#include <Object.mqh>
#include <Contracts header.mqh>
#include "TrendStrategy.mqh"
#include "MeanReversionStrategy.mqh"

// Strategy Registration Function
bool RegisterStrategies(StrategyRegistry &registry, const ulong magic_number) {
    // Register TrendStrategy
    TrendStrategy *trend_strategy = new TrendStrategy("TrendStrategy", magic_number);
    trend_strategy.SetSymbol(_Symbol);
    trend_strategy.SetTimeframe(PERIOD_M30);
    if (!trend_strategy.ValidateInputs()) {
        Print("TrendStrategy validation failed");
        delete trend_strategy;
        return false;
    }
    if (!registry.RegisterStrategy(trend_strategy)) {
        Print("TrendStrategy registration failed");
        delete trend_strategy;
        return false;
    }

    // Register MeanReversionStrategy
    MeanReversionStrategy *mr_strategy = new MeanReversionStrategy("MeanReversionStrategy", magic_number);
    mr_strategy.SetSymbol(_Symbol);
    mr_strategy.SetTimeframe(PERIOD_M30);
    if (!mr_strategy.ValidateInputs()) {
        Print("MeanReversionStrategy validation failed");
        delete mr_strategy;
        return false;
    }
    if (!registry.RegisterStrategy(mr_strategy)) {
        Print("MeanReversionStrategy registration failed");
        delete mr_strategy;
        return false;
    }

    return true;
}
