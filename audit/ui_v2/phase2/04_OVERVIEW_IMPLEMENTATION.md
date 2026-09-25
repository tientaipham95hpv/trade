# 04 — OVERVIEW VIEW IMPLEMENTATION SPECIFICATION

## 1. Grid & Information Density

The Overview View (`web/static/ui_v2/js/overview.js`) renders a dense 12-column Bloomberg-style operator dashboard:

```text
┌────────────────────────────────────────────────────────────────────────┐
│  Top Telemetry Bar: ENV (OFFLINE), EXEC, WEB, TG, HALT, RTT, CLOCK      │
├─────────────────┬──────────────────────┬───────────────────────────────┤
│ SYSTEM STATUS   │ PNL / PERFORMANCE    │ RISK & CIRCUIT BREAKER        │
│ (col-span-4)    │ (col-span-4)         │ (col-span-4)                  │
├─────────────────┴──────────────────────┼───────────────────────────────┤
│ ACTIVE POSITIONS SUMMARY               │ PROTECTION & RECOVERY         │
│ (col-span-8)                           │ (col-span-4)                  │
└────────────────────────────────────────┴───────────────────────────────┘
```

---

## 2. Component Breakdown

### A. System Projection Panel (`col-span-4`)
- **Status Badge**: Displays `HEALTHY` (green dot) or `HALTED` (red dot), or `UNKNOWN` (degraded).
- **Core Status**: `OFFLINE_OK` (Deterministic Sandbox).
- **IPC Transport**: Live round-trip latency (e.g. `14 ms`) to loopback 50051.
- **State Store**: SQLite WAL Certified.
- **Global HALT & Generation**: Reflection of authoritative pause state and current generation token.

### B. PnL & Performance Panel (`col-span-4`)
- **Realized PnL**: Formatted using `Formatters.pnl()`, right-aligned with tabular numbers, colored green for profit, red for loss.
- **Active Positions Count**: Formatted integer with max cap indicator.
- **Unverified Metrics**: Win Rate, Total Trades, and Max Drawdown display `—` with tooltip `Authoritative metric unavailable`.
- **Equity Status**: Displays `Chưa có dữ liệu equity được xác nhận.`

### C. Risk & Circuit Breaker Panel (`col-span-4`)
- **Breaker Status**: `ARMED` (healthy) or `TRIPPED` (halt).
- **Daily Loss**: Current loss vs authoritative limit.
- **Consecutive Loss**: Consecutive loss count vs maximum threshold.
- **Cooldown**: Timestamp of cooldown expiry or `CLEAR`.

### D. Active Positions Mini-Table (`col-span-8`)
- Compact preview of current open positions showing Symbol, Side (LONG/SHORT), Quantity, Entry, Mark, Unrealized PnL, and Protection Status.
- Fallback to institutional empty state when zero positions are active.

### E. Protection & Recovery Panel (`col-span-4`)
- Status of Trailing Stop engine, Activation Risk-Reward ratio, Leverage, and Isolated Margin enforcement.
