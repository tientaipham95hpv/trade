# 08 — PHASE 2 HANDOFF & IMPLEMENTATION READINESS

## 1. Readiness Assessment

Phase 1 (Obsidian Quants Design Foundation) is **COMPLETE and CERTIFIED**. All prerequisite foundations, tokens, components, test suites, and cryptographic core verifications are established and locked.

The repository is fully ready to transition into **Phase 2: Web Dashboard V2 Implementation**.

---

## 2. Phase 2 Scope & Objectives

In Phase 2, the Web Dashboard will be refactored into the modular Obsidian Quants layout while strictly maintaining all existing FastAPI routes and backend data contracts:

1. **Dashboard Shell Architecture**:
   - Refactor `web/templates/` to use the V2 layout (`base.css`, `layout.css`, `components.css`).
   - Implement the top telemetry ticker bar with live ping, IPC status, service PID, and environment indicator.
2. **Telemetry Panels**:
   - Institutional System Status Panel (Execution Service Health, IPC status, State Store integrity).
   - Risk Ledger & Breaker Telemetry Panel (Max drawdown, breaker trip indicators, current state).
   - Authoritative Positions & Balance Grid (Tabular-nums formatted balances, margin ratios, active positions).
   - Audit / Execution Log Feed (Chronological execution receipts, state changes, protection events).
3. **Operational Controls (Fail-Closed & CAS-Guarded)**:
   - Emergency Halt Trigger with confirmation modal.
   - Breaker Reset / Engine Resume Modal with mandatory reason and CAS generation token validation.
4. **Data Polling & SSE Integration**:
   - Seamlessly connect to `/api/status`, `/api/executions`, and existing authenticated API routes.
   - Enforce fail-closed state rendering if backend becomes unreachable (display "SERVICE DISCONNECTED" instead of stale data).

---

## 3. Strict Boundary Rules for Phase 2

1. **DO NOT MODIFY `core/execution/*`**: Must maintain 15/15 hash match at all times.
2. **DO NOT DEPLOY TO VPS**: VPS deployment is strictly scheduled for Phase 6. All work remains in local Git staging.
3. **DO NOT INTRODUCE PROHIBITED SURFACES**:
   - No Binance API key/secret management or forms.
   - No copy-trade options or triggers.
   - No manual order entry (BUY / SELL).
   - No AI automated order placement authority.
   - No environment switcher (environment is strictly determined by execution service).
   - No fake financial fallbacks (e.g. `$1000` fallback).
4. **DO NOT BREAK EXISTING AUTHENTICATED ROUTES**:
   - Retain session and cookie authentication patterns.
   - Ensure backwards compatibility for monitoring scripts.
