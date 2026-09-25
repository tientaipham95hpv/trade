# AUDIT REPORT — PHASE 6B: PRODUCTION DEPLOYMENT ALLOW-LIST

## 1. Mandate & Boundary Enforcement
To maintain strict determinism and eliminate unwanted artifacts, non-production files were strictly excluded from the deployment package.
- **Allowed Category**: Web V2 templates, static assets, FastAPI endpoints, view models, legal templates, portal support.
- **Strictly Excluded**:
  - `core/execution/*`: 0 files copied (execution core stays frozen in-place).
  - `ios-app/*`: 0 files copied (mobile code compiled via CI).
  - `.github/*`: 0 files copied.
  - `tests/*`: 0 files copied.
  - `audit/*`: 0 files copied.
  - `.env`, `*.db`, `*.sqlite`: 0 runtime states copied.

## 2. Inventory of the 49 Deployed Files

### 2.1 Web Application Python Files (5 files):
- `web/__init__.py`
- `web/app.py`
- `web/portal.py`
- `web/track_record.py`
- `web/view_models.py`

### 2.2 Web V2 Templates (10 files):
- `web/templates/ui_v2/base.html`
- `web/templates/ui_v2/dashboard.html`
- `web/templates/ui_v2/landing.html`
- `web/templates/ui_v2/login.html`
- `web/templates/ui_v2/privacy.html`
- `web/templates/ui_v2/risk_warning.html`
- `web/templates/ui_v2/terms.html`
- `web/templates/ui_v2/partials/navigation.html`
- `web/templates/ui_v2/partials/telemetry_bar.html`
- `web/templates/ui_v2_preview.html`

### 2.3 Legacy Templates Preserved for Rollback (10 files):
- `web/templates/api_settings.html`
- `web/templates/dashboard.html`
- `web/templates/index.html`
- `web/templates/login.html`
- `web/templates/privacy.html`
- `web/templates/register.html`
- `web/templates/risk_warning.html`
- `web/templates/terms.html`
- `web/templates/track_record.html`

### 2.4 Web V2 Static Assets (14 files):
- `web/static/ui_v2/base.css`
- `web/static/ui_v2/components.css`
- `web/static/ui_v2/layout.css`
- `web/static/ui_v2/obsidian_quants.css`
- `web/static/ui_v2/responsive.css`
- `web/static/ui_v2/tokens.css`
- `web/static/ui_v2/js/activity.js`
- `web/static/ui_v2/js/api.js`
- `web/static/ui_v2/js/dashboard.js`
- `web/static/ui_v2/js/formatters.js`
- `web/static/ui_v2/js/overview.js`
- `web/static/ui_v2/js/polling.js`
- `web/static/ui_v2/js/positions.js`
- `web/static/ui_v2/js/risk.js`
- `web/static/ui_v2/js/state.js`
- `web/static/ui_v2/js/system.js`

### 2.5 Common Static Assets & Images (10 files):
- `web/static/css/client.css`
- `web/static/css/common.css`
- `web/static/css/portal_dashboard.css`
- `web/static/css/responsive.css`
- `web/static/favicon.svg`
- `web/static/logo.png`
- `web/static/js/theme.js`
- `web/static/images/sprites/sprite_01_pm.png`
- `web/static/images/sprites/sprite_02_risk.png`

**Total Allow-Listed Files**: 49
