# 10 — LEGACY AUDIT & CODE CLEANSING

## 1. Zero Fake Values Audit

1. **Balance Sanitization**:
   - `ios-app/lib/models/models.dart` line 91 was modified to eliminate `safeParseDouble(json['balance'], 1000.0)` -> `safeParseDouble(json['balance'], 0.0)`.
   - V2 models (`SystemStatus`, `PositionView`) strictly define nullable fields (`double? balance`), which default to `null` and render as `—`.
2. **Elimination of Fallbacks**:
   - Zero hardcoded fallback balances ($1000.00, $500.00, etc.) exist in the active runtime.

---

## 2. Unreachable Legacy Screen Isolation

1. **Scanner Tab (`screens/scanner_tab.dart`)**:
   - Zero imports in active V2 runtime.
   - Zero bottom navigation or drawer links.
2. **AI Copilot Tab (`screens/ai_copilot_tab.dart`)**:
   - Zero imports in active V2 runtime.
   - Zero navigation paths.
3. **Legacy History Tab (`screens/history_tab.dart`)**:
   - Retired from bottom navigation.
   - Closed trade history and live logs now handled by V2 models and screens.
4. **Settings Dialog (`screens/settings_dialog.dart`)**:
   - Retired from active view hierarchy.
   - Session settings and logout consolidated into V2 `SystemTab`.
