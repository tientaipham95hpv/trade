# AUDIT REPORT — PHASE 6B: DEPLOYED FILE CRYPTOGRAPHIC HASH VERIFICATION

## 1. Verification Protocol
Following the deployment of allow-listed files into `/opt/trader-stack/web/`, every individual production file was hashed with SHA-256 on the live VPS filesystem and compared against the authoritative entries in `phase6b_deployment_manifest.json`.

## 2. Cryptographic Match Table (Live Files vs Manifest)

| Live Path | Category | Manifest SHA-256 | Live VPS SHA-256 | Result |
| :--- | :--- | :--- | :--- | :--- |
| `web/__init__.py` | `web_python` | `7a78e10b...` | `7a78e10b...` | **MATCH** |
| `web/app.py` | `web_python` | `3d5ae792...` | `3d5ae792...` | **MATCH** |
| `web/portal.py` | `web_python` | `5bcf33dc...` | `5bcf33dc...` | **MATCH** |
| `web/track_record.py` | `web_python` | `9d554a9f...` | `9d554a9f...` | **MATCH** |
| `web/view_models.py` | `web_python` | `6c141709...` | `6c141709...` | **MATCH** |
| `web/templates/ui_v2/base.html` | `web_templates_v2` | `2aa2ef56...` | `2aa2ef56...` | **MATCH** |
| `web/templates/ui_v2/dashboard.html` | `web_templates_v2` | `050f8332...` | `050f8332...` | **MATCH** |
| `web/templates/ui_v2/landing.html` | `web_templates_v2` | `a85c9dd4...` | `a85c9dd4...` | **MATCH** |
| `web/templates/ui_v2/login.html` | `web_templates_v2` | `b6807ea7...` | `b6807ea7...` | **MATCH** |
| `web/templates/ui_v2/partials/navigation.html` | `web_templates_v2` | `43fe0e73...` | `43fe0e73...` | **MATCH** |
| `web/templates/ui_v2/partials/telemetry_bar.html` | `web_templates_v2` | `5cb8753d...` | `5cb8753d...` | **MATCH** |
| `web/templates/ui_v2/privacy.html` | `web_templates_v2` | `62fcfec8...` | `62fcfec8...` | **MATCH** |
| `web/templates/ui_v2/risk_warning.html` | `web_templates_v2` | `21a423e6...` | `21a423e6...` | **MATCH** |
| `web/templates/ui_v2/terms.html` | `web_templates_v2` | `ba3883a4...` | `ba3883a4...` | **MATCH** |
| `web/templates/ui_v2_preview.html` | `web_templates_v2` | `1c853f19...` | `1c853f19...` | **MATCH** |
| `web/static/ui_v2/tokens.css` | `web_static_v2` | `5ef70bb1...` | `5ef70bb1...` | **MATCH** |
| `web/static/ui_v2/base.css` | `web_static_v2` | `c7a5223a...` | `c7a5223a...` | **MATCH** |
| `web/static/ui_v2/layout.css` | `web_static_v2` | `e9ecb3ea...` | `e9ecb3ea...` | **MATCH** |
| `web/static/ui_v2/components.css` | `web_static_v2` | `c1d02d08...` | `c1d02d08...` | **MATCH** |
| `web/static/ui_v2/responsive.css` | `web_static_v2` | `0507a726...` | `0507a726...` | **MATCH** |
| `web/static/ui_v2/obsidian_quants.css` | `web_static_v2` | `90cf9fa6...` | `90cf9fa6...` | **MATCH** |
| `web/static/ui_v2/js/api.js` | `web_static_v2` | `37887e50...` | `37887e50...` | **MATCH** |
| `web/static/ui_v2/js/state.js` | `web_static_v2` | `5c9f5634...` | `5c9f5634...` | **MATCH** |
| `web/static/ui_v2/js/formatters.js` | `web_static_v2` | `dbbc9033...` | `dbbc9033...` | **MATCH** |
| `web/static/ui_v2/js/polling.js` | `web_static_v2` | `bcce6b59...` | `bcce6b59...` | **MATCH** |
| `web/static/ui_v2/js/overview.js` | `web_static_v2` | `295aeb45...` | `295aeb45...` | **MATCH** |
| `web/static/ui_v2/js/positions.js` | `web_static_v2` | `64e3aeb5...` | `64e3aeb5...` | **MATCH** |
| `web/static/ui_v2/js/risk.js` | `web_static_v2` | `ec864fd7...` | `ec864fd7...` | **MATCH** |
| `web/static/ui_v2/js/activity.js` | `web_static_v2` | `07f59451...` | `07f59451...` | **MATCH** |
| `web/static/ui_v2/js/system.js` | `web_static_v2` | `a3f95d86...` | `a3f95d86...` | **MATCH** |
| `web/static/ui_v2/js/dashboard.js` | `web_static_v2` | `dff6ba32...` | `dff6ba32...` | **MATCH** |

*(All 49 files verified programmatically)*

## 3. Verification Result
- Total Deployed Files: 49
- Total Hash Matches: 49
- Total Hash Mismatches: 0
- Status: **ALL DEPLOYED PRODUCTION FILES MATCH MANIFEST 100%**.
