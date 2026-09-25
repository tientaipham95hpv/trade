# 05 — FLUTTER iOS V2 OPERATOR ACTION EVIDENCE

## 1. Flutter Components & Changes

1. **`SystemStatus` Model** (`ios-app/lib/ui_v2/models/system_status.dart`):
   - Added `environment: json['environment'] as String?`
   - Added `recoveryRequired: json['recovery_required'] as bool? ?? false`
   - Added `resumeAllowed: json['resume_allowed'] as bool? ?? false`

2. **`QuantApiClient`** (`ios-app/lib/ui_v2/services/quant_api_client.dart`):
   - Implemented `sendHalt({String? reason, String source = 'flutter'})`
   - Implemented `sendResume({required int expectedHaltGeneration, String source = 'flutter'})`
   - Gated validation: `expectedHaltGeneration < 1` throws `INVALID_HALT_GENERATION` before network dispatch.
   - Handled 401 Unauthorized (token revocation + callback).
   - Handled 403 Forbidden (RBAC violation).
   - Handled 409 Conflict (`STALE_HALT_GENERATION`, `RECOVERY_REQUIRED`).
   - Timeout mapped to `UNKNOWN_OUTCOME`.

3. **`RiskTab`** (`ios-app/lib/ui_v2/screens/risk_tab.dart`):
   - Converted to `StatefulWidget` to maintain `_isExecuting` single-submit guard.
   - `[HALT]` opens `QuantConfirmSheet` with `targetScope: 'GLOBAL'`, calling `apiClient.sendHalt()`.
   - `[RESUME]` enabled only when `status?.resumeAllowed == true`, displays `expectedHaltGeneration`, calls `apiClient.sendResume()`.
   - `[CLOSE ALL]` strictly disabled with `onPressed: null`.

## 2. Test Evidence (16 Passing Tests in `ui_v2_phase4_test.dart`)

- Model parses `environment`, `recovery_required`, and `resume_allowed`.
- Model derives `resumeAllowed == false` when `recovery_required == true`.
- `sendHalt` dispatches POST `/api/pause` with admin Bearer token.
- `sendHalt` throws `UNKNOWN_OUTCOME` on transport timeout.
- `sendHalt` handles 403 Forbidden properly.
- `sendResume` validates `expectedHaltGeneration > 0` locally.
- `sendResume` sends CAS generation and returns result on 200.
- `sendResume` handles 409 `STALE_HALT_GENERATION` cleanly.
- `RiskTab` disables RESUME button when `resumeAllowed` is false.
- `RiskTab` enables RESUME button when `resumeAllowed` is true.
- `RiskTab` tapping HALT opens `QuantConfirmSheet`.
- `RiskTab` tapping RESUME opens `QuantConfirmSheet` showing CAS generation.
