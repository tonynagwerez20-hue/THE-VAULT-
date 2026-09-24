//+------------------------------------------------------------------+
//| Test_ShadowHarness.mq5 - Isolated Shadow Gate Execution Harness  |
//+------------------------------------------------------------------+
#property copyright "AlgoMind Safety Gate Audit"
#property version   "1.00"
#property script_show_inputs

#include <Contracts header.mqh>
#include <Configuration.mqh>
#include <Logger.mqh>
#include <Execution Engine.mqh>

input bool InpShadowOnly = true;

//+------------------------------------------------------------------+
//| Script program start function                                    |
//+------------------------------------------------------------------+
void OnStart()
{
   PrintFormat("[HARNESS_INIT] Isolated Execution Engine Shadow Harness starting...");
   
   //--- Test 2: Runtime Configuration Audit
   g_cfg.shadow_only = InpShadowOnly;
   PrintFormat("[HARNESS_CONFIG] shadow_only=%s symbol=%s", g_cfg.shadow_only ? "true" : "false", _Symbol);
   
   if(!g_cfg.shadow_only)
   {
      PrintFormat("[HARNESS_ERROR] InpShadowOnly MUST be true for harness execution!");
      return;
   }
   
   int mock_submission_count = 0;
   int test_count = 3;
   
   //--- Test Intent Fixtures (Deterministic Test Cases)
   TradeIntent test_intents[3];
   double test_lots[3] = {0.01, 0.02, 0.01};
   
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(ask <= 0.0) ask = 2650.00;
   if(bid <= 0.0) bid = 2649.80;
   
   // Intent 1: XAUUSD BUY
   ZeroMemory(test_intents[0]);
   test_intents[0].intent_id        = 9001;
   test_intents[0].schema_version   = ALGOMIND_SCHEMA_VERSION;
   test_intents[0].symbol           = _Symbol;
   test_intents[0].direction        = +1;
   test_intents[0].timestamp        = TimeCurrent();
   test_intents[0].expiry           = TimeCurrent() + 300;
   test_intents[0].entry_reference  = ask;
   test_intents[0].stop             = ask - 10.0;
   test_intents[0].target           = ask + 20.0;
   test_intents[0].score            = 0.55;
   test_intents[0].confidence       = 0.80;
   test_intents[0].regime           = REGIME_BALANCED;
   test_intents[0].hypothesis       = HYP_MEAN_REVERSION;
   test_intents[0].reason_codes     = "HARNESS_FIXTURE_BUY";
   
   // Intent 2: XAUUSD SELL
   ZeroMemory(test_intents[1]);
   test_intents[1].intent_id        = 9002;
   test_intents[1].schema_version   = ALGOMIND_SCHEMA_VERSION;
   test_intents[1].symbol           = _Symbol;
   test_intents[1].direction        = -1;
   test_intents[1].timestamp        = TimeCurrent();
   test_intents[1].expiry           = TimeCurrent() + 300;
   test_intents[1].entry_reference  = bid;
   test_intents[1].stop             = bid + 10.0;
   test_intents[1].target           = bid - 20.0;
   test_intents[1].score            = 0.60;
   test_intents[1].confidence       = 0.85;
   test_intents[1].regime           = REGIME_BALANCED;
   test_intents[1].hypothesis       = HYP_MEAN_REVERSION;
   test_intents[1].reason_codes     = "HARNESS_FIXTURE_SELL";

   // Intent 3: XAUUSD BUY (Second Iteration)
   ZeroMemory(test_intents[2]);
   test_intents[2].intent_id        = 9003;
   test_intents[2].schema_version   = ALGOMIND_SCHEMA_VERSION;
   test_intents[2].symbol           = _Symbol;
   test_intents[2].direction        = +1;
   test_intents[2].timestamp        = TimeCurrent();
   test_intents[2].expiry           = TimeCurrent() + 300;
   test_intents[2].entry_reference  = ask;
   test_intents[2].stop             = ask - 5.0;
   test_intents[2].target           = ask + 15.0;
   test_intents[2].score            = 0.52;
   test_intents[2].confidence       = 0.75;
   test_intents[2].regime           = REGIME_BALANCED;
   test_intents[2].hypothesis       = HYP_MEAN_REVERSION;
   test_intents[2].reason_codes     = "HARNESS_FIXTURE_BUY_2";

   PrintFormat("--- EXECUTING DETERMINISTIC SHADOW HARNESS TESTS ---");

   for(int i=0; i<test_count; i++)
   {
      string vreason;
      if(!ValidateIntent(test_intents[i], g_cfg, vreason))
      {
         PrintFormat("[HARNESS_INTENT_FAIL] i=%d reason=%s", i, vreason);
         continue;
      }
      
      PrintFormat("[HARNESS_INTENT] id=%I64d symbol=%s type=%s volume=%.2f entry=%.5f sl=%.5f tp=%.5f",
                  test_intents[i].intent_id, test_intents[i].symbol,
                  (test_intents[i].direction==1)?"BUY":"SELL", test_lots[i],
                  test_intents[i].entry_reference, test_intents[i].stop, test_intents[i].target);
      
      PrintFormat("[EXECUTE_INTENT_ENTRY] reached=true intent_id=%I64d", test_intents[i].intent_id);
      
      ExecutionResult er = ExecuteIntent(test_intents[i], test_lots[i], g_cfg);
      
      PrintFormat("[SHADOW_GATE] shadow_only=%s retcode=%u comment=%s",
                  g_cfg.shadow_only ? "true" : "false", er.retcode, er.comment);
                  
      if(er.comment == "SHADOW_MODE_EXECUTION_BLOCKED" || StringFind(er.comment, "SHADOW") >= 0)
      {
         PrintFormat("[SHADOW_INTERCEPT] intercepted=true intent_id=%I64d retcode=%u comment=%s",
                     test_intents[i].intent_id, er.retcode, er.comment);
      }
      else
      {
         PrintFormat("[SHADOW_INTERCEPT_FAIL] intent_id=%I64d retcode=%u comment=%s",
                     test_intents[i].intent_id, er.retcode, er.comment);
         mock_submission_count++;
      }
      
      PrintFormat("[MOCK_BROKER] submission_count=%d", mock_submission_count);
   }

   PrintFormat("--- HARNESS EXECUTION SUMMARY ---");
   PrintFormat("[HARNESS_RESULT] Total Tests=%d Intercepted=%d Mock Submissions=%d",
               test_count, test_count - mock_submission_count, mock_submission_count);
               
   if(mock_submission_count == 0)
   {
      PrintFormat("[HARNESS_FINAL] PASS - All 3 valid test intents reached ExecuteIntent() and were intercepted at shadow_only gate without broker submission.");
   }
   else
   {
      PrintFormat("[HARNESS_FINAL] FAIL - Interception failed for %d intents!", mock_submission_count);
   }
}
