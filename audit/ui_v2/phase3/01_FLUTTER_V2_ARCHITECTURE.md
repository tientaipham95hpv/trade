# 01 — FLUTTER V2 ARCHITECTURE

## 1. Design Tokens and Visual Language

The Flutter iOS V2 operator console adheres strictly to the **Obsidian Quants** visual design language established in Phase 1:

- **Background Foundation**: Deep void `#051424` (`QuantColors.background`).
- **Surface Elevation Hierarchy**:
  - `QuantColors.surfaceLowest`: `#010F1F` (nested telemetry wells, logs background)
  - `QuantColors.surfaceLow`: `#0D1C2D` (icon wells, headers)
  - `QuantColors.surface`: `#122131` (standard panel background)
  - `QuantColors.surfaceHigh`: `#1C2B3C` (active cards)
- **Functional Accents**:
  - `QuantColors.cyan`: `#00F0FF` (OFFLINE environment pill, execution state, active metrics)
  - `QuantColors.green`: `#0ECB81` (HEALTHY state, positive PnL, LONG badge)
  - `QuantColors.gold`: `#F0B90B` (Warning level, TESTNET, caution)
  - `QuantColors.red`: `#F6465D` (HALTED state, negative PnL, SHORT badge, danger triggers)
- **Monospace Tabular Figures**:
  - All numerical values, prices, PnL, timestamps, and percentages utilize tabular figures with slashed zeros (`FontFeature.tabularFigures()`, `FontFeature.slashedZero()`) to prevent horizontal layout jitter during periodic polling.

---

## 2. Directory Layout

All Phase 3 V2 mobile components reside in `ios-app/lib/ui_v2/`:

```text
ios-app/lib/ui_v2/
├── models/
│   ├── activity_view.dart        # Trade history and closed trades models
│   ├── position_view.dart        # Safe, nullable active position models
│   ├── risk_view.dart            # Circuit breaker and telemetry model
│   └── system_status.dart        # /api/status parsing with zero fake defaults
├── screens/
│   ├── home_screen.dart          # Persistent header and 4-tab container
│   ├── login_screen.dart         # Institutional dark login screen
│   ├── overview_tab.dart         # TỔNG QUAN screen
│   ├── position_detail_sheet.dart# Read-only modal position inspection
│   ├── positions_tab.dart        # VỊ THẾ screen
│   ├── risk_tab.dart             # RỦI RO screen
│   └── system_tab.dart           # HỆ THỐNG screen
├── services/
│   ├── auth_store.dart           # Keychain-backed secure storage
│   ├── polling_controller.dart   # Lifecycle-aware background/foreground coordinator
│   └── quant_api_client.dart     # Fail-closed HTTP client with 401 handling
├── theme/
│   ├── quant_colors.dart         # Obsidian Quants color tokens
│   ├── quant_spacing.dart        # Padding, radius, touch targets
│   ├── quant_theme.dart          # ThemeData dark theme definition
│   └── quant_typography.dart     # Tabular monospace and typography styles
├── utils/
│   └── quant_formatters.dart     # Currency, PnL, percentage, latency formatters
└── widgets/
    ├── environment_badge.dart    # OFFLINE pill badge
    ├── quant_confirm_sheet.dart  # Operator confirmation bottom sheet
    ├── quant_empty_state.dart    # Stoic empty state display
    ├── quant_loading.dart        # Institutional spinner
    ├── quant_metric.dart         # Metric display with null '—' fallback
    ├── quant_panel.dart          # Technical bordered panel container
    ├── quant_risk_banner.dart    # Risk alert banner
    ├── quant_section_header.dart # Uppercase tracked section header
    └── quant_status_badge.dart   # HEALTHY / HALTED / UNKNOWN badge
```

---

## 3. Strict Absence of Fake Financial Defaults

1. **Balance Representation**:
   - The backend `/api/status` explicitly returns `"balance": null` when not queried or unbacked.
   - Legacy code parsed `safeParseDouble(json['balance'], 1000.0)`, fabricating a false $1000 balance.
   - V2 models define `final double? balance;` which strictly defaults to `null`.
   - `QuantMetric` and `QuantFormatters` strictly render `—` for null values without exception.
2. **Missing Indicators**:
   - PnL, percentages, margins, and liquidation prices without authoritative verification render `—`.
