# 02 — ROUTE, AUTHENTICATION & ACCESS CONTROL MAP

## 1. Route Mapping & Feature Flag Matrix

All V2 web surfaces are integrated into `web/app.py` under the governance of the `UI_V2_ENABLED` application-layer feature flag:

| Route Path | HTTP Method | Auth Requirement | Behavior when `UI_V2_ENABLED = False` (Default) | Behavior when `UI_V2_ENABLED = True` |
|---|---|---|---|---|
| `/` | `GET` | Public (Cookie Check) | Admin session -> `dashboard_page()`; Anon -> `templates/index.html` | Admin session -> Redirect `/portal/dashboard`; Anon -> `ui_v2/landing.html` |
| `/portal/dashboard` | `GET` | Authenticated | Legacy `templates/dashboard.html` | V2 Operator Terminal `ui_v2/dashboard.html` |
| `/portal/dashboard-v2` | `GET` | Authenticated | **Always V2 Operator Terminal** `ui_v2/dashboard.html` | V2 Operator Terminal `ui_v2/dashboard.html` |
| `/portal/login` | `GET` | Public (Redirects if auth) | Legacy `templates/login.html` | V2 Login `ui_v2/login.html` |
| `/portal/login-v2` | `GET` | Public (Redirects if auth) | **Always V2 Login** `ui_v2/login.html` | V2 Login `ui_v2/login.html` |
| `/portal/ui_v2_preview` | `GET` | **Authenticated OR Dev Gate** | Component Preview (Protected) | Component Preview (Protected) |
| `/risk-warning` | `GET` | Public | Legacy `templates/risk_warning.html` | V2 Restyled `ui_v2/risk_warning.html` |
| `/terms` | `GET` | Public | Legacy `templates/terms.html` | V2 Restyled `ui_v2/terms.html` |
| `/privacy` | `GET` | Public | Legacy `templates/privacy.html` | V2 Restyled `ui_v2/privacy.html` |
| `/api/status` | `GET` | Authenticated (`verify_auth`) | Authoritative status projection | Authoritative status projection |
| `/portal/api-settings` | `GET`/`POST` | Authenticated (`verify_auth`) | `FEATURE_DISABLED` (HTTP 503) | `FEATURE_DISABLED` (HTTP 503) |

---

## 2. Hardening of `/portal/ui_v2_preview`

During the Phase 1 audit, `/portal/ui_v2_preview` was flagged as a potential anonymous information leak if deployed to production.

In Phase 2, the route was hardened at the application layer:
```python
@app.get("/portal/ui_v2_preview", response_class=HTMLResponse)
async def portal_ui_v2_preview(request: Request):
    """Developer preview showcase. Requires authentication unless UI_V2_DEV_PREVIEW_ENABLED is explicitly enabled."""
    client_ctx = get_current_client_from_request(request)
    if not client_ctx and not is_ui_v2_preview_enabled():
        return RedirectResponse(url="/portal/login?next=/portal/ui_v2_preview", status_code=302)
    p = os.path.join(os.path.dirname(__file__), "templates", "ui_v2_preview.html")
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>UI V2 Preview Not Found</h1>", status_code=404)
```

**Outcome**: Anonymous production requests are immediately redirected to `/portal/login` (HTTP 302). Zero telemetry or component structures can be leaked anonymously.

---

## 3. Session & Cookie Authentication Mechanism

- **HttpOnly Cookie**: Web authentication uses a secure `session_token` stored in an HttpOnly cookie with `SameSite=Lax`.
- **Zero Token Exposure in JS**: Browser scripts cannot access raw token strings; fetch requests automatically include credentials via `credentials: 'same-origin'`.
- **Session Validation**: Each authenticated request is validated against active in-memory sessions (`_active_sessions`) and verified against the user's password version and active status in SQLite.
- **Fail-Closed 401 Interception**: If a session expires or is revoked, the client-side `ApiClient` immediately catches HTTP 401 and navigates to `/portal/login?expired=1`.
