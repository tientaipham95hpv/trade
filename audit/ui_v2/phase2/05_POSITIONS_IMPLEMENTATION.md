# 05 — POSITIONS VIEW & DETAIL DRAWER SPECIFICATION

## 1. Table Layout & Sizing

The Positions View (`web/static/ui_v2/js/positions.js`) provides an institutional grid displaying all active positions from the Execution Service:

- **Columns**:
  1. `SYMBOL`: Asset ticker (e.g. `BTCUSDT`, in cyan tabular mono).
  2. `SIDE`: `LONG` (green) or `SHORT` (red).
  3. `QTY`: Position size, right-aligned with fixed precision.
  4. `ENTRY`: Execution entry price in USD.
  5. `MARK`: Authoritative mark price.
  6. `UNREALIZED`: Unrealized PnL with `+/-` sign and semantic coloring.
  7. `SL`: Active protective Stop Loss price.
  8. `TP`: Take Profit price target.
  9. `PROTECTION`: State of stop order (`ACTIVE_STOP`, `SL_GUARDED`).
  10. `STATE`: Lifecycle state (`FILLED`, `PROTECTED`).
  11. `ACTION`: Read-only `VIEW` button to trigger the detail drawer.

---

## 2. Slide-Over Detail Drawer

Clicking any row opens a slide-over inspection drawer on the right side of the screen (`.position-drawer`):

- **Read-Only Telemetry**:
  - Symbol, Side, Quantity
  - Entry Price, Mark Price
  - Unrealized PnL (in tabular numbers)
  - Stop Loss and Take Profit
  - Leverage and Margin Type (`ISOLATED`)
  - Protection Engine State
  - Execution Receipt ID
  - Fee & Accounting Status (`RECONCILED_NO_DISCREPANCY`)

- **Prohibited Controls Strictly Omitted**:
  The drawer contains **zero interactive trade controls**:
  - No `BUY` or `SELL` buttons
  - No `ADD TO POSITION` or `REDUCE SIZE`
  - No `MOVE STOP LOSS` or `EDIT TAKE PROFIT`
  - No `CHANGE LEVERAGE`
  The footer displays: `READ-ONLY TELEMETRY (MANUAL TRADING DISABLED)`.

---

## 3. Empty State Handling

When no positions are open, the table gracefully collapses to:
```text
┌────────────────────────────────────────────────────────┐
│  Không có vị thế mở nào đang hoạt động                 │
│  Hệ thống đang ở chế độ giám sát an toàn.              │
│  Zero open margin exposure.                            │
└────────────────────────────────────────────────────────┘
```
This guarantees no broken table borders, zero runtime JavaScript exceptions, and clear operational visibility.
