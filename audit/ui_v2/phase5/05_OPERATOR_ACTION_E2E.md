# 05 — OPERATOR ACTION END-TO-END VERIFICATION

## 1. Scope & Execution Surfaces

Phase 5 verified offline operator mutations (`HALT` and `RESUME`) on:
- Web Dashboard V2 (`web/static/ui_v2/js/risk.js`)
- Flutter iOS V2 (`ios-app/lib/ui_v2/screens/risk_tab.dart`, `ios-app/lib/ui_v2/services/quant_api_client.dart`)
- Application API layer (`web/app.py`)

## 2. Emergency HALT E2E Lifecycle

1. **Initial State**: Execution service reports state `HEALTHY`, `is_paused = false`, `halt_generation = N`.
2. **Operator Action**:
   - Web: Operator clicks `[EMERGENCY HALT]`, confirms dialog.
   - Flutter: Operator taps `HALT`, modal `QuantConfirmSheet` appears with `PHẠM VI: GLOBAL`, operator confirms.
3. **Execution Guard**:
   - Single-submit execution lock is engaged (`isActionInFlight = true` in Web, `_isExecuting = true` in Flutter).
   - Double-clicking or double-tapping is rejected locally without sending multiple HTTP requests.
4. **Transport**:
   - Dispatches `POST /api/pause` with `{ "reason": "...", "source": "web" | "flutter" }`.
   - Admin authorization verified by `verify_operator_admin`.
5. **Authoritative Response**:
   - Execution client calls `set_halt(reason=..., source=...)`.
   - Response returns `{ "success": true, "is_paused": true, "halt_generation": N+1, "authoritative_state": "HALTED" }`.
6. **Telemetry Refresh**:
   - Immediate out-of-band telemetry fetch refreshes system status.
   - UI reflects `HALTED`, displays new generation `#N+1`.

## 3. Compare-And-Swap (CAS) RESUME E2E Lifecycle

1. **Pre-condition Check**:
   - `resume_allowed == true` (evaluated by backend as `is_paused == true && recovery_required == false`).
   - If `resume_allowed == false`, the RESUME button is strictly disabled in both Web and Flutter.
2. **Operator Action**:
   - Operator clicks/taps `RESUME`.
   - Confirmation dialog explicitly indicates the expected generation `#N+1`.
3. **Transport with CAS**:
   - Dispatches `POST /api/resume` with `{ "expected_halt_generation": N+1, "source": "web" | "flutter" }`.
4. **Backend CAS Evaluation**:
   - Verifies `expected_halt_generation == current_generation`.
   - Invokes execution client `resume(expected_halt_generation=N+1)`.
   - Returns `{ "success": true, "is_paused": false, "authoritative_state": "RESUMED" }`.
5. **State Transition**:
   - Telemetry refreshes, system displays `HEALTHY` / `OPERATIONAL`, `is_paused = false`.
