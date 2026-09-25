# 08 — ENVIRONMENT TRUTH EVIDENCE

## 1. Problem & Architecture

Previously, UI components hardcoded `"OFFLINE"` in badges or templates before verifying with the server.
In Phase 4, the environment badge displays truth:
1. Initial unverified state is `UNKNOWN` (grey badge).
2. The server endpoint `/api/status` returns the authoritative `"environment"` key (`"OFFLINE"`, `"TESTNET"`, or `"LIVE"`).
3. Web and Flutter dynamically update the badge upon receiving authoritative telemetry.

## 2. Web Implementation Evidence

- `web/view_models.py`: Defaults environment to `"UNKNOWN"` when absent or unverified.
- `web/templates/ui_v2/partials/telemetry_bar.html`: Renders initial badge with classes `env-unknown env-badge--unknown` and text `UNKNOWN`.
- `web/static/ui_v2/js/dashboard.js`: In `renderTelemetryBar`, updates class and text based on `status.environment`.

## 3. Flutter Implementation Evidence

- `ios-app/lib/ui_v2/widgets/environment_badge.dart`:
  - `EnvironmentBadge.fromString(null)` -> Renders `"UNKNOWN"` with `QuantColors.textMuted`.
  - `EnvironmentBadge.fromString("TESTNET")` -> Renders `"TESTNET"` with `QuantColors.gold`.
  - `EnvironmentBadge.fromString("LIVE")` -> Renders `"LIVE"` with `QuantColors.red`.
  - `EnvironmentBadge.fromString("OFFLINE")` -> Renders `"OFFLINE"` with `QuantColors.cyan`.
- Updated all screens (`home_screen.dart`, `login_screen.dart`, `overview_tab.dart`, `system_tab.dart`) to pass `status?.environment`.

Tested in `ios-app/test/ui_v2_phase4_test.dart`:
- `EnvironmentBadge renders UNKNOWN for null or empty input`: PASS
- `EnvironmentBadge renders TESTNET in gold`: PASS
- `EnvironmentBadge renders LIVE in red`: PASS
