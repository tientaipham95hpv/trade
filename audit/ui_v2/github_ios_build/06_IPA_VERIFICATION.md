# AUDIT REPORT — PHASE 6A: UNSIGNED IPA DOWNLOAD & CRYPTOGRAPHIC VERIFICATION

## 1. Download Evidence
- **Download Source**: GitHub Actions Artifact `BinanceQuantPro-iOS-unsigned-UI_V2_RC1` from Run `36162430241`
- **Download CLI Command**:
  ```powershell
  gh run download 36162430241 -n BinanceQuantPro-iOS-unsigned-UI_V2_RC1 -D "C:\temp\trade-ios-rc1" --repo tientaipham95hpv/trade
  ```
- **Local Download Path**: `C:\temp\trade-ios-rc1\`
- **Files Acquired**:
  - `BinanceQuantPro-UI_V2_RC1-unsigned.ipa` (10,597,817 bytes)
  - `SHA256SUMS.txt` (105 bytes)

## 2. Cryptographic Checksum Matching
The SHA-256 hash was generated on macOS runner and independently recalculated on the local Windows host.

### 2.1 Manifest Checksum (`SHA256SUMS.txt`)
```text
4eaa0e3385519ca30785f5d6aca8edaee63f2a47094e6a65a88a31f0786f1d07  BinanceQuantPro-UI_V2_RC1-unsigned.ipa
```

### 2.2 Local Verification (`Get-FileHash`)
```powershell
Get-FileHash "C:\temp\trade-ios-rc1\BinanceQuantPro-UI_V2_RC1-unsigned.ipa" -Algorithm SHA256
```
Output:
```text
Algorithm   Hash                                                                Path
---------   ----                                                                ----
SHA256      4EAA0E3385519CA30785F5D6ACA8EDAEE63F2A47094E6A65A88A31F0786F1D07   C:\temp\trade-ios-rc1\Binance...
```
**Match Status**: **EXACT MATCH (100% IDENTICAL)**.

## 3. Package Structure & Hygiene Audit
The IPA archive was unzipped and inspected using Python `zipfile` module:
- **Total Entries in Archive**: 80
- **`Payload/Runner.app` Directory Present**: `True`
- **`Payload/Runner.app/Info.plist` Present**: `True`
- **`Payload/Runner.app/Runner` Executable Present**: `True`
- **`Flutter.framework` Present**: `True`
- **Sensitive File Scan (`.env`, private keys, secrets)**: `0 findings (Empty)`

## 4. Certification
The unsigned IPA is certified authentic, uncorrupted, and structurally valid for ad-hoc signing, simulator deployment, or MDM distribution.
It is explicitly labeled **UNSIGNED** and has not been signed with TestFlight, Enterprise, or App Store certificates.
