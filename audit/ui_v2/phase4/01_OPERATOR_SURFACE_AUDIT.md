# 01 — OPERATOR SURFACE AUDIT

## 1. Surface Identification & Scope

The operator control surfaces integrated in Phase 4 are:
1. **Web Dashboard V2**:
   - Location: Tab `[RỦI RO]` (`risk`)
   - Controls:
     - `[EMERGENCY HALT]` (Action button)
     - `[RESUME WITH CAS]` (Conditional action button)
     - `[CLOSE ALL]` (Disabled indicator only)
2. **Flutter iOS V2**:
   - Location: Screen `RiskTab`
   - Controls:
     - `[HALT]` (Action button)
     - `[RESUME]` (Conditional action button)
     - `[ĐÓNG TẤT CẢ VỊ THẾ]` (Disabled indicator only)

## 2. Invariants Checked

| Surface | Action | Single Submit Lock | Confirmation Modal | Auth Enforced | Endpoint |
|---|---|---|---|---|---|
| Web V2 | HALT | YES (`isActionInFlight`) | YES (Dialog) | YES (Admin cookie / session) | POST `/api/pause` |
| Web V2 | RESUME | YES (`isActionInFlight`) | YES (Shows generation) | YES (Admin cookie / session) | POST `/api/resume` |
| Web V2 | CLOSEALL | N/A | N/A | Disabled (`pointer-events-none opacity-40`) | NONE (No request) |
| Flutter V2 | HALT | YES (`_isExecuting`) | YES (`QuantConfirmSheet`) | YES (Admin Bearer token) | POST `/api/pause` |
| Flutter V2 | RESUME | YES (`_isExecuting`) | YES (`QuantConfirmSheet` + CAS gen) | YES (Admin Bearer token) | POST `/api/resume` |
| Flutter V2 | CLOSEALL | N/A | N/A | Disabled (`onPressed: null`) | NONE (No request) |

## 3. Surface Exclusions Confirmed

The following mutation actions are completely excluded from both surfaces:
- Manual order entry (Buy / Sell)
- Manual single-position close
- Emergency CLOSEALL execution
- Strategy toggle / parameters mutation
- Market scanner trigger
- AI model weights / training
- Credentials insertion / mutation
