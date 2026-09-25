# 03 — COMPONENT INVENTORY & PARITY MATRIX

## 1. Cross-Platform Parity Overview

Phase 1 provides complete visual and structural parity between the Web V2 dashboard primitives and Flutter iOS V2 components. Every visual element has a 1-to-1 equivalent across both platforms.

---

## 2. Component Inventory & Mapping Table

| Component Name | Web V2 CSS Primitive (`web/static/ui_v2/`) | Flutter iOS V2 Widget (`ios-app/lib/ui_v2/`) | Functional Purpose |
|---|---|---|---|
| **Terminal Panel** | `.terminal-panel`, `.panel-header`, `.panel-body`, `.panel-footer` | `QuantPanel` | Primary container for trading telemetry, order books, and logs |
| **Metric Card** | `.metric-card`, `.metric-value`, `.metric-delta`, `.metric-label` | `QuantMetric` | Displaying PnL, Win Rate, Margin Usage, and Balance |
| **Telemetry Item** | `.telemetry-item`, `.telemetry-key`, `.telemetry-val` | `QuantTelemetryItem` / row in `QuantPanel` | Compact key-value telemetry pairs (IPC Latency, Service PID) |
| **Environment Badge** | `.env-badge`, `.env-badge--offline`, `.env-badge--live` | `EnvironmentBadge` (`EnvironmentType.offline`, etc.) | Prominent indicator showing execution environment |
| **Status Badge** | `.status-badge`, `.status-badge--healthy`, `--halt` | `QuantStatusBadge` (`QuantStatusType.healthy`, etc.) | System and operational state pill with indicator dot |
| **Dense Data Table** | `.dense-table`, `.dense-table-container` | `ListView.separated` / `DataTable` with `QuantTypography` | High-density transaction logs, executions, and positions |
| **Risk / Alert Banner** | `.risk-alert`, `.risk-alert--warning`, `--halt` | `QuantRiskBanner` (`RiskSeverity.warning`, etc.) | Highlighting breaker trips, drawdown alerts, and halts |
| **Empty State** | `.empty-state`, `.empty-state-title`, `.empty-state-desc` | `QuantEmptyState` | Informative fallback for zero active positions / executions |
| **Loading Indicator** | `.skeleton`, `.skeleton-text`, `.pulse-loader` | `QuantSkeleton`, `QuantLoading` | Asynchronous placeholder during backend fetches |
| **Confirmation Modal** | `.confirm-dialog`, `.confirm-dialog-content` | `QuantConfirmSheet` | High-risk action verification with CAS generation guard |
| **Section Header** | `.section-header`, `.section-title`, `.section-meta` | `QuantSectionHeader` | Grouping visual panels into semantic dashboard sections |

---

## 3. Behavioral Guarantees

### A. Null and Missing Data Resilience
- **Web V2**: CSS handles empty spans cleanly; empty data attributes or missing values display institutional em-dash (`—`) without distorting cell heights.
- **Flutter V2**: `QuantMetric` defaults to `—` when `value == null`, preventing `NullPointerExceptions` or layout collapses.

### B. Prohibited Functionality Absence
Neither the Web V2 nor the Flutter V2 component libraries contain:
- Input fields for Binance API Keys or Secrets.
- Toggles to enable copy-trading.
- Interactive BUY / SELL manual order entry buttons.
- Autonomous AI order generation selectors.
- Environment switching dropdowns (environment is read-only from backend).
- Hardcoded fake financial data fallbacks.
