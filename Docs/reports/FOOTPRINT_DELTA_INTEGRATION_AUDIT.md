# FOOTPRINT AND PROXY DELTA INTEGRATION AUDIT
**Amigo / ASAP Retail Order-Flow System**
**Date:** September 23, 2026

---

## 1. Producer-Consumer Dependency Map

```text
[Producer: MQL5 Tick Feed / Python Ticks]
                    â”‚
                    â–¼
          [Price Bin Engine]
                    â”‚
                    â–¼
         [Proxy Footprint Engine]
       (Tick Rule Classification)
                    â”‚
        â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
        â–¼                       â–¼
 [Footprint Delta]      [Cumulative Delta]
        â”‚                       â”‚
        â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                    â–¼
        [Footprint Pressure Engine]
        (P = Î£Î´ / (Î£|Î´| + Îµ) âˆˆ [-1, +1])
                    â”‚
        â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
        â–¼           â–¼           â–¼
     [Surge]      [Flip]   [Transition]
        â”‚           â”‚           â”‚
        â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                    â–¼
          [Multi-Bar Events]
     (Persistence, Divergence)
                    â”‚
                    â–¼
       [Shadow Mode Log / EA Output]
```

---

## 2. Integration Status & Path Mapping

| Metric / Feature | Python Implementation (`orderflow_lab`) | MQL5 Native Implementation (`MQL5/Include/`) | Active Runtime Role | Status Label |
| :--- | :--- | :--- | :--- | :--- |
| **Tick Classification** | `PriceBinEngine` (Tick Rule) | `CAM_Footprint::AddTick` (Tick Rule) | Native MQL5 & Python | `IMPLEMENTED AND VERIFIED` |
| **Footprint Pressure** | `ProxyFootprintEngine` | `CAM_Footprint::CalculateFootprintPressure` | Native MQL5 & Python | `IMPLEMENTED AND VERIFIED` |
| **Cumulative Delta** | `ProxyFootprintEngine.cumulative_delta` | `CAM_Footprint::GetCumulativeDelta` | Shadow Mode | `IMPLEMENTED AND VERIFIED` |
| **Legacy Delta** | `delta_A` (Tick sign), `delta_B` ($CLV \times V$) | `FeatureSnapshot.fusion` | Active EA Execution | `IMPLEMENTED AND VERIFIED` |
| **Delta Migration** | Dual-tracking running in parallel | Dual-tracking running in parallel | Shadow Mode | `REQUIRES OWNER DECISION` |

---

## 3. Labeling Integrity Standard
Retail tick data is strictly labeled `PROXY` / `ESTIMATED_DIRECTION`. It is never falsely presented as centralized exchange level-2 depth or true aggressive trader execution.

