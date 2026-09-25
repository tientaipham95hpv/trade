# 06 — STALE INTENT & RECOVERY GUARD END-TO-END VERIFICATION

## 1. Problem Definition: The Stale Operator Intent Risk

In multi-operator environments or when automatic risk circuit breakers trigger, race conditions can occur:
- Screen A opens when system is halted at Generation `A`.
- A new risk incident occurs, causing the system to advance to Generation `B`.
- Operator on Screen A clicks RESUME believing they are clearing incident `A`.
- If unvalidated, incident `B` would be cleared inadvertently, leading to catastrophic capital exposure.

## 2. Test Construction & Verification

Tested in Python via `tests/test_ui_v2_phase5_rc.py::test_cas_stale_intent_and_recovery_guards` and in Flutter via `ios-app/test/ui_v2_phase5_rc_test.dart`:

### Scenario 1: Stale Generation Rejection
1. System is HALTED at Generation `4`.
2. Outdated client submits `expected_halt_generation: 3`.
3. Backend checks: `current_generation (4) != expected_generation (3)`.
4. Execution is refused without invoking `resume()` on execution core.
5. Response returned:
   - HTTP Status: `409 Conflict`
   - Body:
     ```json
     {
       "success": false,
       "code": "STALE_HALT_GENERATION",
       "current_generation": 4,
       "expected_generation": 3,
       "message": "Không thể RESUME: Thế hệ HALT đã thay đổi (hiện tại: 4, yêu cầu: 3)"
     }
     ```
6. Client reaction:
   - Alert shown to operator indicating generation changed.
   - Immediate status refresh to fetch current generation `4`.
   - Zero automatic retry.

### Scenario 2: Recovery Required Guard
1. System is HALTED with `recovery_required: true` (e.g. state inconsistency or database reconciliation pending).
2. Client submits `expected_halt_generation: 4`.
3. Backend checks: `recovery_required == true`.
4. Response returned:
   - HTTP Status: `409 Conflict`
   - Body:
     ```json
     {
       "success": false,
       "code": "RECOVERY_REQUIRED",
       "message": "Không thể RESUME: Yêu cầu khắc phục trạng thái khẩn cấp (recovery_required=True)"
     }
     ```
5. Client reaction:
   - Alert informs operator that manual system recovery is required.
   - UI disables RESUME button until recovery condition is resolved.
