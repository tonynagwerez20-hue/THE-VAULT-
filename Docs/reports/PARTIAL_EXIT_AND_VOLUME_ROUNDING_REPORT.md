# AMIGO — Partial Exit & Volume Rounding Report

**Document Date:** 2026-11-02  
**Target Code:** `MQL5/Include/Position Manager.mqh` (Lines 35–48, 234–275)  
**Evaluator:** Antigravity Execution Engineer  

---

## 1. Broker Volume Rounding Algorithm

The `RoundVolume()` helper handles step sizing and boundary clamping per symbol specifications:

```mql5
double RoundVolume(string symbol, double raw)
{
   double step = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
   if(step <= 0.0) return raw;

   double rounded = MathRound(raw / step) * step;

   double vmin = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double vmax = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
   if(vmin > 0.0 && rounded < vmin) rounded = vmin;
   if(vmax > 0.0 && rounded > vmax) rounded = vmax;

   return rounded;
}
```

---

## 2. Live Partial Feasibility & Dual-Minimum Invariant

In live execution (`!cfg.shadow_only`), taking a partial exit requires splitting a position into two valid broker lots:
1. The **closing slice** (`part`).
2. The **remaining active position** (`vol - part`).

Lines 248–254 enforce the dual-minimum boundary:
```mql5
double vol = PositionGetDouble(POSITION_VOLUME);
double raw  = vol * cfg.partial_fraction;
double part = RoundVolume(sym, raw);
double vmin = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);

if(part >= vmin && (vol - part) >= vmin)
{
   if(g_trade.PositionClosePartial(pid, part))
   {
      g_positions[i].partial_done = true;
      LogMsg(LOG_INFO, "PARTIAL_EXIT", ...);
   }
   else
   {
      LogMsg(LOG_WARN, "PARTIAL_FAILED", ...);
   }
}
```

### The 0.01 Lot Edge Case:
- On micro-accounts or standard minimum lot sizing (0.01 lots on XAUUSDm):
  - `vol` = 0.01
  - `raw` = 0.01 $\times$ 0.50 = 0.005
  - `part` clamped by `RoundVolume` = 0.01
  - Remaining volume = `vol - part` = 0.01 - 0.01 = 0.00 < `vmin` (0.01)
- **Result:** The condition `(vol - part) >= vmin` evaluates to **FALSE**.
- The partial order is safely skipped; the entire 0.01 position remains open to pursue the full TP target. No invalid fractional orders are sent to the broker.

---

## 3. Shadow Mode vs Live Mode Discrepancy

In shadow mode (`cfg.shadow_only == true`):
```mql5
else
{
   // In shadow mode, mark synthetic partial completion
   g_positions[i].partial_done = true;
   LogMsg(LOG_INFO, "SHADOW_PARTIAL", StringFormat("ticket=%I64u horizon=%d partial_hit=true price=%.5f",
          pid, (int)horiz, cur_price));
}
```

### Operational Finding:
In shadow mode, `partial_done` is flagged `true` whenever price touches the partial target ($1.5R$ or $2.0R$) regardless of whether the position volume would physically permit a partial close on a live broker.
- **Classification:** **LIVE MODE VERIFIED; SHADOW MODE SYNTHETIC ASSUMPTION (KNOWN GAP).**
