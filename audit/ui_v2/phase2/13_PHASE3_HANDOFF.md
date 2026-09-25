# 13 — PHASE 3 HANDOFF & IMPLEMENTATION READINESS

## 1. Readiness Assessment

Phase 2 (Web V2 — Obsidian Quants Operator Terminal) is **COMPLETE and CERTIFIED**. All deliverables, template modules, client-side JavaScript controllers, security headers, feature flag mechanisms, and core checksum verifications have been validated.

The repository is fully ready for **UI Phase 3: Flutter iOS V2 Implementation & Navigation Pruning**.

---

## 2. Phase 3 Scope & Objectives

In Phase 3, the mobile iOS application will be updated to match the Obsidian Quants design language and authoritative backend boundaries:

1. **Flutter Navigation Pruning**:
   - Safely deprecate and remove obsolete tabs (`ScannerTab`, `AiCopilotTab`).
   - Remove obsolete API credential input screens.
   - Refactor bottom navigation to institutional views: `Overview`, `Positions`, `Risk`, `System`.

2. **Keychain Authentication Migration**:
   - Replace insecure `SharedPreferences` token storage with `flutter_secure_storage` (iOS Keychain).
   - Enforce biometric / secure enclave session protection where available.

3. **Flutter V2 Screen Implementations**:
   - Rebuild screens using Phase 1 widgets (`QuantPanel`, `QuantMetric`, `EnvironmentBadge`, `QuantStatusBadge`, `QuantSectionHeader`, `QuantRiskBanner`, `QuantConfirmSheet`).
   - Eliminate hardcoded fake defaults (e.g. `$1000` fallback balance) in `api_service.dart` and UI controllers, ensuring unproven fields display `—`.

---

## 3. Explicitly Tracked Risk Register

As mandated by institutional review guidelines, the following architectural risks remain actively tracked:

1. **Legacy 5,470-Line Inline Dashboard in `web/app.py`**:
   - *Status*: Preserved behind `is_ui_v2_enabled() == False` to guarantee zero VPS deployment risk.
   - *Mitigation Plan*: Surgical removal scheduled for Phase 6 after VPS burn-in.

2. **Duplicate Legacy / Template Dashboard Implementation**:
   - *Status*: `templates/dashboard.html` remains active for legacy customers.
   - *Mitigation Plan*: Consolidated cutover scheduled for Phase 6.

3. **Authoritative Semantics of Performance Metrics**:
   - *Status*: `ClientOrderLog` is unauthoritative for Win Rate, Trade Count, and Max Drawdown.
   - *Mitigation Plan*: These fields are rendered as `—` ("Authoritative metric unavailable") in Web V2 and must be rendered identically in Flutter V2.

4. **`/api/resume` CAS Generation Contract**:
   - *Status*: Current Web `/api/resume` fetches the halt generation server-side before issuing `CommandType.RESUME`.
   - *Mitigation Plan*: Verified stable; interactive UI wiring deferred to Phase 4.

5. **Developer Preview Route Exposure**:
   - *Status*: Hardened in Phase 2 with mandatory authentication and `is_ui_v2_preview_enabled()` gate.
   - *Mitigation Plan*: Fully resolved at application layer.

6. **Legacy UI External CDN Dependencies**:
   - *Status*: Legacy templates still reference external CDNs.
   - *Mitigation Plan*: Web V2 operates with zero runtime CDNs; legacy files to be deleted in Phase 6.

7. **Existing Flutter Fake-Value Debt**:
   - *Status*: Legacy Flutter screens in `ios-app/lib/screens/` still contain fallback defaults.
   - *Mitigation Plan*: Explicitly scheduled for refactoring and elimination in Phase 3.
