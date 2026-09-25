# 03 — FLUTTER iOS V2 END-TO-END VERIFICATION

## 1. Architecture & Navigation

The Flutter iOS application replaces obsolete mobile views with the 4-tab Obsidian Quants layout:
- **`OverviewTab`**: Telemetry metrics, PnL indicators, capital safety cards.
- **`PositionsTab`**: Read-only position cards, margin mode indicators, zero manual trade actions.
- **`RiskTab`**: Active circuit breaker telemetry, CAS generation inspection, HALT and RESUME buttons.
- **`SystemTab`**: Institutional certification matrix, execution core verification, governance claims.

## 2. Server URL Security Verification

Tested via `ios-app/test/ui_v2_phase5_rc_test.dart`:
- Default production target: `https://trader.noza.site`.
- `validateServerUrl` enforces:
  - Protocol must be `https://` (plain `http://` rejected).
  - Internal execution IPC port `50051` rejected (`'Không được phép trỏ trực tiếp vào cổng nội bộ IPC (50051)'`).
  - Direct Binance host names (`binance.com`, `binancefuture`, `binance.vision`) rejected (`'Không được phép trỏ trực tiếp vào máy chủ sàn Binance'`).
- `saveServerUrl` throws `ArgumentError` on forbidden values.

## 3. Keychain & Token Storage Lifecycle

Tested via `ios-app/test/ui_v2_phase5_rc_test.dart`:
- Token persistence in secure iOS Keychain (`IOSOptions(accessibility: KeychainAccessibility.first_unlock)`).
- Login persists token via `saveToken`.
- App restart restores session via `getToken`.
- HTTP 401 unauthenticated response immediately clears token and triggers `onUnauthorized` callback.
- Logout clears token immediately.
- Verification: Token is NEVER logged, NEVER stored in SharedPreferences, and NEVER exposed in UI debug trees.

## 4. Polling Lifecycle & Timer Guard

Tested via `ios-app/test/ui_v2_phase5_rc_test.dart`:
- App active (foreground): status, history, logs polled at regular intervals with single in-flight lock.
- App paused (background): timers immediately paused (`isAppInBackground == true`).
- App resumed (foreground): timers resumed and immediate `refreshAll()` triggered.
- Rapid lifecycle toggling (`paused -> resumed -> paused -> resumed`) verified to NOT multiply timers.
