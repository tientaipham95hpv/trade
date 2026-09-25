# 04 — STITCH COMPONENT MAPPING

## 1. Overview & Visual Design Mapping

The visual source is the **Obsidian Quants — Binance Quant Pro** design language:
- **Design Philosophy**: High-density Technical Minimalist.
- **Aesthetic**: Bloomberg Terminal density + Linear dark-mode polish + Institutional quant terminal.
- **Canonical Color Tokens**:
  - `background`: `#051424`
  - `surfaceLowest`: `#010F1F`
  - `surfaceLow`: `#0D1C2D`
  - `surface`: `#122131`
  - `surfaceHigh`: `#1C2B3C`
  - `surfaceHighest`: `#273647`
  - `border`: `#1C2E42`
  - `borderActive`: `#334155`
  - Functional: `gold` (`#F0B90B`), `cyan` (`#00F0FF`), `green` (`#0ECB81`), `red` (`#F6465D`), `purple` (`#A855F7`)
  - Text: `textPrimary` (`#D4E4FA`), `textSecondary` (`#B9CACB`), `textMuted` (`#849495`)
- **Typography**: Inter (UI / navigation / labels) & JetBrains Mono with tabular figures (`tnum`, `zero`) for all prices, PnL, percentages, timestamps, IDs, and metrics.
- **Density & Shapes**: 2px/4px/8px/12px/16px rhythm; 4px default radius; 8px max container radius; 1px subtle borders.

---

## 2. Component-to-Backend Mapping Matrix

| Stitch Visual Component | Target UI Element | Authoritative Backend Field / Source | Empty / Fallback State |
| :--- | :--- | :--- | :--- |
| **Top Telemetry: Environment** | Header Pill Badge | `config.trader_environment` / Backend state | Displays `OFFLINE` (cyan `#00F0FF`) |
| **Top Telemetry: Execution** | Header Pill Badge | `service_status.state` from `query_status()` | `HEALTHY` (green) / `HALTED` (red) / `UNKNOWN` (red) |
| **Top Telemetry: Web State** | Header Pill Badge | `/ready` probe (`READY`, `HALTED`, `NOT_READY`) | `READY` (green) / `NOT_READY` (red) |
| **Top Telemetry: Telegram** | Header Pill Badge | Telegram worker process heartbeat | `READY` (green) / `STANDBY` (gray) |
| **Top Telemetry: HALT** | Header Pill Badge | `service_status.global_halt` & `halt_generation` | `INACTIVE` (cyan) / `GEN #N` (red) |
| **Top Telemetry: Recovery** | Header Pill Badge | `service_status.recovery_required` | `CLEAR` (green) / `RECOVERY_REQUIRED` (red) |
| **Top Telemetry: Latency** | Header Pill Badge | Measured client HTTP roundtrip to `/health` | Tabular numeric ms (e.g. `24 ms`) |
| **System Status Panel** | Multi-row status list | Health dimensions from `query_status()` | Real-time status for each dimension |
| **Performance: Realized PnL**| Metric Card | `pnl.total_pnl` from `query_pnl()` (`pnl_ledger`) | JetBrains Mono; `+$0.00` / `-$0.00` |
| **Performance: Unrealized PnL**| Metric Card | Position sum or `null` in offline | `—` (No unverified calculations) |
| **Performance: Win Rate** | Metric Card | Computed from closed `ClientOrderLog` rows | `—` if 0 closed trades; formatted `0.0%` |
| **Performance: Trade Count** | Metric Card | Count of closed orders in `ClientOrderLog` | Integer count (e.g. `12 trades`) |
| **Equity Curve Chart** | Canvas / SVG Chart | Cumulative realized PnL from `pnl_ledger` | `Chưa có dữ liệu giao dịch.` (no fake curves) |
| **Active Positions Table** | Dense Data Table | `client.query_positions()` list/dict | `Không có vị thế đang mở` |
| **Position Row: Symbol** | Table Column | `position.symbol` (e.g. `BTCUSDT`) | Monospace text |
| **Position Row: Side** | Table Column Badge | `position.side` (`BUY` / `SELL`) | `LONG` (`#0ECB81`) / `SHORT` (`#F6465D`) |
| **Position Row: Qty / Entry** | Table Column | `position.quantity`, `position.entry_price` | Formatted tabular decimal |
| **Position Row: Mark / PnL** | Table Column | `position.current_price`, `position.unrealized_pnl` | Colored green/red |
| **Position Row: SL / TP** | Table Column | `position.stop_loss`, `position.take_profit` | Tabular price or `—` |
| **Position Row: Protection** | Table Column Badge | `position.protection_state` | `ACTIVE` (green) / `NONE` (gray) |
| **Position Detail Drawer** | Slide-out panel | Full position dict + execution receipt ID | Read-only details; safe close button |
| **Risk: Circuit Breaker** | Risk Panel Badge | `query_circuit_breaker()` (`state`, `is_active`)| `HEALTHY` (green) / `TRIPPED` (red) |
| **Risk: Consecutive Losses** | Risk Metric Card | Breaker streak counter from execution store | Integer counter |
| **Risk: Daily Loss** | Risk Metric Card | Accumulated daily loss from risk store | Dollar amount vs max limit |
| **Risk: Cooldown Timer** | Risk Countdown | `circuit_breaker.cooldown_until` | Monospace countdown or `INACTIVE` |
| **Risk: Safety Flags** | Risk List | `global_halt`, `recovery_required`, fee conflicts | Explicit green/red status list |
| **Operator Action: HALT** | Action Button | `POST /api/pause` | Requires confirmation modal |
| **Operator Action: RESUME** | Action Button | `POST /api/resume` (with `halt_generation`) | Enabled only if halted & resumable |
| **Activity Stream** | Event List | `GET /api/history` + `GET /api/logs` | Chronological event list with severity tags |
| **System Info Screen** | Configuration Grid | Non-secret system settings & certification | Display-only; zero secret keys |

---

## 3. Discrepancy & Verification Rules

1. **No Client-Side Financial Authority**:
   - The UI never computes its own PnL ledger. Realized PnL is authoritatively provided by the Execution Service.
   - If a metric cannot be queried from authoritative backend data, it MUST render as `—` (dash) or `No data`.
2. **Tabular Metric Stability**:
   - All financial figures must use `JetBrains Mono` with CSS `font-feature-settings: "tnum" 1, "zero" 1;` to prevent horizontal jumping when numbers update.
3. **Data Update Flash**:
   - Numeric cells flash green (`rgba(14,203,129,0.12)`) on increase, or red (`rgba(246,70,93,0.12)`) on decrease for 150ms.
4. **Strict Color Semantics**:
   - `OFFLINE` environment mode is ALWAYS rendered in **Cyan** (`#00F0FF`).
   - `TESTNET` is rendered in **Gold** (`#F0B90B`).
   - `LIVE` is rendered in high-attention **Red/Gold**.
   - `HALTED` / `CRITICAL` is rendered in **Red** (`#F6465D`).
   - `HEALTHY` / `READY` is rendered in **Green** (`#0ECB81`).
