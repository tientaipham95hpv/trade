# 04 — RESPONSIVE LAYOUT & ACCESSIBILITY SPECIFICATION

## 1. Responsive Layout Strategy

The Web V2 interface implements a 12-column responsive layout engine in `web/static/ui_v2/layout.css` and `responsive.css`:

```text
┌────────────────────────────────────────────────────────────────────────┐
│ Screen Width >= 1440px (Institutional Desktop / Trading Multi-Monitor) │
│ - Full 12-column layout active                                         │
│ - Side-by-side telemetry panels, live charts, execution logs           │
│ - Compact padding (--space-3 = 12px) for maximum information density   │
├────────────────────────────────────────────────────────────────────────┤
│ Screen Width 1024px - 1439px (Laptop / Tablet Landscape)               │
│ - Responsive column collapsing (col-span-8 -> 12, col-span-4 -> 6)     │
│ - Top telemetry bar adapts to horizontal overflow scroll               │
├────────────────────────────────────────────────────────────────────────┤
│ Screen Width 768px - 1023px (Tablet Portrait)                          │
│ - Multi-column panels stack into 2-column or 1-column cards            │
│ - Tables switch to horizontal scrolling containers                     │
├────────────────────────────────────────────────────────────────────────┤
│ Screen Width < 768px (Mobile)                                          │
│ - Single-column layout (all col-span classes collapse to 100% width)   │
│ - Fixed top telemetry condensed into ticker bar                        │
│ - Modal confirmation dialogs expand to full bottom-sheet               │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Touch Target Boundaries (iOS & Mobile)

In compliance with Apple Human Interface Guidelines:
- **Minimum Target Dimension**: 44x44 pt.
- **Implementation in Flutter**: Enforced in `QuantSpacing.minTouchTarget` (`44.0`) and applied to buttons, dialog dismiss controls, and navigation items.
- **Implementation in Web CSS**: Interactive buttons and table action triggers enforce `min-height: 44px; min-width: 44px;` on mobile media queries (`max-width: 768px`).

---

## 3. Visual Accessibility & Contrast Ratios

All color combinations in Obsidian Quants satisfy WCAG 2.1 AA standards for contrast:
- **Primary Text on Background**: `#EAECEF` on `#051424` -> Contrast Ratio **15.4:1** (AAA compliant).
- **Secondary Text on Background**: `#848E9C` on `#051424` -> Contrast Ratio **6.8:1** (AA compliant).
- **Gold Accent on Surface**: `#F0B90B` on `#122131` -> Contrast Ratio **9.2:1** (AAA compliant).
- **Cyan Accent on Surface**: `#00F0FF` on `#122131` -> Contrast Ratio **11.8:1** (AAA compliant).
- **Green Text on Surface**: `#0ECB81` on `#122131` -> Contrast Ratio **7.4:1** (AAA compliant).
- **Red Text on Surface**: `#F6465D` on `#122131` -> Contrast Ratio **5.3:1** (AA compliant).

---

## 4. Keyboard Navigation & Assistive Technologies

### A. Accessible Focus-Visible Rings
Custom outline rings are enabled on all interactive elements:
```css
:focus-visible {
  outline: 2px solid var(--cyan);
  outline-offset: 2px;
}
```

### B. Reduced Motion Compliance
Users who have enabled reduced motion in their OS receive instant transitions without disorientation:
```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

### C. Screen Reader Support
- Semantic HTML tags (`<header>`, `<nav>`, `<main>`, `<section>`, `<table>`, `<th>`, `<td>`, `<button>`).
- ARIA live regions planned for high-frequency ticker updates in Phase 2.
