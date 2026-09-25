# 10 — SECURITY & AUTHORITY AUDIT REVIEW

## 1. Security Baseline & Header Compliance

Web V2 preserves all institutional HTTP security headers configured in `web/app.py`:

```http
X-Content-Type-Options: nosniff
X-Frame-Options: SAMEORIGIN
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

### Content Security Policy (CSP)
The existing CSP permits `'self'` for script, style, image, and font sources. Because Web V2 introduces **zero external runtime CDN dependencies**, it operates in complete compliance with strict CSP requirements.

---

## 2. Authentication & Authorization Boundaries

### A. Anonymous Access Denial
- All terminal telemetry endpoints (`/api/status`, `/api/history`, `/api/logs`) require valid authentication via `verify_auth`.
- Terminal views (`/portal/dashboard-v2`, `/portal/dashboard`) redirect unauthenticated requests immediately to `/portal/login?next=...` with HTTP 302.
- Anonymous requests cannot view balances, positions, breaker status, or logs.

### B. Developer Preview Protection
- `/portal/ui_v2_preview` is protected by `client_ctx` verification unless `UI_V2_DEV_PREVIEW_ENABLED=true` is explicitly configured in developer environments.
- In production, unauthorized requests are blocked and redirected to login.

### C. Session Transport Hardening
- Authentication credentials are not exposed to client JavaScript.
- Sessions use HttpOnly SameSite cookies.
- No bearer tokens or secrets are rendered in DOM attributes.

---

## 3. Credential & Mutation Prohibitions

| Prohibited Vector | Implementation Audit Status | Evidence |
|---|---|---|
| **Binance API Keys** | **ZERO INPUTS / ZERO STORAGE** | No input fields or storage tables exist |
| **Binance API Secrets** | **ZERO INPUTS / ZERO STORAGE** | Permanently purged |
| **Client Trading Authority** | **FAIL-CLOSED (HTTP 503)** | All 6 obsolete APIs return `FEATURE_DISABLED` |
| **Direct Exchange Calls** | **ZERO (PROHIBITED)** | Web process has no direct Binance connection |
| **Direct DB Order Writes** | **ZERO (PROHIBITED)** | SQLite orders table modified by Service PID only |
| **Manual Trade Buttons** | **ZERO CONTROLS** | No BUY/SELL/MODIFY buttons in Web V2 |
| **Copy-Trade Controls** | **DISABLED** | Copy-trade features remain inactive |
| **Environment Switcher** | **READ-ONLY DISPLAY** | Environment fixed to `OFFLINE` by service truth |
