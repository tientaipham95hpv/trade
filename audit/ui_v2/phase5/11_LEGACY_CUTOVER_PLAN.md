# 11 — LEGACY RETIREMENT & PHASE 6 CUTOVER PLAN

## 1. Principles of Safe Cutover

To ensure absolute operational safety:
1. Legacy UI components are NOT deleted during Phase 5.
2. Production cutover during Phase 6 is achieved via configuration flag: `UI_V2_ENABLED=true`.
3. Legacy components are kept available for rapid rollback should any anomaly occur during initial burn-in.

## 2. Legacy Component Inventory & Classification

| Component / Artifact | Path / Identifier | Cutover Classification | Action in Phase 6 / Post-Phase 6 |
|---|---|---|---|
| **Legacy Inline Dashboard** | `dashboard_page()` in `web/app.py` (lines 3348-8774) | `KEEP FOR ROLLBACK` | Retained as fallback when `UI_V2_ENABLED=false`. Mark `DELETE AFTER BURN-IN` (30-day stability window). |
| **Legacy Dashboard Template** | `web/templates/index.html`, `login.html` | `KEEP FOR ROLLBACK` | Fallback template for non-V2 traffic. Safe to archive after burn-in. |
| **Legacy CDN Dependencies** | CDN links in legacy templates (Tailwind CDN, FontAwesome, ChartJS) | `DEPRECATE` | Isolated exclusively to legacy templates; zero V2 code references these. Remove when legacy templates are deleted. |
| **Legacy Flutter Scanner** | `ios-app/lib/screens/scanner_screen.dart`, market scanner tabs | `DEPRECATE` | Retired in V2 navigation. Completely replaced by `SystemTab` and `RiskTab`. |
| **Legacy Flutter AI Copilot** | `ios-app/lib/screens/ai_copilot_screen.dart` | `DEPRECATE` | Retired in V2 navigation. Replaced by `ActivityTab` and institutional audit views. |
| **Legacy API Settings Route** | `/api/settings`, `/api/credentials` | `KEEP FAIL-CLOSED` | Returns 401 unauthenticated or 403 / 503 fail-closed response (`_client_account_feature_disabled`). Never restores credentials. |
| **Legacy Client DB Credential Table** | `ClientApiCredential` in database | `KEEP FAIL-CLOSED` | Retains tombstone schema. Zero active query or mutation capability. |

## 3. Rollback Procedure

If any issue arises during Phase 6 deployment on the VPS:
1. Set `UI_V2_ENABLED=false` in `/etc/trader/trader.env`.
2. Issue `sudo systemctl restart trader-stack-offline.service`.
3. System immediately reverts to legacy UI in < 2 seconds without code modification.
