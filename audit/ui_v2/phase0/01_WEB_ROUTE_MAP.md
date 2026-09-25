# 01 — WEB ROUTE MAP & ASSET INVENTORY

## 1. Inventory of Web Files & Templates

### Server-Side Code
- `web/app.py`: Main FastAPI application (~8,525 lines). Includes inline `dashboard_page()` HTML (~5,470 lines) and API routes.
- `web/portal.py`: HTML renderers for Client Portal login, registration, and fallback dashboard (~442 lines).
- `web/track_record.py`: Track record analytics computation and HTML renderer (~464 lines).
- `run_web.py`: Web server launcher via Uvicorn (`127.0.0.1:8088`).

### Templates Directory (`web/templates/`)
| File | Size (Bytes) | Role & Status |
| :--- | :--- | :--- |
| `index.html` | 18,675 | Institutional landing page (`GET /`). Contains legacy marketing copy and CDN links. |
| `dashboard.html` | 41,913 | Server-rendered portal dashboard (`GET /portal/dashboard`). |
| `login.html` | 11,447 | Portal login view (`GET /portal/login`). |
| `register.html` | 13,858 | Portal registration view (`GET /portal/register`). |
| `api_settings.html` | 962 | Retired credential screen (`GET /portal/api-settings`), returns safe "Feature disabled". |
| `track_record.html` | 27,249 | Historical track record audit report (`GET /track-record`). |
| `risk_warning.html` | 8,973 | Risk disclosure page (`GET /risk-warning`). |
| `privacy.html` | 8,247 | Privacy policy page (`GET /privacy`). |
| `terms.html` | 9,102 | Terms of service page (`GET /terms`). |

### Static Assets Directory (`web/static/`)
- `web/static/favicon.svg` (372 B)
- `web/static/logo.png` (734 KB)
- `web/static/css/client.css` (54.3 KB)
- `web/static/css/common.css` (7.5 KB)
- `web/static/css/portal_dashboard.css` (31.9 KB)
- `web/static/css/responsive.css` (6.9 KB)
- `web/static/images/sprites/sprite_01_pm.png` (139.3 KB)
- `web/static/images/sprites/sprite_02_risk.png` (155.6 KB)
- `web/static/js/theme.js` (1.9 KB)

---

## 2. Complete Active Web Route Map

### 2.1 Public & Unauthenticated Pages
| Route | Method | Handler | Return Type | Description |
| :--- | :--- | :--- | :--- | :--- |
| `/` | `GET` | `root_dispatch_page` | `HTMLResponse` | Landing page (`templates/index.html`) or dashboard if authenticated admin. |
| `/risk-warning` | `GET` | `risk_warning_page` | `HTMLResponse` | Institutional risk disclosure page. |
| `/terms` | `GET` | `terms_page` | `HTMLResponse` | Terms of service. |
| `/privacy` | `GET` | `privacy_page` | `HTMLResponse` | Privacy and security policies. |
| `/track-record` | `GET` | `track_record_page` | `HTMLResponse` | Public audit / track record page. |
| `/health` | `GET` | `health` | `JSONResponse` | Private tunnel liveness probe (`{"status":"ok","service":"trader-web"}`). |
| `/ready` | `GET` | `readiness` | `JSONResponse` | Operational readiness probe (`READY`, `HALTED`, `RECOVERY_REQUIRED`, or `NOT_READY`). |
| `/logo.png` | `GET` | `serve_logo` | `FileResponse` | System brand logo. |
| `/favicon.ico` | `GET` | `serve_favicon` | `FileResponse` | Favicon SVG. |
| `/manifest.json`| `GET` | `serve_manifest`| `JSONResponse` | PWA manifest. |
| `/sw.js` | `GET` | `serve_sw` | `Response` | Service worker script. |

### 2.2 Authentication Routes
| Route | Method | Handler | Auth Required | Description |
| :--- | :--- | :--- | :--- | :--- |
| `/portal/login` | `GET` | `portal_login_page` | None | Renders portal login form. |
| `/portal/login` | `POST` | `portal_login_action`| None | Form-based login; verifies password hash; sets `client_token` cookie. |
| `/portal/logout` | `GET` | `portal_logout_action`| None | Clears `client_token` cookie; redirects to login. |
| `/api/login` | `POST` | `api_login` | None | Admin API login (`{username, password}`); returns session token & sets `session_token` cookie. |
| `/api/check_auth` | `GET` | `api_check_auth` | None | Validates current session token via cookie or `X-Session-Token`. |
| `/api/logout` | `POST` | `api_logout` | None | Invalidates in-memory session and revokes portal JWT. |
| `/api/telegram_webapp_auth` | `POST` | `api_telegram_webapp_auth` | None | One-tap Telegram WebApp HMAC verification. |
| `/api/portal/login` | `POST` | `api_portal_login` | None | JSON API login for client portal; returns JWT. |
| `/api/portal/register`| `POST` | `api_portal_register` | None | Registration for new client account. |
| `/api/portal/logout`| `POST` | `api_portal_logout` | JWT | Revokes client JWT token in database. |
| `/api/portal/me` | `GET` | `api_portal_me` | JWT | Returns authenticated client profile. |

### 2.3 Authenticated Operator & Telemetry APIs (`verify_auth`)
All routes in this group require valid admin session token (via cookie `session_token`, header `X-Session-Token`, or HTTP Basic auth).

| Route | Method | Target Backend / IPC | Description |
| :--- | :--- | :--- | :--- |
| `/api/status` | `GET` | `client.query_status()`, `query_positions()`, `query_pnl()` | Master telemetry endpoint: state, halt status, generation, positions, PnL, health dimensions. |
| `/api/pause` | `POST` | `client.set_halt()` | Trigger durable HALT with operator credentials. |
| `/api/resume` | `POST` | `client.resume()` | Trigger durable RESUME via CAS halt generation. |
| `/api/toggle_pause`| `POST` | `client.set_halt()` / `client.resume()` | Toggle halt state based on current authoritative status. |
| `/api/panic_close` | `POST` | `client.emergency_close_all()` | Emergency close all positions through Execution Service. |
| `/api/close_all_positions` | `POST` | `client.emergency_close_all()` | Alias to panic close. |
| `/api/close_single`| `POST` | `client.close_position(symbol)` | Close single position by symbol through Execution Service. |
| `/api/close_position` | `POST` | `client.close_position(symbol)` | Alias supporting query parameter or JSON body. |
| `/api/history` | `GET` | Database `ClientOrderLog` | Query recent closed orders and execution history. |
| `/api/logs` | `GET` | Local log buffer | Query latest operator and execution logs. |
| `/api/radar` | `GET` | Scanner context (or empty in offline) | Top scanned market pairs (returns disabled in offline). |
| `/api/scanner_radar`| `GET` | Scanner context | Explicitly returns `DISABLED_OFFLINE` in current deployment. |
| `/api/update_settings` | `POST` | Bot context | Safe settings update (e.g. trading_mode, leverage). |
| `/api/download_csv` | `GET` | Export helper | Download trade history CSV. |
| `/api/download_state` | `GET` | State export | Download non-sensitive execution state JSON. |

### 2.4 Retired / Decommissioned Routes (Fail-Closed)
These routes are intentionally disabled and return HTTP 503 `FEATURE_DISABLED` or safe static notice:

| Route | Method | Response | Status |
| :--- | :--- | :--- | :--- |
| `/portal/api-settings` | `GET` | Static HTML | Safe "Feature disabled" page; no credential inputs. |
| `/portal/api-settings` | `POST` | HTTP 503 JSON | `{"code":"FEATURE_DISABLED","feature":"client_account_trading"}` |
| `/api/portal/api-settings` | `GET` | HTTP 503 JSON | `{"code":"FEATURE_DISABLED","feature":"client_account_trading"}` |
| `/api/portal/api-settings` | `POST` | HTTP 503 JSON | `{"code":"FEATURE_DISABLED","feature":"client_account_trading"}` |
| `/api/portal/toggle-copy` | `POST` | HTTP 503 JSON | `{"code":"FEATURE_DISABLED","feature":"client_account_trading"}` |
| `/api/portal/close-position` | `POST` | HTTP 503 JSON | `{"code":"FEATURE_DISABLED","feature":"client_account_trading"}` |
| `/api/portal/emergency-close-all` | `POST` | HTTP 503 JSON | `{"code":"FEATURE_DISABLED","feature":"client_account_trading"}` |
| `/api/portal/update-copy-settings` | `POST` | HTTP 503 JSON | `{"code":"FEATURE_DISABLED","feature":"client_account_trading"}` |
| `/api/admin/clients/{id}/toggle-copy` | `POST` | HTTP 503 JSON | `{"code":"FEATURE_DISABLED","feature":"client_account_trading"}` |

### 2.5 Obsolete Speculative / Disabled Prototype Routes
The following endpoints exist in `web/app.py` from earlier speculative features. They are either inactive, return placeholder data, or are inaccessible in offline mode:
- `/api/manual_order`: Arbitrary BUY/SELL order endpoint (prohibited from UI).
- `/api/ai_chat`, `/api/ai_mascot`, `/api/multi_turn_chat`: AI chat prototypes (zero trading authority).
- `/api/ai_training`, `/api/ai_train`: AI training endpoints (disabled).
- Speculative quant radar endpoints: `/api/funding_arbitrage`, `/api/liquidation_radar`, `/api/volatility_skew`, `/api/pairs_trading`, `/api/whale_tracker`, `/api/cross_basis`, `/api/rl_regime`, `/api/lead_lag`, `/api/smc`, `/api/hfmm`, `/api/ai_synthesis`, `/api/smart_grid`, `/api/pca_basket`, `/api/subaccount_yield`, `/api/genetic_evolution`, `/api/digital_twin_stress`, `/api/edge_latency`.
None of these endpoints are part of the certified offline execution surface. Web V2 will NOT expose them.

---

## 3. Asset Delivery & CDN Removal Strategy

### Current CDN Dependencies (To Be Removed)
Existing templates (`index.html`, `dashboard.html`, `login.html`, `risk_warning.html`) currently load external runtime scripts:
1. `https://cdn.tailwindcss.com` (runtime Tailwind compilation — prohibited in production).
2. `https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css` (FontAwesome CDN).
3. `https://fonts.googleapis.com` & `https://fonts.gstatic.com` (Inter & JetBrains Mono fonts).
4. `https://cdn.jsdelivr.net/npm/chart.js` (Chart.js CDN).

### Web V2 Self-Hosted Asset Architecture
In accordance with Requirement 25 & 26:
1. **CSS System**: Self-contained CSS compiled and bundled in `web/static/css/` containing all Obsidian Quants tokens, layout utilities, and component classes. Zero runtime Tailwind CDN.
2. **Typography**: Self-hosted or system web fonts for Inter and JetBrains Mono with tabular figures (`font-feature-settings: "tnum" 1, "zero" 1;`).
3. **Icons**: Inline SVG icons or lightweight local SVG sprite system replacing external FontAwesome CDN.
4. **Charts**: Lightweight local SVG/Canvas rendering for equity curves and sparklines. No external CDN script dependencies.
