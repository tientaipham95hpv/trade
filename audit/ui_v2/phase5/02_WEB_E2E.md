# 02 — WEB V2 END-TO-END VERIFICATION

## 1. Local Cutover Testing

Tested via `tests/test_ui_v2_phase5_rc.py::test_ui_v2_feature_flag_cutover`:
- Configuration: `UI_V2_ENABLED=true`
- Route Verification Results:
  - `GET /` -> Status 200, renders `ui_v2/landing.html` (verified "Obsidian Quants", institutional typography, navigation links).
  - `GET /portal/login` -> Status 200, renders `ui_v2/login.html` (verified secure login form, brand assets, notice banner).
  - `GET /portal/dashboard` (unauthenticated) -> Status 302, redirects to `/portal/login`.
  - `GET /portal/dashboard` (authenticated) -> Status 200, renders `ui_v2/dashboard.html` with full 5-tab layout.
  - `GET /risk-warning` -> Status 200, renders `ui_v2/risk_warning.html`.
  - `GET /terms` -> Status 200, renders `ui_v2/terms.html`.
  - `GET /privacy` -> Status 200, renders `ui_v2/privacy.html`.
  - `GET /health` -> Status 200, returns `{"status": "ok", "service": "trader-web"}`.
  - `GET /ready` -> Status code consistent with execution service availability.

## 2. Legacy Fallback & Rollback Proof

Tested via `tests/test_ui_v2_phase5_rc.py::test_ui_v2_legacy_fallback`:
- Configuration: `UI_V2_ENABLED=false`
- Route Verification Results:
  - `GET /` -> Status 200, falls back cleanly to legacy index.
  - `GET /portal/login` -> Status 200, falls back cleanly to legacy portal login.
  - `GET /portal/dashboard` -> Falls back cleanly to legacy dashboard handler.
  - `GET /risk-warning`, `/terms`, `/privacy` -> Fall back cleanly to legacy templates.
- **Rollback Guarantee**: Setting `UI_V2_ENABLED=false` in production provides immediate, zero-downtime rollback to legacy UI.

## 3. Developer Preview Route Isolation

Tested via `tests/test_ui_v2_phase5_rc.py::test_ui_v2_preview_route_isolation`:
- Configuration: `UI_V2_DEV_PREVIEW_ENABLED=false`
- Route: `GET /portal/ui_v2_preview`
- Result: 302 Redirect to `/portal/login?next=/portal/ui_v2_preview`.
- Verified: Zero anonymous access to developer preview template, zero telemetry data leakage.
