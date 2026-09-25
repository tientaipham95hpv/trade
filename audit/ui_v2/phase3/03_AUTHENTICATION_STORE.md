# 03 — AUTHENTICATION & SECURE STORE

## 1. Storage Architecture

In Phase 3, session credentials migrated from plaintext/volatile memory to hardware-backed secure storage:

- **Target Platform**: iOS Keychain via `flutter_secure_storage` (^11.2.0).
- **Accessibility Level**: `KeychainAccessibility.first_unlock` (securely available after initial device unlock).
- **Fallback Mechanism**: In-memory map fallback for automated test environments where Keychain platform channels are not registered.

---

## 2. Token Lifecycle

1. **App Launch**:
   - `AuthStore.hasToken()` inspects the Keychain for existing token `quant_session_token`.
   - If present, `QuantApiClient.checkAuth()` queries `GET /api/check_auth` with `X-Session-Token`.
   - If response contains `{"authenticated": true}`, app mounts `QuantHomeScreen`.
   - If unauthenticated or token missing, app mounts `LoginScreen`.
2. **Operator Login**:
   - `QuantApiClient.login(username, password)` sends `POST /api/login`.
   - On HTTP 200 with `{success: true, token: ...}`, token is saved to Keychain via `AuthStore.saveToken()`.
   - App transitions immediately to `QuantHomeScreen`.
   - On HTTP 401: structured `QuantApiException` with message displayed in red alert banner.
   - On HTTP 429: rate limiting alert displayed.
3. **Operator Logout**:
   - `QuantApiClient.logout()` invokes `POST /api/logout` to revoke session server-side.
   - Calls `AuthStore.clearToken()` to erase token from Keychain.
   - App redirects immediately to `LoginScreen`.
4. **Automatic 401 Session Expiry Handling**:
   - Whenever any polling query (`/api/status`, `/api/history`, `/api/logs`) receives HTTP 401:
     - `AuthStore.clearToken()` deletes the token from Keychain.
     - `onUnauthorized` callback is invoked.
     - App transitions safely to `LoginScreen` without crashing or looping.
