# 01 — RELEASE CANDIDATE SCOPE (`UI_V2_RC1`)

## 1. Scope Definition

The `UI_V2_RC1` candidate represents the consolidated deliverable for the Obsidian Quants UI redesign:
- **Target Deployment Platform**: Web Dashboard (`https://trader.noza.site`) and Flutter iOS Mobile App.
- **Operating Environment**: `OFFLINE` (deterministic execution service supervisor).
- **Core Architecture Freeze**: `core/execution/*` remains untouched.

## 2. In-Scope Components

1. **Web Dashboard V2**:
   - Institutional dark-mode layout (`web/static/ui_v2/css/*`).
   - Server-side rendered Jinja2 templates (`web/templates/ui_v2/*`).
   - Client runtime logic (`web/static/ui_v2/js/*`):
     - Single-flight polling with tab awareness (`dashboard.js`).
     - Real-time technical telemetry (`overview.js`).
     - Read-only positions table (`positions.js`).
     - Gated operator actions and safety metrics (`risk.js`).
     - Trade history and audit logs (`activity.js`).
     - Governance and certification transparency (`system.js`).
   - Public institutional landing and legal pages (`landing.html`, `login.html`, `risk_warning.html`, `terms.html`, `privacy.html`).

2. **Flutter iOS V2**:
   - Replaced mobile architecture in `ios-app/lib/ui_v2/*`:
     - 4 core tabs: `OverviewTab`, `PositionsTab`, `RiskTab`, `SystemTab`.
     - Secure token storage via Keychain (`AuthStore`).
     - HTTPS & host validated Gateway configuration.
     - Single-in-flight polling lifecycle (`PollingController`).
     - CAS-protected operator mutations (`sendHalt`, `sendResume`).
     - Zero fake data defaults (em dash for missing/null financial telemetry).

3. **Backend Application Layer**:
   - Dynamic environment projection and state enrichment in `/api/status`.
   - CAS validation in `/api/resume` requiring `expected_halt_generation`.
   - RBAC dependency `verify_operator_admin` (401/403).
   - Zero-secret, read-only view model builders in `web/view_models.py`.

## 3. Explicit Out-of-Scope Exclusions

- Zero Binance Testnet order mutations.
- Zero Binance LIVE order mutations.
- Zero emergency CLOSEALL activation.
- Zero strategy parameter mutations or manual order entries.
- Zero copy-trade features.
- Zero client credential storage.
