//+------------------------------------------------------------------+
//| PositionRecovery.mqh - Versioned Persistent Position State &     |
//| Multi-Horizon Lifecycle Reconciliation Engine for AMIGO          |
//+------------------------------------------------------------------+
#property strict

#include <Contracts header.mqh>
#include <Configuration.mqh>
#include <Logger.mqh>

#define AMIGO_STATE_SCHEMA_VERSION 101
#define AMIGO_STATE_FILE_PRIMARY   "Amigo_positions.dat"
#define AMIGO_STATE_FILE_TEMP      "Amigo_positions.tmp"
#define AMIGO_STATE_MAX_POSITIONS  64

//+------------------------------------------------------------------+
//| Save Active Positions to Versioned Binary Persistent Storage     |
//| Uses Atomic Temp-File Write with Validation Header               |
//+------------------------------------------------------------------+
bool PositionSaveState(const AmigoConfig &cfg)
{
   int count = ArraySize(g_positions);
   if(count > AMIGO_STATE_MAX_POSITIONS) count = AMIGO_STATE_MAX_POSITIONS;

   // Open atomic temporary file in local terminal files sandbox
   int handle = FileOpen(AMIGO_STATE_FILE_TEMP, FILE_BIN|FILE_WRITE);
   if(handle == INVALID_HANDLE)
   {
      LogMsg(LOG_WARN, "PERSIST_SAVE", StringFormat("Failed to open temp state file %s (err=%d)", AMIGO_STATE_FILE_TEMP, GetLastError()));
      return false;
   }

   // 1. Header: Schema version, Magic Number, Count, Timestamp
   FileWriteInteger(handle, AMIGO_STATE_SCHEMA_VERSION, INT_VALUE);
   FileWriteLong(handle, (long)cfg.magic_number);
   FileWriteInteger(handle, count, INT_VALUE);
   FileWriteLong(handle, (long)TimeCurrent());

   // 2. Records: Versioned fields per position
   for(int i = 0; i < count; i++)
   {
      FileWriteLong(handle, (long)g_positions[i].position_id);
      FileWriteInteger(handle, g_positions[i].direction, INT_VALUE);
      FileWriteDouble(handle, g_positions[i].entry);
      FileWriteDouble(handle, g_positions[i].initial_stop);
      FileWriteDouble(handle, g_positions[i].initial_target);
      FileWriteDouble(handle, g_positions[i].initial_atr);
      FileWriteDouble(handle, g_positions[i].initial_risk_per_unit);
      FileWriteInteger(handle, g_positions[i].partial_done ? 1 : 0, INT_VALUE);
      FileWriteDouble(handle, g_positions[i].current_stop);
      FileWriteInteger(handle, g_positions[i].be_activated ? 1 : 0, INT_VALUE);
      FileWriteDouble(handle, g_positions[i].be_trigger_price);
      FileWriteDouble(handle, g_positions[i].last_applied_stop);
      FileWriteInteger(handle, (int)g_positions[i].trailing_mode, INT_VALUE);
      FileWriteInteger(handle, (int)g_positions[i].horizon, INT_VALUE);
      FileWriteLong(handle, (long)g_positions[i].opened);
      FileWriteInteger(handle, g_positions[i].opened_bar_count, INT_VALUE);
   }

   FileClose(handle);

   // Atomic replace: Delete existing primary, rename temp to primary
   if(FileIsExist(AMIGO_STATE_FILE_PRIMARY))
      FileDelete(AMIGO_STATE_FILE_PRIMARY);

   if(!FileMove(AMIGO_STATE_FILE_TEMP, 0, AMIGO_STATE_FILE_PRIMARY, 0))
   {
      LogMsg(LOG_WARN, "PERSIST_SAVE", StringFormat("Failed to replace primary state file with temp (err=%d)", GetLastError()));
      return false;
   }

   return true;
}

//+------------------------------------------------------------------+
//| Load and Reconcile Positions from Persistent State on Startup    |
//| Enforces Strict Fail-Closed Verification against Broker State    |
//+------------------------------------------------------------------+
int PositionReconcileState(const AmigoConfig &cfg)
{
   if(!FileIsExist(AMIGO_STATE_FILE_PRIMARY))
   {
      LogMsg(LOG_INFO, "PERSIST_LOAD", "No prior persistent position state file found. Clean startup.");
      return 0;
   }

   int handle = FileOpen(AMIGO_STATE_FILE_PRIMARY, FILE_BIN|FILE_READ);
   if(handle == INVALID_HANDLE)
   {
      LogMsg(LOG_WARN, "PERSIST_LOAD", StringFormat("Cannot open state file %s (err=%d)", AMIGO_STATE_FILE_PRIMARY, GetLastError()));
      return 0;
   }

   // 1. Read & Validate Header
   int schema = FileReadInteger(handle, INT_VALUE);
   if(schema != AMIGO_STATE_SCHEMA_VERSION)
   {
      LogMsg(LOG_WARN, "PERSIST_LOAD", StringFormat("Unsupported state schema version %d (expected %d). State ignored.", schema, AMIGO_STATE_SCHEMA_VERSION));
      FileClose(handle);
      return 0;
   }

   long saved_magic = FileReadLong(handle);
   if((ulong)saved_magic != cfg.magic_number)
   {
      LogMsg(LOG_WARN, "PERSIST_LOAD", StringFormat("Magic number mismatch in state file: file=%I64d current=%I64u. State ignored.", saved_magic, cfg.magic_number));
      FileClose(handle);
      return 0;
   }

   int count = FileReadInteger(handle, INT_VALUE);
   long saved_time = FileReadLong(handle);

   if(count < 0 || count > AMIGO_STATE_MAX_POSITIONS)
   {
      LogMsg(LOG_WARN, "PERSIST_LOAD", StringFormat("Invalid position count %d in state file. State ignored.", count));
      FileClose(handle);
      return 0;
   }

   int recovered_count = 0;

   // 2. Read each position and reconcile with broker/shadow state
   for(int k = 0; k < count; k++)
   {
      PositionState p;
      ZeroMemory(p);
      p.position_id           = (ulong)FileReadLong(handle);
      p.direction             = FileReadInteger(handle, INT_VALUE);
      p.entry                 = FileReadDouble(handle);
      p.initial_stop          = FileReadDouble(handle);
      p.initial_target        = FileReadDouble(handle);
      p.initial_atr           = FileReadDouble(handle);
      p.initial_risk_per_unit = FileReadDouble(handle);
      p.partial_done          = (FileReadInteger(handle, INT_VALUE) == 1);
      p.current_stop          = FileReadDouble(handle);
      p.be_activated          = (FileReadInteger(handle, INT_VALUE) == 1);
      p.be_trigger_price      = FileReadDouble(handle);
      p.last_applied_stop     = FileReadDouble(handle);
      p.trailing_mode         = (ENUM_TRAILING_MODE)FileReadInteger(handle, INT_VALUE);
      p.horizon               = (ENUM_HORIZON)FileReadInteger(handle, INT_VALUE);
      p.opened                = (datetime)FileReadLong(handle);
      p.opened_bar_count      = FileReadInteger(handle, INT_VALUE);

      // Invariant Check: Broker Position Verification in live mode
      if(!cfg.shadow_only)
      {
         if(!PositionSelectByTicket(p.position_id))
         {
            LogMsg(LOG_INFO, "PERSIST_RECON", StringFormat("Persisted ticket %I64u closed while offline. Skipping.", p.position_id));
            continue;
         }

         // Verify symbol and magic number match
         string pos_sym = PositionGetString(POSITION_SYMBOL);
         ulong  pos_mag = (ulong)PositionGetInteger(POSITION_MAGIC);
         if(pos_sym != cfg.symbol || pos_mag != cfg.magic_number)
         {
            LogMsg(LOG_WARN, "PERSIST_RECON", StringFormat("Ticket %I64u ownership conflict: sym=%s magic=%I64u. Skipping.", p.position_id, pos_sym, pos_mag));
            continue;
         }

         // Update authoritative broker-side current levels
         p.current_stop = PositionGetDouble(POSITION_SL);
         double cur_tp  = PositionGetDouble(POSITION_TP);
         if(cur_tp > 0.0) p.initial_target = cur_tp;

         // Check if stop was manually moved to/beyond entry while offline
         if(!p.be_activated && p.current_stop > 0.0)
         {
            if((p.direction == +1 && p.current_stop >= p.entry) ||
               (p.direction == -1 && p.current_stop <= p.entry))
            {
               p.be_activated = true;
               LogMsg(LOG_INFO, "PERSIST_RECON", StringFormat("Ticket %I64u stop at/beyond entry. Restoring be_activated=true.", p.position_id));
            }
         }
      }

      // Re-register into active in-memory array
      int n = ArraySize(g_positions);
      ArrayResize(g_positions, n + 1);
      g_positions[n] = p;
      recovered_count++;

      string h_name = (p.horizon == HORIZON_SCALPING) ? "SCALPING" : (p.horizon == HORIZON_SWING) ? "SWING" : "INTRADAY";
      LogMsg(LOG_INFO, "PERSIST_RECON", StringFormat("Recovered position %I64u horizon=%s dir=%d entry=%.5f sl=%.5f be=%s partial=%s",
             p.position_id, h_name, p.direction, p.entry, p.current_stop, p.be_activated ? "YES" : "NO", p.partial_done ? "YES" : "NO"));
   }

   FileClose(handle);
   LogMsg(LOG_INFO, "PERSIST_LOAD", StringFormat("Reconciliation complete: %d active positions restored from disk.", recovered_count));
   return recovered_count;
}
