//+------------------------------------------------------------------+
//| TransactionRecon.mqh                                             |
//|                                                                  |
//| Authoritative transaction-stream handler.                        |
//|                                                                  |
//| Per D4 REQ-037 / D3 §18:                                         |
//|   * OnTradeTransaction is the authoritative source for fills,    |
//|     partials, modifications, closures and realized P/L.          |
//|   * Actual account state outranks stale local assumptions.       |
//|   * No blind retry on rejected or uncertain orders.              |
//|                                                                  |
//| The handler is deliberately conservative: it logs every trade    |
//| transaction event and never mutates internal state on an         |
//| uncertain result. State reconciliation is derived from the       |
//| account itself (PositionSelect, HistoryDealSelect) on the next   |
//| tick or on demand.                                               |
//+------------------------------------------------------------------+
#property strict

#include <Contracts header.mqh>
#include <Logger.mqh>

//--- Called from AMIGO.mq5 OnTradeTransaction().
//--- Signature must match the built-in MQL5 event handler parameters
//--- exactly, or the compiler will refuse the call site.
void TransactionReconHandle(const MqlTradeTransaction &trans,
                            const MqlTradeRequest &request,
                            const MqlTradeResult &result)
{
   switch(trans.type)
   {
      case TRADE_TRANSACTION_ORDER_ADD:
         LogMsg(LOG_DEBUG, "RECON",
                StringFormat("ORDER_ADD ticket=%I64u sym=%s",
                             trans.order, trans.symbol));
         break;

      case TRADE_TRANSACTION_ORDER_UPDATE:
         LogMsg(LOG_DEBUG, "RECON",
                StringFormat("ORDER_UPDATE ticket=%I64u state=%d",
                             trans.order, (int)trans.order_state));
         break;

      case TRADE_TRANSACTION_ORDER_DELETE:
         LogMsg(LOG_INFO, "RECON",
                StringFormat("ORDER_DELETE ticket=%I64u reason=%d",
                             trans.order, (int)trans.order_state));
         break;

      case TRADE_TRANSACTION_DEAL_ADD:
         LogMsg(LOG_INFO, "RECON",
                StringFormat("DEAL_ADD ticket=%I64u order=%I64u sym=%s vol=%.2f price=%.5f",
                             trans.deal, trans.order, trans.symbol,
                             trans.volume, trans.price));
         break;

      case TRADE_TRANSACTION_DEAL_UPDATE:
         LogMsg(LOG_DEBUG, "RECON",
                StringFormat("DEAL_UPDATE ticket=%I64u", trans.deal));
         break;

      case TRADE_TRANSACTION_DEAL_DELETE:
         LogMsg(LOG_INFO, "RECON",
                StringFormat("DEAL_DELETE ticket=%I64u", trans.deal));
         break;

      case TRADE_TRANSACTION_HISTORY_ADD:
         LogMsg(LOG_DEBUG, "RECON",
                StringFormat("HISTORY_ADD ticket=%I64u", trans.order));
         break;

      case TRADE_TRANSACTION_HISTORY_UPDATE:
         LogMsg(LOG_DEBUG, "RECON",
                StringFormat("HISTORY_UPDATE ticket=%I64u", trans.order));
         break;

      case TRADE_TRANSACTION_HISTORY_DELETE:
         LogMsg(LOG_INFO, "RECON",
                StringFormat("HISTORY_DELETE ticket=%I64u", trans.order));
         break;

      case TRADE_TRANSACTION_POSITION:
         LogMsg(LOG_INFO, "RECON",
                StringFormat("POSITION_UPDATE ticket=%I64u sym=%s",
                             trans.position, trans.symbol));
         break;

      case TRADE_TRANSACTION_REQUEST:
         LogMsg(LOG_DEBUG, "RECON",
                StringFormat("REQUEST retcode=%u", result.retcode));
         break;

      default:
         LogMsg(LOG_DEBUG, "RECON",
                StringFormat("UNHANDLED type=%d", (int)trans.type));
         break;
   }
}
//+------------------------------------------------------------------+