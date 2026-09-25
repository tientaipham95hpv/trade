# 15 — PHASE 6 HANDOFF SPECIFICATION

## 1. Readiness Assessment

```text
STATUS: READY FOR UI PHASE 6 DEPLOYMENT
RELEASE CANDIDATE: UI_V2_RC1
ENVIRONMENT: OFFLINE
DEPLOYMENT TARGET: https://trader.noza.site
```

All 52 hard gate conditions have been satisfied:
- Web V2 implementation complete.
- Flutter iOS V2 implementation complete.
- Local feature-flag cutover validated (`UI_V2_ENABLED=true`).
- Legacy rollback tested and confirmed operational (`UI_V2_ENABLED=false`).
- Authentication, RBAC, and session expiry verified.
- HALT and RESUME with CAS generation validation certified.
- CLOSEALL verified 100% unwired.
- 0 external runtime CDNs, 0 secret exposures, 0 direct Binance mutations.
- 100% pass across 348 Python tests and 60 Flutter tests.
- Core hashes: 15/15 verified match.

## 2. Phase 6 Deployment Procedure

1. **Pre-flight on Target VPS**:
   - Verify VPS execution core hashes match 15/15 baseline.
   - Verify `trader-stack-offline.service` status is active and healthy.
2. **Synchronize RC1 Codebase**:
   - Deploy `UI_V2_RC1` files according to manifest `audit/ui_v2/phase5/evidence/ui_v2_rc1_manifest.json`.
3. **Configure Environment**:
   - In `/etc/trader/trader.env`:
     ```bash
     UI_V2_ENABLED=true
     UI_V2_DEV_PREVIEW_ENABLED=false
     ENVIRONMENT=OFFLINE
     ```
4. **Restart Web Service**:
   - `sudo systemctl restart trader-stack-offline.service`
5. **Post-Deployment Smoke Verification**:
   - `curl -I https://trader.noza.site/` -> 200 OK (V2 landing)
   - `curl -I https://trader.noza.site/health` -> 200 OK
   - `curl -I https://trader.noza.site/ready` -> 200 READY
   - Authenticated operator smoke login via browser.

## 3. iOS Pre-Build Checklist (Phase 6/7 Mac Environment)

- **Bundle Identifier**: `com.astraquant.binancequantpro`
- **Minimum iOS Version**: `iOS 14.0`
- **Keychain Requirement**: Keychain Sharing entitlement for `quant_session_token`
- **Network Permissions**: `NSAppTransportSecurity` requires HTTPS (no arbitrary loads)
- **Base URL**: Hardcoded institutional default `https://trader.noza.site`
- **Signing**: Apple Developer Distribution Certificate + Provisioning Profile
- **Build Mode**: `flutter build ipa --release` (To be executed on macOS host with Xcode)
