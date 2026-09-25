# 06 — WEB V2 IMPLEMENTATION PLAN

## 1. Information Architecture & Navigation

The Web V2 operator portal is structured into a clean, institutional hierarchy with strict separation between public disclosures and the authenticated operator terminal:

```text
WEB V2 INFORMATION ARCHITECTURE
├── PUBLIC / UNAUTHENTICATED
│   ├── /                 -> Institutional System Landing & Status
│   ├── /risk-warning     -> Risk Disclosure & Safety Policies
│   ├── /privacy          -> Privacy & Data Protection Overview
│   ├── /terms            -> Terms of Service
│   └── /portal/login     -> Secure Operator Login
│
└── AUTHENTICATED PORTAL (/portal/dashboard)
    ├── TOP TELEMETRY BAR (Sticky Header)
    │   [ENVIRONMENT: OFFLINE] [EXECUTION: HEALTHY] [WEB: READY]
    │   [TELEGRAM: READY] [HALT: INACTIVE] [RECOVERY: CLEAR] [LATENCY: 22ms]
    │
    ├── VIEW: OVERVIEW   -> Primary 12-column dense terminal grid
    ├── VIEW: POSITIONS  -> Full-width dense positions table + detail drawer
    ├── VIEW: RISK       -> Dedicated Circuit Breaker & Safety Control center
    ├── VIEW: ACTIVITY   -> Chronological execution events & audit logs
    └── VIEW: SYSTEM     -> Safe read-only system telemetry & certification
```

---

## 2. Desktop Terminal Layout (>= 1440px)

The primary terminal (`/portal/dashboard` - OVERVIEW view) implements a Bloomberg-density 12-column CSS grid:

```text
┌────────────────────────────────────────────────────────────────────────┐
│ TOP TELEMETRY BAR: OFFLINE | EXEC HEALTHY | WEB READY | HALT | LATENCY │
├─────────────────┬───────────────────────────────┬──────────────────────┤
│ SYSTEM STATUS   │ PERFORMANCE / REALIZED PNL    │ RISK / BREAKER       │
│ (3 cols)        │ (6 cols)                      │ (3 cols)             │
│ • Execution Svc │ • Realized PnL (JetBrains)    │ • Breaker: HEALTHY   │
│ • Web & IPC     │ • Win Rate & Total Trades     │ • Cooldown: INACTIVE │
│ • Database      │ • Daily PnL vs Limit          │ • Streak: 0 losses   │
├─────────────────┴───────────────────────────────┼──────────────────────┤
│ ACTIVE POSITIONS TABLE (8 cols)                 │ PROTECTION (4 cols)  │
│ Symbol | Side | Qty | Entry | Mark | PnL | SL/TP │ • Stop-Loss Coverage │
│ (JetBrains Mono numbers, green/red PnL)         │ • Take-Profit State  │
├─────────────────────────────────────────────────┴──────────────────────┤
│ RECENT EXECUTION & SAFETY ACTIVITY (12 cols)                           │
│ Timestamp | Component | Severity | Symbol | Action | Result            │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Responsive Breakpoints

| Breakpoint | Layout Strategy |
| :--- | :--- |
| **>= 1440px** | Dense 12-column multi-pane terminal. All panels visible simultaneously. Minimal 8px panel gap. |
| **1024px – 1439px** | 2-column layout; secondary panels (System Status / Protection) collapsed into tabbed containers. |
| **< 1024px (Mobile)**| Single-column mobile operator layout. Position table adapts to touch-friendly cards. Sticky top telemetry bar remains visible. |

---

## 4. Web V2 Component Library (`web/static/`)

The following shared visual primitives will be constructed in Phase 1:

1. **`TerminalPanel`**: High-density container with surface elevation (`#122131`), 1px subtle border (`#1C2E42`), 4px border radius, and compact 8px padding.
2. **`MetricCard`**: Displays label in Inter uppercase (`#849495`) and value in tabular JetBrains Mono (`#D4E4FA`). Supports data update flash.
3. **`TelemetryBadge`**: Micro status pill (2px radius) with semantic color mapping (`OFFLINE` cyan, `HEALTHY` green, `HALTED` red).
4. **`StatusBadge`**: Pill indicator for position sides (`LONG` green, `SHORT` red) and order states.
5. **`DenseTable`**: Compact data table with sticky header, 1px row borders, tabular numeric alignments, and row click drawer trigger.
6. **`SectionHeader`**: Institutional panel header with title, subtitle, and action slot.
7. **`RiskAlert`**: Prominent safety banner displaying active HALT reasons or recovery alerts.
8. **`EmptyState`**: Stoic, non-decorative empty placeholder (`"Không có vị thế đang mở"`, `"Chưa có dữ liệu giao dịch"`).
9. **`LoadingSkeleton`**: Minimalist dark pulse skeleton replacing spinner clutter.
10. **`ConfirmDialog`**: Modal dialog for operator mutations (HALT, generation-bound RESUME, emergency close) with explicit risk warnings.
11. **`EnvironmentBadge`**: Prominent, persistent badge indicating `OFFLINE` environment mode.

---

## 5. Asset Self-Hosting Architecture

To eliminate all external CDN dependencies (Tailwind CDN, FontAwesome, Google Fonts, Chart.js):
- **Local CSS**: Pre-compiled CSS file (`web/static/css/obsidian_quants.css`) containing all color tokens, typography rules, layout utilities, and component styles.
- **Local Fonts**: Self-hosted WOFF2 font files for `Inter` and `JetBrains Mono` placed in `web/static/fonts/` and declared via `@font-face` with `font-display: swap;`.
- **Local Icons**: Lightweight inline SVG icons embedded directly into components, eliminating FontAwesome CDN requests.
- **Local Charts**: Lightweight SVG/Canvas sparklines and equity curve renderer, eliminating Chart.js CDN.
