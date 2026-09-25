# AUDIT REPORT — PHASE 6C: OBSIDIAN QUANTS DESIGN SYSTEM V3

## 1. Restrained Institutional Color Palette
Obsidian Quants V3 replaces bright cyberpunk hues with a restrained, institutional palette designed for long trading sessions with zero eye fatigue.

| Token | Hex Value | Semantic Usage | Web CSS Var | Flutter QuantColors |
| :--- | :--- | :--- | :--- | :--- |
| **Background** | `#070B12` | Root shell viewport | `--bg` | `QuantColors.background` |
| **Primary Surface** | `#0D111A` | Main panels, terminal body | `--surface` | `QuantColors.surface` |
| **Secondary Surface** | `#121824` | Table hover, metric strips | `--surface-high` | `QuantColors.surfaceHigh` |
| **Elevated Surface** | `#171E2B` | Active nav items, tooltips | `--surface-elevated` | `QuantColors.surfaceElevated` |
| **Border** | `#202938` | Container boundaries | `--border` | `QuantColors.border` |
| **Border Subtle** | `rgba(255,255,255,0.06)` | Table row dividers | `--border-subtle` | `QuantColors.borderSubtle` |
| **Text Primary** | `#E8EDF5` | Primary readings, headers | `--text-primary` | `QuantColors.textPrimary` |
| **Text Secondary** | `#95A1B2` | Subtitles, labels | `--text-secondary` | `QuantColors.textSecondary` |
| **Text Muted** | `#5E6A7D` | Timestamps, empty indicators | `--text-muted` | `QuantColors.textMuted` |
| **Accent Cyan** | `#3DD9EB` | Active indicator (<= 10%) | `--accent-cyan` | `QuantColors.cyan` |
| **Positive** | `#18C784` | Profit, healthy state | `--positive` | `QuantColors.green` |
| **Negative** | `#F0445E` | Loss, critical state | `--negative` | `QuantColors.red` |
| **Warning** | `#F3BA2F` | Degraded, cooldown | `--warning` | `QuantColors.gold` |
| **Critical** | `#FF5C68` | Fail-closed HALT | `--critical` | `QuantColors.critical` |

---

## 2. Strict Accent Usage Rule (<= 10% Visual Surface)
1. **Neutral Background Dominance**: Neutral dark surfaces (`#070B12`, `#0D111A`, `#121824`) occupy > 85% of visual real estate.
2. **Cyan Usage**: Used strictly for active sidebar border tab indicator, environment pill, and IPC latency badge. Cyan borders on ordinary panels have been eliminated.
3. **Green & Red Semantic Discipline**: Never used for decorative purposes; exclusively used for financial delta signs (positive/negative) and authoritative circuit breaker states.

---

## 3. Typographic Hierarchy & Numeric Alignment
- **Page Titles**: 20–22px, font-weight 600, letter-spacing -0.02em.
- **Section Titles**: 12–13px, font-weight 700, uppercase tracked 0.04em.
- **Body Text**: 12–13px, regular, color `#95A1B2`.
- **Dense Table Font**: 12px, tabular monospace, height 36–40px.
- **Metrics Display**: 18–22px, tabular monospace numbers with `font-variant-numeric: tabular-nums` and zero slashed zeroes (`"tnum" 1, "zero" 1`).

---

## 4. Spacing Scale & Border Radii
- **Baseline Scale**: 4px, 6px, 8px, 12px, 16px, 24px (32px/48px gaps eliminated).
- **Border Radii**: 2px (`--radius-micro`), 4px (`--radius-default`), 6px (`--radius-container`), strictly capped at 8px (`--radius-max`).
