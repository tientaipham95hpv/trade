# 07 — POSITIONS TAB & INSPECTION SHEET

## 1. Positions Tab Specification

The `PositionsTab` is a dedicated, read-only view of active positions:

- **Header Telemetry**: Active count vs max concurrent positions, accompanied by explicit notice: `QUYỀN ĐẶT LỆNH THỦ CÔNG: VÔ HIỆU HÓA (PROHIBITED)`.
- **Empty State**: When 0 positions are active, renders `QuantEmptyState` with description: `Lõi giao dịch đang ở trạng thái flat (0 vị thế). Tất cả nguồn lực an toàn trong trạng thái chờ.`
- **Position Cards**:
  - Symbol and Side badge (`LONG` green, `SHORT` red).
  - Leverage indicator (e.g. `5x`).
  - Entry Price vs Mark Price.
  - Unrealized PnL (USDT & %) with directional coloring.
  - Protection status (`BE Moved`, `Armed`, `Trailing`, `—`).

---

## 2. Read-Only Position Detail Sheet

Tapping any position card presents `PositionDetailSheet`:
- Full metadata breakdown: Entry Price, Mark Price, Position Qty, Margin, Liquidation Price, Stop Loss, Take Profit, and Protection Status.
- **Institutional Guard Banner**:
  ```text
  CHẾ ĐỘ XEM CHỈ ĐỌC (READ-ONLY)
  Vị thế được quản lý hoàn toàn tự động bởi lõi giao dịch ngoại tuyến (Execution Service).
  Không mở quyền can thiệp thủ công từ thiết bị di động.
  ```
- **Zero Mutation Surfaces**: Completely free of BUY, SELL, or manual CLOSE order buttons.
