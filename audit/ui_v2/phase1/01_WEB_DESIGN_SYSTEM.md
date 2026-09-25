# 01 — WEB DESIGN SYSTEM SPECIFICATION (WEB V2)

## 1. Architectural Overview

The Web V2 Design System brings institutional quant density and dark-mode elegance to the web interface. Located in `web/static/ui_v2/`, it is structured into modular CSS files with zero runtime framework dependencies:

```text
web/static/ui_v2/
├── tokens.css             # Color palette, typography scale, spacing, radii, z-indices
├── base.css               # Box-sizing, resets, tabular numbers, dark scrollbars, focus rings
├── layout.css             # Bloomberg-density grid (12-column), header, telemetry bar, viewports
├── components.css         # 11 reusable institutional trading terminal primitives
├── responsive.css         # Breakpoint rules (desktop 1440+, tablet 1024-1439, mobile <1024)
└── obsidian_quants.css    # Master bundle importing all modules
```

---

## 2. Design Tokens (`tokens.css`)

### A. Color Palette
The color tokens match the Obsidian Quants / Binance Quant Pro specification:

| Token Name | Hex Value | Usage / Semantic Role |
|---|---|---|
| `--bg` | `#051424` | Deep Navy Canvas (Application Background) |
| `--surface` | `#122131` | Panel and Card Surfaces |
| `--surface-raised` | `#1a2d42` | Elevated Modals, Dropdowns, Tooltips |
| `--surface-sunken` | `#081a2c` | Sunken Wells, Table Headers, Inset Displays |
| `--gold` | `#F0B90B` | Binance Gold Accent, Warnings, Standby States |
| `--gold-glow` | `rgba(240, 185, 11, 0.15)` | Gold Focus and Elevation Glow |
| `--cyan` | `#00F0FF` | High-Tech Telemetry Accent, OFFLINE Mode Indicator |
| `--green` | `#0ECB81` | Quant Profit, Active/Healthy State, Buy Indicators |
| `--red` | `#F6465D` | Quant Loss, Critical Breaker Tripped, Sell Indicators |
| `--border` | `rgba(255, 255, 255, 0.08)`| Subtle Structural Separators |
| `--border-active` | `rgba(0, 240, 255, 0.25)` | Active Panel or Selected Card Borders |
| `--text-primary` | `#EAECEF` | Primary Numerical Values & Headings |
| `--text-secondary` | `#848E9C` | Labels, Metric Captions, Muted Metadata |
| `--text-dim` | `#474D57` | Inactive Toggles, Watermarks, Sub-metadata |

### B. Typography & Font Stacks
To eliminate external runtime dependencies and prevent layout shifts during offline operation, the font stack leverages local institutional and system typefaces:

- **Monospace (Numbers, Code, Feeds)**:
  `'JetBrains Mono', 'SF Mono', 'Fira Code', 'Roboto Mono', 'Cascadia Code', monospace`
- **Sans-Serif (Labels, Headers, Structural Text)**:
  `'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`

### C. Tabular Figures
Financial figures, PnL displays, timestamps, and order books must never jitter when numbers update. Tabular figures are universally applied via:
```css
font-variant-numeric: tabular-nums lining-nums;
font-feature-settings: "tnum" 1, "zero" 1;
```

### D. Spacing & Density
Built on a compact 4px quantum grid:
- `--space-1`: `4px`
- `--space-2`: `8px`
- `--space-3`: `12px`
- `--space-4`: `16px`
- `--space-5`: `20px`
- `--space-6`: `24px`
- `--space-8`: `32px`

---

## 3. Layout Architecture (`layout.css`)

### A. Terminal Shell Structure
```text
┌────────────────────────────────────────────────────────────────────────┐
│  Top Telemetry Bar (32px height, cyan/gold indicators, latency, clock) │
├────────────────────────────────────────────────────────────────────────┤
│  Terminal Nav Bar (48px height, environment badge, operator, status)   │
├────────────────────────────────────────────────────────────────────────┤
│  Terminal Viewport (Full height scrollable container)                  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ 12-Column Responsive Grid (col-span-1 through col-span-12)       │  │
│  │                                                                  │  │
│  │ [ Panel 1: 4 cols ] [ Panel 2: 4 cols ] [ Panel 3: 4 cols ]      │  │
│  │ [ Panel 4: 8 cols               ] [ Panel 5: 4 cols             ]│  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Reusable Component Primitives (`components.css`)

1. **TerminalPanel (`.terminal-panel`)**: Container with surface background, subtle 1px border, header with title and action controls, body, and optional footer.
2. **MetricCard (`.metric-card`)**: Financial metric display featuring label, primary value in tabular mono, delta change badge, and secondary caption.
3. **TelemetryItem (`.telemetry-item`)**: Compact key-value unit designed for top telemetry bar.
4. **EnvironmentBadge (`.env-badge`)**: High-visibility pill indicating runtime environment:
   - `.env-badge--offline`: Cyan glowing badge for OFFLINE mode.
   - `.env-badge--testnet`: Gold badge for Binance Testnet.
   - `.env-badge--live`: Red alert badge for Binance Live Production.
5. **StatusBadge (`.status-badge`)**: Dot + text pill for health (`--healthy`), degraded (`--degraded`), halt (`--halt`), and error (`--error`).
6. **DenseTable (`.dense-table`)**: Tabular data grid with sticky sunken headers, monospace numeric columns right-aligned, and hover row highlighting.
7. **RiskAlert (`.risk-alert`)**: Alert banners with severity levels (`info`, `warning`, `critical`, `halt`).
8. **EmptyState (`.empty-state`)**: Institutional placeholder for empty tables or missing telemetry.
9. **LoadingSkeleton (`.skeleton`)**: Shimmer animation for loading states.
10. **ConfirmDialog (`.confirm-dialog`)**: Technical confirmation modal with explicit action summary, CAS generation validation preview, and destructive confirmation styling.
11. **SectionHeader (`.section-header`)**: Clean section dividing element with category title, subtitle, and right-aligned status chip.
