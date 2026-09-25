# 09 — LEGACY DASHBOARD RETIREMENT & CUTOVER PLAN

## 1. Inventory of Legacy Debt

1. **Inline Monolith in `web/app.py`**:
   - Location: Lines ~3115 to ~8520 (`dashboard_page()`).
   - Size: ~5,400 lines of inline HTML, CSS, Chart.js, lightweight-charts, and JavaScript.
   - Status: Active production interface for admin users when `UI_V2_ENABLED = False`.

2. **Template Monoliths in `web/templates/`**:
   - `templates/dashboard.html`: ~42 KB customer portal template. Contains hardcoded fallback metrics (e.g. `dashboard_data.get('equity', 1000.0)`).
   - `templates/login.html`: ~11 KB login page relying on external Tailwind and FontAwesome CDNs.
   - `templates/index.html`: ~18 KB public landing page.

---

## 2. Phase 2 Isolation Strategy

In Phase 2, **zero legacy code was deleted**:
- Deleting the legacy inline dashboard or legacy templates in Phase 2 would risk breaking production routing on the live VPS during routine deployments.
- Instead, Web V2 is built entirely inside clean files (`web/templates/ui_v2/` and `web/static/ui_v2/`).
- Routing is cleanly branched via `is_ui_v2_enabled()`:
  - When `UI_V2_ENABLED = False` (default), 100% of legacy routes and behavior remain untouched.
  - V2 is fully accessible for testing at `/portal/dashboard-v2` and `/portal/login-v2`.
  - When `UI_V2_ENABLED = True`, production routes seamlessly switch to the V2 server-rendered templates.

---

## 3. Phase 6 Cutover & Deletion Roadmap

The retirement of legacy code will proceed in three strict steps during **UI Phase 6: VPS Deployment**:

1. **Step 1: VPS Staging & Feature Flag Activation**:
   - Deploy V2 code to VPS alongside legacy code.
   - Set `UI_V2_ENABLED=true` in `trader-stack-offline.service` environment.
   - Verify `https://trader.noza.site/` serves V2 landing page.
   - Verify `/portal/dashboard` serves V2 operator terminal.
   - Verify `/health` (HTTP 200) and `/ready` (READY) contracts remain green.

2. **Step 2: Operational Burn-In**:
   - Observe live system over a 24-hour cycle.
   - Confirm zero regression in Telegram notifications, execution receipts, or circuit breaker trips.

3. **Step 3: Surgical Deletion of Legacy Debt**:
   - Once signed off, remove `dashboard_page()` from `web/app.py` (~5,400 lines deleted).
   - Remove legacy templates (`templates/dashboard.html`, `login.html`, `index.html`).
   - Run full regression suite (331 tests) and re-verify core execution hashes.
   - Commit cleanup cleanly to Git.
