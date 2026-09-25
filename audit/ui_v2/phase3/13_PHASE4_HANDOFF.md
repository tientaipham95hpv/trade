# 13 — PHASE 4 HANDOFF SPECIFICATION

## 1. Readiness State

Phase 3 is complete. The mobile interface has been transformed into a read-only operator console.

Current baseline:
- Flutter V2 screens (`OverviewTab`, `PositionsTab`, `RiskTab`, `SystemTab`) fully implemented.
- `AuthStore` secured via iOS Keychain with token validation.
- Polling coordinator active with background suspension and in-flight request lock.
- Zero fake financial values; null values render strictly as `—`.
- Prohibited surfaces (Scanner, Copilot, manual buy/sell buttons) retired.
- Python tests: 331/331 pass.
- Flutter tests: 31/31 pass.
- Execution core: 15/15 files match (0 mismatches).

---

## 2. Phase 4 Objectives (Operator Actions & Mutation Wiring)

Phase 4 will focus exclusively on:
1. **Operator Mutations Wiring**:
   - Wiring `POST /api/pause` (HALT) with target scope and expected halt generation.
   - Wiring `POST /api/resume` (RESUME) with monotonic generation validation.
   - Wiring `POST /api/close_all_positions` (CLOSE ALL) with confirmation gating.
2. **State Synchronization**:
   - Updating UI optimistically or handling immediate polling refresh post-mutation.
   - Idempotency token generation and error handling.
3. **Execution Safety Hard Rules**:
   - Continue strict preservation of `core/execution/*` freeze.
   - Zero direct Binance access from clients.
   - All mutations pass strictly through backend application gateway with admin authentication.

Phase 3 is ready for audit approval. **STOP**. Do not begin Phase 4 until approved.
