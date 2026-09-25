# AUDIT REPORT — PHASE 6A: GITHUB ACTIONS WORKFLOW SPECIFICATION

## 1. Workflow Architecture & Parameters
- **Workflow File**: `.github/workflows/ios-unsigned-build.yml`
- **Workflow Name**: `iOS Unsigned Build`
- **Trigger**:
  ```yaml
  on:
    push:
      branches: [ ui-v2-rc1 ]
    workflow_dispatch:
  ```
- **Execution Runner**: `macos-15` (Apple Silicon M-series macOS environment)
- **Permissions**: `contents: read` (Strict principle of least privilege, preventing any unauthorized repo write access)
- **Target Flutter Version**: `3.44.0` (channel `stable`), exactly matching the local development baseline

## 2. Pipeline Stages
1. **Repository Checkout**:
   - Uses `actions/checkout@v4` with depth 1.
2. **Flutter Setup**:
   - Uses `subosito/flutter-action@v2` configured with `flutter-version: '3.44.0'`, `channel: 'stable'`, and `cache: true`.
3. **Environment Verification**:
   - Prints `flutter --version`, `dart --version`, and `xcodebuild -version`.
4. **Dependency Resolution**:
   - Executes `flutter pub get` in `ios-app/`.
5. **Static Analysis & Test Verification**:
   - Executes `flutter analyze` ensuring zero linter warnings or errors.
   - Executes `flutter test` executing all 60 unit and widget test cases.
6. **Unsigned Compilation**:
   - Executes `flutter build ios --release --no-codesign` in `ios-app/`.
7. **IPA Packaging**:
   - Creates `build/artifacts/` directory.
   - Constructs standard iOS IPA bundle layout: creates `Payload/`, copies `Runner.app` into `Payload/Runner.app`.
   - Compresses `Payload` into `BinanceQuantPro-UI_V2_RC1-unsigned.ipa`.
   - Computes SHA-256 hash using `shasum -a 256` and writes `SHA256SUMS.txt`.
8. **Artifact Upload**:
   - Uploads artifact named `BinanceQuantPro-iOS-unsigned-UI_V2_RC1` containing both `.ipa` and `SHA256SUMS.txt`.
   - Retention period set to 14 days.

## 3. Security & Integrity Controls
- **Code Signing Isolation**: Uses `--no-codesign` exclusively. No Apple Developer accounts, certificates, or provisioning profiles are required or accepted in CI secrets.
- **Leakage Prevention**: Inspects bundle contents ensuring no `.env`, operational keys, or staging credentials are packaged.
