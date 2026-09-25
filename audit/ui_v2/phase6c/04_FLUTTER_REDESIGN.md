# AUDIT REPORT — PHASE 6C: FLUTTER iOS V2 REDESIGN SPECIFICATION

## 1. Mobile Design Philosophy
Flutter iOS V2 does not imitate desktop tables in an unreadable squished format; instead, it adopts a high-density, card-structured institutional operator layout tailored for native mobile usability.

### Key Mobile Architectural Changes:
1. **Persistent Header**:
   - Header bar with `BINANCE QUANT PRO / OPERATOR CONSOLE`, `OFFLINE` environment pill, authoritative status pill (`HEALTHY`), IPC latency, and refresh button.
   - Max 8px border radius throughout.
2. **Bottom Navigation (4 Tabs)**:
   - `TỔNG QUAN` (Overview) — `Icons.dashboard_outlined`
   - `VỊ THẾ` (Positions) — `Icons.table_chart_outlined`
   - `RỦI RO` (Risk) — `Icons.shield_outlined`
   - `HỆ THỐNG` (System) — `Icons.terminal_outlined`
   - Zero emojis. Clean SVG outline icons.
3. **Overview Tab**:
   - Status & projection panel with circuit breaker indicator and authoritative halt generation.
   - Telemetry strip with balance, realized PnL, open position count, and daily loss.
   - Active position preview cards.
4. **Positions Tab**:
   - Structured compact position cards:
     - Header: Symbol + Long/Short subtle pill + leverage tag.
     - Row 1: Entry Price vs Mark Price.
     - Row 2: Unrealized PnL + Stop Loss + Take Profit.
     - Protection status indicator (`ACTIVE_STOP`).
   - Position detail modal bottom sheet (read-only, zero mutation controls).
5. **Risk Tab**:
   - Circuit breaker status (`ARMED / FAIL-CLOSED`).
   - CAS generation inspection (# generation tracking).
   - Recovery required status and resume criteria gate.
   - Operator actions:
     - Dark red outline `HALT` button.
     - Neutral/cyan outline `RESUME` button with CAS confirmation modal.
     - Muted `Emergency close: Unavailable in this console` note.
6. **System Tab**:
   - Grouped settings-style architecture sections:
     - Runtime Environment
     - Authority Boundaries (0 client credentials, loopback IPC only)
     - Core Certification (15/15 verified)
     - Streaming operational logs.
