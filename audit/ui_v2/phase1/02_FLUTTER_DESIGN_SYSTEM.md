# 02 — FLUTTER DESIGN SYSTEM SPECIFICATION (FLUTTER iOS V2)

## 1. Architectural Overview

The Flutter iOS V2 Design System is located in `ios-app/lib/ui_v2/`. It provides a native Flutter implementation of the Obsidian Quants design tokens, widgets, and themes, tailored specifically for high-density mobile trading interfaces on iOS:

```text
ios-app/lib/ui_v2/
├── theme/
│   ├── quant_colors.dart         # Canonical Obsidian Quants color constants
│   ├── quant_spacing.dart        # 4px grid spacing, radii, touch target dimensions
│   ├── quant_typography.dart     # Tabular mono and sans text styles
│   └── quant_theme.dart          # Master dark ThemeData definition
└── widgets/
    ├── environment_badge.dart    # OFFLINE, TESTNET, LIVE environment indicators
    ├── quant_confirm_sheet.dart  # Technical confirmation bottom sheet (CAS preview)
    ├── quant_empty_state.dart    # Institutional empty state placeholder
    ├── quant_loading.dart        # Monospace loading and skeleton widgets
    ├── quant_metric.dart         # Compact metric card with null safety & tabular figures
    ├── quant_panel.dart          # Technical container with header, subtitle, actions
    ├── quant_risk_banner.dart    # Severity banners (info, warning, critical, halt)
    ├── quant_section_header.dart # Section dividers with metadata and chips
    └── quant_status_badge.dart   # Semantic status pills with pulsing dot
```

---

## 2. Core Token Definitions

### A. Color System (`quant_colors.dart`)
```dart
class QuantColors {
  static const Color background = Color(0xFF051424);
  static const Color surface = Color(0xFF122131);
  static const Color surfaceRaised = Color(0xFF1A2D42);
  static const Color surfaceSunken = Color(0xFF081A2C);
  
  static const Color gold = Color(0xFFF0B90B);
  static const Color cyan = Color(0xFF00F0FF);
  static const Color green = Color(0xFF0ECB81);
  static const Color red = Color(0xFFF6465D);
  
  static const Color border = Color(0x14FFFFFF);       // 8% white
  static const Color borderActive = Color(0x4000F0FF); // 25% cyan
  
  static const Color textPrimary = Color(0xFFEAECEF);
  static const Color textSecondary = Color(0xFF848E9C);
  static const Color textDim = Color(0xFF474D57);
}
```

### B. Spacing & Touch Boundaries (`quant_spacing.dart`)
In strict adherence to iOS Human Interface Guidelines and quant density requirements:
- `minTouchTarget`: `44.0 pt` minimum height and width for all tappable controls.
- `radiusSm`: `4.0 pt`, `radiusMd`: `6.0 pt`, `radiusLg`: `8.0 pt`.
- Spacing constants: `xs` (4pt), `sm` (8pt), `md` (12pt), `lg` (16pt), `xl` (20pt), `xxl` (24pt).

### C. Typography & Numerical Stability (`quant_typography.dart`)
Every financial figure uses tabular numerals via `FontFeature.tabularFigures()` and `FontFeature.liningFigures()` to guarantee zero horizontal jitter during continuous real-time data streaming:
```dart
static const TextStyle displayMetric = TextStyle(
  fontFamily: 'Courier',
  fontFeatures: [FontFeature.tabularFigures(), FontFeature.liningFigures()],
  fontSize: 24,
  fontWeight: FontWeight.w700,
  color: QuantColors.textPrimary,
);
```

---

## 3. Reusable Widget Suite

1. **`QuantPanel`**: Standard institutional card supporting optional header title, subtitle, trailing action, footer, and a busy/loading overlay.
2. **`QuantMetric`**: Financial metric card supporting positive/negative color-coded deltas, units, captions, and null safety (gracefully displaying `—` when data is absent).
3. **`EnvironmentBadge`**: Strict environment indicator. Automatically displays `OFFLINE` (Cyan), `TESTNET` (Gold), or `LIVE` (Red).
4. **`QuantStatusBadge`**: Status indicator with colored dot and label for service health, engine state, and breaker indicators.
5. **`QuantSectionHeader`**: Clean typographic section divider supporting status chips and action buttons.
6. **`QuantRiskBanner`**: Prominent callout widget for Breaker Tripped, Risk Warnings, or Emergency Halt states.
7. **`QuantEmptyState`**: Stoic, minimalist empty state showing icon, title, description, and action button.
8. **`QuantLoading` / `QuantSkeleton`**: Monospace pulsing indicator and shimmer skeleton for asynchronous telemetry loads.
9. **`QuantConfirmSheet`**: Modal bottom sheet designed for high-risk operations (e.g. breaker reset, emergency halt), presenting a CAS generation preview and required confirmation toggle.

---

## 4. Theme Integration (`quant_theme.dart`)

The `QuantTheme.darkTheme` integrates cleanly into `MaterialApp`:
```dart
MaterialApp(
  theme: QuantTheme.darkTheme,
  // ...
);
```
It configures dark scaffold backgrounds, custom dark `CardTheme`, `AppBarTheme` with 0 elevation and border separator, `DialogTheme`, and institutional button styles.
