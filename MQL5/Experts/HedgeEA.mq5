//+------------------------------------------------------------------+
//|                                                     HedgeEA.mq5  |
//|                                    Hedge Trading System MT5 EA   |
//|                                  Direct ZMQ DLL Implementation   |
//+------------------------------------------------------------------+
#property copyright "Hedge Trading System"
#property version   "2.01"
#property strict

//+------------------------------------------------------------------+
//|   USER ACTION: Uncomment the line below to DISABLE DLL requirement 
//|   (Required for Strategy Tester backtesting with CSV signals)
//+------------------------------------------------------------------+
//#define DISABLE_ZMQ  // Comment this line ONLY for LIVE trading with ZMQ

//+------------------------------------------------------------------+
//| Log levels enum (Must be at the very top)                        |
//+------------------------------------------------------------------+
enum ENUM_LOG_LEVEL
{
   LOG_LEVEL_DEBUG = 0,
   LOG_LEVEL_INFO = 1,
   LOG_LEVEL_WARNING = 2,
   LOG_LEVEL_ERROR = 3
};

//+------------------------------------------------------------------+
//| Signal Data Structure                                            |
//+------------------------------------------------------------------+
struct SignalData
{
   string   id;            // Unique ID
   string   action;        // LONG, SHORT, CLOSE_LONG, CLOSE_SHORT, REVERSE
   string   symbol;        // Symbol (e.g. XAUUSD)
   double   price;         // Signal Price
   double   sl;            // Stop Loss
   double   tp;            // Take Profit (NEW)
   double   lots;          // Lot Size
   string   bias;          // BIAS (BULLISH/BEARISH)
   long     timestamp;     // Signal Timestamp
};

//+------------------------------------------------------------------+
//| ZeroMQ DLL Imports (Direct)                                      |
//+------------------------------------------------------------------+
#ifndef DISABLE_ZMQ
#import "libzmq.dll"
   long zmq_ctx_new();
   int zmq_ctx_destroy(long context);
   long zmq_socket(long context, int type);
   int zmq_close(long socket);
   int zmq_connect(long socket, const uchar &endpoint[]);
   int zmq_bind(long socket, const uchar &endpoint[]);
   int zmq_setsockopt(long socket, int option, const uchar &value[], int size);
   int zmq_recv(long socket, uchar &buffer[], int length, int flags);
   int zmq_send(long socket, const uchar &buffer[], int length, int flags);
#import
#endif

// ZMQ Constants
#define ZMQ_SUB 2
#define ZMQ_REP 4
#define ZMQ_SUBSCRIBE 6
#define ZMQ_RCVTIMEO 27
#define ZMQ_SNDTIMEO 28
#define ZMQ_DONTWAIT 1

//+------------------------------------------------------------------+
//| Function Prototypes                                              |
//+------------------------------------------------------------------+
bool InitZMQ();
void CheckForSignals();
void CheckHeartbeat();
void ProcessSignalQueue();
int ZmqSetSockOpt(long socket, int option, int value);
int ZmqSetSockOpt(long socket, int option, const uchar &value[]);
void ProcessSignal(string jsonSignal);
bool ParseSignal(string json, SignalData &signal);
bool ValidateSignal(SignalData &signal);
bool CheckRiskLimits(SignalData &signal);
void ExecuteTrade(SignalData &signal);
void ClosePosition(SignalData &signal);
void UpdateTrailingStops();
int CountOpenPositions();
double GetDailyPnL();
void CheckDailyReset();
double NormalizeLots(double lots);
string ExtractStringValue(string json, string key);
double ExtractDoubleValue(string json, string key);
void LogDebug(string message);
void LogInfo(string message);
void LogWarning(string message);
void LogError(string message);
string GetOpenPositionsJson();
string GetHistoryDealsJson(int days);
void CheckForOfflineSignals();

//+------------------------------------------------------------------+
//| Input Parameters                                                 |
//+------------------------------------------------------------------+

// ZeroMQ Settings
input string   ZMQ_HOST = "localhost";          // ZeroMQ Server Host
input int      ZMQ_PORT = 5555;                 // ZeroMQ Server Port
input int      ZMQ_HB_PORT = 5557;              // ZeroMQ Heartbeat Port
input string   ZMQ_TOPIC = "SIGNAL";            // Signal Topic

// Risk Management
input double   MAX_LOT_SIZE = 1.0;              // Maximum Lot Size
input int      MAX_OPEN_POSITIONS = 1;          // Maximum Open Positions (1 for dynamic exits)
input double   MAX_DAILY_DRAWDOWN_PCT = 2.5;    // Max Daily Drawdown %

// Trailing Stop Loss
input bool     ENABLE_TRAILING_SL = true;       // Enable Trailing Stop Loss
input double   TRAILING_STOP_PIPS = 20.0;       // Trailing Stop Distance (pips)
input double   TRAILING_STEP_PIPS = 5.0;        // Trailing Step (pips)

// Execution Settings
input int      SLIPPAGE_POINTS = 10;            // Maximum Slippage (points)
input int      MAGIC_NUMBER = 123456;           // Magic Number
input string   TRADE_COMMENT = "HedgeEA";       // Trade Comment
input int      REVERSAL_DELAY_MS = 500;         // Delay between close and reversal (ms)

// Backtesting / Replay Mode
input bool     BACKTEST_MODE = false;           // Enable Offline Signal Loading (CSV)
input string   BACKTEST_FILE = "backtest_signals.csv"; // Signal file in MQL5/Files
input string   ISIGNAL_FILE = "isignals_backtest.csv"; // Forensic iSignal file
input int      SIGNAL_TIME_SHIFT = 0;           // Shift signal time in hours (e.g. +2, -5)
input bool     ENABLE_VISUAL_REPLAY = false;    // Bypass time checks for visual backtesting

// Logging
input ENUM_LOG_LEVEL LOG_LEVEL = LOG_LEVEL_INFO;  // Log Level
input bool     ENABLE_FILE_LOG = true;          // Enable File Logging

//+------------------------------------------------------------------+
//| Global Variables                                                 |
//+------------------------------------------------------------------+

long zmqContext = 0;
long zmqSubscriber = 0;
long zmqHeartbeat = 0;
bool zmqConnected = false;

// Operating State
bool   IsBacktestActive = false;       // Auto-detected or forced via input
// Signal Queue
string signalQueue[];
int queueHead = 0;
int queueTail = 0;
#define MAX_QUEUE_SIZE 50

double dailyStartBalance = 0.0;
datetime currentDay = 0;

// Position tracking
ulong  currentPositionTicket = 0;
string currentPositionDirection = "";  // "LONG" or "SHORT"
long   lastProcessedLine = 0;          // Changed to long to avoid truncation warnings

// Forensic State (iSignals)
string g_forensic_layers[6] = {"N/A", "N/A", "N/A", "N/A", "N/A", "N/A"};
string g_forensic_action = "WAITING";
string g_forensic_reason = "No data";
datetime g_last_forensic_time = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   Print("=== HedgeEA Initialization (Direct ZMQ v2.03-TIMEPARSE) ===");
   
   // Set Timer (Every 1 second) for fallback signal checking
   EventSetTimer(1);
   
   // Initialize daily tracking
   dailyStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   currentDay = TimeCurrent();
   
   // Auto-detect environment
   IsBacktestActive = BACKTEST_MODE || (bool)MQLInfoInteger(MQL_TESTER);
   
   // Initialize ZeroMQ (Only if NOT in backtest mode)
#ifndef DISABLE_ZMQ
   if(!IsBacktestActive)
   {
      if(!InitZMQ())
      {
         Print("ERROR: Failed to initialize ZeroMQ connection");
         return(INIT_FAILED);
      }
      LogInfo(StringFormat("Listening on %s:%d for topic '%s'", ZMQ_HOST, ZMQ_PORT, ZMQ_TOPIC));
   }
   else
   {
      Print(">>> HedgeEA: BACKTEST MODE ACTIVE <<<");
      Print(">>> Searching for signals in Common Folder: ", BACKTEST_FILE);
   }
#else
   if(!IsBacktestActive)
   {
      Print("ERROR: ZMQ is disabled via macro. Cannot run live.");
      return(INIT_FAILED);
   }
   else
   {
      Print(">>> HedgeEA: BACKTEST MODE ACTIVE (ZMQ Disabled) <<<");
      Print(">>> Searching for signals in Common Folder: ", BACKTEST_FILE);
   }
#endif
   
   LogInfo(StringFormat("Risk Limits: MaxLots=%.2f, MaxPositions=%d, MaxDD=%.1f%%", 
           MAX_LOT_SIZE, MAX_OPEN_POSITIONS, MAX_DAILY_DRAWDOWN_PCT));
   
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   LogInfo("HedgeEA shutting down...");
   
   // Kill timer
   EventKillTimer();
   
   // Cleanup ZeroMQ (Only if it was connected)
#ifndef DISABLE_ZMQ
   if(zmqConnected && !IsBacktestActive)
   {
      if(zmqSubscriber != 0)
         zmq_close(zmqSubscriber);
      if(zmqHeartbeat != 0)
         zmq_close(zmqHeartbeat);
      if(zmqContext != 0)
         zmq_ctx_destroy(zmqContext);
      
      zmqConnected = false;
   }
#endif
   
   Print("=== HedgeEA Deinitialized ===");
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   // Check if we need to reset daily tracking
   CheckDailyReset();
   
   // Update trailing stop loss for open positions
   if(ENABLE_TRAILING_SL)
      UpdateTrailingStops();
   
   // Check for new signals
   if(IsBacktestActive)
   {
      CheckForOfflineSignals();
      CheckForForensicSignals();
   }
   else
      CheckForSignals();
   
   // Process queued signals
   ProcessSignalQueue();
   
   // Respond to heartbeats (skip in backtest)
#ifndef DISABLE_ZMQ
   if(!IsBacktestActive)
      CheckHeartbeat();
#endif
}

//+------------------------------------------------------------------+
//| Timer function for fallback processing                           |
//+------------------------------------------------------------------+
void OnTimer()
{
   if(IsBacktestActive)
   {
      CheckForOfflineSignals();
      CheckForForensicSignals();
      ProcessSignalQueue();
   }
}

//+------------------------------------------------------------------+
//| Initialize ZeroMQ Connection                                     |
//+------------------------------------------------------------------+
bool InitZMQ()
{
#ifndef DISABLE_ZMQ
   Print("DEBUG: Starting InitZMQ...");
   // Create ZeroMQ context
   zmqContext = zmq_ctx_new();
   if(zmqContext == 0)
   {
      LogError("Failed to create ZMQ context");
      return false;
   }
   Print("DEBUG: Context Created: ", zmqContext);
   
   // Create subscriber socket
   zmqSubscriber = zmq_socket(zmqContext, ZMQ_SUB);
   if(zmqSubscriber == 0)
   {
      LogError("Failed to create ZMQ subscriber socket");
      return false;
   }
   Print("DEBUG: SUB Socket Created");
   
   // Set receive timeout to 0 (non-blocking)
   int timeout = 0;
   if(ZmqSetSockOpt(zmqSubscriber, ZMQ_RCVTIMEO, timeout) != 0)
   {
      LogError("Failed to set RCVTIMEO");
      return false;
   }
   
   // Connect to publisher
   string endpoint = StringFormat("tcp://%s:%d", ZMQ_HOST, ZMQ_PORT);
   uchar endpointBytes[];
   StringToCharArray(endpoint, endpointBytes);
   ArrayResize(endpointBytes, ArraySize(endpointBytes) - 1); // Remove null terminator
   
   Print("DEBUG: Connecting SUB to ", endpoint);
   if(zmq_connect(zmqSubscriber, endpointBytes) != 0)
   {
      LogError(StringFormat("Failed to connect to %s", endpoint));
      
      // Get error number (zmq_errno is not imported, but return value is non-zero)
      return false;
   }
   Print("DEBUG: SUB Connected OK");
   
   // Subscribe to topic
   uchar topicBytes[];
   StringToCharArray(ZMQ_TOPIC, topicBytes);
   ArrayResize(topicBytes, ArraySize(topicBytes) - 1); // Remove null terminator
   
   if(ZmqSetSockOpt(zmqSubscriber, ZMQ_SUBSCRIBE, topicBytes) != 0)
   {
      LogError(StringFormat("Failed to subscribe to topic '%s'", ZMQ_TOPIC));
      return false;
   }
   
   // Create heartbeat REP socket
   zmqHeartbeat = zmq_socket(zmqContext, ZMQ_REP);
   if(zmqHeartbeat == 0)
   {
      LogError("Failed to create heartbeat socket");
      return false;
   }
   
   ZmqSetSockOpt(zmqHeartbeat, ZMQ_RCVTIMEO, 1); // Fast non-blocking
   ZmqSetSockOpt(zmqHeartbeat, ZMQ_SNDTIMEO, 1000);
   
   string hbEndpoint = StringFormat("tcp://*:%d", ZMQ_HB_PORT);
   uchar hbBytes[];
   StringToCharArray(hbEndpoint, hbBytes);
   ArrayResize(hbBytes, ArraySize(hbBytes)-1);
   
   Print("DEBUG: Attempting to BIND Heartbeat to ", hbEndpoint);
   if(zmq_bind(zmqHeartbeat, hbBytes) != 0)
   {
      LogError(StringFormat("Failed to bind heartbeat to %s", hbEndpoint));
      return false;
   }
   Print("DEBUG: Heartbeat Bound Successfully");
   
   zmqConnected = true;
   LogInfo("ZeroMQ connection established successfully");
   return true;
#else
   return true;
#endif
}

//+------------------------------------------------------------------+
//| Check for incoming signals                                       |
//+------------------------------------------------------------------+
void CheckForSignals()
{
#ifndef DISABLE_ZMQ
   if(!zmqConnected)
      return;
   
   uchar buffer[4096];
   ArrayInitialize(buffer, 0);
   
   // Non-blocking receive
   int bytesReceived = zmq_recv(zmqSubscriber, buffer, 4096, ZMQ_DONTWAIT);
   
   if(bytesReceived > 0)
   {
      string message = CharArrayToString(buffer, 0, bytesReceived);
      
      // Skip topic, extract JSON
      int spacePos = StringFind(message, " ");
      if(spacePos > 0)
      {
         string jsonData = StringSubstr(message, spacePos + 1);
         
         // Push to queue instead of processing immediately
         int nextTail = (queueTail + 1) % MAX_QUEUE_SIZE;
         if(nextTail != queueHead)
         {
            signalQueue[queueTail] = jsonData;
            queueTail = nextTail;
            LogDebug("Signal added to queue");
         }
         else
         {
            LogWarning("Signal queue full! Dropping signal.");
         }
      }
   }
#endif
}

//+------------------------------------------------------------------+
//| Respond to Heartbeat Pings and Handle REQ/REP Messages          |
//+------------------------------------------------------------------+
void CheckHeartbeat()
{
#ifndef DISABLE_ZMQ
   if(!zmqConnected || zmqHeartbeat == 0) return;
   
   uchar hbBuf[4096];  // Increased buffer for JSON messages
   ArrayInitialize(hbBuf, 0);
   int rec = zmq_recv(zmqHeartbeat, hbBuf, 4096, ZMQ_DONTWAIT);
   if(rec > 0)
   {
      string msg = CharArrayToString(hbBuf, 0, rec);
      
      // Handle simple PING
      if(msg == "PING")
      {
         uchar resp[];
         StringToCharArray("PONG", resp);
         ArrayResize(resp, 4);
         zmq_send(zmqHeartbeat, resp, 4, 0);
         return;
      }
      
      // Try to parse as JSON request
      string requestType = ExtractStringValue(msg, "type");
      
      if(requestType == "SIGNAL")
      {
         // Handle signal execution request with acknowledgment
         SignalData signal;
         if(ParseSignal(msg, signal))
         {
            if(ValidateSignal(signal) && CheckRiskLimits(signal))
            {
               // Execute trade
               MqlTradeRequest request;
               MqlTradeResult result;
               ZeroMemory(request);
               ZeroMemory(result);
               
               request.action = TRADE_ACTION_DEAL;
               request.symbol = signal.symbol;
               request.volume = NormalizeLots(signal.lots);
               request.type = (signal.action == "LONG") ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
               request.price = (signal.action == "LONG") ? SymbolInfoDouble(signal.symbol, SYMBOL_ASK) : SymbolInfoDouble(signal.symbol, SYMBOL_BID);
               request.sl = signal.sl;
               request.tp = 0;
               request.deviation = SLIPPAGE_POINTS;
               request.magic = MAGIC_NUMBER;
               request.comment = TRADE_COMMENT;
               request.type_filling = ORDER_FILLING_IOC;
               
               if(OrderSend(request, result) && result.retcode == TRADE_RETCODE_DONE)
               {
                  // Success - send acknowledgment
                  string ack = StringFormat("{\"status\":\"SUCCESS\",\"ticket\":%I64u,\"execution_price\":%.5f,\"timestamp\":\"%s\"}",
                                          result.order, result.price, TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS));
                  uchar ackBytes[];
                  StringToCharArray(ack, ackBytes);
                  ArrayResize(ackBytes, ArraySize(ackBytes) - 1);
                  zmq_send(zmqHeartbeat, ackBytes, ArraySize(ackBytes), 0);
                  
                  LogInfo(StringFormat("Signal executed with ack: Ticket %I64u", result.order));
               }
               else
               {
                  // Failure - send error
                  string ack = StringFormat("{\"status\":\"FAILED\",\"error\":\"%s\",\"retcode\":%u}",
                                          result.comment, result.retcode);
                  uchar ackBytes[];
                  StringToCharArray(ack, ackBytes);
                  ArrayResize(ackBytes, ArraySize(ackBytes) - 1);
                  zmq_send(zmqHeartbeat, ackBytes, ArraySize(ackBytes), 0);
                  
                  LogError(StringFormat("Signal execution failed: %s", result.comment));
               }
            }
            else
            {
               // Validation failed
               string ack = "{\"status\":\"FAILED\",\"error\":\"Validation or risk limit check failed\"}";
               uchar ackBytes[];
               StringToCharArray(ack, ackBytes);
               ArrayResize(ackBytes, ArraySize(ackBytes) - 1);
               zmq_send(zmqHeartbeat, ackBytes, ArraySize(ackBytes), 0);
            }
         }
         else
         {
            // Parse failed
            string ack = "{\"status\":\"FAILED\",\"error\":\"Failed to parse signal JSON\"}";
            uchar ackBytes[];
            StringToCharArray(ack, ackBytes);
            ArrayResize(ackBytes, ArraySize(ackBytes) - 1);
            zmq_send(zmqHeartbeat, ackBytes, ArraySize(ackBytes), 0);
         }
      }
      else if(requestType == "GET_BALANCE")
      {
         // Handle balance query
         double balance = AccountInfoDouble(ACCOUNT_BALANCE);
         double equity = AccountInfoDouble(ACCOUNT_EQUITY);
         double marginFree = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
         
         string response = StringFormat("{\"status\":\"SUCCESS\",\"balance\":%.2f,\"equity\":%.2f,\"margin_free\":%.2f}",
                                       balance, equity, marginFree);
         uchar respBytes[];
         StringToCharArray(response, respBytes);
         ArrayResize(respBytes, ArraySize(respBytes) - 1);
         zmq_send(zmqHeartbeat, respBytes, ArraySize(respBytes), 0);
         
         LogDebug(StringFormat("Balance query: %.2f", balance));
      }
      else if(requestType == "GET_POSITIONS")
      {
         string response = GetOpenPositionsJson();
         uchar respBytes[];
         StringToCharArray(response, respBytes);
         ArrayResize(respBytes, ArraySize(respBytes) - 1);
         zmq_send(zmqHeartbeat, respBytes, ArraySize(respBytes), 0);
      }
      else if(requestType == "GET_HISTORY")
      {
         int days = (int)ExtractDoubleValue(msg, "days");
         if(days <= 0) days = 7;
         
         string response = GetHistoryDealsJson(days);
         uchar respBytes[];
         StringToCharArray(response, respBytes);
         ArrayResize(respBytes, ArraySize(respBytes) - 1);
         zmq_send(zmqHeartbeat, respBytes, ArraySize(respBytes), 0);
      }
      else
      {
         // Unknown request type
         string ack = "{\"status\":\"ERROR\",\"error\":\"Unknown request type\"}";
         uchar ackBytes[];
         StringToCharArray(ack, ackBytes);
         ArrayResize(ackBytes, ArraySize(ackBytes) - 1);
         zmq_send(zmqHeartbeat, ackBytes, ArraySize(ackBytes), 0);
      }
   }
#endif
}

//+------------------------------------------------------------------+
//| Process any signals in the queue                                 |
//+------------------------------------------------------------------+
void ProcessSignalQueue()
{
   while(queueHead != queueTail)
   {
      string jsonData = signalQueue[queueHead];
      queueHead = (queueHead + 1) % MAX_QUEUE_SIZE;
      
      LogInfo(StringFormat("Popped from queue: %s", jsonData));
      ProcessSignal(jsonData);
   }
}

//+------------------------------------------------------------------+
//| Process received signal                                          |
//+------------------------------------------------------------------+
//+------------------------------------------------------------------+
//| Process received signal                                          |
//+------------------------------------------------------------------+
void ProcessSignal(string jsonSignal)
{
   LogInfo(StringFormat(">>> Pipeline [1/4]: Starting ProcessSignal for: %s", jsonSignal));
   
   // Parse JSON signal
   SignalData signal;
   if(!ParseSignal(jsonSignal, signal))
   {
      LogError("!!! Pipeline [FAIL]: Failed to parse signal JSON structure");
      return;
   }
   
   // Handle different signal types
   if(signal.action == "LONG" || signal.action == "SHORT")
   {
      LogInfo(StringFormat(">>> Pipeline [2/4]: Validating %s signal for %s", signal.action, signal.symbol));
      
      // Entry signal - validate and execute
      if(!ValidateSignal(signal))
      {
         LogWarning("!!! Pipeline [FAIL]: Signal validation rejected the trade");
         return;
      }
      
      LogInfo(">>> Pipeline [3/4]: Checking Risk Management limits...");
      if(!CheckRiskLimits(signal))
      {
         LogWarning("!!! Pipeline [FAIL]: Signal rejected by RiskManager");
         return;
      }
      
      LogInfo(">>> Pipeline [4/4]: Routing to ExecuteTrade...");
      ExecuteTrade(signal);
   }
   else if(signal.action == "CLOSE_LONG" || signal.action == "CLOSE_SHORT")
   {
      LogInfo(StringFormat(">>> Pipeline [EXIT]: Processing %s for %s", signal.action, signal.symbol));
      ClosePosition(signal);
   }
   else if(signal.action == "REVERSE_TO_LONG" || signal.action == "REVERSE_TO_SHORT")
   {
      LogInfo(StringFormat(">>> Pipeline [REVERSE]: Reversing to %s", signal.action));
      ClosePosition(signal);
      Sleep(REVERSAL_DELAY_MS);
      
      signal.action = (signal.action == "REVERSE_TO_LONG") ? "LONG" : "SHORT";
      
      if(!ValidateSignal(signal))
      {
         LogWarning("!!! Pipeline [FAIL]: Reversal validation failed");
         return;
      }
      
      ExecuteTrade(signal);
   }
   else
   {
      LogWarning(StringFormat("!!! Pipeline [FAIL]: Unknown action code: %s", signal.action));
   }
}


//+------------------------------------------------------------------+
//| Parse JSON signal to structure                                   |
//+------------------------------------------------------------------+
bool ParseSignal(string json, SignalData &signal)
{
   signal.action = ExtractStringValue(json, "action");
   signal.symbol = ExtractStringValue(json, "symbol");
   signal.price = ExtractDoubleValue(json, "price");
   signal.sl = ExtractDoubleValue(json, "sl");
   signal.tp = ExtractDoubleValue(json, "tp");
   signal.lots = ExtractDoubleValue(json, "lots");
   signal.bias = ExtractStringValue(json, "bias");
   if(signal.bias == "") signal.bias = ExtractStringValue(json, "desc"); // Fallback to desc
   signal.timestamp = (long)NormalizeDouble(ExtractDoubleValue(json, "timestamp"), 0);
   
   bool success = (signal.action != "" && signal.symbol != "" && signal.price > 0);
   if(success) {
      LogDebug(StringFormat("   [PARSE] Action: %s, Symbol: %s, Price: %.2f, SL: %.2f", signal.action, signal.symbol, signal.price, signal.sl));
   }
   return success;
}

//+------------------------------------------------------------------+
//| Validate signal data                                             |
//+------------------------------------------------------------------+
bool ValidateSignal(SignalData &signal)
{
   // Check action
   if(signal.action != "LONG" && signal.action != "SHORT" && 
      signal.action != "CLOSE_LONG" && signal.action != "CLOSE_SHORT" &&
      signal.action != "REVERSE_TO_LONG" && signal.action != "REVERSE_TO_SHORT")
   {
      Print("   [VALIDATE/FAIL] Invalid action: ", signal.action);
      return false;
   }
   
   // Symbol mapping safety: If signal says XAUUSD and chart is XAUUSD.m, we allow it
   string sigSym = signal.symbol;
   string chartSym = _Symbol;
   StringToUpper(sigSym);
   StringToUpper(chartSym);
   
   bool symMatch = (StringFind(sigSym, chartSym) != -1 || StringFind(chartSym, sigSym) != -1 || sigSym == chartSym);
   
   if(!symMatch)
   {
      Print(StringFormat("   [VALIDATE/FAIL] Symbol mismatch. Signal:%s vs Chart:%s", sigSym, chartSym));
      return false;
   }
   
   // Refresh signal symbol to match broker chart name exactly (crucial for SymbolInfo calls)
   signal.symbol = _Symbol;

   // Check if symbol is tradable
   if(!SymbolInfoInteger(_Symbol, SYMBOL_TRADE_MODE))
   {
      Print("   [VALIDATE/FAIL] Symbol ", _Symbol, " is not tradable (SYMB_TRADE_MODE)");
      return false;
   }
   
   // Skip Lot/SL checks for exit signals
   if(signal.action == "CLOSE_LONG" || signal.action == "CLOSE_SHORT") return true;

   // Check lot size
   double minLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   
   if(signal.lots < minLot || signal.lots > maxLot)
   {
      Print(StringFormat("   [VALIDATE/FAIL] Lot size error: %.2f (min: %.2f, max: %.2f)", signal.lots, minLot, maxLot));
      return false;
   }
   
   // Check stop loss
   if(signal.sl <= 0)
   {
      Print("   [VALIDATE/FAIL] Invalid stop loss (<= 0)");
      return false;
   }
   
   LogDebug("   [VALIDATE/PASS] Signal data is valid");
   return true;
}

//+------------------------------------------------------------------+
//| Check risk management limits                                     |
//+------------------------------------------------------------------+
bool CheckRiskLimits(SignalData &signal)
{
   // Check max lot size
   if(signal.lots > MAX_LOT_SIZE)
   {
      LogWarning(StringFormat("   [RISK/FAIL] Lot size %.2f exceeds maximum limit %.2f", signal.lots, MAX_LOT_SIZE));
      return false;
   }
   
   // Check max open positions
   int openPositions = CountOpenPositions();
   if(openPositions >= MAX_OPEN_POSITIONS)
   {
      LogWarning(StringFormat("   [RISK/FAIL] Max open positions reached (%d/%d)", openPositions, MAX_OPEN_POSITIONS));
      return false;
   }
   
   // Check daily drawdown
   double dailyPnL = GetDailyPnL();
   double maxLoss = dailyStartBalance * (MAX_DAILY_DRAWDOWN_PCT / 100.0);
   
   if(dailyPnL < -maxLoss)
   {
      LogWarning(StringFormat("   [RISK/FAIL] Daily drawdown reached: %.2f (limit: %.2f)", dailyPnL, -maxLoss));
      return false;
   }
   
   LogDebug("   [RISK/PASS] All risk checks passed");
   return true;
}

//+------------------------------------------------------------------+
//| Execute trade based on signal                                    |
//+------------------------------------------------------------------+
void ExecuteTrade(SignalData &signal)
{
   MqlTradeRequest request;
   MqlTradeResult result;
   ZeroMemory(request);
   ZeroMemory(result);
   
   double ask = SymbolInfoDouble(signal.symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(signal.symbol, SYMBOL_BID);
   
   if(ask <= 0 || bid <= 0) {
      LogError(StringFormat("   [EXECUTE/FAIL] Could not get price for %s (Ask:%.2f, Bid:%.2f)", signal.symbol, ask, bid));
      return;
   }

   // Prepare trade request
   request.action = TRADE_ACTION_DEAL;
   request.symbol = signal.symbol;
   request.volume = signal.lots;
   request.type = (signal.action == "LONG") ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   request.price = (signal.action == "LONG") ? ask : bid;
   request.sl = signal.sl;
   request.tp = 0.0;           
   request.deviation = SLIPPAGE_POINTS;
   request.magic = MAGIC_NUMBER;
   request.comment = StringFormat("%s", TRADE_COMMENT);
   request.type_filling = ORDER_FILLING_FOK;
   
   LogInfo(StringFormat("   [EXECUTE/SEND] Request: %s %s %.2f lots @ %.5f (Ask:%.5f, Bid:%.5f)", 
                        (request.type == ORDER_TYPE_BUY ? "BUY" : "SELL"), request.symbol, request.volume, request.price, ask, bid));
   
   // Send order
   if(!OrderSend(request, result))
   {
      LogError(StringFormat("   [ORDER_SEND/ERROR] Critical system error: %d - %s", GetLastError(), result.comment));
      return;
   }
   
   if(result.retcode == TRADE_RETCODE_DONE)
   {
      currentPositionTicket = result.order;
      currentPositionDirection = signal.action;
      
      LogInfo(StringFormat("   [SUCCESS] Trade executed! Ticket: %I64u, Fill Price: %.5f", result.order, result.price));
   }
   else
   {
      LogError(StringFormat("   [EXECUTE/REJECTED] MT5 code: %u, Comment: %s", result.retcode, result.comment));
   }
}

//+------------------------------------------------------------------+
//| Close position based on signal                                   |
//+------------------------------------------------------------------+
void ClosePosition(SignalData &signal)
{
   bool positionClosed = false;
   
   // Find and close all positions with our magic number
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(PositionSelectByTicket(ticket))
      {
         if(PositionGetInteger(POSITION_MAGIC) == MAGIC_NUMBER)
         {
            string posSymbol = PositionGetString(POSITION_SYMBOL);
            if(posSymbol != signal.symbol) continue; // Only close if symbol matches
            
            long posType = PositionGetInteger(POSITION_TYPE);
            double posVolume = PositionGetDouble(POSITION_VOLUME);
            
            // Prepare close request
            MqlTradeRequest request;
            MqlTradeResult result;
            ZeroMemory(request);
            ZeroMemory(result);
            
            request.action = TRADE_ACTION_DEAL;
            request.position = ticket;
            request.symbol = posSymbol;
            request.volume = posVolume;
            request.type = (posType == POSITION_TYPE_BUY) ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
            request.price = (posType == POSITION_TYPE_BUY) ? SymbolInfoDouble(posSymbol, SYMBOL_BID) : SymbolInfoDouble(posSymbol, SYMBOL_ASK);
            request.deviation = SLIPPAGE_POINTS;
            request.magic = MAGIC_NUMBER;
            request.comment = "Exit";
            request.type_filling = ORDER_FILLING_IOC;
            
            // Send close order
            if(OrderSend(request, result))
            {
               if(result.retcode == TRADE_RETCODE_DONE)
               {
                  LogInfo(StringFormat("Position closed: Ticket %I64u at %.5f", ticket, result.price));
                  positionClosed = true;
                  
                  // Clear position tracking
                  currentPositionTicket = 0;
                  currentPositionDirection = "";
               }
               else
               {
                  LogError(StringFormat("Close failed: %u - %s", (uint)result.retcode, result.comment));
               }
            }
            else
            {
               LogError(StringFormat("OrderSend (close) failed: %d", GetLastError()));
            }
         }
      }
   }
   
   if(!positionClosed)
   {
      LogWarning("No position found to close");
   }
}


//+------------------------------------------------------------------+
//| Update trailing stop loss for open positions                     |
//+------------------------------------------------------------------+
void UpdateTrailingStops()
{
   if(!ENABLE_TRAILING_SL) return;

   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   
   // Convert pips to price units
   // Standard: 1 pip = 10 points for most 5/3/2 digit brokers
   double trailingStop = TRAILING_STOP_PIPS * point * 10;
   double trailingStep = TRAILING_STEP_PIPS * point * 10;
   
   static datetime lastLog = 0;
   if(PositionsTotal() > 0 && TimeCurrent() - lastLog > 3600) {
      LogDebug(StringFormat("Trailing check active for %d positions. Stop: %.5f, Step: %.5f", 
               PositionsTotal(), trailingStop, trailingStep));
      lastLog = TimeCurrent();
   }

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(!PositionSelectByTicket(ticket))
         continue;
      
      // Only manage our positions
      if(PositionGetInteger(POSITION_MAGIC) != MAGIC_NUMBER)
         continue;
      
      string symbol = PositionGetString(POSITION_SYMBOL);
      if(symbol != _Symbol)
         continue;
      
      long posType = PositionGetInteger(POSITION_TYPE);
      double currentSL = PositionGetDouble(POSITION_SL);
      double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
      double currentPrice = (posType == POSITION_TYPE_BUY) ? 
                            SymbolInfoDouble(symbol, SYMBOL_BID) : 
                            SymbolInfoDouble(symbol, SYMBOL_ASK);
      
      double newSL = 0;
      bool shouldUpdate = false;
      
      if(posType == POSITION_TYPE_BUY)
      {
         // For LONG positions: trail stop below current price
         newSL = NormalizeDouble(currentPrice - trailingStop, digits);
         
         // Update if:
         // 1. No SL set
         // 2. New SL is higher than existing SL by at least one 'step'
         if(currentSL == 0 || newSL > currentSL + trailingStep)
         {
            shouldUpdate = true;
         }
      }
      else if(posType == POSITION_TYPE_SELL)
      {
         // For SHORT positions: trail stop above current price
         newSL = NormalizeDouble(currentPrice + trailingStop, digits);
         
         // Update if:
         // 1. No SL set
         // 2. New SL is lower than existing SL by at least one 'step'
         if(currentSL == 0 || newSL < currentSL - trailingStep)
         {
            shouldUpdate = true;
         }
      }
      
      // Update stop loss
      if(shouldUpdate)
      {
         MqlTradeRequest request;
         MqlTradeResult result;
         ZeroMemory(request);
         ZeroMemory(result);
         
         request.action = TRADE_ACTION_SLTP;
         request.position = ticket;
         request.symbol = symbol;
         request.sl = newSL;
         request.tp = PositionGetDouble(POSITION_TP);  // Keep existing TP
         
         LogInfo(StringFormat(">>> Trailing SL Update: Ticket %I64u | NewSL: %.5f | PreviousSL: %.5f | Price: %.5f", 
                             ticket, newSL, currentSL, currentPrice));

         if(OrderSend(request, result))
         {
            if(result.retcode == TRADE_RETCODE_DONE)
            {
               LogInfo(StringFormat("   [SUCCESS] Trailing SL moved for ticket %I64u", ticket));
            }
            else
            {
               LogError(StringFormat("   [REJECTED] Trailing SL: %u - %s", result.retcode, result.comment));
            }
         }
         else
         {
            LogError(StringFormat("   [ERROR] OrderSend failed for Trailing SL: %d", GetLastError()));
         }
      }
   }
}


//+------------------------------------------------------------------+
//| Count open positions with our magic number                       |
//+------------------------------------------------------------------+
int CountOpenPositions()
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(PositionSelectByTicket(ticket))
      {
         if((int)PositionGetInteger(POSITION_MAGIC) == MAGIC_NUMBER)
            count++;
      }
   }
   return count;
}

//+------------------------------------------------------------------+
//| Calculate daily P&L                                              |
//+------------------------------------------------------------------+
double GetDailyPnL()
{
   double pnl = 0.0;
   datetime todayStart = StringToTime(TimeToString(TimeCurrent(), TIME_DATE));
   
   // Sum closed trades for today
   HistorySelect(todayStart, TimeCurrent());
   for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = HistoryDealGetTicket(i);
      if(ticket > 0)
      {
         if((int)HistoryDealGetInteger(ticket, DEAL_MAGIC) == MAGIC_NUMBER)
         {
            pnl += HistoryDealGetDouble(ticket, DEAL_PROFIT);
         }
      }
   }
   
   // Add open positions P&L
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(PositionSelectByTicket(ticket))
      {
         if((int)PositionGetInteger(POSITION_MAGIC) == MAGIC_NUMBER)
            pnl += PositionGetDouble(POSITION_PROFIT);
      }
   }
   
   return pnl;
}

//+------------------------------------------------------------------+
//| Check and reset daily tracking                                   |
//+------------------------------------------------------------------+
void CheckDailyReset()
{
   datetime today = StringToTime(TimeToString(TimeCurrent(), TIME_DATE));
   datetime lastDay = StringToTime(TimeToString(currentDay, TIME_DATE));
   
   if(today != lastDay)
   {
      LogInfo(StringFormat("New trading day. Previous day P&L: %.2f", GetDailyPnL()));
      dailyStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
      currentDay = TimeCurrent();
   }
}

//+------------------------------------------------------------------+
//| Normalize lot size to broker requirements                        |
//+------------------------------------------------------------------+
double NormalizeLots(double lots)
{
   double minLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   
   lots = MathMax(minLot, MathMin(maxLot, lots));
   lots = MathFloor(lots / lotStep) * lotStep;
   
   return lots;
}


//+------------------------------------------------------------------+
//| Helper: Extract string value from JSON                           |
//+------------------------------------------------------------------+
string ExtractStringValue(string json, string key)
{
   string searchKey = "\"" + key + "\"";
   int start = StringFind(json, searchKey);
   if(start == -1) return "";
   
   start = StringFind(json, "\"", start + StringLen(searchKey));
   if(start == -1) return "";
   start++;
   
   int end = StringFind(json, "\"", start);
   if(end == -1) return "";
   
   return StringSubstr(json, start, end - start);
}

//+------------------------------------------------------------------+
//| Helper: Extract double value from JSON                           |
//+------------------------------------------------------------------+
double ExtractDoubleValue(string json, string key)
{
   string searchKey = "\"" + key + "\":";
   int start = StringFind(json, searchKey);
   if(start == -1) return 0.0;
   
   start += StringLen(searchKey);
   
   // Skip whitespace
   while(start < StringLen(json) && (StringGetCharacter(json, start) == ' ' || StringGetCharacter(json, start) == '\t'))
      start++;
   
   // Find end of number
   int end = start;
   while(end < StringLen(json))
   {
      ushort ch = StringGetCharacter(json, end);
      if(ch != '.' && ch != '-' && ch != 'e' && ch != 'E' && ch != '+' && (ch < '0' || ch > '9'))
         break;
      end++;
   }
   
   string numStr = StringSubstr(json, start, end - start);
   return StringToDouble(numStr);
}

//+------------------------------------------------------------------+
//| Logging Functions                                                |
//+------------------------------------------------------------------+
void LogDebug(string message)
{
   if(LOG_LEVEL <= LOG_LEVEL_DEBUG)
      Print("[DEBUG] ", message);
}

void LogInfo(string message)
{
   if(LOG_LEVEL <= LOG_LEVEL_INFO)
      Print("[INFO] ", message);
}

void LogWarning(string message)
{
   if(LOG_LEVEL <= LOG_LEVEL_WARNING)
      Print("[WARNING] ", message);
}

void LogError(string message)
{
   if(LOG_LEVEL <= LOG_LEVEL_ERROR)
      Print("[ERROR] ", message);
}

//+------------------------------------------------------------------+
//| ZMQ Wrapper for integer options                                  |
//+------------------------------------------------------------------+
#ifndef DISABLE_ZMQ
int ZmqSetSockOpt(long socket, int option, int value)
{
   uchar bytes[4];
   bytes[0] = (uchar)(value & 0xFF);
   bytes[1] = (uchar)((value >> 8) & 0xFF);
   bytes[2] = (uchar)((value >> 16) & 0xFF);
   bytes[3] = (uchar)((value >> 24) & 0xFF);
   return zmq_setsockopt(socket, option, bytes, 4);
}
#endif

//+------------------------------------------------------------------+
//| ZMQ Wrapper for byte array options                               |
//+------------------------------------------------------------------+
#ifndef DISABLE_ZMQ
int ZmqSetSockOpt(long socket, int option, const uchar &value[])
{
   return zmq_setsockopt(socket, option, value, ArraySize(value));
}
#endif

//+------------------------------------------------------------------+
//|   Get Open Positions as JSON                                     |
//+------------------------------------------------------------------+
//+------------------------------------------------------------------+
//|   Get Open Positions as JSON (String Concatenation Version)      |
//+------------------------------------------------------------------+
string GetOpenPositionsJson()
{
      string json = "{\"status\":\"SUCCESS\",\"positions\":[";
      bool first = true;
      
      for(int i = PositionsTotal() - 1; i >= 0; i--)
      {
            ulong ticket = PositionGetTicket(i);
            if(PositionSelectByTicket(ticket))
            {
                  if((int)PositionGetInteger(POSITION_MAGIC) == MAGIC_NUMBER)
                  {
                        if(!first) json += ",";
                        
                        int type = (int)PositionGetInteger(POSITION_TYPE);
                        string typeStr = (type == (int)POSITION_TYPE_BUY) ? "LONG" : "SHORT";
                        
                        string posJson = "{" + 
                              "\"ticket\":" + (string)ticket + "," +
                              "\"symbol\":\"" + PositionGetString(POSITION_SYMBOL) + "\"," +
                              "\"type\":\"" + typeStr + "\"," +
                              "\"lots\":" + DoubleToString(PositionGetDouble(POSITION_VOLUME), 2) + "," +
                              "\"entry_price\":" + DoubleToString(PositionGetDouble(POSITION_PRICE_OPEN), 5) + "," +
                              "\"sl\":" + DoubleToString(PositionGetDouble(POSITION_SL), 5) + "," +
                              "\"profit\":" + DoubleToString(PositionGetDouble(POSITION_PROFIT), 2) + 
                        "}";
                        
                        json += posJson;
                        first = false;
                  }
            }
      }
      
      json += "]}";
      return json;
}
 
//+------------------------------------------------------------------+
//|   Get History as JSON (String Concatenation Version)             |
//+------------------------------------------------------------------+
string GetHistoryDealsJson(int days)
{
      datetime end = TimeCurrent();
      datetime start = end - (days * 24 * 3600);
      HistorySelect(start, end);
      
      string json = "{\"status\":\"SUCCESS\",\"history\":[";
      bool first = true;
      
      int total = HistoryDealsTotal();
      for(int i = total - 1; i >= 0; i--)
      {
            ulong ticket = HistoryDealGetTicket(i);
            if(HistoryDealGetInteger(ticket, DEAL_MAGIC) == MAGIC_NUMBER)
            {
                  long entry = HistoryDealGetInteger(ticket, DEAL_ENTRY);
                  if(entry == DEAL_ENTRY_OUT)
                  {
                        if(!first) json += ",";
                        
                        long type = HistoryDealGetInteger(ticket, DEAL_TYPE);
                        string typeStr = ((int)type == (int)DEAL_TYPE_BUY) ? "BUY" : "SELL";
                        
                        string dealJson = "{" +
                              "\"ticket\":" + (string)ticket + "," +
                              "\"symbol\":\"" + HistoryDealGetString(ticket, DEAL_SYMBOL) + "\"," +
                              "\"type\":\"" + typeStr + "\"," +
                              "\"lots\":" + DoubleToString(HistoryDealGetDouble(ticket, DEAL_VOLUME), 2) + "," +
                              "\"exit_price\":" + DoubleToString(HistoryDealGetDouble(ticket, DEAL_PRICE), 5) + "," +
                              "\"profit\":" + DoubleToString(HistoryDealGetDouble(ticket, DEAL_PROFIT), 2) + "," +
                              "\"exit_time\":\"" + TimeToString((datetime)HistoryDealGetInteger(ticket, DEAL_TIME), TIME_DATE|TIME_SECONDS) + "\"" +
                        "}";
                        
                        json += dealJson;
                        first = false;
                  }
            }
      }
      
      json += "]}";
      return json;
}

//+------------------------------------------------------------------+
//| Check for signals in a local CSV file (Backtest/Replay Mode)     |
//+------------------------------------------------------------------+
void CheckForOfflineSignals()
{
   // Rate limit: Only check once per second
   static datetime lastCheckTime = 0;
   if(TimeCurrent() == lastCheckTime) return;
   lastCheckTime = TimeCurrent();

   // Reset counter if file is empty or smaller (user cleared it)
   static long lastFileSize = 0;
   
   // Try Common Folder first
   int fileHandle = FileOpen(BACKTEST_FILE, FILE_READ|FILE_CSV|FILE_ANSI|FILE_COMMON, ',');
   bool isCommon = true;
   
   if(fileHandle == INVALID_HANDLE)
   {
      // Try local folder if common fails
      fileHandle = FileOpen(BACKTEST_FILE, FILE_READ|FILE_CSV|FILE_ANSI, ',');
      isCommon = false;
   }
   
   if(fileHandle == INVALID_HANDLE)
   {
      static datetime lastWarn = 0;
      if(TimeCurrent() - lastWarn > 3600) { 
         Print("ERROR: Backtest signal file NOT FOUND in Common or Local folder: ", BACKTEST_FILE); 
         lastWarn = TimeCurrent();
      }
      return;
   }

   // Check if file was reset or updated
   long fileSize = FileSize(fileHandle);
   if(fileSize < lastFileSize) {
      Print("Signal file reset detected. Resetting line counter.");
      lastProcessedLine = 0;
   }
   lastFileSize = fileSize;

   long currentLine = 0;
   int newSignals = 0;
   
   while(!FileIsEnding(fileHandle))
   {
      // 1. Read first token (Timestamp)
      string lineToken = FileReadString(fileHandle);
      StringTrimLeft(lineToken);
      StringTrimRight(lineToken);
      
      // Handle empty tokens/newlines
      if(lineToken == "") {
         if(FileIsEnding(fileHandle)) break;
         continue;
      }
      
      // SAFETY: If the token doesn't look like a date (e.g. 2026-01-14), skip it
      // This prevents "ghost tokens" like lone newlines from shifting the columns
      if(StringLen(lineToken) < 10 || (StringFind(lineToken, "-") == -1 && StringFind(lineToken, ".") == -1))
      {
         // Consume rest of line and skip
         while(!FileIsLineEnding(fileHandle) && !FileIsEnding(fileHandle)) FileReadString(fileHandle);
         continue;
      }

      currentLine++;
      
      // Skip headers (Line 1) and already processed lines
      if(currentLine <= 1 || currentLine <= lastProcessedLine)
      {
         while(!FileIsLineEnding(fileHandle) && !FileIsEnding(fileHandle)) FileReadString(fileHandle);
         continue;
      }

      // Column 1: Time
      string rawTime = lineToken;
      StringReplace(rawTime, "-", ".");
      datetime signalTime = StringToTime(rawTime);
      signalTime = signalTime + (SIGNAL_TIME_SHIFT * 3600);
      
      // Column 2: Symbol
      string sSymbol = FileReadString(fileHandle);
      
      // Column 3: Action
      string sAction = FileReadString(fileHandle);
      
      // Column 4-7: Price, SL, TP, Lots
      double dPrice = StringToDouble(FileReadString(fileHandle));
      double dSL    = StringToDouble(FileReadString(fileHandle));
      double dTP    = StringToDouble(FileReadString(fileHandle));
      double dLots  = StringToDouble(FileReadString(fileHandle));
      
      // Column 8-9: Description, Magic
      string sDesc  = FileReadString(fileHandle);
      string sMagic = FileReadString(fileHandle);

      // Clean up strings
      StringTrimLeft(sSymbol); StringTrimRight(sSymbol);
      StringTrimLeft(sAction); StringTrimRight(sAction);
      
      // TEMPORAL FILTERING:
      datetime currentTime = TimeCurrent();
      
      // 1. Future signal: WAIT
      if(!ENABLE_VISUAL_REPLAY && signalTime > currentTime)
      {
         static datetime lastWaitLog = 0;
         if(TimeCurrent() - lastWaitLog >= 60) 
         {
             Print(StringFormat("Waiting for signal time: %s (Current: %s)", TimeToString(signalTime), TimeToString(currentTime)));
             lastWaitLog = TimeCurrent();
         }
         FileClose(fileHandle);
         return; 
      }
      
      // 2. Old signal: SKIP (Unless in Visual Replay Mode)
      if(!ENABLE_VISUAL_REPLAY && signalTime < currentTime - 3600)
      {
         Print(StringFormat("SKIPPING EXPIRED SIGNAL: %s (Current: %s) -> Diff: %d sec", 
               TimeToString(signalTime), TimeToString(currentTime), (int)(currentTime - signalTime)));
         lastProcessedLine = currentLine;
         continue;
      }
      
      // 3. EXECUTE
      LogInfo(StringFormat(">>> Pipeline [0/4]: Found signal at Line %I64d | Time: %s", currentLine, TimeToString(signalTime)));
      
      // Build JSON with fixed mapping
      string pseudoJson = StringFormat("{\"action\":\"%s\",\"symbol\":\"%s\",\"price\":%.5f,\"sl\":%.5f,\"tp\":%.5f,\"lots\":%.2f,\"desc\":\"%s\",\"timestamp\":%I64d}",
                                       sAction, sSymbol, dPrice, dSL, dTP, dLots, sDesc, (long)signalTime);
      
      ProcessSignal(pseudoJson);
      newSignals++;
      lastProcessedLine = currentLine;
   }

   
   if(newSignals > 0) Print("Processed ", newSignals, " new signals from file.");
   FileClose(fileHandle);
}

//+------------------------------------------------------------------+
//| Check for forensic signals (iSignals)                            |
//+------------------------------------------------------------------+
void CheckForForensicSignals()
{
   if(TimeCurrent() == g_last_forensic_time) return;
   
   // Try Common Folder first
   int fileHandle = FileOpen(ISIGNAL_FILE, FILE_READ|FILE_CSV|FILE_ANSI|FILE_COMMON, ',');
   if(fileHandle == INVALID_HANDLE)
   {
      fileHandle = FileOpen(ISIGNAL_FILE, FILE_READ|FILE_CSV|FILE_ANSI, ',');
   }
   
   if(fileHandle == INVALID_HANDLE) return;
   
   datetime targetTime = TimeCurrent() + (SIGNAL_TIME_SHIFT * 3600);
   bool found = false;
   
   // We skip header and look for the closest time
   FileReadString(fileHandle); // Skip Time
   while(!FileIsLineEnding(fileHandle)) FileReadString(fileHandle);
   
   while(!FileIsEnding(fileHandle))
   {
      string sTime = FileReadString(fileHandle);
      if(sTime == "") continue;
      
      StringReplace(sTime, "-", ".");
      datetime rowTime = StringToTime(sTime);
      
      // If we found the exact bar or the last known bar before current time
      if(rowTime <= targetTime)
      {
         // Read columns: Price, L0, L1, L2, L3, L4, L5, Final, Reason
         FileReadString(fileHandle); // Price
         g_forensic_layers[0] = FileReadString(fileHandle);
         g_forensic_layers[1] = FileReadString(fileHandle);
         g_forensic_layers[2] = FileReadString(fileHandle);
         g_forensic_layers[3] = FileReadString(fileHandle);
         g_forensic_layers[4] = FileReadString(fileHandle);
         g_forensic_layers[5] = FileReadString(fileHandle);
         g_forensic_action    = FileReadString(fileHandle);
         g_forensic_reason    = FileReadString(fileHandle);
         
         found = true;
         // Continue searching to get the latest possible row <= targetTime
      }
      else
      {
         // Row time is in future relative to our target, stop
         break;
      }
      
      // Consume rest of line
      while(!FileIsLineEnding(fileHandle) && !FileIsEnding(fileHandle)) FileReadString(fileHandle);
   }
   
   FileClose(fileHandle);
   g_last_forensic_time = TimeCurrent();
   
   if(found) UpdateForensicDisplay();
}

//+------------------------------------------------------------------+
//| Update the visual forensic display on chart                      |
//+------------------------------------------------------------------+
void UpdateForensicDisplay()
{
   string display = "=== HEDGE-ENGINE FORENSIC INTELLIGENCE ===\n";
   display += StringFormat("Current Time: %s\n", TimeToString(TimeCurrent()));
   display += "------------------------------------------\n";
   display += StringFormat("L0 Session:   [%s]\n", g_forensic_layers[0]);
   display += StringFormat("L1 HTF Bias:  [%s]\n", g_forensic_layers[1]);
   display += StringFormat("L2 Zone Qual: [%s]\n", g_forensic_layers[2]);
   display += StringFormat("L3 Liq Sweep: [%s]\n", g_forensic_layers[3]);
   display += StringFormat("L4 mBOS Shift:[%s]\n", g_forensic_layers[4]);
   display += StringFormat("L5 Displacem: [%s]\n", g_forensic_layers[5]);
   display += "------------------------------------------\n";
   display += StringFormat("ACTION: %s\n", g_forensic_action);
   display += StringFormat("REASON: %s\n", g_forensic_reason);
   display += "==========================================";
   
   Comment(display);
}
//+------------------------------------------------------------------+
