# 04 — AUTHENTICATION & RBAC END-TO-END VERIFICATION

## 1. Authentication Spectrum Testing

Tested via `tests/test_ui_v2_phase5_rc.py::test_auth_e2e_rbac_and_mutation_isolation`:

| Caller Identity | Request Type | Target Endpoint | Expected Result | Verified Result |
|---|---|---|---|---|
| Anonymous | Query | `/api/status` | 401 Unauthorized | 401 Unauthorized |
| Anonymous | Query | `/api/history` | 401 Unauthorized | 401 Unauthorized |
| Anonymous | Mutation | `/api/pause` | 401 Unauthorized | 401 Unauthorized |
| Anonymous | Mutation | `/api/resume` | 401 Unauthorized | 401 Unauthorized |
| Invalid Credentials | Auth | `/api/login` | 401 Unauthorized | 401 Unauthorized (No token issued) |
| Valid Admin | Auth | `/api/login` | 200 OK | 200 OK (JWT issued) |
| Valid Admin | Mutation | `/api/pause` | 200 OK | 200 OK (HALT confirmed) |
| Valid Admin | Mutation | `/api/resume` | 200 OK / 409 CAS | Evaluated by CAS logic |
| Client Role (`client`) | Query | `/api/status` | 200 OK | 200 OK (Read-only data) |
| Client Role (`client`) | Mutation | `/api/pause` | 403 Forbidden | 403 Forbidden ("Bạn không có quyền thực hiện thao tác này.") |
| Client Role (`client`) | Mutation | `/api/resume` | 403 Forbidden | 403 Forbidden ("Bạn không có quyền thực hiện thao tác này.") |

## 2. Session Invalidation & Expiry

- **Web Portal**:
  - Browser sessions use HTTP-only, `SameSite=Lax` cookies.
  - Logging out immediately expires the session cookie with `max-age=0`.
  - Stale session tokens or revoked tokens fail closed with HTTP 401, redirecting to `/portal/login`.
- **Flutter iOS**:
  - Unauthenticated 401 triggers `onUnauthorized()` which resets `hasToken = false`, clears Keychain, and redirects navigation stack to `LoginScreen`.
  - Zero retry storm upon 401.
