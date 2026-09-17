//+------------------------------------------------------------------+
//| MLGate.mqh - ML gate hook (disabled by default)                  |
//|                                                                  |
//| Per D4 REQ-040 / D3 §21: ML is Phase 8, gate/ranker ONLY.        |
//| It may never bypass MQL5 hard risk (P-09). Failure to load,      |
//| out-of-range inference, or manifest mismatch must fail CLOSED.   |
//+------------------------------------------------------------------+
#property strict

#include <Contracts header.mqh>
#include <Configuration.mqh>
#include <Strategy Engine.mqh>

struct MLGateResult
{
   bool   available;   // false = ML not wired in
   bool   pass;        // true = allow, false = veto
   double score;       // 0..1 ranking signal
   string reason;
};

//--- Phase 8 hook. Returns a no-op when cfg.ml_enabled == false.
//--- When implemented, this function MUST:
//---   * load the ONNX/LightGBM model and its manifest;
//---   * verify feature names/order against the manifest hash;
//---   * build the tensor in canonical order;
//---   * validate output is finite and inside [0,1];
//---   * fail closed on any error.
MLGateResult MLGateEvaluate(const FeatureSnapshot &f,
                            const StrategyScores &s,
                            const AlgoMindConfig &cfg)
{
   MLGateResult r;
   r.available = false;
   r.pass      = true;
   r.score     = 0.5;
   r.reason    = "ML_DISABLED";

   if(!cfg.ml_enabled)
      return r;

   //--- Placeholder for Phase 8 model inference.
   //--- Until then, keep the deterministic system as the sole authority.
   r.available = false;
   r.pass      = true;
   r.score     = 0.5;
   r.reason    = "ML_NOT_IMPLEMENTED";
   return r;
}
//+------------------------------------------------------------------+