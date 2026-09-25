# 02 — NAVIGATION MIGRATION

## 1. Migration Map

The legacy Flutter application had 5 navigation items including obsolete exploratory and manual control tabs:

```text
[LEGACY NAVIGATION]               [V2 OBSIDIAN QUANTS NAVIGATION]
-------------------               -------------------------------
DashboardTab ────────────────────> Tab 0: TỔNG QUAN (Overview)
PositionsTab ────────────────────> Tab 1: VỊ THẾ (Positions - Read Only)
HistoryTab   ─────────┐
                      ├─── Folded ──> Integrated into Overview & System
ScannerTab   ─────────┴──────────> [RETIRED / DELETED FROM NAVIGATION]
AiCopilotTab ────────────────────> [RETIRED / DELETED FROM NAVIGATION]
                                   Tab 2: RỦI RO (Risk & Breaker) [NEW]
                                   Tab 3: HỆ THỐNG (System & Governance) [NEW]
```

---

## 2. Retirement Audit

| Legacy Screen | Status | Action Taken |
|---|---|---|
| `screens/scanner_tab.dart` | **RETIRED** | Removed from active navigation, zero routes reference it. |
| `screens/ai_copilot_tab.dart` | **RETIRED** | Removed from active navigation, zero routes reference it. |
| `screens/history_tab.dart` | **RETIRED** | Standalone tab retired; audit logs moved to System tab, performance metrics folded into Overview tab. |
| `screens/settings_dialog.dart` | **RETIRED** | Obsolete credential input dialog retired; session management moved to System tab. |

---

## 3. Active 4-Tab Specification

1. **`TỔNG QUAN` (Overview)**:
   - Icon: `Icons.dashboard_outlined` / `Icons.dashboard`
   - Content: Execution Service projection status, ARMED/TRIPPED circuit breaker, 2x2 key metrics grid (Balance, Realized PnL, PnL State, Open Positions), Active positions preview, and Core Certification badge.
2. **`VỊ THẾ` (Positions)**:
   - Icon: `Icons.table_chart_outlined` / `Icons.table_chart`
   - Content: Dense inspection list of open positions. Tap opens `PositionDetailSheet`. Zero manual BUY/SELL or close order triggers.
3. **`RỦI RO` (Risk)**:
   - Icon: `Icons.shield_outlined` / `Icons.shield`
   - Content: Circuit breaker telemetry, HALT state machine, generation token, subsystem health dimensions, and Phase 3 read-only safety guard notice with preview confirmation sheets.
4. **`HỆ THỐNG` (System)**:
   - Icon: `Icons.terminal_outlined` / `Icons.terminal`
   - Content: Architecture governance matrix (7 hard rules), core execution certification, live system logs viewer (`/api/logs`), active admin session display, and Keychain logout flow.
