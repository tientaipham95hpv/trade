# 13 — RELEASE CANDIDATE MANIFEST (`UI_V2_RC1`)

## 1. Release Identification

- **Release Identifier**: `UI_V2_RC1`
- **Timestamp**: `2026-09-25T22:55:00+07:00`
- **Total Production-Intended Files**: 63
- **Manifest File**: `audit/ui_v2/phase5/evidence/ui_v2_rc1_manifest.json`
- **Manifest SHA-256 Digest**: `042817ef5b0840366464d1f6618f12360ec2b171e87ca3801e8e0f773fa1ccc8`

## 2. Categorization Breakdown

| Category | File Count | Purpose |
|---|---|---|
| `web_templates` | 13 | Jinja2 HTML templates for V2 dashboard, landing, login, and legal |
| `web_static` | 13 | V2 CSS stylesheets, tokens, responsive layouts, and JS controllers |
| `web_application` | 2 | FastAPI web application (`web/app.py`, `web/view_models.py`) |
| `flutter_source` | 27 | Flutter iOS Obsidian Quants UI suite (`ios-app/lib/ui_v2/**/*`) |
| `configuration` | 1 | Global settings template (`config/settings.py`) |
| `tests_python` | 4 | UI V2 foundation, web, phase 4 operator, and phase 5 RC test suites |
| `tests_flutter` | 3 | Phase 3 model, Phase 4 CAS action, and Phase 5 RC flutter test suites |
| **Total** | **63** | Consolidated release candidate |

## 3. Strict Exclusions Verified
- Runtime databases (`*.db`, `*.sqlite`, `*.wal`): Excluded
- Secrets and `.env` files: Excluded
- Temporary log files (`*.log`): Excluded
- Build artifacts (`build/`, `__pycache__/`): Excluded
- Execution core files (`core/execution/*`): Excluded (tracked separately in core manifest)
