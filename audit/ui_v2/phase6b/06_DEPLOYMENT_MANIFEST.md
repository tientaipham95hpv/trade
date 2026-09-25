# AUDIT REPORT — PHASE 6B: IMMUTABLE DEPLOYMENT PACKAGE & MANIFEST SPECIFICATION

## 1. Package Identification
- **Deployment Identifier**: `UI_V2_RC1_PHASE6B_12e92c3`
- **Originating Git Commit**: `12e92c38a26befd3a575887355b7337c89cacad4`
- **Manifest Path**: `audit/ui_v2/phase6b/evidence/phase6b_deployment_manifest.json`
- **Manifest SHA-256 Digest**: `fabb6c6e2bccd6be5383a4c89ff4ce96063967155ba0046677a15d55019a08ce`
- **Staging Archive**: `UI_V2_RC1_PHASE6B_12e92c3.tar.gz`
- **Archive Size**: `1,214,486 bytes`
- **Archive SHA-256 Digest**: `d5e4823e0498d4fb895799e24b3c3afea052db4af0016a1d1f87cd001f0d9c73`

## 2. Integrity Summary
- Total files specified: 49
- Total files verified in staging: 49
- Total files deployed to live `/opt/trader-stack/web/`: 49
- Core files included in package: 0
- Secret scan findings: 0

## 3. Deployment Flow Architecture
1. Local git extraction from commit `12e92c3` to temporary staging directory `C:\temp\trade-deploy-staging\UI_V2_RC1_PHASE6B_12e92c3\`.
2. SHA-256 calculation for every individual file.
3. Creation of `phase6b_deployment_manifest.json`.
4. Packaging into `UI_V2_RC1_PHASE6B_12e92c3.tar.gz`.
5. Secure copy (`scp`) to VPS staging directory `/root/trader-release-staging/`.
6. Independent SHA-256 verification of archive on VPS.
7. Decompression and cryptographic validation of all 49 files against manifest on VPS.
8. Atomic copy into production root `/opt/trader-stack/web/`.
