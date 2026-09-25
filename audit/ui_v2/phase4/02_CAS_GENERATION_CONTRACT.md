# 02 — CAS GENERATION CONTRACT SPECIFICATION

## 1. Context & Motivation

In automated trading systems, an emergency halt can be triggered by either human operators, circuit breakers, or critical risk protections.
If Operator A decides to resume when HALT generation was #1, but in the interim another circuit breaker tripped generating HALT #2, resuming blindly would clear a protective halt that the operator never saw.

Therefore, `RESUME` implements Compare-And-Swap (CAS) on `halt_generation`.

## 2. API Contract: POST `/api/resume`

### Request Payload
```json
{
  "expected_halt_generation": 3,
  "source": "flutter" // or "web"
}
```

### Preconditions & Validations
1. **Authorization**: Caller must be an authenticated `admin`. Non-admin -> `403 Forbidden`.
2. **Payload Validation**:
   - `expected_halt_generation` missing or not positive integer -> `400 Bad Request` (`INVALID_HALT_GENERATION`).
3. **Execution Service State**:
   - State `UNKNOWN` -> `503 Service Unavailable` (`SERVICE_UNKNOWN`).
   - `global_halt == false` -> `409 Conflict` (`NO_ACTIVE_HALT`).
   - `recovery_required == true` -> `409 Conflict` (`RECOVERY_REQUIRED`).
4. **CAS Generation Match**:
   - Current core `halt_generation != expected_halt_generation` -> `409 Conflict` (`STALE_HALT_GENERATION`).
   - Response includes both `current_generation` and `expected_generation`.

### Success Response
```json
{
  "success": true,
  "is_paused": false,
  "halt_generation": null,
  "authoritative_state": "RESUMED",
  "message": "Execution Service đã xác nhận kích hoạt lại thành công"
}
```

## 3. Client Behavior on 409 STALE_HALT_GENERATION
- In both Web V2 and Flutter iOS V2:
  - Error dialog / alert is presented alerting the operator that the halt generation changed.
  - The UI triggers an immediate telemetry refresh to sync with current authoritative generation.
  - The user must review the new status before submitting a new RESUME request with the new generation.
