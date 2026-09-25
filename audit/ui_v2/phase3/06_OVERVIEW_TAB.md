# 06 — OVERVIEW TAB IMPLEMENTATION

## 1. Overview Screen Structure

The `OverviewTab` provides situational awareness formatted for fast institutional inspection:

1. **HALT Warning Banner**:
   - Only appears if the system is `HALTED` or `is_paused == true`.
   - Displays HALT reason and HALT generation token in high-contrast red alert styling.
2. **System Status & Projection Panel**:
   - Execution Service state badge (`HEALTHY`, `HALTED`, or `UNKNOWN`).
   - Projection Source: `EXECUTION_SERVICE`.
   - Circuit Breaker status: `ARMED` (cyan) or `TRIPPED` (red).
   - Generation token and halt reason.
3. **Key Telemetry Metrics (2x2 Grid)**:
   - **Balance (USDT)**: Strictly renders `—` when unbacked (never $1000).
   - **Realized PnL (USDT)**: Directionally colored (`+` green, `-` red, or `—`).
   - **PnL State**: `KNOWN_VALUE` (cyan) or `UNKNOWN` (muted).
   - **Open Positions**: Active count vs max concurrent positions (e.g. `1 / 3`).
4. **Active Positions Snapshot**:
   - Shows top 3 active positions with symbol, side, entry price, and PnL.
   - Tap row to open `PositionDetailSheet`.
   - "XEM TẤT CẢ" header button jumps directly to Positions Tab.
   - If 0 positions: renders stoic `QuantEmptyState` ("Không có vị thế mở").
5. **Governance & Certification Banner**:
   - Lõi giao dịch: `OFFLINE EXECUTION CORE ACCEPTED`
   - Toàn vẹn mã nguồn: `15/15 PRESERVED (0 MISMATCH)`
   - Chứng chỉ API sàn: `REMOVED (0 credentials)`
   - Thị trường mở: `OFFLINE ONLY (Live/Testnet Disabled)`
